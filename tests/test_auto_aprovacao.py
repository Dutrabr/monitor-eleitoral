import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.auto_aprovacao import (
    gerar_decisoes_automaticas,
    segmento_elegivel,
    video_e_falante_unico,
)


def _seg(**kw):
    base = {
        "texto": "algum texto",
        "status": "ok",
        "falante": "SPEAKER_00",
        "no_speech_prob": 0.05,
        "avg_logprob": -0.1,
        "compression_ratio": 1.3,
        "pureza_falante": 1.0,
    }
    base.update(kw)
    return base


# --- segmento_elegivel -------------------------------------------------

def test_segmento_elegivel_com_sinais_bons():
    assert segmento_elegivel(_seg()) is True


def test_segmento_nao_elegivel_no_speech_alto():
    assert segmento_elegivel(_seg(no_speech_prob=0.16)) is False


def test_segmento_nao_elegivel_logprob_baixo():
    assert segmento_elegivel(_seg(avg_logprob=-0.31)) is False


def test_segmento_nao_elegivel_compressao_alta():
    assert segmento_elegivel(_seg(compression_ratio=2.1)) is False


def test_segmento_nao_elegivel_pureza_menor_que_um():
    assert segmento_elegivel(_seg(pureza_falante=0.8)) is False


def test_segmento_nao_elegivel_descartado():
    assert segmento_elegivel(_seg(status="descartado")) is False


def test_segmento_nao_elegivel_sem_metrica_whisper():
    """Transcricao vinda de legenda nao tem essas metricas — nunca auto-aprova."""
    assert segmento_elegivel(_seg(no_speech_prob=None)) is False


# --- video_e_falante_unico ----------------------------------------------

def test_video_falante_unico_true():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_00")]
    assert video_e_falante_unico(segs) is True


def test_video_dois_falantes_false():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01")]
    assert video_e_falante_unico(segs) is False


def test_video_sem_falante_nenhum_false():
    segs = [_seg(falante=None), _seg(falante=None)]
    assert video_e_falante_unico(segs) is False


def test_video_ignora_descartados_na_contagem():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01", status="descartado")]
    assert video_e_falante_unico(segs) is True


# --- gerar_decisoes_automaticas ------------------------------------------

def test_gera_confirmado_para_elegiveis_em_video_falante_unico():
    segs = [_seg(), _seg()]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["decisao"] == "confirmado"
    assert decisoes["0"]["falante_confirmado"] == "candidato_fulano"
    assert decisoes["1"]["decisao"] == "confirmado"


def test_nao_gera_decisao_para_segmento_nao_elegivel():
    segs = [_seg(), _seg(no_speech_prob=0.5)]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert "0" in decisoes
    assert "1" not in decisoes


def test_video_multi_falante_nao_gera_nenhuma_decisao():
    segs = [_seg(falante="SPEAKER_00"), _seg(falante="SPEAKER_01")]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes == {}


def test_nao_sobrescreve_decisao_ja_existente():
    segs = [_seg()]
    existentes = {"0": {"decisao": "rejeitado"}}
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", existentes, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["decisao"] == "rejeitado"


def test_marca_revisado_por_auto_aprovacao():
    segs = [_seg()]
    decisoes = gerar_decisoes_automaticas(segs, "candidato_fulano", {}, revisado_em="2026-08-19T00:00:00+00:00")
    assert decisoes["0"]["revisado_por"] == "auto_aprovacao_confianca"


def test_nao_muta_decisoes_original():
    segs = [_seg()]
    original = {}
    gerar_decisoes_automaticas(segs, "candidato_fulano", original, revisado_em="2026-08-19T00:00:00+00:00")
    assert original == {}
