"""Site publico: evidencia lado a lado, nunca veredito.

Regra invioravel (CLAUDE.md, regra 1): sem nota, sem ranking, sem "vale a
pena votar". Este site mostra o plano de governo (link para o PDF
original, baixado por `plano_de_governo.py`, mais trechos curados
manualmente por tema — ver `candidatos.carregar_plano_curado`) e as
citacoes publicamente confirmadas (ja passaram por revisao humana
obrigatoria — ver `site_revisao.py`), agrupadas por tema. Nao ha
cruzamento automatico entre "prometeu" e "disse" — mesmo o pareamento por
tema do lado do plano e' curadoria manual, nunca inferido por algoritmo.

Rodar: python3 -m transcricao.site_publico --candidatos dados/candidatos --dados dados/transcricoes
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from .candidatos import (
    TEMA_SEM_CLASSIFICACAO,
    UF_NOMES,
    agrupar_por_tema,
    carregar_candidatos,
    carregar_candidatos_por_uf,
    carregar_plano_curado,
    citacoes_do_candidato,
    citacoes_para_linhas,
    url_com_timestamp,
)
from .site_revisao import ROTULOS_TEMA, TEMAS_DISPONIVEIS

TEMPLATES_DIR = Path(__file__).parent / "templates_publico"

CAMPOS_EXPORT = [
    "candidato_slug", "candidato_nome", "partido", "temas",
    "texto", "timestamp", "url_origem", "publicado_em",
]

MIN_COMPARAR = 2
MAX_COMPARAR = 4


def criar_app(
    pasta_candidatos: Path,
    pasta_dados: Path,
    pasta_planos: Path | None = None,
    pasta_planos_curados: Path | None = None,
    pasta_candidatos_governador: Path | None = None,
    pasta_planos_governador: Path | None = None,
    pasta_planos_curados_governador: Path | None = None,
) -> FastAPI:
    pasta_candidatos = Path(pasta_candidatos)
    pasta_dados = Path(pasta_dados)
    pasta_planos = Path(pasta_planos) if pasta_planos else pasta_candidatos.parent / "planos_de_governo"
    pasta_planos_curados = (
        Path(pasta_planos_curados) if pasta_planos_curados
        else pasta_candidatos.parent / "planos_curados"
    )
    pasta_candidatos_governador = (
        Path(pasta_candidatos_governador) if pasta_candidatos_governador
        else pasta_candidatos.parent / "candidatos_governador"
    )
    pasta_planos_governador = (
        Path(pasta_planos_governador) if pasta_planos_governador
        else pasta_candidatos.parent / "planos_de_governo_governador"
    )
    pasta_planos_curados_governador = (
        Path(pasta_planos_curados_governador) if pasta_planos_curados_governador
        else pasta_candidatos.parent / "planos_curados_governador"
    )
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI(title="Monitor Eleitoral")

    def _candidatos() -> list[dict[str, Any]]:
        if not pasta_candidatos.exists():
            return []
        return carregar_candidatos(pasta_candidatos)

    def _candidatos_por_numero() -> list[dict[str, Any]]:
        """Ordem de exibicao publica: numero de urna (regra 3, simetria total)."""
        return sorted(_candidatos(), key=lambda c: c.get("numero") or 0)

    def _candidatos_governador() -> list[dict[str, Any]]:
        if not pasta_candidatos_governador.exists():
            return []
        return carregar_candidatos_por_uf(pasta_candidatos_governador)

    def _candidatos_governador_uf(uf: str) -> list[dict[str, Any]]:
        """Mesma ordem de exibicao publica dos demais cargos: numero de urna."""
        return sorted(
            (c for c in _candidatos_governador() if c["uf"] == uf),
            key=lambda c: c.get("numero") or 0,
        )

    def _publicados() -> list[dict[str, Any]]:
        if not pasta_dados.exists():
            return []
        return [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(pasta_dados.rglob("*.publicado.json"))
        ]

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, tema: str | None = None):
        temas_navegaveis = [
            (valor, rotulo) for valor, rotulo in TEMAS_DISPONIVEIS
            if valor != TEMA_SEM_CLASSIFICACAO
        ]
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "candidatos": _candidatos_por_numero(),
                "temas": temas_navegaveis,
                "tema_selecionado": tema,
            },
        )

    @app.get("/candidato/{slug}", response_class=HTMLResponse)
    def candidato(request: Request, slug: str, tema: str | None = None):
        candidatos = {c["slug"]: c for c in _candidatos()}
        c = candidatos.get(slug)
        if not c:
            raise HTTPException(404, f"candidato '{slug}' nao encontrado")

        citacoes = citacoes_do_candidato(c["falante_id"], _publicados())
        for cit in citacoes:
            cit["url_com_timestamp"] = url_com_timestamp(
                cit.get("url_origem"), cit["inicio"]
            )
        grupos = agrupar_por_tema(citacoes)
        plano_curado = carregar_plano_curado(pasta_planos_curados, slug)

        temas_presentes = set(grupos.keys()) | set(plano_curado.keys())
        temas_ordenados = sorted(temas_presentes, key=lambda t: ROTULOS_TEMA.get(t, t))
        tema_foco = tema if tema in temas_ordenados else None

        timeline = sorted(
            (cit for cit in citacoes if cit.get("publicado_em")),
            key=lambda cit: cit["publicado_em"],
        )

        rotulo_tema_foco = ROTULOS_TEMA.get(tema_foco, tema_foco) if tema_foco else None
        if rotulo_tema_foco:
            og_titulo = f"{c['nome']} sobre {rotulo_tema_foco} — Monitor Eleitoral"
            og_descricao = (
                f"O que {c['nome']} registrou no plano de governo sobre "
                f"{rotulo_tema_foco.lower()}, comparado ao que disse nas redes sociais."
            )
        else:
            og_titulo = f"{c['nome']} — Monitor Eleitoral"
            og_descricao = (
                f"Compare o que {c['nome']} registrou no plano de governo com o "
                "que disse publicamente, tema por tema."
            )

        return templates.TemplateResponse(
            request,
            "candidato.html",
            {
                "candidato": c,
                "grupos": grupos,
                "plano_curado": plano_curado,
                "temas_ordenados": temas_ordenados,
                "tema_foco": tema_foco,
                "tema_sem_classificacao": TEMA_SEM_CLASSIFICACAO,
                "rotulos_tema": ROTULOS_TEMA,
                "total_citacoes": len(citacoes),
                "timeline": timeline,
                "og_titulo": og_titulo,
                "og_descricao": og_descricao,
                "voltar_url": "/",
                "voltar_label": "Todos os candidatos",
            },
        )

    @app.get("/governador", response_class=HTMLResponse)
    def governador_index(request: Request):
        contagem_por_uf: dict[str, int] = {}
        for c in _candidatos_governador():
            contagem_por_uf[c["uf"]] = contagem_por_uf.get(c["uf"], 0) + 1
        estados = sorted(
            (
                {"uf": uf, "nome": nome, "total": contagem_por_uf.get(uf, 0)}
                for uf, nome in UF_NOMES.items()
            ),
            key=lambda e: e["nome"],
        )
        return templates.TemplateResponse(
            request,
            "governador_index.html",
            {"estados": estados, "total_candidatos": sum(contagem_por_uf.values())},
        )

    @app.get("/governador/{uf}", response_class=HTMLResponse)
    def governador_estado(request: Request, uf: str):
        uf = uf.upper()
        if uf not in UF_NOMES:
            raise HTTPException(404, f"UF '{uf}' invalida")
        return templates.TemplateResponse(
            request,
            "governador_estado.html",
            {
                "uf": uf,
                "nome_estado": UF_NOMES[uf],
                "candidatos": _candidatos_governador_uf(uf),
            },
        )

    @app.get("/governador/{uf}/{slug}", response_class=HTMLResponse)
    def governador_candidato(request: Request, uf: str, slug: str, tema: str | None = None):
        uf = uf.upper()
        nome_estado = UF_NOMES.get(uf, uf)
        candidatos = {c["slug"]: c for c in _candidatos_governador_uf(uf)}
        c = candidatos.get(slug)
        if not c:
            raise HTTPException(404, f"candidato '{slug}' nao encontrado em {uf}")

        citacoes = citacoes_do_candidato(c["falante_id"], _publicados())
        for cit in citacoes:
            cit["url_com_timestamp"] = url_com_timestamp(
                cit.get("url_origem"), cit["inicio"]
            )
        grupos = agrupar_por_tema(citacoes)
        plano_curado = carregar_plano_curado(pasta_planos_curados_governador, slug)

        temas_presentes = set(grupos.keys()) | set(plano_curado.keys())
        temas_ordenados = sorted(temas_presentes, key=lambda t: ROTULOS_TEMA.get(t, t))
        tema_foco = tema if tema in temas_ordenados else None

        timeline = sorted(
            (cit for cit in citacoes if cit.get("publicado_em")),
            key=lambda cit: cit["publicado_em"],
        )

        rotulo_tema_foco = ROTULOS_TEMA.get(tema_foco, tema_foco) if tema_foco else None
        if rotulo_tema_foco:
            og_titulo = f"{c['nome']} sobre {rotulo_tema_foco} — Monitor Eleitoral"
            og_descricao = (
                f"O que {c['nome']} (Governador, {nome_estado}) registrou no plano de "
                f"governo sobre {rotulo_tema_foco.lower()}, comparado ao que disse "
                "nas redes sociais."
            )
        else:
            og_titulo = f"{c['nome']} — Monitor Eleitoral"
            og_descricao = (
                f"Compare o que {c['nome']}, candidato a Governador de {nome_estado}, "
                "registrou no plano de governo com o que disse publicamente, tema por tema."
            )

        return templates.TemplateResponse(
            request,
            "candidato.html",
            {
                "candidato": c,
                "grupos": grupos,
                "plano_curado": plano_curado,
                "temas_ordenados": temas_ordenados,
                "tema_foco": tema_foco,
                "tema_sem_classificacao": TEMA_SEM_CLASSIFICACAO,
                "rotulos_tema": ROTULOS_TEMA,
                "total_citacoes": len(citacoes),
                "timeline": timeline,
                "og_titulo": og_titulo,
                "og_descricao": og_descricao,
                "voltar_url": f"/governador/{uf}",
                "voltar_label": f"Candidatos a Governador — {nome_estado}",
            },
        )

    @app.get("/governador/{uf}/{slug}/plano")
    def governador_plano_de_governo(uf: str, slug: str):
        uf = uf.upper()
        caminho = pasta_planos_governador / uf / f"{slug}.pdf"
        if not caminho.exists():
            raise HTTPException(404, f"plano de governo de '{slug}' ({uf}) nao encontrado")
        return FileResponse(caminho, media_type="application/pdf")

    @app.get("/comparar", response_class=HTMLResponse)
    def comparar(
        request: Request,
        tema: str | None = None,
        candidatos: list[str] | None = Query(None),
    ):
        """Modo comparar: mesmo tema, 2 a 4 candidatos lado a lado.

        Sem totalizacao, sem placar — cada coluna e' so' a mesma evidencia que
        `/candidato/{slug}` ja mostra, filtrada pro tema escolhido. Ordem das
        colunas e' sempre por numero de urna (regra 3), nunca pela ordem em
        que os slugs vieram na URL — assim duas pessoas comparando os mesmos
        candidatos sempre veem a mesma ordem.
        """
        temas_navegaveis = [
            (valor, rotulo) for valor, rotulo in TEMAS_DISPONIVEIS
            if valor != TEMA_SEM_CLASSIFICACAO
        ]
        todos_candidatos = _candidatos_por_numero()

        slugs_pedidos: list[str] = []
        for item in candidatos or []:
            slugs_pedidos.extend(s.strip() for s in item.split(",") if s.strip())

        contexto_base = {
            "temas": temas_navegaveis,
            "candidatos": todos_candidatos,
            "tema_escolhido": tema,
            "slugs_escolhidos": slugs_pedidos,
        }

        if not tema or not slugs_pedidos:
            return templates.TemplateResponse(
                request, "comparar.html", {**contexto_base, "modo": "selecionar", "erro": None}
            )

        mapa_candidatos = {c["slug"]: c for c in todos_candidatos}
        slugs_unicos = list(dict.fromkeys(slugs_pedidos))
        invalidos = [s for s in slugs_unicos if s not in mapa_candidatos]
        temas_validos = dict(temas_navegaveis)

        erro = None
        if invalidos:
            erro = f"candidato(s) não encontrado(s): {', '.join(invalidos)}"
        elif tema not in temas_validos:
            erro = f"tema '{tema}' inválido"
        elif not (MIN_COMPARAR <= len(slugs_unicos) <= MAX_COMPARAR):
            erro = (
                f"escolha entre {MIN_COMPARAR} e {MAX_COMPARAR} candidatos "
                f"(você escolheu {len(slugs_unicos)})"
            )

        if erro:
            return templates.TemplateResponse(
                request, "comparar.html", {**contexto_base, "modo": "selecionar", "erro": erro}
            )

        selecionados = sorted(
            (mapa_candidatos[s] for s in slugs_unicos), key=lambda c: c.get("numero") or 0
        )
        publicados = _publicados()
        colunas = []
        for c in selecionados:
            citacoes = citacoes_do_candidato(c["falante_id"], publicados)
            for cit in citacoes:
                cit["url_com_timestamp"] = url_com_timestamp(cit.get("url_origem"), cit["inicio"])
            plano_curado = carregar_plano_curado(pasta_planos_curados, c["slug"])
            colunas.append(
                {
                    "candidato": c,
                    "citacoes": agrupar_por_tema(citacoes).get(tema, []),
                    "plano": plano_curado.get(tema),
                }
            )

        rotulo_tema = temas_validos[tema]
        nomes = " × ".join(c["nome"] for c in selecionados)

        return templates.TemplateResponse(
            request,
            "comparar.html",
            {
                **contexto_base,
                "slugs_escolhidos": [c["slug"] for c in selecionados],
                "modo": "resultado",
                "erro": None,
                "rotulo_tema": rotulo_tema,
                "colunas": colunas,
                "og_titulo": f"{rotulo_tema}: {nomes} — Monitor Eleitoral",
                "og_descricao": (
                    f"Compare o que {nomes} registraram no plano de governo e "
                    f"disseram publicamente sobre {rotulo_tema.lower()}."
                ),
            },
        )

    @app.get("/plano/{slug}")
    def plano_de_governo(slug: str):
        """Serve o PDF baixado localmente — nunca linka direto pro TSE.

        Cadeia de custodia (regra 6 do CLAUDE.md): o hash do arquivo como
        baixado ja foi registrado no momento da coleta (ver MANIFESTO.json
        ao lado dos PDFs); servir do nosso proprio storage garante que o
        link nao quebra se o portal do TSE mudar de endpoint de novo.
        """
        caminho = pasta_planos / f"{slug}.pdf"
        if not caminho.exists():
            raise HTTPException(404, f"plano de governo de '{slug}' nao encontrado")
        return FileResponse(caminho, media_type="application/pdf")

    @app.get("/metodologia", response_class=HTMLResponse)
    def metodologia(request: Request):
        return templates.TemplateResponse(request, "metodologia.html", {})

    @app.get("/dados/citacoes.json")
    def dados_citacoes_json():
        return citacoes_para_linhas(_candidatos() + _candidatos_governador(), _publicados())

    @app.get("/dados/citacoes.csv")
    def dados_citacoes_csv():
        linhas = citacoes_para_linhas(_candidatos() + _candidatos_governador(), _publicados())
        buffer = io.StringIO()
        escritor = csv.DictWriter(buffer, fieldnames=CAMPOS_EXPORT)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({**linha, "temas": "|".join(linha["temas"])})
        return Response(content=buffer.getvalue(), media_type="text/csv")

    return app


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    ap = argparse.ArgumentParser(description="Site publico do Monitor Eleitoral.")
    ap.add_argument("--candidatos", type=Path, default=Path("dados/candidatos"))
    ap.add_argument("--dados", type=Path, default=Path("dados/transcricoes"))
    ap.add_argument("--planos", type=Path, default=Path("dados/planos_de_governo"))
    ap.add_argument("--planos-curados", type=Path, default=Path("dados/planos_curados"))
    ap.add_argument("--candidatos-governador", type=Path, default=Path("dados/candidatos_governador"))
    ap.add_argument("--planos-governador", type=Path, default=Path("dados/planos_de_governo_governador"))
    ap.add_argument(
        "--planos-curados-governador", type=Path, default=Path("dados/planos_curados_governador")
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8001)
    args = ap.parse_args(argv)

    app = criar_app(
        args.candidatos,
        args.dados,
        args.planos,
        args.planos_curados,
        args.candidatos_governador,
        args.planos_governador,
        args.planos_curados_governador,
    )
    uvicorn.run(app, host=args.host, port=args.porta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
