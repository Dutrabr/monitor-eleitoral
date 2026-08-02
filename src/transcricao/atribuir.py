"""Atribuicao de falante a cada palavra e reagrupamento de segmentos.

O Whisper diz *o que* foi dito e *quando*. A diarizacao diz *quem* falou em
cada intervalo. Cruzar os dois e' o que permite afirmar "o candidato disse X"
em vez de "alguem no video disse X".

Regra de ouro implementada aqui: se um segmento do Whisper cruza a fronteira
entre dois falantes, ele e' quebrado. Segmento com falante misturado nunca
deve virar citacao.
"""

from __future__ import annotations

from .modelos import Palavra, Segmento, Turno

GAP_MAXIMO_INTERNO = 2.0  # silencio acima disso quebra o segmento


def sobreposicao(a_ini: float, a_fim: float, b_ini: float, b_fim: float) -> float:
    """Segundos de interseccao entre dois intervalos. Zero se nao cruzam."""
    return max(0.0, min(a_fim, b_fim) - max(a_ini, b_ini))


def falante_da_palavra(palavra: Palavra, turnos: list[Turno]) -> str | None:
    """Falante com maior sobreposicao temporal com a palavra.

    Se a palavra tem duracao zero (acontece), usa contencao do ponto medio.
    Empate resolve pelo turno que comeca antes, para ser deterministico.
    """
    if not turnos:
        return None

    if palavra.duracao <= 0:
        meio = palavra.inicio
        candidatos = [t for t in turnos if t.inicio <= meio <= t.fim]
        if not candidatos:
            return None
        return min(candidatos, key=lambda t: t.inicio).falante

    melhor: tuple[float, float, str] | None = None
    for t in turnos:
        ov = sobreposicao(palavra.inicio, palavra.fim, t.inicio, t.fim)
        if ov <= 0:
            continue
        chave = (-ov, t.inicio, t.falante)
        if melhor is None or chave < melhor:
            melhor = chave
    return melhor[2] if melhor else None


def atribuir_falantes(
    palavras: list[Palavra], turnos: list[Turno]
) -> list[Palavra]:
    """Preenche `falante` em cada palavra. Muta e retorna a lista."""
    for p in palavras:
        p.falante = falante_da_palavra(p, turnos)
    return palavras


def _pureza(palavras: list[Palavra], falante: str | None) -> float:
    if not palavras:
        return 1.0
    iguais = sum(1 for p in palavras if p.falante == falante)
    return iguais / len(palavras)


def _falante_dominante(palavras: list[Palavra]) -> str | None:
    """Falante com mais tempo de fala no grupo (nao mais palavras).

    Tempo e' mais justo que contagem: uma interjeicao curta do entrevistador
    nao deveria vencer uma frase longa do candidato.
    """
    tempos: dict[str | None, float] = {}
    for p in palavras:
        tempos[p.falante] = tempos.get(p.falante, 0.0) + max(p.duracao, 1e-6)
    if not tempos:
        return None
    return max(tempos.items(), key=lambda kv: (kv[1], str(kv[0])))[0]


def reagrupar_por_falante(
    segmento: Segmento, gap_maximo: float = GAP_MAXIMO_INTERNO
) -> list[Segmento]:
    """Quebra um segmento do Whisper em sub-segmentos de falante unico.

    Quebra quando o falante muda ou quando ha silencio longo entre palavras.
    Herda as metricas de confianca do segmento original: elas foram calculadas
    para o bloco inteiro e nao podem ser recomputadas aqui, entao aplicar a
    metrica do pai a cada filho e' a leitura conservadora.
    """
    if not segmento.palavras:
        segmento.pureza_falante = 1.0
        return [segmento]

    grupos: list[list[Palavra]] = [[segmento.palavras[0]]]
    for anterior, atual in zip(segmento.palavras, segmento.palavras[1:]):
        mudou_falante = atual.falante != anterior.falante
        gap = atual.inicio - anterior.fim
        if mudou_falante or gap > gap_maximo:
            grupos.append([atual])
        else:
            grupos[-1].append(atual)

    saida: list[Segmento] = []
    for grupo in grupos:
        dominante = _falante_dominante(grupo)
        texto = "".join(p.texto for p in grupo).strip()
        if not texto:
            continue
        saida.append(
            Segmento(
                inicio=grupo[0].inicio,
                fim=grupo[-1].fim,
                texto=texto,
                avg_logprob=segmento.avg_logprob,
                no_speech_prob=segmento.no_speech_prob,
                compression_ratio=segmento.compression_ratio,
                palavras=grupo,
                falante=dominante,
                pureza_falante=_pureza(grupo, dominante),
            )
        )
    return saida or [segmento]


def aplicar_diarizacao(
    segmentos: list[Segmento], turnos: list[Turno]
) -> list[Segmento]:
    """Pipeline de atribuicao: atribui palavra a palavra, depois reagrupa."""
    for seg in segmentos:
        atribuir_falantes(seg.palavras, turnos)

    saida: list[Segmento] = []
    for seg in segmentos:
        saida.extend(reagrupar_por_falante(seg))
    return saida


def falantes_presentes(segmentos: list[Segmento]) -> list[str]:
    return sorted({s.falante for s in segmentos if s.falante is not None})


def renomear_falantes(
    segmentos: list[Segmento], mapa: dict[str, str]
) -> list[Segmento]:
    """Troca rotulos anonimos (SPEAKER_00) por nomes reais.

    A diarizacao nao sabe *quem* e' cada falante, so que sao diferentes. O
    mapeamento vem de conferencia humana ou de voz de referencia cadastrada.
    Nunca deduza isso automaticamente sem validacao.
    """
    for seg in segmentos:
        if seg.falante in mapa:
            seg.falante = mapa[seg.falante]
        for p in seg.palavras:
            if p.falante in mapa:
                p.falante = mapa[p.falante]
    return segmentos
