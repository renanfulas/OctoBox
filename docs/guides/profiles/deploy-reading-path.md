<!--
ARQUIVO: trilha de leitura para deploy e operacao.

TIPO DE DOCUMENTO:
- trilha de onboarding por perfil

AUTORIDADE:
- media para onboarding de deploy

DOCUMENTO PAI:
- [../governance-reading-index.md](../governance-reading-index.md)
-->

# Trilha de leitura para Deploy e Operacao

## Objetivo

Esta trilha existe para quem vai tocar:

1. deploy
2. rollback
3. restore
4. baseline de ambiente
5. observabilidade
6. seguranca operacional

## Ordem recomendada

1. [../../../README.md](../../../README.md)
2. [../general-architecture-guide.md](../general-architecture-guide.md)
3. [../performance-architecture-guide.md](../performance-architecture-guide.md)
4. [../security-architecture-guide.md](../security-architecture-guide.md)
5. [../../reference/production-security-baseline.md](../../reference/production-security-baseline.md)
6. [../../reference/external-security-edge-playbook.md](../../reference/external-security-edge-playbook.md)
7. [../../reference/cloudflare-edge-rules.md](../../reference/cloudflare-edge-rules.md)
8. [../../rollout/hostinger-vps-production-deploy.md](../../rollout/hostinger-vps-production-deploy.md)
9. [../../rollout/hostinger-vps-post-deploy-smoke-checklist.md](../../rollout/hostinger-vps-post-deploy-smoke-checklist.md)

## Depois disso, entre no runtime

Leia primeiro:

1. `config/settings/base.py`
2. middlewares de monitoramento e seguranca
3. comandos de smoke, integrity e sync em `shared_support/management/commands/*`
4. pontos de metrics e telemetria

## O que esse perfil deve preservar

1. baseline antes de improviso
2. proxy confiavel antes de confiar em IP
3. throttle antes de blocklist agressiva
4. smoke depois de publicar
5. rollback preparado antes da pressa

## Erros mais caros

1. publicar sem smoke
2. endurecer sem observabilidade
3. bloquear sem evidencia
4. mudar runtime sem alinhar runbook
