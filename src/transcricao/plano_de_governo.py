"""Busca e download do plano de governo via API do DivulgaCandContas.

API nao documentada oficialmente. Confirmado AO VIVO em 2026-08-03 contra
dado real de 2026 (ACM Neto, candidato a Governador da Bahia — eleicao
em andamento, registro de presidente ainda nao existe):

  GET {BASE_API}/candidatura/buscar/{ano}/{uf}/{codigo_eleicao}/candidato/{id}
      -> JSON do candidato, com `arquivos: [{idArquivo, nome, codTipo, ...}]`
      -> plano de governo e' o item com codTipo == "5"

  GET {BASE_ARQUIVO}/{idArquivo}
      -> bytes do PDF

As DUAS chamadas exigem o header `Referer: https://divulgacandcontas.tse.jus.br/divulga/`.
Sem ele, `buscar` devolve HTTP 200 com corpo vazio (nao um erro claro) e o
download do arquivo devolve HTTP 403. Nao precisa de cookie de sessao nem
de navegador real — so' o header. Essa e' a causa raiz do "bloqueio" que
uma sessao anterior deste projeto documentou (curl sem Referer): o
endpoint nunca esteve quebrado, faltava so' esse header.

O campo `arquivos[].url` + `arquivos[].nome` concatenados (o jeito que o
script de 2020 baixava, augusto-herrmann/eleicoes-2020-planos-de-governo)
NAO funciona mais — devolve 403 mesmo com Referer e mesmo dentro de uma
sessao de navegador logada. Use sempre `idArquivo` + `/rest/arquivo/doc/`.

`codigo_eleicao` de 2026 (eleicao geral): "20322002026" — visto direto na
URL do site ao navegar pela consulta de candidatos, sem precisar adivinhar.
`municipio`/`uf` para candidatura nacional a Presidente deve ser "BR" (nao
verificado ainda com candidato real, porque presidente nao registrou —
mas confirmado que `cargo=1`/`municipio="BR"` no endpoint `listar`
devolvem estrutura correta para a corrida presidencial contra dado de
2022 ja' encerrado).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

BASE_API = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"
BASE_ARQUIVO = "https://divulgacandcontas.tse.jus.br/divulga/rest/arquivo/doc"
REFERER = "https://divulgacandcontas.tse.jus.br/divulga/"
TIPO_ARQUIVO_PLANO_DE_GOVERNO = "5"


class ColetaIndisponivel(RuntimeError):
    pass


def extrair_id_proposta(candidato: dict[str, Any]) -> int | None:
    """Acha o idArquivo do plano de governo na resposta de um candidato.

    `candidato` e' o JSON de `/candidatura/buscar/.../candidato/{id}`.
    Devolve None se nao houver arquivo do tipo plano de governo (codTipo
    "5") — normal para cargos legislativos, que nao exigem o documento.
    """
    for arquivo in candidato.get("arquivos", []):
        if arquivo.get("codTipo") == TIPO_ARQUIVO_PLANO_DE_GOVERNO:
            return arquivo.get("idArquivo")
    return None


def url_download_proposta(id_arquivo: int) -> str:
    return f"{BASE_ARQUIVO}/{id_arquivo}"


def buscar_candidato(
    ano: int, uf_ou_municipio: str, codigo_eleicao: str, candidato_id: int | str
) -> dict[str, Any]:
    """Busca o JSON completo de um candidato na API do DivulgaCandContas."""
    try:
        import requests
    except ImportError as e:
        raise ColetaIndisponivel("requests nao instalado (pip install requests)") from e

    url = (
        f"{BASE_API}/candidatura/buscar/{ano}/{uf_ou_municipio}/"
        f"{codigo_eleicao}/candidato/{candidato_id}"
    )
    resp = requests.get(url, headers={"Referer": REFERER}, timeout=30)
    resp.raise_for_status()
    if not resp.content:
        raise ColetaIndisponivel(
            f"resposta vazia de {url} — provavelmente falta o header Referer "
            "ou o candidato/eleicao nao existe"
        )
    return resp.json()


def baixar_proposta(candidato: dict[str, Any], destino: Path) -> Path | None:
    """Baixa o PDF do plano de governo, se o candidato tiver um.

    Devolve None (sem baixar nada) se nao houver plano de governo anexado
    — isso e' normal, nao e' erro.
    """
    id_arquivo = extrair_id_proposta(candidato)
    if id_arquivo is None:
        return None

    try:
        import requests
    except ImportError as e:
        raise ColetaIndisponivel("requests nao instalado (pip install requests)") from e

    resp = requests.get(
        url_download_proposta(id_arquivo), headers={"Referer": REFERER}, timeout=60
    )
    resp.raise_for_status()

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    return destino
