import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.modelos import Status
from transcricao import legendas

VTT_SIMPLES = """WEBVTT

00:00:00.080 --> 00:00:02.500
vamos ampliar a rede federal de ensino tecnico

00:00:02.500 --> 00:00:05.000
e como o senhor pretende financiar essa proposta
"""

VTT_ROLLING = """WEBVTT
Kind: captions
Language: pt

00:00:00.080 --> 00:00:02.500 align:start position:0%
vamos<00:00:00.399><c> ampliar</c><00:00:00.799><c> a</c>

00:00:02.500 --> 00:00:02.510 align:start position:0%
vamos ampliar a rede

00:00:02.510 --> 00:00:05.000 align:start position:0%
vamos ampliar a rede
federal<00:00:02.899><c> de</c><00:00:03.199><c> ensino</c>
"""

SRT_SIMPLES = """1
00:00:00,080 --> 00:00:02,500
vamos ampliar a rede federal de ensino tecnico

2
00:00:02,500 --> 00:00:05,000
e como o senhor pretende financiar essa proposta
"""

VTT_ALUCINACAO = """WEBVTT

00:00:00.000 --> 00:00:03.000
inscreva-se no canal e deixe seu like
"""


def test_parseia_vtt_simples():
    cues = legendas.parsear_cues(VTT_SIMPLES)
    assert len(cues) == 2
    assert cues[0] == (0.08, 2.5, "vamos ampliar a rede federal de ensino tecnico")
    assert cues[1][2] == "e como o senhor pretende financiar essa proposta"


def test_parseia_srt():
    cues = legendas.parsear_cues(SRT_SIMPLES)
    assert len(cues) == 2
    assert cues[0][0] == 0.08
    assert cues[0][2] == "vamos ampliar a rede federal de ensino tecnico"


def test_remove_tags_de_timing_por_palavra():
    cues = legendas.parsear_cues(VTT_ROLLING)
    for _, _, texto in cues:
        assert "<" not in texto and ">" not in texto


def test_descarta_cue_identico_ao_anterior():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
mesma frase repetida

00:00:02.000 --> 00:00:04.000
mesma frase repetida

00:00:04.000 --> 00:00:06.000
frase nova
"""
    cues = legendas.parsear_cues(vtt)
    assert [c[2] for c in cues] == ["mesma frase repetida", "frase nova"]


def test_rolling_nao_gera_cues_exatamente_repetidas():
    cues = legendas.parsear_cues(VTT_ROLLING)
    textos = [c[2] for c in cues]
    for a, b in zip(textos, textos[1:]):
        assert a != b


def test_montar_segmentos_marca_revisar_por_falta_de_confianca():
    segs = legendas.montar_segmentos(VTT_SIMPLES)
    assert len(segs) == 2
    assert all(s.status is Status.REVISAR for s in segs)
    assert all("legenda" in m for s in segs for m in s.motivos)


def test_montar_segmentos_descarta_alucinacao_conhecida():
    segs = legendas.montar_segmentos(VTT_ALUCINACAO)
    assert len(segs) == 1
    assert segs[0].status is Status.DESCARTADO


def test_montar_segmentos_nunca_produz_ok():
    segs = legendas.montar_segmentos(VTT_SIMPLES + VTT_ALUCINACAO.replace("WEBVTT\n\n", ""))
    assert all(s.status is not Status.OK for s in segs)
