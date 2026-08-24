"""Classificacao automatica de tema por palavra-chave — PURO, testado.

Contexto e limite desta decisao (2026-08-24, escolha explicita do dono):
ate' aqui, tema era marcado SO' por pessoa, no mesmo passo da revisao
humana (`site_revisao.py`). Quando a auto-aprovacao entrou (2026-08-19),
ela passou a confirmar texto sem passar pela revisao — e, junto, sem
marcar tema. Resultado: as 971 citacoes publicadas nasceram todas sem
tema, e o site inteiro, que e' organizado por tema, ficava com o lado das
falas invisivel.

O que isto **e'**: classificacao topica ("esta frase fala de saude").
O que isto **nao e'**: juizo sobre o candidato. Nao ranqueia, nao pontua,
nao afirma que a fala cumpre ou contradiz o plano — so' diz sob qual
assunto ela deve aparecer. Por isso nao esbarra na regra 1 nem na
Resolucao TSE 23.610/2019 art. 9º-B.

**Risco real assumido:** classificar errado coloca a fala de alguem sob
um tema que ele nao discutiu, criando justaposicao enganosa contra o
plano. Para conter isso, a regra aqui e' deliberadamente conservadora:

  - exige palavra-chave especifica do tema, nao palavra generica;
  - casa por limite de palavra, nunca por substring solta (evita que
    "assistencia" case dentro de outra palavra, ou "arte" dentro de
    "quarteirao");
  - na duvida devolve `[]` — sem tema e' melhor que tema errado, mesmo
    princípio de "nao consta" x "nao verificado" no resto do projeto.

Trecho transcrito e' curto (uma linha de fala), entao a maioria vai cair
em `[]` mesmo. Isso e' esperado, nao falha.
"""

from __future__ import annotations

import re
import unicodedata

# Palavras-chave por tema. Cada termo e' especifico o bastante para que a
# presenca dele indique o assunto sem precisar de contexto. Termos
# ambiguos ficaram de fora de proposito (ex: "programa", "familia",
# "investimento" — aparecem em qualquer tema).
PALAVRAS_POR_TEMA: dict[str, tuple[str, ...]] = {
    "saude": (
        "saude", "hospital", "hospitais", "posto de saude", "upa", "sus",
        "medico", "medicos", "medica", "enfermeiro", "enfermeira", "enfermagem",
        "vacina", "vacinacao", "remedio", "remedios", "farmacia",
        "consulta", "cirurgia", "cirurgias", "leito", "leitos", "ambulancia",
        "atendimento medico", "samu",
    ),
    "educacao": (
        "educacao", "escola", "escolas", "professor", "professores",
        "professora", "professoras", "aluno", "alunos", "creche", "creches",
        "universidade", "universidades", "faculdade", "ensino",
        "alfabetizacao", "merenda", "sala de aula", "matricula",
    ),
    "seguranca_publica": (
        "seguranca publica", "policia", "policial", "policiais",
        "violencia", "criminalidade", "crime", "crimes", "criminoso",
        "traficante", "trafico", "homicidio", "assalto", "roubo",
        "presidio", "penitenciaria", "delegacia", "bombeiro", "bombeiros",
    ),
    "economia_e_emprego": (
        "emprego", "empregos", "desemprego", "trabalhador", "trabalhadores",
        "salario", "salarios", "renda", "imposto", "impostos", "tributo",
        "tributaria", "economia", "economico", "industria", "comercio",
        "empresa", "empresas", "empreendedor", "empresario", "inflacao",
        "juros", "carteira assinada",
    ),
    "infraestrutura_e_mobilidade": (
        "infraestrutura", "estrada", "estradas", "rodovia", "rodovias",
        "asfalto", "pavimentacao", "ponte", "saneamento", "esgoto",
        "agua encanada", "transporte", "onibus", "metro", "mobilidade",
        "obra", "obras", "moradia", "habitacao", "energia eletrica",
    ),
    "meio_ambiente_e_clima": (
        "meio ambiente", "ambiental", "desmatamento", "floresta", "florestas",
        "clima", "climatica", "sustentavel", "sustentabilidade",
        "poluicao", "reciclagem", "amazonia", "preservacao", "nascente",
        "energia limpa", "energia renovavel",
    ),
    "agropecuaria_e_desenvolvimento_rural": (
        "agricultura", "agricultor", "agricultores", "agronegocio",
        "agropecuaria", "pecuaria", "rural", "produtor rural",
        "pequeno produtor", "lavoura", "safra", "plantio", "colheita",
        "assentamento", "extensao rural", "irrigacao", "pesca", "pescador",
    ),
    "assistencia_social_e_combate_a_pobreza": (
        "assistencia social", "pobreza", "miseria", "fome", "vulneravel",
        "vulnerabilidade", "cras", "creas", "bolsa familia", "auxilio",
        "cesta basica", "populacao de rua", "acolhimento",
    ),
    "ciencia_tecnologia_e_inovacao": (
        "ciencia", "cientifico", "tecnologia", "tecnologico", "inovacao",
        "pesquisa cientifica", "startup", "startups", "digitalizacao",
        "inteligencia artificial", "internet", "conectividade",
    ),
    "cultura": (
        "cultura", "cultural", "artista", "artistas", "musica", "teatro",
        "cinema", "museu", "biblioteca", "patrimonio historico",
        "carnaval", "festival",
    ),
    "direitos_humanos_e_igualdade": (
        "direitos humanos", "igualdade", "racismo", "racial", "negro",
        "negra", "indigena", "indigenas", "quilombola", "lgbt",
        "mulher", "mulheres", "feminicidio", "machismo", "deficiencia",
        "acessibilidade", "preconceito", "discriminacao",
    ),
    "politica_externa_e_relacoes_internacionais": (
        "politica externa", "relacoes internacionais", "diplomacia",
        "diplomatico", "mercosul", "onu", "brics", "exportacao",
        "importacao", "acordo internacional", "estrangeiro",
    ),
    "reforma_politica_e_institucional": (
        "reforma politica", "corrupcao", "transparencia", "fiscalizacao",
        "congresso", "senado", "camara dos deputados", "judiciario",
        "supremo", "stf", "eleicao", "eleicoes", "voto", "urna",
        "servidor publico", "servidores publicos",
    ),
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(ch for ch in sem_acento if unicodedata.category(ch) != "Mn")
    return sem_acento.casefold()


def sugerir_temas(texto: str) -> list[str]:
    """Devolve os temas cujas palavras-chave aparecem em `texto`.

    Casa por limite de palavra (`\\b`), entao "arte" nao casa dentro de
    "quarteirao" e "sus" nao casa dentro de "sustentavel". Devolve lista
    ordenada alfabeticamente, ou `[]` quando nada casa com confianca —
    e' o caso mais comum, e e' o comportamento desejado.
    """
    alvo = _normalizar(texto or "")
    if not alvo.strip():
        return []

    achados = []
    for tema, palavras in PALAVRAS_POR_TEMA.items():
        for palavra in palavras:
            if re.search(rf"\b{re.escape(palavra)}\b", alvo):
                achados.append(tema)
                break
    return sorted(achados)
