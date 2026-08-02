import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_youtube import _data_para_iso, _escolher_legenda


def test_data_para_iso_converte_upload_date():
    assert _data_para_iso("20260729") == "2026-07-29T00:00:00+00:00"


def test_data_para_iso_none_quando_ausente():
    assert _data_para_iso(None) is None
    assert _data_para_iso("") is None
    assert _data_para_iso("2026") is None


def test_escolhe_legenda_manual_antes_de_automatica():
    info = {
        "subtitles": {"pt-BR": [{}]},
        "automatic_captions": {"pt": [{}]},
    }
    assert _escolher_legenda(info, idiomas=("pt", "pt-BR")) == ("pt-BR", "manual")


def test_cai_para_automatica_se_nao_houver_manual():
    info = {
        "subtitles": {"en": [{}]},
        "automatic_captions": {"pt": [{}]},
    }
    assert _escolher_legenda(info, idiomas=("pt", "pt-BR")) == ("pt", "automatica")


def test_nenhuma_legenda_nos_idiomas_pedidos():
    info = {"subtitles": {"en": [{}]}, "automatic_captions": {"es": [{}]}}
    assert _escolher_legenda(info, idiomas=("pt", "pt-BR")) is None


def test_sem_chaves_de_legenda_no_info():
    assert _escolher_legenda({}) is None
