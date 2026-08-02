"""Coletor do Instagram: Reels, direto do CDN via instaloader.

Fora de escopo por decisao (ver CLAUDE.md):
  - Stories: efemero de 24h, alta friccao, conteudo pobre para promessa
    programatica.
  - fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia
    (o hash passa a ser do terceiro, nao do original) e re-encoda o audio,
    piorando a transcricao.

instaloader baixa o video direto do CDN da Meta com a propria sessao HTTP —
sem intermediario. Nao ha trilha de legenda separada para Reels como no
YouTube: `accessibility_caption` do Instagram e' descricao de imagem gerada
por IA para acessibilidade, nao transcricao de fala, e por isso nunca e'
usado aqui. Todo Reel coletado passa pela pipeline normal (Whisper +
diarizacao).

Autenticacao e' opcional mas recomendada: sem sessao logada, o Instagram
frequentemente bloqueia ou limita acesso a posts publicos. Gere uma sessao
uma vez com `instaloader --login SEU_USUARIO` e aponte
INSTAGRAM_USUARIO / INSTAGRAM_SESSAO (ver `_sessao`).
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from . import pipeline, proveniencia
from .modelos import Transcricao
from .transcrever import MODELO_PADRAO

_PADRAO_REEL = re.compile(r"instagram\.com/reels?/([A-Za-z0-9_-]+)")


class ColetaIndisponivel(RuntimeError):
    pass


def extrair_shortcode(url: str) -> str:
    """Extrai o shortcode de uma URL de Reel.

    Levanta erro para qualquer outra coisa — post comum (/p/), story,
    perfil ou IGTV. So Reel esta no escopo do projeto.
    """
    m = _PADRAO_REEL.search(url)
    if not m:
        raise ColetaIndisponivel(
            f"URL nao e' um Reel do Instagram (precisa ter /reel/ ou "
            f"/reels/): {url}. Posts comuns e stories estao fora do "
            "escopo por decisao (ver CLAUDE.md)."
        )
    return m.group(1)


def _iso_utc(dt: datetime) -> str:
    """`post.date_utc` do instaloader e' naive mas ja em UTC — so' rotula."""
    if dt.tzinfo is None:
        return dt.isoformat() + "+00:00"
    return dt.isoformat()


def _sessao(L) -> None:
    """Carrega sessao logada, se configurada via variaveis de ambiente.

    Sem isso, instaloader tenta acesso anonimo, que o Instagram costuma
    bloquear ou limitar mesmo para conteudo publico.
    """
    usuario = os.environ.get("INSTAGRAM_USUARIO")
    if not usuario:
        return
    arquivo_sessao = os.environ.get("INSTAGRAM_SESSAO")
    try:
        L.load_session_from_file(usuario, filename=arquivo_sessao)
    except FileNotFoundError as e:
        raise ColetaIndisponivel(
            f"sessao de '{usuario}' nao encontrada. Gere uma vez com: "
            f"instaloader --login {usuario}"
        ) from e


def baixar(url: str, destino: Path) -> dict[str, Any]:
    """Baixa o Reel e devolve metadados de proveniencia.

    `coletado_em` e' registrado logo apos o download terminar — e' o
    momento em que o COLETOR viu o conteudo.
    """
    try:
        import instaloader
    except ImportError as e:
        raise ColetaIndisponivel(
            "instaloader nao instalado (pip install instaloader)"
        ) from e

    shortcode = extrair_shortcode(url)
    destino = Path(destino) / shortcode
    destino.mkdir(parents=True, exist_ok=True)

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )
    _sessao(L)

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        if not post.is_video:
            raise ColetaIndisponivel(
                f"{url} nao e' um video (Reel sem video nao deveria existir)"
            )
        L.download_post(post, target=destino)
    except ColetaIndisponivel:
        raise
    except Exception as e:  # noqa: BLE001 — instaloader tem varias excecoes proprias
        raise ColetaIndisponivel(
            f"falha ao baixar {url}: {e}. Se o Instagram estiver bloqueando "
            "acesso anonimo, configure INSTAGRAM_USUARIO/INSTAGRAM_SESSAO."
        ) from e

    coletado_em = proveniencia.agora_utc()

    arquivos = list(destino.rglob("*.mp4"))
    if len(arquivos) != 1:
        raise ColetaIndisponivel(
            f"esperava exatamente 1 video baixado em {destino}, achei "
            f"{len(arquivos)}"
        )
    arquivo = arquivos[0]

    return {
        "arquivo": arquivo,
        "shortcode": shortcode,
        "canal": f"@{post.owner_username}",
        "url": f"https://www.instagram.com/reel/{shortcode}/",
        "publicado_em": _iso_utc(post.date_utc),
        "coletado_em": coletado_em,
        "video_duracao_s": getattr(post, "video_duration", None),
    }


def coletar(
    url: str,
    saida: Path,
    *,
    pasta_download: Path | None = None,
    nome_modelo: str = MODELO_PADRAO,
    modelo=None,
    usar_diarizacao: bool = True,
    max_falantes: int | None = None,
    mapa_falantes: dict[str, str] | None = None,
) -> Transcricao:
    """Baixa um Reel do Instagram e transcreve pela pipeline normal.

    Sem trilha de legenda separada aqui: sempre Whisper + diarizacao.
    """
    saida = Path(saida)
    pasta_download = Path(pasta_download) if pasta_download else saida / "originais"

    info = baixar(url, pasta_download)

    return pipeline.processar(
        info["arquivo"],
        fonte="instagram",
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
