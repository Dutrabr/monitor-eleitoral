import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_youtube import _data_para_iso, _escolher_legenda, baixar


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


class _DownloadErrorFalso(Exception):
    pass


def _instalar_yt_dlp_falso(monkeypatch, tmp_path, *, falha_na_legenda):
    """Simula o yt-dlp real: 1a chamada (com legenda) pode falhar; refeita
    sem legenda deve funcionar. Reproduz o HTTP 429 real visto em producao
    (2026-08-17): legenda 'pt-PT' rate-limitada derrubava a coleta do
    video inteiro, mesmo o video ja tendo baixado com sucesso.
    """
    chamadas = []

    class _YDLFalso:
        def __init__(self, opcoes):
            self.opcoes = opcoes

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download):
            chamadas.append(dict(self.opcoes))
            if falha_na_legenda and self.opcoes.get("writesubtitles"):
                raise _DownloadErrorFalso(
                    "Unable to download video subtitles for 'pt-PT': "
                    "HTTP Error 429: Too Many Requests"
                )
            (tmp_path / "abc123.mp4").write_bytes(b"video falso")
            return {
                "id": "abc123",
                "ext": "mp4",
                "title": "titulo",
                "uploader": "canal",
                "webpage_url": url,
                "upload_date": "20260817",
            }

    modulo_falso = types.SimpleNamespace(
        YoutubeDL=_YDLFalso,
        utils=types.SimpleNamespace(DownloadError=_DownloadErrorFalso),
    )
    monkeypatch.setitem(sys.modules, "yt_dlp", modulo_falso)
    return chamadas


def test_falha_transitoria_na_legenda_nao_derruba_o_video(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, falha_na_legenda=True)

    info = baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert info["arquivo"].name == "abc123.mp4"
    assert len(chamadas) == 2
    assert chamadas[0]["writesubtitles"] is True
    assert "writesubtitles" not in chamadas[1]


def test_sem_falha_na_legenda_so_uma_chamada(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, falha_na_legenda=False)

    baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert len(chamadas) == 1


def test_baixar_legenda_false_nunca_pede_legenda(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, falha_na_legenda=False)

    baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)

    assert len(chamadas) == 1
    assert "writesubtitles" not in chamadas[0]


def test_erro_nao_relacionado_a_legenda_propaga(monkeypatch, tmp_path):
    class _YDLQuebrado:
        def __init__(self, opcoes):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download):
            raise _DownloadErrorFalso("Video unavailable")

    modulo_falso = types.SimpleNamespace(
        YoutubeDL=_YDLQuebrado,
        utils=types.SimpleNamespace(DownloadError=_DownloadErrorFalso),
    )
    monkeypatch.setitem(sys.modules, "yt_dlp", modulo_falso)

    import pytest

    with pytest.raises(_DownloadErrorFalso, match="Video unavailable"):
        baixar("https://youtube.com/watch?v=abc123", tmp_path)
