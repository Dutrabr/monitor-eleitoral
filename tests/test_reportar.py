import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from transcricao.reportar import (
    MAX_DESCRICAO,
    RelatorioInvalido,
    RelatorioSpam,
    montar_issue,
    validar,
)


def _dados(**overrides):
    base = {
        "tipo": "transcricao",
        "candidato": "lula",
        "url": "https://www.youtube.com/watch?v=abc123",
        "timestamp": "00:01:23",
        "texto": "trecho citado",
        "descricao": "a transcrição trocou uma palavra",
        "contato": "",
        "site": "",
    }
    base.update(overrides)
    return base


def test_relatorio_valido_nao_levanta():
    validar(_dados())  # nao deve levantar


def test_honeypot_preenchido_levanta_spam_especifico():
    with pytest.raises(RelatorioSpam):
        validar(_dados(site="http://spam.example"))


def test_tipo_invalido_rejeitado():
    with pytest.raises(RelatorioInvalido):
        validar(_dados(tipo="chute-qualquer"))


def test_descricao_vazia_rejeitada():
    with pytest.raises(RelatorioInvalido):
        validar(_dados(descricao="   "))


def test_descricao_longa_demais_rejeitada():
    with pytest.raises(RelatorioInvalido):
        validar(_dados(descricao="x" * (MAX_DESCRICAO + 1)))


def test_montar_issue_inclui_campos_principais():
    titulo, corpo = montar_issue(_dados())
    assert "lula" in titulo
    assert "Transcrição errada" in titulo
    assert "https://www.youtube.com/watch?v=abc123" in corpo
    assert "00:01:23" in corpo
    assert "trecho citado" in corpo
    assert "a transcrição trocou uma palavra" in corpo


def test_montar_issue_sem_candidato_nao_quebra():
    titulo, corpo = montar_issue(_dados(candidato=""))
    assert "não informado" in titulo


def test_montar_issue_trunca_texto_longo():
    dados = _dados(texto="p" * 900)
    _, corpo = montar_issue(dados)
    assert "p" * 501 not in corpo
    assert "p" * 500 in corpo


def test_montar_issue_nao_julga_conteudo_do_relato():
    """Regra 1: o modulo formata, nunca opina sobre se o relato procede."""
    _, corpo = montar_issue(_dados(descricao="isso é uma vergonha, mentira descarada"))
    palavras_proibidas = ["procede", "improcedente", "confirmado", "correto", "errado demais"]
    corpo_normalizado = corpo.lower()
    assert not any(p in corpo_normalizado for p in palavras_proibidas)
