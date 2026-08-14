"""Site publico: evidencia lado a lado, nunca veredito.

Regra invioravel (CLAUDE.md, regra 1): sem nota, sem ranking, sem "vale a
pena votar". Este site mostra o plano de governo (link para o PDF
original, baixado por `plano_de_governo.py`) e as citacoes publicamente
confirmadas (ja passaram por revisao humana obrigatoria — ver
`site_revisao.py`), agrupadas por tema. Nao ha cruzamento automatico entre
"prometeu" e "disse" — a leitura e' de quem le.

Rodar: python3 -m transcricao.site_publico --candidatos dados/candidatos --dados dados/transcricoes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from .candidatos import (
    agrupar_por_tema,
    carregar_candidatos,
    citacoes_do_candidato,
    url_com_timestamp,
)
from .site_revisao import ROTULOS_TEMA

TEMPLATES_DIR = Path(__file__).parent / "templates_publico"


def criar_app(
    pasta_candidatos: Path, pasta_dados: Path, pasta_planos: Path | None = None
) -> FastAPI:
    pasta_candidatos = Path(pasta_candidatos)
    pasta_dados = Path(pasta_dados)
    pasta_planos = Path(pasta_planos) if pasta_planos else pasta_candidatos.parent / "planos_de_governo"
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI(title="Monitor Eleitoral")

    def _candidatos() -> list[dict[str, Any]]:
        if not pasta_candidatos.exists():
            return []
        return carregar_candidatos(pasta_candidatos)

    def _publicados() -> list[dict[str, Any]]:
        if not pasta_dados.exists():
            return []
        return [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(pasta_dados.rglob("*.publicado.json"))
        ]

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(
            request, "index.html", {"candidatos": _candidatos()}
        )

    @app.get("/candidato/{slug}", response_class=HTMLResponse)
    def candidato(request: Request, slug: str):
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
        temas_ordenados = sorted(grupos.keys(), key=lambda t: ROTULOS_TEMA.get(t, t))

        return templates.TemplateResponse(
            request,
            "candidato.html",
            {
                "candidato": c,
                "grupos": grupos,
                "temas_ordenados": temas_ordenados,
                "rotulos_tema": ROTULOS_TEMA,
                "total_citacoes": len(citacoes),
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

    return app


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    ap = argparse.ArgumentParser(description="Site publico do Monitor Eleitoral.")
    ap.add_argument("--candidatos", type=Path, default=Path("dados/candidatos"))
    ap.add_argument("--dados", type=Path, default=Path("dados/transcricoes"))
    ap.add_argument("--planos", type=Path, default=Path("dados/planos_de_governo"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8001)
    args = ap.parse_args(argv)

    app = criar_app(args.candidatos, args.dados, args.planos)
    uvicorn.run(app, host=args.host, port=args.porta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
