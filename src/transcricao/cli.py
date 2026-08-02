"""CLI: python -m transcricao.cli <arquivo|pasta> [opcoes]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import qualidade
from .pipeline import processar
from .transcrever import MODELO_PADRAO

EXTENSOES = {".mp4", ".mkv", ".webm", ".mov", ".m4a", ".mp3", ".wav", ".aac", ".opus"}


def _coletar_arquivos(entrada: Path) -> list[Path]:
    if entrada.is_file():
        return [entrada]
    return sorted(
        p for p in entrada.rglob("*") if p.suffix.lower() in EXTENSOES
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Transcricao com proveniencia, diarizacao e descarte por confianca."
    )
    ap.add_argument("entrada", type=Path, help="arquivo de midia ou pasta")
    ap.add_argument(
        "-s", "--saida", type=Path, default=Path("dados/transcricoes")
    )
    ap.add_argument(
        "--fonte", default="desconhecida", help="ex: youtube, instagram, debate"
    )
    ap.add_argument("--url", default=None)
    ap.add_argument("--perfil", default=None, help="@ do perfil ou nome do canal")
    ap.add_argument("--publicado-em", default=None, help="ISO 8601 UTC")
    ap.add_argument(
        "--coletado-em",
        default=None,
        help="ISO 8601 UTC de quando o COLETOR viu o conteudo",
    )
    ap.add_argument("-m", "--modelo", default=MODELO_PADRAO)
    ap.add_argument(
        "--sem-diarizacao",
        action="store_true",
        help="desliga a diarizacao (forca revisao humana)",
    )
    ap.add_argument("--max-falantes", type=int, default=None)
    ap.add_argument(
        "--mapa-falantes",
        type=Path,
        default=None,
        help='JSON tipo {"SPEAKER_00": "candidato_x"}',
    )
    args = ap.parse_args(argv)

    if not args.entrada.exists():
        print(f"erro: {args.entrada} nao existe", file=sys.stderr)
        return 2

    arquivos = _coletar_arquivos(args.entrada)
    if not arquivos:
        print("erro: nenhuma midia encontrada", file=sys.stderr)
        return 2

    mapa = None
    if args.mapa_falantes:
        mapa = json.loads(args.mapa_falantes.read_text(encoding="utf-8"))

    # carrega o modelo uma vez para o lote inteiro
    modelo = None
    if len(arquivos) > 1:
        from .transcrever import carregar_modelo

        print(f"carregando modelo {args.modelo} ...")
        modelo = carregar_modelo(args.modelo)

    total_revisao = 0
    for i, arq in enumerate(arquivos, 1):
        print(f"[{i}/{len(arquivos)}] {arq.name}")
        try:
            t = processar(
                arq,
                fonte=args.fonte,
                saida=args.saida,
                url=args.url,
                perfil=args.perfil,
                publicado_em=args.publicado_em,
                coletado_em=args.coletado_em,
                nome_modelo=args.modelo,
                modelo=modelo,
                usar_diarizacao=not args.sem_diarizacao,
                max_falantes=args.max_falantes,
                mapa_falantes=mapa,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  falhou: {e}", file=sys.stderr)
            continue

        r = qualidade.resumo(t.segmentos)
        marca = "REVISAO OBRIGATORIA" if t.exige_revisao_humana else "ok"
        print(
            f"  {r['ok']} ok / {r['revisar']} revisar / "
            f"{r['descartado']} descartado | falantes: "
            f"{len(t.falantes) or '?'} | {marca}"
        )
        for aviso in t.avisos:
            print(f"  aviso: {aviso}")
        if t.exige_revisao_humana:
            total_revisao += 1

    print(
        f"\n{total_revisao}/{len(arquivos)} itens precisam de conferencia humana "
        f"antes de qualquer publicacao."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
