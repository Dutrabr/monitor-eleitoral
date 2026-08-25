import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.deduplicar import (
    LIMIAR_REPETIDO,
    assinatura,
    encontrar_repetido,
    similaridade,
)

DISCURSO = " ".join(
    f"vamos investir em saude numero {i} para o povo do nosso estado inteiro"
    for i in range(20)
)


def test_recorte_do_mesmo_video_e_detectado():
    """Caso real mais comum: o Reel e' um pedaco do video longo do YouTube.
    Jaccard puniria pela diferenca de tamanho; containment nao."""
    recorte = " ".join(DISCURSO.split()[40:120])
    achado = encontrar_repetido(recorte, {"video_longo": DISCURSO})
    assert achado is not None
    identificador, s = achado
    assert identificador == "video_longo"
    assert s == 1.0


def test_video_diferente_nao_casa():
    outro = " ".join(
        f"proposta {i} sobre transporte coletivo e mobilidade urbana na capital"
        for i in range(20)
    )
    assert encontrar_repetido(outro, {"v1": DISCURSO}) is None


def test_texto_curto_nunca_vira_duplicata():
    """Trecho de 10 palavras casa por acaso dentro de qualquer discurso
    longo; chamar isso de repetido apagaria evidencia real."""
    assert assinatura("apenas algumas poucas palavras aqui") == frozenset()
    assert encontrar_repetido("apenas algumas poucas palavras aqui", {"v1": DISCURSO}) is None


def test_ruido_de_asr_ainda_casa():
    """O mesmo video reencodado por outra plataforma transcreve um pouco
    diferente. Medido em 2026-08-25: 8% de erro de palavra deixa o
    containment em ~0.58 no pior caso, acima do limiar."""
    palavras = DISCURSO.split()
    com_ruido = [
        ("ruidoxyz" if i % 12 == 0 else p) for i, p in enumerate(palavras)
    ]
    s = similaridade(assinatura(" ".join(com_ruido)), assinatura(DISCURSO))
    assert s >= LIMIAR_REPETIDO


def test_devolve_qual_video_casou_nao_so_um_bool():
    """Sem saber COM QUAL casou, o log nao consegue explicar o descarte —
    viraria descarte silencioso (regra 5)."""
    recorte = " ".join(DISCURSO.split()[10:90])
    achado = encontrar_repetido(recorte, {"a": "texto curto", "b": DISCURSO})
    assert achado is not None and achado[0] == "b"


def test_limiar_tem_margem_medida_contra_video_distinto():
    """Videos distintos mediram no maximo 0.008 de containment nos 1.653
    pares reais. O limiar precisa ficar MUITO acima disso."""
    assert LIMIAR_REPETIDO > 0.008 * 10
