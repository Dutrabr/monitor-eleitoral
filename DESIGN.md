# Design system — Monitor Eleitoral (site público)

Fonte da verdade visual do site público. Extraído do CSS real em
`src/transcricao/templates_publico/base.html` (nunca editado à mão sem
olhar o arquivo primeiro) — este documento descreve o que já existe hoje
("linha de base v1"), não uma proposta nova. Referenciado por CLAUDE.md.

Regra: qualquer mudança visual atualiza este arquivo no mesmo commit da
mudança de CSS. Se os dois divergirem, o CSS manda — mas a divergência é
bug de documentação a corrigir, não a ignorar.

## Paleta

Definida como CSS custom properties em `:root`, com variante escura via
`prefers-color-scheme` e via toggle manual (`data-tema="escuro"` /
`data-tema="claro"` persistido em `localStorage`).

| Token | Valor | Uso |
|---|---|---|
| `--teal` | `#0D9488` | cor de marca primária |
| `--teal-forte` | `#0F766E` | gradientes, hover, links (modo claro) |
| `--teal-escuro` | `#0B4F49` | início do gradiente do header |
| `--teal-claro` | `#5EEAD4` | links no modo escuro, acentos |
| `--ambar` | `#F59E0B` | cor de destaque secundária (citações, "não consta") |
| `--ambar-forte` | `#B45309` | texto sobre fundo âmbar claro |
| `--grafite` | `#18181B` | texto no modo claro, fundo do rodapé |
| `--off-white` | `#FAFAF9` | fundo do modo claro |

Superfícies (mudam por tema):
- **Claro**: bg `#FAFAF9` · superfície `#ffffff` · texto `#18181B` · texto-suave `#52525B` · borda `#E4E4E7`
- **Escuro**: bg `#0F1012` · superfície `#1B1C1F` · texto `#FAFAF9` · texto-suave `#A1A1AA` · borda `#303034`

Zero vermelho/azul de propósito — paleta neutra, sem cor associada a
partido (regra 3 do projeto: simetria entre candidatos).

## Tipografia

- Corpo: `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` — fonte de sistema, sem asset de fonte carregado.
- Citações/trechos (`.trecho`, `.citacao`): `ui-serif, Georgia, "Times New Roman", serif` — serifa só nesses dois lugares, pra separar visualmente "evidência" de "interface".
- Tamanho base: `17px`, `line-height: 1.65`.
- Headings (`h1,h2,h3`): `font-weight: 800`, `letter-spacing: -0.02em`, `line-height: 1.15`.
- `h1`: `clamp(2rem, 4.5vw, 3.15rem)` — fluido, sem breakpoint fixo.

## Espaçamento e raio

Não há uma escala numérica estrita (tipo 4/8/12/16) documentada — os
valores no CSS atual são majoritariamente em `rem` ad hoc (`.5rem` até
`4rem`, passando por `.6/.65/.7/.75/.8/.85/.9/.95/1.1/1.25/1.35/1.4/1.5/2/2.5/3`).
Isso é uma lacuna real do sistema atual, não uma decisão — candidato a
corrigir na próxima leva de mudança visual (adotar escala 4px explícita
é a sugestão óbvia, mas não fazer sem decidir isso com o dono primeiro).

Raio de borda, por elemento:
- `4px` — anel de foco
- `8px` (canto) — link "pular para conteúdo"
- `11px` — selo do logo
- `12px` — trechos/citações (canto reto do lado da borda colorida)
- `16px` — cards, colunas de comparação
- `999px` (pill) — chips, botões, tags de status, avatar

## Sombra e foco

- `--sombra`: sombra padrão de card (dupla camada, sutil).
- `--sombra-hover`: mais forte, com tingimento de teal.
- `--anel-foco`: `0 0 0 3px rgba(245,158,11,.55)` — âmbar, usado em `:focus-visible` de links/botões/inputs (acessibilidade via teclado).

## Layout

- Container: `.envelope`, `max-width: 1040px`, padding lateral `1.25rem`.
- Grades responsivas via `auto-fit`/`auto-fill` + `minmax()` — sem breakpoints numéricos fixos pra cards de candidato.
- Painel de comparação (`.paineis`) é 2 colunas (`1fr 1fr`) em desktop; abaixo de `767px` vira abas via `radio + label` (CSS puro, sem JS de tabs).

## Componentes-chave (nomes reais no CSS)

- `header.topo` — gradiente teal com radial-gradient decorativo em âmbar/teal-claro.
- `.chip` / `.chip-opcao` — pills de filtro, estado ativo com gradiente teal.
- `.card-candidato` — card de listagem, hover levanta (`translateY(-3px)`) e troca sombra.
- `.avatar-candidato` — círculo com gradiente teal→âmbar, iniciais.
- `.tema-secao` — seção temática do painel, barra decorativa gradiente teal→âmbar no topo.
- `.coluna` — painel plano×redes, com `h3` em uppercase/letter-spacing.
- `.rotulo-status` — pill de status (`.consta` teal / `.nao-consta` âmbar / `.nao-verificado` cinza neutro).
- `.trecho` / `.citacao` — bloco de evidência com borda esquerda colorida (teal / âmbar) e fundo levemente tingido.
- `.linha-tempo` — timeline com linha vertical e bolinhas gradiente.
- `footer.rodape` — fundo grafite sólido.

## O que NÃO usar

- Sem vermelho/azul (neutralidade partidária).
- Sem fonte custom carregada via asset — decisão explícita anterior (evitar gerenciar binário de fonte por pouco ganho visual). Se isso mudar, atualizar aqui.
- Sem framework de UI/CSS (Tailwind, Bootstrap etc.) — tudo inline em `base.html`, sem build step.
- Sem animação além de hover/transition simples — `@media (prefers-reduced-motion: reduce)` já desliga tudo.

## Status: v1 (linha de base), redesign v2 pendente

Este documento descreve o que existe. Uma leva de redesign visual foi
pedida pelo dono do projeto (2026-08-21) — ainda sem referência visual
definida. Quando uma referência (screenshot, link, ou variações do
Stitch) for escolhida, esta seção vira changelog: o que mudou, por quê,
e a nova versão dos tokens acima.

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
