import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.modelos import Palavra, Segmento, Turno
from transcricao import atribuir


def p(ini, fim, texto=" x", prob=0.95):
    return Palavra(inicio=ini, fim=fim, texto=texto, probabilidade=prob)


def test_sobreposicao_basica():
    assert atribuir.sobreposicao(0, 10, 5, 15) == 5
    assert atribuir.sobreposicao(0, 4, 6, 9) == 0
    assert atribuir.sobreposicao(2, 3, 0, 10) == 1


def test_palavra_dentro_de_um_turno():
    turnos = [Turno(0, 10, "A"), Turno(10, 20, "B")]
    assert atribuir.falante_da_palavra(p(2, 3), turnos) == "A"
    assert atribuir.falante_da_palavra(p(12, 13), turnos) == "B"


def test_palavra_na_fronteira_vence_maior_sobreposicao():
    turnos = [Turno(0, 10, "A"), Turno(10, 20, "B")]
    # 9.0-10.5 -> 1.0s em A, 0.5s em B
    assert atribuir.falante_da_palavra(p(9.0, 10.5), turnos) == "A"
    # 9.8-11.0 -> 0.2s em A, 1.0s em B
    assert atribuir.falante_da_palavra(p(9.8, 11.0), turnos) == "B"


def test_palavra_sem_turno_fica_sem_falante():
    turnos = [Turno(0, 5, "A")]
    assert atribuir.falante_da_palavra(p(20, 21), turnos) is None


def test_sem_diarizacao_fica_sem_falante():
    assert atribuir.falante_da_palavra(p(1, 2), []) is None


def test_palavra_duracao_zero_usa_ponto_medio():
    turnos = [Turno(0, 10, "A"), Turno(10, 20, "B")]
    assert atribuir.falante_da_palavra(p(4, 4), turnos) == "A"
    assert atribuir.falante_da_palavra(p(15, 15), turnos) == "B"


def _segmento_com(palavras):
    return Segmento(
        inicio=palavras[0].inicio,
        fim=palavras[-1].fim,
        texto="".join(x.texto for x in palavras),
        avg_logprob=-0.2,
        no_speech_prob=0.01,
        compression_ratio=1.3,
        palavras=palavras,
    )


def test_reagrupamento_quebra_na_troca_de_falante():
    palavras = [p(0, 1, " um"), p(1, 2, " dois"), p(2, 3, " tres"), p(3, 4, " quatro")]
    turnos = [Turno(0, 2, "A"), Turno(2, 4, "B")]
    saida = atribuir.aplicar_diarizacao([_segmento_com(palavras)], turnos)
    assert len(saida) == 2
    assert saida[0].falante == "A"
    assert saida[0].texto == "um dois"
    assert saida[1].falante == "B"
    assert saida[1].texto == "tres quatro"


def test_reagrupamento_quebra_em_silencio_longo():
    palavras = [p(0, 1, " um"), p(1, 2, " dois"), p(30, 31, " tres")]
    turnos = [Turno(0, 40, "A")]
    saida = atribuir.aplicar_diarizacao([_segmento_com(palavras)], turnos)
    assert len(saida) == 2
    assert all(s.falante == "A" for s in saida)


def test_falante_unico_nao_quebra():
    palavras = [p(0, 1, " um"), p(1, 2, " dois"), p(2, 3, " tres")]
    turnos = [Turno(0, 5, "A")]
    saida = atribuir.aplicar_diarizacao([_segmento_com(palavras)], turnos)
    assert len(saida) == 1
    assert saida[0].pureza_falante == 1.0


def test_dominante_e_por_tempo_nao_por_contagem():
    # entrevistador solta tres monossilabos; candidato fala uma frase longa
    palavras = [
        p(0.0, 0.1, " e"),
        p(0.1, 0.2, " ah"),
        p(0.2, 0.3, " sim"),
        p(0.3, 5.0, " precisamos-reformar-o-sistema"),
    ]
    for w in palavras[:3]:
        w.falante = "B"
    palavras[3].falante = "A"
    seg = _segmento_com(palavras)
    # forca um unico grupo desligando a quebra
    grupos = atribuir.reagrupar_por_falante(seg, gap_maximo=1e9)
    # a troca de falante ainda quebra, entao esperamos 2 grupos
    assert len(grupos) == 2
    longo = max(grupos, key=lambda s: s.fim - s.inicio)
    assert longo.falante == "A"


def test_pureza_calculada_quando_ha_mistura():
    palavras = [p(0, 1), p(1, 2), p(2, 3)]
    palavras[0].falante = "A"
    palavras[1].falante = "A"
    palavras[2].falante = "A"
    seg = _segmento_com(palavras)
    grupos = atribuir.reagrupar_por_falante(seg)
    assert grupos[0].pureza_falante == 1.0


def test_falantes_presentes_ordenado_e_sem_none():
    segs = [
        Segmento(0, 1, "a", -0.2, 0.01, 1.2, falante="SPEAKER_01"),
        Segmento(1, 2, "b", -0.2, 0.01, 1.2, falante="SPEAKER_00"),
        Segmento(2, 3, "c", -0.2, 0.01, 1.2, falante=None),
    ]
    assert atribuir.falantes_presentes(segs) == ["SPEAKER_00", "SPEAKER_01"]


def test_renomear_falantes_atinge_palavras():
    palavras = [p(0, 1), p(1, 2)]
    for w in palavras:
        w.falante = "SPEAKER_00"
    seg = _segmento_com(palavras)
    seg.falante = "SPEAKER_00"
    atribuir.renomear_falantes([seg], {"SPEAKER_00": "candidato_x"})
    assert seg.falante == "candidato_x"
    assert all(w.falante == "candidato_x" for w in seg.palavras)
