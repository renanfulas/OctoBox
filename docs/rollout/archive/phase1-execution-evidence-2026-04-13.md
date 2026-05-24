<!--
ARQUIVO: evidencia executada da Fase 1 em 2026-04-13.

TIPO DE DOCUMENTO:
- log de execucao

AUTORIDADE:
- media

DOCUMENTOS IRMAOS:
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)
- [restore-and-rollback-drill.md](restore-and-rollback-drill.md)

QUANDO USAR:
- para registrar o que foi provado de verdade no ambiente de trabalho atual
- para distinguir evidencia real de intencao documental
-->

# Evidencia da Fase 1 - 2026-04-13

## Objetivo

Registrar o que foi executado de verdade durante a rodada de fechamento da Fase 1.

## Evidencias coletadas hoje

### 1. Integridade base do projeto

Comando:

```powershell
py manage.py check
```

Resultado:

1. `System check identified no issues (0 silenced).`

### 2. Contrato minimo da API v1

Comando:

```powershell
py manage.py test boxcore.tests.test_api
```

Resultado:

1. `4 tests` executados
2. `OK`

Leitura:

1. healthcheck e fronteira da API continuam de pe

### 3. `snapshot_version` nas superficies quentes

Comando executado via shell do Django para:

1. `owner`
2. `manager`
3. `reception`

Resultado:

1. `owner` emitindo `snapshot_version`
2. `manager` emitindo `snapshot_version`
3. `reception` emitindo `snapshot_version`

Leitura:

1. as tres superficies continuam com contrato de versao ativo

### 4. Backup local de referencia

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_sqlite.ps1
```

Resultado:

1. backup gerado em `backups/db-20260413-050155.sqlite3`

Leitura:

1. isso prova a trilha local
2. nao substitui o backup PostgreSQL do ambiente alvo

## O que NAO ficou provado hoje

Ainda nao ficou provado com evidencia real:

1. rollback de aplicacao em ambiente de homologacao
2. smoke funcional completo do dia D com Owner, Manager e Reception logados no ambiente final

## Evidencias adicionais coletadas na rodada seguinte

### 5. Drill local de restore em SQLite

Passos executados:

1. copia do backup local `backups/db-20260413-050155.sqlite3`
2. restauracao para `backups/restore-drill-20260413.sqlite3`
3. `PRAGMA integrity_check`
4. leitura de tabelas do banco restaurado
5. inicializacao do Django apontando para o arquivo restaurado

Resultado:

1. arquivo restaurado criado
2. `integrity = ok`
3. `table_count = 28`
4. `django_migrations = 40`

Leitura:

1. o trilho local de restore em SQLite foi provado
2. isso reduz risco de Fase 1 no ambiente atual
3. isso nao substitui o drill de restore em PostgreSQL da homologacao/producao

### 6. Preflight do rollback

Evidencia coletada:

1. HEAD atual identificado como `dc5ef8a`
2. commit anterior identificado como `9e0e2bb`
3. diff entre `HEAD~1` e `HEAD` listado
4. worktree atual esta suja com muitas modificacoes nao commitadas

Leitura:

1. existe um ponto de retorno identificavel
2. nao e seguro executar checkout de rollback real neste workspace agora
3. o drill de rollback continua bloqueado ate ocorrer em ambiente controlado ou branch limpa

## Conclusao desta rodada

Hoje foi possivel fechar com evidencia:

1. integridade base
2. contrato da API v1
3. runtime boundary e snapshots
4. backup local de referencia

Os bloqueadores reais que continuam abertos sao:

1. `rollback ensaiado`
2. `smoke funcional do go-live`
3. `restore PostgreSQL no ambiente alvo`

## Evidencias adicionais coletadas na rodada do smoke funcional

### 7. Smoke funcional local com host permitido

Primeira tentativa:

1. o smoke com `django.test.Client()` usando host padrao `testserver` falhou com `DisallowedHost`
2. isso nao indicou bug de produto; indicou apenas que o ambiente respeita `ALLOWED_HOSTS`

Rodada valida:

1. smoke repetido com `HTTP_HOST=localhost`
2. rotas com `200`:
   - `/api/v1/health/`
   - `/dashboard/` com `owner_morumbi`
   - `/operacao/owner/` com `owner_morumbi`
   - `/operacao/recepcao/` com `recepcao_santo_amaro`
   - `/alunos/` com `manager_vila_andrade`
   - `/grade-aulas/` com `coach_brooklin`
3. `/operacao/manager/` retornou `404` na primeira rodada valida

Leitura:

1. a rota do manager nao estava quebrada; ela estava desligada por `OPERATIONS_MANAGER_WORKSPACE_ENABLED=False`
2. isso e um bloqueador real de go-live quando o piloto incluir Manager

### 8. Smoke do manager com a feature flag ligada

Rodada valida:

1. `OPERATIONS_MANAGER_WORKSPACE_ENABLED=1` no processo de teste
2. `/operacao/manager/` respondeu `200`
3. `/operacao/manager/fragmentos/boards/` respondeu `200`

Leitura:

1. o workspace do manager esta funcional
2. o go-live precisa apenas carregar a flag correta no ambiente alvo

### 9. Ambiente controlado para rollback drill

Evidencia coletada:

1. worktree limpo ja existe em `C:/Users/renan/OneDrive/Documents/OctoBOX-rollback-drill`
2. branch dedicada identificada como `codex/rollback-drill-phase1`
3. HEAD do worktree limpo alinhado com `dc5ef8a`

Leitura:

1. o ensaio de rollback agora tem pista separada do workspace principal
2. isso reduz risco de apagar trabalho vivo durante o drill

### 10. Restore PostgreSQL preparado, mas ainda nao executado

Evidencia coletada:

1. o ambiente atual continua em SQLite
2. `pg_dump`, `pg_restore` e `psql` nao estao instalados nesta maquina
3. foi criado o script `scripts/restore_postgres.ps1` para o drill de homologacao

Leitura:

1. o restore PostgreSQL continua pendente
2. a fundacao operacional agora esta preparada para rodar assim que a homologacao PostgreSQL existir

### 12. Preflight real da homologacao PostgreSQL

Passos executados:

1. leitura das variaveis de ambiente criticas da homologacao
2. verificacao local de `psql`, `pg_dump`, `pg_restore` e `docker`
3. verificacao de servicos locais de PostgreSQL e Redis

Resultado:

1. nenhuma variavel de ambiente critica da homologacao estava carregada
2. `psql = None`
3. `pg_dump = None`
4. `pg_restore = None`
5. `docker = None`
6. nenhum servico local de PostgreSQL ou Redis foi encontrado

Leitura:

1. nao existe homologacao PostgreSQL pronta neste ambiente atual
2. portanto o restore real nao pode ser executado agora sem inventar infraestrutura
3. isso nao e falha do runbook; e ausencia de precondicao

Evidencia associada:

1. [postgres-homolog-restore-checklist-2026-04-13.md](postgres-homolog-restore-checklist-2026-04-13.md)

### 11. Rollback drill executado no worktree limpo

Ambiente usado:

1. worktree limpo em `C:/Users/renan/OneDrive/Documents/OctoBOX-rollback-drill`
2. branch de preparo `codex/rollback-drill-phase1`
3. banco apontado para `backups/restore-drill-20260413.sqlite3`
4. segredo e blind index temporarios apenas para o ensaio
5. `OPERATIONS_MANAGER_WORKSPACE_ENABLED=1` para incluir o papel Manager no circuito

Rodada A. Estado atual do app (`dc5ef8a`)

1. `py manage.py check` respondeu sem issues
2. smoke com `HTTP_HOST=localhost` respondeu `200` para:
   - `/api/v1/health/`
   - `/dashboard/`
   - `/operacao/owner/`
   - `/operacao/manager/`
   - `/operacao/recepcao/`
   - `/alunos/`
   - `/grade-aulas/`

Rodada B. Rollback para `9e0e2bb`

1. worktree voltou para `9e0e2bb`
2. `py manage.py check` respondeu sem issues
3. smoke repetido com o mesmo circuito respondeu `200` para todas as rotas centrais:
   - `/api/v1/health/`
   - `/dashboard/`
   - `/operacao/owner/`
   - `/operacao/manager/`
   - `/operacao/recepcao/`
   - `/alunos/`
   - `/grade-aulas/`

Rodada C. Retorno para o estado atual

1. worktree voltou para a branch `codex/rollback-drill-phase1`
2. HEAD final confirmado novamente em `dc5ef8a`

Leitura:

1. o drill de rollback de aplicacao foi provado em ambiente controlado
2. o time agora tem uma pista segura para repetir esse ensaio sem tocar no workspace principal
3. isso fecha o bloqueador de `rollback ensaiado`

Observacao:

1. o ensaio usou SQLite restaurado e ambiente controlado
2. ele nao substitui o restore PostgreSQL real da homologacao/producao

### 13. Rodada final de validacao interna do repositorio

Comandos:

```powershell
py manage.py check
py manage.py sync_runtime_assets --collectstatic
py manage.py test boxcore.tests.test_api boxcore.tests.test_catalog boxcore.tests.test_dashboard boxcore.tests.test_operations tests.test_manager_workspace_toggle --verbosity 1
```

Resultado:

1. `py manage.py check` respondeu sem issues
2. `sync_runtime_assets --collectstatic` sincronizou `static/css` e `static/js` com `staticfiles`
3. a bateria ampla executou `111 tests`
4. resultado final da bateria ampla: `OK`

Leitura:

1. o runtime local continua coerente depois dos merges recentes em `main`
2. os fluxos centrais da Fase 1 continuam de pe em `api`, `catalog`, `dashboard` e `operations`
3. o gargalo restante da Fase 1 nao esta mais no codigo do repositorio
4. o bloqueador real continua sendo a homologacao PostgreSQL com restore executado de verdade

### 14. Provisionamento local da homologacao PostgreSQL e restore real

Passos executados:

1. PostgreSQL 15 instalado localmente
2. Redis local instalado e respondendo `PONG`
3. bancos criados:
   - `octobox_homolog`
   - `octobox_restore_test`
4. arquivo de ambiente gerado em `.env.homolog.local`
5. `migrate` executado com sucesso usando a `.venv`
6. `sync_runtime_assets --collectstatic` executado com sucesso
7. `bootstrap_roles` executado com sucesso
8. usuarios de teste criados no banco principal:
   - `owner_homolog`
   - `manager_homolog`
   - `recepcao_homolog`
9. dump PostgreSQL gerado em `backups/octobox-20260414-013716.dump`
10. restore real executado para `octobox_restore_test`
11. validacao no banco restaurado:
   - `auth_user = 3`
   - `auth_group = 6`
12. validacao da aplicacao apontando para o banco restaurado:
   - `manage.py check` verde
   - `/api/v1/health/` = `200`
   - `/operacao/owner/` = `200`

Leitura:

1. a homologacao PostgreSQL local foi provada de verdade
2. o restore real deixou de ser hipotese e virou evidencia
3. a Fase 1 nao tem mais bloqueador tecnico no trilho de backup/restore
4. os proximos passos passam a ser operacionais do piloto, nao fundacao da homologacao
