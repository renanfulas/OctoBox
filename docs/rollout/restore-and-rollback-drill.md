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
- nao executar restore destrutivo no ambiente ativo do primeiro box.
-->

# Drill de restore e rollback da Fase 1

## Objetivo

Provar que o time consegue:

1. gerar backup
2. restaurar backup
3. voltar a aplicacao para uma versao anterior
4. fazer isso com ordem e sem improviso

Em linguagem simples:

1. nao basta ter extintor pendurado na parede
2. precisamos saber puxar o pino sem tremer a mao

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

## Tabela de registro do ensaio

Preencher ao final:

| Item | Resultado | Evidencia |
| --- | --- | --- |
| Backup gerado | `pendente` | caminho do arquivo |
| Restore executado | `pendente` | horario e banco de teste |
| Healthcheck apos restore | `pendente` | status da rota |
| Login apos restore | `pendente` | usuario testado |
| Rollback simulado | `pendente` | release anterior |
| Healthcheck apos rollback | `pendente` | status da rota |
| Rotas centrais apos rollback | `pendente` | lista das rotas testadas |

---

## Criterio de aprovado

O drill so fica aprovado quando:

1. backup foi gerado
2. restore foi executado
3. healthcheck e login voltaram apos restore
4. rollback foi simulado
5. healthcheck e rotas centrais voltaram apos rollback

---

## Formula curta

Se o time nao consegue restaurar e voltar em ambiente controlado, ainda nao sabe proteger o primeiro box em producao.
