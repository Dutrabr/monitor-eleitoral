"""Deteccao de video repetido entre plataformas — PURO, sem I/O.

Campanha publica a MESMA peca no YouTube, Instagram, TikTok e Facebook.
Dos 141 candidatos a Governador que ainda faltam coletar, 96 tem mais de
uma plataforma cadastrada no TSE — entao repetir e' o caso comum, nao a
excecao. Sem isso, a mesma fala apareceria varias vezes na pagina do
candidato como se fossem declaracoes distintas, inflando a contagem de
citacoes e dando peso falso a um unico video.

Hash nao resolve: o mesmo video reencodado por cada plataforma tem bytes
diferentes, entao `hash_sha256_original` (regra 6) prova origem mas nao
identifica conteudo repetido. A comparacao aqui e' pelo TEXTO transcrito.

Metrica: "containment" de shingles de 5 palavras — a fracao dos trechos
de 5 palavras do documento menor que tambem aparecem no maior. Escolhida
em cima do caso real mais dificil: o Reel costuma ser um RECORTE do video
longo do YouTube, nao uma copia inteira. Jaccard puniria o recorte (os
tamanhos diferem muito); containment nao.

Limiar calibrado contra dado real, nao intuicao (2026-08-25), medindo os
1.653 pares dos 58 videos ja coletados:
  - videos DISTINTOS:              containment maximo 0.008
  - recorte contiguo do mesmo video:                 1.000
  - mesmo video com 8% de erro de ASR (reencode):    0.576 no pior caso
LIMIAR_REPETIDO = 0.30 fica ~37x acima do pior caso de video distinto e
bem abaixo do pior caso de duplicata real. Se a margem encolher quando o
volume crescer, remedir com os mesmos tres cenarios antes de mexer.

Nunca descarta em silencio (mesmo espirito da regra 5): quem chama
recebe QUAL video ja existente casou e decide o que fazer. Errar pra
menos (deixar passar uma duplicata) custa um video a mais na fila, que e'
visivel e corrigivel; errar pra mais (apagar evidencia real achando que e'
repetida) e' invisivel. Por isso o limiar erra pro lado alto.
"""

from __future__ import annotations

import re
import unicodedata

TAMANHO_SHINGLE = 5
LIMIAR_REPETIDO = 0.30
MIN_PALAVRAS = 30


def _palavras(texto: str) -> list[str]:
    decomposto = unicodedata.normalize("NFD", texto or "")
    sem_acento = "".join(
        c for c in decomposto if unicodedata.category(c) != "Mn"
    ).lower()
    return re.findall(r"[a-z0-9]+", sem_acento)


def assinatura(texto: str) -> frozenset[tuple[str, ...]]:
    """Conjunto de shingles de 5 palavras que identifica o conteudo.

    Devolve conjunto vazio para texto curto demais (< MIN_PALAVRAS): um
    trecho de 10 palavras casaria por acaso dentro de qualquer discurso
    longo, e chamar isso de duplicata apagaria evidencia real.
    """
    palavras = _palavras(texto)
    if len(palavras) < MIN_PALAVRAS:
        return frozenset()
    return frozenset(
        tuple(palavras[i : i + TAMANHO_SHINGLE])
        for i in range(len(palavras) - TAMANHO_SHINGLE + 1)
    )


def similaridade(a: frozenset, b: frozenset) -> float:
    """Containment: fracao do documento MENOR contida no maior (0.0 a 1.0)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def encontrar_repetido(
    texto: str, existentes: dict[str, str]
) -> tuple[str, float] | None:
    """O texto ja existe em `existentes` ({identificador: texto})?

    Devolve `(identificador, similaridade)` do MAIS parecido acima do
    limiar, ou None. Devolver o par (e nao so' um bool) e' de proposito:
    quem chama precisa poder dizer NO LOG com qual video casou, senao
    vira descarte silencioso.
    """
    nova = assinatura(texto)
    if not nova:
        return None
    melhor: tuple[str, float] | None = None
    for identificador, texto_existente in existentes.items():
        s = similaridade(nova, assinatura(texto_existente))
        if s >= LIMIAR_REPETIDO and (melhor is None or s > melhor[1]):
            melhor = (identificador, s)
    return melhor
