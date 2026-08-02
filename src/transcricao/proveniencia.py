"""Cadeia de custodia do material coletado.

O ativo defensavel do projeto nao e' a transcricao, e' o arquivo original com
hash e horario de coleta. A transcricao e' derivada e refazivel; o original,
se o candidato apagar o post, e' irrecuperavel.

Regra: hasheie o arquivo COMO BAIXADO, antes de qualquer conversao. O hash do
WAV convertido nao prova nada sobre a origem.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TAXA_AMOSTRAGEM = 16_000  # Whisper opera em 16 kHz mono


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_arquivo(caminho: Path, algoritmo: str = "sha256") -> str:
    h = hashlib.new(algoritmo)
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def ffmpeg_disponivel() -> bool:
    return shutil.which("ffmpeg") is not None


def _versao_ffmpeg() -> str:
    try:
        saida = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return saida.stdout.splitlines()[0] if saida.stdout else "desconhecida"
    except Exception:
        return "desconhecida"


def extrair_audio(origem: Path, destino: Path) -> dict[str, Any]:
    """Extrai audio mono 16 kHz PCM para transcricao.

    Retorna o registro do que foi feito, para entrar no manifesto. O comando
    exato fica gravado: e' isso que permite a um terceiro reproduzir o passo.
    """
    if not ffmpeg_disponivel():
        raise RuntimeError(
            "ffmpeg nao encontrado. Instale com: brew install ffmpeg"
        )

    destino.parent.mkdir(parents=True, exist_ok=True)
    comando = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i", str(origem),
        "-vn",
        "-ac", "1",
        "-ar", str(TAXA_AMOSTRAGEM),
        "-acodec", "pcm_s16le",
        str(destino),
    ]
    proc = subprocess.run(comando, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not destino.exists():
        raise RuntimeError(
            f"falha ao extrair audio de {origem.name}: "
            f"{proc.stderr[-600:] if proc.stderr else 'erro desconhecido'}"
        )

    return {
        "comando": " ".join(comando),
        "ffmpeg": _versao_ffmpeg(),
        "taxa_amostragem": TAXA_AMOSTRAGEM,
        "canais": 1,
        "codec": "pcm_s16le",
        "hash_audio_extraido": hash_arquivo(destino),
        "extraido_em": agora_utc(),
    }


def manifesto(
    origem: Path,
    *,
    fonte: str,
    url: str | None = None,
    perfil: str | None = None,
    publicado_em: str | None = None,
    coletado_em: str | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta o registro de proveniencia do arquivo original.

    `coletado_em` deve ser o horario em que o COLETOR viu o conteudo, nao a
    hora da transcricao. Se voce nao passou isso desde a coleta, o campo perde
    valor probatorio: registre no coletor, nao aqui.
    """
    origem = Path(origem)
    reg: dict[str, Any] = {
        "arquivo": origem.name,
        "bytes": origem.stat().st_size,
        "hash_sha256_original": hash_arquivo(origem),
        "fonte": fonte,
        "url": url,
        "perfil": perfil,
        "publicado_em_utc": publicado_em,
        "coletado_em_utc": coletado_em,
        "manifesto_gerado_em_utc": agora_utc(),
        "ambiente": {
            "python": sys.version.split()[0],
            "sistema": f"{platform.system()} {platform.release()}",
        },
    }
    if extras:
        reg.update(extras)
    return reg


def salvar_json(dados: dict[str, Any], destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return destino


def verificar_integridade(caminho: Path, hash_esperado: str) -> bool:
    """Reconferencia. Rode isso antes de usar qualquer trecho como citacao."""
    return hash_arquivo(Path(caminho)) == hash_esperado
