#!/usr/bin/env python3
"""Busca os candidatos a Presidente 2026 no DivulgaCandContas e atualiza
`dados/candidatos/*.json` + baixa os PDFs de plano de governo em
`dados/planos_de_governo/`.

Idempotente: roda de novo a qualquer momento ate' 15/08/2026 (fim do
registro de candidatura) para pegar candidatos que entraram depois.
Sobrescreve os registros existentes; nao apaga candidatos que sairem da
lista (registro cancelado, etc.) — isso exige revisao humana, nao remocao
automatica.

    python3 scripts/atualizar_candidatos_presidente.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao import proveniencia  # noqa: E402
from transcricao.plano_de_governo import (  # noqa: E402
    baixar_proposta,
    buscar_candidato,
)

RAIZ = Path(__file__).resolve().parents[1]
PASTA_CANDIDATOS = RAIZ / "dados" / "candidatos"
PASTA_PLANOS = RAIZ / "dados" / "planos_de_governo"

ANO = 2026
MUNICIPIO_NACIONAL = "BR"
CODIGO_ELEICAO_2026 = "20322002026"
CARGO_PRESIDENTE = 1


def _slugificar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _listar_ids_presidente() -> list[int]:
    import requests

    from transcricao.plano_de_governo import BASE_API, REFERER

    url = (
        f"{BASE_API}/candidatura/listar/{ANO}/{MUNICIPIO_NACIONAL}/"
        f"{CODIGO_ELEICAO_2026}/{CARGO_PRESIDENTE}/candidatos"
    )
    resp = requests.get(url, headers={"Referer": REFERER}, timeout=30)
    resp.raise_for_status()
    return [c["id"] for c in resp.json().get("candidatos", [])]


def main() -> int:
    PASTA_CANDIDATOS.mkdir(parents=True, exist_ok=True)
    PASTA_PLANOS.mkdir(parents=True, exist_ok=True)

    ids = _listar_ids_presidente()
    print(f"{len(ids)} candidato(s) a Presidente encontrado(s) no DivulgaCandContas.")

    manifesto: list[dict] = []
    for cid in ids:
        candidato = buscar_candidato(ANO, MUNICIPIO_NACIONAL, CODIGO_ELEICAO_2026, cid)
        nome_urna = candidato["nomeUrna"]
        slug = _slugificar(nome_urna)
        falante_id = f"candidato_{slug.replace('-', '_')}"

        destino_pdf = PASTA_PLANOS / f"{slug}.pdf"
        caminho = baixar_proposta(candidato, destino_pdf)

        hash_pdf = proveniencia.hash_arquivo(caminho) if caminho else None
        tamanho = caminho.stat().st_size if caminho else None

        vices = candidato.get("vices") or []
        vice_nomes = [v.get("nm_URNA") for v in vices]

        registro = {
            "slug": slug,
            "nome": nome_urna,
            "nome_completo": candidato.get("nomeCompleto"),
            "partido": candidato["partido"]["sigla"],
            "numero": candidato.get("numero"),
            "cargo": "Presidente",
            "vice": ", ".join(vice_nomes) if vice_nomes else None,
            "falante_id": falante_id,
            "plano_de_governo": f"/plano/{slug}" if caminho else None,
            "fonte_dados": {
                "api": "divulgacandcontas.tse.jus.br",
                "candidato_id_tse": cid,
                "eleicao_id_tse": CODIGO_ELEICAO_2026,
                "coletado_em": proveniencia.agora_utc(),
            },
        }
        (PASTA_CANDIDATOS / f"{slug}.json").write_text(
            json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        manifesto.append(
            {
                "slug": slug,
                "nome": nome_urna,
                "arquivo_pdf": f"dados/planos_de_governo/{slug}.pdf" if caminho else None,
                "hash_sha256_pdf": hash_pdf,
                "bytes": tamanho,
            }
        )
        print(f"  {nome_urna:30} slug={slug:30} {'ok' if caminho else 'SEM PLANO DE GOVERNO'}")

    (PASTA_PLANOS / "MANIFESTO.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n{len(manifesto)} candidato(s) processado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
