"""Busca trechos candidatos num plano de governo por palavra-chave de tema.

Ferramenta de APOIO a curadoria manual (dados/planos_curados/) — nunca
decide sozinha se um tema "consta" no plano. So' acha candidatos a trecho
pra um humano ler e confirmar, mesmo padrao de Whisper achar fala em
escala pra a revisao humana confirmar depois (ver `revisao.py`).

Uso:
    python3 scripts/buscar_trecho_plano.py <slug> <palavra-chave> [mais...]
    python3 scripts/buscar_trecho_plano.py zema saude sus "atencao primaria"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_PLANOS = RAIZ / "dados" / "planos_de_governo"


def extrair_paginas(caminho_pdf: Path) -> list[str]:
    resultado = subprocess.run(
        ["pdftotext", "-layout", str(caminho_pdf), "-"],
        capture_output=True, text=True, check=True,
    )
    return resultado.stdout.split("\f")


def buscar(slug: str, palavras: list[str]) -> None:
    caminho = PASTA_PLANOS / f"{slug}.pdf"
    if not caminho.exists():
        print(f"plano de governo de '{slug}' nao encontrado em {caminho}")
        return

    paginas = extrair_paginas(caminho)
    termos = [p.lower() for p in palavras]
    encontrou = False
    for i, pagina in enumerate(paginas, start=1):
        if any(t in pagina.lower() for t in termos):
            encontrou = True
            print(f"\n=== {slug} — pagina {i} ===")
            print(pagina.strip()[:1200])
    if not encontrou:
        print(f"{slug}: nenhuma pagina bateu com {palavras}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    buscar(sys.argv[1], sys.argv[2:])
