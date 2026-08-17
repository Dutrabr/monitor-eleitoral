import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.site_revisao import criar_app


def _montar_fila(tmp_path, falante_item0="SPEAKER_00"):
    dados = tmp_path / "transcricoes"
    dados.mkdir()
    fila = {
        "arquivo": "video.mp4",
        "hash_sha256_original": "abc123",
        "url": "https://exemplo/watch?v=1",
        "itens": [
            {
                "inicio": 0.0,
                "fim": 3.0,
                "timestamp": "00:00:00",
                "falante": falante_item0,
                "texto": "texto original",
                "status": "ok",
                "motivos": [],
            }
        ],
    }
    (dados / "video.fila_revisao.json").write_text(json.dumps(fila), encoding="utf-8")
    (dados / "video.wav").write_bytes(b"RIFF....WAVEfmt ")
    return dados


def test_confirmar_sem_falante_mantem_original_none(tmp_path):
    """Sem o campo falante preenchido, nao inventa atribuicao (regra 5)."""
    dados = _montar_fila(tmp_path, falante_item0=None)
    app = criar_app(dados)
    client = TestClient(app)

    resp = client.post(
        "/item/video/segmento/0",
        data={"decisao": "confirmado", "texto_final": "texto confirmado"},
    )
    assert resp.status_code == 200

    client.post("/item/video/publicar")
    publicado = json.loads((dados / "video.publicado.json").read_text())
    assert publicado["citacoes"][0]["falante"] is None


def test_confirmar_com_falante_preenche_gap_de_diarizacao(tmp_path):
    """Caso real: diarizacao nao atribuiu ninguem, humano confirma quem falou."""
    dados = _montar_fila(tmp_path, falante_item0=None)
    app = criar_app(dados)
    client = TestClient(app)

    resp = client.post(
        "/item/video/segmento/0",
        data={
            "decisao": "confirmado",
            "texto_final": "texto confirmado",
            "falante": "candidato_zema",
        },
    )
    assert resp.status_code == 200
    assert "candidato_zema" in resp.text

    client.post("/item/video/publicar")
    publicado = json.loads((dados / "video.publicado.json").read_text())
    assert publicado["citacoes"][0]["falante"] == "candidato_zema"


def test_falante_override_substitui_atribuicao_existente(tmp_path):
    dados = _montar_fila(tmp_path, falante_item0="SPEAKER_00")
    app = criar_app(dados)
    client = TestClient(app)

    client.post(
        "/item/video/segmento/0",
        data={
            "decisao": "confirmado",
            "texto_final": "texto confirmado",
            "falante": "candidato_correto",
        },
    )
    client.post("/item/video/publicar")
    publicado = json.loads((dados / "video.publicado.json").read_text())
    assert publicado["citacoes"][0]["falante"] == "candidato_correto"


def test_rejeitar_ignora_campo_falante(tmp_path):
    dados = _montar_fila(tmp_path, falante_item0=None)
    app = criar_app(dados)
    client = TestClient(app)

    resp = client.post(
        "/item/video/segmento/0",
        data={"decisao": "rejeitado", "falante": "candidato_zema"},
    )
    assert resp.status_code == 200
    decisoes = json.loads((dados / "video.decisoes.json").read_text())
    assert "falante_confirmado" not in decisoes["0"]


def test_reconfirmar_com_texto_e_falante_corrigidos(tmp_path):
    """Reproduz o fluxo real: confirma, depois corrige texto e falante numa segunda submissao."""
    dados = _montar_fila(tmp_path, falante_item0=None)
    app = criar_app(dados)
    client = TestClient(app)

    client.post(
        "/item/video/segmento/0",
        data={"decisao": "confirmado", "texto_final": "primeira tentativa"},
    )
    client.post(
        "/item/video/segmento/0",
        data={
            "decisao": "confirmado",
            "texto_final": "texto corrigido de verdade",
            "falante": "candidato_zema",
        },
    )
    client.post("/item/video/publicar")
    publicado = json.loads((dados / "video.publicado.json").read_text())
    assert publicado["citacoes"][0]["texto"] == "texto corrigido de verdade"
    assert publicado["citacoes"][0]["falante"] == "candidato_zema"
