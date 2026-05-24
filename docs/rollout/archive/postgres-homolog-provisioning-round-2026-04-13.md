<!--
ARQUIVO: rodada preenchida de provisionamento da homologacao PostgreSQL em 2026-04-13.

TIPO DE DOCUMENTO:
- vistoria operacional

AUTORIDADE:
- alta para o fechamento da Fase 1

DOCUMENTOS IRMAOS:
- [postgres-homolog-provisioning-checklist.md](postgres-homolog-provisioning-checklist.md)
- [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md)
- [postgres-homolog-restore-checklist-template.md](postgres-homolog-restore-checklist-template.md)
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)

QUANDO USAR:
- para transformar o checklist generico em uma rodada real
- para saber exatamente o que falta antes do restore PostgreSQL
- para evitar "acho que esta pronto" sem evidencia

PONTO CRITICO:
- este documento descreve o estado real do ambiente acessivel nesta data
- se a homologacao existir em outro host, este documento deve ser atualizado la tambem
-->

# Rodada de provisionamento da homologacao PostgreSQL - 2026-04-13

## Objetivo

Registrar o estado real da homologacao PostgreSQL da Fase 1, separando:

1. o que ja existe
2. o que falta
3. quem e o dono
4. qual e o proximo comando ou acao

Em linguagem simples: este documento e a prancheta do vistoriador. Ele nao pergunta "a casa ideal existe?". Ele pergunta "o que ja tem nesta casa, o que falta instalar e quem vai buscar a peca?".

## Resumo executivo

O bloqueador de infraestrutura da homologacao PostgreSQL foi fechado nesta rodada local.

O que ja foi provado:

1. o codigo e os runbooks estao prontos
2. o runtime local esta saudavel
3. o restore local em SQLite foi provado
4. o rollback controlado foi provado

O que ainda nao foi provado no host definitivo do piloto:

1. deploy da homologacao definitiva do piloto
2. host final com HTTPS e dominios reais
3. repeticao do mesmo ritual fora desta maquina local

## Quadro preenchido

| Area | Status | Ja existe | Faltando | Dono | Proximo comando ou acao |
| --- | --- | --- | --- | --- | --- |
| Host da homologacao | `validado` | homologacao local definida nesta maquina | host definitivo do piloto ainda nao definido | Ops / Infra | definir depois o host definitivo do piloto |
| PostgreSQL principal | `validado` | PostgreSQL 15 local instalado e banco `octobox_homolog` criado | nenhuma pendencia local | Ops / Infra | repetir no host definitivo quando ele existir |
| Banco isolado de restore | `validado` | banco `octobox_restore_test` criado e usado no drill | nenhuma pendencia local | Ops / Infra | repetir no host definitivo quando ele existir |
| Ferramentas PostgreSQL | `validado` | `psql`, `pg_dump`, `pg_restore` disponiveis via `C:\Program Files\PostgreSQL\15\bin` | nenhuma pendencia local | Ops / Infra | opcional: adicionar `bin` ao `PATH` global do host definitivo |
| Redis de homologacao | `validado` | Redis local instalado e respondendo `PONG` em `localhost:6379` | nenhuma pendencia local | Ops / Infra | repetir no host definitivo quando ele existir |
| Env vars criticas | `validado` | `.env.homolog.local` gerado com `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, `PHONE_BLIND_INDEX_KEY`, `BOX_RUNTIME_SLUG` e afins | domínios reais do piloto ainda nao definidos | Ops / Infra | ajustar apenas no host definitivo |
| App de homologacao | `validado` | `migrate`, `check`, `sync_runtime_assets`, `bootstrap_roles` e smoke contra o banco restaurado validados localmente | deploy definitivo com HTTPS ainda nao feito | Engenharia / Ops | repetir no host final do piloto |
| Usuarios de teste | `validado` | `owner_homolog`, `manager_homolog`, `recepcao_homolog` criados no banco principal e copiados no restore | nenhuma pendencia local | Operacao / Engenharia | trocar por usuarios reais do box piloto |
| Pasta de evidencias | `parcial` | docs, dump e evidencias existem no repo e em `backups/` | consolidar pasta operacional da rodada do piloto real | Operacao / Engenharia | organizar evidencia final do host definitivo |
| Restore PostgreSQL real | `validado` | dump `backups/octobox-20260414-013716.dump` restaurado em `octobox_restore_test` com validacao de dados e smoke `200` | repetir no host definitivo do piloto quando existir | Ops / Engenharia | guardar este ritual como padrao do piloto |

## Evidencia coletada nesta rodada

### Ja existe

1. [postgres-homolog-provisioning-checklist.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-provisioning-checklist.md)
2. [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md)
3. [postgres-homolog-restore-checklist-template.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-checklist-template.md)
4. [backup_postgres.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/backup_postgres.ps1)
5. [restore_postgres.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/restore_postgres.ps1)
6. validacao interna da Fase 1 verde em `2026-04-13` com:
   - `py manage.py check`
   - `py manage.py sync_runtime_assets --collectstatic`
   - `111 tests` verdes

### Faltando com evidencia direta

Comandos executados nesta maquina:

```powershell
Get-Command psql, pg_dump, pg_restore
Get-ChildItem Env: | Where-Object {
  $_.Name -match 'DATABASE_URL|REDIS_URL|DJANGO_SECRET_KEY|PHONE_BLIND_INDEX_KEY|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|BOX_RUNTIME_SLUG|OPERATIONS_MANAGER_WORKSPACE_ENABLED'
}
```

Leitura:

1. host definitivo do piloto ainda nao foi definido
2. HTTPS e dominios reais do piloto ainda nao foram configurados
3. o ritual ainda precisa ser repetido no ambiente definitivo, nao apenas na homologacao local

## Failure checks

Nao avancar para o restore real se qualquer item abaixo continuar verdadeiro:

1. o host definitivo do piloto ainda nao existe
2. HTTPS e dominios reais do piloto ainda nao foram configurados
3. o ritual de restore ainda nao foi repetido fora desta maquina local

## Menor caminho para destravar

### Onda 1. Infra local

1. definir o host da homologacao
2. provisionar PostgreSQL 15+
3. criar:
   - banco principal
   - banco isolado de restore
4. provisionar Redis
5. instalar client tools do PostgreSQL

### Onda 2. Runtime local

1. carregar envs reais
2. publicar a app
3. rodar:
   - `migrate`
   - `collectstatic`
   - `bootstrap_roles`
4. validar:
   - `/api/v1/health/`
   - `/login/`
   - `/dashboard/`

### Onda 3. Drill local

1. criar usuarios de teste
2. copiar o template do restore para a rodada
3. gerar backup PostgreSQL
4. restaurar no banco isolado
5. rodar smoke
6. atualizar a matriz da Fase 1

## Proximos comandos

### 1. Verificar ferramentas PostgreSQL no host operacional

```powershell
Get-Command psql, pg_dump, pg_restore
```

### 1A. Se a homologacao for local e voce abrir um PowerShell como Administrador

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\provision_postgres_homolog_local.ps1
```

### 2. Verificar envs criticas no host da homologacao

```powershell
Get-ChildItem Env: | Where-Object {
  $_.Name -match 'DATABASE_URL|REDIS_URL|DJANGO_SECRET_KEY|PHONE_BLIND_INDEX_KEY|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|BOX_RUNTIME_SLUG|OPERATIONS_MANAGER_WORKSPACE_ENABLED'
}
```

### 3. Quando o host definitivo do piloto estiver pronto, abrir o runbook

1. [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md)
2. [postgres-homolog-restore-checklist-template.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-checklist-template.md)

## Veredito desta rodada

### Pode abrir o primeiro box hoje?

Ainda nao.

### Motivo

O bloqueador de homologacao PostgreSQL foi fechado localmente. O que falta agora e o trilho operacional do piloto real: host definitivo, usuarios reais do box, smoke final e war room.

### Formula curta

1. o carro esta pronto
2. a oficina esta arrumada
3. o manual esta escrito
4. agora falta levar esse mesmo carro para a pista definitiva do piloto
