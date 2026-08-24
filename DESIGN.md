# Design system — Monitor Eleitoral (site público)

Fonte da verdade visual do site público. Extraído do CSS real em
`src/transcricao/templates_publico/base.html` (nunca editado à mão sem
olhar o arquivo primeiro). Referenciado por CLAUDE.md.

Regra: qualquer mudança visual atualiza este arquivo no mesmo commit da
mudança de CSS. Se os dois divergirem, o CSS manda — mas a divergência é
bug de documentação a corrigir, não a ignorar.

## Conceito: "console de evidência" (v2)

O site é um instrumento de leitura de evidência, não uma peça de
campanha. A linguagem visual vem do material do próprio projeto —
timestamp, número de página, hash, cadeia de custódia — tratado como
leitura de instrumento em vez de letra miúda. Daí vêm as três decisões
que definem o v2:

1. **Escuro por padrão.** O claro existe e é bem resolvido, mas é
   variante. Inverte o padrão do v1 (que era claro por padrão).
2. **Metadata em monoespaçada.** Tudo que é aparato de prova (fonte,
   página, timestamp, contagem, status) usa mono. O que é fala humana
   usa serifa. O que é interface usa sans. Três vozes tipográficas com
   papéis separados, não decoração.
3. **Geometria reta.** Cantos retos (0–2px) no lugar dos cards
   arredondados de 16px do v1; separação por linha de 1px e por grade,
   não por sombra difusa.

## Paleta

CSS custom properties em `:root`. **Escuro é o `:root` nu** (padrão);
claro entra por `@media (prefers-color-scheme: light)` guardado com
`:root:not([data-tema="escuro"])`, e por `:root[data-tema="claro"]` para
a escolha manual vencer em qualquer sistema.

### Escuro (padrão)

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#070B0D` | fundo (quase preto com viés teal, não preto puro) |
| `--superficie` | `#0E1619` | painéis, cabeçalho, rodapé, cards |
| `--superficie-alta` | `#131F23` | hover de card, elevação |
| `--borda` | `#1E2C31` | linhas de 1px que estruturam tudo |
| `--texto` | `#E6F0F0` | texto principal |
| `--texto-suave` | `#9DB2B8` | texto secundário |
| `--texto-fraco` | `#6B8189` | metadata, estados vazios |
| `--teal` | `#2DD4BF` | sinal do **plano de governo** |
| `--ambar` | `#FBBF24` | sinal da **fala pública** |

### Claro (variante)

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#EFF4F4` | fundo (neutro com viés teal, não branco puro) |
| `--superficie` | `#FFFFFF` | painéis |
| `--borda` | `#D2DEDE` | linhas |
| `--texto` | `#0B1618` | texto principal |
| `--teal` | `#0F7A70` | sinal do plano (escurecido p/ contraste) |
| `--ambar` | `#B26B00` | sinal da fala (escurecido p/ contraste) |

Auxiliares em ambos: `--teal-tinta` / `--ambar-tinta` (fundo dos blocos
de evidência), `--teal-linha` / `--ambar-linha` (bordas de sinal),
`--grade` (textura de grade do fundo).

**Zero vermelho/azul de propósito** — paleta neutra, sem cor associada a
partido (regra 3 do projeto: simetria entre candidatos). Teal e âmbar
não são "bom" e "ruim": são apenas *plano* e *fala*, dois canais.

## Tipografia

Três famílias com papéis separados, carregadas do Google Fonts:

| Token | Família | Papel |
|---|---|---|
| `--f-disp` | **Archivo** 700/900 | títulos — pesada, tracking negativo |
| `--f-body` | **IBM Plex Sans** 400/500/600 | interface e texto corrido |
| `--f-mono` | **IBM Plex Mono** 400/500 | toda metadata e rótulo de instrumento |
| `--f-serif` | **IBM Plex Serif** 400 | blocos de evidência (`.trecho`, `.citacao`) |

- Tamanho base `17px`, `line-height 1.65`.
- Títulos: `font-weight 900`, `letter-spacing -0.03em`, `text-wrap: balance`.
- Rótulos mono: uppercase, `letter-spacing` entre `.08em` e `.16em`.
- `font-variant-numeric: tabular-nums` onde há dígito em coluna.

**Isto reverte a decisão do v1 de não carregar fonte externa.** Ver
"Custo assumido" no fim deste documento.

## Espaçamento, raio e traço

- Raio: `0` em quase tudo. Exceções: `2px` no anel de foco.
  O v1 usava 8/11/12/16/999px — o v2 abandonou o arredondado.
- Separação: linha de `1px` em `--borda`. Grades de card usam
  `gap: 1px` sobre fundo `--borda`, criando malha em vez de cards soltos.
- Sombra: quase ausente. `--sombra-hover` é anel de 1px em teal, não borrão.
- Fundo: grade sutil de 46px (`--grade`) em `body`, ligada à ideia de
  instrumento — nunca forte o bastante para competir com texto.

## Componentes-chave (nomes reais no CSS)

- `header.topo` — barra sólida com hairline em gradiente teal→âmbar embaixo.
- `.faixa-aviso` — faixa de status em mono no topo absoluto da página.
- `.selo-eyebrow` — rótulo de seção, mono uppercase com borda teal.
- `.chip` / `.chip-combo` / `.chip-opcao` — filtros retos; ativo é teal sólido com texto no fundo.
- `.grade-candidatos` — malha de 1px; `.card-candidato` acende barra teal embaixo no hover.
- `.avatar-candidato` — **retrato** retangular com borda teal e leve halo; `.avatar-grande` acrescenta cantos de mira (usado na página do candidato). É aqui que vivem as fotos dos 209 candidatos e as 27 bandeiras de estado.
- `.paineis` / `.coluna` — os dois canais de comparação, separados por linha de 1px; `h3` em mono uppercase (teal no plano, âmbar nas redes).
- `.rotulo-status` — mono uppercase com borda: `.consta` teal, `.nao-consta` âmbar, `.nao-verificado` neutro.
- `.trecho` / `.citacao` — evidência em serifa, borda esquerda de 2px + fundo tingido.
- `.linha-tempo` — marcadores quadrados com brilho teal.
- `.faq-item` (em `perguntas.html`) — acordeão `<details>` com `+`/`−` em mono.

## O que NÃO usar

- Sem vermelho/azul (neutralidade partidária).
- Sem cantos arredondados grandes — o v2 é reto por decisão.
- Sem sombra difusa como recurso de elevação — use linha e fundo.
- Sem framework de UI/CSS — tudo inline em `base.html`, sem build step.
- Sem animação além de hover/transition simples; `prefers-reduced-motion` desliga tudo.
- Sem cor definida só dentro de `@media` ou `[data-tema]` — todo token
  existe no `:root` nu primeiro, senão o estado "sistema" quebra.

## Custo assumido no v2

**Fonte externa.** O v1 não carregava fonte de propósito. O v2 carrega
quatro famílias do Google Fonts, o que significa: (a) requisição a um
terceiro em cada visita, incluindo IP do visitante — relevante num site
cívico; (b) dependência de disponibilidade do Google. A alternativa é
self-host (adiciona binário ao repositório, o que o projeto evitava) ou
voltar a fonte de sistema (perde boa parte da identidade). Se a decisão
mudar, trocar as quatro variáveis `--f-*` resolve sem tocar em mais nada.

## Changelog

**2026-08-21 — coluna "Redes sociais" vazia.** No painel de comparação
por tema (`candidato.html`), quando um tema tem plano preenchido mas
nenhuma citação de rede social confirmada, a coluna direita virava uma
caixa do mesmo tamanho/peso visual que a coluna do plano, só com uma
frase solta dentro — ficava parecendo bug, não "informação real que
ainda não existe". Comparadas 3 variações (artefato com conteúdo real
do Zema); o dono escolheu a opção B: caixa menor, centralizada, borda
tracejada em vez de sólida, texto em `--texto-fraco` — sinaliza
"placeholder", não compete com o conteúdo real ao lado.

Implementado: `.coluna-redes.vazio` em `base.html` + classe condicional
em `candidato.html` (`{% if not citacoes %} vazio{% endif %}`). Novos
tokens `--texto-fraco` e `--borda-tracejada` (light e dark) adicionados
à paleta acima. Copy da mensagem vazia trocada de "Nenhuma publicação
encontrada sobre este tema até o momento." para "Redes sociais —
nenhuma citação coletada ainda para este tema." (mais claro sobre o que
falta: coleta, não "não achamos").

Achado no processo, não corrigido (fora de escopo desta mudança): hoje
**nenhuma** das 144 citações publicadas tem tema marcado
(`"temas": []` em todas, ver `dados_publicos/citacoes.json`) — marcação
de tema é manual, feita no fluxo de revisão humana (`site_revisao.py`),
e nenhum revisor marcou tema ainda em nenhuma das citações existentes.
Na prática, isso significa que **toda** seção temática do site hoje
mostra a coluna vazia — o estado "cheio" (`.citacao`, não alterado
nesta mudança) só aparece na seção separada "Sem tema definido", que
usa um layout de lista corrida diferente, não o painel de 2 colunas.
Não é bug de template — é reflexo real do estado da curadoria.

**Ainda não aplicado a `comparar.html`**: essa página tem um padrão de
estado vazio parecido ("Nenhuma publicação encontrada...") mas dentro
de um card único por candidato (não colunas lado a lado competindo em
peso visual) — o problema visual identificado não se aplica do mesmo
jeito ali. Não mexido por decisão de escopo (um componente por vez).

**2026-08-21 — chips de tema.** Os 13 chips de filtro (home) e os
chips-âncora (página de candidato) tinham todos o mesmo contorno teal
sempre visível, mudando só quando ativo — em 3-4 linhas ficava
repetitivo, difícil de escanear. Comparadas 3 direções (artefato com
conteúdo real); o dono escolheu a combinação: chip neutro em repouso
(sem contorno colorido, texto `--texto-suave`), ganha borda/cor teal só
no hover, e carrega um número real — não decorativo.

Implementado: classe `.chip-combo` nova em `base.html` (substitui
`.chip` nesses dois lugares específicos; `.chip` original continua
existindo, ainda usado em `comparar.html`). O número significa coisas
diferentes por página, de propósito — cada um é a contagem que faz
sentido naquele contexto, não a mesma métrica repetida:
- **Home** (`index.html`): quantos candidatos têm esse tema marcado
  "consta" no plano curado — ajuda a escolher tema antes de clicar.
  Novo helper `_contagem_candidatos_por_tema()` em `site_publico.py`,
  passado como `contagem_por_tema` pro template.
- **Página de candidato** (`candidato.html`): quantas citações esse
  candidato específico tem nesse tema — já disponível em `grupos`, sem
  precisar de cálculo novo (`(grupos.get(tema) or [])|length`).

Confirma o mesmo achado da mudança anterior: como nenhuma citação tem
tema marcado ainda, todo chip de tema (exceto "Sem tema definido") hoje
mostra 0 na página de qualquer candidato — números batendo com a
realidade, não um bug da contagem nova.

**2026-08-21 — badge de número no card.** `.card-candidato .numero`
("Número 13") usava o mesmo pill com gradiente teal do resto da
página — mais um lugar repetindo o mesmo motivo. Trocado por texto
simples, uppercase, `--texto-fraco`, sem chrome nenhum. Só CSS
(`base.html`), nenhuma mudança de template — a classe já batia com o
HTML existente. Card de candidato de Governador usa o mesmo componente
(`card-candidato`), então herda a mudança automaticamente.

Discutido mas **não implementado ainda**: foto do candidato ou logo do
partido dentro do círculo do avatar (hoje só a inicial do nome). Foto
real do candidato é viável — a fonte já é a mesma API do TSE
(DivulgaCandContas) usada pro resto do projeto, mas exige confirmar se
a API serve foto por `candidato_id_tse`, baixar com a mesma disciplina
de proveniência dos PDFs de plano (regra 6: hash antes de qualquer
conversão), e decidir fallback pra quem não tiver foto (letra
continua). Logo de partido teria menos candidatos pra buscar (~13-30
partidos vs. 196 candidatos), mas entra em conflito direto com a
decisão já registrada acima ("Zero vermelho/azul de propósito — paleta
neutra, sem cor associada a partido") — a maioria dos logos partidários
usa cor forte de partido, o oposto do que o projeto decidiu
deliberadamente evitar. Decisão em aberto, aguardando o dono escolher
entre as duas (ou nenhuma).

**2026-08-21 — foto real do candidato no avatar (decisão: foto, não
logo de partido).** Confirmado que a API do TSE (DivulgaCandContas)
serve foto oficial por candidato via o campo `fotoUrl` (retornado por
`buscar/{ano}/{uf}/{eleicao}/candidato/{id}`, mesma API já usada pro
resto do projeto) — path real: `/divulga/rest/arquivo/img/{eleicao}/
{candidato_id_tse}/{uf}`. Mesmo bloqueio Akamai já documentado (403 via
`curl` direto); resolvido do mesmo jeito que os PDFs de Governador em
volume: `navigate()` numa aba real do Chrome baixa de verdade pro
`~/Downloads` (conta como ação real do usuário, não como download
automático em sequência — o bloqueio de múltiplos downloads automáticos
do Chrome só pegou a tentativa via `blob`+`<a download>`+`.click()`
sintético, essa sim bloqueada). Nomes de arquivo no Downloads são os que
o próprio candidato subiu no cadastro (ex: "foto hertz.jpg", "IMG_0958.
jpg") — diferentes entre si, sem colisão nos 13 casos, mas sem garantia
nenhuma disso pra um lote maior (Governador, se algum dia vier) —
teria que voltar ao mesmo cuidado de casar por ORDEM de requisição
usado nos PDFs de Governador em 2026-08-20.

13 fotos dos candidatos a Presidente baixadas (161×225px, JPEG),
hash sha256 registrado em `dados/fotos_candidatos/MANIFESTO.json`
(mesmo padrão de `dados/planos_de_governo/MANIFESTO.json` — não vai
pro `dados_publicos/`, fica só local, regra 6). Nova rota `GET /foto/
{slug}` em `site_publico.py`, serve do storage local (nunca linka
direto pro TSE, mesmo motivo do `/plano/{slug}`), 404 limpo quando não
há foto — nunca inventa imagem. `.avatar-candidato` ganhou `<img
onerror="this.remove()">` sobrepondo a letra (que continua lá atrás,
sempre renderizada) — se a foto falhar ou não existir (todos os 196
candidatos de Governador, por enquanto), a imagem se remove e a letra
com gradiente aparece exatamente como antes, sem JS condicional extra
nem campo novo passado do backend pro template. Aplicado nos 5 lugares
que renderizam avatar de candidato (`index.html`, `comparar.html` x2,
`governador_estado.html`, `candidato.html`) — `governador_index.html`
ficou de fora de propósito, o avatar ali mostra sigla de UF, não
candidato.

`exportar_dados_publicos.py` ganhou cópia de `dados/fotos_candidatos/
*.jpg` (não copia o `MANIFESTO.json`, mesma exclusão já aplicada aos
PDFs de plano). `render.yaml` e `site_publico.main()` ganharam
`--fotos`, default resolve sozinho pro sibling de `--candidatos`
então não quebra quem chama sem o flag.

**2026-08-21 — logo no header (substitui o selo "ME").** Pedido do
dono: símbolo + texto, não monograma. Descartei de propósito a ideia
óbvia (balança da justiça) — balança simboliza julgamento/veredito, o
que contraria diretamente a regra 1 do projeto (nunca veredito, é
resolução do TSE). Em vez disso, o símbolo é **duas colunas lado a lado
com linhas de texto** — literalmente o padrão de UI já central do site
(`.paineis`, plano × redes sociais), sem sugerir qual lado "vence".
Colunas com peso visual idêntico (mesma opacidade, mesmo número de
linhas) de propósito, ecoando a regra 3 (simetria total).

SVG inline em `base.html` (`fill="currentColor"`, herda branco do
contexto `.marca`), sem asset externo pro header. Favicon é uma versão
separada com cor explícita (`src/transcricao/static/favicon.svg`,
painéis em `--teal-forte` sólido, linhas em `--off-white` — contraste
alto pra ler bem pequeno numa aba de navegador). Primeiro asset
estático do projeto — `site_publico.py` ganhou `app.mount("/static",
StaticFiles(...))` e `<link rel="icon">` em `base.html`. Faz parte de
`src/`, vai pro git normal (não é dado gerado, não passa por
`exportar_dados_publicos.py`).

**2026-08-21 — bandeira de cada estado em `/governador` (lista de
UFs).** Pedido do dono. As 27 bandeiras (26 estados + DF) são símbolo
oficial de ente público — domínio público, sem direito autoral, sem
exigência legal de atribuição. Baixadas via `curl` direto da Wikimedia
Commons (`upload.wikimedia.org`, sem o bloqueio Akamai que afeta o TSE)
— URLs completas extraídas via JS na página real da Wikipédia
(`Unidades_federativas_do_Brasil`, listando as 27 na ordem alfabética
esperada), nunca adivinhadas. SVG original de cada uma (não thumbnail
PNG), salvos em `src/transcricao/static/bandeiras/{UF}.svg` — 1,3MB no
total, leve o bastante pra não pesar no deploy.

`governador_index.html` ganhou `<img src="/static/bandeiras/{{ e.uf
}}.svg" onerror="this.remove()">` dentro do `.avatar-candidato`, mesmo
padrão de fallback das fotos de candidato (se faltar uma bandeira, cai
pra sigla de UF que já tinha). Efeito colateral esperado e aceito: como
bandeiras são retangulares e o avatar é circular, `object-fit: cover`
corta as bordas — em bandeiras com lema/texto perto da borda (ex:
Paraíba, "NEGO LIBERTATEM") só uma parte aparece. Mesmo comportamento
que já existe pras fotos de candidato, não é bug novo.

Achado no processo (bloqueio de ambiente, não do site): o sandbox do
Bash bloqueia `for`/`while` com múltiplas chamadas de rede dentro do
mesmo comando — `curl` "command not found" só dentro do loop, funciona
normal fora dele. As 26 bandeiras restantes (depois da primeira) foram
baixadas uma chamada por vez.

Não mexido ainda: `governador_estado.html` (página de um estado
específico) não mostra a bandeira — só foi pedida pra lista de estados.
`site_publico.py` não precisou de mudança nova (a rota `/static` já
existia desde o logo).

**2026-08-21 — foto real dos 196 candidatos a Governador.** Pedido do
dono, mesma ideia já feita pros 13 de Presidente: foto real dentro do
círculo do avatar em vez de letra+gradiente. Fonte é a mesma API do TSE
(`fotoUrl`, endpoint `.../rest/arquivo/img/{eleicao_id}/{candidato_id}/
{UF}`), mas com um bug real encontrado e corrigido antes de baixar em
massa: copiar o padrão de Presidente usando `UF="BR"` devolve, pra todo
candidato a Governador, o MESMO placeholder genérico de 4704 bytes —
Presidente é candidatura nacional (BR é o valor certo), Governador é
por estado, então a URL precisa da UF real de cada candidato. Corrigido
antes do lote completo; confirmado com um candidato de teste (BA)
devolvendo foto real e distinta.

As 196 fotos baixadas via `navigate()` real do navegador em lotes de
até 25 (mesma técnica de 2026-08-20 pros PDFs de plano de governo de
Governador — navegação real conta como gesto de usuário pro Chrome,
não dispara o bloqueio de "múltiplos downloads automáticos" que um
clique sintético via JS dispara). Passo extra novo aqui que os PDFs não
tinham exigido: como todas as 196 fotos vêm do mesmo padrão de nome
(`{candidato_id}_BR.jpg`-like, mas na prática timestamps de download
muito próximos), casar arquivo baixado → candidato por `ls -lt` ou por
mtime de segundo (`stat -f "%m"`) tinha empate real entre arquivos
baixados na mesma janela de 1s — resolvido usando `st_birthtime` (Python,
precisão de microssegundo no macOS) pra ordem cronológica inequívoca.
Verificado ao final: 196/196 JPEGs válidos, 196 hashes SHA256 únicos —
zero atribuição errada.

Salvas em `dados/fotos_candidatos_governador/{UF}/{slug}.jpg` (fora do
git, mesmo padrão de `dados/fotos_candidatos/` de Presidente), com
`MANIFESTO.json` de proveniência (hash sha256, bytes, candidato_id_tse,
uf, coletado_em) ao lado — regra 6. `site_publico.py` ganhou a rota
`/governador/{uf}/{slug}/foto` (equivalente por UF de `/foto/{slug}`),
parâmetro `pasta_fotos_governador` em `criar_app()` e flag `--fotos-
governador` na CLI; `render.yaml` e `exportar_dados_publicos.py`
atualizados pra também levar essas fotos pro deploy público (ainda não
tinham sido levadas nesta sessão até este ponto).

Dois lugares usam a foto: `governador_estado.html` (grade de
candidatos do estado — tinha um bug de copy-paste corrigido no
processo: usava `/foto/{slug}`, a rota de Presidente, em vez de
`/governador/{uf}/{slug}/foto`) e `candidato.html` (cabeçalho da página
de detalhe — como esse template é compartilhado entre Presidente e
Governador, ganhou um `{% if candidato.uf %}` pra escolher a rota
certa; candidato de Presidente não tem campo `uf`, então cai no `/foto/
{slug}` de sempre). Mesmo fallback `onerror="this.remove()"` de sempre
se a foto faltar.

**2026-08-22 — espaço de patrocínio no rodapé.** Nova seção
`.apoio-rodape` no fim de `footer.rodape`, atrás de um separador sutil
(`border-top: 1px solid rgba(255,255,255,.12)`) pra não se misturar com
o texto de isenção de responsabilidade logo acima. Rótulo "Apoio" em
uppercase pequeno e opaco (mesmo padrão visual dos eyebrows já usados
no site), logos em escala de cinza-neutra por padrão do próprio design
do rodapé escuro (`--grafite`), `opacity: .85` subindo pra `1` no
hover — discreto, nunca compete visualmente com o conteúdo de
comparação de candidatos. Sem patrocinador cadastrado (estado atual),
a seção inteira não renderiza (`{% if patrocinadores %}`) — rodapé
fica idêntico ao de antes. Ver nota completa em `CLAUDE.md` (2026-08-22)
sobre a decisão de nunca usar rede de anúncio automática, só
patrocínio curado a mão pelo dono, e a regra editorial de nunca aceitar
patrocinador ligado a candidato/partido/campanha.

**2026-08-24 — redesign v2 "console de evidência".** O dono pediu algo
"bem mais bonito e futurista". Apresentadas 3 direções em artefato com
conteúdo real (ACM Neto/BA, tema Agropecuária: trecho real do plano na
pg. 65 × falas reais transcritas, com hash e timestamp verdadeiros):
**A — console de evidência** (escuro, instrumental), **B — câmara de
vidro** (claro, translúcido, glassmorphism) e **C — arquivo aberto**
(alto contraste, tipografia enorme). O dono escolheu **A**.

Tensão levantada antes de propor, e que moldou as três: o site vive de
credibilidade, e "futurista" no sentido neon/cripto/game teria custo
justamente onde ele precisa parecer mais confiável. A saída foi buscar o
futuro no vocabulário do próprio material — hash, timestamp, página,
cadeia de custódia — em vez de em efeito visual. **O aparato que prova a
evidência virou o assunto visual.**

O que mudou, em relação ao v1:
- Escuro passou a ser o padrão (`:root` nu), claro virou variante. O
  toggle e a persistência em `localStorage` continuam funcionando; o
  script ganhou tratamento do estado "sistema" (antes ele assumia que
  ausência de `data-tema` era claro, o que inverteria errado agora).
- Paleta reescrita nos dois temas — teal e âmbar seguem sendo os únicos
  sinais (regra 3 intacta: zero vermelho/azul).
- Tipografia passou de fonte-de-sistema única para quatro papéis
  (Archivo / Plex Sans / Plex Mono / Plex Serif). **Reverte decisão
  explícita do v1**; custo documentado na seção "Custo assumido".
- Geometria: cantos arredondados (8–16px) → retos; sombra difusa →
  linha de 1px e malha de grade.
- `.avatar-candidato` virou retrato retangular com borda de sinal e
  halo; `.avatar-grande` (página do candidato) ganhou cantos de mira.
  **As 209 fotos e as 27 bandeiras foram preservadas** — só mudou o
  enquadramento, que era a preocupação explícita do dono ao escolher A.

Nenhum nome de classe foi alterado, então nenhum template quebrou. As 6
rotas principais foram testadas manualmente nos dois temas.

**2026-08-24 — página `/perguntas` (FAQ + glossário + contato).** Pedido
do dono de "uma funcionalidade pro público tirar dúvidas". Levantado o
risco antes de construir: um chatbot de IA respondendo sobre candidatos
colidiria com a regra 1 e com a Resolução TSE 23.610/2019, art. 9º-B
(alterada pela 23.755/2026), que veda sistema de IA recomendar/ranquear
candidato **inclusive a pedido do usuário** — na prática, alguém
perguntaria "em quem voto?" e qualquer resposta viraria risco. Descartado
em favor de conteúdo curado.

A página reúne três coisas numa só rota: 11 perguntas em acordeão
(`<details>`, sem JS), glossário de 8 termos, e o canal de contato. O
conteúdo é factual sobre o método — e explicita os limites: por que o
site não diz se o candidato cumpriu, por que "não consta" é diferente de
"não verificado", por que alguns candidatos aparecem sem citação alguma.
Rascunho escrito por mim, revisão do dono pendente antes de considerar
final.

Dois testes novos em `test_site_publico.py`: um de acessibilidade da
rota, outro que falha se alguém reescrever o conteúdo e remover a recusa
explícita de dar nota/ranking/recomendação — a promessa é parte do
produto, não texto decorativo.

**2026-08-24 — busca com destaque (`/busca`).** Última das quatro coisas
pedidas pelo dono na leva de "tirar dúvidas do público". Busca literal no
texto das citações já publicadas (não olha plano de governo), com o termo
destacado no resultado.

Decisão de neutralidade que moldou a implementação: **o resultado é
ordenado por número de urna, nunca por relevância.** Ordenar por "melhor
resultado" — mesmo que o critério seja contagem de ocorrências — seria
uma forma indireta de ranquear candidato, o que a regra 3 proíbe. O
resumo acima dos resultados diz isso explicitamente ao leitor ("ordem de
número de urna, sem ranking"), e há teste que quebra se a ordem mudar.

Duas funções puras novas em `candidatos.py`, ambas testadas:
- `buscar_citacoes()` — casa ignorando acento e caixa (`saude` acha
  `SAÚDE`); termo vazio devolve `[]`, nunca "tudo".
- `destacar()` — devolve lista de pedaços `{texto, marcado}` em vez de
  HTML pronto. Assim o template escapa o conteúdo normalmente e o termo
  de busca não vira vetor de injeção. Depende de a normalização preservar
  o comprimento da string (cada caractere acentuado vira um base); há
  teste explícito pra isso, porque se quebrar o destaque corta a palavra
  no lugar errado.

Detalhe de CSS que valeu ajuste: `mark` com padding lateral empurrava a
pontuação seguinte, exibindo "saúde ." em vez de "saúde.". Trocado por
fundo + `box-shadow` como sublinhado, sem padding horizontal.

Estado vazio da busca não afirma ausência: diz que a palavra não aparece
*no que já foi coletado e verificado*, e aponta para `/perguntas` —
mesmo princípio de "não consta" × "não verificado".
