# Reception Session Surface Cleanup C.O.R.D.A.

**Status**: Draft
**Created On**: 2026-03-30

## Contexto

A recepcao ja teve a cobranca curta endurecida e o workspace principal ficou bem mais limpo.

Sobrou um pequeno bolsao visual em dois cards de sessao com `style=` inline.

## Objetivo

Remover a divida visual local desses dois cards e deixar a manutencao deles no CSS certo.

## Riscos

1. mexer demais em arquivos que podem nem estar vivos no runtime principal
2. espalhar regra em CSS errado
3. transformar uma limpeza curta em reforma desnecessaria

## Direcao

1. extracao simples para o owner correto
2. validar que os templates ficam limpos
3. registrar se a peca parece viva ou residual

## Acoes

1. mapear inline style e uso real
2. mover estilo para `class-grid.css`
3. validar integridade
4. classificar a peca como runtime vivo ou estoque residual
