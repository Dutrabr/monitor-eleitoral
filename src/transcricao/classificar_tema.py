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
# ARMADILHA, achada ao expandir a lista em 2026-08-25: a comparacao roda
# sobre texto sem acento e em minuscula, entao SIGLA DE PROGRAMA PODE
# COLIDIR COM PALAVRA COMUM. Dois casos reais medidos no corpus:
#   - "SUAS" (Sistema Unico de Assistencia Social) vira identico ao
#     pronome "suas" — 11 ocorrencias no corpus, TODAS o pronome.
#   - "porto" casa com "Porto Alegre"/"Porto Velho" (nome de cidade),
#     nao com o porto de infraestrutura. Por isso a lista usa "porto de".
# Antes de acrescentar sigla curta, conte as ocorrencias reais no corpus e
# LEIA os casos. Classificar errado poe a fala de alguem sob tema que ele
# nao discutiu, criando justaposicao enganosa contra o plano de governo.

PALAVRAS_POR_TEMA: dict[str, tuple[str, ...]] = {
    "saude": (
        "tratamento", "tratamentos", "saude mental", "medicamento", "medicamentos", "cirurgico", "paciente", "pacientes",
        "saude", "hospital", "hospitais", "posto de saude", "upa", "sus",
        "medico", "medicos", "medica", "enfermeiro", "enfermeira", "enfermagem",
        "vacina", "vacinacao", "remedio", "remedios", "farmacia",
        "consulta", "cirurgia", "cirurgias", "leito", "leitos", "ambulancia",
        "atendimento medico", "samu",
        "farmacia popular", "mais medicos", "santa casa", "vigilancia sanitaria",
        "saude da familia", "agente de saude", "cartao sus", "hemocentro",
        "maternidade", "pronto socorro", "atencao basica", "fila de espera",
        "transplante",
    ),
    "educacao": (
        "estudante", "estudantes", "estudantil", "bolsa de estudo", "educacional", "escolar",
        "educacao", "escola", "escolas", "professor", "professores",
        "professora", "professoras", "aluno", "alunos", "creche", "creches",
        "universidade", "universidades", "faculdade", "ensino",
        "alfabetizacao", "merenda", "sala de aula", "matricula",
        "prouni", "fies", "enem", "sisu",
        "fundeb", "pe de meia", "ideb", "instituto federal",
        "ensino medio", "ensino fundamental", "educacao infantil", "escola em tempo integral",
        "evasao escolar", "piso do magisterio", "transporte escolar", "ensino tecnico",
        "analfabetismo",
    ),
    "seguranca_publica": (
        "seguranca publica", "policia", "policial", "policiais",
        "violencia", "criminalidade", "crime", "crimes", "criminoso",
        "traficante", "trafico", "homicidio", "assalto", "roubo",
        "presidio", "penitenciaria", "delegacia", "bombeiro", "bombeiros",
        "lei maria da penha", "milicia", "milicias", "faccao",
        "faccoes", "videomonitoramento", "camera corporal", "guarda municipal",
        "socioeducativo", "feminicidio", "porte de arma",
    ),
    "economia_e_emprego": (
        "recuperacao judicial", "orcamento", "arrecadacao", "sonegacao", "credito", "financiamento",
        "emprego", "empregos", "desemprego", "trabalhador", "trabalhadores",
        "salario", "salarios", "renda", "imposto", "impostos", "tributo",
        "tributaria", "economia", "economico", "industria", "comercio",
        "empresa", "empresas", "empreendedor", "empresario", "inflacao",
        "juros", "carteira assinada",
        "sebrae", "senai", "qualificacao profissional", "primeiro emprego",
        "microcredito", "reforma tributaria", "fgts", "zona franca",
        "informalidade", "geracao de emprego", "vaga de trabalho", "custo de vida",
    ),
    "infraestrutura_e_mobilidade": (
        "duplicacao", "duplicar", "minha casa minha vida", "construcao civil", "casa propria", "pavimentar",
        "infraestrutura", "estrada", "estradas", "rodovia", "rodovias",
        "asfalto", "pavimentacao", "ponte", "saneamento", "esgoto",
        "agua encanada", "transporte", "onibus", "metro", "mobilidade",
        "obra", "obras", "moradia", "habitacao", "energia eletrica",
        "luz para todos", "novo pac", "casa verde e amarela", "brt",
        "vlt", "ferrovia", "ferroviario", "aeroporto",
        "tarifa zero", "passe livre", "porto de", "drenagem",
        "abastecimento de agua", "banheiro", "calcamento",
    ),
    "meio_ambiente_e_clima": (
        "meio ambiente", "ambiental", "desmatamento", "floresta", "florestas",
        "clima", "climatica", "sustentavel", "sustentabilidade",
        "poluicao", "reciclagem", "amazonia", "preservacao", "nascente",
        "energia limpa", "energia renovavel",
        "licenciamento ambiental", "credito de carbono", "cerrado", "caatinga",
        "pantanal", "cop30", "transicao energetica", "area de protecao",
        "queimada", "queimadas", "enchente", "enchentes",
        "aterro sanitario", "lixao",
    ),
    "agropecuaria_e_desenvolvimento_rural": (
        "agricultura", "agricultor", "agricultores", "agronegocio",
        "agropecuaria", "pecuaria", "rural", "produtor rural",
        "pequeno produtor", "lavoura", "safra", "plantio", "colheita",
        "assentamento", "extensao rural", "irrigacao", "pesca", "pescador",
        "pronaf", "garantia safra", "pnae", "embrapa",
        "credito rural", "incra", "reforma agraria", "agroecologia",
        "agricultura familiar", "silo", "armazenagem", "defensivo",
        "fertilizante", "rebanho",
    ),
    "assistencia_social_e_combate_a_pobreza": (
        "assistencial", "beneficio social", "inclusao social",
        "assistencia social", "pobreza", "miseria", "fome", "vulneravel",
        "vulnerabilidade", "cras", "creas", "bolsa familia", "auxilio",
        "cesta basica", "populacao de rua", "acolhimento",
        "bpc", "cadunico", "cadastro unico", "tarifa social",
        "vale gas", "auxilio gas", "seguranca alimentar", "restaurante popular",
        "cozinha comunitaria", "banco de alimentos", "extrema pobreza", "albergue",
    ),
    "ciencia_tecnologia_e_inovacao": (
        "ciencia", "cientifico", "tecnologia", "tecnologico", "inovacao",
        "pesquisa cientifica", "startup", "startups", "digitalizacao",
        "inteligencia artificial", "internet", "conectividade",
        "cnpq", "capes", "fapesp", "banda larga",
        "fibra otica", "inclusao digital", "parque tecnologico", "bolsa de pesquisa",
        "laboratorio",
    ),
    "cultura": (
        "cultura", "cultural", "artista", "artistas", "musica", "teatro",
        "cinema", "museu", "biblioteca", "patrimonio historico",
        "carnaval", "festival",
        "lei rouanet", "lei aldir blanc", "lei paulo gustavo", "ponto de cultura",
        "artesanato",
    ),
    "direitos_humanos_e_igualdade": (
        "direitos humanos", "igualdade", "racismo", "racial", "negro",
        "negra", "indigena", "indigenas", "quilombola", "lgbt",
        "mulher", "mulheres", "feminicidio", "machismo", "deficiencia",
        "acessibilidade", "preconceito", "discriminacao",
        "lgbtqia", "pessoa com deficiencia", "igualdade racial", "povos indigenas",
        "violencia domestica", "casa da mulher", "idoso", "idosos",
    ),
    "politica_externa_e_relacoes_internacionais": (
        "politica externa", "relacoes internacionais", "diplomacia",
        "diplomatico", "mercosul", "onu", "brics", "exportacao",
        "importacao", "acordo internacional", "estrangeiro",
    ),
    "reforma_politica_e_institucional": (
        "assembleia legislativa", "camara municipal", "mandato", "reeleicao", "improbidade",
        "reforma politica", "corrupcao", "transparencia", "fiscalizacao",
        "congresso", "senado", "camara dos deputados", "judiciario",
        "supremo", "stf", "eleicao", "eleicoes", "voto", "urna",
        "servidor publico", "servidores publicos",
        "tribunal de contas", "portal da transparencia", "concurso publico", "licitacao",
        "controladoria", "voto distrital", "clausula de barreira", "foro privilegiado",
    ),
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(ch for ch in sem_acento if unicodedata.category(ch) != "Mn")
    return sem_acento.casefold()


def classificar_sequencia(
    itens: list[dict], janela: int = 2, segundos_max: float = 20.0
) -> list[list[str]]:
    """Classifica uma sequencia de trechos do MESMO video, com contexto.

    Motivo: cada citacao e' uma linha de ~3 segundos de fala. Uma frase
    sobre saude vira varias citacoes, e so' uma delas costuma conter a
    palavra "saude" — as outras ficam orfas mesmo sendo o mesmo assunto.

    Regra de heranca, deliberadamente estreita para nao alastrar tema
    errado pelo video inteiro: um trecho sem tema proprio herda o tema do
    trecho anterior mais proximo que tenha um, desde que (a) esteja a no
    maximo `janela` posicoes de distancia e (b) a fala anterior tenha
    comecado ha' menos de `segundos_max`. Se qualquer das duas condicoes
    falhar, o trecho fica sem tema.

    Heranca so' anda para a frente (continuacao de fala). Trecho que ja'
    tem tema proprio nunca e' alterado.

    `itens` sao dicts com `texto` e, opcionalmente, `inicio` (segundos).
    """
    proprios = [sugerir_temas(it.get("texto") or "") for it in itens]
    resultado: list[list[str]] = []

    for i, temas in enumerate(proprios):
        if temas:
            resultado.append(temas)
            continue

        herdado: list[str] = []
        for passo in range(1, janela + 1):
            j = i - passo
            if j < 0:
                break
            if not proprios[j]:
                continue
            inicio_atual = itens[i].get("inicio")
            inicio_ancora = itens[j].get("inicio")
            if inicio_atual is not None and inicio_ancora is not None:
                if inicio_atual - inicio_ancora > segundos_max:
                    break
            herdado = list(proprios[j])
            break
        resultado.append(herdado)

    return resultado


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
