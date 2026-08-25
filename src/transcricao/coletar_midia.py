"""Coletor generico: YouTube, Instagram, TikTok e Facebook pelo mesmo caminho.

Motivo (2026-08-25): dos 141 candidatos a Governador que ainda faltam
coletar, so' 57 tem YouTube cadastrado no TSE — 79 tem SO' Instagram e 5
so' TikTok/Facebook. Ficar so' no YouTube deixaria 60% do alcance
possivel de fora.

O download continua sendo `coletar_youtube.baixar`, que ja' e' yt-dlp
puro e nunca foi especifico do YouTube: a mesma chamada resolve
tiktok, facebook, facebook:reel e instagram. O que muda aqui e' so'
descobrir a plataforma pela URL e registra-la em `fonte` na proveniencia.

**Kwai nao e' suportado** — nao existe extractor no yt-dlp. Candidato que
so' tem Kwai fica sem coleta, e isso e' fato registrado, nao falha
silenciosa: `detectar_plataforma` levanta erro em vez de adivinhar.

Sobre o Instagram: continua existindo `coletar_instagram.py`, que usa
instaloader. Os dois baixam direto do CDN da Meta (nenhum e' ripper de
terceiro, ver "Fora de escopo" no CLAUDE.md), entao a cadeia de custodia
vale igual. O caminho do yt-dlp existe porque `instaloader.Profile.
from_username` quebrou com erro de schema da propria Meta em 2026-08-22 e
disparou rate-limit na conta pessoal do dono; ter dois caminhos e'
resiliencia, nao duplicacao.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import deduplicar
from .coletar_youtube import NAVEGADOR_COOKIES_PADRAO
from .coletar_youtube import coletar as _coletar_via_ytdlp
from .modelos import Transcricao
from .transcrever import MODELO_PADRAO

# Ordem importa: "youtu.be" antes de qualquer regra mais larga.
PLATAFORMAS: tuple[tuple[str, str], ...] = (
    ("youtube.com", "youtube"),
    ("youtu.be", "youtube"),
    ("instagram.com", "instagram"),
    ("tiktok.com", "tiktok"),
    ("facebook.com", "facebook"),
    ("fb.watch", "facebook"),
)

SEM_SUPORTE: tuple[tuple[str, str], ...] = (
    ("kwai.com", "Kwai"),
    ("kwai-video.com", "Kwai"),
)


class PlataformaNaoSuportada(ValueError):
    pass


def detectar_plataforma(url: str) -> str:
    """Nome da plataforma a partir da URL, para registrar em `fonte`.

    Levanta `PlataformaNaoSuportada` em vez de cair num padrao generico:
    gravar fonte errada na proveniencia e' pior que falhar na hora.
    """
    u = (url or "").lower()
    for dominio, nome in SEM_SUPORTE:
        if dominio in u:
            raise PlataformaNaoSuportada(
                f"{nome} nao tem extractor no yt-dlp; nao ha' como coletar {url}"
            )
    for dominio, nome in PLATAFORMAS:
        if dominio in u:
            return nome
    raise PlataformaNaoSuportada(f"plataforma nao reconhecida na URL: {url}")


def textos_ja_coletados(pasta: Path) -> dict[str, str]:
    """{nome_do_video: texto transcrito} do que ja' existe em disco.

    Usado para detectar peca repetida entre plataformas antes de somar
    a mesma fala duas vezes na pagina do candidato.
    """
    import json

    pasta = Path(pasta)
    textos: dict[str, str] = {}
    for arquivo in sorted(pasta.glob("*.fila_revisao.json")):
        try:
            fila = json.loads(arquivo.read_text())
        except (OSError, ValueError):
            continue
        textos[arquivo.name.replace(".fila_revisao.json", "")] = " ".join(
            item.get("texto", "") for item in fila.get("itens", [])
        )
    return textos


def coletar(
    url: str,
    saida: Path,
    *,
    pasta_download: Path | None = None,
    forcar_whisper: bool = False,
    nome_modelo: str = MODELO_PADRAO,
    modelo: Any = None,
    usar_diarizacao: bool = True,
    max_falantes: int | None = None,
    mapa_falantes: dict[str, str] | None = None,
    navegador_cookies: str | None = NAVEGADOR_COOKIES_PADRAO,
) -> Transcricao:
    """Baixa e transcreve de qualquer plataforma suportada."""
    return _coletar_via_ytdlp(
        url,
        saida,
        pasta_download=pasta_download,
        forcar_whisper=forcar_whisper,
        nome_modelo=nome_modelo,
        modelo=modelo,
        usar_diarizacao=usar_diarizacao,
        max_falantes=max_falantes,
        mapa_falantes=mapa_falantes,
        navegador_cookies=navegador_cookies,
        fonte=detectar_plataforma(url),
    )


def checar_repetido(transcricao: Transcricao, pasta: Path) -> tuple[str, float] | None:
    """A transcricao recem-feita repete um video ja' coletado?

    Devolve `(nome_do_video_existente, similaridade)` ou None. Nao apaga
    nem esconde nada — quem chama decide, e o resultado tem que aparecer
    no log (ver docstring de `deduplicar`).
    """
    texto = " ".join(s.texto for s in transcricao.segmentos)
    return deduplicar.encontrar_repetido(texto, textos_ja_coletados(pasta))
