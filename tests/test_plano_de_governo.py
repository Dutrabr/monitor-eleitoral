import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.plano_de_governo import extrair_id_proposta, url_download_proposta


def test_extrai_id_quando_ha_plano_de_governo():
    candidato = {
        "arquivos": [
            {"idArquivo": 111, "codTipo": "14", "nome": "certidao.pdf"},
            {"idArquivo": 222, "codTipo": "5", "nome": "plano de governo.pdf"},
        ]
    }
    assert extrair_id_proposta(candidato) == 222


def test_none_quando_sem_arquivo_do_tipo_plano():
    candidato = {"arquivos": [{"idArquivo": 111, "codTipo": "14", "nome": "certidao.pdf"}]}
    assert extrair_id_proposta(candidato) is None


def test_none_quando_sem_arquivos():
    assert extrair_id_proposta({}) is None
    assert extrair_id_proposta({"arquivos": []}) is None


def test_url_download_usa_id_arquivo():
    assert url_download_proposta(50016847977) == (
        "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/doc/50016847977"
    )
