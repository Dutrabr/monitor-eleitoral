import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.candidatos import (
    TEMA_SEM_CLASSIFICACAO,
    agrupar_por_tema,
    carregar_candidatos,
    citacoes_do_candidato,
    url_com_timestamp,
)


def test_carregar_candidatos_ordena_por_nome(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps({"slug": "b", "nome": "Beltrana"}))
    (tmp_path / "a.json").write_text(json.dumps({"slug": "a", "nome": "Alfredo"}))
    candidatos = carregar_candidatos(tmp_path)
    assert [c["nome"] for c in candidatos] == ["Alfredo", "Beltrana"]


def test_citacoes_do_candidato_filtra_por_falante():
    publicados = [
        {
            "url": "https://exemplo/1",
            "citacoes": [
                {"falante": "candidato_a", "texto": "x"},
                {"falante": "candidato_b", "texto": "y"},
            ],
        }
    ]
    citacoes = citacoes_do_candidato("candidato_a", publicados)
    assert len(citacoes) == 1
    assert citacoes[0]["texto"] == "x"
    assert citacoes[0]["url_origem"] == "https://exemplo/1"


def test_citacoes_do_candidato_agrega_varios_arquivos():
    publicados = [
        {"url": "u1", "citacoes": [{"falante": "candidato_a", "texto": "x"}]},
        {"url": "u2", "citacoes": [{"falante": "candidato_a", "texto": "z"}]},
    ]
    citacoes = citacoes_do_candidato("candidato_a", publicados)
    assert len(citacoes) == 2


def test_agrupar_por_tema_basico():
    citacoes = [
        {"texto": "a", "temas": ["educacao"]},
        {"texto": "b", "temas": ["saude"]},
    ]
    grupos = agrupar_por_tema(citacoes)
    assert grupos["educacao"] == [citacoes[0]]
    assert grupos["saude"] == [citacoes[1]]


def test_agrupar_por_tema_multi_tema_aparece_nos_dois_grupos():
    citacoes = [{"texto": "a", "temas": ["educacao", "saude"]}]
    grupos = agrupar_por_tema(citacoes)
    assert grupos["educacao"] == citacoes
    assert grupos["saude"] == citacoes


def test_agrupar_por_tema_sem_tema_vai_para_grupo_explicito():
    citacoes = [{"texto": "a", "temas": []}]
    grupos = agrupar_por_tema(citacoes)
    assert grupos[TEMA_SEM_CLASSIFICACAO] == citacoes


def test_url_com_timestamp_youtube_sem_query():
    assert url_com_timestamp("https://www.youtube.com/watch?v=abc", 65.0) == (
        "https://www.youtube.com/watch?v=abc&t=65s"
    )


def test_url_com_timestamp_youtu_be():
    assert url_com_timestamp("https://youtu.be/abc", 10.0) == "https://youtu.be/abc?t=10s"


def test_url_com_timestamp_fonte_desconhecida_nao_altera():
    url = "https://www.instagram.com/reel/abc/"
    assert url_com_timestamp(url, 10.0) == url


def test_url_com_timestamp_sem_url():
    assert url_com_timestamp(None, 10.0) is None
