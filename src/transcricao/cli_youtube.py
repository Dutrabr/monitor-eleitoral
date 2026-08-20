"""CLI: python -m transcricao.cli_youtube <url> [opcoes]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import proveniencia, qualidade
from .auto_aprovacao import gerar_decisoes_automaticas
from .coletar_youtube import IDIOMAS_PADRAO, NAVEGADOR_COOKIES_PADRAO, ColetaIndisponivel, coletar
from .transcrever import MODELO_PADRAO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Baixa video do YouTube e transcreve: legenda quando existir, "
            "Whisper no resto."
        )
    )
    ap.add_argument("url")
    ap.add_argument("-s", "--saida", type=Path, default=Path("dados/transcricoes"))
    ap.add_argument(
        "--idiomas",
        nargs="+",
        default=list(IDIOMAS_PADRAO),
        help="ordem de preferencia de idioma da legenda",
    )
    ap.add_argument(
        "--forcar-whisper",
        action="store_true",
        help="ignora legenda disponivel e roda a pipeline normal com diarizacao",
    )
    ap.add_argument("-m", "--modelo", default=MODELO_PADRAO)
    ap.add_argument(
        "--sem-diarizacao",
        action="store_true",
        help="desliga a diarizacao quando cair no Whisper (forca revisao humana)",
    )
    ap.add_argument("--max-falantes", type=int, default=None)
    ap.add_argument(
        "--mapa-falantes",
        type=Path,
        default=None,
        help='JSON tipo {"SPEAKER_00": "candidato_x"}',
    )
    ap.add_argument(
        "--navegador-cookies",
        default=NAVEGADOR_COOKIES_PADRAO,
        help=(
            "navegador local (com sessao logada) de onde extrair cookies "
            "para evitar bloqueio do YouTube por volume de trafego anonimo "
            f"(padrao: {NAVEGADOR_COOKIES_PADRAO})"
        ),
    )
    ap.add_argument(
        "--sem-cookies-navegador",
        action="store_true",
        help="desliga cookies de navegador (necessario em ambiente sem Chrome, ex: CI/servidor)",
    )
    ap.add_argument(
        "--falante-confirmado",
        default=None,
        help=(
            "falante_id (ex: candidato_fulano) do canal de onde este video foi "
            "coletado. So' tem efeito se o video inteiro tiver UM UNICO falante: "
            "gera confirmacao automatica pros segmentos de alta confianca (ver "
            "auto_aprovacao.py — excecao explicita a regra 2, taxa de erro "
            "aceita ~5%, decisao do dono do projeto em 2026-08-19). Video com "
            "mais de um falante ignora esta flag e cai na revisao normal."
        ),
    )
    args = ap.parse_args(argv)

    mapa = None
    if args.mapa_falantes:
        mapa = json.loads(args.mapa_falantes.read_text(encoding="utf-8"))

    try:
        t = coletar(
            args.url,
            saida=args.saida,
            idiomas=tuple(args.idiomas),
            forcar_whisper=args.forcar_whisper,
            nome_modelo=args.modelo,
            usar_diarizacao=not args.sem_diarizacao,
            max_falantes=args.max_falantes,
            mapa_falantes=mapa,
            navegador_cookies=None if args.sem_cookies_navegador else args.navegador_cookies,
        )
    except ColetaIndisponivel as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2

    r = qualidade.resumo(t.segmentos)
    marca = "REVISAO OBRIGATORIA" if t.exige_revisao_humana else "ok"
    print(
        f"{r['ok']} ok / {r['revisar']} revisar / {r['descartado']} descartado "
        f"| falantes: {len(t.falantes) or '?'} | {marca}"
    )
    for aviso in t.avisos:
        print(f"aviso: {aviso}")

    if args.falante_confirmado:
        base = Path(t.proveniencia["arquivo"]).stem
        segmentos = t.para_dict()["segmentos"]
        decisoes = gerar_decisoes_automaticas(
            segmentos, args.falante_confirmado, {}, revisado_em=proveniencia.agora_utc()
        )
        if decisoes:
            caminho = args.saida / f"{base}.decisoes.json"
            caminho.write_text(json.dumps(decisoes, ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                f"auto-aprovacao: {len(decisoes)}/{r['ok'] + r['revisar']} segmento(s) "
                f"confirmado(s) automaticamente em {caminho.name} — o resto continua "
                "na revisao humana normal."
            )
        else:
            print("auto-aprovacao: nenhum segmento se qualificou (ou video tem mais de um falante).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
