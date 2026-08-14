import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.site_publico import criar_app


def _montar_projeto(tmp_path):
    candidatos = tmp_path / "candidatos"
    dados = tmp_path / "transcricoes"
    planos = tmp_path / "planos_de_governo"
    candidatos.mkdir()
    dados.mkdir()
    planos.mkdir()

    (candidatos / "fulano.json").write_text(
        json.dumps(
            {
                "slug": "fulano",
                "nome": "Fulano de Tal",
                "partido": "Partido A",
                "cargo": "Presidente",
                "falante_id": "candidato_fulano",
                "plano_de_governo": "/plano/fulano",
            }
        ),
        encoding="utf-8",
    )
    (planos / "fulano.pdf").write_bytes(b"%PDF-1.4 conteudo falso")
    return candidatos, dados, planos


def test_plano_de_governo_serve_pdf_local(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/plano/fulano")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-1.4 conteudo falso"


def test_plano_de_governo_404_quando_nao_existe(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/plano/nao-existe")
    assert resp.status_code == 404


def test_pasta_planos_padrao_e_irma_de_candidatos(tmp_path):
    """Sem --planos explicito, assume dados/planos_de_governo ao lado de dados/candidatos."""
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados)  # sem pasta_planos
    client = TestClient(app)

    resp = client.get("/plano/fulano")
    assert resp.status_code == 200


def test_candidato_lista_citacoes_confirmadas(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "citacoes": [
                    {
                        "inicio": 1.0,
                        "fim": 2.0,
                        "timestamp": "00:00:01",
                        "falante": "candidato_fulano",
                        "texto": "frase confirmada",
                        "temas": ["educacao"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/candidato/fulano")
    assert resp.status_code == 200
    assert "frase confirmada" in resp.text
    assert "Educação" in resp.text


def test_candidato_inexistente_404(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/candidato/ninguem")
    assert resp.status_code == 404
