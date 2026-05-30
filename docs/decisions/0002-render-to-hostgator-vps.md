<!-- ARQUIVO: lição 0002 — deploy saiu do Render para HostGator VPS. -->
# 0002 — Deploy saiu do Render para HostGator VPS

- **date:** 2026-05-30
- **area:** `docs/rollout/hostgator/`, `scripts/linux/*`, `scripts/hostgator_*`, `scripts/linux/bootstrap_hostgator_octobox.sh`
- **status:** active

## O que mudou
A rota de deploy **abandonou o Render** (PaaS). `render.yaml` foi removido do repo. Produção passou a rodar em **VPS HostGator self-hosted**: gunicorn + nginx + PostgreSQL + Redis na mesma máquina, backup externo no Cloudflare R2, tudo provisionado por `scripts/linux/bootstrap_hostgator_octobox.sh`. Runbooks atuais: `docs/rollout/hostgator/`.

## Por quê
Migração para infra self-hosted controlada (VPS única) em vez de PaaS gerenciado. (A rota Render nunca foi a produção real corrente.)

## Lição / padrão reutilizável
1. **Docs de procedimento morto são DELETADOS, não arquivados** — quando o "porquê" já está num decision-log como este. Os docs Render (`deploy-homologation.md`, `homologation-deploy-checklist.md`) foram apagados; o conteúdo original continua recuperável no **git history**.
2. **Cuidado com o nome do provedor:** por um tempo os docs diziam "Hostinger" descrevendo o servidor **HostGator** (nomes quase idênticos). Fonte da verdade é sempre o **script** (`hostgator_*`, `infra/hostgator-vps/`), não a prosa.
3. Rota atual de deploy/backup/restore/rollback/smoke: **`docs/rollout/hostgator/`** (corrigidos dos scripts, não copiados de prosa stale).
