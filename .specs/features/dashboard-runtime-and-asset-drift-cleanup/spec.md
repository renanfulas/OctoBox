# Spec

## Objetivo

Garantir que o dashboard tenha uma unica implementacao viva para seus cards de abertura e uma trilha de assets previsivel.

## Requisitos funcionais

1. o dashboard deve usar uma unica familia oficial para a abertura visivel
2. a familia nao utilizada nao deve continuar recebendo manutencao de runtime
3. o componente de lista generico nao deve carregar regra de negocio especifica de dashboard
4. o ambiente de desenvolvimento nao deve depender de sync manual e opaco entre `static/` e `staticfiles/`
5. os testes devem apontar para a estrutura viva da tela

## Requisitos nao funcionais

1. zero regressao visual na abertura atual do dashboard
2. zero traceback em templates
3. menor area de override por escopo
4. menor custo cognitivo para manutencao futura

## Fora de escopo

1. redesenhar o dashboard inteiro
2. refatorar todos os componentes compartilhados do produto
3. eliminar todo `!important` do repositorio inteiro

## Definicao de pronto

1. existe uma fonte oficial de verdade para a abertura do dashboard
2. o legado morto de `priority_strip` deixa de confundir o runtime ativo
3. a variante do dashboard nao depende de condicionais perigosas no template generico
4. existe fluxo claro para runtime CSS sem drift oculto
5. os testes acompanham a tela real
