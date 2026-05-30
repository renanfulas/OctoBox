<!--
ARQUIVO: runbook de RESTORE do PostgreSQL — HostGator VPS de producao.

POR QUE ELE EXISTE:
- restore so e protecao se foi ENSAIADO. Este runbook e o roteiro curto de prova e de
  recuperacao real, derivado do fluxo dos scripts de backup (R2 -> pg_restore).

FONTE DA VERDADE (codigo vence este doc):
- scripts/restore_postgres.ps1  (helper de restore local em Windows)
- rclone + pg_restore           (fluxo real na VPS Linux)

REGRA INEGOCIAVEL:
- NUNCA restaurar sobre o banco vivo do cliente. Sempre banco isolado.
-->

# Restore — HostGator VPS

Restore tem dois usos: **prova periódica** (provar que o backup presta) e **recuperação real**
(desastre). Os dois usam **banco isolado** — nunca o banco vivo.

## 1. Trazer o dump do R2 (se não estiver mais local)

```bash
# listar o que existe no R2
rclone lsf r2:octobox-backups/octoboxfit-production/ | tail

# baixar o dump escolhido para a VPS
rclone copyto r2:octobox-backups/octoboxfit-production/octobox-AAAAmmdd-HHmmss.dump \
  /srv/octobox/backups/octobox-AAAAmmdd-HHmmss.dump
```

## 2. Criar o banco isolado

```sql
CREATE DATABASE octobox_restore_test OWNER octobox_app;
```

## 3. Restaurar nele — `pg_restore`

```bash
PGPASSWORD='<senha>' pg_restore \
  --host 127.0.0.1 --port 5432 \
  --username octobox_app \
  --dbname octobox_restore_test \
  --clean --if-exists \
  /srv/octobox/backups/octobox-AAAAmmdd-HHmmss.dump
```

> **Local (Windows):** para restaurar um dump na sua máquina, use `scripts/restore_postgres.ps1`.

## 4. Validar depois do restore

1. `pg_restore` terminou **sem erro**;
2. conexão ao banco restaurado funciona;
3. tabelas principais existem (`\dt` mostra `boxcore_*`, `control_*` etc.);
4. smoke mínimo da app contra o banco isolado, quando der.

## 5. Registrar

Anote **horário, arquivo restaurado e responsável** (a prova só conta se ficou registrada).

## Recuperação REAL (desastre) — sequência

1. **Pare a app** (não deixe escrever no banco corrompido).
2. Restaure num banco **novo** (`octobox_control_restored`), não por cima do atual.
3. Valide (passo 4) **antes** de apontar a app pra ele.
4. Só então troque `DATABASE_URL` no `octobox.env` e suba a app.
5. Faça um backup imediato do estado recuperado.

## Failure checks — NÃO dê o restore por bom se:

- `pg_restore` reclamou de objeto/owner e você **ignorou**;
- restaurou num banco que **já tinha dados** (devia ser isolado/vazio);
- nunca validou as tabelas principais;
- é a **primeira vez** que você roda restore (ensaie ANTES de precisar de verdade).
