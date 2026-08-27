<!--
ARQUIVO: ensaio operacional de restore e rollback para a Fase 1.

TIPO DE DOCUMENTO:
- runbook de ensaio

AUTORIDADE:
- alta para liberar o primeiro box

DOCUMENTOS IRMAOS:
- [backup-guide.md](backup-guide.md)
- [postgres-homolog-restore-runbook.md](postgres-homolog-restore-runbook.md)
- [first-box-production-execution-checklist.md](first-box-production-execution-checklist.md)
- [phase1-closed-beta-operations-matrix.md](phase1-closed-beta-operations-matrix.md)

QUANDO USAR:
- antes do primeiro box
- sempre que houver duvida se o time sabe voltar sem panico

POR QUE ELE EXISTE:
- backup sem restore testado e rollback sem ensaio sao falsas sensacoes de seguranca.
- a Fase 1 precisa provar recuperacao, nao apenas deploy.

PONTOS CRITICOS:
- este ensaio deve ser feito em homologacao ou ambiente isolado.
- nao executar restore destrutivo no ambiente ativo de um box.
- as Partes A e B foram provadas em 2026-04 num runtime de banco/schema unico. A Parte C
  existe porque o runtime virou schema-per-tenant em 2026-05 e recuperar UM box passou a
  ser uma operacao diferente de recuperar o cluster.
-->

# Drill de restore e rollback da Fase 1

## Objetivo

Provar que o time consegue:

1. gerar backup
2. restaurar backup
3. voltar a aplicacao para uma versao anterior
4. recuperar um unico box sem afetar os outros
5. fazer isso com ordem e sem improviso

Em linguagem simples:

1. nao basta ter extintor pendurado na parede
2. precisamos saber puxar o pino sem tremer a mao

## Estado do ensaio

| Parte | Estado | Observacao |
| --- | --- | --- |
| A. Backup e restore do cluster | `aprovado em 2026-04-14` | evidencia em [archive/phase1-execution-evidence-2026-04-13.md](archive/phase1-execution-evidence-2026-04-13.md), item 14 |
| B. Rollback de aplicacao | `aprovado em 2026-04-13` | mesma evidencia, item 11 |
| C. Restore por tenant | `nunca executado` | **bloqueia prometer recuperacao individual em venda** — ver [phase1-commercial-gate-audit-2026-08-06.md](phase1-commercial-gate-audit-2026-08-06.md) |

Ressalva que vale para A e B: os dois foram provados **antes** da virada schema-per-tenant.
Continuam validos como prova de que o time sabe operar backup, restore e rollback — mas nao
provam nada sobre schemas de tenant. A Parte C cobre exatamente esse vao.

---

## Parte A. Drill de backup e restore

### Precondicoes

1. ambiente de homologacao ou restauracao isolada disponivel
2. acesso ao banco PostgreSQL
3. script [../../scripts/backup_postgres.ps1](../../scripts/backup_postgres.ps1) funcional
4. script [../../scripts/restore_postgres.ps1](../../scripts/restore_postgres.ps1) funcional
5. alguem responsavel por registrar horario e resultado

### Passo 1. Gerar backup real

Checklist:

1. rodar o script de backup
2. confirmar nome do arquivo
3. confirmar timestamp
4. confirmar tamanho do arquivo

Evidencia esperada:

1. caminho do arquivo `.dump`
2. horario do backup

### Passo 2. Restaurar em ambiente isolado

Checklist:

1. escolher banco de teste de restauracao
2. rodar o script de restore PostgreSQL
3. confirmar que o banco sobe sem erro
4. abrir `/api/v1/health/`
5. testar login
6. testar ao menos `/dashboard/`, `/alunos/` e `/operacao/`

Evidencia esperada:

1. horario de inicio e fim do restore
2. status do healthcheck
3. status do login
4. rotas testadas

### Failure checks do restore

Se qualquer item abaixo falhar, o restore deve ser considerado reprovado:

1. arquivo de backup nao existe
2. script de restore falha
3. banco restaurado sobe mas o app nao loga
4. healthcheck nao responde `status=ok`

---

## Parte B. Drill de rollback de aplicacao

### Precondicoes

1. existe uma versao anterior identificavel do app
2. existe responsavel tecnico pelo rollback
3. existe ambiente onde o rollback pode ser simulado sem destruir o box real

### Passo 1. Definir o ponto de retorno

Checklist:

1. registrar hash ou release anterior
2. registrar quem aprova rollback
3. registrar quem executa rollback

### Passo 2. Simular rollback

Checklist:

1. voltar o deploy para a versao anterior
2. abrir `/api/v1/health/`
3. testar login
4. testar `/dashboard/`
5. testar `/operacao/recepcao/`
6. testar `/operacao/manager/`

Evidencia esperada:

1. release anterior aplicada
2. horario de rollback
3. tempo total de retorno

### Failure checks do rollback

Se qualquer item abaixo falhar, o rollback deve ser considerado reprovado:

1. time nao consegue apontar a versao anterior correta
2. rollback sobe mas login quebra
3. rollback sobe mas rotas centrais quebram
4. ninguem sabe quem aprova ou executa a volta

---

---

## Parte C. Drill de restore por tenant

Esta parte responde a pergunta que a venda faz: *"se der problema no MEU box, voces recuperam
o MEU box?"*. Ela nao existia enquanto havia um box so, porque restaurar o cluster e restaurar
o box eram a mesma coisa. Com dois ou mais clientes pagantes, deixam de ser.

### Precondicoes

1. cluster PostgreSQL com **pelo menos 2 tenants provisionados** (o drill precisa provar que o
   box vizinho nao se mexe)
2. `pg_dump`, `pg_restore`, `psql` e `createdb` disponiveis
3. banco isolado de restore disponivel (`octobox_restore_test`)
4. alguem responsavel por registrar horarios

### Passo 1. Dump de um tenant

```bash
PGPASSWORD='<senha>' bash scripts/linux/backup_tenant_schema.sh \
  --slug <box-slug> --database octobox_control --user octobox_app
```

Evidencia esperada:

1. caminho do arquivo `tenant-<slug>-AAAAmmdd-HHmmss.dump`
2. tamanho maior que zero

### Passo 2. Restore isolado (nao destrutivo)

```bash
PGPASSWORD='<senha>' bash scripts/linux/restore_tenant_schema.sh \
  --slug <box-slug> --user octobox_app \
  --backup-file backups/tenants/tenant-<slug>-AAAAmmdd-HHmmss.dump
```

Depois, com `DATABASE_URL` apontando para o banco isolado:

```bash
python manage.py smoke_test_tenant --slug <box-slug>
```

Evidencia esperada:

1. contagem de tabelas restauradas maior que zero
2. `smoke_test_tenant` com exit `0`
3. horario de inicio e fim (este e o numero que vira SLA comercial)

### Passo 3. Ensaio da promocao para o banco vivo

**Nao automatizado de proposito.** Esta sequencia troca dados de um cliente pagante e deve ser
digitada com atencao, uma linha por vez, em homologacao antes de existir em producao.

A rede de seguranca e o `RENAME`: o schema quebrado nao e apagado, e movido para o lado. Se o
restore vier torto, a volta e instantanea.

```sql
-- 1. tirar o schema quebrado da frente (nao apagar — renomear)
ALTER SCHEMA box_<slug> RENAME TO box_<slug>_broken_<AAAAmmdd>;
```

```bash
# 2. restaurar o schema bom, vindo do dump, direto no banco vivo
PGPASSWORD='<senha>' pg_restore --host 127.0.0.1 --port 5432 \
  --username octobox_app --dbname octobox_control \
  --schema box_<slug> --no-owner \
  backups/tenants/tenant-<slug>-AAAAmmdd-HHmmss.dump

# 3. provar o box recuperado
python manage.py smoke_test_tenant --slug <box-slug>
```

```sql
-- 4. so depois do smoke verde, e so depois de o dono confirmar os dados:
DROP SCHEMA box_<slug>_broken_<AAAAmmdd> CASCADE;
```

Se algo falhar entre 2 e 3, a volta e desfazer o rename:

```sql
DROP SCHEMA box_<slug> CASCADE;                              -- descarta a tentativa
ALTER SCHEMA box_<slug>_broken_<AAAAmmdd> RENAME TO box_<slug>;  -- devolve o estado anterior
```

### Passo 4. Provar que o vizinho nao se mexeu

O ponto inteiro da Parte C. Antes e depois da promocao, no **outro** box:

```bash
python manage.py smoke_test_tenant --slug <outro-box-slug>
```

E conferir uma contagem estavel (alunos, pagamentos) nesse outro schema.

### Failure checks da Parte C

Se qualquer item abaixo falhar, o restore por tenant esta reprovado:

1. dump gerado com tamanho zero, ou de schema inexistente
2. `smoke_test_tenant` falha no banco isolado
3. a promocao exigiu improviso fora do roteiro
4. o box vizinho mudou de estado durante a operacao
5. ninguem cronometrou o tempo total de recuperacao

---

## Tabela de registro do ensaio

| Item | Resultado | Evidencia |
| --- | --- | --- |
| Backup do cluster gerado | `aprovado 2026-04-14` | `backups/octobox-20260414-013716.dump` |
| Restore do cluster executado | `aprovado 2026-04-14` | banco `octobox_restore_test`; `auth_user = 3`, `auth_group = 6` |
| Healthcheck apos restore | `aprovado 2026-04-14` | `/api/v1/health/` = `200` |
| Login apos restore | `aprovado 2026-04-14` | `owner_homolog` em `/operacao/owner/` = `200` |
| Rollback simulado | `aprovado 2026-04-13` | `dc5ef8a` -> `9e0e2bb` -> retorno, em worktree limpo |
| Healthcheck apos rollback | `aprovado 2026-04-13` | `/api/v1/health/` = `200` |
| Rotas centrais apos rollback | `aprovado 2026-04-13` | dashboard, owner, manager, recepcao, alunos, grade — todas `200` |
| **Dump por tenant** | `pendente` | caminho do arquivo |
| **Restore isolado por tenant** | `pendente` | horarios e contagem de tabelas |
| **`smoke_test_tenant` pos-restore** | `pendente` | exit code |
| **Promocao ensaiada** | `pendente` | horario e tempo total de recuperacao |
| **Box vizinho intacto** | `pendente` | smoke do outro slug, antes e depois |

---

## Criterio de aprovado

O drill so fica aprovado quando:

1. backup foi gerado
2. restore foi executado
3. healthcheck e login voltaram apos restore
4. rollback foi simulado
5. healthcheck e rotas centrais voltaram apos rollback
6. um tenant foi restaurado sozinho, com `smoke_test_tenant` verde
7. o box vizinho ficou provadamente intacto durante a operacao
8. o tempo total de recuperacao de um box foi medido e registrado

---

## Formula curta

Se o time nao consegue restaurar e voltar em ambiente controlado, ainda nao sabe proteger o primeiro box em producao.

E se consegue recuperar o cluster mas nao um box sozinho, ainda nao pode prometer recuperacao para o segundo cliente.
