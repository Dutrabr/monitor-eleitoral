import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from transcricao.candidatos import (
    TEMA_SEM_CLASSIFICACAO,
    agrupar_por_tema,
    buscar_citacoes,
    destacar,
    carregar_candidatos,
    carregar_patrocinadores,
    carregar_plano_curado,
    citacoes_do_candidato,
    citacoes_para_linhas,
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


def test_citacoes_do_candidato_propaga_data_de_publicacao():
    publicados = [
        {
            "url": "https://exemplo/1",
            "publicado_em": "2026-08-01T00:00:00+00:00",
            "citacoes": [{"falante": "candidato_a", "texto": "x"}],
        }
    ]
    citacoes = citacoes_do_candidato("candidato_a", publicados)
    assert citacoes[0]["publicado_em"] == "2026-08-01T00:00:00+00:00"


def test_carregar_plano_curado_sem_arquivo_devolve_vazio(tmp_path):
    assert carregar_plano_curado(tmp_path, "ninguem") == {}


def test_carregar_plano_curado_le_status_e_trechos(tmp_path):
    (tmp_path / "fulano.json").write_text(
        json.dumps(
            {
                "saude": {
                    "status": "consta",
                    "trechos": [{"texto": "trecho do plano", "pagina": 12}],
                },
                "educacao": {"status": "nao_consta"},
            }
        ),
        encoding="utf-8",
    )
    dados = carregar_plano_curado(tmp_path, "fulano")
    assert dados["saude"]["status"] == "consta"
    assert dados["saude"]["trechos"][0]["pagina"] == 12
    assert dados["educacao"]["status"] == "nao_consta"


def test_carregar_plano_curado_status_invalido_levanta_erro(tmp_path):
    (tmp_path / "fulano.json").write_text(
        json.dumps({"saude": {"status": "mentira"}}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="status invalido"):
        carregar_plano_curado(tmp_path, "fulano")


def test_carregar_patrocinadores_sem_arquivo_devolve_vazio(tmp_path):
    assert carregar_patrocinadores(tmp_path / "patrocinadores.json") == []


def test_carregar_patrocinadores_le_lista(tmp_path):
    caminho = tmp_path / "patrocinadores.json"
    caminho.write_text(
        json.dumps([{"nome": "Empresa X", "url": "https://x.example", "logo_arquivo": "x.svg"}]),
        encoding="utf-8",
    )
    patrocinadores = carregar_patrocinadores(caminho)
    assert patrocinadores == [
        {"nome": "Empresa X", "url": "https://x.example", "logo_arquivo": "x.svg"}
    ]


def test_carregar_patrocinadores_campo_faltando_levanta_erro(tmp_path):
    caminho = tmp_path / "patrocinadores.json"
    caminho.write_text(json.dumps([{"nome": "Empresa X"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="logo_arquivo"):
        carregar_patrocinadores(caminho)


def test_citacoes_para_linhas_achata_por_candidato():
    candidatos = [
        {"slug": "fulano", "nome": "Fulano", "partido": "P", "falante_id": "candidato_fulano"},
    ]
    publicados = [
        {
            "url": "u1",
            "publicado_em": "2026-08-01T00:00:00+00:00",
            "citacoes": [
                {
                    "falante": "candidato_fulano",
                    "texto": "x",
                    "temas": ["saude", "educacao"],
                    "timestamp": "00:00:01",
                }
            ],
        }
    ]
    linhas = citacoes_para_linhas(candidatos, publicados)
    assert len(linhas) == 1
    assert linhas[0]["candidato_slug"] == "fulano"
    assert linhas[0]["temas"] == ["saude", "educacao"]
    assert linhas[0]["publicado_em"] == "2026-08-01T00:00:00+00:00"


def _pub(falante, textos):
    return {
        "url": "https://youtube.com/watch?v=x",
        "publicado_em": "2026-08-01T00:00:00Z",
        "citacoes": [{"falante": falante, "texto": t, "inicio": 0} for t in textos],
    }


def test_busca_ignora_acento_e_caixa():
    candidatos = [{"slug": "a", "nome": "A", "numero": 10, "falante_id": "cand_a"}]
    pubs = [_pub("cand_a", ["Vamos falar de SAÚDE pública"])]
    achado = buscar_citacoes(candidatos, pubs, "saude")
    assert len(achado) == 1
    assert len(achado[0]["citacoes"]) == 1


def test_busca_ordena_por_numero_de_urna_nunca_por_relevancia():
    """Regra 3: resultado nunca pode sugerir ranking entre candidatos."""
    candidatos = [
        {"slug": "c", "nome": "C", "numero": 44, "falante_id": "cand_c"},
        {"slug": "a", "nome": "A", "numero": 13, "falante_id": "cand_a"},
    ]
    # 'c' tem mais ocorrencias — mesmo assim deve vir depois, por ter numero maior
    pubs = [_pub("cand_c", ["saude", "saude", "saude"]), _pub("cand_a", ["saude"])]
    achado = buscar_citacoes(candidatos, pubs, "saude")
    assert [g["candidato"]["numero"] for g in achado] == [13, 44]


def test_busca_vazia_nao_devolve_tudo():
    candidatos = [{"slug": "a", "nome": "A", "numero": 10, "falante_id": "cand_a"}]
    pubs = [_pub("cand_a", ["qualquer coisa"])]
    assert buscar_citacoes(candidatos, pubs, "   ") == []


def test_destacar_preserva_o_texto_original_acentuado():
    """Busca sem acento casa, mas o trecho exibido mantem a grafia real.

    Depende de a normalizacao preservar o comprimento da string (cada
    caractere acentuado vira um caractere base). Se isso quebrar, os
    indices desalinham e o destaque corta a palavra no lugar errado.
    """
    pedacos = destacar("Falo de saúde aqui", "saude")
    assert [p["texto"] for p in pedacos] == ["Falo de ", "saúde", " aqui"]
    assert [p["marcado"] for p in pedacos] == [False, True, False]


def test_destacar_marca_todas_as_ocorrencias():
    pedacos = destacar("saude e mais saude", "saude")
    assert sum(1 for p in pedacos if p["marcado"]) == 2


def test_classificar_tema_acha_assunto_obvio():
    from transcricao.classificar_tema import sugerir_temas
    assert sugerir_temas("vamos construir mais uma escola") == ["educacao"]
    assert "saude" in sugerir_temas("o hospital precisa de mais leitos")


def test_classificar_tema_prefere_vazio_a_errado():
    """Na duvida, sem tema — mesmo principio de 'nao consta' x 'nao verificado'."""
    from transcricao.classificar_tema import sugerir_temas
    assert sugerir_temas("bom dia a todos, obrigado por virem") == []
    assert sugerir_temas("") == []
    assert sugerir_temas("   ") == []


def test_classificar_tema_casa_por_palavra_inteira():
    """'sus' nao pode casar dentro de 'sustentavel'."""
    from transcricao.classificar_tema import sugerir_temas
    assert "saude" not in sugerir_temas("um projeto sustentavel para o estado")
    assert "saude" in sugerir_temas("o sus precisa de mais verba")


def test_classificar_tema_multiplo():
    from transcricao.classificar_tema import sugerir_temas
    temas = sugerir_temas("investir em escola e em hospital")
    assert temas == ["educacao", "saude"]


def test_classificar_sequencia_herda_de_fala_contigua():
    """Continuacao de fala herda o tema do trecho anterior proximo."""
    from transcricao.classificar_tema import classificar_sequencia
    seq = [
        {"texto": "vamos falar de saude", "inicio": 0},
        {"texto": "e da qualidade do atendimento", "inicio": 3},
    ]
    assert classificar_sequencia(seq) == [["saude"], ["saude"]]


def test_classificar_sequencia_nao_herda_apos_intervalo_longo():
    """Fala distante no tempo nao herda — evita alastrar tema pelo video."""
    from transcricao.classificar_tema import classificar_sequencia
    seq = [
        {"texto": "vamos falar de saude", "inicio": 0},
        {"texto": "mudando de assunto agora", "inicio": 120},
    ]
    assert classificar_sequencia(seq) == [["saude"], []]


def test_classificar_sequencia_nao_sobrescreve_tema_proprio():
    from transcricao.classificar_tema import classificar_sequencia
    seq = [
        {"texto": "falando de saude", "inicio": 0},
        {"texto": "agora sobre escola", "inicio": 3},
    ]
    assert classificar_sequencia(seq) == [["saude"], ["educacao"]]


def test_citacoes_do_candidato_separa_material_de_campanha():
    """Locutor/jingle no canal oficial nao pode virar fala do candidato.

    E' o erro que a regra 5 existe para impedir, e que aconteceu de
    verdade: 5 videos narrados em terceira pessoa foram publicados como
    palavra do candidato antes desta separacao existir.
    """
    publicados = [
        {"url": "u1", "citacoes": [{"falante": "cand_a", "texto": "eu farei X"}]},
        {
            "url": "u2",
            "tipo_material": "material_de_campanha",
            "citacoes": [{"falante": "cand_a", "texto": "ele fez X"}],
        },
    ]
    falas = citacoes_do_candidato("cand_a", publicados)
    assert [c["texto"] for c in falas] == ["eu farei X"]

    campanha = citacoes_do_candidato("cand_a", publicados, tipo="material_de_campanha")
    assert [c["texto"] for c in campanha] == ["ele fez X"]


def test_citacoes_do_candidato_sem_tipo_conta_como_fala():
    """Arquivo antigo, sem o campo, continua sendo tratado como fala."""
    publicados = [{"url": "u", "citacoes": [{"falante": "cand_a", "texto": "oi"}]}]
    assert len(citacoes_do_candidato("cand_a", publicados)) == 1
