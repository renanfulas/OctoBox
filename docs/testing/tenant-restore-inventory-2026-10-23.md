# Inventário de dependências para restore de um tenant — 2026-10-23

## Escopo e qualidade da evidência

Este inventário fecha o pacote F1 do subplano C.O.R.D.A. Foi feito por leitura de código,
migrations, runbooks e consulta somente de leitura aos catálogos PostgreSQL locais. Nenhum dump,
restore, troca de schema ou escrita foi feito no banco de origem; o roundtrip sintético posterior
ocorreu somente em containers PostgreSQL descartáveis.

O banco consultado é o PostgreSQL local configurado como `octobox_control`, em loopback,
versão 15.19. Ele contém um schema tenant de desenvolvimento (`box_test`) e um `control.Box`
ativo. **Não representa topologia nem volume de produção** e não permite provar isolamento do
box vizinho. O commit base do checkout é `a2ab398f`; os arquivos locais de outros trabalhos
foram preservados.

## Topologia e ownership

- `config/settings/base.py` declara `SHARED_APPS` em `public` e `TENANT_APPS` em cada schema
  `box_<slug>`. As implementações de `students`, `finance`, `operations`, `communications` e
  outros domínios mantêm diversos modelos com `app_label='boxcore'`; migrations e nomes físicos
  `boxcore_*` continuam pertencendo ao estado histórico de `boxcore`.
- `public` guarda `control.Box`, `Domain`, `Membership`, `BoxProvisioningEvent`, usuários/grupos
  Django e `StudentIdentity`, `StudentBoxMembership`, convites e transferências. `Box.schema_name`
  é o mapa do control plane para o tenant; o fluxo de provisionamento é explícito e
  `auto_create_schema/auto_drop_schema` estão desligados.
- `StudentIdentity` liga-se a `control.Box` dentro de `public`. Em cada schema, `boxcore_student`
  e `student_app_studentprofilechangerequest` têm FK real para `public.student_identity_studentidentity`.
  `StudentBoxMembership` vive em `public` e aponta para `Box`/`StudentIdentity`, mas seus campos
  `box_root_slug` e `student_id` são referências lógicas sem FK para o schema do box.
- `Domain`/`Membership` e `StudentBoxMembership` não podem ser reconstruídos a partir do dump do
  tenant. São dependências compartilhadas que precisam existir no snapshot de laboratório.

### Domínio e roteamento efetivo

`control.Domain` é um modelo de `django-tenants`, mas o próprio contrato em `control/models.py`
classifica o domínio como Fase 2; a aplicação atual resolve o schema staff por
`TenantBySessionMiddleware` + `Membership` (`control/middleware.py`). Portanto, um Box ativo sem
linha em `control_domain` é válido e o smoke de restore não deve exigir domínio cadastrado nem
atribuir a ele o roteamento atual. No ensaio operacional, Domain continua sendo metadado shared a
comparar entre o snapshot anterior e o restaurado; essa igualdade precisa de baseline/canário e não
pode ser provada pelo smoke isolado, que não conhece o estado anterior.

### Disposição das referências fracas examinadas

| Referência | Contrato no código | Gate atual / limite |
|---|---|---|
| `StudentIdentity.student_id` | Student do Box identificado por `box_id` ou `box_root_slug`; o helper abre o schema explicitamente | Smoke valida existência/alinhamento quando preenchida e Box por FK ou alias (`schema_name`/`slug`) |
| `StudentBoxMembership.student_id` | vínculo multi-box do identity com Student daquele Box | Smoke valida Student, identity, Box/root e retorno fraco da identidade |
| `StudentProfileChangeRequest.student/identity` | ambos devem apontar ao mesmo agregado Student/identity do Box | Smoke valida os dois lados e recusa FK real para identity de outro Box |
| Consent, invitation, invite link e push subscription | cada linha shared tem FK opcional `box` e root legado; FK é a âncora preferida | Smoke compara FK/root para Box (inclui aliases legados) sem exigir identidade atual no mesmo Box em registros históricos |
| `StudentTransfer.from/to_box(_root_slug)` | duas referências ao Box, representando lados diferentes da transferência | Smoke compara cada FK/slug quando aquele lado menciona o Box; `student_id` permanece histórico e não é exigido como Student atual |
| `StudentJourneyMilestone.identity_id` | ID opcional em evento analítico tenant-local, sem FK; o writer repete o ID em `subject_key` com `subject_kind=identity` e, para coorte identity, em `cohort_key` | Smoke valida essa coerência interna, sem exigir que a identidade ainda exista nem conferir membership atual; o ID pode ser histórico após exclusão/transferência |
| `StripePaymentRef.box_schema/payment_id` | índice shared usado por webhook `charge.*` para entrar no tenant e localizar Payment | Smoke exige schema canônico para referências do Box, Payment existente, e confronta Payment intent quando o Payment mantém esse valor; referências sem PI no tenant só permitem provar o alvo numérico existe |
| `PublicWorkoutAccount/Assessment.student_identity_id` | referência informativa; os modelos declaram que não é ressincronizada nem autoridade | Fora do gate de restore de tenant; não deve ser usada para resolver identidade ou acesso |

Esta classificação é dirigida às referências encontradas no código e não substitui nova varredura de
modelos/catálogo em cada topologia. O gate não tenta resolver IDs históricos de convites,
transferências ou milestones; qualquer requisito de existência precisa de contrato próprio antes de
ser imposto no restore. A expansão local de 24/10/2026 revisou outros campos escalares de ID nos
apps tenant/shared e registrou o único novo vínculo corrente ao Box identificado neste recorte em
`WorkoutApprovalPolicySetting.box_id`; os demais têm semântica local, polimórfica, histórica,
opcional ou de correlação externa e não entram no gate sem contrato adicional.

## Resultado do catálogo PostgreSQL local

| Evidência | Resultado observado |
|---|---:|
| PostgreSQL | 15.19 |
| schemas tenant no banco | 1 (`box_test`, desenvolvimento) |
| relações em `public` / tenant | 72 / 52 |
| sequences em `public` / tenant | 69 / 52 |
| sequences com dependência de ownership | 69 / 52 |
| FKs totais / entre schemas | 159 / 31 |
| FKs entre schemas, direção | 31 tenant → `public`; zero public → tenant; zero tenant → tenant |
| FKs tenant → `public.auth_user` | 29 |
| FKs tenant → `public.student_identity_studentidentity` | 2 |
| extensões instaladas | apenas `plpgsql` 1.0 (`pg_catalog`) |
| famílias de privilégios de tabela/sequência observadas | SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES e TRIGGER |

As 31 FKs externas usam `NO ACTION` no catálogo; remoções ORM com `SET_NULL`/`CASCADE` são
comportamento do coletor Django e não alteram o tipo de ação gravado na constraint PostgreSQL.
Todas as 31 constraints consultadas estavam validadas. O catálogo local não mostrou referências
de `public` para tabelas tenant, mas isso deve ser refeito em cada ambiente e tenant na hora do
ensaio.

`boxcore_student.identity_id` pode apontar para `StudentIdentity` compartilhada; copiar somente
o schema do box não inclui a identidade. A restauração precisa de uma base `public` coerente.
Mesmo quando a FK é satisfeita, os campos fracos (`StudentBoxMembership.student_id` e
`box_root_slug`) não têm integridade física: o pós-restore deve comparar identidade, box,
membership e student manualmente/comando semântico.

## Migrations, grants e extensão

O schema consultado registra a tabela `django_migrations` e app labels compartilhados e
históricos: `boxcore`, `operations`, `student_app`, `student_identity`, `control`, entre outros.
Seu ledger de desenvolvimento está atrasado em relação ao código atual (`student_app` até
0025); o teste E2 já havia aplicado `student_app.0028` em banco descartável. Não usar o ledger
local como afirmação sobre outro schema. O verificador `makemigrations --check` contra o banco
default continua limitado pelo histórico pré-existente inconsistente `public_workouts.0040`
aplicado antes de `.0039`.

O dump de tenant registra em seu manifesto versões de migrations por app, FKs externas,
contagens de tabelas/views/sequences, ownership de sequences, extensão e ACLs de relations e do
schema. O dump full também recebe manifesto de tipo, banco de origem, major PostgreSQL,
versão do cliente, tamanho e SHA-256. Nenhuma linha de negócio, segredo, nome/email/telefone de
aluno é copiada para o manifesto.

## Arquivos fora do PostgreSQL e efeitos externos

- Os modelos de domínio atuais não declaram `FileField`/`ImageField`. CSVs de importação são
  temporários (`/tmp`/arquivo temporário do request); `AsyncJob` pode guardar caminho/status no
  banco, mas o arquivo pode sumir em restart/restore. O ensaio deve pausar e drenar/invalidar
  imports e retries antes de comparar dados.
- Exports CSV são arquivos no filesystem em `exports/<box-slug>/`, gerados por `reporting/tasks.py`
  e referenciados por `AsyncJob.result.file_url`. O `MEDIA_ROOT` não estava configurado; vazio
  fazia o caminho ficar relativo ao `WorkingDirectory`, dentro da release imutável do deploy.
  Corrigido neste pacote: `OCTOBOX_MEDIA_ROOT` agora controla `MEDIA_ROOT`; o deploy aponta para
  `/srv/octobox/shared/media`, persistente entre releases. Esse diretório não é incluído no
  dump PostgreSQL. Export é artefato regenerável; após restore, links sem arquivo devem expirar/
  ser regenerados. Retenção e backup de exports continuam sem política operacional comprovada.
- Uploads/importações temporárias, exports e `MEDIA_ROOT` são efeitos fora do banco. O dump
  isolado não os transporta.
- `AsyncJob`, outbox de notificação de pagamento e `WhatsAppMessageLog` ficam em tabelas tenant
  (muitas sob `boxcore_*`). Seus estados podem refletir tentativas já executadas por provedores
  externos. Email/WhatsApp já aceitos ou entregues não são revertidos restaurando SQL; pause
  schedulers/retries/callbacks durante a comparação e reconcilie idempotência/estado antes de
  reativar.
- `octobox.env` é copiado para R2 cifrado com `age`; a chave privada fica fora da VPS. O código
  está presente, mas disponibilidade atual do objeto remoto, chave privada e teste de decrypt
  operacional não foram confirmados nesta etapa. Segredos e chaves necessários para descriptografar
  dados são pré-requisito de qualquer recuperação.

## Procedimento de laboratório aprovado para F2

1. Gerar o dump tenant e manifesto com `backup_tenant_schema.sh`; gerar/selecionar também dump
   full e manifesto da mesma base. Os hashes detectam corrupção/troca de arquivo. Diferença de
   instante entre os dois snapshots pode causar FK órfã; o restore valida FKs e deve falhar
   fechado se a base compartilhada não contiver as referências.
2. Usar uma role de restore com `CREATEDB` e permissões para carregar as extensões listadas.
   Usar o arquivo full em ambiente de laboratório com acesso restrito: contém dados de vários
   boxes e PII. A etapa atual não sanitiza dumps full. Isolar rede/credenciais, controlar acesso
   e eliminar o banco de laboratório conforme política aprovada após o ensaio.
3. `restore_tenant_schema.sh` exige nome novo `octobox_restore_<run-id>`, recusa banco já
   existente, verifica os dois manifestos, hashes, schema, origem e major PostgreSQL; restaura
   o full no laboratório recém-criado, substitui **somente nesse banco isolado** o schema-alvo
   pelo dump tenant e confere tabelas/FKs não validadas.
4. Apontar `DATABASE_URL` de um processo de smoke dedicado para o banco isolado e executar
   `migrate_schemas --schema=<tenant> --check` e
   `smoke_test_tenant --slug <slug> --schema-only --restore-semantic`. Comparar também
   Domain, canários e hash/contagem do box B.

Esse procedimento de laboratório não autoriza promoção. Restaurar o schema em produção sem
reconciliar as referências shared e efeitos externos permanece bloqueado por F2/V08.

## Preparação do cenário F2 em CI — 2026-10-23

O job `postgres-dump-restore` em `.github/workflows/backup-integrity-check.yml` foi ampliado
para montar dois schemas sintéticos (`box_alpha` e `box_bravo`) com IDs de linha coincidentes,
FKs tenant→shared para identidade e dado compartilhado, e membership lógico/shared por schema.
O job captura um fingerprint determinístico do canário de B mais seus vínculos antes do dump,
restaura A no banco isolado e exige que os dados e vínculos de A estejam legíveis e que o
fingerprint/membership de B permaneçam idênticos.

Esse teste exercita o isolamento do procedimento de restore com dados descartáveis. Ele não
simula tráfego simultâneo, writers, jobs, cron, callbacks/webhooks, pagamentos ou mensagens já
aceitas por provedores; tampouco cobre os modelos/login/roteamento/smokes reais do OctoBOX. O
Workflow ainda precisa ser executado no Linux CI para contar como evidência. Para promoção, é
necessário outro ensaio em homologação com writers de A contidos e B exercitado, conforme F2;
nenhuma automação de promoção foi acrescentada.

### Roundtrip local com os scripts reais

O mesmo cenário sintético foi executado em Docker com PostgreSQL 15. Dumps full e tenant,
manifestos, verificação de hashes/origem/major e restore isolado passaram. O restore manteve
uma tabela tenant, zero FKs inválidas, os vínculos de A com dado compartilhado/identidade/
membership e o fingerprint de B `8c9e277471bc55c62c001b28552aafbe` sem alteração. O ensaio levou
aproximadamente dois segundos entre início e fim do restore reportados pelo script (sem contar
provisionamento Docker/backup).

O primeiro roundtrip falhou ao restaurar as tabelas após apagar o schema A: o dump seletivo
observado não recriou o namespace. Corrigimos `restore_tenant_schema.sh` para criar o schema
vazio dentro do DB descartável antes do `pg_restore` e repetimos o cenário com sucesso. O job
CI atual inclui essa pré-condição implicitamente pelo uso do script real.

### Roundtrip OctoBOX completo com smoke semântico — 2026-10-23

Em PostgreSQL 15.19 descartável, foram aplicadas as migrations atuais shared e os dois schemas
foram criados por `provision_box`. Cada Box recebeu um aluno sintético com `student_id=1`, uma
`StudentIdentity` shared e `StudentBoxMembership`; o ID coincidente exercitou a separação por
schema. Os smokes semânticos pré-backup passaram 6/6 em A e B. Os scripts reais geraram os
archives e manifestos full/tenant, e `restore_tenant_schema.sh` recuperou A num DB novo em 6 s,
com 57 tabelas e zero FKs inválidas. `migrate_schemas --check` e os smokes semânticos pós-restore
passaram 6/6 para A e B. O fingerprint de B foi `7e6222f0befb4808a48f83fedf4ea730` antes e
depois. Testes negativos controlados no clone confirmaram a reprovação de `box_root_slug`
divergente e Student de A ligado à identidade de B; os canários foram restaurados e ambos os
smokes passaram novamente. Manifest hashes, timestamps, limites e limpeza estão no
[relatório F2](tenant-restore-drill-2026-10-23.md). Isso fecha evidência sintética do smoke
semântico e do roundtrip real dos scripts. `tests/test_tenant_restore_semantic_smoke.py` cobre
o caminho íntegro e as duas falhas semânticas em PostgreSQL e foi incluído no workflow de
recuperação/PII; a execução no GitHub ainda está pendente. O ensaio não prova freeze/writers concorrentes, tráfego B
durante restauração, domínio/login, operação de homologação nem promoção.

### Inventário inicial de writers e contenção por tenant

| Caminho atual | Escopo observado | Limite para congelar apenas A mantendo B ativo |
|---|---|---|
| Requests autenticados | `TenantBySessionMiddleware` resolve o box e o novo `TenantWriteFenceMiddleware` mantém advisory shared lock durante execução da view; box congelado recebe 503/Retry-After. | Migration/comando e middleware ainda não foram aplicados em homologação. Requests public→tenant que não setam `request.tenant` no middleware final dependem de guarda no call site. SSE já aberto permanece conectado; streams atuais usam Redis e a view não mantém lock ao longo do stream. |
| SSE de aluno e operações | `student_event_stream` e `manager_event_stream` capturam o schema `box_<slug>` antes da iteração lazy e publicam/assinam canais Redis namespaced por tenant. Sem contexto Box, publisher não publica e stream retorna 403. | O stream é somente leitura e pode continuar conectado durante freeze; o guard protege mutações HTTP e não encerra conexões SSE. Se o stream ganhar escrita, a operação deve adquirir o guard por mutação; fechamento por freeze pode ser tratado separadamente se necessário. |
| `sweep_active_tenants` | Itera todos os boxes ACTIVE e agora guarda cada handler por schema; box congelado é contabilizado como skipped. | Protege somente comandos que usam este helper; loops/schema_context fora dele seguem exigindo inventário. |
| Retry Signal Mesh | `run_signal_mesh_retry_sweep --schema` filtra `AsyncJob`; chamadas shared de WhatsApp/Stripe executam uma vez. O retry WhatsApp agora lê inbox tenant-local por Box e ignora eventos antigos public sem rota; Stripe associado usa o router/fence. | O sweep de webhook continua examinando todos os boxes ativos, com isolamento no guard, e Stripe não associável continua sem Box atribuível. Conferir contagens por Box e reconciliar filas/efeitos externos antes/depois. |
| Webhook Stripe inbound | View em `public` persiste envelope e chama o router; eventos tenant resolvidos por metadata/subscription/`StripePaymentRef` entram no fence e, se A congelado, são adiados sem consumir tentativa. | Novos eventos A podem continuar chegando e acumulando pending; evento não associável e efeitos externos precisam reconciliação. Reconciliador Stripe de drift também pula tenant congelado. |
| Webhook WhatsApp poll | Endpoint público exige HMAC por instância opaca e resolve schema somente no mapa server-side; processor resolve `Student` por blind index exato, consulta `ClassSession` e grava inbox cifrada + `Attendance` no schema roteado, sob write fence. Retry usa a mesma inbox tenant-local. Eventos antigos em `WebhookEvent` continuam em `public`, com chave global e sem rota; o sweep só os conta/ignora. | O receiver novo tem isolamento local; emissão Evolution, secrets por instância e teste sender→receiver ainda não existem. Não inferir tenant de eventos legados por telefone, título, modalidade ou box ativo único. Evento roteado de Box congelado retorna retry/503 sem consumir tentativa. Reconciliar/quarentenar a fila pública antiga antes de qualquer ativação; isso não requer inferência nem migração automática. |
| Webhook Resend | Delivery/event vivem em `public`, mas invitation referencia box. `process_resend_webhook` resolve o box ativo, mantém advisory shared lock, usa `schema_context` para auditoria e retorna 503/Retry-After quando congelado; a transação também reverte atualizações shared. | Sem box ativo resolvível, agora levanta `ResendWebhookTenantUnresolved`: a view retorna 503/Retry-After e não grava delivery/event/auditoria sem atribuição. Resend anuncia retries automáticos e replay manual; evento não resolvido ainda não tem inbox local se retries expirarem. Eventos já aceitos externamente não são revertidos pelo restore. |
| Funil, callback e marcos de identidade | `record_student_onboarding_event`/`record_authenticated_student_return` adquirem fence em tenant corrente e public→tenant; auditoria async guarda dentro da thread. `StudentOAuthCallbackView` mantém fence em authenticate+finalize após resolver Box. Sem box resolvido, para antes de autenticar/criar identidade; auditorias sem tenant não escrevem em `public`. | O code OAuth já foi trocado antes da resolução por provider subject/e-mail; após atribuição do box, o aluno precisa iniciar outra vez. O rate-limit não está particionado por box quando callback é ambíguo; permanece efeito de cache global, não write DB tenant. |
| Payment notifications | Scanner percorre tenants ativos e executa entrega externa dentro do schema; passa por `sweep_active_tenants` e pula A congelado. `run_in_background` também guarda tenant capturado. | O timer é global e segue acordando o scanner; reconciliar entregas `unknown`/aceitas antes de reativar. Outros schedulers externos não foram observados em execução. |
| Import noturno de leads | Scanner por tenant aceita `--schema`; hoje `.delay()` usa shim síncrono (Celery não instalado), mas o próprio código alerta que um worker futuro exige schema explícito no payload. | Filtrar o sweep não interrompe job já iniciado; drenar/pausar job A e impedir redelivery durante o restore. |
| Outbox público Curva | `drain_public_workout_outbox` opera em tabelas compartilhadas públicas e o timer systemd é global. | Não é writer tenant de box no código observado; o timer deve ser inventariado no escopo do ensaio integrado para não misturar produtos/efeitos externos. |
| Timers/serviços systemd que escrevem ou entregam durante F2 | `octobox-nightly-lead-imports.timer`, `octobox-payment-notifications.timer` e `octobox-signal-mesh-retries.timer` percorrem boxes/filas e podem alterar B ou produzir efeitos externos; `octobox-public-workout-{metrics,notices,operations,outbox}.timer` grava em estado compartilhado; `octobox-public-workout-rest-alerts.service` é worker contínuo sem timer. `octobox-backup.timer` pode concorrer com a captura pareada. | O repositório versiona essas unidades, mas isso não prova quais estão instaladas/ativas no host. No drill, registrar estado active/enabled e parar os timers instalados; aguardar one-shots ativos concluírem, reconciliar leases e só então parar o worker contínuo. Retomar apenas timer/worker originalmente ativos. `octobox-runtime-check.timer` é somente leitura. |
| Operações administrativas de ciclo de vida | `control.services.archive_box()` e `unarchive_box()` alteram o nome do schema por DDL e atualizam o Box; agora mantêm `tenant_write_exclusive()` na transação da operação. Os comandos de management são os chamadores encontrados. | O lock drena writers protegidos; freeze ativo recusa a operação. Testes concorrentes PostgreSQL verificaram espera pelo writer e recusa do box congelado, e os testes existentes de archive/unarchive passaram. `delete_user_safely()` agora adquire lock exclusivo para todos os boxes do usuário em ordem estável antes de qualquer escrita tenant/compartilhada; Box congelado aborta antes de iniciar o cleanup. Não foram encontrados chamadores ativos; o helper continua sensível e protegido para eventual uso. Provisionamento/seed opera em Boxes PROVISIONING e não é writer do tenant A ativo, mas cria/atualiza control plane em `public`; suspender novos signups e `provision_box`/`reprovision_box` durante snapshots pareados. |
| Bootstrap de papéis e permissões compartilhadas | `bootstrap_roles` grava Groups/Permissions em `public`, com efeito de ACL compartilhado por todos os tenants; não é uma escrita isolável pelo fence de um Box. | Não executar durante captura/restauração F2; tratar como alteração global de acesso com serialização própria. |
| Backfill/rotação PII por management command | `backfill_student_cpf_lookup_index --apply` e `rotate_pii_encryption --apply` escrevem no tenant explicitado por `--schema`; agora os handlers desses modos obtêm `tenant_write_guard` pela duração da operação. Dry-run/verify permanecem read-only e não adquirem lease. | Freeze bloqueia o início do modo de escrita. Os dois comandos foram exercitados com Box congelado e não alteraram o canário; suítes normais continuam passando. Outras ferramentas de manutenção/migrations com escrita explícita precisam ser serializadas pelo runbook ou adicionadas ao fence antes do drill. |


| Cleanup WOD e sweeps/retries agendados | `cleanup_wod_apply_intents`, `cleanup_wod_input_drafts`, retries de AsyncJob, retries WhatsApp/Stripe, payment notifications e import noturno passam por `sweep_active_tenants` para a perna tenant; o guard permanece no handler. | Box congelado é ignorado e contabilizado; timer pode continuar globalmente. O shim atual de tasks é síncrono. Worker Celery separado não está instalado nem validado, e teria de receber schema explícito e revalidar fence antes de executar. |
| Carga sintética de performance | `access.populate_test_db` cria/usa `box_test`, migra quando cria Box novo e popula Student/financeiro/aulas. A operação de schema/migration/população agora roda dentro do guard depois de resolver Box; schema divergente de `box_test` é recusado. | Box congelado interrompe a carga antes do DDL e das escritas tenant. A regressão em PostgreSQL confirma recusa e contagem de Student inalterada. A criação inicial do Box/owner permanece etapa de provisioning quando o Box ainda não existe. |
| Garbage collector legado de WhatsApp | `cron_whatsapp_log_sweep --schema box_<slug>` consulta um Box ACTIVE; preserva retenção de sete dias, dry-run por padrão e `tenant_write_guard` em `--apply`. Não foi encontrado dispatcher/timer versionado no repo. | `--apply` exclui somente logs elegíveis do schema explicitado e aborta se o Box estiver congelado. A suíte focal passou 22/22 + 8 subtests em PostgreSQL 15.19 descartável; cobre dry-run, corte de retenção e freeze; não executar `--apply` durante snapshots/restores nem instalar scheduler como parte de F2. |
| Smoke pre-VPS sintético | `run_pre_vps_operational_smoke --schema box_<slug>` exige Box ACTIVE, valida o alvo em `public`, obtém `tenant_write_guard` e executa dentro de `schema_context` explícito. Consulta os snapshots do dashboard/Beacon e cria, lê e remove somente um `AsyncJob` marcado, já `COMPLETED` e não elegível a retry. | Os sweeps de jobs e webhooks foram removidos: o smoke não despacha nem consome fila real. Sem scheduler encontrado. Testes diretos do comando passaram 3/3; com `tests/test_tenant_write_fence.py`, a execução passou 26/26 + 8 subtests em PostgreSQL descartável, repetida em container Linux Python 3.12/PostgreSQL 15.19 com dependências do CI e provou que Box congelado aborta antes de criar AsyncJob. A query de dashboard/Beacon e o sucesso do comando não foram integrados nesse caso; durante restore continua sendo mais seguro não executá-lo porque o dashboard sincroniza status de sessões no Box alvo. |
| Limpeza PII legada | `cleanse_legacy_pii --schema box_<slug>` regrava Student, StudentIntake, WhatsAppContact e WhatsAppMessageLog no schema tenant explícito, dentro de `tenant_write_guard` + `schema_context`. | Box inexistente ou congelado aborta antes da regravação; a regressão freeze está em `tests/test_tenant_write_fence.py` (suite focal 22/22 + 8 subtests em PostgreSQL descartável). O comando não oferece dry-run/checkpoint e não deve ser usado como rotação de keyring; manter operação manual por tenant e preferir `rotate_pii_encryption` para troca de chave. |
| Comandos de leitura, escrita compartilhada e onboarding cross-schema | `smoke_test_tenant` consulta metadados/tabelas/ACL; `seed_consent_documents`, `configure_public_workout_experiment`, `backfill_public_workout_load_log_set_role` e `bootstrap_roles` escrevem estado global em `public`. `seed_onboarding_scenarios --box-slug` resolve Box ACTIVE e mantém `tenant_write_guard` + `schema_context` durante gravações em Student tenant e invitations/links shared, com `box` e `box_root_slug=box.schema_name`. | O smoke é read-only. PostgreSQL descartável confirmou bloqueio antes de qualquer convite/link shared, criação dos cenários em ambos os schemas, associação ao Box, reexecução idempotente e preservação de link pré-existente. `--flush` remove apenas invitations `@qa.seed` daquele Box; links são preservados porque o modelo não tem marcador de propriedade do seed. Writers shared globais não participam do fence tenant; o runbook `docs/rollout/restore-and-rollback-drill.md` exige pausa/parada confirmada antes de snapshots F2 A/B. |
| Seeds/importers operacionais tenant | `seed_dashboard --schema`, `import_students_csv ... --schema` e `seed_movement_library --schema` exigem Box ACTIVE e executam sob `tenant_write_guard` + `schema_context`. O dashboard seed deixou de criar superuser global como efeito colateral; esse objeto nem era usado pela massa tenant. `backfill_staff_membership --box` grava `Membership` shared para um Box específico e guarda a mutação pelo schema desse Box; `--dry-run` continua read-only. | A suíte PostgreSQL descartável `tests/test_tenant_write_fence.py` + `boxcore/tests/test_import_students.py` passou 22/22 + 8 subtests: freeze barra os três writers tenant antes de ler CSV/alterar linhas, bloqueia o backfill antes do bulk insert shared, e a importação normal segue atualizando/criando alunos no tenant explícito. Exemplos de CSV foram atualizados para exigir `--schema`. |
| Writers globais de conta e corredor público | `bootstrap_superdev` cria/atualiza User privilegiado em `public`. Comandos `public_workouts` `complete_public_workout_assessment_profile`, `classify_public_workout_movements`, `configure_public_workout_experiment`, `backfill_public_workout_load_log_set_role`, `extract_movements_from_html` e `seed_legacy_workout_accounts` alteram tabelas shared fora do schema tenant. | Pausar essas operações globais em um ensaio A/B que usa snapshots pareados; elas não aceitam Box e não são bloqueadas pelo fence tenant. Não executar `bootstrap_superdev` nem esses comandos durante a janela. |
| Seeds e reset de workspace de demonstração | `seed_south_sp_box`, `seed_pilot_workspace` e `reset_demo_workspace` agora exigem contexto tenant e `tenant_write_guard`; `scripts/seed_demo_week.py` usa o mesmo guard antes de abrir o schema. São ferramentas manuais sem timer/dispatcher de produção encontrado. | Box congelado recusa os quatro caminhos. O reset continua destrutivo se executado em box não congelado; restringir seu uso a demo e não executá-lo durante a janela do drill. Testes atuais verificam recusa sob freeze e os testes de seed/reset normais continuam passando; as commands recusam também execução a partir de `public` ou schema fora do padrão `box_<slug>`. |

### Auditoria complementar de management commands — 2026-10-23

Uma segunda passagem sobre os 69 arquivos de implementação em `management/commands/*.py`
(excluídos os `__init__.py`) encontrados no checkout classificou as superfícies de escrita
relevantes para os snapshots pareados e atualizou o
[preflight F2](../rollout/restore-and-rollback-drill.md):

| Classe | Commands identificados | Tratamento na janela |
|---|---|---|
| Fence do tenant usado pelo drill | `set_tenant_write_fence` | Única escrita de control plane permitida no drill: congelar/liberar somente A após o procedimento e a confirmação do estado dos writers; nunca alterar o fence de B. |
| Control plane/shared sem fence tenant | `activate_box`, `archive_box`, `unarchive_box`, `attach_superdev_to_boxes`, `provision_box`, `reprovision_box`, `bootstrap_roles`, `bootstrap_superdev`, `bootstrap_control`, `provision_owner`, `migrate_existing_data_to_pilot`, `seed_consent_documents`, `populate_test_db` | Pausar; alteram status/schema/membership, auth/permissões, migrations ou dados shared. Archive/unarchive usam lock exclusivo, mas ainda mudam o mapa global. `populate_test_db` escreve Box/User/Group antes do guard que protege o payload tenant. |
| Shared knowledge/retention/retry | `ingest_project_knowledge`, `purge_stripe_webhook_events`, `run_due_webhook_retries` | Pausar; escrevem índice shared, removem eventos processados ou processam a fila global legacy e podem disparar efeitos externos. |
| Índices de e-mail shared | `backfill_student_identity_email_lookup_index --apply`, `backfill_student_app_invitation_email_lookup_index --apply`, `backfill_public_workout_account_email_lookup_index --apply`, `backfill_public_workout_commerce_email_lookup_indexes --apply`, `backfill_pending_signup_email_lookup_index --apply` | Pausar durante os snapshots pareados; gravam HMAC em `public` e não usam fence tenant. `--dry-run`/`--verify` não escrevem, mas não devem disputar a janela de captura sem liberação explícita. |
| Public Workouts shared | `add_public_workout_assessment`, `backfill_public_workout_load_log_set_role`, `capture_public_workout_metrics`, `classify_public_workout_movements`, `complete_public_workout_assessment_profile`, `configure_public_workout_experiment`, `drain_public_workout_notices`, `drain_public_workout_outbox`, `extract_movements_from_html`, `migrate_legacy_workouts`, `reconcile_public_workout_operations`, `run_public_workout_rest_alerts`, `seed_legacy_payment_schedule`, `seed_legacy_workout_accounts`, `upgrade_periodization_model` | Pausar comandos, timers e envio/lease ativos; não usam fence tenant. Relatório de funil e avaliação do gate de crescimento são read-only. |
| Escrita tenant direcionada | `backfill_staff_membership`, `backfill_student_cpf_lookup_index --apply`, `cleanse_legacy_pii`, `cron_whatsapp_log_sweep --apply`, `import_students_csv`, `reset_demo_workspace`, `seed_dashboard`, `seed_movement_library`, `seed_onboarding_scenarios`, `seed_pilot_workspace`, `seed_south_sp_box`, `rotate_pii_encryption --apply` | Os handlers auditados obtêm guard para o schema/alvo; dry-run/verify sem escrita ficam fora do guard. Não iniciar em A congelado; seeds sem opção de schema exigem contexto tenant corrente. |
| Sweeps tenant-aware / effects | `compute_lead_features`, `contribute_network_channel_aggregates`, `evaluate_finance_followups`, `run_due_async_job_retries`, `run_due_nightly_lead_import_jobs`, `run_due_payment_notifications`, `run_signal_mesh_retry_sweep`, `cleanup_wod_apply_intents`, `cleanup_wod_input_drafts` | `sweep_active_tenants` guarda cada perna tenant e pula Box congelado, mas o sweep pode alterar B ou dados shared; parar/drain durante os dumps pareados. |
| Leitura / filesystem | `audit_blind_index`, `check_asyncjob_signal_mesh_migration`, `check_historical_integrity`, `check_static_drift`, `evaluate_public_workout_growth_gate`, `reconcile_stripe_payments`, `report_legacy_whatsapp_queue`, `report_pii_encryption_formats`, `report_public_workout_funnel`, `search_project_knowledge`, `smoke_test_tenant` | Read-only na implementação consultada; `report_legacy_whatsapp_queue --schema public` agrega somente metadados operacionais e não lê payload/erro. O smoke de dashboard `run_pre_vps_operational_smoke` é exceção: sincroniza estado no schema e deve ser pausado. `sync_runtime_assets` escreve arquivos, não o banco; suspender deploy/collectstatic na janela. |
| Placeholder removido do fluxo | `restore_snapshot` | Agora falha fechado porque a implementação anterior nunca restaurou; o único restore documentado é `restore_tenant_schema.sh` em DB novo isolado. |

Além dos commands nomeados, não executar `migrate`, `flush`, `loaddata`, `createsuperuser`,
`changepassword`, shell com escrita ou SQL manual. A auditoria cobre os arquivos versionados
nesta árvore, não scripts/operadores fora do checkout, hooks do provedor, requisições já em voo
ou comandos adicionados posteriormente; qualquer elemento não classificado continua proibido.
`set_tenant_write_fence` é a única escrita de control plane prevista durante o drill, estritamente
para congelar/liberar A conforme os passos registrados; não se altera o fence de B.

Como não há modo read-only global no Django, o procedimento operacional agora testa o fence com
A/B acessíveis somente ao operador e, após os canários, fecha ingress em todas as réplicas antes
dos dumps. A unit versionada `octobox-gunicorn.service` fixa `TimeoutStopSec=30`/`KillMode=mixed`;
o runbook exige shutdown limpo, ausência de processos Gunicorn e zero sessão restante da role do
app antes de capturar. Após validar archives/manifests, o app pode voltar com A ainda congelado;
o restore continua isolado, e o fingerprint de B no clone é comparado ao baseline do dump. Isso
é um procedimento documentado, não prova de que o host de homologação tem uma única réplica ou de
que a barreira foi operada. Callbacks de provedores também precisam ser pausados e seus event IDs
reconciliados por retry/replay confirmado no emissor; não há prova uniforme de retry após 503/corte
para todas as integrações.

**Conclusão de contenção:** existe agora um fence local tenant-scoped parcial para middleware HTTP, sweeps
comuns, jobs capturados, reconciliação financeira, eventos Stripe associados, Resend associado, callback
OAuth com Box resolvido, escrita dos marcos/auditorias de funil e o receiver novo de WhatsApp poll. Os testes
locais provam bloqueio de A, isolamento da rota de middleware, skip de sweep congelado, espera do freeze
por writer protegido em voo e persistência de um `Student` em B enquanto A está congelado. Resend e
OAuth sem Box resolvido param sem gravar estado compartilhado/tenant atribuível; o OAuth já trocou o code e
requer novo início. A transição grava flag no control plane e usa advisory lock para aguardar work units
protegidas em voo. Isso não é um freeze/read-only completo: eventos Stripe não atribuíveis, eventos WhatsApp
da inbox pública antiga sem rota, jobs disparados por mecanismos não inventariados e SSE já aberto continuam
fora da contenção comprovada.
Nenhuma migration/comando foi aplicado em produção/homologação. Houve uma prova sintética de advisory
lock com três subprocessos independentes, mas ainda não houve ensaio de tráfego entre servidores Django,
restore seletivo A/B nem writer externo com A congelado e B em escrita real. O gate de promoção F2
permanece bloqueado.

**Auditoria complementar F2 — operações de ciclo de vida e manutenção (2026-10-23):**
`archive_box`/`unarchive_box` fazem `ALTER SCHEMA ... RENAME` e atualizam `Box` dentro de transação. Os
serviços agora mantêm `tenant_write_exclusive()` durante o rename, aguardam writers protegidos e recusam
Box congelado. `delete_user_safely` adquire todos os locks exclusivos dos boxes do usuário, em ordem
estável, antes de qualquer alteração tenant ou exclusão shared; um box congelado aborta antes do cleanup.
Os modos `--apply` de `backfill_student_cpf_lookup_index` e `rotate_pii_encryption` também adquirem
`tenant_write_guard`; dry-run/verify não escrevem e não adquirem lease. Em PostgreSQL 15.19 descartável,
**16/16** testes fence/archive passaram (12 fence + 4 archive/unarchive), incluindo concorrência e aborto
por freeze; as suítes CPF (**6/6**) e rotação (**4/4**) passaram com chave de teste compatível. Depois de incluir os guards de seeds, a validação consolidada de seis arquivos (`test_tenant_write_fence`, `test_control_services`, `test_student_cpf_lookup_index`, `test_pii_encryption_rotation`, `test_seed_pilot_workspace`, `test_reset_demo_workspace`) passou **58/58** em container descartável, com `TEST_DATABASE_URL` e `DATABASE_URL` explicitamente apontados a `127.0.0.1:55432/test_db`; container removido ao final. A primeira invocação tinha usado a precedência de `TEST_DATABASE_URL` do workspace e não foi considerada evidência; o alvo era `test_octobox_control`, e consulta pelos dois marcadores sintéticos desta tarefa encontrou zero resíduos. Os dois
cleaners WOD e os retry/nightly sweeps usam `sweep_active_tenants`, que mantém a lease durante o handler.
Não foi encontrada dependência Celery nos requirements; o shim de `shared_task` em operations executa
síncrono, enquanto `auditing.tasks.async_log_audit_event` não tem caller no repo. Workers Celery futuros
não estão provados e exigirão schema explícito. Outros comandos de manutenção com escrita explícita devem
ser serializados pelo runbook ou adicionados ao fence antes do drill. Nenhuma operação foi executada em
tenant real.

### Contrato receptor para WhatsApp poll — implementado localmente; emissor pendente

O receiver deve aceitar somente evento autenticado e roteável; o contrato passa a ser:

- Headers obrigatórios: `X-OctoBox-Instance` (ID opaco, sem schema/slug), `X-OctoBox-Timestamp` (Unix seconds), `X-OctoBox-Event-Id` (ID estável do provedor), `X-OctoBox-Key-Id` (versão da chave) e `X-OctoBox-Signature: v1=<hex HMAC-SHA256>`.
- Bytes assinados, em UTF-8: `v1\n<instance-id>\n<key-id>\n<timestamp>\n<event-id>\n<raw-request-body>`. O sender assina os bytes originais antes de qualquer parse/re-serialização. A comparação é constant-time. Timestamp fora de ±300 segundos, body acima de 64 KiB, campos inválidos, evento ID divergente do JSON ou assinatura/chave desconhecida são rejeitados antes de abrir schema tenant.
- O receiver resolve o ID opaco numa allowlist de configuração do ambiente que associa `instance -> schema ativo + key-id -> secret`; secrets residem no secret store do ambiente, nunca no payload ou logs. Aceitar chave atual e anterior durante rotação curta, sem aceitar key IDs fora do mapa. Confirmar em `public` que o Box está cadastrado e ACTIVE e que o schema mapeado é o schema dele. Não aceitar `schema_name` fornecido pelo emissor como autoridade.
- Exigir `event_id` estável do provedor; não usar `message_id`/`vote_id` como fallback sem contrato que garanta equivalência. Dedupe por `(tenant, provider, event_id)` numa inbox tenant-local. Persistir somente campos mínimos para reprocesso, com telefone cifrado e sem payload bruto ou hash não keyed do corpo.
- Sob `tenant_write_guard(schema)` e `schema_context(schema)`, uma única transação cria/obtém inbox, bloqueia a intenção, resolve o aluno por blind index exato, confere classe e grava `Attendance`, marcando a inbox `processed`. Lock/idempotência da inbox e Attendance tornam retry e concorrência seguros. Retry sweep itera tenants e chama o mesmo use case dentro do guard/schema corretos; eventos legados sem identidade tenant são apenas contabilizados/skipped, nunca inferidos por telefone.
- Sem instance/header/assinatura/config/Box válidos: responder 401/400 sem tocar `WebhookEvent`, `Student`, `ClassSession` ou `Attendance`. Box congelado/dependência transitória: 503 + `Retry-After`, sem consumir tentativa. Evento já processado: resposta idempotente 200. Log somente reason code, correlation ID e schema já resolvido; nunca telefone, assinatura, segredo ou body.

O receiver local implementa os headers/canonicalização acima (incluindo instance ID e key ID na mensagem assinada), verifica allowlist/assinatura antes de abrir o tenant, bypassa o middleware de fingerprint global do webhook antigo, usa inbox cifrada por schema e o retry sweep só reprocessa intents dentro do Box. A allowlist `WHATSAPP_POLL_WEBHOOK_INSTANCES_JSON` está vazia por padrão. A documentação Evolution consultada descreve headers customizados por instância e JWT HS256 por `jwt_key`, não HMAC sobre corpo bruto; por isso a conexão direta com o receiver não satisfaz o contrato. O guia `docs/integrations/whatsapp_evolution_setup.md` foi corrigido para exigir bridge autenticada, fixture versionada com voto em texto e emissão HMAC; ainda faltam versão/payload da instância usada pelo OctoBOX, provisionamento dos segredos, prova em dois boxes e reconciliação manual da fila legada public. Relatos oficiais consultados incluem Evolution API 2.3.0 sem resultado legível no evento reportado e Evolution Go 0.7.1 com `pollUpdateMessage` cifrado; não extrapolar esses relatos a outra versão. A suíte de assinatura, middleware, endpoint, retry e persistência passou 24/24 em DB PostgreSQL descartável; `boxcore.0035` foi aplicada em `box_test` e o catálogo confirmou `phone varchar(2048)`. Eventos legados sem tenant são contados e ignorados, nunca roteados por inferência.

### Evidência local do fence — 2026-10-23

`manage.py check` e `py_compile` passaram. A repetição inicial da classe `TransactionTestCase` falhou no
`flush` global por FKs entre schemas e pela remoção do fixture session-scoped `box_test`. O harness foi
ajustado para preservar esse fixture e limpar apenas os eventos/boxes criados pela classe, sem `flush`
global. Em banco PostgreSQL descartável com migrations, a classe passou **8/8**; o caso novo congela A,
confirma que a guarda rejeita sua gravação e persiste um `Student` no schema real `box_test` (B), além do
teste concorrente que prova que freeze aguarda writer protegido em voo. Cinco regressões focais
OAuth/onboarding passaram no mesmo banco; total combinado **13/13**. pytest em Windows ainda emite aviso
de que não consegue gravar `.pytest_cache`, sem afetar o resultado.

**Ensaio adicional de advisory lock entre processos (PostgreSQL 15.19 descartável):** um processo Python
independente segurou `tenant_write_guard(A)` por três segundos; outro processo executou o freeze e só
retornou após **3,09 s**, confirmando a drenagem cross-process. Enquanto o freeze de A aguardava, um
terceiro processo gravou e removeu um canário em B (`box_test`); após A ficar congelado, outra gravação
independente em B também passou. Box A foi descongelado/removido e o container descartável foi encerrado.
Isso prova o advisory lock de sessão entre processos e disponibilidade de B nessa prova sintética; não
é tráfego simultâneo de dois servidores Django, não inclui worker Celery/webhook Evolution nem executa
restore seletivo A enquanto B recebe tráfego real. Essas etapas seguem no gate F2.

Os testes de callback OAuth sem Box e Resend sem Box foram acrescentados. Cinco testes focais
(OAuth sem Box, convite inválido, rate limit, Resend sem Box e Resend associado) passaram em PostgreSQL
descartável. A base `test_octobox_f2_unresolved_verify_20261023` foi removida após a execução. Isso não
prova o replay durável de webhook Resend após a janela de retries nem substitui CI Linux ou ensaio A/B.

## Lacunas reais que permanecem

- A consulta atual viu apenas um schema tenant; não mediu diferenças de migrations/ACL/constraints
  em dois boxes, nem inbound FKs em ambiente maior.
- O full dump pode conter PII; não existe baseline compartilhada sanitizada e coerente aprovada
  para o ensaio automático. A política de retenção/eliminação do DB laboratorial ainda precisa
  ser aplicada no ambiente de teste.
- `pg_dump`, `pg_restore` e restore seletivo foram executados em PostgreSQL 15 descartável com
  dois tenants sintéticos. `psql/pg_dump` não estão instalados no host Windows; GitHub CI/Linux e
  smoke OctoBOX com modelos reais continuam pendentes.
- Não há manifesto/backup de exports nem TTL. O caminho persistente de mídia foi corrigido, mas
  política de expiração, restauração e regeneração ainda precisa de aceite operacional.
- Não foi provada disponibilidade de segredos age, acesso aos backups remotos, conexão multi-box
  real, implementação de freeze tenant-scoped, contenção de jobs em voo/cron/webhooks, RTO/RPO de
  recuperação completa, ou integridade de um box B real. A preservação comprovada de B usa somente
  canários descartáveis.
- `smoke_test_tenant --schema-only --restore-semantic` verifica Box/schema, Owner membership,
  Student→StudentIdentity, StudentBoxMembership→Identity/Student, StudentProfileChangeRequest→
  Student/Identity e o retorno fraco StudentIdentity→Student quando preenchido, incluindo
  referências legadas por `box_root_slug`;
  continua faltando executar esse gate no restore A/B
  com migrations completas e shared snapshot coerente. Domain não participa do roteamento atual;
  o procedimento ainda compara as linhas shared de Domain e fingerprints com baseline pré-restore.

**Decisão F1:** o dump por tenant é um artefato seletivo, não um restore standalone. A base
shared deve vir de dump full coerente e restrito ao laboratório; nunca restaurar `public` nem
rodar `pg_restore`, `DROP SCHEMA` ou `ALTER SCHEMA RENAME` no banco ativo como exploração.
Atualizar esta evidência depois de repetir o catálogo em homologação com pelo menos dois boxes.
Preencher a execução real em cópia do [template do ensaio F2](tenant-restore-drill-template.md).

**F2 — referência compartilhada do pedido de perfil (23/10/2026):** o inventário já identificava
FKs de `student_app_studentprofilechangerequest` para o tenant Student e para `public.StudentIdentity`,
mas o smoke só conferia `Student` e `StudentBoxMembership`. Agora também compara o par do pedido
com o Box e o vínculo `Student.identity_id`, inclusive para pedidos resolvidos; relações legadas com
`Student.identity_id` ou `StudentIdentity.student_id` nulos continuam aceitas quando não contradizem
os dados disponíveis. Um caso adversarial com FKs válidas e identidade de outro Box é reprovado.
`tests/test_tenant_restore_semantic_smoke.py` passou 1/1 em PostgreSQL 15 descartável com migrations
reais; `py_compile` e `git diff --check` passaram. Isso continua sendo um gate sintético, não prova
um restore A/B real nem fecha F2.

**F2 — compatibilidade de alias no smoke (23/10/2026):** o resolver `student_identity.facade.tenant_resolver`
procura Box por `schema_name` ou por `slug` quando a FK `box` não está preenchida. O smoke antes
exigia somente `schema_name`, contrariando esse fallback legado. Agora `StudentIdentity`,
`StudentBoxMembership` e `StudentProfileChangeRequest` reconhecem ambos; a regressão zera as FKs,
grava `box_root_slug=Box.slug` e comprova aprovação. A suíte focal passou **1/1** com migrations em
PostgreSQL 15 descartável, inclusive os casos negativos já existentes.

**F2 — âncoras shared por Box (23/10/2026):** o gate read-only compara FK opcional e root legado
para consentimentos, convites individuais/de grupo, subscriptions push e os lados de origem/destino
de `StudentTransfer`. Não exige Student atual para `student_id` histórico de convite/transferência,
nem exige que a identidade atual esteja no Box de um consentimento histórico. O teste reproduz
FK/slug divergentes em invitation e transfer e rejeita ambos; fixture positiva com quatro sidecars e
transferência pendente também passa. `tests/test_tenant_restore_semantic_smoke.py` passou **1/1**
em PostgreSQL 15 descartável com migrations reais.

**F2 — contrato interno de milestone (23/10/2026):** a análise de `funnel_events._milestone_keys`
e `record_authenticated_student_return` confirma que todo milestone com `identity_id` grava o mesmo
ID em `subject_key`/`identity`, e também em `cohort_key` se `cohort_kind=identity`. O smoke valida
esses campos mas tolera ID ausente em `public` e não exige membership atual, pois o fato analítico
é histórico. O teste altera `subject_key` sem alterar `identity_id`, recebe reprovação e depois
restaura o canário; módulo focal passou **1/1** com migrations em PostgreSQL 15 descartável.

**F2 — referência de webhook Stripe (23/10/2026):** `integrations/stripe/router.py` grava
`StripePaymentRef` em public antes do reconcile e usa `box_schema/payment_id` para roteamento de
refund/dispute sem metadata no evento. O smoke valida schema canônico, Payment existente e, quando
`Payment.stripe_payment_intent_id` foi persistido, igualdade de PI/schema/PK mesmo se o registro
shared foi desviado para outro Box. A regressão cobre Payment ausente, schema legado não canônico
e a chave roteada para outro Box/pagamento; fixture correta passa. O contrato em código deixa PI
ausente no Payment enquanto a cobrança aguarda confirmação, então nesses casos só se pode provar
que o Payment alvo existe; comparar com estado anterior continua sendo função do drill/baseline.
`tests/test_tenant_restore_semantic_smoke.py` passou **1/1** em PostgreSQL 15 descartável.

**Rechecagem de commands (24/10/2026):** após adicionar o backfill shared de `PendingSignup`, o checkout contém **72 implementações** de management command (excluindo `__init__.py`); todas estão nomeadas nas classes da tabela acima, inclusive `set_tenant_write_fence` como a única escrita control-plane autorizada no drill e os cinco backfills de e-mail como writers shared a pausar. Os backfills gravam somente HMAC em `public`; modos dry-run/verify não escrevem. Isso não cobre scripts externos ao Django, operadores, hooks do provedor nem processos em voo. `populate_test_db` permanece fora da janela F2 por suas escritas `auth/control` anteriores ao guard. A verificação de nomes e a contagem completa precisam ser repetidas após novas adições ao checkout.

**F2 — expansão do censo de referências escalares (24/10/2026):** o registry Django e os leitores/escritores foram revisados para campos escalares de ID além de `student_id`/`identity_id`. `WorkoutApprovalPolicySetting.box_id` é a única nova referência corrente a entidade shared identificada neste recorte: o setting vive no schema tenant e `operations.workout_approval_policy.resolve_workout_approval_policy()` procura a configuração pelo PK do `control.Box` corrente, embora não exista FK. O smoke read-only agora exige que cada setting presente no schema restaurado use o PK do Box alvo; a regressão adultera esse valor e exige reprovação. IDs de sessão em eventos e `StudentAppActivity.source_object_id` são locais/polimórficos ou telemetria; `AsyncJob.created_by_id` é ator opcional sem garantia de retenção; UUIDs de request do draft são chaves de correlação; e IDs de provider são externos. Nenhum é tratado como FK atual. `tests/test_tenant_restore_semantic_smoke.py` passou **1/1** em PostgreSQL descartável com migrations reais. O censo é delimitado aos modelos instalados e código deste checkout; não infere contratos de integrações externas nem substitui a comparação de baseline do drill.

**F2 — reconciliação de timers e identidade das units (24/10/2026):** comparação dos 11 timers versionados com `docs/rollout/restore-and-rollback-drill.md` identificou a omissão de `octobox-wod-cleanup.timer` e do `octobox-runtime-check.timer`. O primeiro apaga drafts/intents vencidos; o segundo não grava no banco, mas pode emitir alerta externo se HTTP for parado. Ambos foram incluídos na pausa documentada. `octobox-wod-cleanup` e seis outros jobs Django agora usam `octobox:octobox` com `UMask=0077`; o scanner de notificações já usava essa identidade. `octobox-env-backup.timer` foi classificado como cópia externa de segredo, sem escrita tenant; nenhum segredo pode ser rotacionado durante a janela. `tests.test_tenant_restore_timer_inventory` passou **2 testes + 8 subtests**, YAML parseou e `git diff --check` passou; `systemd-analyze verify` retornou sucesso em Ubuntu 24.04 descartável com avisos de modo gerados pelo bind mount Windows. O estado instalado e serviços/units externos ao checkout não foram inspecionados; `octobox-backup`, `octobox-env-backup` e `octobox-runtime-check` continuam como `root` e precisam de revisão específica de privilégio mínimo.

**F2 — revisão de privilégio dos serviços de backup/runtime (24/10/2026):** `octobox-backup` e `octobox-env-backup` permanecem `root`: os scripts exigem EUID 0, usam `/root/.config/rclone/rclone.conf` (diretório 0700/arquivo 0600), escrevem estado/artefatos e fazem retenção/sync. `octobox-runtime-check` não precisa dessas operações; a unit agora define `User=octobox`, `Group=octobox`, `UMask=0077`, aponta para `/srv/octobox/current`, e o script não exige root. O runbook usa `systemctl start/status` para o disparo manual, preservando ambiente e identidade da unit. Teste em container Ubuntu 24.04 passou como `octobox` com diretórios `root:octobox` `0750`, status `0640`, dump sintético `0600` e health/systemctl/df simulados; `systemd-analyze verify` retornou sucesso com avisos de permissão do bind mount Windows; a regressão passou **4 testes + 9 subtests**. O check depende de `/srv/octobox/shared/deploy-state/last_backup_path` ser legível (arquivo esperado 0640 por `Group=octobox`/`UMask=0027` da unit de backup) e dos diretórios de backup atravessáveis; essa convenção foi inspecionada no bootstrap e script, não medida no host. Instalação, estado/permissões reais, runtime do webhook e unidade de backup ativa seguem pendentes; nenhuma unit foi operada no host.

### F2 — canais Redis realtime agora separados por tenant (24/10/2026)

O inventário do checkout identificou os publicadores centralizados em `shared_support.student_event_stream` e `shared_support.manager_event_stream`. Antes da correção, o primeiro formava o canal somente pelo PK do aluno e o segundo assinava um canal global. O mesmo PK pode existir em Boxes diferentes; os streams carregam tipos e metadata operacionais. Agora os dois canais são namespaced por `connection.schema_name` validado como `box_<slug>`, e publicação/leitura falha fechada quando não há contexto Box. `StreamingHttpResponse` é lazy, então o schema de inscrição é capturado na view, antes do iterador ser executado.

Validação: `tests/test_tenant_scoped_event_streams.py` + `tests/test_g2_safe_error_surfaces.py`, **23/23**. O stream é read-only e pode permanecer aberto durante freeze; o tenant write fence protege writes HTTP e não encerra SSE existente. Se surgir escrita no stream, ela precisa adquirir o guard explicitamente. Sem migration ou acesso a Redis/host real.

**Atualização F2 — channels audit (24/10/2026):** a leitura dos callsites não encontrou publicação direta fora dos dois módulos centrais. Os callers de produto encontrados em `catalog`, `operations` e `onboarding` são fluxos tenant por request; a fachada inbound legada de `communications` não tem caller de runtime neste checkout. Se ela for reativada em webhook/worker, deve resolver/ativar o Box explicitamente antes de mutar e publicar. O modo fail-closed impede canal cross-tenant, mas pode suprimir a notificação de refresh quando um caller executar sem contexto.
