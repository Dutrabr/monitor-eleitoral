import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.plano_de_governo import extrair_url_proposta


def test_extrai_url_quando_ha_plano_de_governo():
    candidato = {
        "arquivos": [
            {"codTipo": "1", "url": "dados/2026/DF/1/1/", "nome": "foto123.jpg"},
            {"codTipo": "5", "url": "dados/2026/DF/1/1/", "nome": "proposta_governo999.pdf"},
        ]
    }
    assert extrair_url_proposta(candidato) == (
        "https://divulgacandcontas.tse.jus.br/dados/2026/DF/1/1/proposta_governo999.pdf"
    )


def test_none_quando_sem_arquivo_do_tipo_plano():
    candidato = {"arquivos": [{"codTipo": "1", "url": "x/", "nome": "foto.jpg"}]}
    assert extrair_url_proposta(candidato) is None


def test_none_quando_sem_arquivos():
    assert extrair_url_proposta({}) is None
    assert extrair_url_proposta({"arquivos": []}) is None


def test_none_quando_arquivo_do_tipo_mas_sem_url_ou_nome():
    candidato = {"arquivos": [{"codTipo": "5", "url": None, "nome": None}]}
    assert extrair_url_proposta(candidato) is None
