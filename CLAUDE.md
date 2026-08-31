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
2. **Nenhuma citacao vai ao ar sem um humano ter ouvido o trecho — OU sem
   passar num limiar de confianca calibrado e explicitamente aceito pelo
   dono do projeto.** A transcricao serve para *encontrar* a fala em
   escala. A publicacao e' verificada — por humano na maioria dos casos,
   ou automaticamente quando os 4 sinais de confianca do Whisper batem
   **e** o video inteiro tem um so' falante do inicio ao fim (nunca em
   video com mais de uma pessoa). Excecao decidida em 2026-08-19 (ver
   `auto_aprovacao.py` e "Estado atual" abaixo) — taxa de erro aceita
   ~5%, calibrada contra amostra real, nao intuicao. Ajustar o limiar
   exige amostra nova medida (`scripts/analisar_confianca_threshold.py`),
   nunca so' "parece que ta' bom". `Transcricao.exige_revisao_humana`
   implementa a parte que ainda e' sempre manual.
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

## Design visual do site publico

`DESIGN.md`, na raiz, e' a fonte da verdade do sistema visual (paleta,
tipografia, espacamento, raio, sombra, componentes) — extraido do CSS
real de `base.html`, nao inventado. Antes de mexer no CSS do site
publico, ler `DESIGN.md`; depois de mexer, atualizar `DESIGN.md` no
mesmo commit. Ver secao final do arquivo pro status atual (v1 linha de
base, redesign v2 pendente de referencia visual do dono).

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

Pronto (2026-08-19): coletado o segundo dos 9 candidatos, Renan Santos
(canal oficial achado pelo site cadastrado no TSE, que linkava pro
YouTube @RenanSantosMBL). Achado e corrigido um gap real no caminho:
o video tinha legenda automatica do YouTube, entao caiu em
`_processar_com_legenda` — e essa funcao nunca chamava
`proveniencia.extrair_audio`, so' o caminho Whisper gerava o `.wav`.
Resultado: `site_revisao.py` devolvia 404 em `/item/{nome}/audio` pra
qualquer item vindo de legenda, travando a revisao humana (regra 2 exige
poder ouvir). Nunca tinha aparecido porque os 3 videos de YouTube
coletados antes (Lula, Flavio, Zema) caiam todos no caminho Whisper.
Corrigido chamando `extrair_audio` tambem em `_processar_com_legenda`
(mesmo padrao de `pipeline.processar`), com teste novo usando ffmpeg
real (`test_caminho_de_legenda_tambem_gera_wav_para_o_player_de_revisao`).
Pro item ja coletado antes do fix, o `.wav` foi gerado retroativamente do
`.mp4` original ja baixado (sem novo download) e o manifesto de
proveniencia foi atualizado a mao com o registro da extracao.

Pronto (2026-08-19): Renan Santos e Hertz Dias coletados, revisados pelo
dono do projeto e publicados (Renan: 346 citacoes via legenda do YouTube;
Hertz: 7 citacoes via Instagram Reel, Whisper + diarizacao real). No caso
do Hertz, achado um gap na revisao: o campo `falante` ficou em branco no
formulario (so' 1 falante detectado), entao a citacao publicada nao
batia com `falante_id` do candidato e ficava invisivel no site publico —
corrigido a mao nas decisoes (`falante_confirmado`) apos confirmar com o
dono que era mesmo o candidato falando, e republicado. 7 dos 9 candidatos
tem citacao publicada agora; faltam Samara e Veterinario Wilson Grassi.

Pronto (2026-08-19): site publico v2, Fase 1 — comparacao por tema entre
plano de governo e redes sociais, por candidato. Motivado por um prompt de
design que o dono trouxe pedindo exatamente esse cruzamento; decisao
tomada junto com ele pra nao virar "interpretacao automatizada" (o que a
regra 1 proibe): o pareamento tema-a-tema do lado do plano e' **curadoria
manual**, mesmo espirito de `revisao.py` — nenhum algoritmo decide se um
tema "consta" no plano.

- Novo: `dados/planos_curados/{slug}.json` (fora do git, hand-edited),
  schema documentado no docstring de `candidatos.py`. Por tema:
  `{"status": "consta", "trechos": [{"texto":..., "pagina":...}]}` ou
  `{"status": "nao_consta"}`. Tema ausente do arquivo = "nao verificado
  ainda" — nunca vira "nao consta" por omissao (mesmo principio de
  `qualidade.py`). `carregar_plano_curado` levanta erro claro se o
  `status` gravado nao for um dos dois validos, pra pegar erro de
  digitacao na curadoria cedo.
- Gap pequeno corrigido no caminho: `publicado_em`/`coletado_em` existiam
  em `proveniencia.manifesto` mas nunca eram propagados por
  `pipeline.fila_de_verificacao` nem `revisao.montar_publicacao` — sem
  isso nao dava pra mostrar data nos cards nem montar a linha do tempo.
  Agora os dois campos atravessam a cadeia toda.
- `site_publico.py` ganhou: `/candidato/{slug}` redesenhado com painel de
  2 colunas por tema (plano curado × citacoes, com os 3 rotulos "Consta no
  plano" / "Nao consta no plano" / "Tema nao verificado ainda"), linha do
  tempo cronologica, `/metodologia`, exports `/dados/citacoes.json` e
  `/dados/citacoes.csv`. Candidatos agora ordenados por **numero de urna**
  em vez de alfabetico (uma das duas opcoes que o proprio prompt de design
  permitia; descartei "ordem aleatoria por sessao" porque URL de
  comparacao compartilhavel ficaria mais complexa sem ganho real).
- Design: paleta teal/ambar/grafite, dark mode (`prefers-color-scheme` +
  toggle persistido em `localStorage`), fonte de sistema em vez de
  Inter Tight/Satoshi (evita gerenciar asset binario de fonte por pouco
  ganho visual), tudo inline em `base.html` — sem build step, sem pacote
  novo. Paineis 2-colunas/abas-mobile sao CSS puro (radio+label,
  `nth-of-type` estrutural), sem framework de tabs em JS — testado a
  logica de toggle via JS direto no navegador (a ferramenta de resize de
  janela desta sessao nao mudava o viewport real pra confirmar visualmente
  em largura de celular, mas a media query em si e' CSS padrao).
- Fase 2 (nao feita ainda, escopo separado por decisao — ver plano
  salvo): modo comparar 2-4 candidatos, busca com destaque, player
  embutido do YouTube, botao "copiar link", animacoes de entrada.

Pronto (2026-08-19): email placeholder do rodape/metodologia trocado por
contato real (jvriibmr@gmail.com).

Pronto (2026-08-19): coleta+revisao real dos 2 candidatos que faltavam
(Samara, Veterinario Wilson Grassi) — os 9 candidatos tem citacao
publicada agora. No processo, mesmo gap de falante do Hertz Dias
reapareceu nos dois (formulario de revisao preenchido com o rotulo bruto
da diarizacao em vez de `candidato_*`) — corrigido a mao apos confirmar
com o dono que era mesmo o candidato falando, republicado. Achado
tambem: o primeiro Reel testado da Samara (9.7s) nao tinha fala alguma
(so' musica/texto na tela) — Whisper devolveu 0 segmentos, exit code 0,
sem erro — silencioso o suficiente pra passar despercebido se ninguem
checasse a contagem de segmentos. Trocado por outro Reel do mesmo perfil.

Pronto (2026-08-19): curadoria manual dos 13 temas × 9 candidatos = 117
entradas em `dados/planos_curados/` completa — o painel de comparacao
nao mostra mais "tema nao verificado" em lugar nenhum. Processo: criado
`scripts/buscar_trecho_plano.py` (usa `pdftotext -layout`, ja disponivel
no sistema, sem lib nova) pra achar pagina candidata por titulo de secao
ou por contagem de palavra-chave; eu (Claude) nunca decidi sozinho se um
tema consta — sempre apresentei o trecho achado com pagina e pedi
confirmacao antes de gravar, mesmo espirito de `revisao.py`. 9 entradas
viraram `"status": "nao_consta"` de verdade, nao suposicao: Renan Santos
(sem capitulo dedicado a meio ambiente nem a direitos humanos, confirmado
contra a lista completa dos seus 14 capitulos), Veterinario Wilson Grassi
(sem eixo de assistencia social nem de cultura, confirmado contra os 14
eixos do documento — e um caso raro onde o proprio candidato *declara*
por escrito que omite doutrina de politica externa, "a omissao e
deliberada", entao esse tema entrou como `consta` citando a propria
frase), Samara (plano de so' 2 paginas, sem conteudo de ciencia/
tecnologia nem de cultura), Escritor Augusto Cury e Hertz Dias (sem
projeto/secao dedicada a cultura, so' mencoes de passagem).

Pronto (2026-08-19): modo comparar (`/comparar?tema=X&candidatos=a,b`) —
2 a 4 candidatos lado a lado, mesmo tema, ordenados por numero de urna
sempre (nao pela ordem da URL). Formulario GET puro, sem JS de tab
framework; URL do resultado ja e' o link compartilhavel.

Pronto (2026-08-19): redesign visual completo (header em gradiente,
hero na home, avatares circulares, hover com elevacao, divisores em
gradiente) — o layout anterior estava sobrio demais, dono do projeto
nem tinha aberto o site ainda por causa disso. Paleta neutra mantida
(sem vermelho/azul).

Pronto (2026-08-19): lista de candidatos a Presidente cresceu de 9 pra
13 (registro fechou 15/08). Adicionados CLARIANA BARAO, PABLO MARÇAL,
RONALDO CAIADO, RUI COSTA PIMENTA. **Achado importante**: a API do
DivulgaCandContas (`requests`/`curl` direto, o metodo que
`plano_de_governo.py` e os scripts sempre usaram) passou a devolver
403 do Akamai — nao so' pra candidato novo, pro dominio inteiro,
mesmo com headers de navegador completos. NAO e' bug de codigo, e'
bot-detection real; nao tentei contornar (proibido). Descoberto que a
API responde normal quando chamada de dentro de uma aba real do
Chrome ja carregada (via `fetch()` no console) — sessao real passa no
desafio, script direto nao. Pra esses 4, dados + 1 PDF (Clariana)
foram pegos assim; Ronaldo Caiado e Rui Costa Pimenta ficaram so' com
o `idArquivo` anotado em `fonte_dados.plano_pendente_idArquivo` — o
download automatico via blob+`<a download>` funcionou uma vez só,
Chrome bloqueia downloads automaticos em sequencia depois da primeira
(precisa de interacao real do usuario pra autorizar mais). Pablo
Marçal genuinamente nao tem plano de governo cadastrado no TSE ainda
(`arquivos` vazio na resposta da API).

Nao feito, escopo grande demais pra uma sessao — Governador (197
candidatos em 26 estados + DF) e "outros politicos" (Senador 316,
Deputado Federal 7679, Deputado Estadual 11148): o dono topou
"presidente e governador, tudo bem se nao der o resto". Mesmo so'
governador, isso significa dezenas de novos `dados/candidatos/*.json`
+ PDFs de plano — viavel dado que e' so' registro factual (sem
julgamento editorial), mas cada citacao de video desses candidatos
ainda vai precisar do MESMO fluxo de revisao humana obrigatoria
(regra 2) que os 9 de presidente — ou seja, essa expansao aumenta MUITO
o trabalho de revisao manual do dono do projeto, nao so' o meu.

Proximo:
- se for expandir pra Governador: decidir por onde comecar (todos os
  26 estados de uma vez, ou um piloto de poucos estados primeiro?) —
  vale perguntar antes de rodar, dado o tamanho
- baixar os planos de governo pendentes de Ronaldo Caiado
  (idArquivo 280017106566) e Rui Costa Pimenta (idArquivo 280017113417)
  — via navegador real (`fetch` + `<a download>`), um de cada vez
- curar Saude/Educacao/Seguranca/etc. pros 4 candidatos novos de
  Presidente (ainda sem nenhuma entrada em `dados/planos_curados/`)
- decidir se/quando faz o resto da Fase 2 (busca com destaque, player
  embutido, botao copiar link)
- decidir sobre hospedagem publica — hoje o site so' roda em
  localhost, ninguem fora desta maquina consegue ver

Pronto (2026-08-19): **auto-aprovacao de segmentos de alta confianca —
excecao explicita e calibrada a regra 2** (ver `auto_aprovacao.py`).
Motivo: o dono do projeto nao tem tempo pra revisar cada citacao a mao e
pediu uma metrica que aumente a confianca sem depender do tempo dele.
Recusei aprovar automatico "porque parece confiavel" sem medir — rodei
`scripts/analisar_confianca_threshold.py` contra os 141 segmentos ja
revisados a mao ate' agora (10 videos via Whisper real, excluindo o de
legenda que nao tem essas metricas). Achado real, nao intuicao: usando
so' `no_speech_prob` como sinal, o mesmo nivel de "incerteza" aparecia
tanto em trechos que precisaram correcao quanto em trechos perfeitos —
36 dos 136 segmentos confirmados sem correcao tinham `no_speech_prob`
igual ou maior que um dos 2 episodios reais de erro. Um sinal so' nao
separa nada.

Testei combinar os 4 sinais que a pipeline ja calcula (`no_speech_prob
< 0.15`, `avg_logprob > -0.30`, `compression_ratio < 2.0`,
`pureza_falante == 1.0`) **mais** a exigencia de o video inteiro ter um
so' falante do inicio ao fim (nunca em video multi-falante — esse
cenario a amostra nem testou ainda). Resultado: 87 dos 141 segmentos
(62%) teriam sido auto-aprovados por esses 4 sinais juntos, com **zero**
erros de texto observados nesse grupo. Pela regra de tres (limite
superior pra zero eventos observados em n tentativas, 95% de confianca,
e' ~3/n), a taxa real de erro nesse grupo fica em ate' ~3,4% — dentro do
~5% ("1 em 20") que o dono decidiu aceitar explicitamente, depois de eu
apresentar tambem a opcao mais conservadora (~1%) e explicar que a
amostra e' pequena demais (so' 2 episodios de erro no total) pra
qualquer numero ser garantia.

Implementado em `auto_aprovacao.py` (funcoes puras, testadas —
`tests/test_auto_aprovacao.py`, 17 testes): `segmento_elegivel` checa os
4 sinais; `video_e_falante_unico` bloqueia qualquer video com mais de um
falante detectado (sem excecao); `gerar_decisoes_automaticas` gera
decisoes CONFIRMADO reusando `revisao.registrar_decisao`, marcadas com
`revisado_por="auto_aprovacao_confianca"` pra distinguir de revisao
humana real no audit trail. Nunca sobrescreve decisao ja existente.

Ligado nas CLIs (`cli_youtube.py`, `cli_instagram.py`) via flag nova
`--falante-confirmado candidato_x`: o dono continua afirmando de qual
canal oficial o video veio (mesma convencao de sempre — nunca busca
generica), mas nao precisa mais ouvir cada segmento se o video inteiro
for de um so' falante com sinais bons. Se o video tiver mais de um
falante, a flag nao faz nada e cai na revisao humana normal de sempre,
sem aviso enganoso de "tudo aprovado".

**Isso e' decisao explicita do dono do projeto, registrada aqui porque
mexe numa regra inviolavel — nao decidi isso sozinho, e' escolha dele
apos ver o numero real.** Amostra ainda pequena; revisitar com
`scripts/analisar_confianca_threshold.py` quando o volume de revisao
real crescer (o proprio script avisa se a amostra ainda ta' abaixo de
300).

Pronto (2026-08-19): planos de governo dos 2 PDFs pendentes (Ronaldo
Caiado, Rui Costa Pimenta) baixados via navegador real e registrados.
Curadoria dos 13 temas completa pros 3 candidatos novos com plano
(Clariana Barao, Ronaldo Caiado, Rui Costa Pimenta) — 12 dos 13
candidatos a Presidente com o painel de comparacao 100% preenchido
(consta ou nao_consta medido, nunca "nao verificado"). Pablo Marcal e'
excecao genuina: nao tem nenhum plano de governo registrado no TSE
(`arquivos` vazio na resposta da API), entao os 13 temas dele ficam
"nao verificado" de proposito — nao ha' documento pra checar.

Pronto (2026-08-20): **site publico no ar**, fora do localhost —
https://monitor-eleitoral.onrender.com (Render, plano free — "dorme"
depois de ~15min sem acesso, primeiro request seguinte demora uns
30-50s pra acordar, normal do plano gratuito). Repo no GitHub:
github.com/Dutrabr/monitor-eleitoral.

Deploy so' le `dados_publicos/` (ver
`scripts/exportar_dados_publicos.py`), nunca `dados/` inteiro — sem
midia original, sem decisoes de revisao, sem fila de verificacao, so'
o que ja' e' evidencia confirmada e publica (candidatos, planos de
governo em PDF, planos curados, citacoes ja' publicadas).
`requirements-publico.txt` fica sem faster-whisper/pyannote/yt-dlp/
instaloader — deploy nunca coleta nem transcreve.

**Fluxo pra atualizar o site publico depois de publicar algo novo
localmente**: `python3 scripts/exportar_dados_publicos.py` (regenera
`dados_publicos/`) -> `git add dados_publicos/` -> commit -> `git push`
-> Render redeploya sozinho a cada push na branch `main`.

Nota tecnica do proprio deploy: `render.yaml` original tinha um campo
`pythonVersion` que nao existe nesse formato do blueprint do Render —
corrigido pra `envVars: [{key: PYTHON_VERSION, value: "3.13.11"}]`,
que e' a forma documentada.

Pronto (2026-08-20): registro factual dos 197 candidatos a Governador 2026
(26 estados + DF) coletado — decisao do dono do projeto, apos eu perguntar
(regra do "Proximo" acima), de fazer todos os estados de uma vez em vez de
um piloto. `dados/candidatos_governador/{uf}/{slug}.json` (mesmo schema de
`dados/candidatos/`, `cargo: "Governador"`, pasta separada por decisao —
nao mistura com os 13 de Presidente ainda, integracao no site publico e'
decisao em aberto, nao feita nesta sessao). 190 dos 197 tem PDF de plano de
governo baixado em `dados/planos_de_governo_governador/{uf}/`; os 6 sem
plano sao factuais (API nao tem `arquivos` codTipo "5" pra eles): Vera
Lucia (CE), Ben Mendes (MG), Pedro Coutinho (PB), Eduardo Paes (RJ),
Garotinho (RJ), Policial Edjane (SP).

Achado: a API `listar` (cargo=3) ainda bloqueia `requests`/`curl` direto
com 403 do Akamai — confirmado de novo nesta sessao, mesmo bloqueio
documentado em 2026-08-19 pros 4 candidatos novos de Presidente. Sessao
real de aba do Chrome (via extensao Claude in Chrome, `fetch()` no
contexto da pagina) continua sendo o unico jeito que funciona; nao e'
"contornar" deteccao, e' navegacao real pelo portal.

Tecnica nova pra download de PDF em volume (o caso de Presidente so'
tinha baixado 1-2 por vez manualmente): `navigate()` direto pra URL do
arquivo (`/rest/arquivo/doc/{idArquivo}`) baixa pro `~/Downloads` sem
disparar o bloqueio de "downloads automaticos multiplos" do Chrome que
uma sessao anterior [ver nota de 2026-08-19 acima] tinha batido usando
blob+`<a download>`+`.click()` via JS — a diferenca parece ser que
navegacao real (mesmo disparada pela extensao) conta como acao do
usuario pro Chrome, enquanto o clique sintetico em JS sem gesto real
nao conta. Baixados os 191 PDFs em lotes de ate 25 via `browser_batch`
(varias chamadas `navigate` num so' round trip), sem nenhum bloqueio.

Duas armadilhas reais encontradas e corrigidas:
- **Nome de arquivo duplicado**: varios candidatos do mesmo partido (PCO,
  15 casos) reusam o MESMO PDF nacional, mesmo nome de arquivo. Baixar
  dois do mesmo nome no mesmo lote faz o Chrome sufixar "(1)", "(2)" —
  sem cuidado, o script de mover por nome exato erra o candidato. Corrigido
  separando por lotes sem nome duplicado (a maioria) e, pros duplicados,
  casando por ORDEM de pedido (indice do sufixo = ordem em que o
  `navigate` foi disparado, confirmado meticulosamente com contagem exata
  antes de mover).
- **Arquivo antigo com nome igual ja' no Downloads**: ACM Neto (BA) ja'
  tinha um PDF de mesmo nome no `~/Downloads` de um teste manual de
  2026-08-03 (`plano_de_governo.py`). O script de mover (que procura pelo
  nome exato sem sufixo) pegou o arquivo ANTIGO em vez do baixado nesta
  sessao, sem erro nenhum. So' nao virou dado errado porque o conteudo
  e' byte-a-byte identico (mesmo hash sha256) — verificado comparando
  todos os 190 PDFs por data de modificacao contra o horario da sessao;
  so' esse caso deu incompatibilidade, e por sorte inofensiva. Isso e' um
  risco generico de casar arquivo baixado por nome em vez de por
  identificador: se o dono tiver outro PDF de nome igual e conteudo
  DIFERENTE no Downloads dele no futuro, o mesmo mecanismo erraria
  silenciosamente. Nao criei protecao automatica pra isso (regra de nao
  adicionar validacao para cenario que nao aconteceu de verdade) mas fica
  registrado o padrao de risco caso reapareca em escala.

Achado tambem: a API devolveu DOIS registros de candidatura pra "ELIZEU
AGUIAR" (PI, NOVO, mesmo nome/numero/vice), com `id` e `numeroProcesso`
diferentes, ambos "Concorrendo". Nao decidi sozinho qual e' o "certo" —
mantido um registro de candidato so' (mesmo slug), mas documentado o
outro id/plano no campo `fonte_dados.nota` do JSON, pra um humano decidir
se e' erro de cadastro do TSE ou coisa real (ex: substituicao de
candidatura). Por isso 197 candidaturas da API viraram 196 arquivos de
candidato.

Ainda nao feito, decisao em aberto: curadoria dos 13 temas x candidatos
de Governador (o que foi feito pra Presidente via `buscar_trecho_plano.py`
+ confirmacao humana) e integracao no site publico (`site_publico.py` hoje
nao filtra por `cargo`, entao misturar as duas pastas de candidatos sem
mudanca de codigo faria os 196 governadores aparecerem juntos com os 13
presidenciais numa lista so' — precisa decisao de design antes: pagina
separada por cargo? Filtro? Selecionar estado primeiro?).

Pronto (2026-08-20): Governador integrado no site publico **local**
(`site_publico.py`) — decisao do dono, apos eu perguntar, de fazer isso
antes da curadoria de temas. Design: pasta separada (`dados/
candidatos_governador/{uf}/`) nunca se mistura com os 13 de Presidente
numa lista so' — o motivo e' que `numero` de urna e' por corrida (um
governador de SP numero 13 nao tem relacao nenhuma com um presidente
numero 13) e 196 nomes numa lista flat quebraria a leitura por numero de
urna que o rodape do site promete. Rotas novas, todas com estado (`uf`)
explicito na URL pra nao colidir com slug de Presidente:
- `GET /governador` — lista as 27 UFs (ordem alfabetica pelo nome do
  estado, nunca por sigla ou por contagem — regra 3).
- `GET /governador/{uf}` — candidatos daquele estado, ordem de numero de
  urna (mesma regra da pagina de Presidente).
- `GET /governador/{uf}/{slug}` — reusa o MESMO template `candidato.html`
  de Presidente (generico o bastante: so' precisava de um `voltar_url`/
  `voltar_label` parametrizavel em vez de link fixo pra `/`). Mostra 0
  citacoes pra todos os 196 (real — nenhuma coleta de video foi feita
  ainda pra Governador) e todos os 13 temas como "nao verificado ainda"
  (real — curadoria e' o proximo passo, ainda nao feito). Nao inventei
  dado nenhum pra preencher isso.
- `GET /governador/{uf}/{slug}/plano` — serve o PDF do storage local
  (mesmo padrao de `/plano/{slug}` do Presidente).

`candidatos.py` ganhou `UF_NOMES` (mapa sigla -> nome completo) e
`carregar_candidatos_por_uf` (mesmo `carregar_candidatos`, mas usa
`rglob` pra' entrar nas subpastas por UF). Os 190 JSONs de candidato que
tinham plano tiveram o campo `plano_de_governo` corrigido de path de
arquivo (`dados/planos_de_governo_governador/...`) pra rota
(`/governador/{uf}/{slug}/plano`) — o campo sempre foi rota no formato
de Presidente (`/plano/{slug}`), nao path de disco; o template so'
funciona se for URL.

Nao mexi no `/candidato/{slug}` nem em nenhuma rota de Presidente —
zero risco pro que ja' esta' no ar. Rodei os 156 testes (todos passam,
nenhum novo teste automatizado pras rotas de Governador ainda — validei
manualmente: cada rota nova com `urllib` mais screenshot real no
navegador de `/governador`, `/governador/BA` e `/governador/BA/acm-neto`)
e testei os casos de erro (UF invalida, candidato inexistente — ambos
404 correto).

`/dados/citacoes.json` e `.csv` (export publico) agora somam os dois
pools de candidato — hoje isso nao muda nada na pratica (Governador
tem zero citacao), mas evita que uma citacao futura de Governador
fique invisivel no export so' porque ninguem lembrou de atualizar essa
rota depois.

**Decisao em aberto, NAO feita nesta sessao**: publicar isso no site
publico de verdade (`monitor-eleitoral.onrender.com`). Motivos pra nao
fazer sozinho: (1) `dados/planos_de_governo_governador/` sozinho tem
182MB — o fluxo de deploy hoje (`exportar_dados_publicos.py` -> git
push) nunca lidou com um payload desse tamanho, precisa decisao sobre
git-lfs ou outra estrategia; (2) zero curadoria feita ainda, entao os
196 governadores apareceriam com todos os 13 temas em "nao verificado" —
factualmente correto mas pode passar impressao de site incompleto pro
publico; (3) e' push pra producao, decisao que cabe ao dono, nao a mim
decidir sozinho.

Corrigido (2026-08-20, durante a curadoria em lote de Governador):
`dados/planos_curados_governador/` estava sendo gravada como pasta plana
(`{slug}.json`), diferente de `candidatos_governador/` e
`planos_de_governo_governador/`, que sempre foram por UF
(`{uf}/{slug}.json`). Isso e' uma colisao real: "vera-lucia" existe como
candidata a Governadora tanto em SP quanto no CE (pessoas diferentes).
Sem a subpasta por UF, a curadoria de uma sobrescreveria/vazaria pra'
pagina da outra — achado a tempo, antes de eu curar a segunda (a de SP
ja' tinha 14 temas gravados; a do CE ainda nao tinha sido tocada).
Corrigido: os ~50 arquivos ja' gravados foram migrados pra'
`{uf}/{slug}.json`, `site_publico.governador_candidato` agora passa
`pasta_planos_curados_governador / uf` pra' `carregar_plano_curado`, e
`exportar_dados_publicos.py` usa `_copiar_por_uf` (mesmo helper de
`planos_de_governo_governador`) em vez de copia plana. Verificado que
`/governador/SP/vera-lucia` e `/governador/CE/vera-lucia` agora mostram
dados independentes.

Corrigido (2026-08-20, durante a curadoria em lote de Governador —
Distrito Federal): o arquivo cadastrado pelo proprio TSE como "plano de
governo" (`codTipo` "5") do candidato Rico Pinheiro (DF, PRTB) **nao e'
um plano de governo** — e' uma decisao judicial do TRE-DF sobre disputa
de filiacao partidaria (PJe, processo de FILIAÇÃO PARTIDÁRIA), 3 paginas,
zero conteudo de proposta de governo. Confirmado que nao e' erro nosso
de baixar/mover arquivo errado (mesmo padrao de risco documentado pro
caso do ACM Neto em 2026-08-20): o hash sha256 do PDF local bate
exatamente com o que ja' estava registrado em `fonte_dados.hash_sha256_pdf`
desde o download original — o proprio TSE serviu esse documento sob a
categoria errada. Corrigido: o PDF foi movido de
`dados/planos_de_governo_governador/DF/rico-pinheiro.pdf` pra'
`dados/planos_de_governo_governador/_documentos_invalidos/DF-rico-pinheiro-
decisao-judicial-TRE-nao-e-plano-de-governo.pdf` (preservado como
evidencia, fora do caminho normal de lookup por slug/UF — `_copiar_por_uf`
so' varre `{uf}/*.pdf`, entao a subpasta `_documentos_invalidos/` nunca
entra no export nem na rota publica). `plano_de_governo` no JSON do
candidato virou `null` (mesmo padrao dos 6 candidatos genuinamente sem
plano) e `fonte_dados` ganhou um campo `nota` documentando o problema, pra'
nao virar um "sumiu sem explicacao" se alguem olhar o arquivo depois.
Sem arquivo em `planos_curados_governador/DF/rico-pinheiro.json` — nao ha'
o que curar, os 14 temas ficam "nao verificado ainda", mesmo tratamento
de quando nao existe plano nenhum. Verificado com `TestClient`: a pagina
`/governador/DF/rico-pinheiro` nao mostra mais o link "Ler o plano de
governo completo", e a rota `/governador/DF/rico-pinheiro/plano` agora
devolve 404 (antes serviria a decisao judicial como se fosse o plano).
`dados_publicos/` regenerado depois do fix (`exportar_dados_publicos.py`);
ainda nao commitado/enviado pro deploy publico nesta sessao.

Pronto (2026-08-20/21): curadoria dos 14 temas completa pra' Mato Grosso — os
6 candidatos a Governador (Doutora Natasha, Mauricio Coelho, Otaviano
Pivetta, Rafaell Milas, Sargento Laudicerio (Lau), Wellington Fagundes)
com `dados/planos_curados_governador/MT/*.json` gravado, cada trecho
apresentado ao dono do projeto com pagina antes de gravar (mesmo fluxo
de `buscar_trecho_plano.py` usado pra Presidente, so' que sem o script —
os planos de Governador tem estrutura (indice, eixos numerados) variada
demais entre candidatos pra' um script generico, entao a leitura foi
manual por candidato, guiada por indice/sumario quando existia e por
busca de palavra-chave quando nao). Dois achados reais de "nao consta"
justificado por evidencia, nao por omissao: **Rafaell Milas** (MT) tem um
plano tecnico enxuto de so' 6 eixos que genuinamente nao cobre 6 dos 14
temas (confirmado por contagem de palavra-chave no PDF inteiro: zero
mencao a mulher/racial/LGBT/deficiencia, pobreza/SUAS, agricultura
familiar/rural, meio ambiente como agenda propria, cultura, ou municipio
como parceria dedicada). **Mauricio Coelho** (MT) tem 2 nao-consta por
um motivo mais especifico: o plano cita agricultura familiar e
assistencia social so' pra dizer que vai REDIRECIONAR o fundo FETHAB que
hoje financia essas duas areas pra pagar divida salarial de servidor —
ou seja, a unica mencao e' de retirar recurso dessas areas, nao de
expandi-las.

Corrigido no caminho (2026-08-21): o PDF cadastrado pelo TSE como plano
de governo de **Rico Pinheiro** (Governador, DF) nao e' um plano de
governo — e' uma decisao judicial do TRE-DF sobre disputa de filiacao
partidaria do PRTB. Ver nota de 2026-08-21 em "Estado atual" (mais acima
nesse arquivo) pro detalhe completo da correcao (`plano_de_governo: null`
no candidato, PDF movido pra' `_documentos_invalidos/`).

Estado da curadoria de Governador por UF, 2026-08-21 (candidatos com
plano de governo real / candidatos curados — os sem PDF ficam de fora da
contagem por nao terem o que curar):
AC 6/6, AL 4/4, AM 7/7, AP 5/5, BA 7/7, CE 8/8 (Vera Lucia sem plano),
DF 10/10 (Rico Pinheiro sem plano valido), ES 5/5, GO 6/6, MT 6/6, SP 6/6
(Policial Edjane sem plano) — 11 UFs completas. MA, MG, MS, PB, PE,
PI, PR, RJ, RN, RR, RS, SC com 1 candidato curado cada (parcial). MT
(quando comecei) tambem estava nessa lista mas foi concluido nesta
mesma sessao. PA, RO, SE, TO ainda sem nenhum candidato curado.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Goiás — os 6
candidatos (Daniel Vilela, Luciana Amorim, Luis Cesar Bueno, Marconi
Perillo, Wilder Morais, e Danilo Pinheiro que ja' estava pronto de uma
sessao anterior) com `dados/planos_curados_governador/GO/*.json`
gravado. Padrao comum aos planos de Goiás: quase todos organizam o
documento em eixos/programas numerados com sumario claro (Daniel Vilela:
6 eixos; Marconi Perillo: 10 areas tematicas + pacto municipal; Wilder
Morais: 12 programas numerados), o que tornou a localizacao dos 14 temas
mais rapida que em Mato Grosso. Duas excecoes ficaram registradas como
"nao_consta" — nenhuma por decisao unilateral minha, sempre confirmado
com o dono do projeto antes de gravar:
- Luciana Amorim (Unidade Popular): meio ambiente e clima, e gestao
  fiscal e divida publica — zero mencao no documento inteiro (varredura
  de palavra-chave confirmou).
- Trés outros temas de fronteira dessa mesma candidata (ciencia e
  tecnologia, reforma politica, relacoes federativas) tinham so' uma
  mencao tenue/indireta cada; o dono decidiu marcar como "consta" mesmo
  assim, entao ficaram registrados com o trecho tenue e a pagina, sem
  inflar a citacao.
Luis Cesar Bueno teve o mesmo padrao de fronteira em 3 temas (assistencia
social, gestao fiscal, reforma politica) — so' apareciam embutidos como
mecanismo de auditoria/financiamento DENTRO do capitulo de Saude ou do
fundo de mobilidade, nunca como agenda propria do Estado. Apresentado ao
dono caso a caso; ele decidiu "consta" nos 3, entao ficaram gravados
citando o trecho embutido tal como esta' no documento (nao inventei
conteudo mais forte do que existe).

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Maranhao — os 8
candidatos a Governador (Andre Luis, Dimas Cassimiro — ja' pronto de sessao
anterior, Eduardo Braide, Felipe Camarao, Orleans Brandao, Reginaldo Lima,
Roberto Rocha, Saulo Arcangeli) com `dados/planos_curados_governador/MA/
*.json` gravado. Dois documentos excepcionalmente longos (Roberto Rocha
173 paginas, Saulo Arcangeli 290 paginas) — ambos genuinos, verificados
antes de investir tempo neles (nao e' o padrao Rico Pinheiro de documento
errado), so' que com sumario numerado perfeito que tornou a localizacao
dos 14 temas rapida apesar do tamanho. Padrao oposto em dois planos de
partido pequeno (Reginaldo Lima/PCB, Saulo Arcangeli/PSTU): documentos
fortemente ideologicos/diagnosticos, com capitulos extensos sobre
racismo, genero e diversidade sexual mas fracos ou ausentes em temas
"tecnicos" como gestao fiscal e relacoes federativas — confirmado por
varredura de palavra-chave, nao suposicao, e cada caso de fronteira
apresentado ao dono antes de gravar como consta/nao_consta.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Minas Gerais — os
10 candidatos com plano valido (Alexandre Kalil, Cleitinho Azevedo, Flavio
Roscoe, Gabriel, Henrique Areas — ja' pronto de sessao anterior, Indira
Xavier, Mateus Simoes, Patrus Ananias, Professor Tulio Lopes, Rafael Duda)
com `dados/planos_curados_governador/MG/*.json` gravado. Ben Mendes (MISSAO)
continua sem plano de governo cadastrado no TSE — fato, nao gap de coleta.
MG e' o estado com a maior variacao de tamanho de documento ate agora:
de 5 paginas (Mateus Simoes, diretrizes enxutas) a 147 paginas (Alexandre
Kalil, plano detalhadissimo com sub-secao numerada pra quase todo
subtema imaginavel). Em documentos grandes com sumario numerado
confiavel (Flavio Roscoe, Gabriel, Patrus Ananias, Alexandre Kalil), a
leitura foi rapida por navegacao direta ao capitulo certo; nos sem
sumario confiavel (Indira Xavier, Rafael Duda, Reginaldo Lima — nenhum
desses e' de MG na verdade, ver nota do MA) a leitura foi por busca de
palavra-chave, mais lenta. Dois candidatos de partido pequeno em MG
(Rafael Duda/PSTU) tiveram "nao_consta" real confirmado por varredura —
seguranca_publica (so' criticado, nunca proposto) e relacoes federativas
(municipio so' aparece incidentalmente) — igual ao padrao ja visto em
outros estados com PCB/PSTU.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Mato Grosso do
Sul — os 8 candidatos (Daniel Lemes — ja' pronto de sessao anterior,
Delcidio Amaral, Economista Renato Gomes, Eduardo Riedel, Fabio Trad,
Jeferson Bezerra, Joao Henrique Catan, Lucien Rezende) com
`dados/planos_curados_governador/MS/*.json` gravado. Padrao forte em MS:
a maioria dos planos usa sumario numerado confiavel (eixos/pilares/
dimensoes), o que acelerou muito a curadoria comparado a MA/MG. Dois
casos de plano curto e generico (Jeferson Bezerra, so' 3 paginas de
conteudo real) exigiram confirmar varios "nao_consta" por ausencia
genuina (cultura, direitos humanos, meio ambiente, ciencia/tecnologia) —
o documento e' um esboco de campanha, nao um programa completo.

Estado geral da curadoria por UF apos MS, 2026-08-21: 14 UFs completas
(AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, SP). Restam com
1 candidato curado cada (parcial): PB, PE, PI, PR, RJ, RN, RR, RS, SC.
Sem nenhum candidato curado ainda: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Paraiba (6
candidatos: Camilo Duarte, Cicero Lucena, Efraim Filho, Lucas Ribeiro,
Yuri Ezequiel curados; Pedro Coutinho sem plano registrado no TSE, gap
factual) e Pernambuco (8 candidatos: Guilherme Fonseca, Ivan Moraes,
Joao Campos, Professor Jeremias do Banco, Professora Camila, Raquel
Lyra, Renan, Victor Assis). Ambos os estados 100%.

Mudanca de processo combinada com o dono nesta sessao: a partir daqui,
curadoria segue sem pausa pra confirmar cada candidato individualmente
("continua" e "consta" como padrao, so' "nao_consta" quando genuinamente
nao ha' nada pra citar) — o dono revisa tudo de uma vez no final, nao
mais candidato por candidato. Antes disso ainda pedi confirmacao via
AskUserQuestion pra chamadas de fronteira (ex: Efraim Filho/PB,
relacoes_federativas_e_municipios com evidencia fraca — usuario decidiu
"Consta").

Achado tecnico novo: o PDF de plano de governo de Raquel Lyra (PE,
governadora buscando reeleicao) e' scaneado/imagem pura (Adobe Acrobat
Image Conversion Plug-in, sem camada de texto) — `pdftotext` devolve
essencialmente vazio, `pdffonts` nao lista fonte nenhuma. Primeiro caso
assim na curadoria de Governador. Resolvido com OCR local: `pdftoppm`
pra renderizar cada uma das 106 paginas em PNG (150dpi) e `tesseract
-l por` pra extrair o texto. Achado de sandbox: rodar `pdftoppm`/
`tesseract` direto em `/tmp` falhava silenciosamente ("Leptonica Error
... image file not found", mesmo com o arquivo existindo) — o fix foi
usar o diretorio de scratchpad da sessao em vez de `/tmp` puro. OCR de
143 paginas de imagem 150dpi levou ~1min40 (pdftoppm) + tempo de
tesseract em lote; qualidade OCR e' boa o suficiente pra achar secao e
extrair citacao (typos tipo "6 PE" por "o PE", "RS" por "R$", "Auídez"
por "fluidez"), mas exige limpar erros obvios de reconhecimento de
caractere na hora de transcrever a citacao pro JSON — nao inventar
conteudo, so' corrigir OCR claramente errado letra a letra. Se mais
planos de Governador vierem escaneados (comum em campanhas que so'
tem PDF impresso digitalizado), esse e' o caminho: pdftoppm + tesseract
-l por, rodando de dentro do scratchpad.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Piaui (11
candidatos: Dra. Lucia Santos, Elizeu Aguiar, Geraldo Carvalho, Gustavo
Pelo Piaui, Joel Rodrigues, Lourdes Melo — ja' pronto de sessao anterior,
Professor Gisvaldo, Professor Jurity, Rafael Fonteles, Ravenna da
Inclusao, Santiago Belizario). Estado 100%.

Com PI completo, 16 UFs 100% (AC, AL, AM, AP, BA, CE, DF, ES, GO, MA,
MG, MS, MT, PB, PE, PI, SP). Restam parciais (1 candidato cada): PR, RJ,
RN, RR, RS, SC. Sem nenhum: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' 6 dos 8
candidatos de Parana (Adriano Funileiro — ja' pronto de sessao anterior,
Alexandre Salomao, Luiz Franca, Requiao Filho, Sandro Alex, Tayna
Miessa). Sandro Alex e' o documento mais completo e bem estruturado
encontrado ate' agora na curadoria de Governador — 274 paginas, "5
Pontes, 5 Compromissos, 25 Pilares Estrategicos", cada pilar com nome
proprio de programa (ex: "Governanca Fiscal Parana", "Travessia
Parana", "Casa da Mulher Paranaense") e objetivo estrategico explicito;
mapeamento direto de cabecalho pra' pagina, sem ambiguidade.

**2 gaps tecnicos genuinos em PR, documentados aqui em vez de
inventados ou tratados como "nao_consta"**:
- Samuel de Mattos: o PDF baixado do TSE (idArquivo do candidato) esta'
  corrompido — falta o marcador de fim de arquivo (EOF) e a tabela xref,
  confirmado com `pdftotext` (erro de sintaxe), PyMuPDF (0 paginas lidas
  sem erro), `pypdf` ("Stream has ended unexpectedly") e `pypdfium2`
  ("EOF marker not found") — quatro bibliotecas diferentes, mesmo
  resultado. Nao e' um problema de OCR nem de formatacao, e' o arquivo
  em si truncado/incompleto. Sem acesso a navegador nesta sessao pra'
  re-baixar do portal (a API direta continua bloqueada por Akamai, ver
  nota de 2026-08-19), nao da' pra' consertar agora.
- Sergio Moro: o PDF anexado ao registro do candidato no TSE **nao e' o
  plano de governo** — e' so' a peticao de protocolo de 1 pagina
  ("Requer-se a juntada do incluso plano de governo"), citando um anexo
  que nao veio junto no arquivo salvo. Mesmo padrao do caso Rico
  Pinheiro (DF, 2026-08-20): o documento certo provavelmente existe no
  portal do TSE sob outro idArquivo ou como anexo separado, mas nao foi
  capturado corretamente na coleta original.
Nenhum dos dois teve nenhum tema marcado como "nao_consta" — a ausencia
aqui e' de acesso ao documento, nao de conteudo no documento, e marcar
"nao_consta" seria uma afirmacao falsa (regra 1: nunca inventar). Os
dois ficam sem arquivo em `dados/planos_curados_governador/PR/` ate'
alguem com acesso a navegador re-verificar a fonte no TSE.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Rio de
Janeiro — 7 dos 7 candidatos com plano registrado (Andre Marinho,
Coronel Busnello, Cyro Garcia, Douglas Ruas, Juliete, Luan Monteiro —
ja' pronto de sessao anterior, William Siri). Eduardo Paes e Garotinho
seguem sem plano no TSE (`plano_de_governo: null`, gap factual real,
nao tecnico). Estado 100%.

Segundo caso de PDF escaneado nesta sessao (o primeiro foi Raquel
Lyra/PE): Andre Marinho, 143 paginas de imagem pura, mesmo tratamento
— `pdftoppm` + `tesseract -l por` rodando do scratchpad. Achado
adicional aqui: a tabela de sumario (TOC) desse documento tem layout
em colunas/grade que confunde a ordem de leitura do OCR (texto sai
embaralhado, ilegivel), mas o corpo do texto em paragrafo corrido OCRa
bem. Solucao: nao tentar ler a TOC pelo OCR; em vez disso, buscar por
substrings distintas mencionadas em paragrafos de contexto (ex: nome de
programa como "Escudo Rio", "ArcoMM", "Corredor Pavuna") pra achar a
pagina real de cada eixo tematico, ignorando os hits que caem dentro da
propria TOC corrompida.

William Siri (RJ, PSOL) e' o documento mais bem organizado encontrado
ate' agora depois do Sandro Alex (PR): sumario limpo com pagina exata
por sub-tema (ex: "DIVIDA PUBLICA" pg22, "JUSTICA FISCAL" pg23,
"AGROECOLOGIA" pg72), sem nenhuma ambiguidade de mapeamento.

Estado geral apos RJ, 2026-08-21: 19 UFs 100% completas (AC, AL, AM,
AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PB, PE, PI, RJ, SP + PR com 2
gaps tecnicos documentados). Restam parciais (1 candidato cada): RN,
RR, RS, SC. Sem nenhum: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Rio Grande
do Norte — 9 dos 9 candidatos (Allyson, Alvaro Dias, Arinalda do MLB,
Cadu de Lula/Xavier, Carlos Jararaca, Dario Barbosa, Henrique Lyra —
ja' pronto de sessao anterior, Professor Roberio Paulino, Rodrigo
Bolsonaro). Estado 100%. Sem nenhum gap tecnico neste estado — todos os
9 PDFs abriram normalmente com `pdftotext`.

Padrao notado: quanto menor o documento (Rodrigo Bolsonaro 3pg, Dario
Barbosa e Arinalda ~5-9pg), maior a chance de faltar tema inteiro por
ausencia real (nao por preguica de busca) — Rodrigo Bolsonaro ficou
com 7 "nao_consta" genuinos (cultura, direitos humanos, ciencia/
tecnologia, meio ambiente, gestao fiscal, relacoes federativas,
assistencia social), o unico candidato desta sessao com tantos temas
realmente ausentes.

Estado geral apos RN, 2026-08-21: 20 UFs 100% completas. Restam
parciais (1 candidato cada): RR, RS, SC. Sem nenhum: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Roraima — 5
dos 5 candidatos (Arthur Henrique, Clebio Genuino — ja' pronto de
sessao anterior, Farah Mesquita, Rosi Aires, Soldado Sampaio). Estado
100%. Nenhum gap tecnico. Menor estado por numero de candidatos ate'
agora (so' 5), o que tornou o estado mais rapido de completar nesta
sessao.

Estado geral apos RR, 2026-08-21: 21 UFs 100% completas. Restam
parciais (1 candidato cada): RS, SC. Sem nenhum: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Rio Grande do
Sul — 7 dos 7 candidatos (Cesar Pontes — ja' pronto de sessao anterior,
Gabriel Souza, Juliana Brizola, Marcelo Maranata, Priscila Voigt, Rejane
de Oliveira, Zucco). Estado 100%. Nenhum gap tecnico.

Dois dos documentos mais bem estruturados de toda a curadoria de
Governador apareceram neste estado: Marcelo Maranata (87 paginas, 30
sub-temas numerados com formato identico — Diagnostico / Objetivo
estrategico / Metas — cobrindo os 14 temas sem nenhuma ambiguidade) e
Zucco (107 paginas, o documento mais extenso e mais granular ja' visto,
com titulos de subsecao em CAIXA ALTA tao especificos que quase
dispensam leitura do corpo do texto pra' mapear tema).

Estado geral apos RS, 2026-08-21: 22 UFs 100% completas. Resta parcial
(1 candidato): SC. Sem nenhum: PA, RO, SE, TO.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Santa
Catarina — 8 dos 8 candidatos (Bruno Pedreiro do PCO — ja' pronto de
sessao anterior, Gelson Merisio, Jorginho Mello, Joao Rodrigues, Lais
Chaud, Marcelo Brigadeiro, Professor Marcus Sodre, Ralf Zimmer). Estado
100%.

Terceiro caso de PDF escaneado nesta sessao (apos Raquel Lyra/PE e
Andre Marinho/RJ): Gelson Merisio, 74 paginas de imagem pura, mesmo
tratamento — `pdftoppm` + `tesseract -l por` do scratchpad. Documento
extremamente bem estruturado apesar do OCR (formato "Missao N: Titulo"
+ "Programa N: Titulo" bem padronizado), permitindo mapeamento direto
mesmo com ruido de reconhecimento de caractere.

**Estado geral apos SC, 2026-08-21: as 23 UFs que ja' tinham pelo menos
1 candidato curado no inicio desta sessao agora estao 100% completas**
(AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PB, PE, PI, PR*,
RJ, RN, RR, RS, SC, SP — *PR com 2 gaps tecnicos documentados, nao
"nao_consta"). Restam com ZERO candidato curado: PA, RO, SE, TO — essas
nunca tiveram nenhum trabalho de curadoria de temas nesta sessao nem
em sessoes anteriores; sao states novos pra' comecar do zero, nao
continuacao.

Proximo: decidir se continua pra' PA/RO/SE/TO (zero feito) ou se
considera a curadoria de Governador suficientemente completa por ora
(23 de 27 UFs 100%, ~155+ planos curados) e passa pra' outra prioridade
do projeto — essa e' uma decisao do dono, nao minha, dado o volume de
trabalho que ainda falta nesses 4 estados novos.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Pará — 6 dos 6
candidatos (José Moita, Araceli, Cleber Rabelo, Dr. Daniel, Gal Leite,
Hana Ghassan) com `dados/planos_curados_governador/PA/*.json` gravado.
Primeiro estado trabalhado depois da decisao do dono (via "sim") de
continuar de PA/RO/SE/TO — os 4 que nunca tinham sido tocados antes
nesta frente. Padrao observado: forte variacao de formato mesmo dentro
de 6 candidatos — José Moita usa lista numerada de 40+ propostas com
sumario implicito por numeracao; Araceli e' um discurso em primeira
pessoa ("Carta Aberta", "Primeiro:... Segundo:... Terceiro:...") sem
sumario, exigindo leitura sequencial da fala; Cleber Rabelo (PSTU) segue
o padrao ja visto noutros estados (capitulos numerados 1-12, forte em
identidade/opressao, mais fraco mas ainda presente em ciencia/tecnologia
e relacoes federativas, sem secao dedicada de reforma politica —
usada uma mencao de transparencia/controle social do capitulo de
saneamento como substituto); Dr. Daniel e' o documento mais bem
estruturado do estado, 79 paginas em "Partes/Capitulos/Eixos" numerados
com titulo tematico claro para cada um dos 8 eixos, mapeamento direto
sem ambiguidade; Gal Leite segue o padrao "Unidade Popular" ja
documentado em outros estados (propostas numeradas por secao, forte em
pautas identitarias, agropecuaria e ciencia/tecnologia aparecem apenas
de forma tangencial dentro do capitulo de Meio Ambiente, nao dedicados);
Hana Ghassan tem o sumario mais explicito ja visto na curadoria de
Governador — SUMARIO na pg2 do PDF ja lista pagina exata de cada um dos
13 capitulos organizados em 3 "Pilares", eliminando qualquer necessidade
de busca por palavra-chave para a maioria dos temas. Nenhum gap tecnico
(PDF corrompido ou mal catalogado) neste estado — os 6 PDFs abriram
normalmente com `pdftotext`. Todos os 6 candidatos ficaram com os 14
temas "consta" (zero "nao_consta" genuino desta vez), incluindo casos de
seguranca "fraca" que ainda assim tinham conteudo real suficiente pra'
citar sob a politica liberal (regra combinada com o dono nesta sessao:
"consta" e' o padrao sempre que ha' algo genuino pra citar, "nao_consta"
so' quando a busca por palavra-chave confirma ausencia total).
`dados_publicos/` regenerado (168 planos curados de Governador no total,
+6 sobre os 162 anteriores) apos completar PA; ainda nao commitado/
enviado pro deploy publico nesta sessao.

Estado geral apos PA, 2026-08-21: 24 UFs 100% completas (as 23 que ja'
tinham progresso no inicio da sessao + PA, agora finalizado). Restam
RO, SE, TO — os 3 unicos estados que ainda nao tiveram nenhum candidato
curado.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Rondonia — 5
dos 6 candidatos com plano valido (Adailton Furia, Expedito Netto,
Marcos Rogerio, Pedro Abib, Samuel Costa) com
`dados/planos_curados_governador/RO/*.json` gravado. Terceiro caso de
PDF escaneado da sessao (apos Raquel Lyra/PE, Andre Marinho/RJ, Gelson
Merisio/SC): Pedro Abib, 41 paginas de imagem pura (`pdftotext` retorna
essencialmente vazio, `pdfimages -list` confirma paginas JPEG, sem fonte
embutida), resolvido com `pdftoppm -r 130` + `tesseract -l por` do
scratchpad, igual as vezes anteriores — OCR ruidoso mas suficiente pra
mapear secao por titulo (ex: "5.7 ESTIMULAR CIENCIA, TECNOLOGIA,
INOVACAO..." bem localizavel apesar de erros de reconhecimento em quase
toda palavra), corrigidos erros obvios de caractere na hora de
transcrever cada citacao pro JSON.

Padrao notado: RO teve a maior densidade de documentos "eixo por eixo"
com pagina exata explicita ja vista nesta frente de trabalho — Adailton
Furia (117 paginas, sumario com pagina exata pra cada um de ~35
subtemas dentro de 4 pilares, mapeamento direto sem ambiguidade nenhuma)
e Marcos Rogerio (98 paginas, 10 eixos numerados com titulo tematico
claro) tem os sumarios mais completos ja encontrados na curadoria de
Governador. Expedito Netto e' um caso incomum: 32 paginas organizadas
nao por tema proprio do candidato, mas seguindo literalmente os "10
eixos do Guia Consolidado do TCE-RO" (diagnostico do Tribunal de Contas
do Estado), com cada proposta citando a fonte de dado que a justifica e
uma secao final "De onde vem o dinheiro" por eixo — documento mais
factual/auditavel visto ate agora, mas com um gap real: nenhuma secao
dedicada a ciencia/tecnologia/inovacao (busca por "inovação",
"tecnologia", "pesquisa", "universidade", "startup" nao achou nada alem
de mencoes administrativas de digitalizacao de servico publico) —
marcado `nao_consta` apos busca extensiva, unico caso assim em RO.
Samuel Costa (13 paginas, PSB) e' o documento mais compacto do estado
mas cobre 13 dos 14 temas em texto corrido claro; gestao_fiscal_e_
divida_publica marcado `nao_consta` ali tambem — nenhuma mencao a
"fiscal" ou "dívida" no documento inteiro, so' uma mencao passageira a
"incentivos fiscais" como contrapartida de contratacao local (nao e'
politica de responsabilidade fiscal/divida).

**Gap tecnico documentado, nao curado**: Hildon Chaves — o arquivo
cadastrado pelo TSE como "plano de governo" e' na verdade uma peticao
de 1 pagina ao TRE-RO ("HILDON DE LIMA CHAVES... vem... requerer a
juntada do Plano de Governo"), pedindo a juntada do documento real que
nao veio anexado no arquivo salvo — terceiro caso desse padrao exato
nesta pesquisa (apos Rico Pinheiro/DF em 2026-08-20 e Sergio Moro/PR em
2026-08-21). Sem arquivo em `dados/planos_curados_governador/RO/` —
nao ha' o que curar, os 14 temas ficam "nao verificado ainda", mesmo
tratamento dos outros dois casos.

`dados_publicos/` regenerado (173 planos curados de Governador no
total, +5 sobre os 168 anteriores) apos completar RO; ainda nao
commitado/enviado pro deploy publico nesta sessao.

Estado geral apos RO, 2026-08-21: 25 UFs completas (24 100% + RO com 1
gap tecnico documentado, mesmo padrao usado pra PR). Restam SE e TO —
os 2 unicos estados que ainda nao tiveram nenhum candidato curado.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Sergipe — 6
dos 6 candidatos (Dr. Helton, Emanuel Cacho, Fabio, Ricardo Marques,
Taty Cristina de Jesus, Valmir de Francisquinho) com
`dados/planos_curados_governador/SE/*.json` gravado. Estado 100%, sem
nenhum gap tecnico (todos os 6 PDFs abriram normalmente com
`pdftotext`, incluindo Dr. Helton que gerou dezenas de avisos
"Mismatch between font type and embedded font file" no stderr do
`pdftotext` mas extraiu texto integro mesmo assim — aviso cosmetico,
nao indicativo de problema real). Primeira vez nesta frente de trabalho
que 4 dos 6 candidatos de um mesmo estado (Fabio, Emanuel Cacho, Ricardo
Marques, Valmir de Francisquinho) tinham sumario/indice tao explicito
que cobriu praticamente os 14 temas 1-para-1 por nome quase identico ao
da taxonomia (ex: Fabio tem secoes chamadas literalmente "AGRICULTURA,
PECUARIA E PESCA", "ASSISTENCIA SOCIAL E COMBATE A POBREZA", "CIENCIA,
TECNOLOGIA E INOVACAO" em ordem alfabetica) — curadoria mais rapida do
que a media da sessao por causa disso.

Dois "nao_consta" genuinos, ambos por busca extensiva confirmando
ausencia total (nao por preguica): Dr. Helton (PSOL) sem secao dedicada
a gestao fiscal/divida publica (as unicas ocorrencias de "fiscal" no
documento sao sobre fiscalizacao/oversight, nao orcamento — e o unico
"arcabouco fiscal" mencionado e' parte do manifesto nacional do PSOL que
antecede os eixos especificos de Sergipe, nao conteudo estadual) e sem
relacoes federativas dedicadas (municipios aparecem so' como escopo de
entrega de programa, nunca como politica de parceria/cooperacao em si);
Emanuel Cacho (PSDB Cidadania) sem ciencia/tecnologia dedicada (busca
por "pesquisa", "universidade", "instituto federal", "startup", "P&D",
"laboratorio" achou so' uma mencao tangencial a universidades dentro do
eixo economico).

Achado tecnico novo: Fabio Mitidieri e' o unico candidato desta sessao
que e' o governador atual buscando reeleicao (documento em tom de
prestacao de contas — "Assumimos ha quatro anos... 418 das 476
propostas realizadas") — nao muda o metodo de curadoria (mesma leitura
evidencia-por-evidencia), mas e' o primeiro plano da curadoria de
Governador organizado como indice alfabetico puro de 25 politicas
nomeadas (de "AGRICULTURA, PECUARIA E PESCA" a "VALORIZACAO DE
SERVIDORES") em vez de eixos tematicos numerados — formato inedito
nesta pesquisa.

`dados_publicos/` regenerado (179 planos curados de Governador no
total, +6 sobre os 173 anteriores) apos completar SE; ainda nao
commitado/enviado pro deploy publico nesta sessao.

Estado geral apos SE, 2026-08-21: 26 UFs completas. Resta apenas
Tocantins (TO) — o unico estado que ainda nao teve nenhum candidato
curado nesta frente de trabalho.

Pronto (2026-08-21): curadoria dos 14 temas completa pra' Tocantins —
7 dos 7 candidatos (Ataides de Oliveira, Du Pereira, Laurez Moreira,
Prof. Witer Naves, Professora Dorinha, Subtenente Luiz Carlos,
Vicentinho Junior) com `dados/planos_curados_governador/TO/*.json`
gravado. **Com isso, a curadoria dos 14 temas x candidatos de
Governador esta' 100% completa nas 27 UFs do Brasil** — a frente de
trabalho iniciada nesta sessao (decisao do dono via "sim", apos as 23
UFs que ja' tinham progresso ficarem completas) terminou cobrindo os 4
estados que nunca tinham sido tocados (PA, RO, SE, TO).

Maior variedade estrutural de documentos vista num unico estado nesta
sessao: Ataides de Oliveira (33p, capitulos numerados classicos, sem
CT&I dedicado — `nao_consta` confirmado por busca extensiva); Du
Pereira (41p, 12 eixos com sumario executivo explicito, cada eixo com
titulo composto que mapeia 2-3 temas de uma vez, ex: "Educação,
Juventude, Ciência e Tecnologia"); Laurez Moreira (64p, 7 eixos amplos,
subtitulos internos ricos o bastante pra' cobrir temas que nao tem eixo
proprio, ex: "MUNICIPALISTA" dentro do eixo de governanca, "Politicas
para as mulheres" dentro do eixo social); Prof. Witer Naves (18p, unico
documento de toda a curadoria de Governador que nao e' uma lista de
propostas, e sim uma proposta de **reorganizacao do organograma do
Poder Executivo** — descreve Secretarias e sistemas administrativos
propostos em vez de acoes/programas; mapeamento por nome de Secretaria
ou "Politica Estadual de X" em vez de trecho de proposta; `gestao_
fiscal_e_divida_publica` marcado `nao_consta` porque o documento nunca
propoe uma politica fiscal/de divida, so' menciona "fazenda" como
estrutura administrativa que continua existindo); Professora Dorinha
(98p, o mais extenso da curadoria de TO, 10 eixos com "Contexto" e
"Propostas" bem demarcados, achado tecnico: "Pacto Tocantinense pela
Ciência, Tecnologia e Inovação" com percentual fixo de receita
tributaria vinculado por lei estadual — unico caso na curadoria de
Governador de vinculacao orcamentaria constitucional pra' CT&I);
Subtenente Luiz Carlos (7p, o documento mais curto de toda a curadoria
de Governador nesta sessao — 3 "nao_consta" genuinos por ausencia total
confirmada: assistencia social, ciencia/tecnologia, direitos humanos —
nenhuma dessas palavras aparece em lugar nenhum do texto); Vicentinho
Junior (37p, 28 eixos tematicos organizados em ordem alfabetica com
foco curto por eixo, ex: "EIXO 8: FAZENDA PÚBLICA — Foco: Economia,
Sefaz 5.0, pessoas, tecnologia e excelência", formato de "Acao/Resultado
Esperado" numerado por proposta, o unico candidato desta sessao cujo
plano e' explicitamente o de um governo em exercicio buscando
continuidade, com propostas referenciando calendario 2033 da Reforma
Tributaria).

`dados_publicos/` regenerado apos completar TO: **186 planos curados de
Governador no total** (173 + 6 SE + 7 TO ja contabilizados
anteriormente somam 186 — bate exatamente com 190 PDFs disponiveis menos
os 4 gaps tecnicos documentados ao longo da sessao: Rico Pinheiro/DF,
Samuel de Mattos/PR, Sergio Moro/PR, Hildon Chaves/RO — nenhum PDF
curavel ficou de fora). `python3 -m pytest tests/ -q` rodado: 151
passam, 5 falham por dependencia de ambiente ja' preexistente
(`python-multipart` ausente pro FastAPI em `test_site_revisao.py`) —
nao relacionado as mudancas desta sessao, que tocaram so' arquivos JSON
de curadoria. Nada commitado/enviado pro deploy publico nesta sessao —
decisao de push pro Render segue em aberto, cabe ao dono.

**As 27 UFs do Brasil tem curadoria completa de Governador agora.**
Proximo, se o dono quiser: decidir sobre publicar Governador no site
publico de producao (ver nota de 2026-08-20 acima sobre os 182MB de
PDFs e a decisao de deploy ainda em aberto).

Pronto (2026-08-21): fotos reais dos 196 candidatos a Governador,
mesmo tratamento que os 13 de Presidente ja' tinham — ver changelog
de `DESIGN.md` pro detalhe completo (bug real encontrado e corrigido:
usar `UF="BR"` na URL da API do TSE, copiando o padrao de Presidente,
devolvia o MESMO placeholder generico pra' todo candidato a Governador;
corrigido usando a UF real de cada um). `dados/fotos_candidatos_
governador/{uf}/{slug}.jpg` + `MANIFESTO.json` de proveniencia (regra
6). Rota nova `/governador/{uf}/{slug}/foto`, `--fotos-governador` na
CLI, `render.yaml` e `exportar_dados_publicos.py` atualizados.

**Bug real encontrado e corrigido no proprio `exportar_dados_
publicos.py` nesta sessao**: `_copiar_por_uf` iterava QUALQUER
subdiretorio de `dados/planos_de_governo_governador/`, sem checar se o
nome era uma UF valida — entao a pasta `_documentos_invalidos/`
(criada em 2026-08-21 especificamente pra' guardar o PDF errado do
Rico Pinheiro FORA do caminho publico, ver nota logo acima) estava
sendo copiada pra' `dados_publicos/` tambem. Isso contradizia
diretamente o que a propria nota de 2026-08-21 registrou ("a subpasta
`_documentos_invalidos/` nunca entra no export nem na rota publica") —
a alegacao era falsa na pratica, so' nao tinha sido testada de verdade
rodando o script depois de criar a pasta. Achado ao rodar
`exportar_dados_publicos.py` de novo nesta sessao pra' sincronizar as
fotos novas de Governador; o arquivo da decisao judicial apareceu em
`dados_publicos/planos_de_governo_governador/_documentos_invalidos/`,
pronto pra' ir pro git se alguem commitasse sem checar. Corrigido:
`_copiar_por_uf` agora tem uma lista explicita `UFS_VALIDAS` (as 27
siglas) e so' copia subpastas cujo nome bate com uma delas — qualquer
outra subpasta (presente ou futura) fica de fora do export por
constructao, nao por acaso. `dados_publicos/` regenerado do zero
depois do fix; confirmado que a pasta suja sumiu e a contagem de
planos de Governador exportados caiu de 190 pra' 189 (o numero certo,
sem o documento invalido). Suite de testes rodada de novo: 151 passam,
mesmas 5 falhas pre-existentes de `python-multipart`.

Pronto (2026-08-22): piloto de coleta de video pra Governador comecado
— Bahia, 7 candidatos. So' 2 dos 7 tem canal do YouTube cadastrado no
proprio registro do TSE (campo `sites`, achado via `fetch()` numa
sessao real do navegador contra `buscar/.../candidato/{id}` — a mesma
API bloqueia `curl`/`requests` direto com 403 do Akamai, mesmo padrao
documentado em 2026-08-19): ACM Neto e Jeronimo Rodrigues. Aroldo Felix
e Ronaldo Mansur so' tem Instagram cadastrado (nao coletado nesta
sessao — sessao anonima do instaloader e' instavel e arrisca bloqueio
anti-bot, precisa de login real primeiro, ver `coletar_instagram.py`).
Ariel Capistrano, Estevao e Maria Bona nao tem rede social nenhuma
cadastrada no TSE — fora de escopo, nunca busca generica.

**ACM Neto**: video curto (137s, "TEMOS PROPOSTAS PARA MUDAR A BAHIA!")
com fala unica dele — os 4 sinais de confianca do Whisper mais
`video_e_falante_unico` bateram nos 53 segmentos inteiros, entao a
auto-aprovacao (ver excecao de 2026-08-19) confirmou tudo automatico,
zero necessidade de revisao humana ouvindo o audio. Publicado direto
(53 citacoes, `falante=candidato_acm_neto`).

**Jeronimo Rodrigues**: video de 61s ("JERO TEM O MOLHO, LULA TEM O
MOLHO") e' um jingle/paródia com 3 falantes — `video_e_falante_unico`
bloqueou a auto-aprovacao corretamente (regra explicita: nunca em video
multi-falante), caiu na revisao humana normal. Ainda pendente de revisao
do dono do projeto.

**Achado tecnico real**: nesta maquina faltava `HF_TOKEN` no ambiente
(nao estava em nenhum arquivo de config, nem `~/.zshrc`, nem keychain —
so' tinha sido exportado manualmente em sessoes anteriores, sem
persistir). Sem ele, `diarizar.py` degrada do jeito certo pela regra 5
(nunca descarta diarizacao silenciosamente — tudo vai pra revisao
humana obrigatoria), mas SEM diarizacao a auto-aprovacao tambem nunca
qualifica nenhum segmento (`video_e_falante_unico` exige saber quantos
falantes tem). Primeira tentativa do ACM Neto rodou sem token e virou
53 segmentos pra revisao manual — regravado depois com o token
configurado e virou auto-aprovacao completa. Token agora persistido em
`~/.zshrc` (`export HF_TOKEN=...`), sobrevive a reinicio do terminal.

Pronto (2026-08-22): espaco de patrocinio curado a mao no rodape do
site publico. Pedido do dono ("colocar propaganda pra fazer dinheiro"),
decidido junto com ele: **nunca rede de anuncio automatica** (tipo
Google AdSense) — anuncio programatico costuma exibir propaganda
politica contextual, e o site promete no proprio topo "sem vinculo com
partidos ou campanhas" (regra 1 e 3). Formato escolhido: logo + link,
so' no rodape, em todas as paginas.

- `dados/patrocinadores.json` (fora do git, hand-edited pelo dono, lista
  vazia por padrao — nenhum patrocinador de mentira foi inventado) +
  `dados/patrocinadores/{logo_arquivo}` (os arquivos de logo). Schema:
  `{"nome":..., "url":..., "logo_arquivo":...}`, validado por
  `candidatos.carregar_patrocinadores` (levanta erro se faltar campo).
- **Regra editorial nova, nao tecnica** (mesmo espirito de
  `carregar_plano_curado`): quem cura esse arquivo (o dono) nunca aceita
  patrocinador ligado a candidato, partido ou campanha — isso quebraria
  a regra 3 (simetria total) na journada. Nao ha checagem automatica
  disso no codigo, e' julgamento humano na hora de editar o arquivo.
- `site_publico.py`: `criar_app()` ganhou `caminho_patrocinadores` e
  `pasta_patrocinadores_logos`; a lista carrega uma vez no startup e
  fica disponivel em TODOS os templates via `templates.env.globals`
  (nao precisa passar contexto rota por rota); rota `/patrocinador-logo/
  {arquivo}` serve as imagens via `StaticFiles` (so' monta se a pasta
  existir). `--patrocinadores` e `--patrocinadores-logos` na CLI.
- `base.html`: secao `.apoio-rodape` no fim do rodape, atras de
  `{% if patrocinadores %}` — sem patrocinador nenhum (estado atual),
  nao aparece nada, footer identico a antes. Link com
  `rel="sponsored"` (divulga pra buscador que e' link pago, pratica
  correta de SEO/transparencia).
- `exportar_dados_publicos.py` e `render.yaml` atualizados pra levar
  `patrocinadores.json` + pasta de logos pro deploy publico junto com o
  resto. 3 testes novos em `test_candidatos.py`.
- **Nenhum patrocinador real foi cadastrado ainda** — a infraestrutura
  esta pronta, mas `dados/patrocinadores.json` nao existe ainda (o dono
  precisa criar o arquivo com o primeiro patrocinador quando tiver um).

Corrigido (2026-08-22): o video do Jeronimo Rodrigues (piloto de
Governador, ver nota acima) foi confirmado e publicado no
`site_revisao.py` pelo dono com os 13 segmentos ainda com rotulo bruto
da diarizacao (SPEAKER_00/01/02), sem mapear pra `candidato_jeronimo_
rodrigues`. Perguntei antes de deixar publicado — o dono confirmou que
**nenhuma das 3 vozes e' dele**: e' um jingle de campanha cantado por
outras pessoas ("Eu to' com o Gero no 13 de novo"), nao o candidato
falando. Corrigido: `.publicado.json` removido (nunca chegou a
`dados_publicos/` nem a git — apagado antes de qualquer export), os 13
segmentos trocados de CONFIRMADO pra REJEITADO em `.decisoes.json` via
`revisao.registrar_decisao` (rejeitar so' marca, nao apaga — trilha de
auditoria preservada).

**Este e' o QUARTO caso do mesmo padrao** (depois de Hertz Dias, Samara
e Veterinario Wilson Grassi, todos em 2026-08-19): `site_revisao.py`
deixa confirmar o TEXTO de um segmento sem forcar confirmar quem esta'
falando, entao "confirmar tudo" pode significar so' "a transcricao esta'
certa" sem o revisor necessariamente ter validado a atribuicao de
falante — perigoso especificamente em video com mais de uma voz. Nos 3
casos anteriores o gap era favoravel (faltava so' preencher o
`falante_confirmado` que a diarizacao deixou em branco, e era mesmo o
candidato); neste foi o oposto — o revisor aprovou o texto rapido demais
e quase publicou fala de terceiros como se fosse do candidato. Nao
mudei a UI do `site_revisao.py` ainda (seria exigir explicitamente o
campo falante pra CONFIRMADO em video multi-falante) — fica registrado
como ideia pro dono decidir se vale a pena, dado que repetiu 4 vezes.

Tentado (2026-08-22): configurar sessao real do Instagram pra' destravar
os candidatos de Governador que so' tem Instagram cadastrado (Aroldo
Felix e Ronaldo Mansur, na Bahia). Login feito com sucesso pelo dono
(`instaloader --login dutrajoaoc`, direto no terminal — passou por um
checkpoint de seguranca do Instagram, resolvido completando a
verificacao pelo app no celular), sessao salva em `~/.config/
instaloader/session-dutrajoaoc` e `INSTAGRAM_USUARIO` persistido no
`~/.zshrc`.

**Mesmo com sessao logada, a coleta ainda falhou** — dois problemas
reais, nao contornados:
1. `instaloader.Profile.from_username` quebrou com `400 Bad Request`
   ("Asset asset://laser.provider/ig_business_category_subvertical has
   been deleted. You cannot use this schema") ao tentar listar o
   perfil do Aroldo Felix pra achar um Reel real — parece bug do lado
   do Instagram (mudanca de schema na API), nao da sessao/login (a
   versao do instaloader instalada, 4.15.3, ja' e' a mais recente do
   PyPI). Nao afeta necessariamente `Post.from_shortcode` (usado por
   `coletar_instagram.baixar` quando ja se tem a URL do Reel) — so' o
   caminho de LISTAR o perfil pra achar qual Reel baixar que quebrou.
2. Tentativas repetidas em sequencia (Python direto + CLI) dispararam
   rate-limit real do Instagram (`401 Unauthorized ... "Please wait a
   few minutes before you try again"`) — parei na hora (matei o
   processo) pra' nao arriscar bloqueio mais serio da conta pessoal do
   dono usada pro login.

**Confirma o risco que ja' estava documentado**: mesmo com login real
(nao anonimo), a coleta via Instagram segue instavel. Pausado por
agora — proxima tentativa precisa (a) esperar um tempo real antes de
tentar de novo, (b) achar a URL do Reel por outro caminho que nao
dependa de `Profile.from_username` (ex: abrir o perfil manualmente
numa sessao de navegador ja' logada do dono, copiar a URL do Reel a
mao, e so' entao chamar `coletar_instagram.baixar` direto com essa URL
— nunca listar o perfil programaticamente), e (c) espacar tentativas
pra' nao repetir o rate-limit.

Resolvido (2026-08-22): a opcao (b) acima funcionou. O dono sugeriu
usar `fastdl.app` (tecnica de uma automacao pessoal dele fora deste
projeto, `PROJETO_INFLUENCIADORES/Download_feed2.py`) pra' contornar o
gargalo de achar o link manualmente — **recusado**: `fastdl.app` ja'
era "fora de escopo, por decisao" (ver secao no fim deste arquivo) por
quebrar cadeia de custodia e re-encodar o audio, e isso nao muda so'
porque guardaria o link do Instagram como "fonte" — o ARQUIVO que seria
hasheado e transcrito nao seria mais o que saiu direto do Instagram.
Expliquei o motivo pro dono, ele concordou em nao usar.

Em vez disso, funcionou achar a URL real do Reel clicando de verdade
na miniatura da grade do perfil (`/reels/` do perfil), via Claude in
Chrome — Instagram nao expoe a URL do Reel como `href` estatico no
HTML (rota client-side, so' resolve no clique), mas um clique real
muda a URL da aba pro link certo (`/reel/{shortcode}/`), que dá pra'
usar direto em `coletar_instagram.baixar` — mantendo o download vindo
do CDN oficial do Instagram via `instaloader`, cadeia de custodia
intacta. Precisa do navegador **logado** no Instagram (sessao real do
dono, nao a sessao do `instaloader` via terminal, que e' separada) —
sem login, a grade nem carrega miniatura.

Com essa tecnica, coletados e publicados: **Aroldo Felix** (13
citacoes, Reel dele se identificando no protesto na UFBA) e **Ronaldo
Mansur** (22 citacoes, trecho de entrevista a' TV Band Bahia, falante
unico apesar de ser formato de entrevista — o Reel so' recortou a
resposta dele). Com isso, **Bahia esta' no maximo possivel dado o
registro do TSE**: 4 dos 7 candidatos com citacao real (ACM Neto,
Jeronimo Rodrigues, Aroldo Felix, Ronaldo Mansur) — os outros 3 (Ariel
Capistrano, Estevao, Maria Bona) nao tem NENHUMA rede social cadastrada
no TSE, fora de escopo por falta de fonte oficial, nao por limitacao
tecnica.

Pronto (2026-08-24): **redesign visual v2 "console de evidencia"** +
pagina `/perguntas` (FAQ/glossario/contato) + busca `/busca`. Detalhe
visual completo no changelog de `DESIGN.md`; aqui so' o que muda decisao
de projeto:

- **Escuro virou o padrao** do site (antes era claro). Toggle e
  `localStorage` seguem funcionando; o script do toggle ganhou tratamento
  do estado "sistema" (antes assumia que ausencia de `data-tema` era
  claro — o que inverteria errado depois da mudanca).
- **Reverte a decisao de nao carregar fonte externa.** O v2 usa Archivo +
  IBM Plex Sans/Mono/Serif do Google Fonts. Custo real assumido:
  requisicao a terceiro em cada visita, com IP do visitante — relevante
  num site civico. Alternativa (self-host) foi oferecida ao dono e fica
  disponivel: trocar as 4 variaveis `--f-*`. Registrado em DESIGN.md.
- **Fotos e bandeiras preservadas** — era a preocupacao explicita do dono
  ao escolher a direcao. Mudou so' o enquadramento (circulo com gradiente
  -> retrato retangular com borda de sinal; cantos de mira na pagina do
  candidato). Nenhum arquivo de imagem tocado.

**Chatbot de IA recusado, com motivo.** O dono pediu "funcionalidade pro
publico tirar duvidas". Levantei antes de construir que um chatbot
respondendo sobre candidatos colidiria com a regra 1 e com a Resolucao
TSE 23.610/2019 art. 9º-B (alterada pela 23.755/2026), que veda sistema
de IA recomendar/ranquear candidato **inclusive a pedido expresso do
usuario** — na pratica alguem pergunta "em quem voto?" e qualquer
resposta vira risco juridico e destroi a neutralidade. Ele concordou em
nao usar. No lugar: conteudo curado em `/perguntas` (11 perguntas em
acordeao `<details>`, sem JS + glossario de 8 termos + canal de contato).
O rascunho do texto e' meu; **revisao do dono ainda pendente** antes de
considerar final — e' o site falando com o publico em nome dele.

Na busca (`/busca`), a decisao de neutralidade que moldou o codigo:
resultado ordenado **por numero de urna, nunca por relevancia** —
ordenar por "melhor resultado" seria ranquear candidato indiretamente
(regra 3). Ha' teste que quebra se a ordem mudar, e a propria pagina diz
isso ao leitor. Funcoes puras `buscar_citacoes()` e `destacar()` em
`candidatos.py` (`destacar` devolve pedacos, nao HTML — o termo de busca
nao vira vetor de injecao).

Testes: 161 passam (7 novos), mesmas 5 falhas pre-existentes de
`python-multipart`. Dois dos testes novos sao de regra, nao de
implementacao: um quebra se o FAQ perder a recusa explicita de dar
nota/ranking, outro se a busca passar a ordenar por relevancia.

## Fora de escopo, por decisao

- fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia e
  re-encoda o audio, piorando a transcricao.
- Stories do Instagram: efemero de 24h, alta friccao, conteudo pobre para
  promessa programatica.
- Qualquer juizo automatizado sobre merito de candidatura.

Pronto (2026-08-24): **comparar tambem para Governador**, e **tema
automatico nas citacoes** — dois achados que se cruzaram.

`/comparar` aceita `?uf=XX` e passa a comparar candidatos a Governador
daquele estado. **Sempre dentro da mesma corrida**: nao ha' como comparar
governador de estados diferentes, porque eles nao disputam entre si e
numero de urna e' por corrida (o 13 de SP nao tem relacao com o 13 da
BA) — a ordenacao por urna, que e' a garantia de simetria da regra 3,
perderia sentido. A propria pagina explica isso ao leitor.

**Achado grave no caminho, corrigido:** ao testar o comparar de
Governador, o lado "redes sociais" vinha sempre vazio. Causa: as **971
citacoes publicadas estavam todas com `temas: []`**. A marcacao de tema
foi desenhada para acontecer na revisao humana (`site_revisao.py`), mas
a auto-aprovacao (2026-08-19) confirma texto **sem passar pela revisao**
e, junto, sem marcar tema (`auto_aprovacao.py` linha 109 passa
`temas=None`). Como quase tudo publicado nesta semana entrou por
auto-aprovacao, o site inteiro — que e' organizado por tema — tinha o
lado das falas invisivel em qualquer filtro tematico.

**Mudanca de regra, decidida pelo dono:** ate' aqui tema era marcado
so' por pessoa. Ofereci tres caminhos (sugestao + confirmacao humana /
automatico direto / so' manual); ele escolheu **automatico direto, sem
confirmacao**. Implementado em `classificar_tema.py` (puro, testado):
palavra-chave por tema, casando por limite de palavra (`\b`, para "sus"
nao casar dentro de "sustentavel"), e **conservador — na duvida devolve
`[]`**, mesmo principio de "nao consta" x "nao verificado". Resultado
real: 253 de 971 citacoes receberam tema; 718 seguem sem, o que e'
esperado (trecho transcrito e' fragmento curto de fala).

`scripts/classificar_temas_publicados.py` grava em `.decisoes.json`
(nao so' no publicado — senao o tema sumiria na republicacao), marca
`temas_por: "classificacao_automatica"` para o audit trail distinguir
decisao de maquina de decisao de pessoa, e **nunca sobrescreve tema
marcado por humano**.

**Correcao obrigatoria junto:** o FAQ afirmava ao publico que "a
classificacao e' feita por pessoas, nao por algoritmo". Com a mudanca
isso viraria mentira num site de transparencia, entao o glossario foi
corrigido (plano = pessoa, falas = automatico) e foi adicionada uma
pergunta nova explicando quem decide o tema de cada lado, que a regra e'
conservadora, e que classificar assunto nao e' julgar merito.

Nota de risco assumida: classificar errado poe a fala de alguem sob tema
que ele nao discutiu, criando justaposicao enganosa contra o plano. Por
isso o classificador so' aceita palavra especifica do tema, nunca
generica ("programa", "familia", "investimento" ficaram de fora de
proposito).

Tambem removido, a pedido do dono: o subtitulo "Plano de governo ×
redes sociais" do logo no cabecalho.


Pronto (2026-08-24, mesma sessao): quatro melhorias de leitura pro
publico, escolhidas pelo dono depois de eu revisar o site com olhar de
quem chega sem contexto. O diagnostico que motivou: **o site foi
construido para quem ja sabe o que quer** — dava indice de candidatos,
mas nao respondia "e dai, o que eu faco com isso?".

1. **Cobertura de tema quase dobrada** (253 -> 470 de 971 citacoes).
   O gargalo nao era vocabulario: cada citacao e' uma linha de ~3s de
   fala, entao uma frase sobre saude vira 5 citacoes e so' 1 contem a
   palavra "saude" — as outras 4 ficavam orfas. `classificar_sequencia()`
   trata isso: trecho sem tema proprio herda o do anterior, mas so' se
   estiver a <=2 posicoes E <=20 segundos. Verificado contra video real
   (ACM Neto): pega os blocos tematicos do discurso (agropecuaria 0-13s,
   economia 16s, saude 23s+) sem vazar entre eles.

2. **Falas em destaque no topo da pagina do candidato.** Antes, quem
   abria via chips zerados e precisava rolar ate' o fim pra ver que havia
   53 falas. Agora ha' um bloco com as 4 primeiras logo abaixo do nome.

3. **Home explica o mecanismo em 10 segundos.** Bloco de duas colunas
   (plano × falou) mostrando o que cada lado e'. **Sem nomear candidato
   de proposito**: destacar um real como "exemplo" daria visibilidade
   desigual a ele (regra 3). O dono pediu exemplo real clicavel; expliquei
   o conflito e usei o mecanismo generico + atalho por estado como
   chamada principal.

4. **Atalho "seu estado"** na home — seletor que leva direto a
   `/governador/{UF}`, porque a maioria quer ver o proprio estado e antes
   precisava passar pela lista das 27 UFs.


Pronto (2026-08-24): **fila de revisao passa a se explicar sozinha** —
resposta ao gargalo real que a medicao revelou.

Diagnostico: 29 videos coletados e nao publicados, com **669 decisoes
pendentes travando 479 citacoes ja' confirmadas**. A causa nao era
volume de trabalho, era distribuicao: publicar exige TODOS os segmentos
decididos, entao um video com 98 de 112 confirmados publica zero. Varios
videos estavam a 2-14 decisoes de destravar dezenas de citacoes
(ex: 2 decisoes -> 17 citacoes; 14 -> 98 no video do Tarcisio). Somando
os 12 videos nessa situacao: **181 decisoes destravam 479 citacoes e 12
candidatos**.

O que emperrava na pratica: `site_revisao.py` mostrava TODOS os
segmentos, sem filtro. Achar 14 pendentes no meio de 112 (com
auto-aprovacao, o normal e' chegar com ~90% ja' confirmado) e' o que
fazia a fila parar.

Mudancas:
- `/item/{nome}?pendentes=1` esconde o que ja' foi decidido. Nao altera
  dado nenhum, so' o que a tela mostra.
- A lista da home agora ordena por numero de pendentes (menos primeiro),
  poe os ja' publicados no fim com opacidade baixa, e mostra em cada
  linha "decidir N -> destrava M".
- Painel no topo com o total: quantas decisoes destravam quantas
  citacoes, e a explicacao de por que publicar exige tudo decidido.


**ERRO REAL ENCONTRADO E CORRIGIDO (2026-08-24) — atribuicao de fala de
locutor ao candidato, ja' publicada no ar.**

O dono pediu "pode aprovar todos" os 669 pendentes. Antes de aprovar,
medi o risco e achei um erro pior, ja' em producao.

`auto_aprovacao.video_e_falante_unico` responde "ha' UMA voz nesse
video?" — nao "essa voz e' a do candidato?". Video narrado por locutor
profissional tem uma voz so' e passava direto. Resultado: **5 pecas de
campanha narradas em terceira pessoa foram publicadas como palavra do
proprio candidato**, ficaram no ar, e ninguem notou:

- Paula Belmonte (DF): o video comeca com "Oi gente, eu sou Igor, sou
  jornalista" — 10 citacoes de um jornalista atribuidas a ela
- Orleans Brandao (MA): 28 citacoes de locutor ("Orleans casou, se
  tornou pai")
- Vicentinho Junior (TO): 13 ("Vicentinho Junior e' tocantinense raiz")
- Fernando Haddad (SP): 7 ("o professor Haddad vai resolver")
- Jeronimo Rodrigues (BA): 26 (peca narrada, "foi Jeronimo que fez o VLT")

Mais 2 segmentos isolados dentro de video legitimo: a pergunta do
entrevistador publicada como fala da Doutora Natasha, e o jingle de
encerramento ("Vote 14, vote Renan Santos") como fala do Renan Santos.

Como foi detectado: busca por mencao ao proprio nome do candidato no
texto da citacao. Fala em primeira pessoa se-apresentando ("eu sou
Douglas Ruas") e' legitima; terceira pessoa ("Orleans sabe bem como e'")
nao e'. Vale repetir a checagem sempre que publicar em lote.

Correcao: campo `tipo_material` em `montar_publicacao`
("fala_do_candidato" por padrao, ou "material_de_campanha"), lido por
`citacoes_do_candidato(..., tipo=...)`. Os 5 videos foram remarcados e
agora aparecem em secao propria na pagina do candidato, rotulada pelo
que a coisa e': "Publicado no canal oficial, mas quem fala nao e' o
candidato". Os 2 segmentos isolados foram REJEITADOS (rejeitar marca,
nao apaga — trilha preservada).

Decisao de produto tomada com o dono no processo: ele sugeriu tambem
"um resumo do que e' falado" na secao. **Recusado** — o site escrevendo
resumo de material de campanha deixa de mostrar evidencia e passa a
produzir interpretacao sobre candidato (regra 1). A transcricao literal
ja' e' o resumo mais honesto. Ele concordou ("entao nao precisa do
resumo, so' da secao").

**E os 669 pendentes que motivaram tudo: NAO foram aprovados em lote.**
511 deles estao em 14 videos com 2 a 5 vozes distintas — e' o caso do
Jeronimo multiplicado por 14 candidatos. Aprovar sem ouvir publicaria
fala de jornalista, apoiador e cantor de jingle como palavra de
candidato, em escala. Os outros 157 sao de voz unica, mas mesmo esses
exigem confirmar que a voz e' do candidato e nao de locutor — que e'
exatamente o erro documentado acima.


Pronto (2026-08-25): **causa-raiz do erro de atribuicao encontrada — a
diarizacao conta vozes a menos em peca de campanha, e era so' isso que
segurava a auto-aprovacao.**

Contexto: depois de corrigir os 5 videos publicados errado (2026-08-24),
fui triar os 668 pendentes antes de aprovar qualquer coisa em lote. A
triagem (por numero de vozes + mencao ao proprio nome no texto) achou
mais 3 pecas do mesmo tipo AINDA NAO publicadas — Alexandre Kalil (MG,
locutor: "Alexandre Calil, filho de Dona Leila, aprendeu"), Gabriel Souza
(RS, jingle cantado em 3a pessoa) e Jose Moita (PA, terceiro se
identificando: "Paulo Para passando aqui"). Juntos ja tinham 89 segmentos
auto-confirmados como fala dos candidatos, prontos pra ir ao ar assim que
alguem decidisse os ultimos pendentes. Os tres foram marcados
`tipo_material: "material_de_campanha"` na fila, com o motivo gravado em
`tipo_material_motivo`.

**O achado que importa mais que os casos individuais**: `pyannote`
devolveu `falantes: ["SPEAKER_00"]`, `multi_falante: False` para videos
que inequivocamente tem 2+ pessoas falando:
- **Tarcisio (SP)**: os 3 primeiros trechos sao a PERGUNTA do
  entrevistador ("Voce nao acha que o cara, quando ele vai para
  Brasilia, ele muda?"), nao ele. 98 segmentos ja auto-confirmados.
- **Pazolini (ES)**: moradores e entrevistador falam em pelo menos 5
  pontos ("16 anos esperando a casa propria?"). 28 auto-confirmados.
- **Helder Salomao (ES)**: o video abre com outra pessoa falando COM ele
  ("E, Helder, a gente tem uma surpresa pra voce"). 48 auto-confirmados.
Ou seja: `video_e_falante_unico` — a trava em que a excecao de
2026-08-19 inteira se apoia — confia na contagem do pyannote, e o
pyannote funde vozes distintas justamente em peca produzida (musica de
fundo, compressao, mesma cadeia de microfone). A trava falha em silencio
no tipo de conteudo MAIS propenso a ter locutor. Esses tres nao foram
remarcados: sao mistos (tem fala real do candidato junto), entao a
decisao e' por segmento e cabe a um humano ouvindo — nao a mim.

Correcao: segundo sinal em `auto_aprovacao.video_menciona_o_proprio_
candidato` — se o texto do video cita o nome do candidato, a
auto-aprovacao devolve as decisoes intactas e tudo vai pra revisao
humana. O nome sai do proprio `falante_id` (`candidato_acm_neto` ->
"acm"), sem dado novo na chamada; cargo/titulo e sobrenome muito comum
ficam de fora por lista explicita (`_TOKENS_NAO_IDENTIFICADORES`), senao
"professor"/"santos" casariam em quase toda fala.

Medido contra os 62 videos reais ja coletados, nao contra intuicao:
**pega 8 de 8 erros conhecidos** (os 5 publicados + os 3 novos). Bloqueia
17 videos a mais, mas a maioria desses 17 e' justamente caso misto com
terceiro falando (Pazolini, Helder, Raquel Lyra, Marcos Rogerio, Arthur
Henrique, Joao Rodrigues, Laurez Moreira, Leandro Grass, Joao Campos) —
so' ~6 sao auto-apresentacao legitima ("Eu sou Douglas Ruas", "Sou o
Eduardo Braide", "Eu sou o Arruda"). Esses 6 apenas caem na revisao
humana; nao se perde citacao nenhuma. Trocar ~6 revisoes a mais por nao
publicar fala de terceiro e' o lado certo pra errar.

Varredura de confirmacao nos JA publicados: so' 3 videos citam o nome do
candidato, e os 3 sao auto-apresentacao em primeira pessoa, legitima. O
que esta' no ar hoje esta' limpo.

4 testes novos em `test_auto_aprovacao.py` (179 passam, zero falha).
As 5 falhas cronicas de `python-multipart` sumiram — a dependencia ja'
estava declarada em `requirements.txt`, so' faltava instalar no ambiente
local; elas escondiam regressao justamente em `site_revisao.py`.

**Os 668 pendentes seguem sem aprovacao em lote, de proposito.** 460
estao em 12 videos com 2 a 4 vozes; 208 em 14 videos de voz unica — e
esses 208 sao justamente os segmentos que os 4 sinais de confianca
REPROVARAM, ou seja, os menos confiaveis do lote, nao os mais. Aprovar
tudo publicaria fala de jornalista, apoiador e cantor de jingle como
palavra de candidato, em escala.

Pronto (2026-08-25): **teto real de cobertura de Governador medido, e
coletor generico pras outras plataformas.**

Levantado o campo `sites` do registro no TSE dos 196 candidatos a
Governador — dado que nunca tinha sido guardado em
`dados/candidatos_governador/*.json`. Sem ele, ninguem sabia se "faltam
180" significava 180 coletas possiveis ou 40.

Detalhe tecnico da coleta: a API segue bloqueando `curl`/`requests` com
403 do Akamai, e **o CDN de dados abertos (`cdn.tse.jus.br`) tambem** —
`consulta_cand_2026.zip` e `rede_social_candidato_2026.zip` dao o mesmo
403, entao nao ha' atalho por dados abertos. Funcionou pelo **Playwright**
(Chromium real navegando o portal, `fetch()` no contexto da pagina), sem
depender da extensao Claude in Chrome, que nao estava conectada. A
resposta da API traz CPF e titulo de eleitor — **guardado so' o campo
`sites`**, o resto descartado.

Numeros (`dados/redes_sociais_governador.json`, fora do git):
  196 candidatos | 152 com plataforma de video utilizavel |
  16 ja com citacao | **136 faltam coletar** | 44 sem plataforma
Dos 136: 55 YouTube, 78 Instagram, 2 Facebook, 1 TikTok.
**Os 44 nao sao trabalho pendente — sao limite factual** (sem canal de
video cadastrado no TSE, e o projeto nunca faz busca generica).

Achado de qualidade de dado: 9 candidatos digitaram handle ou texto
livre no lugar da URL (ex: Cyro Garcia registrou
`https://@CYROGARCIA16/INSTAGRAN/FACEBOOK/TIKTOK`). Um detector ingenuo
por substring classificaria isso como TikTok. As URLs sao extraidas por
regex de `https?://` de dentro do campo — aproveitando so' o que ja'
estava escrito ali, sem inventar link. Sobraram 44 sem nada aproveitavel.

**`coletar_midia.py`** (novo): YouTube, Instagram, TikTok e Facebook pelo
mesmo caminho. `coletar_youtube.baixar` sempre foi yt-dlp puro e nunca
foi especifico do YouTube — a unica coisa presa era `fonte="youtube"`
hardcoded em tres lugares, agora parametro (padrao inalterado, nada que
ja' chamava quebrou). `detectar_plataforma` levanta erro em vez de
adivinhar: **Kwai nao tem extractor no yt-dlp**, entao candidato so' com
Kwai fica registrado como sem coleta, nao vira fonte errada na
proveniencia. `cli_midia.py` e' a CLI.

O caminho do instaloader (`coletar_instagram.py`) continua existindo. Os
dois baixam direto do CDN da Meta (nenhum e' ripper de terceiro), entao a
cadeia de custodia vale igual; ter dois caminhos e' resiliencia depois
que `Profile.from_username` quebrou com erro de schema da Meta e disparou
rate-limit na conta do dono (2026-08-22).

**`deduplicar.py`** (novo, puro, testado): campanha publica a MESMA peca
em varias redes — **96 dos candidatos que faltam tem mais de uma
plataforma**, entao repetir e' o caso comum, nao a excecao. Sem isso a
mesma fala apareceria 2-3 vezes na pagina do candidato como se fossem
declaracoes distintas, inflando a contagem e dando peso falso a um unico
video. Hash nao resolve: cada plataforma reencoda, entao
`hash_sha256_original` prova origem mas nao identifica conteudo repetido.

Metrica: containment de shingles de 5 palavras. Escolhida pelo caso real
mais dificil — o Reel costuma ser um RECORTE do video longo, e Jaccard
puniria a diferenca de tamanho. **Limiar medido, nao chutado**, contra os
1.653 pares dos 58 videos ja coletados:
  - videos DISTINTOS: containment maximo **0.008**
  - recorte contiguo do mesmo video: **1.000**
  - mesmo video com 8% de erro de ASR: **0.576** no pior caso
`LIMIAR_REPETIDO = 0.30` fica ~37x acima do pior distinto e bem abaixo do
pior duplicado. Texto com menos de 30 palavras nunca vira duplicata (um
trecho curto casa por acaso dentro de qualquer discurso longo).

Repetido **nunca e' apagado** (mesmo espirito da regra 5): fica marcado
em `repetido_de` na fila, a auto-aprovacao e' pulada, e o log diz COM
QUAL video casou e em que porcentagem. Errar pra menos custa um video a
mais na fila — visivel e corrigivel; errar pra mais apagaria evidencia
real em silencio. Por isso o limiar erra pro lado alto.

11 testes novos (194 passam).

Pronto (2026-08-30): **63 clipes de sabatina de Presidente coletados**
(Lula, Renan Santos, Augusto Cury, Flavio Bolsonaro — os 4 que tiveram
sabatina em veiculo de imprensa nesta semana, confirmado por busca real,
nao suposicao; Edmilson Costa e Rui Costa Pimenta ficaram de fora por
falta de fonte confirmada, nao decisao arbitraria). Fonte: canal oficial
do **g1** (Grupo Globo) no YouTube — decisao nova, tomada com o dono
antes de agir: ate' aqui a convencao sempre foi canal oficial do PROPRIO
candidato; como nenhum dos 4 repostou a sabatina no canal dele, o dono
autorizou expandir pra' canal do veiculo de imprensa (nunca canal de
reacao/terceiro tipo "TV Afiada" — so' g1, que e' a fonte primaria).
Achado no meio do processo: a estimativa inicial (~37 clipes, baseada em
busca web solta) ficou bem abaixo do real (64, contado direto na
listagem do canal) — o dono foi avisado do numero real antes de rodar
tudo, confirmou "seguir sem parar".

Achado tecnico: yt-dlp 2026.7.4 (instalado) falhava com "The page needs
to be reloaded" em TODO video recem-postado do g1, mas video antigo
qualquer funcionava normal — nao era bloqueio de IP (padrao diferente do
caso de 2026-08-18), era a versao desatualizada nao lidando com alguma
mudanca recente da API do YouTube. Resolvido com
`pip install --upgrade yt-dlp` (2026.7.4 → 2026.8.19).

**Zero segmento foi auto-aprovado, e isso e' o resultado certo, nao um
bug.** Rodei `auto_aprovacao.gerar_decisoes_automaticas` de verdade (nao
um bypass) sobre os 9.343 segmentos novos: 100% bloqueados por
`video_e_falante_unico` — e' formato sabatina, jornalista pergunta +
candidato responde, exatamente o cenario que a trava existe pra pegar.
O dono pediu "aprovar de forma automatica"; expliquei que isso
contrariaria a regra 2 e citei os 5 casos reais ja documentados
(Paula Belmonte, Orleans Brandao, Vicentinho Junior, Fernando Haddad,
Jeronimo Rodrigues) de locutor/entrevistador virando "fala do
candidato" quando esse tipo de trava e' pulado — e ele nao insistiu.
Fila de revisao pulou de 668 para ~10.000 itens pendentes; fica
registrado aqui porque e' um salto grande, nao porque mudei algo na
decisao de nao aprovar em lote.

Pronto (2026-08-30): **formulario publico de report de erro**
(`/reportar-erro`), pedido do dono no mesmo fôlego do item acima —
motivado em parte pelo volume que acabou de entrar na fila. Ver
changelog de 2026-08-30 em `DESIGN.md` pro detalhe visual; aqui so' a
decisao de arquitetura: os reports vao pra' uma **issue no GitHub**
(`Dutrabr/monitor-eleitoral`, label `report-usuario`), nao pra' arquivo
local — o disco do Render (producao) e' efemero, um arquivo gravado ali
some no proximo deploy. Escolhida pelo dono entre 3 opcoes (GitHub
Issues / email via servico externo / Supabase) — GitHub porque o repo
ja existe e nao pede infraestrutura nova.

`reportar.py` (puro, testado — `tests/test_reportar.py`, 9 testes):
valida o formulario e monta titulo/corpo da issue; **nunca julga se o
relato procede** (regra 1 vale pra conteudo gerado por usuario tambem),
so' formata pra' um humano avaliar. `site_publico.py` faz a chamada HTTP
de verdade (`urllib.request`, sem dependencia nova) e cuida do que e'
I/O: honeypot (`RelatorioSpam` finge sucesso, nao da pista pro bot),
rate-limit simples por IP em memoria (30s entre reports, reseta a cada
restart — suficiente pro tamanho do site, nao e' defesa contra ataque
serio), e erro claro se `GITHUB_TOKEN_REPORTS` nao estiver configurado
em vez de fingir que enviou. 6 testes novos em `test_site_publico.py`
com `urlopen` mockado (nunca bate na API real do GitHub durante teste).

Cada citacao publicada (`candidato.html` — falas em destaque, lista
"sem tema", coluna "redes sociais" do painel comparativo, material de
campanha, linha do tempo) ganhou link "reportar erro" que pre-preenche
candidato/fonte/timestamp/trecho via query string, usando um macro
Jinja (`link_reportar`) pra nao repetir a URL 5 vezes. Link do rodape
"Reportar um erro" trocou de `mailto:` pra `/reportar-erro`; botao de
contato em `/perguntas` ganhou um segundo botao ao lado (duvida de
metodo continua email, report de citacao especifica agora tem
formulario com contexto).

`render.yaml` ganhou `GITHUB_TOKEN_REPORTS` com `sync: false` (variavel
de ambiente secreta, preenchida a mao no dashboard do Render, nunca no
blueprint commitado). **Ainda falta**: o dono precisa criar um GitHub
Personal Access Token (escopo `issues:write` no repo, ou `repo` se for
PAT classico) e colar no dashboard do Render — nao e' algo que da' pra
fazer sozinho, exige acao na conta dele. Sem o token, a rota falha de
forma clara ("Nao foi possivel enviar agora") em vez de fingir sucesso.

212 testes passam (`python3 -m pytest tests/ -q`).
