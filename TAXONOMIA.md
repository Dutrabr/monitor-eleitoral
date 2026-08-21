# Taxonomia temática — APROVADA (2026-08-03)

Aprovada pelo dono do projeto. As 13 categorias abaixo estão em uso em
`modelos.Tema`. As perguntas em aberto que não foram respondidas
explicitamente na aprovação levaram a uma decisão padrão minha — marcadas
como **[padrão meu]** abaixo. Se não era essa a intenção, é so' me avisar
e eu ajusto (mudar um Enum e seus usos é barato).

## Critérios usados

- Baseado em categorias recorrentes em coberturas de propostas de governo
  no Brasil (educação, saúde, segurança, economia aparecem quase
  universalmente).
- Ordem **alfabética de propósito** — não é ranking de importância. Mantida
  alfabética também no código, para não insinuar prioridade.
- Nem agregada demais (perde nuance) nem fragmentada demais (regra 3 do
  projeto: simetria entre candidatos).

## Categorias (13)

1. Agropecuária e desenvolvimento rural
2. Assistência social e combate à pobreza
3. Ciência, tecnologia e inovação
4. Cultura
5. Direitos humanos e igualdade (raça, gênero, orientação sexual, pessoas com deficiência)
6. Economia e emprego
7. Educação
8. Infraestrutura e mobilidade
9. Meio ambiente e clima
10. Política externa e relações internacionais
11. Reforma política e institucional
12. Saúde
13. Segurança pública

## Decisões sobre as perguntas em aberto

- **Granularidade de economia** — **[padrão meu]**: nao separei
  tributação em categoria própria. "Economia e emprego" cobre por ora;
  fácil de desmembrar depois se a cobertura real mostrar que precisa.
- **Habitação** — **[padrão meu]**: fica dentro de "Infraestrutura e
  mobilidade", sem categoria própria.
- **Item "sem tema definido"** — **[padrão meu, mas alinhado ao espírito
  do projeto]**: existe um valor explícito `SEM_TEMA_DEFINIDO` no enum.
  Nunca força encaixe artificial — mesmo principio de "na dúvida, não
  decida sozinho" que já rege `qualidade.py` (REVISAR em vez de OK
  forçado).
- **Multi-tema** — **[padrão meu]**: uma citação pode ter mais de um
  tema. Implementado como lista (`temas: list[str]`), não campo único.
  Combina com o resto do projeto: `Segmento.motivos` já é lista pelo
  mesmo motivo (nunca forçar uma unica explicação/rotulo quando mais de
  um se aplica).
- **Fonte de validação externa** — não validado contra taxonomia de
  terceiros (TSE/IBGE/ONGs). Decisão própria do projeto, documentada
  aqui.

## Taxonomia de Governador — divergente da de Presidente (2026-08-20)

Ao curar o plano de governo do Fernando Haddad (SP), "Política externa e
relações internacionais" não apareceu em nenhuma página — esperado,
política externa não é competência constitucional de estado. O dono do
projeto decidiu, olhando esse caso real, trocar esse tema só na
taxonomia de Governador (Presidente mantém os 13 originais, intactos):

- **Sai**: Política externa e relações internacionais.
- **Entram**: Relações federativas e municípios (coordenação
  estado-prefeituras, pactos, apoio técnico/financeiro — recorrente nos
  planos de governador, sem tema próprio antes) e Gestão fiscal e dívida
  pública (responsabilidade fiscal, orçamento, endividamento do estado).

Resultado: 14 temas pra Governador (13 originais − 1 + 2), vive em
`candidatos.ROTULOS_TEMA_GOVERNADOR` / `candidatos.TEMAS_GOVERNADOR_DISPONIVEIS`,
separado do `Tema` enum de `modelos.py` (que continua servindo Presidente
e a marcação de tema em citações de vídeo — ver nota abaixo).

**Gap conhecido, não fechado nesta sessão**: `modelos.Tema` (usado pelo
site de revisão humana, `site_revisao.py`, pra marcar tema numa citação
de vídeo) não tem os 2 temas novos nem removeu política externa —
continua sendo so' a taxonomia de Presidente. Isso não trava nada hoje
porque nenhuma citação de vídeo de Governador foi coletada ainda (regra
2 exige revisão humana, e essa coleta é um projeto à parte, não
começado). Quando começar a revisão de vídeo de Governador,
`site_revisao.py` vai precisar de um seletor de tema consciente do
cargo do candidato sendo revisado — do contrário uma citação sobre
"relação com prefeituras", por exemplo, não teria como ser marcada
com o tema certo.

## Onde isso vive no código

- `modelos.Tema`: o enum com as 13 categorias + `SEM_TEMA_DEFINIDO`.
- `revisao.registrar_decisao(...)`: aceita `temas: list[str] | None` ao
  confirmar um segmento — a marcação de tema acontece no mesmo passo da
  revisão humana, por quem já está ouvindo o trecho.
- `revisao.montar_publicacao(...)`: cada citação publicada carrega
  `"temas": [...]` (lista vazia se o revisor não marcou nenhum).
- Interface (`site_revisao.py` / `_segmento.html`): checkboxes de tema no
  formulário de confirmação.
