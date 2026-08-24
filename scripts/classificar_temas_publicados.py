"""Marca tema nas citacoes ja confirmadas, por classificacao automatica.

Contexto (2026-08-24): a auto-aprovacao confirma texto sem passar pela
revisao humana e, junto, sem marcar tema — entao as 971 citacoes
publicadas nasceram todas com `temas: []`. Como o site inteiro e'
organizado por tema, o lado das falas ficava invisivel em qualquer
filtro tematico (painel de comparacao, `/comparar`, chips de tema).

Este script escreve o tema em `.decisoes.json` (nao so' no
`.publicado.json`), porque e' de la' que `montar_publicacao` le' — se
gravasse so' no publicado, o tema sumiria na proxima republicacao.

Marca a origem em `temas_por: "classificacao_automatica"`, para que o
audit trail continue distinguindo o que foi decisao de pessoa do que foi
decisao de maquina — mesmo espirito de `revisado_por` na auto-aprovacao.

**Nao sobrescreve tema marcado por humano.** Se `temas` ja tem conteudo
e `temas_por` nao e' automatico, o item e' pulado.

    python3 scripts/classificar_temas_publicados.py [--aplicar]

Sem `--aplicar` roda em modo simulacao e so' mostra o que faria.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from transcricao import proveniencia  # noqa: E402
from transcricao.classificar_tema import classificar_sequencia  # noqa: E402
from transcricao.revisao import montar_publicacao  # noqa: E402

TRANSCRICOES = RAIZ / "dados" / "transcricoes"
MARCA = "classificacao_automatica"


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    total_itens = 0
    total_marcados = 0
    total_sem_tema = 0
    total_preservados = 0
    por_tema: Counter[str] = Counter()
    arquivos_tocados = 0

    for caminho_dec in sorted(TRANSCRICOES.glob("*.decisoes.json")):
        base = caminho_dec.name.removesuffix(".decisoes.json")
        caminho_fila = TRANSCRICOES / f"{base}.fila_revisao.json"
        caminho_pub = TRANSCRICOES / f"{base}.publicado.json"
        if not caminho_fila.exists() or not caminho_pub.exists():
            continue

        decisoes = json.loads(caminho_dec.read_text(encoding="utf-8"))
        fila = json.loads(caminho_fila.read_text(encoding="utf-8"))
        itens = fila.get("itens", [])
        mudou = False

        # Classifica o video inteiro de uma vez: trecho sem palavra-chave
        # propria pode herdar o tema da fala imediatamente anterior (ver
        # `classificar_sequencia`). Usa o texto corrigido pelo humano
        # quando existir.
        textos_para_classificar = []
        for i, item in enumerate(itens):
            entrada = decisoes.get(str(i)) or {}
            textos_para_classificar.append(
                {
                    "texto": entrada.get("texto_final") or item.get("texto") or "",
                    "inicio": item.get("inicio"),
                }
            )
        temas_da_sequencia = classificar_sequencia(textos_para_classificar)

        for indice, entrada in decisoes.items():
            if entrada.get("decisao") != "confirmado":
                continue
            total_itens += 1

            ja_tem = entrada.get("temas")
            if ja_tem and entrada.get("temas_por") != MARCA:
                total_preservados += 1
                continue

            try:
                temas = temas_da_sequencia[int(indice)]
            except (ValueError, IndexError):
                continue

            if temas != (ja_tem or []):
                entrada["temas"] = temas
                entrada["temas_por"] = MARCA
                mudou = True

            if temas:
                total_marcados += 1
                por_tema.update(temas)
            else:
                total_sem_tema += 1

        if mudou:
            arquivos_tocados += 1
            if aplicar:
                caminho_dec.write_text(
                    json.dumps(decisoes, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                publicacao = montar_publicacao(fila, decisoes)
                proveniencia.salvar_json(publicacao, caminho_pub)

    print(f"citacoes confirmadas analisadas: {total_itens}")
    print(f"  com tema atribuido: {total_marcados}")
    print(f"  sem tema (nenhuma palavra-chave bateu): {total_sem_tema}")
    print(f"  tema humano preservado: {total_preservados}")
    print(f"arquivos alterados: {arquivos_tocados}")
    print()
    print("distribuicao por tema:")
    for tema, n in por_tema.most_common():
        print(f"  {n:5d}  {tema}")

    if not aplicar:
        print()
        print("SIMULACAO — nada foi gravado. Rode com --aplicar para valer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
