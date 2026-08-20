"""Junta transcricao.json + decisoes.json de todo item ja revisado a mao,
pra medir contra amostra real (nao intuicao) a taxa de erro do limiar de
auto-aprovacao em `auto_aprovacao.py`.

Regra do proprio projeto (`qualidade.py`, `CLAUDE.md`): ajustar limiar
contra amostra rotulada e taxa de erro medida, nunca por intuicao ou
poucas observacoes. Rode este script de novo sempre que o volume de
revisao humana crescer bastante, pra saber se da' pra apertar ou se
precisa afrouxar `auto_aprovacao.NO_SPEECH_MAX` / `LOGPROB_MIN` /
`COMPRESSION_MAX`.

    python3 scripts/analisar_confianca_threshold.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from transcricao.auto_aprovacao import segmento_elegivel  # noqa: E402

PASTA = RAIZ / "dados" / "transcricoes"


def coletar_amostra() -> list[dict]:
    linhas = []
    for f in sorted(PASTA.glob("*.transcricao.json")):
        base = f.stem.replace(".transcricao", "")
        dec_path = PASTA / f"{base}.decisoes.json"
        if not dec_path.exists():
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        if any("legenda" in a for a in t.get("avisos", [])):
            continue  # sem sinais de confianca do Whisper, fora do escopo
        decisoes = json.loads(dec_path.read_text(encoding="utf-8"))
        for i, seg in enumerate(t["segmentos"]):
            if seg["status"] == "descartado":
                continue
            d = decisoes.get(str(i))
            if not d or d.get("revisado_por"):
                continue  # sem decisao humana, ou decisao ja' era automatica
            texto_editado = bool(d.get("texto_final")) and d["texto_final"] != seg["texto"]
            linhas.append({"arquivo": base, "indice": i, "segmento": seg, "texto_editado": texto_editado})
    return linhas


def main() -> int:
    amostra = coletar_amostra()
    print(f"amostra: {len(amostra)} segmentos com decisao humana real (nao auto-aprovada)")

    elegiveis = [l for l in amostra if segmento_elegivel(l["segmento"])]
    erros_nos_elegiveis = [l for l in elegiveis if l["texto_editado"]]
    print(
        f"elegiveis pelo limiar atual: {len(elegiveis)}/{len(amostra)} "
        f"({100 * len(elegiveis) / len(amostra):.0f}%)"
    )
    print(f"desses, precisaram correcao de texto na amostra real: {len(erros_nos_elegiveis)}")
    if elegiveis:
        limite_superior = 3 / len(elegiveis)  # regra de tres p/ zero eventos observados
        print(
            f"limite superior de erro (regra de tres, 95% confianca, "
            f"assumindo zero erros observados): ~{100 * limite_superior:.1f}%"
        )
    if len(amostra) < 300:
        print(
            "\naviso: amostra ainda pequena (< 300). Nao aperte o limiar so' com isso "
            "— espere mais revisao real acumular antes de mudar auto_aprovacao.py."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
