<!--
ARQUIVO: roteiro exato de restore PostgreSQL em homologacao para a Fase 1.

TIPO DE DOCUMENTO:
- runbook operacional

AUTORIDADE:
- alta para liberar o primeiro box

DOCUMENTOS IRMAOS:
- [backup-guide.md](backup-guide.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md)
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)
- [postgres-homolog-restore-checklist-template.md](postgres-homolog-restore-checklist-template.md)

QUANDO USAR:
- quando a homologacao PostgreSQL estiver pronta
- antes de liberar o primeiro box
- sempre que houver duvida se a restauracao real foi de fato provada

POR QUE ELE EXISTE:
- transforma o ultimo bloqueador da Fase 1 em uma sequencia executavel.
- evita o erro classico de ter backup mas nao conseguir religar a casa.

PONTOS CRITICOS:
- nao executar este roteiro contra o banco ativo do box real.
- o alvo deste roteiro e um banco isolado de restauracao.
-->

# Roteiro exato do restore PostgreSQL em homologacao

## Objetivo

Provar em ambiente PostgreSQL real que o time consegue:

1. gerar um backup valido
2. restaurar esse backup em banco isolado
3. subir a aplicacao contra o banco restaurado
4. validar login e rotas centrais
5. registrar evidencias suficientes para remover o bloqueador da Fase 1

Em linguagem simples:

1. nao basta guardar a chave reserva
2. precisamos abrir a porta com ela

---

## Definicao de aprovado

O restore PostgreSQL so fica aprovado quando:

1. um arquivo `.dump` real foi gerado
2. o restore em banco isolado terminou sem erro
3. `/api/v1/health/` respondeu `200`
4. login funcionou
5. as rotas centrais responderam sem `500`
6. horario, banco alvo, arquivo e responsavel ficaram registrados

---

## Precondicoes obrigatorias

Antes de comecar, confirmar estes seis itens:

1. existe uma homologacao PostgreSQL funcional
2. `pg_dump` e `pg_restore` estao instalados na maquina ou runner do ensaio
3. existe um banco de restore isolado, por exemplo `octobox_restore_test`
4. o app de homologacao pode ser apontado para esse banco isolado
5. ha um responsavel tecnico e um responsavel por registrar a evidencia
6. o box real ainda nao depende deste banco de teste para operar

Se qualquer um falhar:

1. parar o roteiro
2. nao improvisar
3. corrigir a precondicao antes de seguir

---

## Checklist rapido: pronto ou nao pronto

Use este bloco antes de rodar qualquer comando.

Se qualquer resposta for `nao`, o runbook para aqui.

| Item | Pronto? |
| --- | --- |
| Existe banco PostgreSQL principal da homologacao | `sim / nao` |
| Existe banco isolado de restore, como `octobox_restore_test` | `sim / nao` |
| `pg_dump`, `pg_restore` e `psql` estao instalados | `sim / nao` |
| `DATABASE_URL`, `DJANGO_SECRET_KEY`, `PHONE_BLIND_INDEX_KEY` e `REDIS_URL` estao configurados | `sim / nao` |
| `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` estao coerentes com a URL de homologacao | `sim / nao` |
| `OPERATIONS_MANAGER_WORKSPACE_ENABLED=True` esta definido se o piloto incluir Manager | `sim / nao` |
| A app de homologacao sobe com `manage.py check` ou equivalente | `sim / nao` |
| `migrate`, `collectstatic` e `bootstrap_roles` ja foram executados | `sim / nao` |
| `/api/v1/health/`, `/login/` e `/dashboard/` ja respondem no host de homologacao | `sim / nao` |
| Existe pelo menos um usuario valido para `Owner`, `Manager` e `Recepcao` | `sim / nao` |
| Existe um responsavel tecnico pelo restore | `sim / nao` |
| Existe um responsavel por registrar a evidencia final | `sim / nao` |

Formula curta:

1. se qualquer linha ficar em `nao`, ainda nao e hora de puxar a alavanca

---

## Variaveis que precisam estar em maos

Registrar antes de executar:

1. `DbHost`
2. `Port`
3. `Database` da homologacao principal
4. `RestoreDatabase` isolado
5. `User`
6. URL ou hostname da homologacao
7. hash ou release atual da aplicacao

Tabela rapida:

| Campo | Exemplo |
| --- | --- |
| DbHost | `localhost` |
| Port | `5432` |
| Database | `octobox_control` |
| RestoreDatabase | `octobox_restore_test` |
| User | `postgres` |
| URL | `https://homolog.seudominio.com` |
| Release | `dc5ef8a` |

---

## Parte A. Gerar o backup real

### Passo 1. Rodar backup

```powershell
Set-ExecutionPolicy -Scope Process Bypass
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/backup_postgres.ps1 -DbHost localhost -Port 5432 -Database octobox_control -User postgres -Password $securePassword
```

### O que verificar

1. arquivo `.dump` criado em `backups/`
2. timestamp coerente
3. tamanho do arquivo maior que zero

### Evidencia minima

1. caminho completo do arquivo
2. horario da geracao
3. tamanho do arquivo

### Failure checks

Se qualquer item abaixo acontecer, o backup falhou:

1. arquivo nao foi criado
2. arquivo ficou com tamanho zero
3. `pg_dump` retornou erro

---

## Parte B. Restaurar em banco isolado

### Passo 2. Garantir que o banco de restore existe

O banco isolado precisa existir antes do restore.

Exemplo manual com `psql`:

```powershell
$env:PGPASSWORD="sua_senha"
psql -h localhost -U postgres -c "CREATE DATABASE octobox_restore_test;"
```

Se o banco ja existir:

1. manter o nome
2. confirmar que ele nao e usado pela homologacao viva

### Passo 3. Rodar o restore

```powershell
Set-ExecutionPolicy -Scope Process Bypass
$securePassword = Read-Host "Senha do banco" -AsSecureString
./scripts/restore_postgres.ps1 -DbHost localhost -Port 5432 -Database octobox_restore_test -User postgres -BackupFile backups/octobox-AAAAmmdd-HHmmss.dump -Password $securePassword
```

### O que verificar

1. o comando terminou sem erro
2. o banco restaurado responde conexao
3. tabelas principais existem

### Evidencia minima

1. horario de inicio
2. horario de fim
3. nome do banco restaurado
4. caminho do arquivo usado

### Failure checks

Se qualquer item abaixo acontecer, o restore falhou:

1. `pg_restore` falhou
2. o banco restaurado nao aceita conexao
3. as tabelas principais nao aparecem

---

## Parte C. Subir a app contra o banco restaurado

### Passo 4. Apontar a homologacao de teste para o banco isolado

Neste passo, use um ambiente isolado da homologacao ou um processo temporario do app.

Variaveis minimas:

```env
DJANGO_ENV=production
DJANGO_DEBUG=False
DATABASE_URL=postgresql://postgres:senha@host:5432/octobox_restore_test
DJANGO_ALLOWED_HOSTS=homolog.seudominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://homolog.seudominio.com
DJANGO_SECRET_KEY=...
PHONE_BLIND_INDEX_KEY=...
REDIS_URL=...
OPERATIONS_MANAGER_WORKSPACE_ENABLED=True
```

### Passo 5. Validar integridade basica

Rodar:

```powershell
py manage.py check
```

Se a homologacao usa Linux/gunicorn, o equivalente deve ser executado no runtime real.

### Failure checks

Se qualquer item abaixo acontecer, parar:

1. `manage.py check` falha
2. o processo nao sobe
3. assets nao carregam

---

## Parte D. Smoke funcional do restore

### Passo 6. Validar o minimo vital

Testar nesta ordem:

1. `/api/v1/health/`
2. `/login/`
3. `/dashboard/`
4. `/operacao/owner/`
5. `/operacao/manager/`
6. `/operacao/recepcao/`
7. `/alunos/`
8. `/grade-aulas/`

### Resultado esperado

1. `health` responde `200`
2. login funciona
3. rotas centrais sem `500`
4. papeis principais entram nas telas certas

### Failure checks

Se qualquer item abaixo acontecer, reprovar:

1. `health` nao responde `200`
2. login nao funciona
3. `owner`, `manager` ou `reception` falham
4. a app sobe, mas as rotas centrais quebram

---

## Parte E. Registrar a evidencia

Ao final, registrar:

1. data e hora do ensaio
2. nome do banco restaurado
3. arquivo `.dump` utilizado
4. responsavel tecnico
5. resultado do `health`
6. resultado do login
7. lista de rotas testadas
8. tempo total do restore

Modelo curto:

| Campo | Valor |
| --- | --- |
| Data | `AAAA-MM-DD` |
| Inicio | `HH:MM` |
| Fim | `HH:MM` |
| Banco restore | `octobox_restore_test` |
| Arquivo | `backups/octobox-...dump` |
| Health | `200` |
| Login | `ok` |
| Rotas | `health, dashboard, owner, manager, reception, alunos, grade` |
| Responsavel | `nome` |

---

## Como isso fecha a Fase 1

Depois deste roteiro:

1. atualizar [phase1-execution-evidence-2026-04-13.md](phase1-execution-evidence-2026-04-13.md)
2. mudar `Restore testado` para `validado` em [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)
3. repetir o smoke do go-live no ambiente alvo se a URL final for diferente

---

## Formula curta

Se a homologacao PostgreSQL nao consegue levantar a casa restaurada e abrir as portas principais, o primeiro box ainda esta confiando em sorte.
