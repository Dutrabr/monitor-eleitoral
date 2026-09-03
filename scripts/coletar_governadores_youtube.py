#!/usr/bin/env python3
"""Coleta em lote: um video do canal oficial de cada candidato a Governador.

Fonte do canal: campo `sites` do registro no TSE (ver
`dados/redes_sociais_governador.json`) — NUNCA busca generica. Se o
candidato nao cadastrou canal, ele fica de fora, e isso e' fato
registrado, nao falha.

REGRA DE ESCOLHA, identica para todos (regra 3 do projeto — simetria):
o video MAIS RECENTE do canal cuja duracao esteja entre DUR_MIN e
DUR_MAX. Sem essa regra fixa, escolher "o melhor video" de cada um
viraria curadoria editorial disfarcada. Curto demais raramente tem fala
citavel; longo demais custa horas de transcricao sem ganho proporcional.

Idempotente: pula quem ja' tem citacao publicada e quem ja' foi coletado
nesta pasta.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from transcricao import proveniencia, qualidade  # noqa: E402
from transcricao.auto_aprovacao import gerar_decisoes_automaticas  # noqa: E402
from transcricao.coletar_midia import checar_repetido, coletar  # noqa: E402
from transcricao.coletar_youtube import RUNTIMES_JS, ColetaIndisponivel  # noqa: E402

DUR_MIN = 30
DUR_MAX = 600
QUANTOS_LISTAR = 20


def abas_do_canal(url: str) -> list[str]:
    """URLs a tentar, em ordem. Canal so' de Shorts nao tem aba /videos, e
    canal recem-criado as vezes so' responde na raiz — cair fora por isso
    seria perder candidato por detalhe de layout do YouTube, nao por
    ausencia de conteudo.

    A query string TEM que sair antes de anexar a aba: muito link
    cadastrado no TSE vem com rastreador de compartilhamento
    (`@canal?si=ABC`), e concatenar daria `@canal?si=ABC/videos` — 404
    garantido, que o script leria como canal sem conteudo.
    """
    partes = urlsplit(url.strip())
    esquema = (partes.scheme or "https").lower()
    host = partes.netloc.lower()
    caminho = partes.path.rstrip("/")
    for prefixo in ("/user/", "/channel/", "/c/"):
        if caminho.lower().startswith(prefixo):
            caminho = prefixo + caminho[len(prefixo):]
            break
    for sufixo in ("/videos", "/streams", "/shorts", "/featured"):
        if caminho.lower().endswith(sufixo):
            caminho = caminho[: -len(sufixo)]
            break
    base = urlunsplit((esquema, host, caminho, "", ""))
    return [base + "/videos", base + "/shorts", base]


def abrir_listador(navegador_cookies: str | None):
    """Um unico YoutubeDL reaproveitado para listar TODOS os canais.

    Extrair cookie do Chrome e' caro (descriptografia AES) e acontece uma
    vez por instancia. Criando uma instancia por canal — pior ainda, por
    aba de canal — o custo dominava o tempo total do lote.
    """
    import yt_dlp

    opcoes = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": QUANTOS_LISTAR,
        "ignoreerrors": True,
        # Sem isto, canal com cookie de outra conta do Google devolve
        # "Playlists that require authentication may not extract correctly"
        # e o listador volta VAZIO — que o script lia como "canal sem
        # video". Opcao documentada do proprio yt-dlp, sugerida na
        # mensagem de erro dele.
        "extractor_args": {"youtubetab": {"skip": ["authcheck"]}},
    }
    if navegador_cookies:
        opcoes["cookiesfrombrowser"] = (navegador_cookies,)
        opcoes["remote_components"] = ["ejs:github"]
        opcoes["js_runtimes"] = list(RUNTIMES_JS)
    return yt_dlp.YoutubeDL(opcoes)


def escolher_video(canal: str, listador) -> tuple[dict | None, str]:
    """Devolve (video_escolhido, motivo).

    Distinguir "canal nao pode ser lido" de "canal lido, nada na faixa de
    duracao" importa: o primeiro e' falha tecnica pra investigar, o
    segundo e' fato sobre o canal. Tratar os dois como a mesma coisa ja'
    fez o script reportar "sem video" pra canal cheio de video.
    """
    viu_algum = False
    for aba in abas_do_canal(canal):
        try:
            info = listador.extract_info(aba, download=False)
        except Exception:  # noqa: BLE001 — aba inexistente, tenta a proxima
            continue
        if not info:
            continue
        for e in info.get("entries") or []:
            if not e:
                continue
            d = e.get("duration")
            if d:
                viu_algum = True
            if d and DUR_MIN <= d <= DUR_MAX:
                return ({"id": e.get("id"), "titulo": e.get("title"), "duracao": d,
                         "url": e.get("url")
                         or f"https://www.youtube.com/watch?v={e.get('id')}"}, "ok")
    return (None, "nada_na_faixa" if viu_algum else "canal_ilegivel")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", type=Path, default=RAIZ / "dados/transcricoes")
    ap.add_argument("--redes", type=Path, default=RAIZ / "dados/redes_sociais_governador.json")
    ap.add_argument("--limite", type=int, default=None, help="processa so' os N primeiros")
    ap.add_argument("--uf", default=None, help="filtra por estado")
    ap.add_argument("--navegador-cookies", default="chrome")
    ap.add_argument("--so-listar", action="store_true", help="mostra o que faria, sem baixar")
    args = ap.parse_args(argv)

    dados = json.loads(args.redes.read_text(encoding="utf-8"))
    alvos = [c for c in dados["falta_coletar"] if "YouTube" in c["plataformas"]]
    if args.uf:
        alvos = [c for c in alvos if c["uf"] == args.uf.upper()]
    if args.limite:
        alvos = alvos[: args.limite]

    print(f"{len(alvos)} candidato(s) a processar", flush=True)
    listador = abrir_listador(args.navegador_cookies)
    ok = pulados = falhas = 0

    for i, c in enumerate(alvos, 1):
        falante_id = "candidato_" + c["slug"].replace("-", "_")
        canais = [u for u in c["urls"] if "youtu" in u.lower()]
        cab = f"[{i}/{len(alvos)}] {c['uf']} {c['nome']}"
        if not canais:
            print(f"{cab}: sem URL de YouTube", flush=True)
            pulados += 1
            continue
        try:
            escolha, motivo = escolher_video(canais[0], listador)
        except Exception as e:  # noqa: BLE001 — canal pode estar fora do ar
            print(f"{cab}: ERRO ao listar canal: {str(e)[:120]}", flush=True)
            falhas += 1
            continue
        if not escolha:
            if motivo == "canal_ilegivel":
                print(f"{cab}: NAO CONSEGUI LISTAR o canal ({canais[0]}) — "
                      "falha tecnica, nao ausencia de conteudo", flush=True)
                falhas += 1
            else:
                print(f"{cab}: canal lido, mas nenhum video entre "
                      f"{DUR_MIN}-{DUR_MAX}s nos {QUANTOS_LISTAR} mais recentes",
                      flush=True)
                pulados += 1
            continue
        if (args.saida / f"{escolha['id']}.fila_revisao.json").exists():
            print(f"{cab}: ja coletado ({escolha['id']})", flush=True)
            pulados += 1
            continue

        print(f"{cab}: {escolha['duracao']}s — {(escolha['titulo'] or '')[:55]}", flush=True)
        if args.so_listar:
            ok += 1
            continue

        try:
            t = coletar(
                escolha["url"],
                saida=args.saida,
                navegador_cookies=args.navegador_cookies,
            )
        except (ColetaIndisponivel, Exception) as e:  # noqa: BLE001
            print(f"    ERRO na coleta: {str(e)[:150]}", flush=True)
            falhas += 1
            continue

        r = qualidade.resumo(t.segmentos)
        base = Path(t.proveniencia["arquivo"]).stem
        print(f"    {r['ok']} ok / {r['revisar']} revisar / {r['descartado']} desc "
              f"| {len(t.falantes) or '?'} falante(s)", flush=True)

        repetido = checar_repetido(t, args.saida)
        if repetido and repetido[0] != base:
            outro, s = repetido
            print(f"    REPETIDO de '{outro}' ({s:.0%}) — fora da auto-aprovacao", flush=True)
            fila = args.saida / f"{base}.fila_revisao.json"
            if fila.exists():
                d = json.loads(fila.read_text(encoding="utf-8"))
                d["repetido_de"] = {"video": outro, "semelhanca": round(s, 4)}
                fila.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            decisoes = gerar_decisoes_automaticas(
                t.para_dict()["segmentos"], falante_id, {},
                revisado_em=proveniencia.agora_utc(),
            )
            if decisoes:
                (args.saida / f"{base}.decisoes.json").write_text(
                    json.dumps(decisoes, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"    auto-aprovado: {len(decisoes)} segmento(s)", flush=True)
            else:
                print("    tudo pra revisao humana (multi-falante ou cita o "
                      "proprio nome)", flush=True)
        ok += 1

    print(f"\nfim: {ok} coletado(s), {pulados} pulado(s), {falhas} falha(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
