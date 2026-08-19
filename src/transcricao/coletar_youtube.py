"""Coletor do YouTube: legenda automatica quando existir, Whisper so no resto.

Baixa o video (nao so o audio) via yt-dlp: e' o arquivo original que serve de
prova de custodia, e a resposta ao "apagaram o post" precisa da midia
completa, nao so da faixa sonora. yt-dlp e' importado sob demanda para nao
exigir a lib em quem so testa a pipeline.

Se houver legenda no YouTube (manual ou automatica) nos idiomas pedidos, ela
substitui o Whisper — mas nunca herda a confianca do ASR: todo segmento vindo
de legenda vai para revisao humana obrigatoria (ver `legendas.py`). Sem
legenda, cai na pipeline normal (transcrever.py + diarizar.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import legendas, pipeline, proveniencia
from .modelos import Transcricao
from .transcrever import MODELO_PADRAO

IDIOMAS_PADRAO = ("pt", "pt-BR", "pt-PT")

FORMATO_PADRAO = "bv*[height<=1080]+ba/b"
FORMATO_RESERVA = "best"
NAVEGADOR_COOKIES_PADRAO = "chrome"


class ColetaIndisponivel(RuntimeError):
    pass


def _erro_menciona(erro: Exception, texto: str) -> bool:
    return texto in str(erro).lower()


def _falha_de_legenda_ou_formato(erro: Exception) -> bool:
    return _erro_menciona(erro, "subtitle") or _erro_menciona(
        erro, "unable to download video data"
    )


def _falha_de_formato(erro: Exception) -> bool:
    return _erro_menciona(erro, "unable to download video data")


def _data_para_iso(data: str | None) -> str | None:
    """Converte upload_date do yt-dlp ('AAAAMMDD') para ISO 8601 UTC.

    So a data e' confiavel: o yt-dlp nao expoe hora de publicacao. A hora
    fica zerada de proposito — nao inventar precisao que nao existe.
    """
    if not data or len(data) != 8:
        return None
    return f"{data[0:4]}-{data[4:6]}-{data[6:8]}T00:00:00+00:00"


def _escolher_legenda(
    info: dict[str, Any], idiomas: tuple[str, ...] = IDIOMAS_PADRAO
) -> tuple[str, str] | None:
    """Escolhe (idioma, tipo) preferindo legenda manual sobre automatica.

    `tipo` e' "manual" ou "automatica". None se nenhum idioma pedido tiver
    legenda disponivel.
    """
    manuais = info.get("subtitles") or {}
    automaticas = info.get("automatic_captions") or {}
    for idioma in idiomas:
        if idioma in manuais:
            return idioma, "manual"
    for idioma in idiomas:
        if idioma in automaticas:
            return idioma, "automatica"
    return None


def baixar(
    url: str,
    destino: Path,
    idiomas: tuple[str, ...] = IDIOMAS_PADRAO,
    baixar_legenda: bool = True,
    navegador_cookies: str | None = NAVEGADOR_COOKIES_PADRAO,
) -> dict[str, Any]:
    """Baixa video + legenda (se houver) e devolve metadados de proveniencia.

    `coletado_em` e' registrado logo apos o download terminar: e' o momento
    em que o COLETOR viu o conteudo, que e' o que a proveniencia exige.

    `baixar_legenda=False` pula o pedido de legenda por completo — use
    quando o chamador ja sabe que vai forcar Whisper de qualquer jeito
    (`coletar(..., forcar_whisper=True)`), o que economiza requisicoes ao
    YouTube e evita o proximo paragrafo por completo.

    `navegador_cookies`: nome do navegador de onde extrair cookies de uma
    sessao logada (padrao "chrome"; None desliga). Descoberto em producao
    (2026-08-18): apos algumas dezenas de downloads anonimos no mesmo dia,
    o YouTube passou a devolver HTTP 403 em QUALQUER video, nao so' os que
    a sessao ja tinha tocado — bloqueio por volume de trafego anonimo, nao
    por video especifico. Autenticar com cookies de um navegador local
    logado de verdade (`--cookies-from-browser`, recurso padrao e
    documentado do yt-dlp) resolveu na hora: o YouTube trata sessao
    autenticada com muito mais tolerancia. Isso NAO e' burlar protecao —
    e' usar a propria conta logada do usuario, o oposto de se disfarcar.
    Exige um Chrome instalado nesta maquina com sessao ja logada no
    Google/YouTube; sem isso, ou em ambiente sem navegador (CI, servidor),
    passe `navegador_cookies=None`.

    O video em si e' sempre mais importante que legenda ou qualidade
    maxima: duas falhas transitorias reais de producao motivaram uma
    cadeia de fallback (2026-08-17):
      1. Legenda rate-limitada pelo YouTube (HTTP 429) derrubava a coleta
         inteira mesmo com o video ja baixado — corrigido tentando de
         novo sem pedir legenda.
      2. O formato preferido (video+audio separados, ate 1080p, exige
         merge) as vezes recebe HTTP 403 num stream especifico, enquanto
         um formato mais simples (`best`, unico stream, resolucao menor)
         funciona no mesmo instante — corrigido caindo pra esse formato
         de reserva. Resolucao nao importa para transcricao; a midia
         completa como prova de custodia sim, e essa ela preserva.
    As duas causas podem se combinar na mesma chamada (legenda falha,
    tenta sem legenda, MESMO formato falha de novo, ai' cai pro formato
    de reserva) — a cadeia abaixo cobre isso. `navegador_cookies` e'
    ortogonal a essa cadeia: se aplica em toda tentativa, pois e' a defesa
    contra a causa mais provavel de bloqueio (volume, nao formato/legenda).
    """
    try:
        import yt_dlp
    except ImportError as e:
        raise ColetaIndisponivel(
            "yt-dlp nao instalado (pip install yt-dlp)"
        ) from e

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)

    opcoes_base: dict[str, Any] = {
        "outtmpl": str(destino / "%(id)s.%(ext)s"),
        "format": FORMATO_PADRAO,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    if navegador_cookies:
        opcoes_base["cookiesfrombrowser"] = (navegador_cookies,)
        opcoes_base["remote_components"] = ["ejs:github"]
    opcoes_legenda = {
        **opcoes_base,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": list(idiomas),
        "subtitlesformat": "vtt",
    }
    opcoes_reserva = {**opcoes_base, "format": FORMATO_RESERVA}

    tentativas: list[tuple[dict, Any]] = []
    if baixar_legenda:
        tentativas.append((opcoes_legenda, _falha_de_legenda_ou_formato))
    tentativas.append((opcoes_base, _falha_de_formato))
    tentativas.append((opcoes_reserva, None))

    info = None
    for i, (opcoes, erro_recuperavel) in enumerate(tentativas):
        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                info = ydl.extract_info(url, download=True)
            break
        except yt_dlp.utils.DownloadError as e:
            ultima_tentativa = i == len(tentativas) - 1
            if ultima_tentativa or erro_recuperavel is None or not erro_recuperavel(e):
                raise

    coletado_em = proveniencia.agora_utc()

    video_id = info["id"]
    arquivo = destino / f"{video_id}.{info.get('ext', 'mp4')}"
    if not arquivo.exists():
        candidatos = [
            p for p in destino.glob(f"{video_id}.*")
            if p.suffix not in (".vtt", ".part")
        ]
        if not candidatos:
            raise ColetaIndisponivel(
                f"download concluido mas arquivo de midia nao encontrado "
                f"para {video_id} em {destino}"
            )
        arquivo = candidatos[0]

    legenda = None
    legenda_tipo = None
    legenda_idioma = None
    escolha = _escolher_legenda(info, idiomas)
    if escolha:
        legenda_idioma, legenda_tipo = escolha
        candidato = destino / f"{video_id}.{legenda_idioma}.vtt"
        if candidato.exists():
            legenda = candidato

    return {
        "arquivo": arquivo,
        "legenda": legenda,
        "legenda_tipo": legenda_tipo,
        "legenda_idioma": legenda_idioma,
        "video_id": video_id,
        "titulo": info.get("title"),
        "canal": info.get("uploader") or info.get("channel"),
        "url": info.get("webpage_url", url),
        "publicado_em": _data_para_iso(info.get("upload_date")),
        "coletado_em": coletado_em,
    }


def _processar_com_legenda(info: dict[str, Any], saida: Path) -> Transcricao:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    base = info["arquivo"].stem

    manifesto = proveniencia.manifesto(
        info["arquivo"],
        fonte="youtube",
        url=info["url"],
        perfil=info["canal"],
        publicado_em=info["publicado_em"],
        coletado_em=info["coletado_em"],
        extras={
            "legenda": {
                "tipo": info["legenda_tipo"],
                "idioma": info["legenda_idioma"],
            }
        },
    )

    # audio para o player de site_revisao.py (regra 2: humano precisa poder ouvir)
    caminho_wav = saida / f"{base}.wav"
    manifesto["audio"] = proveniencia.extrair_audio(info["arquivo"], caminho_wav)

    conteudo = info["legenda"].read_text(encoding="utf-8")
    segmentos = legendas.montar_segmentos(conteudo)

    t = Transcricao(
        proveniencia=manifesto,
        idioma=info["legenda_idioma"] or "pt",
        duracao=segmentos[-1].fim if segmentos else 0.0,
        segmentos=segmentos,
        falantes=[],
        diarizacao_disponivel=False,
        avisos=[
            f"transcricao vinda de legenda do youtube "
            f"({info['legenda_tipo']}), sem diarizacao — revisao obrigatoria"
        ],
    )

    proveniencia.salvar_json(t.para_dict(), saida / f"{base}.transcricao.json")
    proveniencia.salvar_json(
        pipeline.fila_de_verificacao(t), saida / f"{base}.fila_revisao.json"
    )
    return t


def coletar(
    url: str,
    saida: Path,
    *,
    pasta_download: Path | None = None,
    idiomas: tuple[str, ...] = IDIOMAS_PADRAO,
    forcar_whisper: bool = False,
    nome_modelo: str = MODELO_PADRAO,
    modelo=None,
    usar_diarizacao: bool = True,
    max_falantes: int | None = None,
    mapa_falantes: dict[str, str] | None = None,
    navegador_cookies: str | None = NAVEGADOR_COOKIES_PADRAO,
) -> Transcricao:
    """Baixa do YouTube e transcreve: legenda se houver, Whisper senao.

    `forcar_whisper=True` ignora legenda disponivel e roda a pipeline normal
    (com diarizacao) mesmo assim — util quando a legenda existe mas e'
    ruim demais para servir de base.

    `navegador_cookies`: ver docstring de `baixar()`. Padrao usa cookies do
    Chrome local (autenticado) para evitar bloqueio por volume de trafego
    anonimo; passe None em ambiente sem navegador (CI, servidor).
    """
    saida = Path(saida)
    pasta_download = Path(pasta_download) if pasta_download else saida / "originais"

    info = baixar(
        url,
        pasta_download,
        idiomas=idiomas,
        baixar_legenda=not forcar_whisper,
        navegador_cookies=navegador_cookies,
    )

    if info["legenda"] and not forcar_whisper:
        return _processar_com_legenda(info, saida)

    return pipeline.processar(
        info["arquivo"],
        fonte="youtube",
        saida=saida,
        url=info["url"],
        perfil=info["canal"],
        publicado_em=info["publicado_em"],
        coletado_em=info["coletado_em"],
        nome_modelo=nome_modelo,
        modelo=modelo,
        usar_diarizacao=usar_diarizacao,
        max_falantes=max_falantes,
        mapa_falantes=mapa_falantes,
    )
