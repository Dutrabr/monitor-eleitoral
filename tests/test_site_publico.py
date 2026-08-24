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


def _adicionar_segundo_candidato(candidatos, numero_fulano=10, numero_beltrano=5):
    (candidatos / "fulano.json").write_text(
        json.dumps(
            {
                "slug": "fulano",
                "nome": "Fulano de Tal",
                "partido": "Partido A",
                "cargo": "Presidente",
                "numero": numero_fulano,
                "falante_id": "candidato_fulano",
                "plano_de_governo": "/plano/fulano",
            }
        ),
        encoding="utf-8",
    )
    (candidatos / "beltrano.json").write_text(
        json.dumps(
            {
                "slug": "beltrano",
                "nome": "Beltrano da Silva",
                "partido": "Partido B",
                "cargo": "Presidente",
                "numero": numero_beltrano,
                "falante_id": "candidato_beltrano",
                "plano_de_governo": "/plano/beltrano",
            }
        ),
        encoding="utf-8",
    )


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


def test_candidato_sem_curadoria_de_plano_nao_quebra(tmp_path):
    """Regressao zero pros candidatos ja publicados sem dados/planos_curados/*.json."""
    candidatos, dados, planos = _montar_projeto(tmp_path)
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "publicado_em": "2026-08-01T00:00:00+00:00",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_fulano", "texto": "frase confirmada",
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
    assert "Tema não verificado no plano ainda" in resp.text
    assert "frase confirmada" in resp.text


def test_candidato_com_plano_curado_consta(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    planos_curados = planos.parent / "planos_curados"
    planos_curados.mkdir()
    (planos_curados / "fulano.json").write_text(
        json.dumps(
            {"educacao": {"status": "consta", "trechos": [{"texto": "trecho do plano", "pagina": 4}]}}
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos, planos_curados)
    client = TestClient(app)

    resp = client.get("/candidato/fulano")
    assert resp.status_code == 200
    assert "Consta no plano" in resp.text
    assert "trecho do plano" in resp.text


def test_candidato_com_plano_curado_nao_consta(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    planos_curados = planos.parent / "planos_curados"
    planos_curados.mkdir()
    (planos_curados / "fulano.json").write_text(
        json.dumps({"educacao": {"status": "nao_consta"}}), encoding="utf-8"
    )
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_fulano", "texto": "frase confirmada",
                        "temas": ["educacao"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos, planos_curados)
    client = TestClient(app)

    resp = client.get("/candidato/fulano")
    assert resp.status_code == 200
    assert "Não consta no plano" in resp.text


def test_candidato_com_tema_na_query_marca_foco(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_fulano", "texto": "frase de saude",
                        "temas": ["saude"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/candidato/fulano?tema=saude")
    assert resp.status_code == 200
    assert "sobre Saúde" in resp.text


def test_metodologia_acessivel(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/metodologia")
    assert resp.status_code == 200
    assert "não faz" in resp.text.lower()


def test_perguntas_acessivel(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/perguntas")
    assert resp.status_code == 200
    assert "Perguntas frequentes" in resp.text


def test_perguntas_reafirma_que_nao_ha_veredito(tmp_path):
    """A pagina de duvidas nao pode abrir brecha pra veredito (regra 1).

    Se alguem reescrever esse conteudo e tirar a recusa explicita de dar
    nota/ranking/recomendacao, o teste quebra — a promessa e' parte do
    produto, nao so' texto decorativo.
    """
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    texto = client.get("/perguntas").text.lower()
    assert "nunca veredito" in texto
    assert "não recomenda voto" in texto


def test_export_json_inclui_citacoes(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "publicado_em": "2026-08-01T00:00:00+00:00",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_fulano", "texto": "frase confirmada",
                        "temas": ["educacao"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/dados/citacoes.json")
    assert resp.status_code == 200
    linhas = resp.json()
    assert len(linhas) == 1
    assert linhas[0]["candidato_slug"] == "fulano"
    assert linhas[0]["temas"] == ["educacao"]


def test_export_csv_tem_cabecalho_e_junta_temas(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_fulano", "texto": "frase confirmada",
                        "temas": ["educacao", "saude"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/dados/citacoes.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "candidato_slug" in resp.text
    assert "educacao|saude" in resp.text


def test_comparar_sem_parametros_mostra_formulario(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/comparar")
    assert resp.status_code == 200
    assert "Comparar candidatos" in resp.text


def test_comparar_com_um_candidato_pede_pelo_menos_dois(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/comparar", params={"tema": "saude", "candidatos": "fulano"})
    assert resp.status_code == 200
    assert "entre 2 e 4" in resp.text


def test_comparar_candidato_inexistente_da_erro(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get(
        "/comparar", params={"tema": "saude", "candidatos": ["fulano", "ninguem"]}
    )
    assert resp.status_code == 200
    assert "não encontrado" in resp.text


def test_comparar_ordena_por_numero_de_urna_independente_da_url(tmp_path):
    """fulano tem numero 10, beltrano tem numero 5 — na URL fulano vem primeiro,
    mas beltrano (numero menor) deve aparecer primeiro no resultado."""
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos, numero_fulano=10, numero_beltrano=5)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get(
        "/comparar", params={"tema": "saude", "candidatos": ["fulano", "beltrano"]}
    )
    assert resp.status_code == 200
    assert resp.text.index("Beltrano da Silva") < resp.text.index("Fulano de Tal")


def test_comparar_mostra_citacoes_e_plano_do_tema_escolhido(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos)
    planos_curados = planos.parent / "planos_curados"
    planos_curados.mkdir()
    (planos_curados / "fulano.json").write_text(
        json.dumps({"saude": {"status": "consta", "trechos": [{"texto": "trecho de saude", "pagina": 3}]}}),
        encoding="utf-8",
    )
    (dados / "item1.publicado.json").write_text(
        json.dumps(
            {
                "url": "https://exemplo/1",
                "citacoes": [
                    {
                        "inicio": 1.0, "fim": 2.0, "timestamp": "00:00:01",
                        "falante": "candidato_beltrano", "texto": "fala de saude do beltrano",
                        "temas": ["saude"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = criar_app(candidatos, dados, planos, planos_curados)
    client = TestClient(app)

    resp = client.get(
        "/comparar",
        params={"tema": "saude", "candidatos": ["fulano", "beltrano"]},
    )
    assert resp.status_code == 200
    assert "trecho de saude" in resp.text
    assert "fala de saude do beltrano" in resp.text
    assert "Consta no plano" in resp.text


def test_comparar_aceita_candidatos_em_lista_separada_por_virgula(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos)
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get("/comparar", params={"tema": "saude", "candidatos": "fulano,beltrano"})
    assert resp.status_code == 200
    assert "Fulano de Tal" in resp.text
    assert "Beltrano da Silva" in resp.text


def test_comparar_mais_de_quatro_candidatos_da_erro(tmp_path):
    candidatos, dados, planos = _montar_projeto(tmp_path)
    _adicionar_segundo_candidato(candidatos)
    for slug, numero in [("c3", 3), ("c4", 4), ("c5", 6)]:
        (candidatos / f"{slug}.json").write_text(
            json.dumps(
                {
                    "slug": slug, "nome": slug, "partido": "P", "numero": numero,
                    "falante_id": f"candidato_{slug}",
                }
            ),
            encoding="utf-8",
        )
    app = criar_app(candidatos, dados, planos)
    client = TestClient(app)

    resp = client.get(
        "/comparar",
        params={"tema": "saude", "candidatos": ["fulano", "beltrano", "c3", "c4", "c5"]},
    )
    assert resp.status_code == 200
    assert "entre 2 e 4" in resp.text
