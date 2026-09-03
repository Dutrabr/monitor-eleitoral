import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.coletar_youtube import (
    FORMATO_PADRAO,
    FORMATO_RESERVA,
    RUNTIMES_JS,
    _data_para_iso,
    _escolher_legenda,
    _processar_com_legenda,
    baixar,
)

ffmpeg_ok = shutil.which("ffmpeg") is not None
requer_ffmpeg = pytest.mark.skipif(not ffmpeg_ok, reason="ffmpeg ausente")

VTT_SIMPLES = """WEBVTT

00:00:00.080 --> 00:00:02.500
vamos ampliar a rede federal de ensino tecnico
"""


@pytest.fixture
def video_original(tmp_path):
    """Arquivo de midia real, gerado pelo ffmpeg — simula o .mp4 baixado do YouTube."""
    destino = tmp_path / "abc123.mp4"
    subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-y", str(destino), "-loglevel", "error",
        ],
        check=True,
    )
    return destino


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


def test_cookies_de_navegador_habilitados_por_padrao(monkeypatch, tmp_path):
    """Descoberto em producao (2026-08-18): sem autenticacao, o YouTube
    passa a bloquear (403) QUALQUER video apos volume de trafego anonimo.
    Cookies de uma sessao logada real resolvem — deve ser o padrao."""
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)

    assert chamadas[0]["cookiesfrombrowser"] == ("chrome",)
    assert chamadas[0]["remote_components"] == ["ejs:github"]


def test_habilita_deno_e_node_como_runtime_js(monkeypatch, tmp_path):
    """O yt-dlp habilita SO' o deno por padrao, entao um node instalado e'
    reportado como "unavailable" e o desafio JS do YouTube nao resolve —
    exatamente o que travou a segunda maquina de coleta (Windows,
    2026-09-03), onde `node --version` respondia v24.20.0 e o yt-dlp dizia
    `JS runtimes: none`. Habilitar os dois faz a mesma configuracao valer
    nas duas maquinas, sem ajuste por maquina."""
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar("https://youtube.com/watch?v=abc123", tmp_path, baixar_legenda=False)

    assert chamadas[0]["js_runtimes"] == {
        "deno": {"path": None}, "node": {"path": None}}


def test_opcoes_de_runtime_js_sao_aceitas_pelo_yt_dlp_real():
    """O dublê de yt-dlp dos outros testes so' registra as opcoes, nao valida
    o formato delas — entao ele aprovou uma lista `["deno", "node"]` que o
    yt-dlp de verdade rejeita com ValueError (a CLI aceita lista e converte
    para dict antes da API Python; quem chama a API tem que passar o dict
    pronto). Esse teste fecha esse buraco: constroi um YoutubeDL real so'
    para submeter a constante a validacao da propria lib."""
    yt_dlp = pytest.importorskip("yt_dlp")

    yt_dlp.YoutubeDL({"quiet": True, "js_runtimes": dict(RUNTIMES_JS)}).close()


def test_navegador_cookies_none_desliga_cookies(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar(
        "https://youtube.com/watch?v=abc123", tmp_path,
        baixar_legenda=False, navegador_cookies=None,
    )

    assert "cookiesfrombrowser" not in chamadas[0]
    assert "remote_components" not in chamadas[0]
    assert "js_runtimes" not in chamadas[0]


def test_navegador_cookies_customizado(monkeypatch, tmp_path):
    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=lambda o, i: None)

    baixar(
        "https://youtube.com/watch?v=abc123", tmp_path,
        baixar_legenda=False, navegador_cookies="firefox",
    )

    assert chamadas[0]["cookiesfrombrowser"] == ("firefox",)


def test_cookies_aplicam_em_todas_as_tentativas_da_cadeia(monkeypatch, tmp_path):
    """cookiesfrombrowser e' defesa contra bloqueio por volume, ortogonal
    a legenda/formato — precisa estar presente em toda tentativa, nao so'
    na primeira."""

    def decidir(opcoes, indice):
        if opcoes.get("writesubtitles"):
            return _MSG_LEGENDA_429
        if opcoes.get("format") == FORMATO_PADRAO:
            return _MSG_FORMATO_403
        return None

    chamadas = _instalar_yt_dlp_falso(monkeypatch, tmp_path, decidir=decidir)

    baixar("https://youtube.com/watch?v=abc123", tmp_path)

    assert len(chamadas) == 3
    for c in chamadas:
        assert c["cookiesfrombrowser"] == ("chrome",)


@requer_ffmpeg
def test_caminho_de_legenda_tambem_gera_wav_para_o_player_de_revisao(
    tmp_path, video_original
):
    """site_revisao.py serve /item/{nome}/audio a partir de um .wav ao lado
    da fila — sem ele, o revisor nao consegue ouvir o trecho (regra 2).
    O caminho de legenda pulava esse passo (so' o caminho Whisper gerava
    o wav), entao todo item vindo de legenda ficava sem audio tocavel."""
    legenda = tmp_path / "abc123.pt.vtt"
    legenda.write_text(VTT_SIMPLES, encoding="utf-8")

    info = {
        "arquivo": video_original,
        "legenda": legenda,
        "legenda_tipo": "automatica",
        "legenda_idioma": "pt",
        "video_id": "abc123",
        "titulo": "titulo de teste",
        "canal": "@canal",
        "url": "https://youtube.com/watch?v=abc123",
        "publicado_em": None,
        "coletado_em": "2026-08-18T12:00:00+00:00",
    }

    saida = tmp_path / "saida"
    _processar_com_legenda(info, saida)

    assert (saida / "abc123.wav").exists()
