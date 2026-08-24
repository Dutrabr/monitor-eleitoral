"""Fluxo de revisao humana: fila -> decisao -> publicacao.

Puro — sem I/O. Nenhuma decisao e' automatica: cada item citavel da fila
(`pipeline.fila_de_verificacao`, que ja exclui os DESCARTADOS) precisa de um
CONFIRMADO ou REJEITADO explicito antes de poder entrar em publicacao.
Rejeitar nao apaga nada — so' marca que aquele trecho nao vai ao ar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from .modelos import Tema


class Decisao(str, Enum):
    CONFIRMADO = "confirmado"
    REJEITADO = "rejeitado"


def _validar_temas(temas: list[str] | None) -> list[str]:
    if not temas:
        return []
    validos = {t.value for t in Tema}
    invalidos = [t for t in temas if t not in validos]
    if invalidos:
        raise ValueError(f"tema(s) invalido(s): {invalidos}")
    return list(temas)


def registrar_decisao(
    decisoes: dict[str, Any],
    indice: int,
    decisao: Decisao,
    *,
    texto_final: str | None = None,
    temas: list[str] | None = None,
    falante: str | None = None,
    revisado_por: str | None = None,
    revisado_em: str | None = None,
) -> dict[str, Any]:
    """Devolve uma NOVA copia de `decisoes` com a decisao aplicada.

    Nao muta o dict recebido. Nao acessa relogio por conta propria: quem
    chama passa `revisado_em`, o que mantem a funcao testavel sem mock de
    tempo e deixa explicito de onde vem o timestamp de auditoria.

    `temas` (ver TAXONOMIA.md) so' se aplica a CONFIRMADO — uma citacao
    rejeitada nao vai ao ar, entao classifica-la por tema nao tem uso. Uma
    citacao pode ter varios temas, ou nenhum (lista vazia): nunca forca
    encaixe artificial.

    `falante`: a diarizacao pode nao atribuir ninguem a um segmento (gap de
    cobertura — ver `atribuir.py`), ou atribuir errado. O humano que ouviu
    o audio confirma ou corrige isso no mesmo passo em que confirma o
    texto. Sem essa confirmacao explicita, `montar_publicacao` usa o
    falante que a diarizacao deu (que pode ser None) — nunca inventa um.
    """
    novas = dict(decisoes)
    entrada: dict[str, Any] = {"decisao": decisao.value}
    if decisao is Decisao.CONFIRMADO:
        entrada["texto_final"] = texto_final
        entrada["temas"] = _validar_temas(temas)
        if falante:
            entrada["falante_confirmado"] = falante
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
                "falante": d.get("falante_confirmado") or item["falante"],
                "texto": d.get("texto_final") or item["texto"],
                "temas": d.get("temas") or [],
            }
        )

    return {
        "arquivo": fila.get("arquivo"),
        "hash_sha256_original": fila.get("hash_sha256_original"),
        "url": fila.get("url"),
        "publicado_em": fila.get("publicado_em"),
        "coletado_em": fila.get("coletado_em"),
        # "fala_do_candidato" (padrao) ou "material_de_campanha" — video
        # publicado no canal oficial em que quem fala NAO e' o candidato
        # (locutor, jingle, depoimento de terceiro). Ver nota em CLAUDE.md.
        "tipo_material": fila.get("tipo_material") or "fala_do_candidato",
        "citacoes": citacoes,
    }
