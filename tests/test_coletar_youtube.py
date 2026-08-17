import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_youtube import (
    FORMATO_PADRAO,
    FORMATO_RESERVA,
    _data_para_iso,
    _escolher_legenda,
    baixar,
)


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


_MSG_LEGENDA_429 = (
    "Unable to download video subtitles for 'pt-PT': "
    "HTTP Error 429: Too Many Requests"
)
_MSG_FORMATO_403 = "unable to download video data: HTTP Error 403: Forbidden"


def _instalar_yt_dlp_falso(monkeypatch, tmp_path, *, decidir):
    """Instala um yt-dlp falso cujo comportamento por chamada e' definido
    por `decidir(opcoes, indice_chamada) -> str | None`: devolve uma
    mensagem de erro para falhar essa chamada, ou None para suceder.

    Reproduz duas falhas reais de producao (2026-08-17): legenda 'pt-PT'
    rate-limitada (HTTP 429) e formato preferido de video recebendo
    HTTP 403 num stream especifico — as duas podiam derrubar a coleta
    inteira antes da cadeia de fallback em `baixar()`.
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
            erro = decidir(self.opcoes, len(chamadas) - 1)
            if erro:
                raise _DownloadErrorFalso(erro)
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
    def decidir(opcoes, indice):
        return _MSG_LEGENDA_429 if opcoes.get("writesubtitles") else None

    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=decidir)

    info = baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert info["arquivo"].name == "abc123.mp4"
    assert len(chamadas) == 2
    assert chamadas[0]["writesubtitles"] is True
    assert "writesubtitles" not in chamadas[1]


def test_sem_falha_so_uma_chamada(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert len(chamadas) == 1


def test_baixar_legenda_false_nunca_pede_legenda(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)

    assert len(chamadas) == 1
    assert "writesubtitles" not in chamadas[0]


def test_erro_nao_relacionado_a_legenda_ou_formato_propaga(monkeypatch, tmp_path):
    import pytest

    chamadas = _instalar_yt_dlp_falso(
        monkeypatch, tmp_path, decidir=lambda o, i: "Video unavailable"
    )

    with pytest.raises(_DownloadErrorFalso, match="Video unavailable"):
        baixar("https://youtube.com/watch?v=abc123", tmp_path)
    assert len(chamadas) == 1


def test_falha_de_formato_cai_para_formato_de_reserva(monkeypatch, tmp_path):
    """Reproduz o HTTP 403 real (2026-08-17): formato preferido falha,
    formato de reserva (mais simples) funciona."""

    def decidir(opcoes, indice):
        return _MSG_FORMATO_403 if opcoes.get("format") == FORMATO_PADRAO else None

    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=decidir)

    info = baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)

    assert info["arquivo"].name == "abc123.mp4"
    assert len(chamadas) == 2
    assert chamadas[0]["format"] == FORMATO_PADRAO
    assert chamadas[1]["format"] == FORMATO_RESERVA


def test_falha_de_legenda_e_de_formato_combinadas(monkeypatch, tmp_path):
    """As duas falhas reais de producao podem se combinar na mesma
    chamada: legenda falha, tenta sem legenda, MESMO formato falha de
    novo, so' entao cai pro formato de reserva. 3 chamadas ao todo."""

    def decidir(opcoes, indice):
        if opcoes.get("writesubtitles"):
            return _MSG_LEGENDA_429
        if opcoes.get("format") == FORMATO_PADRAO:
            return _MSG_FORMATO_403
        return None

    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=decidir)

    info = baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert info["arquivo"].name == "abc123.mp4"
    assert len(chamadas) == 3
    assert chamadas[0]["writesubtitles"] is True
    assert chamadas[1]["format"] == FORMATO_PADRAO and "writesubtitles" not in chamadas[1]
    assert chamadas[2]["format"] == FORMATO_RESERVA


def test_formato_de_reserva_e_ultimo_recurso_propaga_se_tambem_falhar(monkeypatch, tmp_path):
    import pytest

    chamadas = _instalar_yt_dlp_falso(
        monkeypatch, tmp_path, decidir=lambda o, i: _MSG_FORMATO_403
    )

    with pytest.raises(_DownloadErrorFalso, match="403"):
        baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)
    assert len(chamadas) == 2
