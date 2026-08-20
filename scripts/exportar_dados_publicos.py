"""Exporta so' o subconjunto de `dados/` que o site publico precisa, pra
`dados_publicos/` — a UNICA pasta de dados que vai pro deploy (git).

`dados/` inteiro fica de fora do git de proposito (contem midia original,
decisoes de revisao, fila de verificacao — proveniencia interna, nao
destinada a redistribuicao publica). O site publico so' precisa de,
pra Presidente:

  - dados/candidatos/*.json          -> dados_publicos/candidatos/
  - dados/planos_de_governo/*.pdf    -> dados_publicos/planos_de_governo/
  - dados/planos_curados/*.json      -> dados_publicos/planos_curados/
  - dados/transcricoes/*.publicado.json -> dados_publicos/transcricoes/

e pra Governador (mesmo espirito, pastas por UF preservadas porque
`site_publico.governador_plano_de_governo` espera `{uf}/{slug}.pdf`):

  - dados/candidatos_governador/{uf}/*.json       -> dados_publicos/candidatos_governador/{uf}/
  - dados/planos_de_governo_governador/{uf}/*.pdf -> dados_publicos/planos_de_governo_governador/{uf}/
  - dados/planos_curados_governador/*.json        -> dados_publicos/planos_curados_governador/

Nao copia .wav, .mp4, .decisoes.json, .fila_revisao.json nem MANIFESTO.json
— isso e' prova de custodia interna, nunca foi feito pra sair da maquina
de quem revisa.

Idempotente: roda de novo sempre que publicar algo novo (nova citacao, novo
tema curado, novo candidato) antes de commitar/dar push pro deploy.

    python3 scripts/exportar_dados_publicos.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "dados"
DESTINO = RAIZ / "dados_publicos"


def _limpar_e_copiar(pastas: list[str]) -> None:
    for nome in pastas:
        alvo = DESTINO / nome
        if alvo.exists():
            shutil.rmtree(alvo)
        alvo.mkdir(parents=True)


def _copiar_por_uf(origem: Path, destino: Path, extensao: str) -> int:
    """Copia `origem/{uf}/*.extensao` pra `destino/{uf}/`, preservando UF."""
    n = 0
    if not origem.exists():
        return n
    for pasta_uf in sorted(origem.iterdir()):
        if not pasta_uf.is_dir():
            continue
        alvo_uf = destino / pasta_uf.name
        alvo_uf.mkdir(parents=True, exist_ok=True)
        for f in pasta_uf.glob(f"*.{extensao}"):
            shutil.copy2(f, alvo_uf / f.name)
            n += 1
    return n


def main() -> int:
    _limpar_e_copiar([
        "candidatos", "planos_de_governo", "planos_curados", "transcricoes",
        "candidatos_governador", "planos_de_governo_governador", "planos_curados_governador",
    ])

    n_candidatos = 0
    for f in (ORIGEM / "candidatos").glob("*.json"):
        shutil.copy2(f, DESTINO / "candidatos" / f.name)
        n_candidatos += 1

    n_planos = 0
    for f in (ORIGEM / "planos_de_governo").glob("*.pdf"):
        shutil.copy2(f, DESTINO / "planos_de_governo" / f.name)
        n_planos += 1

    n_curados = 0
    if (ORIGEM / "planos_curados").exists():
        for f in (ORIGEM / "planos_curados").glob("*.json"):
            shutil.copy2(f, DESTINO / "planos_curados" / f.name)
            n_curados += 1

    n_publicados = 0
    for f in (ORIGEM / "transcricoes").rglob("*.publicado.json"):
        shutil.copy2(f, DESTINO / "transcricoes" / f.name)
        n_publicados += 1

    n_candidatos_gov = _copiar_por_uf(
        ORIGEM / "candidatos_governador", DESTINO / "candidatos_governador", "json"
    )
    n_planos_gov = _copiar_por_uf(
        ORIGEM / "planos_de_governo_governador", DESTINO / "planos_de_governo_governador", "pdf"
    )
    n_curados_gov = 0
    if (ORIGEM / "planos_curados_governador").exists():
        for f in (ORIGEM / "planos_curados_governador").glob("*.json"):
            shutil.copy2(f, DESTINO / "planos_curados_governador" / f.name)
            n_curados_gov += 1

    print(f"candidatos (Presidente): {n_candidatos}")
    print(f"planos de governo (PDF, Presidente): {n_planos}")
    print(f"planos curados (Presidente): {n_curados}")
    print(f"citacoes publicadas: {n_publicados}")
    print(f"candidatos (Governador): {n_candidatos_gov}")
    print(f"planos de governo (PDF, Governador): {n_planos_gov}")
    print(f"planos curados (Governador): {n_curados_gov}")
    print(f"\nexportado pra {DESTINO} — revise o 'git status' antes de commitar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
