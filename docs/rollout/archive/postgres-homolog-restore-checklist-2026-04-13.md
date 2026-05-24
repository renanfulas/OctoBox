<!--
ARQUIVO: checklist preenchido do restore PostgreSQL em homologacao em 2026-04-13.

TIPO DE DOCUMENTO:
- evidencia operacional preenchida

AUTORIDADE:
- media

DOCUMENTOS IRMAOS:
- [postgres-homolog-restore-checklist-template.md](postgres-homolog-restore-checklist-template.md)
- [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md)
- [phase1-execution-evidence-2026-04-13.md](phase1-execution-evidence-2026-04-13.md)
-->

# Checklist preenchido - Restore PostgreSQL em homologacao - 2026-04-13

## Identificacao da rodada

| Campo | Preencher |
| --- | --- |
| Data | `2026-04-13` |
| Inicio | `execucao local nesta thread` |
| Fim | `execucao local nesta thread` |
| Responsavel tecnico | `Codex` |
| Responsavel pela evidencia | `Codex` |
| URL da homologacao | `nao disponivel neste ambiente` |
| Release / commit | `dc5ef8a` |
| Banco principal | `nao disponivel neste ambiente` |
| Banco de restore | `nao disponivel neste ambiente` |
| Arquivo `.dump` usado | `nao aplicavel` |

---

## Parte A. Pronto ou nao pronto

Marcar `sim` ou `nao`.

| Item | Status | Observacao |
| --- | --- | --- |
| Existe banco PostgreSQL principal da homologacao | `nao` | nenhum servico PostgreSQL detectado |
| Existe banco isolado de restore | `nao` | banco de restore nao existe neste ambiente |
| `pg_dump`, `pg_restore` e `psql` estao instalados | `nao` | `shutil.which(...)` retornou `None` para os tres binarios |
| `DATABASE_URL` esta configurada | `nao` | nenhuma variavel `DATABASE_URL` presente no ambiente atual |
| `DJANGO_SECRET_KEY` esta configurada | `nao` | nao havia env carregada nesta sessao para homologacao |
| `PHONE_BLIND_INDEX_KEY` esta configurada | `nao` | nao havia env carregada nesta sessao para homologacao |
| `REDIS_URL` esta configurada | `nao` | nenhuma variavel `REDIS_URL` presente no ambiente atual |
| `DJANGO_ALLOWED_HOSTS` esta coerente | `nao` | nao havia env de homologacao carregada nesta sessao |
| `DJANGO_CSRF_TRUSTED_ORIGINS` esta coerente | `nao` | nao havia env de homologacao carregada nesta sessao |
| `OPERATIONS_MANAGER_WORKSPACE_ENABLED=True` esta ativo se o piloto incluir Manager | `nao` | nao havia env carregada; a validacao anterior do manager foi feita de forma manual no processo de teste |
| A app sobe com `manage.py check` ou equivalente | `sim` | `py manage.py check` verde no workspace local |
| `migrate`, `collectstatic` e `bootstrap_roles` ja foram executados | `nao` | nao ha evidencia de homologacao PostgreSQL nesta maquina |
| `/api/v1/health/`, `/login/` e `/dashboard/` respondem na homologacao | `nao` | nao existe host de homologacao identificado neste ambiente |
| Existe usuario valido para `Owner` | `sim` | usuario local identificado no banco SQLite atual |
| Existe usuario valido para `Manager` | `sim` | usuario local identificado no banco SQLite atual |
| Existe usuario valido para `Recepcao` | `sim` | usuario local identificado no banco SQLite atual |

Gate:

1. ha multiplos itens em `nao`
2. o roteiro de restore PostgreSQL nao pode ser executado neste ambiente ainda

---

## Parte B. Backup real

### Comando executado

`nao executado`

### Registro

| Campo | Preencher |
| --- | --- |
| Horario do backup | `nao executado` |
| Caminho do arquivo | `nao executado` |
| Tamanho do arquivo | `nao executado` |
| Backup concluido sem erro? | `nao` |

---

## Parte C. Restore no banco isolado

### Comando executado

`nao executado`

### Registro

| Campo | Preencher |
| --- | --- |
| Inicio do restore | `nao executado` |
| Fim do restore | `nao executado` |
| Banco restaurado | `nao executado` |
| Restore concluido sem erro? | `nao` |

---

## Parte D. Validacao da app contra o banco restaurado

### Registro

| Item | Resultado | Observacao |
| --- | --- | --- |
| `manage.py check` verde | `sim` | validacao local no runtime SQLite atual |
| Processo sobe | `parcial` | so no ambiente local atual |
| Assets carregam | `parcial` | nao validado em homologacao PostgreSQL |
| `health` responde `200` | `parcial` | validado apenas no ambiente local |
| Login funciona | `parcial` | validado apenas no ambiente local |

---

## Parte E. Smoke funcional

| Rota | Resultado | Observacao |
| --- | --- | --- |
| `/api/v1/health/` | `parcial` | validado apenas em ambiente local |
| `/login/` | `parcial` | nao validado em homologacao PostgreSQL |
| `/dashboard/` | `parcial` | validado apenas em ambiente local |
| `/operacao/owner/` | `parcial` | validado apenas em ambiente local |
| `/operacao/manager/` | `parcial` | validado apenas em ambiente local com flag ligada |
| `/operacao/recepcao/` | `parcial` | validado apenas em ambiente local |
| `/alunos/` | `parcial` | validado apenas em ambiente local |
| `/grade-aulas/` | `parcial` | validado apenas em ambiente local |

---

## Parte F. Resultado final

| Item | Preencher |
| --- | --- |
| Restore PostgreSQL aprovado? | `nao` |
| Bloqueador da Fase 1 pode ser removido? | `nao` |
| Pendencias abertas | `provisionar homologacao PostgreSQL`, `instalar pg_dump/pg_restore/psql`, `definir envs reais`, `executar backup e restore reais` |
| Proximo passo | `subir a homologacao PostgreSQL e rerodar este checklist` |

## Formula curta

1. hoje foi possivel executar o preflight real
2. ele provou que a infraestrutura de homologacao PostgreSQL ainda nao existe neste ambiente
