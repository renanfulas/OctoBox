# Corda Plan

## Meta

Fechar a raiz dos overrides invisiveis do dashboard sem remendo.

## Sequencia

1. mapear a trilha viva do dashboard e declarar a fonte unica de verdade
2. aposentar o legado morto de `priority_strip` da camada ativa
3. separar a variante do dashboard do componente generico `page_reading_list.html`
4. definir uma rotina confiavel para evitar drift entre `static/` e `staticfiles/`
5. alinhar testes e artefatos ao runtime real

## Guardrail

Nao fazer:

1. mais condicional de dashboard dentro do componente generico
2. mais sync manual ad-hoc como solucao permanente
3. mais correcoes em `dashboard_glance_card` sem confirmar que a tela viva usa essa familia
