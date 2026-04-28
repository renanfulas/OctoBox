<!--
ARQUIVO: mapa do projeto derivado da suite de testes.

POR QUE ELE EXISTE:
- transforma os testes em um mapa pratico do esqueleto real do OctoBOX.
- ajuda humanos e agentes a entenderem quais circuitos do produto ja possuem contrato vivo.

O QUE ESTE ARQUIVO FAZ:
1. resume a leitura de todos os arquivos de teste do projeto.
2. organiza a suite por dominios funcionais.
3. aponta onde procurar quando uma mudanca tocar um circuito sensivel.
4. registra lacunas e riscos que os testes tambem revelam.

PONTOS CRITICOS:
- este mapa nao substitui a suite: ele aponta para ela.
- quando testes forem criados, renomeados ou removidos, este documento precisa ser atualizado.
- testes, runtime e codigo continuam vencendo qualquer resumo escrito aqui.
-->

# Mapa do projeto pelos testes

Atualizado em: 2026-04-28.

Este mapa foi feito lendo a suite atual de testes do OctoBOX. Pense nos testes como sensores espalhados por um predio: eles mostram quais paredes, portas, alarmes e corredores ja foram medidos. Quando muitos sensores aparecem em um corredor, aquele corredor provavelmente e uma parte viva e importante do produto.

## Metodo de leitura

Foram considerados os arquivos de teste do projeto fora de `.venv`, `.git`, `.claude`, `staticfiles`, `backups`, `tmp` e da pasta espelho legada `OctoBox/`.

Resultado da leitura:

1. 107 arquivos com nome de teste.
2. 765 testes automatizados detectados por classes/funcoes `test*`.
3. 6 arquivos soltos na raiz com nome de teste; alguns sao scripts manuais, nao testes pytest convencionais.
4. A maior densidade esta em app do aluno/identidade, WOD/operacoes, financeiro/churn, catalogo/alunos e integracoes/jobs.

Regra de autoridade:

1. se este mapa divergir do teste, o teste vence.
2. se o teste divergir do runtime real, investigue o runtime e atualize o teste.
3. se um doc antigo divergir dos testes, trate o doc antigo como snapshot historico.

## Esqueleto vivo que a suite revela

O OctoBOX testado hoje e um monolito modular orientado por dominio. O Django ainda e o corpo que sobe a aplicacao, mas os testes mostram que o comportamento vivo ja esta distribuido por apps e fachadas promovidas:

1. `access` controla entrada, login, papeis, shell e hosts publico/app.
2. `students`, `catalog`, `finance` e `operations` concentram o negocio operacional.
3. `student_identity` e `student_app` formam o segundo produto: a experiencia mobile/PWA do aluno.
4. `communications`, `integrations`, `jobs` e `api/v1` formam a fronteira externa e assincrona.
5. `knowledge`, `guide`, `monitoring`, `reporting` e `shared_support` sustentam leitura, observabilidade, payloads e ferramentas transversais.
6. `boxcore` ainda guarda muito estado historico, mas os testes confirmam que ele nao deve ser lido como unico centro conceitual do runtime.

Em linguagem simples: o projeto nao e mais uma caixa unica. Ele e uma academia com varios setores: recepcao, financeiro, sala de treino, app do aluno, seguranca, relatorios e sala de controle. Os testes dizem quais setores ja tem alarme na porta.

## Mapa por circuito

### 1. Acesso, login, papeis e shell

O que os testes protegem:

1. landing publica e separacao entre host de marketing e host do app.
2. login com CSRF, redirect seguro e bloqueio de `next` externo.
3. criacao/edicao de perfis de acesso sem depender do admin bruto.
4. grupos e permissoes padrao para owner, dev, manager, reception e coach.
5. shell compartilhado, contadores e contexto de navegacao.

Testes principais:

1. `access/tests/test_access_overview.py`
2. `access/tests/test_login_security.py`
3. `access/tests/test_public_landing.py`
4. `access/tests/test_security.py`
5. `boxcore/tests/test_access.py`
6. `tests/test_shell_and_context.py`

Arquivos de codigo que este corredor costuma tocar:

1. `access/views.py`
2. `access/roles/*`
3. `access/context_processors.py`
4. `access/permissions/mixins.py`
5. `templates/access/*`
6. `config/urls.py`

Risco de debito tecnico:

1. misturar host publico e host do app pode quebrar marketing, login e seguranca ao mesmo tempo.
2. permissao criada diretamente na view tende a virar excecao invisivel; prefira o contrato de roles/permissoes.

### 2. Catalogo, alunos, planos e cadastro

O que os testes protegem:

1. diretorio de alunos, filtros, KPIs, export CSV/PDF e acoes rapidas.
2. cadastro rapido com normalizacao de telefone, CPF, data e notas.
3. fluxo intake -> aluno definitivo.
4. matricula, plano, cobranca inicial e acoes na ficha do aluno.
5. queries, services, workflows e page payloads do catalogo.
6. blind index para telefone e identidade de canal.

Testes principais:

1. `boxcore/tests/test_catalog.py`
2. `boxcore/tests/test_catalog_services.py`
3. `boxcore/tests/test_students_domain.py`
4. `boxcore/tests/test_student_acquisition.py`
5. `boxcore/tests/test_student_source_capture_view.py`
6. `boxcore/tests/test_student_source_declaration.py`
7. `boxcore/tests/test_blind_index.py`
8. `tests/test_catalog_report_exports.py`
9. `tests/test_students_facade_attribution.py`

Arquivos de codigo que este corredor costuma tocar:

1. `catalog/views/student_views.py`
2. `catalog/student_queries.py`
3. `catalog/services/student_workflows.py`
4. `catalog/services/student_enrollment_actions.py`
5. `catalog/services/student_payment_actions.py`
6. `catalog/forms.py`
7. `students/models.py`
8. `onboarding/models.py`
9. `templates/catalog/*`

Risco de debito tecnico:

1. colocar regra de negocio dentro do template deixa o teste cego.
2. mexer em normalizacao de telefone sem atualizar blind index pode quebrar busca, deduplicacao e WhatsApp.

### 3. Financeiro, pagamentos, churn e vendas rapidas

O que os testes protegem:

1. centro financeiro visual com filtros, planos, carteira e fila operacional.
2. exportacao, criacao/edicao de planos e estado de filtro em sessao.
3. pagamentos, parcelamento, regeneracao, cancelamento, estorno e reativacao.
4. Stripe checkout/webhooks, idempotencia e contratos de retorno.
5. churn financeiro, follow-up, analytics, recomendacao e tensionamento de prioridade.
6. quick sales com memoria, templates, fuzzy matching e acoes pela interface.

Testes principais:

1. `boxcore/tests/test_finance.py`
2. `boxcore/tests/test_finance_churn_foundation.py`
3. `tests/test_finance_center_request.py`
4. `tests/test_integrations_stripe_services.py`
5. `tests/test_quick_sales_wave2.py`
6. `tests/test_quick_sales_wave3.py`
7. `tests/test_quick_sales_wave4.py`
8. `boxcore/tests/test_catalog_services.py`
9. `boxcore/tests/test_audit.py`

Arquivos de codigo que este corredor costuma tocar:

1. `catalog/views/finance_views.py`
2. `catalog/finance_queries.py`
3. `catalog/services/finance_communication_actions.py`
4. `catalog/services/membership_plan_workflows.py`
5. `finance/models.py`
6. `finance/*`
7. `quick_sales/*`
8. `integrations/stripe/*`
9. `templates/catalog/finance*.html`

Risco de debito tecnico:

1. financeiro mistura dinheiro, status operacional e auditoria; um atalho sem teste pode parecer pequeno e quebrar caixa.
2. idempotencia em pagamento e webhook e contrato de seguranca, nao detalhe cosmetico.

### 4. Operacoes, aulas, grade e WOD

O que os testes protegem:

1. workspace operacional por papel.
2. grade de aulas, recorrencia, limite diario/semanal/mensal e bloqueio de exclusao com presenca.
3. snapshots de aula, ocupacao, status automatico e sessoes em andamento.
4. importacao operacional de leads, policy, inspector, orchestrator, jobs e despacho noturno.
5. editor de WOD, board de aprovacao, historico pos-publicacao e governanca semanal.
6. smart paste, parser, projection, conflitos e criacao de drafts.

Testes principais:

1. `boxcore/tests/test_operations.py`
2. `boxcore/tests/test_operations_domain.py`
3. `boxcore/tests/test_operations_services.py`
4. `boxcore/tests/test_operations_policy.py`
5. `boxcore/tests/test_operations_inspector.py`
6. `boxcore/tests/test_operations_orchestrator.py`
7. `boxcore/tests/test_operations_jobs.py`
8. `boxcore/tests/test_operations_night_dispatch_command.py`
9. `operations/domain/tests/test_session_cancellation_rules.py`
10. `tests/test_coach_wod_editor.py`
11. `tests/test_workout_approval_board.py`
12. `tests/test_workout_planner_builders.py`
13. `tests/test_workout_post_publication_history.py`
14. `tests/test_workout_smart_paste.py`
15. `tests/test_workout_weekly_governance.py`
16. `tests/test_wod_paste_parser.py`
17. `tests/test_wod_projection.py`

Arquivos de codigo que este corredor costuma tocar:

1. `operations/workspace_views.py`
2. `operations/queries.py`
3. `operations/models.py`
4. `operations/forms.py`
5. `operations/services/*`
6. `operations/tasks.py`
7. `operations/workout_planner_builders.py`
8. `operations/workout_corridor_navigation.py`
9. `templates/operations/*`
10. `student_app/models.py`

Risco de debito tecnico:

1. WOD e grade parecem telas de treino, mas carregam politica operacional. Se bypassar aprovacao, historico ou permissao, a rotina do box perde rastreabilidade.
2. Smart Paste precisa manter preview/revisao antes de gravar; transformar parse em save direto aumenta o risco de publicar semana errada.

### 5. App do aluno e identidade

O que os testes protegem:

1. entrada por convite, identidade do aluno e troca de box ativo.
2. PWA, manifest, service worker, offline, grade, WOD, RM e configuracoes.
3. middleware de autenticacao do aluno.
4. consumo de WOD publicado, RM e relacao com sessoes.
5. diferenca entre usuario interno e experiencia mobile do aluno.

Testes principais:

1. `student_identity/tests.py`
2. `student_app/tests.py`
3. `tests/test_weekly_wod_plan_models.py`
4. `boxcore/tests/test_guide.py`

Arquivos de codigo que este corredor costuma tocar:

1. `student_identity/*`
2. `student_app/views/*`
3. `student_app/models.py`
4. `student_app/services/*`
5. `student_app/urls.py`
6. `templates/student_app/*`
7. `static/css/student_app/*`
8. `static/js/student_app/*`

Risco de debito tecnico:

1. app do aluno e produto proprio; nao trate como so uma tela pequena do admin.
2. mudanca visual em `student_app` precisa respeitar mobile/PWA/offline e os contratos de identidade.

### 6. API, jobs, integracoes e Signal Mesh

O que os testes protegem:

1. raiz da API, versionamento e manifesto.
2. rotas `api/v1` para integracoes, jobs e RAG.
3. contratos de Signal Mesh: envelope, idempotencia, retry, failure policy e middleware.
4. jobs base, dispatcher, modelo, comando e reprocessamento.
5. WhatsApp webhook/reprocessing e Stripe services.
6. comandos de sweep e retry.

Testes principais:

1. `boxcore/tests/test_api.py`
2. `tests/test_api_v1_routing.py`
3. `tests/test_api_v1_integrations_views.py`
4. `tests/test_api_v1_jobs_views.py`
5. `tests/test_asyncjob_signal_mesh_migration_command.py`
6. `tests/test_integrations_mesh_contracts.py`
7. `tests/test_integrations_mesh_failure_policy.py`
8. `tests/test_integrations_mesh_retry_policy.py`
9. `tests/test_integrations_middleware.py`
10. `tests/test_jobs_base.py`
11. `tests/test_jobs_dispatcher.py`
12. `tests/test_jobs_models.py`
13. `tests/test_jobs_management_command.py`
14. `tests/test_jobs_reprocessing.py`
15. `tests/test_signal_mesh_management_commands.py`

Arquivos de codigo que este corredor costuma tocar:

1. `api/urls.py`
2. `api/v1/urls.py`
3. `api/v1/views.py`
4. `api/v1/internal_views.py`
5. `integrations/*`
6. `jobs/*`
7. `monitoring/*`
8. `shared_support/idempotency.py`

Risco de debito tecnico:

1. integracao externa precisa de contrato estreito. Um payload frouxo vira bug que so aparece quando o parceiro chama.
2. retry sem idempotencia pode duplicar efeito: em dinheiro ou presenca, duplicar efeito e pior que falhar visivelmente.

### 7. Comunicacoes, WhatsApp e inbound

O que os testes protegem:

1. contato WhatsApp com blind index.
2. deduplicacao/idempotencia de inbound.
3. services de comunicacao e logs de toque operacional.
4. reprocessamento de eventos WhatsApp.
5. ligacao entre mensagens, contato, intake, aluno e financeiro.

Testes principais:

1. `boxcore/tests/test_integrations.py`
2. `tests/test_communications_inbound_idempotency.py`
3. `tests/test_communications_services.py`
4. `tests/test_integrations_whatsapp_models.py`
5. `tests/test_integrations_whatsapp_reprocessing.py`
6. `tests/test_integrations_whatsapp_services.py`
7. `test_whatsapp_webhook.py` como script pratico/manual.

Arquivos de codigo que este corredor costuma tocar:

1. `communications/models.py`
2. `communications/services.py`
3. `communications/queries.py`
4. `integrations/whatsapp/*`
5. `boxcore/models/communications.py`
6. `shared_support/phone_numbers.py`

Risco de debito tecnico:

1. telefone criptografado nao deve ser consultado por igualdade direta.
2. use `contact_id`, `phone_lookup_index` e normalizacao compartilhada para evitar regressao silenciosa.

### 8. Conhecimento interno, RAG e guide

O que os testes protegem:

1. retrieval interno de conhecimento do projeto.
2. API de RAG com autorizacao, busca e resposta.
3. guide/system map como superficie interna de leitura do sistema.
4. despacho/reindex como job ou fronteira async.

Testes principais:

1. `tests/test_knowledge_retrieval.py`
2. `tests/test_api_v1_project_rag_views.py`
3. `boxcore/tests/test_guide.py`
4. `tests/test_jobs_dispatcher.py`

Arquivos de codigo que este corredor costuma tocar:

1. `knowledge/*`
2. `guide/*`
3. `api/v1/project_rag_views.py`
4. `jobs/*`

Risco de debito tecnico:

1. RAG deve continuar como camada de leitura; nao misture com regra transacional.
2. citacao e autorizacao importam: busca interna nao pode virar vazamento interno amplo.

### 9. Dashboard, page payloads e leitura executiva

O que os testes protegem:

1. dashboard por papel e prioridades de leitura.
2. layout schema, preferencia de blocos e anti-burst.
3. page payload, hero contract, bridge contract e surface runtime.
4. snapshot serializavel e helpers de prioridade.

Testes principais:

1. `boxcore/tests/test_dashboard.py`
2. `boxcore/tests/test_page_payloads.py`
3. `tests/test_dashboard_reading_priority.py`
4. `tests/test_dashboard_snapshot_serialization.py`
5. `tests/test_page_payload_priority_helpers.py`
6. `tests/test_manager_workspace_toggle.py`

Arquivos de codigo que este corredor costuma tocar:

1. `dashboard/*`
2. `shared_support/page_payloads.py`
3. `operations/queries.py`
4. `templates/dashboard/*`
5. `templates/shared/*`

Risco de debito tecnico:

1. dashboard nao deve virar soma de cards aleatorios; os testes protegem prioridade e acao principal.
2. page payload e contrato entre backend e front. Quebrar chave de payload quebra tela sem erro obvio no Python.

### 10. Monitoramento, performance, deploy e smoke

O que os testes protegem:

1. budget de performance visual/frontend.
2. query count e benchmarks de dashboard, alunos e financeiro.
3. headers de timing e ocultacao de debug interno.
4. published page probe.
5. contrato de deploy Render/public hosts.
6. pre-VPS operational smoke e integridade historica.
7. Alert Siren, Red Beacon e runtime Signal Mesh.

Testes principais:

1. `boxcore/tests/test_frontend_performance_budgets.py`
2. `tests/test_performance.py`
3. `tests/test_request_timing_headers.py`
4. `tests/test_published_page_probe.py`
5. `tests/test_render_deploy_contract.py`
6. `tests/test_pre_vps_operational_smoke_command.py`
7. `tests/test_historical_integrity_command.py`
8. `tests/test_monitoring_alert_siren.py`
9. `tests/test_monitoring_beacon_snapshot.py`
10. `tests/test_monitoring_signal_mesh_metrics.py`
11. `tests/test_monitoring_signal_mesh_runtime.py`

Arquivos de codigo que este corredor costuma tocar:

1. `monitoring/*`
2. `shared_support/published_page_probe.py`
3. `shared_support/request_timing.py`
4. `config/settings/*`
5. `management/commands/*`
6. `.github/workflows/*`

Risco de debito tecnico:

1. performance e smoke sao contrato de operacao, nao luxo.
2. debug header em producao e risco de vazamento; teste deve continuar protegendo isso.

### 11. Auditoria, seguranca e dados sensiveis

O que os testes protegem:

1. eventos de auditoria em login, logout, admin e acoes financeiras.
2. CSRF, CSP, private admin path, throttling e guardas de seguranca.
3. blind index e criptografia de PII.
4. scripts manuais de stress, rate limit e injecao CSV.

Testes principais:

1. `boxcore/tests/test_audit.py`
2. `boxcore/tests/test_security_guards.py`
3. `boxcore/tests/test_blind_index.py`
4. `access/tests/test_login_security.py`
5. `access/tests/test_security.py`
6. `test_csv_injection.py` como script manual.
7. `test_fire.py` como script manual de stress.
8. `test_rate_limit.py` como script manual.
9. `test_whale.py` como script manual de volume.

Arquivos de codigo que este corredor costuma tocar:

1. `auditing/*`
2. `shared_support/security/*`
3. `shared_support/crypto_fields.py`
4. `access/permissions/*`
5. `config/settings/production.py`
6. `operations/services/contact_importer.py`

Risco de debito tecnico:

1. scripts manuais na raiz nao entram naturalmente como pytest; se virarem gate de release, devem migrar para teste automatizado ou comando documentado.
2. dado sensivel precisa de contrato simples e repetivel: criptografia para armazenar, blind index para buscar.

### 12. Onboarding, intake e importacao

O que os testes protegem:

1. intake center e convite de aluno.
2. atribuicao de origem, canal operacional e fallback legado.
3. importacao CSV de alunos.
4. lead import pipeline e politicas de volume.
5. captura de fonte declarada pelo aluno.

Testes principais:

1. `boxcore/tests/test_onboarding.py`
2. `onboarding/tests.py`
3. `boxcore/tests/test_import_students.py`
4. `tests/test_onboarding_attribution.py`
5. `boxcore/tests/test_operations_policy.py`
6. `boxcore/tests/test_operations_inspector.py`
7. `boxcore/tests/test_operations_orchestrator.py`
8. `boxcore/tests/test_operations_jobs.py`

Arquivos de codigo que este corredor costuma tocar:

1. `onboarding/*`
2. `operations/services/contact_importer.py`
3. `operations/services/lead_import_*`
4. `students/*`
5. `templates/onboarding/*`

Risco de debito tecnico:

1. onboarding e funil comercial; perder origem/canal agora reduz inteligencia futura.
2. importacao grande precisa de policy e job, nao request HTTP longo.

### 13. Reporting e exportacoes

O que os testes protegem:

1. fachada de reporting delegando para infraestrutura.
2. exportacoes de catalogo.

Testes principais:

1. `tests/test_reporting_facade.py`
2. `tests/test_catalog_report_exports.py`

Arquivos de codigo que este corredor costuma tocar:

1. `reporting/*`
2. `catalog/*`

Risco de debito tecnico:

1. relatorio deve ficar atras de fachada; se cada view montar exportacao do seu jeito, a manutencao espalha.

## Inventario completo dos arquivos de teste lidos

### `access/tests`

1. `access/tests/test_access_overview.py` - 2 testes.
2. `access/tests/test_login_security.py` - 3 testes.
3. `access/tests/test_public_landing.py` - 4 testes.
4. `access/tests/test_security.py` - 1 teste.

### `boxcore/tests`

1. `boxcore/tests/test_access.py` - 14 testes.
2. `boxcore/tests/test_api.py` - 5 testes.
3. `boxcore/tests/test_audit.py` - 3 testes.
4. `boxcore/tests/test_blind_index.py` - 11 testes.
5. `boxcore/tests/test_catalog.py` - 57 testes.
6. `boxcore/tests/test_catalog_services.py` - 12 testes.
7. `boxcore/tests/test_dashboard.py` - 23 testes.
8. `boxcore/tests/test_finance.py` - 12 testes.
9. `boxcore/tests/test_finance_churn_foundation.py` - 36 testes.
10. `boxcore/tests/test_frontend_performance_budgets.py` - 10 testes.
11. `boxcore/tests/test_guide.py` - 21 testes.
12. `boxcore/tests/test_import_students.py` - 1 teste.
13. `boxcore/tests/test_integrations.py` - 5 testes.
14. `boxcore/tests/test_onboarding.py` - 8 testes.
15. `boxcore/tests/test_operations.py` - 35 testes.
16. `boxcore/tests/test_operations_domain.py` - 16 testes.
17. `boxcore/tests/test_operations_inspector.py` - 7 testes.
18. `boxcore/tests/test_operations_jobs.py` - 2 testes.
19. `boxcore/tests/test_operations_night_dispatch_command.py` - 5 testes.
20. `boxcore/tests/test_operations_orchestrator.py` - 4 testes.
21. `boxcore/tests/test_operations_policy.py` - 8 testes.
22. `boxcore/tests/test_operations_services.py` - 8 testes.
23. `boxcore/tests/test_page_payloads.py` - 10 testes.
24. `boxcore/tests/test_reset_demo_workspace.py` - 2 testes.
25. `boxcore/tests/test_security_guards.py` - 11 testes.
26. `boxcore/tests/test_seed_pilot_workspace.py` - 1 teste.
27. `boxcore/tests/test_settings.py` - 6 testes.
28. `boxcore/tests/test_student_acquisition.py` - 2 testes.
29. `boxcore/tests/test_student_source_capture_view.py` - 1 teste.
30. `boxcore/tests/test_student_source_declaration.py` - 3 testes.
31. `boxcore/tests/test_students_domain.py` - 22 testes.

### Apps com `tests.py`

1. `onboarding/tests.py` - 3 testes.
2. `student_app/tests.py` - 81 testes.
3. `student_identity/tests.py` - 53 testes.

### `operations/domain/tests`

1. `operations/domain/tests/test_session_cancellation_rules.py` - 17 testes.

### `tests`

1. `tests/test_api_v1_integrations_views.py` - 2 testes.
2. `tests/test_api_v1_jobs_views.py` - 3 testes.
3. `tests/test_api_v1_project_rag_views.py` - 4 testes.
4. `tests/test_api_v1_routing.py` - 3 testes.
5. `tests/test_asyncjob_signal_mesh_migration_command.py` - 2 testes.
6. `tests/test_auto_callables.py` - 4 testes.
7. `tests/test_catalog_report_exports.py` - 2 testes.
8. `tests/test_class_session_class_type.py` - 2 testes.
9. `tests/test_coach_wod_editor.py` - 32 testes.
10. `tests/test_communications_inbound_idempotency.py` - 2 testes.
11. `tests/test_communications_services.py` - 3 testes.
12. `tests/test_dashboard_reading_priority.py` - 4 testes.
13. `tests/test_dashboard_snapshot_serialization.py` - 2 testes.
14. `tests/test_finance_center_request.py` - 2 testes.
15. `tests/test_historical_integrity_command.py` - 3 testes.
16. `tests/test_import_all_modules.py` - 1 teste.
17. `tests/test_integrations_mesh_contracts.py` - 4 testes.
18. `tests/test_integrations_mesh_failure_policy.py` - 4 testes.
19. `tests/test_integrations_mesh_retry_policy.py` - 5 testes.
20. `tests/test_integrations_middleware.py` - 3 testes.
21. `tests/test_integrations_stripe_services.py` - 2 testes.
22. `tests/test_integrations_whatsapp_models.py` - 2 testes.
23. `tests/test_integrations_whatsapp_reprocessing.py` - 3 testes.
24. `tests/test_integrations_whatsapp_services.py` - 2 testes.
25. `tests/test_jobs_base.py` - 2 testes.
26. `tests/test_jobs_dispatcher.py` - 5 testes.
27. `tests/test_jobs_management_command.py` - 2 testes.
28. `tests/test_jobs_models.py` - 1 teste.
29. `tests/test_jobs_reprocessing.py` - 3 testes.
30. `tests/test_knowledge_retrieval.py` - 3 testes.
31. `tests/test_manager_workspace_toggle.py` - 5 testes.
32. `tests/test_monitoring_alert_siren.py` - 2 testes.
33. `tests/test_monitoring_beacon_snapshot.py` - 2 testes.
34. `tests/test_monitoring_signal_mesh_metrics.py` - 1 teste.
35. `tests/test_monitoring_signal_mesh_runtime.py` - 1 teste.
36. `tests/test_onboarding_attribution.py` - 4 testes.
37. `tests/test_operations_action_views.py` - 3 testes.
38. `tests/test_operations_tasks.py` - 3 testes.
39. `tests/test_operations_workspace_signal_mesh.py` - 2 testes.
40. `tests/test_operations_workspace_transport.py` - 2 testes.
41. `tests/test_operations_workspace_views.py` - 1 teste.
42. `tests/test_page_payload_priority_helpers.py` - 4 testes.
43. `tests/test_performance.py` - 4 testes.
44. `tests/test_pre_vps_operational_smoke_command.py` - 1 teste.
45. `tests/test_published_page_probe.py` - 4 testes.
46. `tests/test_quick_sales_wave2.py` - 5 testes.
47. `tests/test_quick_sales_wave3.py` - 5 testes.
48. `tests/test_quick_sales_wave4.py` - 7 testes.
49. `tests/test_render_deploy_contract.py` - 2 testes.
50. `tests/test_reporting_facade.py` - 1 teste.
51. `tests/test_request_timing_headers.py` - 2 testes.
52. `tests/test_shell_and_context.py` - 2 testes.
53. `tests/test_signal_mesh_management_commands.py` - 2 testes.
54. `tests/test_students_facade_attribution.py` - 2 testes.
55. `tests/test_weekly_wod_plan_models.py` - 3 testes.
56. `tests/test_wod_paste_parser.py` - 2 testes.
57. `tests/test_wod_projection.py` - 2 testes.
58. `tests/test_workout_approval_board.py` - 15 testes.
59. `tests/test_workout_planner_builders.py` - 20 testes.
60. `tests/test_workout_post_publication_history.py` - 6 testes.
61. `tests/test_workout_smart_paste.py` - 8 testes.
62. `tests/test_workout_weekly_governance.py` - 4 testes.

### Scripts manuais soltos na raiz

1. `test_csv_injection.py` - script manual de protecao contra formula/injecao CSV.
2. `test_fire.py` - script manual de stress em `/login/`.
3. `test_login_error.py` - 1 teste automatizado detectado.
4. `test_rate_limit.py` - script manual de rajada contra login.
5. `test_whale.py` - script manual de importacao massiva.
6. `test_whatsapp_webhook.py` - script manual pratico do webhook de voto WhatsApp.

## Como usar este mapa em mudancas futuras

Antes de mexer em um dominio:

1. ache o circuito acima.
2. leia os testes principais do circuito.
3. leia os arquivos de codigo apontados.
4. faca a menor mudanca que respeite o contrato atual.
5. rode pelo menos a suite focada daquele circuito.

Exemplos:

1. Mudou WOD? Rode `tests/test_coach_wod_editor.py`, `tests/test_workout_approval_board.py`, `tests/test_workout_smart_paste.py` e os testes de `operations`.
2. Mudou aluno/financeiro? Rode `boxcore/tests/test_catalog.py`, `boxcore/tests/test_catalog_services.py`, `boxcore/tests/test_finance.py` e `boxcore/tests/test_finance_churn_foundation.py`.
3. Mudou login/role/shell? Rode `access/tests/*`, `boxcore/tests/test_access.py` e `tests/test_shell_and_context.py`.
4. Mudou API/job/integracao? Rode `tests/test_api_v1_*`, `tests/test_jobs_*` e `tests/test_integrations_*`.
5. Mudou app do aluno? Rode `student_identity/tests.py`, `student_app/tests.py` e `tests/test_weekly_wod_plan_models.py`.

## Lacunas que a leitura dos testes sugere

1. Os scripts manuais da raiz tem valor operacional, mas deveriam virar comandos ou testes pytest se forem gate recorrente.
2. Algumas suites grandes acumulam muitos contratos em um arquivo unico, especialmente `boxcore/tests/test_catalog.py`, `student_app/tests.py` e `student_identity/tests.py`; no futuro, vale dividir por corredor sem mudar comportamento.
3. Como alguns dominios ainda dependem de modelos historicos em `boxcore`, qualquer refactor de app label/model precisa de onda pequena e testes focados.
4. O mapa mostra boa cobertura de WOD, app do aluno, financeiro e integracoes; mudancas nessas areas devem assumir alto risco de regressao se feitas sem suite focada.

## Resumo executivo

O esqueleto real do OctoBOX pelos testes e:

1. `access` abre a porta certa para cada pessoa.
2. `catalog/students/finance` cuidam do aluno e do dinheiro.
3. `operations` organiza rotina, aula, lead import e WOD.
4. `student_identity/student_app` entregam o produto mobile do aluno.
5. `api/integrations/jobs/communications` conectam o sistema com o mundo externo.
6. `knowledge/guide/monitoring/reporting/shared_support` sustentam inteligencia, visibilidade, documentacao interna e contratos transversais.
7. `boxcore` ainda e importante, mas cada vez mais como raiz historica e ponte de estado, nao como mapa mental unico.
