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

Hoje, a Fase 1 esta travada por infraestrutura de homologacao PostgreSQL ainda ausente neste ambiente.

O que ja foi provado:

1. o codigo e os runbooks estao prontos
2. o runtime local esta saudavel
3. o restore local em SQLite foi provado
4. o rollback controlado foi provado

O que ainda nao foi provado:

1. PostgreSQL real de homologacao
2. banco isolado de restore
3. ferramentas `psql`, `pg_dump`, `pg_restore`
4. envs reais da homologacao
5. app de homologacao publicada contra PostgreSQL

## Quadro preenchido

| Area | Status | Ja existe | Faltando | Dono | Proximo comando ou acao |
| --- | --- | --- | --- | --- | --- |
| Host da homologacao | `bloqueador` | runbooks e checklist prontos no repo | host real definido para homologacao | Ops / Infra | definir host, URL e acesso operacional |
| PostgreSQL principal | `bloqueador` | contrato, runbook de restore e script [provision_postgres_homolog_local.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/provision_postgres_homolog_local.ps1) | instancia PostgreSQL 15+ da homologacao | Ops / Infra | abrir PowerShell elevado e provisionar a instancia ou criar host externo |
| Banco isolado de restore | `bloqueador` | runbook exige esse banco | banco `octobox_restore_test` ou equivalente | Ops / Infra | criar banco isolado para o drill |
| Ferramentas PostgreSQL | `bloqueador` | scripts [backup_postgres.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/backup_postgres.ps1) e [restore_postgres.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/restore_postgres.ps1) | `psql`, `pg_dump`, `pg_restore` no host operacional | Ops / Infra | instalar PostgreSQL client tools e validar com `Get-Command psql, pg_dump, pg_restore` |
| Redis de homologacao | `bloqueador` | contrato de env documentado | Redis real e `REDIS_URL` real | Ops / Infra | provisionar Redis e registrar `REDIS_URL` |
| Env vars criticas | `bloqueador` | `.env.example` documenta as chaves necessarias | envs reais carregadas no host | Ops / Infra | definir `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, `PHONE_BLIND_INDEX_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `BOX_RUNTIME_SLUG` |
| App de homologacao | `bloqueador` | app local validada; docs de deploy existem | deploy homolog publicado e saudavel | Engenharia / Ops | publicar homologacao e validar `/api/v1/health/`, `/login/`, `/dashboard/` |
| Usuarios de teste | `parcial` | papeis e `bootstrap_roles` funcionam localmente | usuarios reais `Owner`, `Manager`, `Recepcao` na homologacao | Operacao / Engenharia | executar `bootstrap_roles` e criar usuarios de teste |
| Pasta de evidencias | `parcial` | docs e templates de evidencias existem | pasta real da rodada e responsavel definidos | Operacao / Engenharia | criar pasta da rodada e copiar o template do restore |
| Restore PostgreSQL real | `bloqueador` | runbook pronto e restore local SQLite provado | execucao real contra homologacao PostgreSQL | Ops / Engenharia | rodar [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md) quando os pre-requisitos acima estiverem verdes |

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

1. `psql` ausente
2. `pg_dump` ausente
3. `pg_restore` ausente
4. envs criticas da homologacao nao carregadas nesta sessao

Tentativa de destravar:

1. o pacote `postgresql15` foi localizado no Chocolatey
2. o pacote `redis` foi localizado no Chocolatey
3. a instalacao real falhou porque este PowerShell nao esta elevado como Administrador
4. por isso o menor caminho repetivel agora e o script [provision_postgres_homolog_local.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/provision_postgres_homolog_local.ps1) rodado em shell elevado

## Failure checks

Nao avancar para o restore real se qualquer item abaixo continuar verdadeiro:

1. nao existe host da homologacao definido
2. nao existe PostgreSQL 15+ acessivel
3. nao existe banco isolado para restore
4. `psql`, `pg_dump` ou `pg_restore` continuam ausentes
5. `DATABASE_URL` e `REDIS_URL` reais continuam ausentes
6. a app de homologacao ainda nao responde em `/api/v1/health/`
7. os usuarios `Owner`, `Manager` e `Recepcao` ainda nao existem na homologacao

## Menor caminho para destravar

### Onda 1. Infra

1. definir o host da homologacao
2. provisionar PostgreSQL 15+
3. criar:
   - banco principal
   - banco isolado de restore
4. provisionar Redis
5. instalar client tools do PostgreSQL

### Onda 2. Runtime

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

### Onda 3. Drill

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

### 3. Quando o host estiver pronto, abrir o runbook

1. [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md)
2. [postgres-homolog-restore-checklist-template.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-checklist-template.md)

## Veredito desta rodada

### Pode abrir o primeiro box hoje?

Nao.

### Motivo

O bloqueador restante nao esta no codigo. Ele esta na ausencia da homologacao PostgreSQL real e do restore executado nela.

### Formula curta

1. o carro esta pronto
2. a oficina esta arrumada
3. o manual esta escrito
4. falta construir a pista real e fazer a volta nela
