<!--
ARQUIVO: trilha de leitura para backend.

TIPO DE DOCUMENTO:
- trilha de onboarding por perfil

AUTORIDADE:
- media para onboarding backend

DOCUMENTO PAI:
- [../governance-reading-index.md](../governance-reading-index.md)
-->

# Trilha de leitura para Backend

## Objetivo

Esta trilha existe para quem vai tocar:

1. regra de negocio
2. leitura e mutacao
3. facades
4. integracoes
5. contratos backend-frontend

## Ordem recomendada

1. [../../../README.md](../../../README.md)
2. [../general-architecture-guide.md](../general-architecture-guide.md)
3. [../backend-architecture-guide.md](../backend-architecture-guide.md)
4. [../../reference/reading-guide.md](../../reference/reading-guide.md)
5. [../../architecture/promoted-public-facades-map.md](../../architecture/promoted-public-facades-map.md)
6. [../../architecture/django-core-strategy.md](../../architecture/django-core-strategy.md)
7. [../../plans/catalog-page-payload-presenter-blueprint.md](../../plans/catalog-page-payload-presenter-blueprint.md)

## Depois disso, entre no runtime

Prioridade de leitura:

1. `config/urls.py`
2. app real do dominio
3. `queries`, `services`, `actions`, `workflows`, `use_cases`
4. `presentation` ou payload builder da tela consumidora
5. legado em `boxcore` apenas quando o corredor novo ainda depender dele

## O que esse perfil deve preservar

1. view fina
2. regra fora da borda
3. contrato pequeno e serializavel
4. borda sem dependencia desnecessaria de `infrastructure`

## Erros mais caros

1. reintroduzir `boxcore` como resposta padrao
2. misturar leitura pesada com mutacao
3. duplicar regra entre trilho novo e trilho historico
4. criar facade que nao reduz acoplamento real
