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

Formato de um plano de governo curado (opcional, um arquivo JSON por
candidato em `dados/planos_curados/{slug}.json`):
{
  "saude": {"status": "consta", "trechos": [{"texto": "trecho literal do PDF", "pagina": 12}]},
  "educacao": {"status": "nao_consta"}
}

Curadoria e' manual — um humano le o PDF e cola o trecho, o mesmo espirito
de `revisao.py`: nenhum algoritmo decide se um tema "consta" no plano, so'
expoe o que um humano encontrou (ou confirmou ausente). Tema sem entrada
no arquivo fica "nao verificado ainda" — nunca vira "nao consta" por
omissao (mesmo principio de `qualidade.py`: na duvida, nao decida
sozinho).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEMA_SEM_CLASSIFICACAO = "sem_tema_definido"
STATUS_PLANO_VALIDOS = {"consta", "nao_consta"}


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
                citacoes.append(
                    {
                        **c,
                        "url_origem": publicado.get("url"),
                        "publicado_em": publicado.get("publicado_em"),
                    }
                )
    return citacoes


def carregar_plano_curado(pasta_planos_curados: Path, slug: str) -> dict[str, dict[str, Any]]:
    """Le a curadoria manual do plano de governo de um candidato, por tema.

    Sem arquivo pra esse slug: devolve `{}` (nenhum tema verificado ainda —
    nao e' erro, e' o estado inicial de todo candidato). Com arquivo:
    valida que todo `status` presente e' um dos `STATUS_PLANO_VALIDOS`, pra
    pegar erro de digitacao na curadoria cedo em vez de esconder o tema
    silenciosamente no site publico.
    """
    caminho = Path(pasta_planos_curados) / f"{slug}.json"
    if not caminho.exists():
        return {}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    for tema, entrada in dados.items():
        status = entrada.get("status")
        if status not in STATUS_PLANO_VALIDOS:
            raise ValueError(
                f"{caminho}: status invalido '{status}' para o tema '{tema}' "
                f"(esperado um de {sorted(STATUS_PLANO_VALIDOS)})"
            )
    return dados


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


def citacoes_para_linhas(
    candidatos: list[dict[str, Any]], arquivos_publicados: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Achata citacoes de todos os candidatos numa lista de linhas, pra dados abertos.

    Uma linha por citacao (nao por tema) — `temas` fica como lista; quem
    consome o JSON decide como tratar. O export CSV junta com "|".
    """
    linhas = []
    for c in candidatos:
        for cit in citacoes_do_candidato(c["falante_id"], arquivos_publicados):
            linhas.append(
                {
                    "candidato_slug": c["slug"],
                    "candidato_nome": c["nome"],
                    "partido": c.get("partido"),
                    "temas": cit.get("temas") or [],
                    "texto": cit["texto"],
                    "timestamp": cit.get("timestamp"),
                    "url_origem": cit.get("url_origem"),
                    "publicado_em": cit.get("publicado_em"),
                }
            )
    return linhas
