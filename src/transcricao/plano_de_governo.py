"""Extracao da URL do plano de governo a partir da resposta da API do TSE.

API nao documentada oficialmente (DivulgaCandContas). Pesquisa feita em
2026-08 a partir de fontes de terceiros:
  - https://github.com/augusto-herrmann/divulgacandcontas-doc
    (swagger.yaml com os endpoints de candidatura)
  - https://github.com/augusto-herrmann/eleicoes-2020-planos-de-governo
    (script real, `mayor_proposals.py`, que baixou planos de governo de
    prefeitos em 2020 e confirma o padrao abaixo em producao)

Padrao confirmado (script de 2020, prefeitos):
  GET  {BASE}/candidatura/listar/{ano}/{municipio}/{codigo_eleicao}/{cargo}/candidatos
  GET  {BASE}/candidatura/buscar/{ano}/{municipio}/{codigo_eleicao}/candidato/{id}
       -> resposta tem `arquivos: [{"codTipo": "...", "url": "...", "nome": "..."}]`
       -> plano de governo e' o arquivo com codTipo == "5"
       -> PDF final: "https://divulgacandcontas.tse.jus.br/" + url + nome

VERIFICADO ao vivo em 2026-08-03 contra a eleicao presidencial de 2022 (ja'
encerrada — nao mexe com dado de 2026, que ainda nao existe):
  - BASE precisa ser https, nao http (a porta 80 nem aceita conexao mais):
    "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"
  - `/candidatura/listar/2022/BR/544/1/candidatos` funciona e devolve
    candidatos reais a presidente (Ciro Gomes id 280001612393, Constituinte
    Eymael, etc.) — confirma `municipio="BR"` para candidatura nacional e
    `cargo=1` para Presidente (a resposta trouxe
    `"cargo":{"codigo":1,"nome":"Presidente"}` explicitamente).
  - `codigo_eleicao="544"` funcionou para 2022. Ainda ASSIM E' PRECISO
    achar o codigo equivalente de 2026 quando existir (nao adivinhar).
  - Os candidatos devolvidos por `listar` vem com `"arquivos": null` —
    essa chamada sozinha NAO da' a URL do plano de governo.

BLOQUEIO ENCONTRADO (2026-08-03), ainda sem solucao:
  - `/candidatura/buscar/.../candidato/{id}` — que deveria trazer o
    `arquivos` de um candidato especifico — devolve HTTP 200 com corpo
    VAZIO (0 bytes), de forma reproduzivel: testado com o `id` da listagem,
    com o numero de urna, com/sem cookie de sessao, com/sem header
    Referer, em varias tentativas espacadas. Parece que esse endpoint
    especifico do script de 2020 nao funciona mais (o portal atual pode
    ter trocado a rota de detalhe do candidato).
  - Hotlink direto ao PDF pelo padrao mais novo
    (`/candidaturas/oficial/2022/BR/BR/544/candidatos/{id}/{arquivo}.pdf`,
    achado via busca — URLs reais de propostas de 2022) tambem devolve
    HTTP 403 da propria infra do TSE, mesmo com Referer do dominio deles.
  - Antes de escrever a parte de I/O deste modulo, alguem precisa achar a
    rota de detalhe do candidato que o portal ATUAL usa de verdade —
    provavelmente inspecionando as chamadas de rede que o site faz num
    navegador de verdade (DevTools), nao só' testando as rotas do script
    antigo de 2020.

Este modulo so' implementa a parte pura (o que independe de rede): dado um
JSON de candidato ja' obtido, extrair a URL do PDF do plano de governo.
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
