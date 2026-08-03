# Taxonomia temática — RASCUNHO, precisa de aprovação

**Este documento não está em uso.** Nenhum código do projeto depende
dele. É um ponto de partida para você revisar, editar e aprovar — só
depois disso ele deveria virar código (um enum, uma lista de constantes)
e ser referenciado pelo pipeline.

## Por que isso é decisão sua, não minha

O CLAUDE.md do projeto já registra isso, mas vale repetir aqui: a
taxonomia decide **como o conteúdo é organizado** para a comparação
plano-de-governo vs. fala pública. Isso molda a leitura do produto final
mesmo sem nenhum veredito explícito — se "segurança pública" for uma
categoria e "direitos humanos" não for, ou se forem fundidas numa só,
isso já é uma escolha editorial com peso. A Resolução TSE 23.610/2019
(art. 9º-B) veda que sistemas de IA "recomendem, ranqueiem, sugiram ou
priorizem" — uma taxonomia em si não faz isso, mas quem a define está
tomando uma decisão jornalística que precisa ser sua, documentada e
publicada antes de qualquer análise (regra já registrada no CLAUDE.md).

## Critérios que usei para este rascunho

- Baseado em categorias recorrentes em coberturas de propostas de governo
  no Brasil (educação, saúde, segurança, economia aparecem quase
  universalmente).
- Ordem **alfabética de propósito** — não é ranking de importância. Se
  aprovar, sugiro manter alfabética no código também, para não insinuar
  prioridade.
- Tentei nem agregar demais (perde nuance) nem fragmentar demais (louça
  demais pra manter simetria entre candidatos — regra 3 do projeto).
- Cada categoria devia, na teoria, conseguir classificar tanto um trecho
  de plano de governo quanto uma frase solta de rede social — categorias
  burocráticas demais (ex: "gestão orçamentária") tendem a falhar nisso.

## Proposta (13 categorias)

1. **Agropecuária e desenvolvimento rural**
2. **Assistência social e combate à pobreza**
3. **Ciência, tecnologia e inovação**
4. **Cultura**
5. **Direitos humanos e igualdade** (raça, gênero, orientação sexual, pessoas com deficiência)
6. **Economia e emprego**
7. **Educação**
8. **Infraestrutura e mobilidade**
9. **Meio ambiente e clima**
10. **Política externa e relações internacionais**
11. **Reforma política e institucional**
12. **Saúde**
13. **Segurança pública**

## Perguntas em aberto para você decidir

- **Granularidade de economia**: "Economia e emprego" está genérico de
  propósito. Vale separar tributação/reforma tributária como categoria
  própria? Foi um dos temas mais debatidos nas eleições recentes.
- **Habitação**: mereceria categoria própria ou fica dentro de
  "Infraestrutura"? Depende de quanto os candidatos costumam falar disso
  como pauta própria.
- **Item "outros/sem classificação"**: toda taxonomia fechada tem sobra.
  Um item confirmado mas que não se encaixa em nenhuma categoria vai pra
  onde? Sugiro um rótulo explícito tipo "sem tema definido" em vez de
  forçar encaixe — mas isso é call sua.
- **Multi-tema**: um trecho pode caber em mais de uma categoria (ex:
  "creche para trabalhadoras rurais" toca educação + trabalho +
  agropecuária). Permitir mais de um rótulo por citação, ou forçar
  escolha de um só?
- **Fonte de validação**: pretende validar essa lista contra alguma
  taxonomia já publicada (TSE, IBGE, alguma ONG de monitoramento
  eleitoral) para dar mais peso institucional à escolha, ou é
  suficiente ser uma decisão própria do projeto, documentada?

## Próximo passo

Edite a lista acima direto neste arquivo (ou me diga o que mudar), decida
as perguntas em aberto, e quando estiver fechada eu transformo isso em
código (provavelmente um `Enum` em `src/transcricao/` similar ao
`Status` de `modelos.py`) com testes garantindo que toda citação
publicada tenha exatamente a cardinalidade de tema que você decidir
(um só, ou permitir múltiplos).
