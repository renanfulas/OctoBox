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
| C. Restore por tenant | `F1 preparado; ensaio F2 nunca executado` | **bloqueia prometer recuperação individual em venda** — ver [phase1-commercial-gate-audit-2026-08-06.md](phase1-commercial-gate-audit-2026-08-06.md) e [inventário F1](../testing/tenant-restore-inventory-2026-10-23.md) |

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

1. dump full e dump tenant do mesmo banco de origem, cada um com manifesto e SHA-256 válidos
2. PostgreSQL/`pg_restore` de major compatível com os dois manifestos; `pg_dump`, `pg_restore`,
   `psql`, `createdb`, Python 3 e `sha256sum` disponíveis
3. capacidade de criar um banco novo `octobox_restore_<run-id>` a partir de `template0`, com role
   que possa instalar as extensões listadas no manifesto
4. laboratório restrito: o dump full pode conter PII de vários boxes; não abrir porta pública,
   não compartilhar credenciais e aplicar política de eliminação ao encerrar
5. no ensaio F2, base de pelo menos dois boxes com canários/fingerprints independentes; não usar
   este requisito como licença para escrever no cluster ativo
6. responsável registra horários e o estado antes/depois

### Passo 1. Dumps pareados e manifestos

O dump por tenant sozinho não contém `public.auth_user`, `StudentIdentity`, control plane ou
membership shared. Gere também um dump full e mantenha os quatro arquivos juntos. O manifesto do
tenant lista FKs, sequences, grants, extensões e migrations sem conteúdo de linhas.

```bash
PGPASSWORD='<senha>' bash scripts/linux/backup_postgres.sh \
  --database octobox_control --user octobox_app --output-dir backups
```

```bash
PGPASSWORD='<senha>' bash scripts/linux/backup_tenant_schema.sh \
  --slug <box-slug> --database octobox_control --user octobox_app
```

Evidencia esperada:

1. caminho e SHA-256 do dump full e manifesto `.manifest.json`
2. caminho e SHA-256 do dump `tenant-<slug>-AAAAmmdd-HHmmss.dump` e manifesto `.manifest.json`
3. mesma origem de banco e major PostgreSQL nos dois manifestos
4. manifesto sem linhas de negócio, segredo, nome, email ou telefone

### Passo 2. Restore isolado (não destrutivo para a origem)

Não crie o banco manualmente e não aplique apenas migrations shared vazias: os vínculos tenant→
`auth_user`/`StudentIdentity` dependem de registros reais. O script verifica hashes, schema,
origem/major dos manifestos, exige nome novo e inexistente com prefixo `octobox_restore_`, restaura
o dump full nesse DB de laboratório e substitui nele apenas o schema-alvo pelo dump tenant. O
`DROP SCHEMA` interno só pode ocorrer no banco recém-criado pelo script; o banco de origem não é
alvo de nenhuma operação.

Desde a repassagem de 24/10/2026, o manifesto recusa FKs entrantes de outros schemas.
O script também executa `tenant_restore_external_dependencies.sql` contra a base full já
restaurada no laboratório, antes do DROP: FKs, views e materialized views externas dependentes
bloqueiam a substituição. Isso preserva constraints/objetos do vizinho que o dump tenant não
conseguiria recriar. Se houver bloqueio, manter o laboratório isolado e reconciliar as
dependências; não remover a barreira para forçar o restore. Objetos customizados continuam
exigindo inventário. Evidências: [repassagem C.O.R.D.A.](../testing/corda-implementation-review-2026-10-24.md).

```bash
PGPASSWORD='<senha>' bash scripts/linux/restore_tenant_schema.sh \
  --slug <box-slug> --user <role-de-laboratorio> \
  --target-database octobox_restore_<run-id> \
  --backup-file backups/tenants/tenant-<slug>-AAAAmmdd-HHmmss.dump \
  --base-backup-file backups/octobox-AAAAmmdd-HHmmss.dump
```

Depois, mantendo `DATABASE_URL` apontando para o banco isolado:

```bash
python manage.py migrate_schemas --schema=box_<slug> --check --noinput
python manage.py smoke_test_tenant --slug <box-slug> --schema-only --restore-semantic
```

Antes do smoke, configure `DATABASE_URL` para o DB isolado. O dump full contém PII; proteja
também os manifests/dumps em repouso e elimine o DB/lab ao fim conforme a política local.

Evidencia esperada:

1. hashes e origem/major dos manifestos aprovados; destino novo criado a partir de `template0`
2. contagem de tabelas restauradas maior que zero e nenhuma FK não validada
3. migrations sem drift e `smoke_test_tenant --slug <slug> --schema-only --restore-semantic`
   com exit `0` no banco isolado
4. vínculos físicos e lógicos de `Box`, `Domain`, `Membership`, `StudentIdentity` e
   `StudentBoxMembership` verificados; efeitos externos/retries reconciliados
5. horário de início/fim (ainda não é SLA comercial até ensaio repetível)

### Passo 3. Promoção para banco ativo — ainda não autorizada

O antigo roteiro `ALTER SCHEMA RENAME` + `pg_restore` direto no banco ativo foi retirado: no
estado atual não reconcilia as referências shared/logical e pode deixar constraints, rotas e
efeitos externos inconsistentes. A promoção exige desenho de V08/F2, snapshot/rollback aprovado,
contenção comprovada dos escritores e ensaio em homologação; não há SQL operacional aprovado
nesta seção. Não executar `DROP`, `RENAME` ou `pg_restore` no cluster vivo como teste.

#### Preflight de contenção para futuro ensaio F2 A/B

Este checklist prepara somente um ensaio controlado em homologação isolada. Não autoriza
promoção em produção. Escolha A (Box restaurado) e B (Box vizinho ativo), registre os dois
schemas, contagens/fingerprints e estado das filas antes de iniciar. Não use tenants reais
como canários descartáveis. Registre a rodada numa cópia protegida do
[template F2](../testing/tenant-restore-drill-template.md); não preencha nem comite valores
operacionais sensíveis nesta árvore.

1. Restrinja o ambiente de homologação ao operador do ensaio e suspenda novas ativações/signup.
   O repositório não tem modo read-only global para o plano shared/public. Mantenha o app online
   apenas para a prova A/B do passo 2; depois dela, corte todo o ingress OctoBOX e pare
   graciosamente as instâncias web antes dos dumps pareados, conforme instruções abaixo. Se não
   for possível restringir e drenar todas as instâncias, adie a captura. Pause/configure também
   os webhooks de provedores da homologação: corte novas entregas durante a janela e registre
   eventos já aceitos. Só reabra a entrega após ingress/web workers; confirme retry ou replay
   documentado do emissor e reconcilie event IDs antes de liberar A. Se o provedor não permitir
   pausa nem replay verificável, não inicie o drill com credenciais/callbacks ativos. Pause e
   confirme parados os comandos de
   control plane `activate_box`, `archive_box`, `unarchive_box`, `attach_superdev_to_boxes`,
   `provision_box`, `reprovision_box`, `bootstrap_roles`, `bootstrap_superdev`,
   `bootstrap_control`, `provision_owner`, `seed_consent_documents` e `populate_test_db`, além de
   `migrate_existing_data_to_pilot`. Os comandos alteram `control.Box`/schema/membership,
   auth/grupos, migration shared ou dados em `public`; `populate_test_db` cria/atualiza dados de
   teste shared antes de entrar no guard tenant, e `migrate_existing_data_to_pilot` copia tabelas
   de `public` para o tenant e pode truncar a origem. Archive/unarchive adquirem o lock exclusivo
   do fence, mas ainda podem mudar o mapeamento compartilhado de B e por isso também ficam
   pausados. Os demais comandos enumerados não são serializados pelo fence tenant durante a
   operação.

   Também não execute manualmente writers do Public Workouts: `add_public_workout_assessment`,
   `backfill_public_workout_load_log_set_role`, `capture_public_workout_metrics`,
   `classify_public_workout_movements`, `complete_public_workout_assessment_profile`,
   `configure_public_workout_experiment`, `drain_public_workout_notices`,
   `drain_public_workout_outbox`, `extract_movements_from_html`, `migrate_legacy_workouts`,
   `reconcile_public_workout_operations`, `run_public_workout_rest_alerts`,
   `seed_legacy_payment_schedule`, `seed_legacy_workout_accounts` e
   `upgrade_periodization_model`. Pause também `ingest_project_knowledge` (escreve no índice shared),
   `purge_stripe_webhook_events` (remove eventos shared processados) e
   `run_due_webhook_retries` (processa a fila legada shared e pode produzir efeitos externos).
   Esses comandos alteram modelos shared, enviam efeitos externos ou ambos.
   `report_public_workout_funnel`, `evaluate_public_workout_growth_gate`,
   `reconcile_stripe_payments`, `audit_blind_index` e os comandos `check_*` de integridade são
   somente leitura segundo suas implementações atuais. Registre operador, início e confirmação de
   parada; se qualquer writer manual estiver ativa, adie a captura. Não execute
   migrations, bootstrap, provisionamento/alteração de usuários (`createsuperuser`,
   `changepassword`), movimentação de dados, `flush`, `loaddata`, shell com escrita ou
   reconciliação shared durante a captura/reconciliação.
   No host de homologação, pause também os schedulers e processos de entrega que podem mudar B,
   produzir efeitos externos ou concorrer com os dumps. Primeiro registre o estado `active` e
   `enabled` de cada unidade instalada; pare timers, sem `disable`/`mask`.
   Antes de executar a lista abaixo, confirme presença com `systemctl cat <unidade>` e omita
   apenas as unidades realmente ausentes:

   ```bash
   systemctl stop octobox-nightly-lead-imports.timer \
     octobox-payment-notifications.timer octobox-signal-mesh-retries.timer \
     octobox-public-workout-metrics.timer octobox-public-workout-notices.timer \
     octobox-public-workout-operations.timer octobox-public-workout-outbox.timer \
     octobox-backup.timer octobox-wod-cleanup.timer octobox-runtime-check.timer
   systemctl list-timers --all
   ```

   Confirme timers sem próxima execução. Não mate serviços `Type=oneshot`: aguarde a conclusão
   natural de qualquer unidade em voo e reconcilie leases/entregas antes dos snapshots. Depois
   confirme o worker contínuo `octobox-public-workout-rest-alerts.service` sem envio/lease ativo e
   então rode `systemctl stop octobox-public-workout-rest-alerts.service`; ele não tem timer.
   O `octobox-runtime-check.timer` não grava no banco, mas pode chamar
   `OCTOBOX_ALERT_WEBHOOK_URL` quando Nginx/Gunicorn estiverem parados; mantenha-o pausado
   durante a janela para evitar alertas de indisponibilidade planejada. O `octobox-wod-cleanup.timer`
   executa exclusões tenant-local de drafts/intents expirados e também deve permanecer pausado.
   `octobox-env-backup.timer` só copia o arquivo de ambiente cifrado para o backup remoto; não
   escreve em dados de Box. Mantenha alterações de variáveis e chaves congeladas durante a janela.
   Além dos timers, pause e drene os workers contínuos acima; não rode os comandos shared
   manualmente durante a janela.
2. Congele A e mantenha o fence até terminar comparação e reconciliação:

   ```bash
   python manage.py set_tenant_write_fence \
     --schema box_<slug_A> --freeze --reason "F2 restore rehearsal"
   ```

   Consulte em `public.control_box` que `write_frozen_at` está preenchido. Confirme que uma
   request de escrita tenant para A recebe 503 com `Retry-After`, enquanto B segue aceitando
   a gravação canário definida no plano de teste. O freeze espera os handlers protegidos que
   já entraram; não encerra SSE previamente aberto nem suspende efeitos já aceitos por
   provedores.

   Registre o resultado do canário de B no baseline. Em seguida, feche ingress para todos os
   hosts/replicas da homologação. No host dedicado descrito pelas unidades do repositório,
   interrompa primeiro Nginx e depois Gunicorn; em host compartilhado, faça o corte equivalente
   no balanceador apenas para os vhosts OctoBox, sem parar serviços de terceiros:

   ```bash
   sudo systemctl stop nginx.service
   sudo systemctl stop octobox-gunicorn.service
   systemctl show -p ActiveState nginx.service octobox-gunicorn.service
   pgrep -af '[g]unicorn.*config.wsgi' || echo 'nenhum processo Gunicorn OctoBox'
   ```

   As units no repositório usam `TimeoutStopSec=30` e `KillMode=mixed`; confirme no journal que
   Gunicorn encerrou normalmente, sem timeout/kill, e que todas as instâncias foram drenadas.
   Usando a role de aplicação, confirme que não restam sessões do app no PostgreSQL (sem
   selecionar ou imprimir texto de query):

   ```sql
   SELECT count(*)
   FROM pg_stat_activity
   WHERE datname = current_database()
     AND usename = '<role_da_aplicacao>'
     AND pid <> pg_backend_pid();
   ```

   Exija resultado zero antes dos dumps e mantenha o ingress/app parados até o Passo 5.
3. Confira que comandos direcionados a A usam o fence e recusam mutação quando congelado:
   `seed_onboarding_scenarios --box-slug <slug_A>`, `cleanse_legacy_pii --schema box_<slug_A>`,
   `backfill_student_cpf_lookup_index --schema box_<slug_A> --apply`,
   `rotate_pii_encryption --schema box_<slug_A> ... --apply`, `seed_dashboard --schema box_<slug_A>`,
   `import_students_csv ... --schema box_<slug_A>`, `seed_movement_library --schema box_<slug_A>`
   e `backfill_staff_membership --box <slug_A>`. O guard protege a operação em A.
   `seed_pilot_workspace`, `seed_south_sp_box` e `reset_demo_workspace` dependem do schema atual
   da conexão e também são fenced; não os invoque sem contexto tenant explícito. `--flush` do
   seed de onboarding não remove links existentes. `cron_whatsapp_log_sweep --schema box_<slug_A>`
   é dry-run por padrão e obtém o fence com `--apply`; não o execute com `--apply` na janela.
   Não há scheduler configurado para esse comando.

   Pause também sweeps tenant-aware enquanto captura os dumps pareados: mesmo pulando A congelado,
   podem gravar em B ou alterar filas compartilhadas. Incluem `compute_lead_features`,
   `contribute_network_channel_aggregates`, `evaluate_finance_followups`,
   `run_due_nightly_lead_import_jobs`, `run_due_payment_notifications`,
   `run_due_async_job_retries`, `run_signal_mesh_retry_sweep`, `cleanup_wod_apply_intents` e
   `cleanup_wod_input_drafts`. O preflight do host deve confirmar timers/serviços instalados e
   interromper invocações manuais desses comandos durante a janela.

   Não executar comandos de manutenção não classificados; `migrate`, `flush`, `loaddata`, shell
   com escrita e SQL manual ficam proibidos.
4. Não rode `run_pre_vps_operational_smoke --schema ...` durante a janela: o smoke atual já não chama
   retry sweeps e está isolado a um Box, mas o snapshot do dashboard sincroniza status de sessões
   dentro do schema alvo. Pause/drain jobs externos ou não duráveis que possam já estar em voo para A;
   anote retries, mensagens aceitas por provedor e itens
   sem identidade de Box. Eventos Stripe não associáveis, fila WhatsApp legada em `public`, SSE já
   aberto e worker/subprocesso sem schema explícito são bloqueadores, não itens que o freeze possa
   presumir contidos. Para cada provedor de webhook, registre event IDs aceitos antes da pausa e
   confirme no próprio emissor retry/replay após reabrir o endpoint; não presuma que 503 ou corte
   de conexão será repetido. Evento sem confirmação de entrega/replay permanece pendência e impede
   descongelar A.
5. Só então capture snapshots pareados e confira hashes/manifests. Se Nginx/Gunicorn estavam ativos
   antes da janela, reinicie-os agora; mantenha timers pausados e A congelado. Execute o restore
   isolado do Passo 2 enquanto B pode voltar a aceitar tráfego/canário na origem. Compare o B do
   clone com o fingerprint baseline capturado no dump — novas escritas na origem após o snapshot
   não fazem parte desse baseline. Após smoke, compare A com seu baseline e B com fingerprint/
   contagens anteriores. Reconcilie referências compartilhadas e efeitos externos antes de
   descongelar A. Se qualquer fila, referência ou writer estiver sem atribuição/estado final,
   mantenha o ensaio reprovado.
6. Retome somente as unidades que estavam ativas antes da janela, depois de registrar os resultados
   e confirmar que a reconciliação terminou. Inicie primeiro os timers/serviços globais; a retomada
   operacional de A ocorre por ação separada e registrada:

   ```bash
   python manage.py set_tenant_write_fence --schema box_<slug_A> --unfreeze
   ```

   Um freeze/unfreeze bem-sucedido não aprova promoção; o aceite ainda depende do gate abaixo.

### Passo 4. Provar que o vizinho não se mexeu no laboratório

No laboratório, medir o tenant B após restaurar o full e novamente após substituir A. A fonte
ativa não é alterada por este ensaio.

```bash
python manage.py smoke_test_tenant --slug <outro-box-slug>
```

E conferir uma contagem estavel (alunos, pagamentos) nesse outro schema.

### Failure checks da Parte C

Se qualquer item abaixo falhar, o restore por tenant esta reprovado:

1. manifesto/hash ausente, mismatch de schema/origem/major ou archive ilegível
2. target já existe, não usa prefixo `octobox_restore_` ou restore full/tenant falha
3. FK não validada ou `smoke_test_tenant --schema-only --restore-semantic` falha no banco isolado
4. vínculos lógicos, filas de jobs/entrega ou efeito externo não reconciliados
5. fingerprint/contagem de B mudou no laboratório
6. ninguem cronometrou tempo e registrou ambiente/limites

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
| **Dump por tenant** | `aprovado sintético 2026-10-23` | manifest/hash full + tenant em `docs/testing/tenant-restore-drill-2026-10-23.md` |
| **Restore isolado por tenant** | `aprovado sintético 2026-10-23` | destino descartável; 57 tabelas, zero FKs inválidas; 6 s no restore script |
| **`smoke_test_tenant --restore-semantic` pós-restore** | `aprovado sintético 2026-10-23` | A e B 6/6; teste PostgreSQL 1/1; defeitos de referência reprovados no clone |
| **Promocao ensaiada** | `pendente` | horario e tempo total de recuperacao |
| **Box vizinho intacto** | `aprovado sintético 2026-10-23` | fingerprint B `7e6222f0befb4808a48f83fedf4ea730` antes/depois; B não recebeu writes durante o restore |

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
