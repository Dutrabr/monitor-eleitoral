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
  revisao.py            fluxo fila -> decisao -> publicacao — PURO, testado
  site_revisao.py       FastAPI + Jinja2 + HTMX: interface de revisao humana
  templates_revisao/    templates Jinja2 do site de revisao
  plano_de_governo.py   extrai URL do PDF do plano de governo (API TSE) — PURO, testado
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
falante e descarte por confianca. Validado ao vivo em 2026-08-03 com
Whisper real + pyannote real (nao dublê), pipeline completo YouTube ->
transcricao. Corrigidos dois bugs de compatibilidade com versoes
instaladas mais novas das libs (detalhes no docstring de `diarizar.py`):
`Pipeline.from_pretrained(use_auth_token=)` -> `token=`, e o retorno da
pipeline de diarizacao mudou de `Annotation` direto para `DiarizeOutput`
(usamos `.exclusive_speaker_diarization`, de proposito, para nao herdar
ambiguidade de fala sobreposta). Tambem sao TRES modelos gated no Hugging
Face agora, nao dois — o terceiro (`speaker-diarization-community-1`) e'
dependencia transitiva nao documentada em lugar nenhum.

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

Pronto: site de revisao humana (`site_revisao.py`), interno — nao e' o site
publico. Fluxo fila -> decisao -> publicacao: cada item citavel exige
CONFIRMADO ou REJEITADO explicito de um humano (nunca automatico); rejeitar
so' marca, nao apaga. Publicar recusa (HTTP 400) se houver pendencia. O
player de audio serve o `.wav` de 16 kHz que a propria pipeline ja gera ao
lado da fila, com suporte a range request para pular direto ao timestamp.
Decisoes ficam num sidecar `NOME.decisoes.json`, com timestamp de auditoria;
publicacao final em `NOME.publicado.json` — so' evidencia confirmada, nunca
veredito. Rodar: `cd src && python3 -m transcricao.site_revisao --dados
../dados/transcricoes`. Validado com teste HTTP completo (confirmar,
rejeitar, gating de publicacao, persistencia, range request) — **sem**
verificacao visual em navegador (extensao do Chrome nao estava conectada
na sessao em que foi construido).

Pesquisado (2026-08-02) e testado ao vivo (2026-08-03) contra a eleicao de
2022: API do DivulgaCandContas para plano de governo. Nao documentada
oficialmente; achada via `github.com/augusto-herrmann/divulgacandcontas-doc`
(swagger nao-oficial) e `github.com/augusto-herrmann/eleicoes-2020-planos-de-governo`
(script real que baixou planos de prefeitos em 2020). Confirmado ao vivo
contra 2022 (eleicao encerrada, dado publico — nao mexe com 2026):
BASE precisa ser https (`divulga/rest/v1`, a porta 80 nem conecta mais);
`/candidatura/listar/2022/BR/544/1/candidatos` devolve candidatos reais a
presidente, confirmando `municipio="BR"` e `cargo=1` para candidatura
nacional a Presidente. **Bloqueio novo, sem solucao ainda**:
`/candidatura/buscar/.../candidato/{id}` — que deveria trazer `arquivos`
(onde mora a URL do plano de governo, `codTipo == "5"`) — devolve HTTP 200
com corpo vazio de forma reproduzivel (testado com id da listagem, numero
de urna, com/sem cookie de sessao, com/sem Referer). Hotlink direto ao PDF
pelo padrao mais novo (achado por busca, URLs reais de 2022) devolve 403
da propria infra do TSE. Aparenta que o portal atual trocou a rota de
detalhe do candidato — falta descobrir qual e' a nova, provavelmente
inspecionando as chamadas de rede do site num navegador de verdade
(DevTools), nao so' testando rotas do script antigo de 2020. Detalhes e
as chamadas exatas testadas estao no docstring de `plano_de_governo.py`.
`plano_de_governo.py` implementa e testa so' a parte pura (extrair a URL
do PDF dado um JSON de candidato ja' obtido) — a parte de I/O fica
bloqueada nesse endpoint quebrado.

Observado no teste real com Whisper (nao-dublê, ver `transcrever.py`):
`language` fica fixo em "pt" nas opcoes do decoder. Isso e' proposital (o
publico do projeto so' fala portugues), mas significa que, se algum
coletor apontar por engano pra conteudo em outro idioma, o Whisper NAO
falha de forma obvia — ele produz um texto fluente em portugues (as vezes
parecido com traducao) em vez de erro claro. Testado com um video em
ingles: saiu portugues plausivel mas incorreto, com `avg_logprob`/
`no_speech_prob` dentro da faixa aceitavel — foi para REVISAR, nao
DESCARTADO. A rede de seguranca aqui e' a revisao humana obrigatoria (regra
2), nao os limiares de `qualidade.py`: um revisor ouvindo o trecho percebe
na hora que e' outro idioma. Isso reforca que a revisao humana nao e'
so' verificacao de fidelidade — tambem pega escopo errado.

Proximo:
- achar a rota atual de detalhe do candidato no DivulgaCandContas (a do
  script de 2020 devolve corpo vazio agora — ver bloqueio acima), depois
  implementar a parte de I/O da ingestao (hoje so' a extracao pura existe)
- taxonomia tematica unica, publicada antes de qualquer analise — decisao
  editorial, nao so' tecnica; precisa de definicao do dono do projeto antes
  de qualquer analise comparativa
- site publico (FastAPI + Jinja2 + HTMX) — depende dos dois itens acima

## Fora de escopo, por decisao

- fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia e
  re-encoda o audio, piorando a transcricao.
- Stories do Instagram: efemero de 24h, alta friccao, conteudo pobre para
  promessa programatica.
- Qualquer juizo automatizado sobre merito de candidatura.
