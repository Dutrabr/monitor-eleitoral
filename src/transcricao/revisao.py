"""Fluxo de revisao humana: fila -> decisao -> publicacao.

Puro — sem I/O. Nenhuma decisao e' automatica: cada item citavel da fila
(`pipeline.fila_de_verificacao`, que ja exclui os DESCARTADOS) precisa de um
CONFIRMADO ou REJEITADO explicito antes de poder entrar em publicacao.
Rejeitar nao apaga nada — so' marca que aquele trecho nao vai ao ar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Decisao(str, Enum):
    CONFIRMADO = "confirmado"
    REJEITADO = "rejeitado"


def registrar_decisao(
    decisoes: dict[str, Any],
    indice: int,
    decisao: Decisao,
    *,
    texto_final: str | None = None,
    revisado_por: str | None = None,
    revisado_em: str | None = None,
) -> dict[str, Any]:
    """Devolve uma NOVA copia de `decisoes` com a decisao aplicada.

    Nao muta o dict recebido. Nao acessa relogio por conta propria: quem
    chama passa `revisado_em`, o que mantem a funcao testavel sem mock de
    tempo e deixa explicito de onde vem o timestamp de auditoria.
    """
    novas = dict(decisoes)
    entrada: dict[str, Any] = {"decisao": decisao.value}
    if decisao is Decisao.CONFIRMADO:
        entrada["texto_final"] = texto_final
    if revisado_por:
        entrada["revisado_por"] = revisado_por
    if revisado_em:
        entrada["revisado_em"] = revisado_em
    novas[str(indice)] = entrada
    return novas


def resumo(fila: dict[str, Any], decisoes: dict[str, Any]) -> dict[str, int]:
    total = len(fila.get("itens", []))
    confirmados = sum(
        1 for d in decisoes.values() if d.get("decisao") == Decisao.CONFIRMADO.value
    )
    rejeitados = sum(
        1 for d in decisoes.values() if d.get("decisao") == Decisao.REJEITADO.value
    )
    return {
        "total": total,
        "confirmados": confirmados,
        "rejeitados": rejeitados,
        "pendentes": total - confirmados - rejeitados,
    }


def pronto_para_publicacao(fila: dict[str, Any], decisoes: dict[str, Any]) -> bool:
    """Todo item citavel precisa de decisao — nenhum pendente."""
    return resumo(fila, decisoes)["pendentes"] == 0


def montar_publicacao(fila: dict[str, Any], decisoes: dict[str, Any]) -> dict[str, Any]:
    """Monta o registro final: so' evidencia confirmada, nunca veredito.

    Levanta ValueError se houver item pendente — publicar com pendencia
    seria decisao automatica por omissao, exatamente o que a regra 1 do
    projeto proibe.
    """
    if not pronto_para_publicacao(fila, decisoes):
        raise ValueError("ha' item pendente de revisao; nao pode publicar")

    citacoes = []
    for i, item in enumerate(fila.get("itens", [])):
        d = decisoes.get(str(i), {})
        if d.get("decisao") != Decisao.CONFIRMADO.value:
            continue
        citacoes.append(
            {
                "inicio": item["inicio"],
                "fim": item["fim"],
                "timestamp": item["timestamp"],
                "falante": item["falante"],
                "texto": d.get("texto_final") or item["texto"],
            }
        )

    return {
        "arquivo": fila.get("arquivo"),
        "hash_sha256_original": fila.get("hash_sha256_original"),
        "url": fila.get("url"),
        "citacoes": citacoes,
    }
