<!--
ARQUIVO: trilha de leitura para frontend.

TIPO DE DOCUMENTO:
- trilha de onboarding por perfil

AUTORIDADE:
- media para onboarding frontend

DOCUMENTO PAI:
- [../governance-reading-index.md](../governance-reading-index.md)
-->

# Trilha de leitura para Frontend

## Objetivo

Esta trilha existe para quem vai tocar:

1. templates
2. contratos de tela
3. CSS
4. layout
5. assets
6. experiencia percebida

## Ordem recomendada

1. [../../../README.md](../../../README.md)
2. [../general-architecture-guide.md](../general-architecture-guide.md)
3. [../frontend-architecture-guide.md](../frontend-architecture-guide.md)
4. [../css-architecture-guide.md](../css-architecture-guide.md)
5. [../performance-architecture-guide.md](../performance-architecture-guide.md)
6. [../../plans/front-end-restructuring-guide.md](../../plans/front-end-restructuring-guide.md)
7. [../../reference/front-end-city-map.md](../../reference/front-end-city-map.md)
8. [../../reference/front-end-octobox-organization-standard.md](../../reference/front-end-octobox-organization-standard.md)
9. [../../experience/css-guide.md](../../experience/css-guide.md)

## Depois disso, entre no runtime

Leia primeiro:

1. `shared_support/page_payloads.py`
2. `catalog/presentation/*`
3. `templates/*` da area que voce vai tocar
4. `static/css/design-system/*`
5. `static/css/catalog/*` apenas quando a tela ainda morar nesse trilho historico

## O que esse perfil deve preservar

1. backend entrega verdade, frontend organiza experiencia
2. CSS entra na camada certa
3. a fachada deve parecer produto unico, nao mosaico
4. performance faz parte da UX

## Erros mais caros

1. corrigir local mexendo no global sem necessidade
2. criar CSS novo fora da superficie certa
3. deixar JS deduzir regra por classe visual
4. inflar payload de backend com cosmetica que o front pode compor
