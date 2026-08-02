"""Parser de legendas (WebVTT/SRT) para Segmento.

Puro — sem I/O, sem rede. Quem baixa o arquivo e' o coletor; aqui so se
interpreta o conteudo ja lido.

Legenda nao tem confianca de ASR (sem avg_logprob/no_speech_prob/
compression_ratio), entao os segmentos daqui nunca chegam a Status.OK por
conta propria — ver `qualidade.avaliar_texto` e `montar_segmentos`.
"""

from __future__ import annotations

import re

from .modelos import Segmento, Status
from .qualidade import avaliar_texto

_TAG_TEMPO = re.compile(r"<\d{2}:\d{2}:\d{2}[.,]\d{3}>")
_TAG_HTML = re.compile(r"</?c[^>]*>|</?[a-zA-Z][^>]*>")
_LINHA_TEMPO_VTT = re.compile(
    r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
)
_LINHA_INDICE_SRT = re.compile(r"^\d+$")


def _tempo_para_segundos(tempo: str) -> float:
    tempo = tempo.replace(",", ".")
    h, m, resto = tempo.split(":")
    s, ms = resto.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _limpar_texto(bruto: str) -> str:
    """Remove tags de timing por palavra e formatacao, colapsa espacos."""
    t = _TAG_TEMPO.sub("", bruto)
    t = _TAG_HTML.sub("", t)
    t = " ".join(t.split())
    return t.strip()


def parsear_cues(conteudo: str) -> list[tuple[float, float, str]]:
    """Extrai (inicio, fim, texto) de um arquivo VTT ou SRT.

    Cues identicos ao anterior sao descartados aqui: e' a assinatura mais
    comum de legenda automatica "rolling" do YouTube, que reemite o mesmo
    texto varias vezes com timestamps levemente diferentes. Isso nao resolve
    todo caso de rolling caption (uma cobertura completa exigiria remontar
    a legenda a partir das tags de timing por palavra), mas evita a
    duplicacao grosseira mais frequente.
    """
    cues: list[tuple[float, float, str]] = []
    texto_anterior: str | None = None

    blocos = re.split(r"\r?\n\r?\n+", conteudo.strip())
    for bloco in blocos:
        linhas = [l for l in bloco.splitlines() if l.strip()]
        if not linhas:
            continue

        idx_tempo = None
        for i, linha in enumerate(linhas):
            if _LINHA_TEMPO_VTT.search(linha):
                idx_tempo = i
                break
        if idx_tempo is None:
            continue

        m = _LINHA_TEMPO_VTT.search(linhas[idx_tempo])
        assert m is not None
        inicio = _tempo_para_segundos(m.group(1))
        fim = _tempo_para_segundos(m.group(2))

        texto_bruto = " ".join(linhas[idx_tempo + 1:])
        texto = _limpar_texto(texto_bruto)
        if not texto or texto == "WEBVTT":
            continue
        if texto == texto_anterior:
            continue

        cues.append((inicio, fim, texto))
        texto_anterior = texto

    return cues


def montar_segmentos(conteudo: str) -> list[Segmento]:
    """Converte o conteudo de uma legenda em Segmentos ja avaliados.

    Sem confianca de ASR: todo segmento vai para REVISAR, exceto quando o
    texto bate com alucinacao/spam conhecido (ai' vai direto pra
    DESCARTADO) — mesmas regras de `qualidade.avaliar_texto`.
    """
    segmentos: list[Segmento] = []
    for inicio, fim, texto in parsear_cues(conteudo):
        seg = Segmento(
            inicio=inicio,
            fim=fim,
            texto=texto,
            avg_logprob=0.0,
            no_speech_prob=0.0,
            compression_ratio=1.0,
        )
        motivos = avaliar_texto(texto)
        if motivos:
            seg.status = Status.DESCARTADO
            seg.motivos = motivos
        else:
            seg.status = Status.REVISAR
            seg.motivos = ["fonte: legenda, sem confianca de ASR — revisao obrigatoria"]
        segmentos.append(seg)
    return segmentos
