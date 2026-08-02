"""Extracao da URL do plano de governo a partir da resposta da API do TSE.

API nao documentada oficialmente (DivulgaCandContas). Pesquisa feita em
2026-08 a partir de fontes de terceiros:
  - https://github.com/augusto-herrmann/divulgacandcontas-doc
    (swagger.yaml com os endpoints de candidatura)
  - https://github.com/augusto-herrmann/eleicoes-2020-planos-de-governo
    (script real, `mayor_proposals.py`, que baixou planos de governo de
    prefeitos em 2020 e confirma o padrao abaixo em producao)

Padrao confirmado (script de 2020, prefeitos):
  BASE = "http://divulgacandcontas.tse.jus.br/divulga/rest/v1"
  GET  {BASE}/candidatura/listar/{ano}/{municipio}/{codigo_eleicao}/{cargo}/candidatos
  GET  {BASE}/candidatura/buscar/{ano}/{municipio}/{codigo_eleicao}/candidato/{id}
       -> resposta tem `arquivos: [{"codTipo": "...", "url": "...", "nome": "..."}]`
       -> plano de governo e' o arquivo com codTipo == "5"
       -> PDF final: "https://divulgacandcontas.tse.jus.br/" + url + nome

NAO VERIFICADO ainda, precisa de confirmacao com dado real antes de usar:
  - `codigo_eleicao`: e' um id numerico por eleicao (ex: "2030402020" foi o
    de municipais 2020), NAO e' o ano. O de 2026 (geral) ainda nao existe
    publicamente enquanto o registro de candidatura nao fecha (15/08/2026).
  - `cargo` (POSITION_CODE): o script usa "11" para prefeito. Presidente
    deveria ser "1" pela convencao usual do TSE, mas isso nao foi
    confirmado contra a API real.
  - `municipio`: candidatura de prefeito e' naturalmente por municipio.
    Presidente e' candidatura nacional — nao esta confirmado se a API
    exige um municipio "coringa" (ex: capital do estado, ou um codigo
    nacional especial) para listar candidatos a presidente, ou se ha
    outro endpoint. Isso precisa ser descoberto testando contra uma
    eleicao presidencial ja' encerrada (2022) antes de apontar para 2026.

Este modulo so' implementa a parte pura (o que independe de rede): dado um
JSON de candidato ja' obtido, extrair a URL do PDF do plano de governo. A
parte de I/O (descobrir codigo_eleicao/cargo/municipio certos e buscar via
HTTP) fica para quando houver dado real pra testar contra a API.
"""

from __future__ import annotations

from typing import Any

TIPO_ARQUIVO_PLANO_DE_GOVERNO = "5"
BASE_ARQUIVOS = "https://divulgacandcontas.tse.jus.br/"


def extrair_url_proposta(candidato: dict[str, Any]) -> str | None:
    """Acha a URL do PDF do plano de governo na resposta de um candidato.

    `candidato` e' o JSON de `/candidatura/buscar/.../candidato/{id}`.
    Devolve None se nao houver arquivo do tipo plano de governo (codTipo
    "5") — isso e' normal, nem todo candidato anexa o documento.
    """
    for arquivo in candidato.get("arquivos", []):
        if arquivo.get("codTipo") == TIPO_ARQUIVO_PLANO_DE_GOVERNO:
            url = arquivo.get("url")
            nome = arquivo.get("nome")
            if url and nome:
                return f"{BASE_ARQUIVOS}{url}{nome}"
            return None
    return None
