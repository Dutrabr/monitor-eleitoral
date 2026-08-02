# Monitor Eleitoral — contexto para o Claude Code

## O que e' este projeto

Compara o que candidatos a presidente **registraram no plano de governo** com o
que **dizem nas redes sociais e em videos**. Exibe evidencia lado a lado. O
leitor tira a conclusao.

## Regras invioláveis (nao negocie estas)

1. **O site exibe evidencia, nunca veredito.** Sem nota, sem ranking, sem score,
   sem "vale a pena votar". A Resolucao TSE 23.610/2019, art. 9º-B (alterada pela
   Res. 23.755/2026) veda que sistemas de IA recomendem, ranqueiem, sugiram ou
   priorizem candidatos — inclusive a pedido expresso do usuario.
2. **Nenhuma citacao vai ao ar sem um humano ter ouvido o trecho.** A
   transcricao serve para *encontrar* a fala em escala. A publicacao e'
   verificada. `Transcricao.exige_revisao_humana` implementa isso.
3. **Simetria total entre candidatos.** Mesma pipeline, mesma janela temporal,
   mesmos parametros. Assimetria transforma ferramenta civica em peca de
   campanha.
4. **Zero adjetivo proprio sobre candidato.** O projeto nao qualifica, nao
   interpreta intencao, nao chama nada de "escandalo". Agrega e mostra.
5. **Nunca descartar diarizacao silenciosamente.** Sem diarizacao confiavel, o
   item vai para revisao humana. Atribuir fala de entrevistador a candidato e' o
   erro que destroi o projeto.
6. **Hash do arquivo como baixado, antes de qualquer conversao.** O hash do WAV
   convertido nao prova nada sobre a origem.

## Arquitetura

```
src/transcricao/
  modelos.py          dataclasses puras (Palavra, Turno, Segmento, Transcricao)
  qualidade.py        regras de descarte/alucinacao — PURO, testado
  atribuir.py         cruza diarizacao x timestamps de palavra — PURO, testado
  legendas.py         parser de legenda VTT/SRT -> Segmento — PURO, testado
  proveniencia.py     hash, extracao de audio, manifesto de custodia
  transcrever.py      wrapper faster-whisper (parametros anti-alucinacao)
  diarizar.py         wrapper pyannote, com degradacao explicita
  pipeline.py         orquestracao (arquivo local -> transcricao)
  coletar_youtube.py    baixa do YouTube (yt-dlp); legenda quando existir, Whisper senao
  coletar_instagram.py  baixa Reels do Instagram (instaloader); sempre Whisper
  cli.py                interface de linha de comando (arquivo/pasta local)
  cli_youtube.py        interface de linha de comando (URL do YouTube)
  cli_instagram.py      interface de linha de comando (URL do Reel)
```

**Camadas puras vs. de I/O:** `qualidade.py` e `atribuir.py` nao fazem I/O e nao
dependem de modelo. Toda regra de negocio nova vai nelas, com teste. Nao
espalhe logica de decisao dentro de `pipeline.py`.

## Como rodar

```bash
python3 -m pytest tests/ -q          # 41 testes, sem baixar modelo
python3 demo.py                      # pipeline com transcritor falso
cd src && python3 -m transcricao.cli ARQUIVO --fonte youtube
```

## Convencoes

- Portugues nos identificadores e mensagens; sem acento em nome de simbolo.
- Nada de emoji em log ou saida de terminal.
- Timestamps sempre UTC, ISO 8601.
- `coletado_em` e' quando o **coletor** viu o conteudo, nao quando transcreveu.
  Esse campo precisa vir do coletor; preenchido depois, perde valor probatorio.
- Ao mexer em limiar de `qualidade.py`, ajuste contra amostra rotulada a mao e
  registre a taxa de erro. Nao ajuste por intuicao.

## Estado atual

Pronto: modulo de transcricao com proveniencia, diarizacao, atribuicao de
falante e descarte por confianca.

Pronto: coletor do YouTube (`coletar_youtube.py` / `cli_youtube.py`). Baixa o
video (nao so o audio, para preservar a midia completa como prova). Prefere
legenda manual, depois automatica, nos idiomas pedidos; sem nenhuma das duas,
cai na pipeline normal (Whisper + diarizacao). Segmento vindo de legenda
**nunca** chega a `Status.OK` — falta confianca de ASR, entao vai sempre para
`REVISAR` (ou `DESCARTADO` se bater com alucinacao/spam conhecido); e
`diarizacao_disponivel=False` ja forca `exige_revisao_humana=True` pela regra
existente em `modelos.Transcricao`. Validado com smoke test manual real
(download + parsing de legenda). Dedup de legenda "rolling" e' parcial — so
remove cues identicas consecutivas, nao remonta a partir de tags de timing
por palavra.

Pronto: coletor do Instagram (`coletar_instagram.py` / `cli_instagram.py`).
So' Reels (URL precisa ter `/reel/` ou `/reels/`; post comum, story e perfil
sao rejeitados na propria extracao do shortcode). Baixa direto do CDN da
Meta via instaloader, sem ripper de terceiro. Nao ha trilha de legenda
separada para Reels — todo item passa pela pipeline normal (Whisper +
diarizacao); `accessibility_caption` do Instagram e' descricao de imagem
por IA, nao transcricao de fala, e por isso nunca e' usado como fonte de
texto. **Nao testado com download real**: autenticacao anonima do
instaloader e' instavel e testar sem login arrisca acionar bloqueio
anti-bot; testado apenas o que independe de rede (extracao de shortcode,
conversao de data). Antes do primeiro uso real, gere uma sessao com
`instaloader --login SEU_USUARIO` e exporte `INSTAGRAM_USUARIO` (e
`INSTAGRAM_SESSAO` se o arquivo nao estiver no caminho padrao).

Proximo:
- ingestao dos planos de governo (disponiveis no DivulgaCandContas apos o
  registro, ate 15/08/2026)
- taxonomia tematica unica, publicada antes de qualquer analise
- interface de revisao humana (fila -> conferencia -> publicacao)
- FastAPI + Jinja2 + HTMX para o site

## Fora de escopo, por decisao

- fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia e
  re-encoda o audio, piorando a transcricao.
- Stories do Instagram: efemero de 24h, alta friccao, conteudo pobre para
  promessa programatica.
- Qualquer juizo automatizado sobre merito de candidatura.
