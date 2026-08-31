"""Relato de erro enviado por leitor do site publico.

PURO: valida o formulario e monta titulo/corpo da issue do GitHub. O
envio de verdade (chamada HTTP pra API do GitHub) e I/O e fica em
`site_publico.py`, mesma separacao que o resto do projeto usa.

Por que issue do GitHub como destino (decisao do dono, 2026-08-30): o
site publico roda no Render (plano free), cujo disco e efemero — gravar
um arquivo local no deploy some no proximo restart/redeploy. O repo do
projeto ja existe no GitHub, entao vira o destino duravel mais simples
sem inventar infraestrutura nova (banco, servico de email).

Regra 1 do projeto vale aqui tambem: este modulo nao julga se o relato
procede, so' formata pra' um humano (o dono) avaliar depois.
"""

from __future__ import annotations

from typing import Any

TIPOS_PROBLEMA: dict[str, str] = {
    "transcricao": "Transcrição errada",
    "falante": "Falante errado / não é o candidato",
    "tema": "Tema errado",
    "outro": "Outro",
}

MAX_DESCRICAO = 2000
MAX_TEXTO_TRECHO = 500
MAX_CONTATO = 200


class RelatorioInvalido(ValueError):
    pass


class RelatorioSpam(RelatorioInvalido):
    """Honeypot preenchido — nunca chega no GitHub, mas nao avisa o remetente."""


def validar(dados: dict[str, Any]) -> None:
    """Levanta `RelatorioInvalido` (ou `RelatorioSpam`) se o formulario nao serve.

    Nao levanta nada se o relatorio e valido.
    """
    if (dados.get("site") or "").strip():  # honeypot: campo que humano nunca preenche
        raise RelatorioSpam("honeypot preenchido")
    if dados.get("tipo") not in TIPOS_PROBLEMA:
        raise RelatorioInvalido("tipo de problema invalido")
    descricao = (dados.get("descricao") or "").strip()
    if not descricao:
        raise RelatorioInvalido("descricao obrigatoria")
    if len(descricao) > MAX_DESCRICAO:
        raise RelatorioInvalido(f"descricao passa de {MAX_DESCRICAO} caracteres")
    if len(dados.get("contato") or "") > MAX_CONTATO:
        raise RelatorioInvalido(f"contato passa de {MAX_CONTATO} caracteres")


def montar_issue(dados: dict[str, Any]) -> tuple[str, str]:
    """(titulo, corpo) da issue do GitHub a partir do formulario ja validado."""
    tipo_rotulo = TIPOS_PROBLEMA.get(dados.get("tipo", ""), "Outro")
    candidato = (dados.get("candidato") or "").strip() or "não informado"
    texto = (dados.get("texto") or "").strip()[:MAX_TEXTO_TRECHO]
    url = (dados.get("url") or "").strip()
    timestamp = (dados.get("timestamp") or "").strip()
    descricao = (dados.get("descricao") or "").strip()
    contato = (dados.get("contato") or "").strip()

    titulo = f"[report] {tipo_rotulo} — {candidato}"

    linhas = [f"**Tipo:** {tipo_rotulo}", f"**Candidato:** {candidato}"]
    if url:
        linhas.append(f"**Fonte:** {url}")
    if timestamp:
        linhas.append(f"**Timestamp citado:** {timestamp}")
    if texto:
        linhas.append(f"**Trecho citado:**\n> {texto}")
    linhas.append(f"**Descrição do leitor:**\n{descricao}")
    if contato:
        linhas.append(f"**Contato informado:** {contato}")
    linhas.append("---\nEnviado pelo formulário público do site (`/reportar-erro`).")

    corpo = "\n\n".join(linhas)
    return titulo, corpo
