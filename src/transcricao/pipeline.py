"""Orquestracao: original -> audio -> transcricao -> diarizacao -> qualidade.

Saida por item: um JSON com proveniencia, segmentos atribuidos e a fila de
verificacao humana. Nada aqui publica nada.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import atribuir, diarizar as mod_diarizar, proveniencia, qualidade
from .modelos import Status, Transcricao
from .transcrever import MODELO_PADRAO, transcrever


def processar(
    caminho_original: Path,
    *,
    fonte: str,
    saida: Path,
    url: str | None = None,
    perfil: str | None = None,
    publicado_em: str | None = None,
    coletado_em: str | None = None,
    nome_modelo: str = MODELO_PADRAO,
    modelo=None,
    usar_diarizacao: bool = True,
    max_falantes: int | None = None,
    mapa_falantes: dict[str, str] | None = None,
) -> Transcricao:
    caminho_original = Path(caminho_original)
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    base = caminho_original.stem

    # 1. proveniencia do arquivo COMO BAIXADO, antes de qualquer conversao
    manifesto = proveniencia.manifesto(
        caminho_original,
        fonte=fonte,
        url=url,
        perfil=perfil,
        publicado_em=publicado_em,
        coletado_em=coletado_em,
    )

    # 2. audio 16 kHz mono
    caminho_wav = saida / f"{base}.wav"
    manifesto["audio"] = proveniencia.extrair_audio(caminho_original, caminho_wav)

    # 3. transcricao
    segmentos, meta_asr = transcrever(
        caminho_wav, modelo=modelo, nome_modelo=nome_modelo
    )
    manifesto["asr"] = meta_asr

    avisos: list[str] = []

    # 4. diarizacao
    diarizacao_ok = False
    if usar_diarizacao:
        try:
            turnos = mod_diarizar.fundir_turnos_adjacentes(
                mod_diarizar.diarizar(caminho_wav, max_falantes=max_falantes)
            )
            segmentos = atribuir.aplicar_diarizacao(segmentos, turnos)
            diarizacao_ok = True
            manifesto["diarizacao"] = {
                "modelo": "pyannote/speaker-diarization-3.1",
                "turnos": len(turnos),
            }
        except mod_diarizar.DiarizacaoIndisponivel as e:
            avisos.append(f"diarizacao indisponivel: {e}")
            manifesto["diarizacao"] = {"disponivel": False, "motivo": str(e)}
    else:
        avisos.append("diarizacao desligada por opcao do usuario")

    if mapa_falantes:
        atribuir.renomear_falantes(segmentos, mapa_falantes)
        manifesto["mapa_falantes"] = mapa_falantes

    # 5. qualidade
    segmentos = qualidade.avaliar(segmentos)

    t = Transcricao(
        proveniencia=manifesto,
        idioma=meta_asr.get("idioma_detectado", "pt"),
        duracao=float(meta_asr.get("duracao_s", 0.0)),
        segmentos=segmentos,
        falantes=atribuir.falantes_presentes(segmentos),
        diarizacao_disponivel=diarizacao_ok,
        avisos=avisos,
    )

    proveniencia.salvar_json(t.para_dict(), saida / f"{base}.transcricao.json")
    proveniencia.salvar_json(
        fila_de_verificacao(t), saida / f"{base}.fila_revisao.json"
    )
    return t


def fila_de_verificacao(t: Transcricao) -> dict[str, Any]:
    """Itens que exigem um humano ouvir antes de qualquer publicacao.

    Cada item traz o segundo exato para conferencia. O revisor abre o
    original, pula para o timestamp, ouve e confirma ou corrige.
    """
    itens = [
        {
            "inicio": round(s.inicio, 2),
            "fim": round(s.fim, 2),
            "timestamp": _hms(s.inicio),
            "falante": s.falante,
            "texto": s.texto,
            "status": s.status.value,
            "motivos": s.motivos,
        }
        for s in t.segmentos
        if s.status is not Status.DESCARTADO
    ]
    return {
        "arquivo": t.proveniencia.get("arquivo"),
        "hash_sha256_original": t.proveniencia.get("hash_sha256_original"),
        "url": t.proveniencia.get("url"),
        "publicado_em": t.proveniencia.get("publicado_em_utc"),
        "coletado_em": t.proveniencia.get("coletado_em_utc"),
        "exige_revisao_humana": t.exige_revisao_humana,
        "multi_falante": t.multi_falante,
        "diarizacao_disponivel": t.diarizacao_disponivel,
        "avisos": t.avisos,
        "resumo": qualidade.resumo(t.segmentos),
        "itens": itens,
    }


def _hms(segundos: float) -> str:
    s = int(segundos)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def carregar_transcricao(caminho: Path) -> dict[str, Any]:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)
