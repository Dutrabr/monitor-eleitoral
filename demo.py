#!/usr/bin/env python3
"""Demonstracao sem baixar modelo de ML.

Roda a pipeline inteira com um transcritor falso, para voce ver o formato de
saida e as regras de qualidade funcionando antes de puxar o large-v3.

    python3 demo.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from test_pipeline import ModeloFalso, ModeloRuidoso  # noqa: E402
from transcricao import diarizar as mod_diarizar  # noqa: E402
from transcricao import pipeline, qualidade  # noqa: E402
from transcricao.modelos import Turno  # noqa: E402


def audio_sintetico(destino: Path, segundos: int = 6) -> Path:
    subprocess.run(
        [
            "ffmpeg", "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={segundos}",
            "-ac", "1", "-ar", "16000", "-y", str(destino), "-loglevel", "error",
        ],
        check=True,
    )
    return destino


def cenario(titulo, modelo, turnos, tmp):
    print("=" * 72)
    print(titulo)
    print("=" * 72)

    mod_diarizar.diarizar = lambda *a, **k: turnos  # duble
    origem = audio_sintetico(tmp / "entrevista.wav")

    t = pipeline.processar(
        origem,
        fonte="debate",
        saida=tmp / "saida",
        url="https://exemplo.com/video/123",
        perfil="@canal_oficial",
        coletado_em="2026-07-29T21:00:00+00:00",
        modelo=modelo,
    )

    print(f"\nfalantes detectados : {t.falantes}")
    print(f"multi falante       : {t.multi_falante}")
    print(f"revisao obrigatoria : {t.exige_revisao_humana}")
    print(f"resumo              : {qualidade.resumo(t.segmentos)}")
    print(f"hash do original    : {t.proveniencia['hash_sha256_original'][:24]}...")

    print("\nsegmentos:")
    for s in t.segmentos:
        print(f"  [{s.status.value:11}] {s.falante or '???':14} "
              f"{s.inicio:5.1f}-{s.fim:5.1f}  {s.texto[:52]}")
        for m in s.motivos:
            print(f"                {'':14} -> {m}")

    fila = pipeline.fila_de_verificacao(t)
    print(f"\nfila de revisao ({len(fila['itens'])} itens, descartados fora):")
    print(json.dumps(fila["itens"][:2], ensure_ascii=False, indent=2)[:700])
    print()


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cenario(
            "CENARIO 1 — entrevista com 2 falantes (candidato + entrevistador)",
            ModeloFalso(),
            [Turno(0.0, 3.0, "SPEAKER_00"), Turno(3.0, 6.0, "SPEAKER_01")],
            tmp,
        )
        cenario(
            "CENARIO 2 — falante unico, com alucinacao do Whisper em silencio",
            ModeloRuidoso(),
            [Turno(0.0, 6.0, "SPEAKER_00")],
            tmp,
        )


if __name__ == "__main__":
    main()
