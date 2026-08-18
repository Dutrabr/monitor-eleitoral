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
  plano_de_governo.py   busca candidato e baixa o PDF do plano de governo (API TSE)
  candidatos.py         registro de candidatos + agregacao por tema — PURO em boa parte, testado
  site_publico.py       site publico: FastAPI + Jinja2, evidencia lado a lado
  templates_publico/    templates Jinja2 do site publico
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
rejeitar, gating de publicacao, persistencia, range request) e depois
com verificacao visual real no navegador (clique real em confirmar/
rejeitar/publicar, player tocando, swap OOB do resumo funcionando sem
reload). O endpoint de publicar devolvia JSON cru na tela; trocado para
devolver uma mensagem HTML legivel.

Pronto (2026-08-03, via DevTools no navegador real): ingestao do plano de
governo via API do DivulgaCandContas, `plano_de_governo.py`. A sessao
anterior tinha documentado um bloqueio ("buscar candidato" devolvia corpo
vazio, hotlink do PDF devolvia 403) e concluido que faltava achar uma rota
nova. Era mais simples que isso: **faltava so' o header `Referer:
https://divulgacandcontas.tse.jus.br/divulga/`** — sem ele, `buscar`
devolve HTTP 200 com corpo vazio (nao um erro) e o download do arquivo
devolve 403. Nao precisa de cookie de sessao nem navegador real, so' esse
header, confirmado com `curl` puro. Descoberto navegando o portal de
verdade (candidatura ja' em andamento para 2026 — Governador, Senador etc.
— presidente ainda nao registrou) e lendo as chamadas de rede reais via
DevTools.

Tambem corrigido: o campo `arquivos[].url + arquivos[].nome` (o jeito que
o script de 2020 baixava) NAO funciona mais — da' 403 mesmo com Referer e
mesmo numa sessao de navegador logada. O download real e' por
`arquivos[].idArquivo` em `GET .../rest/arquivo/doc/{idArquivo}`.
Validado contra dado real: baixado o PDF de 20 paginas do plano de
governo 2026 de ACM Neto (candidato a Governador da Bahia).

`codigo_eleicao` de 2026 (eleicao geral): `"20322002026"` — visto direto
na URL do portal, nao precisou adivinhar. `cargo=1`/`municipio="BR"` para
candidatura nacional a Presidente segue confirmado (contra 2022, ja' que
presidente nao registrou ainda) mas falta testar com um candidato a
presidente de verdade quando o registro fechar (15/08/2026) — o
mecanismo de busca+download ja' esta' prova, so' falta aplicar aos ids
certos quando existirem.

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

Pronto (2026-08-03): taxonomia tematica aprovada pelo dono do projeto —
ver TAXONOMIA.md. 13 categorias + `SEM_TEMA_DEFINIDO`, em `modelos.Tema`.
Marcacao de tema acontece no mesmo passo da revisao humana (quem confirma
um segmento pode marcar um ou mais temas via checkbox); `temas: list[str]`
viaja ate' `montar_publicacao`, vazio se o revisor nao marcou nada — nunca
forca encaixe.

Pronto (2026-08-03): site publico (`site_publico.py`). So' mostra: dados
basicos do candidato, link para o PDF do plano de governo, e as citacoes
CONFIRMADAS (nunca as pendentes/rejeitadas) agrupadas por tema em ordem
alfabetica do rotulo. **Nenhum cruzamento automatico entre "prometeu" e
"disse"** — nao ha extracao de texto do PDF por tema nem pontuacao de
aderencia; isso seria interpretacao, e regra 1 do projeto proibe qualquer
coisa que beire veredito. Link com timestamp funciona so' para YouTube
(`?t=Ns`, unico formato documentado publicamente); outras fontes linkam
sem parametro de tempo, nunca inventando um que a plataforma nao suporta.

Pronto (2026-08-14): registro real dos 9 candidatos a Presidente 2026 ja
inscritos no DivulgaCandContas (EDMILSON COSTA/PCB, ESCRITOR AUGUSTO
CURY/AVANTE, FLAVIO BOLSONARO/PL, HERTZ DIAS/PSTU, LULA/PT, RENAN
SANTOS/MISSAO, SAMARA/UP, VETERINARIO WILSON GRASSI/DEMOCRATA, ZEMA/NOVO
— registro ainda nao fechou, essa lista pode crescer ate' 15/08/2026).
`dados/candidatos/{slug}.json` com dados reais (nome completo, partido,
numero, vice, `fonte_dados` com o id do candidato na API do TSE para
rastreabilidade) para cada um; os 9 PDFs de plano de governo baixados de
verdade em `dados/planos_de_governo/{slug}.pdf`, com hash sha256 de cada
um registrado em `MANIFESTO.json` ao lado (cadeia de custodia, regra 6).
`falante_id` segue o padrao `candidato_{slug_com_underscore}` (ex:
`candidato_lula`) — e' o valor que `--mapa-falantes` precisa usar na
hora de coletar midia desses candidatos.

Adicionado `site_publico.py: GET /plano/{slug}`, que serve o PDF do
proprio storage local em vez de linkar direto pro TSE — evita depender
da disponibilidade/formato de URL do portal deles (que ja mudou de
endpoint uma vez nesta mesma pesquisa). Validado contra o servidor real
rodando com os 9 candidatos: index lista todos em ordem alfabetica,
pagina de candidato carrega, PDF baixa integro (conferido com `file`).
5 testes novos com `fastapi.testclient.TestClient` (nao tinha esse padrao
de teste no projeto ainda) cobrindo a rota `/plano/{slug}` e o 404 de
plano ausente.

**`dados/candidatos/` e `dados/planos_de_governo/` NAO estao no git** —
`dados/` inteiro e' gitignored (mesma convencao de todo resto que o
pipeline gera). Isso significa que essa base de 9 candidatos existe so'
nesta maquina; se for rodar em outro lugar, precisa gerar de novo com
`scripts/atualizar_candidatos_presidente.py` (idempotente, ja' no
repositorio — nao e' mais scratch).

Pronto (2026-08-17): primeira citacao real, do inicio ao fim, publicada
e visivel no site publico. Coletado um Short real do canal oficial do
Zema (fonte: campo `sites` do proprio registro na API do TSE, nao busca
generica), pipeline completo com Whisper real + diarizacao real,
revisado por um humano de verdade em `site_revisao.py` (nao por mim —
ver nota abaixo), publicado, e confirmado aparecendo em
`/candidato/zema` com link certo pro plano de governo e pro trecho
exato na fonte.

No processo, achado e corrigido um gap real: a diarizacao deixou um
segmento sem falante atribuido (buraco de cobertura, nao erro — ver
`atribuir.py`). O humano ouviu, confirmou que era o Zema, mas
`site_revisao.py` nao tinha como capturar essa correcao — so' texto e
tema eram editaveis. Adicionado campo `falante` opcional no formulario
de confirmacao (`revisao.registrar_decisao(..., falante=...)`,
`montar_publicacao` usa `falante_confirmado` quando presente, senao cai
no valor original da diarizacao — nunca inventa). Funciona tanto para
preencher um buraco quanto para corrigir uma atribuicao errada. 12
testes novos (7 em `test_revisao.py` puro, 5 em `test_site_revisao.py`
novo, primeiro teste desse site usando `TestClient`).

**Importante sobre quem fez a revisao humana**: eu (Claude) nunca
cliquei em confirmar usando meu proprio julgamento sobre o audio — nao
tenho como ouvir, e mesmo se tivesse, regra 2 exige um humano de
verdade. Toda decisao de confirmar/rejeitar/corrigir texto e falante
nesse teste foi do dono do projeto, ouvindo o audio real. Meu papel foi
so' technical: subir o servidor, aplicar as correcoes que ele ditou
(inclusive via chat, replicando o que ele teria digitado no formulario),
e implementar o campo que faltava quando o formulario nao dava conta do
que ele precisava corrigir.

Ainda falta: repetir esse fluxo pros outros 8 candidatos (e' manual,
video por video — nao ha' processo em lote ainda) e decidir se/como
extrair texto do plano de governo por tema (hoje e' so' um link pro PDF
inteiro) — se fizer, repensar com cuidado o risco de virar interpretacao
automatizada.

Observado DUAS vezes agora (Zema em 2026-08-17, Flavio Bolsonaro em
2026-08-18, ambos clipes de campanha/comicio): segmentos com texto
coerente e politicamente relevante descartados por `no_speech_prob` alto
(0.78-0.99), provavelmente por musica/aplausos de fundo confundindo o
classificador do Whisper — nao silencio de verdade. `DESCARTADO` nunca
entra na fila de revisao (`pipeline.fila_de_verificacao` exclui), entao
esse conteudo fica invisivel para o humano, mesmo sendo potencialmente
relevante (no caso do Flavio, incluia mencao a CPMI do INSS e pedido de
prisao do "Lulinha"). **Nao mexi no limiar `NO_SPEECH_MAX` de
`qualidade.py`** — regra do proprio arquivo e' so' ajustar contra amostra
rotulada a mao com taxa de erro medida, nao por duas observacoes. Mas se
esse padrao se repetir mais vezes em clipes de comicio/campanha, vale
juntar esses casos como a amostra rotulada que falta para uma recalibragem
de verdade.

Pronto (2026-08-18): coletor do YouTube autentica com cookies de um
navegador local logado (`coletar_youtube.baixar(..., navegador_cookies=
"chrome")`, padrao). Achado em producao: depois de algumas dezenas de
downloads anonimos no mesmo dia (varios candidatos, varios vídeos), o
YouTube passou a devolver HTTP 403 em QUALQUER video — nao so' os ja'
tocados, confirmado testando um video completamente nao relacionado que
tinha funcionado horas antes. Nao era rate-limit de um video especifico,
era bloqueio por volume de trafego anonimo. Levou uma noite inteira pra
descobrir isso: tentativa as 03:33 via cron (agendada pra 2h depois da
primeira falha) ainda falhou, e so' foi resolvido comparando com outro
projeto do dono (coletor de video de "influenciadores" apostas, em
`~/Documents/PROJETOS/PROJETO - PROJETO_INFLUENCIADORES/Download_youtube.py`)
que usa exatamente essa tecnica e nunca foi bloqueado. `--cookies-from-
browser` e' recurso padrao e documentado do yt-dlp — usar a propria conta
logada do usuario e' o oposto de burlar protecao, e' se identificar de
verdade em vez de trafegar anonimo. CLI ganhou `--navegador-cookies` e
`--sem-cookies-navegador` (para ambiente sem Chrome, ex: servidor/CI).
5 testes novos cobrindo o comportamento (padrao ligado, desligavel,
customizavel, presente em toda tentativa da cadeia de fallback).

Proximo:
- repetir a coleta+revisao real pros outros 8 candidatos
- acompanhar o DivulgaCandContas ate' 15/08/2026: a lista de 9 pode
  crescer; reexecutar a coleta de candidatos quando fechar

## Fora de escopo, por decisao

- fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia e
  re-encoda o audio, piorando a transcricao.
- Stories do Instagram: efemero de 24h, alta friccao, conteudo pobre para
  promessa programatica.
- Qualquer juizo automatizado sobre merito de candidatura.
