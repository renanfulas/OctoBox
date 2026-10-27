<!--
ARQUIVO: corpus de contrato para rascunho, preview e confirmação do WOD diário/semanal.
STATUS: baseline A1; C-01–C-09 têm testes focais. W-00–W-07 têm exemplos e expectativas; W-07 agora fixa os sete dias, com evidência de parser. W-04 simula timeout HTTP sem chamar provider real; W-05 prova parse determinístico e confirmação/distribuição da fixture, não execução nem semântica de provider externo. ACL e isolamento tenant end-to-end ainda não foram executados integralmente.
BASE: a2ab398f5774b609b979a31c00527bc88b64b1fb.
-->

# Corpus de contrato — entrada e aplicação de WOD

Este corpus define entradas e resultados esperados para A2–A4. É uma especificação revisável, não uma alegação de que todos os casos foram executados. IDs abaixo são rótulos de fixture.

## Fixtures

| Fixture | Programa | ClassType | Aula | Estado inicial |
|---|---|---|---|---|
| P-CF | CrossFit | cross | S-101 | Sem WOD |
| P-CF | CrossFit | cross | S-102 | WOD draft, versão 4 |
| P-HY | HYROX customizado | cross | S-201 | Sem WOD |
| P-HY | HYROX customizado | cross | S-202 | Sem WOD |
| P-YG | Yoga customizado | other | S-301 | Sem WOD |
| P-OLD | Programa legado sem FK | cross | S-401 | Sem WOD |
| P-COM | CrossFit | cross | S-501 | completed; WOD publicado v8 |
| P-CAN | CrossFit | cross | S-502 | canceled |

S-101 e S-201 compartilham `ClassType=cross`, mas pertencem a programas distintos. A seleção nova de P-CF inclui apenas sessões P-CF; P-HY inclui apenas P-HY. O payload legado somente com `class_type=cross` mantém o alcance histórico por tipo e pode incluir ambos; preview precisa mostrar essa amplitude antes da confirmação compatível.

## Entradas de conteúdo

### W-00 — aplicação diária simples

Requisição legada atual: `target_date=2026-10-26`, `template_id=T-01`, `class_type=cross`, `mode=replace_empty`. Requisição nova equivalente escolhe `workout_program_id=P-CF` e referencia o template-base T-01.

Esperado: preview novo inclui somente aulas do programa P-CF naquela data, mostra quantidade e destinos por aula, preserva drafts existentes em `replace_empty`, e não altera o WOD até confirmação. Adapter legado conserva o filtro por `class_type` e identifica a faixa ampliada.

Evidência focal: `DayApplyFlowTests.test_day_preview_shows_distinct_programs_without_mutation` comprova prévia sem escrita e escopo por programa; `WodApplyIntentTests.test_daily_targets_one_program_preserves_completed_and_replays` comprova confirmação no programa escolhido, preservação de concluídas e replay único. A regressão diária passou 18 testes + 2 subtests em PostgreSQL descartável.

### W-01 — semana com valores preservados

```text
Segunda
Aquecimento
5 min remo
Força
Deadlift 5x5 75%
WOD AMRAP 12 min
10 burpees
12 wall balls 9 kg

Quarta
Mobilidade
8 min flow de quadril
```

Esperado: dois dias (weekday 0 e 2), ordem preservada, `12 min`, `5x5`, `75%` e `9 kg` sem perda/arredondamento; texto original continua disponível. Linha significativa não interpretada vira diagnóstico e bloqueia confirmação. Autosave não chama IA.

Evidência focal: `WodPasteParserTests.test_w01_preserves_weekdays_strength_reps_loads_and_amrap_timecap` e `WorkoutSmartPasteFlowTests.test_w01_weekly_contract_persists_structured_values_without_normalizer` verificam os valores e sua persistência no payload; a fixture entrou no parse determinístico sem chamar normalizador. `tests/test_wod_paste_parser.py` passou 5/5 e o fluxo HTTP passou 1/1 em PostgreSQL com migrations reais.

### W-02 — movimento personalizado

```text
Sexta
WOD For time 18 min
21-15-9 Atlas carry customizado 24 kg
```

Esperado: preservar rótulo raw `Atlas carry customizado` e carga `24 kg`; não inventar slug de catálogo. Mostrar como personalizado/sem vínculo validado e exigir reconhecimento explícito antes de confirmar. Sugestão automática não substitui o texto sem aceite.

Evidência focal: `WodPasteParserTests.test_w02_custom_movement_keeps_ladder_timecap_and_fixed_load_without_slug_guess` preserva o esquema 21-15-9, timecap 18, rótulo e carga sem criar slug. `WorkoutSmartPasteFlowTests.test_w02_custom_carry_keeps_load_and_requires_explicit_review_and_distribution_ack` confirmou o fluxo completo: revisão humana define `custom`, distribuição sem ACK não grava e com ACK usa o movimento/carga preservados.

### W-03 — troca de programa com preview aberto

Autor salva semana 2026-11-02 em P-CF, depois escolhe P-HY antes de confirmar o preview antigo.

Esperado: abrir draft independente de P-HY ou retornar `409 stale_preview`; não alterar o programa do plano P-CF nem enviar conteúdo para S-201/S-202. Plano confirmado não volta a draft por troca no composer.

Evidência focal (23/10/2026): `WorkoutSmartPasteFlowTests.test_switching_program_keeps_old_weekly_draft_and_confirmation_stale` passou em PostgreSQL descartável. Confirmar o plano CrossFit com o programa HYROX é recusado e mantém o plano original; trocar o composer cria/retoma um draft HYROX independente sem substituir o texto CrossFit.

### W-04 — texto incompleto / parser indisponível

```text
Segunda
WOD
```

Esperado: texto fica durável com ACK; preview diagnostica ausência de blocos; confirmação é bloqueada e nenhuma sessão é criada. Timeout do normalizador não perde texto nem altera WOD publicado.

Evidência focal (23/10/2026): `WorkoutSmartPasteFlowTests.test_provider_unavailable_preserves_source_and_offers_smartplan_recovery` comprova configuração sem credencial; `WorkoutSmartPasteFlowTests.test_provider_timeout_preserves_source_and_blocks_distribution` injeta `requests.exceptions.Timeout` na fronteira HTTP real do normalizador. Ambos mantêm `source_text`, exigem revisão e não criam `SessionWorkout`. O timeout foi simulado; nenhum provider real foi chamado.

### W-05 — WhatsApp, acentos, decimal, percentual e RX/scaled

```text
Terça
Força
Agachamento 4x6 52,5 kg
WOD For time 15 min
RX: 3 rounds de 12 thrusters 60% RM
Scaled: 3 rounds de 10 thrusters 35 kg
```

Esperado: terça-feira (weekday 1); acentos/texto original preservados; decimal `52,5 kg`, `60% RM`, `35 kg`, ordem RX/scaled e formato de 15 minutos preservados semanticamente. Se parser não consegue representar qualquer trecho sem perda, preview marca revisão necessária e bloqueia confirmar até correção explícita.

Evidência focal (23/10/2026): `WodPasteParserTests.test_w05_decimal_rx_scaled_source_is_structured_without_normalizer` e `WorkoutSmartPasteFlowTests.test_w05_decimal_rx_scaled_source_is_structured_without_normalizer` passaram. O parser determinístico preserva `52,5 kg`, `60% RM`, `35 kg`, reps, rounds e a flag Scaled; o endpoint persiste a estrutura sem chamar provider. A combinação de avisos dos parsers também permanece coberta. A fixture HTTP foi ampliada até confirmação explícita e distribuição de uma aula de terça-feira; uma execução em PostgreSQL 15 descartável com migrations reais passou 1/1 e comprovou as cargas e a marca Scaled nos movimentos projetados. Isso não prova a semântica de um provider externo.

### W-06 — dia ausente e dia duplicado

```text
Segunda
WOD AMRAP 10 min
8 burpees

Quinta-feira
WOD EMOM 12 min
```

Esperado: só segunda e quinta têm programação; os outros dias não recebem WOD inferido. Se a mesma entrada trouxer duas seções de segunda, preview mantém ambas visíveis e retorna conflito `duplicate_weekday`; não mescla nem escolhe silenciosamente, e não persiste uma semana confirmável até o autor resolver.

Evidência focal (23/10/2026): `WodPasteParserTests.test_w06_keeps_only_explicit_weekdays_and_does_not_infer_missing_days` e `WorkoutSmartPasteFlowTests.test_w06_weekly_contract_persists_only_explicit_weekdays` garantem apenas weekdays 0/3, AMRAP e EMOM preservados, sem provider; a regressão de duplicidade `test_duplicate_weekday_remains_editable_and_cannot_be_confirmed` mantém ambas as seções visíveis e impede confirmação. Parser 6/6; os dois fluxos HTTP passaram 2/2 em PostgreSQL descartável com migrations reais. O ensaio achou e corrigiu dois perdas de semântica no caminho freeform: aliases com hífen e cabeçalhos `WOD EMOM/AMRAP N min`.

### W-07 — corpus fixo de uma semana completa

```text
Segunda
WOD AMRAP 10 min
8 burpees

Terça
Força
Deadlift 3x5 60%
WOD For time 12 min
10 push up

Quarta
WOD EMOM 10 min
6 power snatch 40 kg

Quinta
WOD AMRAP 9 min
10 box jump

Sexta
Força
Back squat 3x5 70%
WOD For time 14 min
12 wall balls 9 kg

Sábado
WOD AMRAP 12 min
8 lunges

Domingo
Mobilidade
8 min flow de quadril
```

Esperado: exatamente sete dias, em ordem de segunda a domingo (weekdays `0..6`), sem dia inferido ou duplicado e sem warning de parser. Cargas, séries/repetições, timecaps e rótulo de mobilidade permanecem representados. A modalidade/programa é selecionada explicitamente no composer: com `P-HY` e `P-CF` compartilhando `ClassType=cross`, escolher `P-HY` nunca pode enviar a semana a sessões `P-CF`. O texto não é fonte de inferência de programa. A seleção e o escopo de destinos são revisados antes da confirmação; o preview não grava e a confirmação não publica além da política do box.

Evidências locais: `WodPasteParserTests.test_w07_fixed_seven_day_week_has_all_weekdays_and_no_warnings` valida a estrutura (arquivo parser 7/7); `WorkoutSmartPasteFlowTests.test_w07_full_week_persists_every_explicit_weekday_without_normalizer` valida POST, persistência do texto e dos sete dias e ausência de chamada ao normalizador (1/1, PostgreSQL com migrations reais). `WodProjectionTests.test_full_week_projection_only_targets_selected_program_with_shared_class_type` envia um payload de sete dias à prévia e projeção do serviço com sete pares de sessões P-HY/P-CF que compartilham `ClassType=cross`; a prévia e a gravação selecionaram apenas os sete destinos P-HY. `tests/test_wod_projection.py` + `tests/test_wod_projection_concurrency.py` passaram 17/17 em PostgreSQL com migrations reais. Parser, persistência HTTP e projeção de serviço são evidências separadas; ainda não são uma única navegação HTTP de parse até projeção. A desambiguação também continua coberta pelos casos M-01–M-04 e seus testes de fluxo.

## Corrida e confirmação

| ID | Preparação | Resposta esperada | Persistência |
|---|---|---|---|
| C-01 | Duas abas leem versão 7; ambas salvam `expected_version=7` | Uma recebe v8; outra `409 stale_version` | Segunda não sobrescreve a primeira |
| C-02 | Preview lista S-101 sem WOD; concorrente cria WOD | `409 stale_preview` | Nenhum outro destino é parcialmente aplicado |
| C-03 | Preview seleciona P-CF; aula troca para P-HY | `409 stale_preview` | Nenhuma escrita |
| C-04 | Mesmo `intent_id` e fingerprint repetidos após resposta perdida | Replay da resposta original | Só uma alteração |
| C-05 | Reusar `intent_id` com outro conteúdo/programa/data | `409 idempotency_key_reused` | Nenhuma nova escrita |
| C-06 | Falha no destino N de lote com N+1 destinos | Erro reconhecível | Rollback integral |
| C-07 | Mesmo idempotency key/fingerprint semanal | Replay do `ReplicationBatch` | Sem duplicar `SessionWorkout` |
| C-08 | Mesma chave semanal com fingerprint diferente | Conflito | Batch original íntegro |
| C-09 | Plano revisado depois do preview | `409 stale_preview` | Versão mais nova preservada |

Evidência focal (23/10/2026): C-06 passou em PostgreSQL descartável com migrations reais por `WodProjectionTests.test_failure_on_later_destination_rolls_back_the_whole_distribution_batch`: falha simulada na segunda submissão deixou zero `ReplicationBatch` e zero `SessionWorkout` nos dois destinos.

C-09 passou em PostgreSQL descartável com migrations reais por `WodProjectionTests.test_plan_revision_after_preview_rejects_the_old_confirmation_fingerprint`: editar `parsed_payload` pelo writer versionado após emitir a prévia incrementou a revisão; o fingerprint antigo foi rejeitado, a revisão nova permaneceu e nenhum lote/WOD foi criado.

### Evidência por ID — corrida e confirmação

| ID | Teste executado | Evidência focal |
|---|---|---|
| C-01 | `test_two_tabs_updating_one_draft_have_one_winner` | 1 gravação vence; a concorrente recebe `stale_version`; versão final 2. |
| C-02 | `WodApplyIntentTests.test_weekly_new_workout_after_preview_rejects_stale_fingerprint` | WOD concorrente permanece e o segundo destino não recebe escrita parcial; fingerprint stale e sem batch novo. |
| C-03 | `WodApplyIntentTests.test_weekly_program_change_after_preview_rejects_stale_fingerprint` | Troca de programa invalida a prévia; dois destinos conferidos, nenhuma escrita parcial. |
| C-04 | `WodApplyIntentTests.test_daily_targets_one_program_preserves_completed_and_replays` | Mesmo intent/fingerprint retorna replay, com um único efeito. |
| C-05 | `WodApplyIntentTests.test_daily_targets_one_program_preserves_completed_and_replays` | Mesmo intent com fingerprint diferente retorna `409 idempotency_key_reused`. |
| C-06 | `WodProjectionTests.test_failure_on_later_destination_rolls_back_the_whole_distribution_batch` | Falha no segundo destino reverte batch e workouts (executado separadamente; ver acima). |
| C-07 | `WodApplyIntentTests.test_weekly_token_targets_program_and_replays_batch` | Replay retorna o mesmo `ReplicationBatch`, sem duplicar workout. |
| C-08 | `WodProjectionTests.test_idempotency_key_cannot_be_reused_for_another_target_week` | Reuso para outra semana é recusado; batch original continua único. |
| C-09 | `WodProjectionTests.test_plan_revision_after_preview_rejects_the_old_confirmation_fingerprint` | Revisão após prévia invalida fingerprint; conteúdo novo persiste sem distribuição. |

Em 23/10/2026, os arquivos completos `tests/test_wod_apply_intents.py`, `tests/test_wod_projection.py` e o teste concorrente C-01 passaram **29/29** em PostgreSQL descartável com migrations reais. C-06 passou 1/1 em execução focal anterior. Os resultados provam esses casos automatizados, não todo WOD, ACL, isolamento multi-tenant ou provider real.

## Limites e cadência de autosave (A3)

| Limite | Contrato | Verificação |
|---|---|---|
| Texto de rascunho | Até 20.000 caracteres inclusive; acima retorna HTTP `413 draft_too_large` sem persistir | `WodApplyIntentTests.test_draft_size_boundary_and_http_status` |
| Rascunhos ativos | Até 20 por autor no schema/box corrente; o 21º é recusado com `draft_quota` | `WodApplyIntentTests.test_active_draft_quota_is_per_author_and_box` |
| Expiração | 30 dias desde a última gravação confirmada; atualizar renova a janela | `WodApplyIntentTests.test_draft_expiration_is_sliding_for_thirty_days` |
| Frequência de autosave | 90 saves em 300 s; a tentativa 91 recebe HTTP `429 rate_limited` e `Retry-After: 300`. Descarte não consome a quota | `WodApplyIntentTests.test_save_rate_limit_has_exact_window_and_retry_after` e `test_discard_remains_available_when_save_rate_limit_is_exhausted` |

No navegador e no servidor, comprimento conta pontos de código Unicode. O debounce de 800 ms evita gravação por tecla; o throttle do servidor é a proteção independente para tentativas concorrentes/malformadas.

## Programa, estado e ACL

| ID | Ação | Resultado esperado |
|---|---|---|
| M-01 | Preview diário escolhe P-CF com P-HY no mesmo `class_type=cross` | Só P-CF é elegível |
| M-02 | Preview diário escolhe P-HY | Só P-HY; compatibilidade de bloco usa `allowed_block_kinds` |
| M-03 | Preview diário escolhe P-YG (`other`) | Seleção por FK de programa; não converter slug em `ClassType` |
| M-04 | Payload legado envia `class_type=cross` | Adapter preserva alcance por tipo e identifica que não escolheu um programa |
| M-04a | Entrada nova especifica apenas `ClassType=cross` quando há P-CF e P-HY | `409 ambiguous_legacy_scope` (ou validação bloqueante antes de preview); exigir seleção explícita de programa |
| M-05 | Programa/template inativo ou arquivado ao confirmar | Conflito/entrada inválida reconhecível, sem mutação |
| M-06 | Destino `completed` ou `canceled` | Jornada nova retorna `skipped_completed`/`skipped_canceled`; não altera WOD; se mudar depois da prévia, confirmação stale |
| M-07 | WOD existente draft em `replace_empty` | Preservado, com skip explicado |
| M-08 | WOD published/pending/rejected em `overwrite` | Sem overwrite ou reset de aprovação; skip explicado |
| A-01 | Coach aplica à própria aula e template próprio | Permitido, respeitando policy de publicação |
| A-02 | Coach tenta aula alheia ou template alheio | Negado (`403`/`404` conforme proteção de existência), sem mutação |
| A-03 | Manager usa Smart Paste/apply e tenta editor individual | Paste/apply permitido; editor bloqueado |
| A-04 | Owner usa as três superfícies | Permitido conforme policy do box |
| A-05 | Intent pertence a outro usuário/schema | Não revelar existência nem reproduzir resultado |

Evidência ACL (23/10/2026): nove testes focais passaram em PostgreSQL descartável com migrations reais, cobrindo Coach (aula/template próprio e bloqueio em recurso alheio), Manager (Smart Paste e aplicação diária permitidos, editor individual bloqueado) e Owner (editor, Smart Paste e aplicação diária permitidos); plano semanal de outro autor responde 404. O caso `test_daily_intent_from_another_tenant_schema_is_not_replayed` passou 1/1 com dois schemas e UUID de intent coincidente: confirmação no schema A retorna `not_found`, sem alterar estado/resposta da intent em B. Isso cobre A-01–A-05 no nível do intent e das superfícies exercitadas; ainda não prova todas as ações/rotas do planner nem isolamento de todas as entidades.

Complemento de privacidade do draft semanal (23/10/2026): `WodApplyIntentTests.test_manager_cannot_read_or_update_coachs_weekly_draft` confirma que um Manager pode abrir seu próprio escopo semanal, mas recebe draft vazio quando o Coach salvou texto na mesma semana/programa; tentar salvar usando o UUID e versão do Coach retorna `draft_missing` e não altera texto nem versão. A classe `tests/test_wod_apply_intents.py` passou 18/18 em PostgreSQL descartável com migrations reais. Esta evidência é isolamento por autor dentro do tenant, além do isolamento por schema já exercitado para intents.

Complemento cross-schema HTTP A-05 (23/10/2026): `test_weekly_draft_routes_do_not_read_or_mutate_another_tenant_schema` usa o mesmo autor, semana e PK de programa nos schemas A/B, cria plano e draft somente em B e chama a rota real com o tenant A selecionado. GET em A não revela texto, `plan_id` de B retorna `404 scope_not_found`, e POST com UUID/versão do draft de B retorna `409 draft_missing`; o estado e o texto em B permanecem intactos e continuam legíveis ao selecionar B. O teste passou isoladamente e, junto ao módulo `tests/test_wod_confirmation_concurrency.py`, passou **15/15** em PostgreSQL 15 descartável com migrations reais. Prova de isolamento das rotas weekly draft no par sintético, não de todas as entidades WOD.

Complemento de privacidade do draft semanal (23/10/2026): `WodApplyIntentTests.test_manager_cannot_read_or_update_coachs_weekly_draft` confirma que um Manager pode abrir seu próprio escopo semanal, mas recebe draft vazio quando o Coach salvou texto na mesma semana/programa; tentar salvar usando o UUID e versão do Coach retorna `draft_missing` e não altera texto nem versão. A classe `tests/test_wod_apply_intents.py` passou 18/18 em PostgreSQL descartável com migrations reais. Esta evidência é isolamento por autor dentro do tenant, além do isolamento por schema já exercitado para intents.

Evidência M-01–M-08 (23/10/2026): diário selecionado por `WorkoutProgram` exclui programa vizinho com o mesmo `ClassType`, enquanto adapter legado segue por `ClassType`; destino concluído/cancelado é excluído e aula concluída é preservada na confirmação; `replace_empty` preserva WOD existente e `overwrite` preserva `published`, `pending_approval` e `rejected`. Projeção semanal ignora canceladas. M-05 recebeu testes de stale preview para programa desativado e template arquivado: ambos retornam conflito sem mutação. Os novos testes M-05/M-08 passaram 3/3 junto da regressão de estados; as demais assertions constam nos casos focais e evidências anteriores deste corpus. O inventário precisa continuar distinguindo prévia de confirmação: M-05 do caminho novo já bloqueia o stale, mas outros handlers legados ainda devem ser verificados por ação.

Evidência M-04a (23/10/2026): `DayApplyFlowTests.test_program_preview_rejects_ambiguous_class_type_only_scope` envia `ClassType=cross` para a rota nova de prévia enquanto duas trilhas `WorkoutProgram` compartilham esse tipo, mas omite o ID de programa. A validação exige `workout_program_id`, retorna HTTP 400 `invalid_payload` e não cria nenhum WOD; o endpoint legado permanece explicitamente separado. O teste passou 1/1 em PostgreSQL descartável com migrations reais.

Evidência M-06 (23/10/2026): `WodApplyIntentTests.test_daily_targets_one_program_preserves_completed_and_replays` inclui aula cancelada na prévia e confirmação: ela aparece como `skipped_canceled` e não recebe WOD. `test_daily_cancellation_after_preview_blocks_entire_batch` confirma que cancelar uma aula depois da prévia retorna `409 stale_preview`, sem escrita. No semanal, `test_weekly_cancellation_after_preview_rejects_stale_fingerprint` também rejeita o fingerprint antigo e não cria batch/WOD. `tests/test_wod_apply_intents.py` passou 20/20 em PostgreSQL descartável com migrations reais.

### Planner legado — rotas, ACL e efeitos

| Ação | ACL e filtro | Efeito confirmado no código |
|---|---|---|
| `workout-planner` (GET) | Coach, Manager, Owner; Coach vê aulas próprias, Manager/Owner escopo do box | Leitura da semana e painel; sem mutação |
| Aplicar template confiável ao slot | Owner/Manager; template ativo e `is_trusted`; qualquer aula do box | Submete via policy de aprovação vigente |
| Duplicar slot da semana anterior | Coach/Owner; Coach só aula própria | Cria cópia em draft; agora exige mesmo `WorkoutProgram` se a aula-alvo o tiver, fallback por `ClassType` só para alvo legado sem programa |
| Excluir WOD selecionado / limpar semana | Coach/Manager/Owner; Coach limitado às próprias aulas; Manager/Owner escopo do box | Hard-delete de `SessionWorkout`, qualquer estado. São comandos destrutivos separados de `overwrite`; a confirmação atualmente é apresentada pela UI antes do POST. |

Em 23/10/2026, `tests/test_workout_planner_builders.py` passou **27/27** em PostgreSQL descartável com migrations reais. Inclui Manager aplicando template confiável, Coach recusado nessa rota, limites de remoção por Coach, Owner duplicando slot e a regressão de programa: uma fonte da semana anterior de outra modalidade não é copiada. Esta cobertura valida os handlers do planner; não é auditoria de todas as rotas de gerenciamento/arquivamento de templates.

### Gerenciamento de templates — ACL por autor

- Management: Coach vê apenas templates próprios; Owner vê o catálogo do box; Manager não tem acesso à tela.
- Policy de aprovação e archive-all: Owner. Archive/restore, duplicate/delete, metadata, ativação/destaque e operações de bloco/movimento: Coach/Owner, com Coach restrito aos templates próprios (incluindo a propriedade herdada por bloco/movimento).
- A inspeção descobriu que archive/restore aceitavam Coach mas não validavam autoria. Os dois handlers agora rejeitam a mutação de template alheio com mensagem de autorização; Owner continua abrangente. `tests/test_wod_template_archive.py` passou **14/14** em PostgreSQL descartável com migrations reais, incluindo regressões de Coach próprio/alheio, restore, archive-all e confirmação explícita. Um teste HTTP adicional tentou as 13 rotas de duplicate/delete/toggle/metadata e operações filhas; as alterações do template alheio foram bloqueadas e o estado inteiro permaneceu intacto (**1/1**).

O teste agregado percorre cada rota filha individualmente; policy de aprovação permanece coberta pelo seu teste Owner-only.

## Invariantes de compatibilidade

- App do aluno mostra apenas WOD publicado; rascunho/preview/intent não aparecem. Preservar `workout.version` na chave de cache e snapshots.
- Confirmação passa por `route_workout_submission()` e policy do box; não publica diretamente nem contorna aprovação.
- Cada alteração lógica incrementa `SessionWorkout.version`; rollback/replay não cria revisão falsa nem repete escrita.
- Estado de batch/intent é tenant-local; PK igual em schemas distintos não cruza resultado ou undo.
- Texto é dado não confiável: escapar na UI e não registrar conteúdo em logs.
- Undo de 60 s continua condicionado ao snapshot; sua expiração não encerra idempotência.

## Dependências para executar

1. PostgreSQL de teste com duas conexões/barreiras para concorrência, CAS, rollback e unicidade. SQLite ou execução sequencial não prova isso.
2. Duas `WorkoutProgram` no mesmo tenant com `class_type=cross` e sessões ligadas explicitamente. Reproduzido em diário e semanal: jornada A4 seleciona somente a trilha escolhida; compatibilidade legada diária inclui ambas por tipo.
3. Roles Coach, Manager e Owner; dois schemas com IDs locais coincidentes.
4. Policy `strict` e `trusted_template` nas fixtures.
5. Provider normalizador substituível por fake de sucesso, timeout e indisponibilidade. Nenhum segredo real é necessário ao corpus determinístico.

## Status A1

Corpus preparado em 23/10/2026 sobre a baseline `a2ab398f5774b609b979a31c00527bc88b64b1fb`. Casos executados e limites atuais estão discriminados por teste no subplano; este documento continua sendo contrato de aceite, não declaração de execução integral. Os casos restantes exigem a cobertura e os gates explicitamente indicados acima.

Evidência cross-schema do planner legado (23/10/2026): `test_workout_planner_actions_do_not_touch_another_tenant_schema` cria sessão e WOD exclusivos do schema B e seleciona A na sessão HTTP. Duplicar slot anterior e excluir por sessão respondem 404; limpar a semana em A redireciona normalmente e preserva o WOD B. Manager envia `session_id` de B à telemetria do picker: recebe 204 sem criar evento em A. A view valida sessão no schema ativo e template ativo/não arquivado antes de emitir telemetria. A rota trusted-template foi chamada com sessão B/template A e sessão A/template B; ambas retornam 404, sem WOD em A e sem alteração do template/bloco em B. O teste passou **1/1** em PostgreSQL descartável com migrations reais. A cobertura é desses seis cenários de rota e do par de schemas criado pelo teste; não afirma isolamento de todas as rotas/entidades do planner.

Evidência de saída segura do WOD (23/10/2026): `StudentAppExperienceTests.test_student_wod_escapes_pasted_markup_and_omits_unsafe_movement_urls` renderiza campos estruturados persistidos contendo `<script>`, `<img onerror>`, `<svg onload>` e iframe, além de URLs `javascript:` e `data:` introduzidas diretamente no catálogo. O HTML escapa os campos de texto e não cria links com esses schemes; URLs HTTP/HTTPS válidas continuam disponíveis para referência e demonstração. A camada de leitura `movement_references` valida schemes HTTP(S) para as duas URLs antes de expor dados ao snapshot do aluno. Teste focal passou **1/1** em PostgreSQL descartável com migrations reais. A execução confirma a renderização do aluno; prévia real em browser e segurança do provider permanecem gates separados.

Evidência de prévia/diff hostil (23/10/2026): `WorkoutSmartPasteFlowTests.test_smartplan_preview_escapes_hostile_source_diff_and_reason` envia colagem com `<script>` e injeta no resultado simulado do normalizador texto `<img onerror>` e motivo contendo `javascript:`. A resposta HTML do preview mantém os valores como texto escapado, sem criar tags executáveis. Passou **1/1** em PostgreSQL descartável com migrations reais. O teste isola o contrato server-side e não chama provider; a validação do provider real e browser continuam pendentes.

Evidência de fronteira do normalizador (23/10/2026): a regressão de timeout agora inclui instrução hostil e URL `https://attacker.invalid/collect`. A chamada simulada permanece um único POST para o endpoint fixo da Anthropic, envia a colagem como string JSON não confiável e mantém a instrução de sistema de tratar o conteúdo como dado. O timeout preserva o texto e bloqueia distribuição. `WorkoutSmartPasteFlowTests.test_provider_timeout_preserves_source_and_blocks_distribution` passou **1/1** em PostgreSQL descartável; o mock impede qualquer tráfego externo. Isso verifica a construção do request e a ausência de fetch da URL nesse caminho, não resistência empírica a prompt injection no modelo real.

Evidência do diff de aprovação (23/10/2026): `WorkoutApprovalBoardTests.test_approval_board_renders_diff_against_last_published_revision` passou a inserir HTML hostil em título, notas, bloco e movimento, confrontando uma revisão publicada anterior. A resposta da board contém as strings escapadas e não contém as tags executáveis literais. Teste focal passou **1/1** em PostgreSQL descartável com migrations reais. Assim, preview Smart Paste, diff de aprovação e WOD do aluno têm cobertura server-side; o provider real e QA visual continuam separados.
