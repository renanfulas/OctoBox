# Checklist de Provisionamento da Homologação PostgreSQL

## Objetivo
Preparar a infraestrutura mínima da homologação PostgreSQL para executar o restore real da Fase 1 com segurança, evidência e baixa improvisação.

Em linguagem simples: este documento é a lista de "o que precisa existir na casa" antes de abrir a torneira e testar a caixa d'água de verdade.

## Escopo
Este checklist cobre:
- host da homologação
- PostgreSQL real
- Redis de homologação
- variáveis de ambiente
- publicação da app
- usuários de teste
- pasta de evidências

Este checklist não substitui:
- [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md)
- [postgres-homolog-restore-checklist-template.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-checklist-template.md)
- [first-box-production-execution-checklist.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/first-box-production-execution-checklist.md)

Ferramenta de apoio:
- [provision_postgres_homolog_local.ps1](C:/Users/renan/OneDrive/Documents/OctoBOX/scripts/provision_postgres_homolog_local.ps1)

## Status
Use:
- `[ ]` nao iniciado
- `[~]` em andamento
- `[x]` validado
- `[!]` bloqueador

## 1. Host da Homologação
- [ ] Existe um host de homologação definido
- [ ] O host de homologação tem dono técnico definido
- [ ] O host permite acesso operacional para deploy e validação
- [ ] O host tem diretório/pasta definida para evidências do drill

Campos:
- Host/URL:
- Responsável técnico:
- Pasta de evidências:

## 2. PostgreSQL
- [ ] Existe uma instância PostgreSQL da homologação
- [ ] A versão do PostgreSQL é 15 ou superior
- [ ] Existe um banco principal da homologação
- [ ] Existe um banco isolado para restore de teste
- [ ] Existem credenciais válidas para acesso administrativo ou operacional

Campos:
- Host PostgreSQL:
- Porta:
- Banco principal:
- Banco de restore:
- Usuário:

## 3. Ferramentas Obrigatórias
- [ ] `psql` está instalado no host operacional
- [ ] `pg_dump` está instalado no host operacional
- [ ] `pg_restore` está instalado no host operacional
- [ ] Os comandos acima respondem sem erro básico de instalação

Comando de verificação:

```powershell
Get-Command psql, pg_dump, pg_restore
```

## 4. Redis de Homologação
- [ ] Existe um Redis de homologação
- [ ] O `REDIS_URL` foi definido
- [ ] A app consegue alcançar o Redis

Campos:
- REDIS_URL:

## 5. Variáveis de Ambiente
- [ ] `DATABASE_URL` definido
- [ ] `REDIS_URL` definido
- [ ] `DJANGO_SECRET_KEY` definido
- [ ] `PHONE_BLIND_INDEX_KEY` definido
- [ ] `DJANGO_ALLOWED_HOSTS` definido
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` definido
- [ ] `BOX_RUNTIME_SLUG` definido
- [ ] `OPERATIONS_MANAGER_WORKSPACE_ENABLED` revisado conforme o piloto

Comando de verificação:

```powershell
Get-ChildItem Env: | Where-Object {
  $_.Name -match 'DATABASE_URL|REDIS_URL|DJANGO_SECRET_KEY|PHONE_BLIND_INDEX_KEY|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|BOX_RUNTIME_SLUG|OPERATIONS_MANAGER_WORKSPACE_ENABLED'
}
```

## 6. Publicação da App
- [ ] A app de homologação foi publicada
- [ ] `migrate` foi executado
- [ ] `collectstatic` foi executado
- [ ] `bootstrap_roles` foi executado
- [ ] `/api/v1/health/` responde
- [ ] `/login/` responde
- [ ] `/dashboard/` responde

Campos:
- URL da homologação:
- Data do deploy:

## 7. Usuários de Teste
- [ ] Existe 1 usuário `Owner`
- [ ] Existe 1 usuário `Manager`
- [ ] Existe 1 usuário `Recepcao`
- [ ] As credenciais foram testadas

Campos:
- Owner:
- Manager:
- Recepcao:

## 8. Pasta de Evidências
- [ ] Existe uma pasta definida para guardar dump, logs e checklist
- [ ] O nome da rodada do drill foi definido
- [ ] O checklist preenchível foi copiado para a rodada atual

Campos:
- Nome da rodada:
- Pasta de evidências:

## 9. Gate de Pronto para Restore
So avance para o restore real quando todas as respostas abaixo forem "sim":

- [ ] O PostgreSQL existe e está acessível
- [ ] O banco principal existe
- [ ] O banco isolado de restore existe
- [ ] `psql`, `pg_dump` e `pg_restore` existem
- [ ] A app responde em `/api/v1/health/`
- [ ] Os usuários de teste existem e entram
- [ ] As envs críticas estão carregadas
- [ ] O responsável técnico está definido
- [ ] A pasta de evidências está pronta

## 10. Failure Checks
Nao rode o restore real se qualquer item abaixo for verdadeiro:

- [ ] Ainda nao existe banco isolado para restore
- [ ] Ainda nao existe `DATABASE_URL` real da homologação
- [ ] Ainda nao existe `REDIS_URL` real da homologação
- [ ] A app nao responde em `/api/v1/health/`
- [ ] `pg_dump`, `pg_restore` ou `psql` estao ausentes
- [ ] Ainda nao existem usuários de teste validos
- [ ] Ninguem foi definido como responsável pela execução

## 11. Próximo Passo
Quando este checklist estiver verde:

1. abrir o runbook [postgres-homolog-restore-runbook.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-runbook.md)
2. copiar o template [postgres-homolog-restore-checklist-template.md](C:/Users/renan/OneDrive/Documents/OctoBOX/docs/rollout/postgres-homolog-restore-checklist-template.md)
3. executar backup
4. executar restore
5. rodar smoke funcional
6. anexar evidência à Fase 1
