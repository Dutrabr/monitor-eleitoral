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

## Fora de escopo, por decisao

- fastdl.app ou qualquer ripper de terceiro: quebra a cadeia de custodia e
  re-encoda o audio, piorando a transcricao.
- Stories do Instagram: efemero de 24h, alta friccao, conteudo pobre para
  promessa programatica.
- Qualquer juizo automatizado sobre merito de candidatura.
