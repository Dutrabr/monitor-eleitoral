"""Registro de candidatos e agregacao de citacoes publicadas por tema.

O site publico (`site_publico.py`) le esse registro + os arquivos
`NOME.publicado.json` espalhados em `dados/transcricoes/` e monta a pagina
de cada candidato. Nao ha nenhum cruzamento automatico entre o que o
plano de governo diz e o que a citacao diz, nem pontuacao de aderencia —
o projeto mostra evidencia lado a lado, a leitura e' de quem le (regra 1
do CLAUDE.md).

Formato de um registro de candidato (um arquivo JSON por candidato):
{
  "slug": "fulano-de-tal",
  "nome": "Fulano de Tal",
  "partido": "PARTIDO X",
  "cargo": "Presidente",
  "falante_id": "candidato_fulano",
  "plano_de_governo": "caminho/ou/url/para/o/pdf"
}

`falante_id` precisa bater com o `Segmento.falante` depois de
`atribuir.renomear_falantes` (ver `--mapa-falantes` no README) — e' assim
que uma citacao publicada e' associada a uma pessoa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEMA_SEM_CLASSIFICACAO = "sem_tema_definido"


def carregar_candidatos(pasta: Path) -> list[dict[str, Any]]:
    """Le todos os registros de candidato numa pasta, ordenados por nome.

    Ordem alfabetica de proposito — nenhuma outra ordenacao (regra 3:
    simetria total entre candidatos, nunca uma lista que sugira hierarquia).
    """
    candidatos = [
        json.loads(caminho.read_text(encoding="utf-8"))
        for caminho in sorted(Path(pasta).glob("*.json"))
    ]
    return sorted(candidatos, key=lambda c: c["nome"])


def citacoes_do_candidato(
    falante_id: str, arquivos_publicados: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Filtra, entre varios .publicado.json ja carregados, as citacoes de um falante."""
    citacoes = []
    for publicado in arquivos_publicados:
        for c in publicado.get("citacoes", []):
            if c.get("falante") == falante_id:
                citacoes.append({**c, "url_origem": publicado.get("url")})
    return citacoes


def agrupar_por_tema(
    citacoes: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa citacoes por tema. Uma citacao com N temas aparece em N grupos.

    Citacao sem tema marcado entra em `TEMA_SEM_CLASSIFICACAO` de forma
    explicita — nunca fica invisivel so' porque ninguem marcou um tema.
    """
    grupos: dict[str, list[dict[str, Any]]] = {}
    for c in citacoes:
        temas = c.get("temas") or [TEMA_SEM_CLASSIFICACAO]
        for tema in temas:
            grupos.setdefault(tema, []).append(c)
    return grupos


def url_com_timestamp(url: str | None, inicio: float) -> str | None:
    """Adiciona parametro de tempo a URL, quando o formato e' conhecido.

    So' YouTube tem parametro de tempo documentado publicamente
    (`?t=SEGUNDOSs`). Para outras fontes (Instagram, etc.), devolve a URL
    sem alteracao — nao inventamos um parametro que a plataforma nao
    suporta de verdade.
    """
    if not url:
        return url
    if "youtube.com" in url or "youtu.be" in url:
        separador = "&" if "?" in url else "?"
        return f"{url}{separador}t={int(inicio)}s"
    return url
