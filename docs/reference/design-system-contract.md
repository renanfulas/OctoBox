<!--
ARQUIVO: contrato curto do design system.

POR QUE ELE EXISTE:
- deixa claro onde cada regra global deve morar para evitar CSS espalhado e dificil de manter.
- reduz ambiguidade quando quisermos ajustar resposta visual, espacamento ou componente compartilhado.

O QUE ESTE ARQUIVO FAZ:
1. define ownership rapido dos arquivos centrais do design system.
2. separa o que entra em spacing, responsiveness e components.
3. registra a heuristica para customizacao local sem travar evolucao futura.

PONTOS CRITICOS:
- este contrato precisa continuar curto e operacional.
- se um ajuste nao for realmente global, ele nao deve entrar aqui.
-->

# Contrato curto do design system

## Ordem de ownership

Quando uma mudanca for de front-end compartilhado, revise nesta ordem:

1. [static/css/design-system/tokens.css](static/css/design-system/tokens.css)
2. [static/css/design-system/spacing.css](static/css/design-system/spacing.css)
3. [static/css/design-system/responsiveness.css](static/css/design-system/responsiveness.css)
4. [static/css/design-system/components.css](static/css/design-system/components.css)
5. CSS da tela local

## O que entra em cada camada

Tokens:

1. variaveis globais de cor, espaco, raio, sombra e tipografia

Spacing:

1. utilitarios de stack e section gap
2. ritmo base entre blocos e grupos internos
3. regras neutras de respiro em cards e paines

Responsiveness:

1. regras de fluidez e anti-overflow
2. reorganizacao estrutural de grupos compartilhados
3. comportamento movel de baixa especificidade

Components:

1. aparencia e composicao de hero, card, tabela, pill, action e state
2. regras visuais reutilizaveis entre varias telas

CSS da tela:

1. identidade local
2. hierarquia propria da pagina
3. excecoes e ajustes que dependem do contexto daquela superficie

## Regra de decisao

Pergunte nesta ordem:

1. isso vale para varias telas ou so uma?
2. isso muda ritmo, resposta estrutural ou identidade visual?
3. isso precisa ser facil de sobrescrever depois?

Se a resposta for:

1. varias telas e ritmo: spacing
2. varias telas e estrutura responsiva: responsiveness
3. varias telas e aparencia compartilhada: components
4. uma tela especifica: CSS local da tela

## Regra de override

1. prefira classes locais da pagina para excecoes
2. evite aumentar especificidade nas camadas globais
3. use as camadas globais como baseline, nao como lugar de microajuste local