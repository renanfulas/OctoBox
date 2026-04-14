<!--
ARQUIVO: checklist copiavel e preenchivel para restore PostgreSQL em homologacao.

TIPO DE DOCUMENTO:
- template operacional

AUTORIDADE:
- media

DOCUMENTOS IRMAOS:
- [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
- [phase1-execution-evidence-2026-04-13.md](phase1-execution-evidence-2026-04-13.md)

QUANDO USAR:
- no dia do restore PostgreSQL real
- durante homologacao
- como folha unica de preenchimento durante a execucao

POR QUE ELE EXISTE:
- evita que o time tenha que montar planilha ou bloco de notas na hora.
- transforma o runbook em evidência operacional preenchível.

PONTOS CRITICOS:
- preencher durante a execucao, nao depois de memoria.
- se houver falha critica, marcar e parar o roteiro.
-->

# Checklist preenchivel - Restore PostgreSQL em homologacao

## Identificacao da rodada

| Campo | Preencher |
| --- | --- |
| Data | |
| Inicio | |
| Fim | |
| Responsavel tecnico | |
| Responsavel pela evidencia | |
| URL da homologacao | |
| Release / commit | |
| Banco principal | |
| Banco de restore | |
| Arquivo `.dump` usado | |

---

## Parte A. Pronto ou nao pronto

Marcar `sim` ou `nao`.

| Item | Status | Observacao |
| --- | --- | --- |
| Existe banco PostgreSQL principal da homologacao | | |
| Existe banco isolado de restore | | |
| `pg_dump`, `pg_restore` e `psql` estao instalados | | |
| `DATABASE_URL` esta configurada | | |
| `DJANGO_SECRET_KEY` esta configurada | | |
| `PHONE_BLIND_INDEX_KEY` esta configurada | | |
| `REDIS_URL` esta configurada | | |
| `DJANGO_ALLOWED_HOSTS` esta coerente | | |
| `DJANGO_CSRF_TRUSTED_ORIGINS` esta coerente | | |
| `OPERATIONS_MANAGER_WORKSPACE_ENABLED=True` esta ativo se o piloto incluir Manager | | |
| A app sobe com `manage.py check` ou equivalente | | |
| `migrate`, `collectstatic` e `bootstrap_roles` ja foram executados | | |
| `/api/v1/health/`, `/login/` e `/dashboard/` respondem na homologacao | | |
| Existe usuario valido para `Owner` | | |
| Existe usuario valido para `Manager` | | |
| Existe usuario valido para `Recepcao` | | |

Gate:

1. se qualquer linha estiver `nao`, parar aqui

---

## Parte B. Backup real

### Comando executado

```powershell
Set-ExecutionPolicy -Scope Process Bypass
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/backup_postgres.ps1 -DbHost __________________ -Port ______ -Database __________________ -User __________________ -Password $securePassword
```

### Registro

| Campo | Preencher |
| --- | --- |
| Horario do backup | |
| Caminho do arquivo | |
| Tamanho do arquivo | |
| Backup concluido sem erro? | |

Failure checks:

1. arquivo nao criado
2. tamanho zero
3. comando falhou

---

## Parte C. Restore no banco isolado

### Comando executado

```powershell
Set-ExecutionPolicy -Scope Process Bypass
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/restore_postgres.ps1 -DbHost __________________ -Port ______ -Database __________________ -User __________________ -BackupFile __________________ -Password $securePassword
```

### Registro

| Campo | Preencher |
| --- | --- |
| Inicio do restore | |
| Fim do restore | |
| Banco restaurado | |
| Restore concluido sem erro? | |

Failure checks:

1. `pg_restore` falhou
2. banco restaurado nao conectou
3. restore apontou para banco errado

---

## Parte D. Validacao da app contra o banco restaurado

### Comando de verificacao basica

```powershell
py manage.py check
```

### Registro

| Item | Resultado | Observacao |
| --- | --- | --- |
| `manage.py check` verde | | |
| Processo sobe | | |
| Assets carregam | | |
| `health` responde `200` | | |
| Login funciona | | |

Gate:

1. se `health` ou login falhar, parar aqui

---

## Parte E. Smoke funcional

Marcar resultado de cada rota:

| Rota | Resultado | Observacao |
| --- | --- | --- |
| `/api/v1/health/` | | |
| `/login/` | | |
| `/dashboard/` | | |
| `/operacao/owner/` | | |
| `/operacao/manager/` | | |
| `/operacao/recepcao/` | | |
| `/alunos/` | | |
| `/grade-aulas/` | | |

Failure checks:

1. qualquer rota central com `500`
2. `manager` falhar quando o piloto incluir esse papel
3. `owner` ou `recepcao` falharem

---

## Parte F. Resultado final

| Item | Preencher |
| --- | --- |
| Restore PostgreSQL aprovado? | |
| Bloqueador da Fase 1 pode ser removido? | |
| Pendencias abertas | |
| Proximo passo | |

## Formula curta

1. se esta folha nao fecha verde, o primeiro box ainda nao entra
