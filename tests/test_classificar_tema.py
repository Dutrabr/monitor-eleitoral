"""Testes das armadilhas de vocabulario do classificador de tema.

Os testes basicos vivem em test_candidatos.py; aqui ficam os casos que
existem porque um erro real quase entrou (ver comentario no topo de
classificar_tema.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from transcricao.classificar_tema import sugerir_temas


def test_sigla_que_colide_com_palavra_comum_nao_entra():
    """'SUAS' (Sistema Unico de Assistencia Social) vira identico ao
    pronome 'suas' quando o texto e' normalizado sem acento/maiuscula.
    No corpus real as 11 ocorrencias eram TODAS o pronome — incluir a
    sigla classificaria 11 falas sob um tema que ninguem discutiu."""
    assert sugerir_temas("Defendeu suas ideias, grande articulador") == []
    assert sugerir_temas("pagar suas despesas no longo prazo") == []


def test_porto_so_conta_como_infraestrutura_com_complemento():
    """'Porto Alegre' e 'Porto Velho' sao nomes de cidade, nao porto."""
    assert "infraestrutura_e_mobilidade" not in sugerir_temas(
        "em um trecho fundamental entre Porto Alegre e Uruguaiana"
    )
    assert "infraestrutura_e_mobilidade" in sugerir_temas("o Porto de Rio Grande")


def test_programas_com_nome_proprio_sao_sinal_forte():
    """Nome proprio de programa publico e' de alta precisao: ninguem diz
    'ProUni' sem estar falando de educacao."""
    assert sugerir_temas("ampliar o ProUni") == ["educacao"]
    assert sugerir_temas("o Pronaf para o pequeno produtor") == [
        "agropecuaria_e_desenvolvimento_rural"
    ]
    assert sugerir_temas("a Lei Maria da Penha precisa ser aplicada") == [
        "seguranca_publica"
    ]
