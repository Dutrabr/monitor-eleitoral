import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao import revisao
from transcricao.revisao import Decisao


def _fila(n=2):
    return {
        "arquivo": "video.mp4",
        "hash_sha256_original": "abc123",
        "url": "https://exemplo/watch?v=1",
        "itens": [
            {
                "inicio": float(i),
                "fim": float(i + 1),
                "timestamp": f"00:00:0{i}",
                "falante": "SPEAKER_00",
                "texto": f"texto {i}",
                "status": "ok",
                "motivos": [],
            }
            for i in range(n)
        ],
    }


def test_registrar_decisao_nao_muta_original():
    original = {}
    novas = revisao.registrar_decisao(original, 0, Decisao.CONFIRMADO, texto_final="x")
    assert original == {}
    assert novas["0"]["decisao"] == "confirmado"
    assert novas["0"]["texto_final"] == "x"


def test_rejeitado_nao_carrega_texto_final():
    novas = revisao.registrar_decisao({}, 0, Decisao.REJEITADO)
    assert "texto_final" not in novas["0"]


def test_resumo_conta_pendentes():
    fila = _fila(3)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="a")
    r = revisao.resumo(fila, decisoes)
    assert r == {"total": 3, "confirmados": 1, "rejeitados": 0, "pendentes": 2}


def test_pronto_para_publicacao_falso_com_pendente():
    fila = _fila(2)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="a")
    assert revisao.pronto_para_publicacao(fila, decisoes) is False


def test_pronto_para_publicacao_verdadeiro_quando_tudo_decidido():
    fila = _fila(2)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="a")
    decisoes = revisao.registrar_decisao(decisoes, 1, Decisao.REJEITADO)
    assert revisao.pronto_para_publicacao(fila, decisoes) is True


def test_montar_publicacao_falha_com_pendente():
    fila = _fila(1)
    with pytest.raises(ValueError):
        revisao.montar_publicacao(fila, {})


def test_montar_publicacao_so_inclui_confirmados():
    fila = _fila(2)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="texto corrigido")
    decisoes = revisao.registrar_decisao(decisoes, 1, Decisao.REJEITADO)
    pub = revisao.montar_publicacao(fila, decisoes)
    assert len(pub["citacoes"]) == 1
    assert pub["citacoes"][0]["texto"] == "texto corrigido"
    assert pub["hash_sha256_original"] == "abc123"


def test_montar_publicacao_usa_texto_original_se_sem_correcao():
    fila = _fila(1)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final=None)
    pub = revisao.montar_publicacao(fila, decisoes)
    assert pub["citacoes"][0]["texto"] == "texto 0"


def test_montar_publicacao_sem_itens_citaveis_da_lista_vazia():
    fila = _fila(0)
    pub = revisao.montar_publicacao(fila, {})
    assert pub["citacoes"] == []


def test_registrar_decisao_aceita_temas_validos():
    novas = revisao.registrar_decisao(
        {}, 0, Decisao.CONFIRMADO, texto_final="x",
        temas=["educacao", "saude"],
    )
    assert novas["0"]["temas"] == ["educacao", "saude"]


def test_registrar_decisao_rejeita_tema_invalido():
    with pytest.raises(ValueError):
        revisao.registrar_decisao(
            {}, 0, Decisao.CONFIRMADO, texto_final="x", temas=["tema_que_nao_existe"]
        )


def test_registrar_decisao_sem_temas_da_lista_vazia():
    novas = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="x")
    assert novas["0"]["temas"] == []


def test_rejeitado_nao_carrega_temas():
    novas = revisao.registrar_decisao({}, 0, Decisao.REJEITADO)
    assert "temas" not in novas["0"]


def test_montar_publicacao_inclui_temas_da_citacao():
    fila = _fila(1)
    decisoes = revisao.registrar_decisao(
        {}, 0, Decisao.CONFIRMADO, texto_final="a", temas=["saude"]
    )
    pub = revisao.montar_publicacao(fila, decisoes)
    assert pub["citacoes"][0]["temas"] == ["saude"]


def test_montar_publicacao_temas_vazio_quando_nao_marcado():
    fila = _fila(1)
    decisoes = revisao.registrar_decisao({}, 0, Decisao.CONFIRMADO, texto_final="a")
    pub = revisao.montar_publicacao(fila, decisoes)
    assert pub["citacoes"][0]["temas"] == []
