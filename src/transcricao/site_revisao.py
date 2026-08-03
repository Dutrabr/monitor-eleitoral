"""Site de revisao humana: fila -> conferencia -> publicacao.

Ferramenta interna, nao o site publico. Nenhuma decisao e' automatica: o
reviewer ouve o trecho exato (o wav de 16 kHz que a pipeline ja gera fica
ao lado da fila — e' o que este site serve para o player) e confirma ou
rejeita cada item antes de qualquer publicacao. `publicar` recusa itens
com pendencia (ver `revisao.montar_publicacao`).

Rodar: python3 -m transcricao.site_revisao --dados dados/transcricoes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from . import proveniencia
from .modelos import Tema
from .revisao import (
    Decisao,
    montar_publicacao,
    pronto_para_publicacao,
    registrar_decisao,
    resumo,
)

TEMPLATES_DIR = Path(__file__).parent / "templates_revisao"

ROTULOS_TEMA = {
    Tema.AGROPECUARIA.value: "Agropecuária e desenvolvimento rural",
    Tema.ASSISTENCIA_SOCIAL.value: "Assistência social e combate à pobreza",
    Tema.CIENCIA_TECNOLOGIA.value: "Ciência, tecnologia e inovação",
    Tema.CULTURA.value: "Cultura",
    Tema.DIREITOS_HUMANOS.value: "Direitos humanos e igualdade",
    Tema.ECONOMIA_EMPREGO.value: "Economia e emprego",
    Tema.EDUCACAO.value: "Educação",
    Tema.INFRAESTRUTURA.value: "Infraestrutura e mobilidade",
    Tema.MEIO_AMBIENTE.value: "Meio ambiente e clima",
    Tema.POLITICA_EXTERNA.value: "Política externa e relações internacionais",
    Tema.REFORMA_POLITICA.value: "Reforma política e institucional",
    Tema.SAUDE.value: "Saúde",
    Tema.SEGURANCA_PUBLICA.value: "Segurança pública",
    Tema.SEM_TEMA_DEFINIDO.value: "Sem tema definido",
}
TEMAS_DISPONIVEIS = [(t.value, ROTULOS_TEMA[t.value]) for t in Tema]


def _base(caminho_fila: Path) -> str:
    return caminho_fila.name[: -len(".fila_revisao.json")]


def _caminho_decisoes(caminho_fila: Path) -> Path:
    return caminho_fila.with_name(f"{_base(caminho_fila)}.decisoes.json")


def criar_app(pasta_dados: Path) -> FastAPI:
    pasta_dados = Path(pasta_dados)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI(title="Monitor Eleitoral — revisao humana")

    def _listar_filas() -> list[Path]:
        return sorted(pasta_dados.rglob("*.fila_revisao.json"))

    def _carregar_fila(nome: str) -> tuple[Path, dict[str, Any]]:
        achados = [p for p in _listar_filas() if _base(p) == nome]
        if not achados:
            raise HTTPException(404, f"item '{nome}' nao encontrado")
        caminho = achados[0]
        return caminho, json.loads(caminho.read_text(encoding="utf-8"))

    def _carregar_decisoes(caminho_fila: Path) -> dict[str, Any]:
        caminho = _caminho_decisoes(caminho_fila)
        if not caminho.exists():
            return {}
        return json.loads(caminho.read_text(encoding="utf-8"))

    def _salvar_decisoes(caminho_fila: Path, decisoes: dict[str, Any]) -> None:
        proveniencia.salvar_json(decisoes, _caminho_decisoes(caminho_fila))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        itens = []
        for caminho in _listar_filas():
            fila = json.loads(caminho.read_text(encoding="utf-8"))
            decisoes = _carregar_decisoes(caminho)
            itens.append(
                {
                    "nome": _base(caminho),
                    "resumo": resumo(fila, decisoes),
                    "pronto": pronto_para_publicacao(fila, decisoes),
                    "url": fila.get("url"),
                }
            )
        return templates.TemplateResponse(request, "lista.html", {"itens": itens})

    @app.get("/item/{nome}", response_class=HTMLResponse)
    def ver_item(request: Request, nome: str):
        caminho, fila = _carregar_fila(nome)
        decisoes = _carregar_decisoes(caminho)
        segmentos = []
        for i, item in enumerate(fila.get("itens", [])):
            d = decisoes.get(str(i)) or {}
            segmentos.append(
                {
                    "indice": i,
                    **item,
                    "decisao": d.get("decisao"),
                    "texto_final": d.get("texto_final"),
                    "temas": d.get("temas") or [],
                }
            )
        return templates.TemplateResponse(
            request,
            "item.html",
            {
                "nome": nome,
                "fila": fila,
                "segmentos": segmentos,
                "resumo": resumo(fila, decisoes),
                "pronto": pronto_para_publicacao(fila, decisoes),
                "temas_disponiveis": TEMAS_DISPONIVEIS,
            },
        )

    @app.get("/item/{nome}/audio")
    def audio(nome: str):
        caminho, _ = _carregar_fila(nome)
        wav = caminho.with_name(f"{_base(caminho)}.wav")
        if not wav.exists():
            raise HTTPException(404, "audio original nao encontrado ao lado da fila")
        return FileResponse(wav, media_type="audio/wav")

    @app.post("/item/{nome}/segmento/{indice}", response_class=HTMLResponse)
    def decidir_segmento(
        request: Request,
        nome: str,
        indice: int,
        decisao: str = Form(...),
        texto_final: str = Form(""),
        temas: list[str] = Form([]),
    ):
        caminho, fila = _carregar_fila(nome)
        itens = fila.get("itens", [])
        if not (0 <= indice < len(itens)):
            raise HTTPException(404, f"segmento {indice} nao existe em '{nome}'")
        try:
            d = Decisao(decisao)
        except ValueError:
            raise HTTPException(400, f"decisao invalida: {decisao!r}")

        decisoes = _carregar_decisoes(caminho)
        item = itens[indice]
        texto_limpo = texto_final.strip()
        try:
            novas = registrar_decisao(
                decisoes,
                indice,
                d,
                texto_final=(texto_limpo or item["texto"]) if d is Decisao.CONFIRMADO else None,
                temas=temas if d is Decisao.CONFIRMADO else None,
                revisado_em=proveniencia.agora_utc(),
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        _salvar_decisoes(caminho, novas)

        segmento = {
            "indice": indice,
            **item,
            "decisao": novas[str(indice)]["decisao"],
            "texto_final": novas[str(indice)].get("texto_final"),
            "temas": novas[str(indice)].get("temas") or [],
        }
        html_segmento = templates.get_template("_segmento.html").render(
            request=request,
            nome=nome,
            segmento=segmento,
            temas_disponiveis=TEMAS_DISPONIVEIS,
        )
        html_controles = templates.get_template("_controles.html").render(
            request=request,
            nome=nome,
            resumo=resumo(fila, novas),
            pronto=pronto_para_publicacao(fila, novas),
        )
        return HTMLResponse(html_segmento + html_controles)

    @app.post("/item/{nome}/publicar", response_class=HTMLResponse)
    def publicar(nome: str):
        caminho, fila = _carregar_fila(nome)
        decisoes = _carregar_decisoes(caminho)
        try:
            publicacao = montar_publicacao(fila, decisoes)
        except ValueError as e:
            raise HTTPException(400, str(e))
        destino = caminho.with_name(f"{_base(caminho)}.publicado.json")
        proveniencia.salvar_json(publicacao, destino)
        return (
            f'<p style="color:#2e7d32">'
            f"publicado: {len(publicacao['citacoes'])} citacao(oes) em "
            f"{destino.name}</p>"
        )

    return app


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    ap = argparse.ArgumentParser(description="Site de revisao humana da fila de transcricao.")
    ap.add_argument("--dados", type=Path, default=Path("dados/transcricoes"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8000)
    args = ap.parse_args(argv)

    app = criar_app(args.dados)
    uvicorn.run(app, host=args.host, port=args.porta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
