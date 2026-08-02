"""Regras de descarte e sinalizacao de segmentos.

Esta e' a camada mais importante do projeto. Uma frase alucinada pelo Whisper
atribuida a um candidato a presidente e' processo judicial. As regras aqui
sao deliberadamente conservadoras: na duvida, REVISAR; no sinal claro de
silencio/musica, DESCARTADO.

Nenhuma funcao aqui faz I/O ou depende de modelo, o que permite testar tudo.
"""

from __future__ import annotations

import re
import unicodedata

from .modelos import Palavra, Segmento, Status

# ---------------------------------------------------------------------------
# Limiares. Ajuste com base em amostra rotulada a mao, nao por intuicao.
# ---------------------------------------------------------------------------

NO_SPEECH_MAX = 0.60          # acima disso: provavel trecho sem fala
AVG_LOGPROB_MIN = -1.00       # abaixo disso: modelo pouco confiante
COMPRESSION_RATIO_MAX = 2.40  # acima disso: texto repetitivo (loop classico)
PROB_PALAVRA_MIN = 0.50       # palavra individual duvidosa
FRACAO_PALAVRAS_FRACAS_MAX = 0.30  # % de palavras fracas tolerada no segmento

# Fala humana em portugues fica, grosso modo, entre 5 e 25 caracteres/segundo.
# Fora dessa faixa costuma ser artefato: texto colado em silencio, ou legenda
# de musica comprimida num instante.
CHARS_POR_SEG_MIN = 3.0
CHARS_POR_SEG_MAX = 30.0
DURACAO_MINIMA_PARA_TAXA = 1.0  # nao aplicar taxa em segmento muito curto

PUREZA_FALANTE_MIN = 0.85     # abaixo disso, o segmento mistura falantes

# Frases que o Whisper inventa em silencio. Lista inicial em pt-BR; amplie
# conforme observar o corpus real.
ALUCINACOES_COMUNS = (
    "legendas pela comunidade amara.org",
    "legendado pela comunidade amara.org",
    "amara.org",
    "obrigado por assistir",
    "obrigada por assistir",
    "inscreva-se no canal",
    "se inscreve no canal",
    "deixe seu like",
    "ate o proximo video",
    "transcricao automatica",
    "subtitles by",
    "thanks for watching",
)


def _normalizar(texto: str) -> str:
    """Minusculas, sem acento, sem pontuacao, espacos colapsados."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _fracao_palavras_fracas(palavras: list[Palavra]) -> float:
    if not palavras:
        return 0.0
    fracas = sum(1 for p in palavras if p.probabilidade < PROB_PALAVRA_MIN)
    return fracas / len(palavras)


def _texto_e_alucinacao_conhecida(texto: str) -> bool:
    norm = _normalizar(texto)
    if not norm:
        return True
    return any(_normalizar(a) in norm for a in ALUCINACOES_COMUNS)


def _tem_repeticao_interna(texto: str, min_repeticoes: int = 4) -> bool:
    """Detecta a mesma palavra ou n-grama curto repetido em loop."""
    palavras = _normalizar(texto).split()
    if len(palavras) < min_repeticoes:
        return False
    # mesma palavra consecutiva N vezes
    seguidas = 1
    for a, b in zip(palavras, palavras[1:]):
        seguidas = seguidas + 1 if a == b else 1
        if seguidas >= min_repeticoes:
            return True
    # bigrama repetido em loop
    if len(palavras) >= min_repeticoes * 2:
        bigramas = [" ".join(palavras[i:i + 2]) for i in range(len(palavras) - 1)]
        seguidas = 1
        for a, b in zip(bigramas, bigramas[2:]):
            seguidas = seguidas + 1 if a == b else 1
            if seguidas >= min_repeticoes:
                return True
    return False


def avaliar_texto(texto: str) -> list[str]:
    """Sinais de alucinacao que dependem so do texto, sem metricas do Whisper.

    Usado por fontes sem confianca de ASR (ex: legenda do YouTube), onde
    avg_logprob/no_speech_prob/compression_ratio nao existem.
    """
    motivos: list[str] = []
    if _texto_e_alucinacao_conhecida(texto):
        motivos.append("texto vazio ou alucinacao conhecida")
    if _tem_repeticao_interna(texto):
        motivos.append("repeticao em loop no texto")
    return motivos


def avaliar_segmento(seg: Segmento) -> Segmento:
    """Aplica as regras e preenche `status` e `motivos` in-place."""
    motivos: list[str] = []
    descartar = False

    if _texto_e_alucinacao_conhecida(seg.texto):
        motivos.append("texto vazio ou alucinacao conhecida")
        descartar = True

    if seg.no_speech_prob > NO_SPEECH_MAX:
        motivos.append(
            f"no_speech_prob={seg.no_speech_prob:.2f} > {NO_SPEECH_MAX}"
        )
        descartar = True

    if _tem_repeticao_interna(seg.texto):
        motivos.append("repeticao em loop no texto")
        descartar = True

    if seg.avg_logprob < AVG_LOGPROB_MIN:
        motivos.append(
            f"avg_logprob={seg.avg_logprob:.2f} < {AVG_LOGPROB_MIN}"
        )

    if seg.compression_ratio > COMPRESSION_RATIO_MAX:
        motivos.append(
            f"compression_ratio={seg.compression_ratio:.2f} > "
            f"{COMPRESSION_RATIO_MAX}"
        )

    fracao = _fracao_palavras_fracas(seg.palavras)
    if fracao > FRACAO_PALAVRAS_FRACAS_MAX:
        motivos.append(f"{fracao:.0%} das palavras com probabilidade baixa")

    if seg.duracao >= DURACAO_MINIMA_PARA_TAXA:
        taxa = len(seg.texto.strip()) / seg.duracao
        if not (CHARS_POR_SEG_MIN <= taxa <= CHARS_POR_SEG_MAX):
            motivos.append(f"taxa implausivel de {taxa:.1f} chars/s")

    if seg.pureza_falante < PUREZA_FALANTE_MIN:
        motivos.append(
            f"segmento mistura falantes (pureza={seg.pureza_falante:.2f})"
        )

    if seg.falante is None and seg.palavras:
        motivos.append("sem falante atribuido")

    if descartar:
        seg.status = Status.DESCARTADO
    elif motivos:
        seg.status = Status.REVISAR
    else:
        seg.status = Status.OK

    seg.motivos = motivos
    return seg


def marcar_repeticoes_consecutivas(segmentos: list[Segmento]) -> list[Segmento]:
    """Sinaliza segmentos consecutivos com texto identico.

    E' a assinatura mais comum de alucinacao do Whisper em trilha sonora:
    a mesma frase repetida por minutos.
    """
    anterior_norm: str | None = None
    repeticoes = 0
    for seg in segmentos:
        atual = _normalizar(seg.texto)
        if atual and atual == anterior_norm:
            repeticoes += 1
            if repeticoes >= 2:
                seg.status = Status.DESCARTADO
                if "texto repetido de segmentos anteriores" not in seg.motivos:
                    seg.motivos.append("texto repetido de segmentos anteriores")
        else:
            repeticoes = 0
        anterior_norm = atual
    return segmentos


def avaliar(segmentos: list[Segmento]) -> list[Segmento]:
    """Ponto de entrada: avalia cada segmento e depois olha a sequencia."""
    return marcar_repeticoes_consecutivas(
        [avaliar_segmento(s) for s in segmentos]
    )


def resumo(segmentos: list[Segmento]) -> dict[str, int]:
    return {
        "total": len(segmentos),
        "ok": sum(1 for s in segmentos if s.status is Status.OK),
        "revisar": sum(1 for s in segmentos if s.status is Status.REVISAR),
        "descartado": sum(1 for s in segmentos if s.status is Status.DESCARTADO),
    }
