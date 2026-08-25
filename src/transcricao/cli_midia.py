"""CLI: python -m transcricao.cli_midia <url> [opcoes]

Coleta de YouTube, Instagram, TikTok ou Facebook pelo mesmo comando —
a plataforma sai da propria URL (ver `coletar_midia.detectar_plataforma`).

Alem do que `cli_youtube` ja' fazia, este comando checa se o video
REPETE alguma peca ja' coletada. Campanha publica o mesmo video em
varias redes, e sem essa checagem a mesma fala apareceria duas ou tres
vezes na pagina do candidato como se fossem declaracoes distintas.
Repetido nunca e' apagado: fica marcado (`repetido_de` na fila) e fora
da auto-aprovacao, entao so' vai ao ar se um humano decidir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import proveniencia, qualidade
from .auto_aprovacao import gerar_decisoes_automaticas
from .coletar_midia import PlataformaNaoSuportada, checar_repetido, coletar
from .coletar_youtube import NAVEGADOR_COOKIES_PADRAO, ColetaIndisponivel
from .transcrever import MODELO_PADRAO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Baixa video de YouTube/Instagram/TikTok/Facebook e transcreve, "
            "avisando se o video repete uma peca ja' coletada."
        )
    )
    ap.add_argument("url")
    ap.add_argument("-s", "--saida", type=Path, default=Path("dados/transcricoes"))
    ap.add_argument("-m", "--modelo", default=MODELO_PADRAO)
    ap.add_argument("--sem-diarizacao", action="store_true")
    ap.add_argument("--max-falantes", type=int, default=None)
    ap.add_argument("--mapa-falantes", type=Path, default=None)
    ap.add_argument("--navegador-cookies", default=NAVEGADOR_COOKIES_PADRAO)
    ap.add_argument("--sem-cookies-navegador", action="store_true")
    ap.add_argument(
        "--falante-confirmado",
        default=None,
        help=(
            "falante_id (ex: candidato_fulano) do canal oficial de onde o video "
            "veio. So' tem efeito em video de UM UNICO falante cujo texto NAO "
            "cite o nome do proprio candidato (ver auto_aprovacao.py)."
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
            nome_modelo=args.modelo,
            usar_diarizacao=not args.sem_diarizacao,
            max_falantes=args.max_falantes,
            mapa_falantes=mapa,
            navegador_cookies=(
                None if args.sem_cookies_navegador else args.navegador_cookies
            ),
        )
    except PlataformaNaoSuportada as e:
        print(f"erro: {e}", file=sys.stderr)
        return 3
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

    base = Path(t.proveniencia["arquivo"]).stem
    caminho_fila = args.saida / f"{base}.fila_revisao.json"

    repetido = checar_repetido(t, args.saida)
    if repetido and repetido[0] != base:
        outro, semelhanca = repetido
        print(
            f"REPETIDO: este video reaproveita {semelhanca:.0%} do conteudo de "
            f"'{outro}', ja' coletado. Nada foi apagado — o item fica marcado e "
            f"fora da auto-aprovacao; publique-o so' se for mesmo material novo."
        )
        if caminho_fila.exists():
            fila = json.loads(caminho_fila.read_text(encoding="utf-8"))
            fila["repetido_de"] = {"video": outro, "semelhanca": round(semelhanca, 4)}
            caminho_fila.write_text(
                json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    if args.falante_confirmado and not repetido:
        segmentos = t.para_dict()["segmentos"]
        decisoes = gerar_decisoes_automaticas(
            segmentos,
            args.falante_confirmado,
            {},
            revisado_em=proveniencia.agora_utc(),
        )
        if decisoes:
            caminho = args.saida / f"{base}.decisoes.json"
            caminho.write_text(
                json.dumps(decisoes, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                f"auto-aprovacao: {len(decisoes)}/{r['ok'] + r['revisar']} segmento(s) "
                f"confirmado(s) automaticamente em {caminho.name} — o resto continua "
                "na revisao humana normal."
            )
        else:
            print(
                "auto-aprovacao: nenhum segmento se qualificou (video com mais de um "
                "falante, ou o texto cita o nome do proprio candidato)."
            )
    elif args.falante_confirmado and repetido:
        print("auto-aprovacao: pulada porque o video foi marcado como repetido.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
