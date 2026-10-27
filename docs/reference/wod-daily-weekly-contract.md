# Contrato dos fluxos diário e semanal de WOD

**Status:** contrato extraído em 26/10/2026 para P01 sobre `main` (`096edb0b`). A validação desta branch está em [validação P01](../testing/pr-p01-validation-2026-10-26.md).

**Autoridade:** contrato atual de rotas, ACL, estados e gravação. Em caso de diferença, conferir primeiro o código apontado e atualizar esta referência junto com a mudança. O corpus abaixo especifica exemplos e expectativas; seus cenários não são todos evidência de execução.

**Fonte complementar:** [corpus de entrada e aplicação WOD](../testing/wod-input-contract-corpus.md). Os planos C.O.R.D.A., inventários de privacidade e revisão transversal do checkout combinado serão publicados nos respectivos pacotes de documentação e privacidade.

## Rotas e autorização

| Superfície | Rota Django / URL | Papéis | Escopo e observação |
|---|---|---|---|
| Editor individual | `coach-session-workout-editor` — `/operacao/coach/aula/<session_id>/wod/` | Coach, Owner | Coach só abre aula atribuída a ele; a view resolve a sessão antes do editor. Manager não usa este editor. |
| Smart Paste semanal | `workout-smart-paste` — `/operacao/wod/paste/` | Coach, Manager, Owner | `plan_id` é carregado somente quando `created_by=request.user`. Manager não lê plano de Coach. |
| Rascunho recuperável | `wod-input-draft` — `/operacao/wod/rascunho/` | Coach, Manager, Owner | A rota exige sessão autenticada. Escopo diário restringe a Coach/Owner; escopo semanal admite os três papéis. Autor, Box, sessão, plano e programa são resolvidos no servidor. |
| Aplicação diária legada | `wod-day-apply-preview`, `wod-day-apply` — `/operacao/wod/planner/dia/conferir/`, `/operacao/wod/planner/dia/aplicar/` | Coach, Manager, Owner | Escopo por data + `ClassType`; Coach limitado às próprias aulas e a template de sua autoria. A prévia não cria um recibo vinculado à confirmação. |
| Aplicação diária nova | `wod-day-program-preview`, `wod-day-program-confirm` — `/operacao/wod/planner/dia/programa/conferir/`, `/operacao/wod/planner/dia/programa/confirmar/` | Coach, Manager, Owner | Exige `WorkoutProgram` ativo explícito. Coach limitado às próprias aulas e a template de sua autoria. Confirmação é vinculada ao autor e à intenção preparada. |
| Undo diário | `wod-day-apply-undo` — `/operacao/wod/planner/dia/desfazer/` | Coach, Manager, Owner | Undo complementar usa dados em cache com janela de 60 segundos; não é a confirmação durável da aplicação. |

Os handlers diários estão em [workout_day_apply_views.py](../../operations/workout_day_apply_views.py); os endpoints de editor e draft ficam em [workout_editor_views.py](../../operations/workout_editor_views.py) e [workout_draft_views.py](../../operations/workout_draft_views.py).

## Fonte de verdade e recuperação

- `WodInputDraft` é buffer de texto recuperável por autor e escopo, separado do WOD por aula e do plano semanal. O código limita o texto a 20.000 caracteres, mantém até 20 rascunhos ativos por autor/tenant e renova `expires_at` em 30 dias a cada save. A limpeza efetiva depende do comando/timer instalado e executado.
- `WeeklyWodPlan.source_text` e `parsed_payload` são a autoria persistente do plano semanal e da leitura estruturada. O plano tem `revision` e estado `draft`/`confirmed`; não tem TTL atualmente. A retenção e o envio condicional do texto a provider estão detalhados no inventário de conteúdo.
- `SessionWorkout` é o WOD pertencente à aula. A confirmação semanal registra um `ReplicationBatch`; `SessionWorkout.replication_batch` é opcional e usa `SET_NULL`. Não há FK de volta de `SessionWorkout` a `WeeklyWodPlan`.

## Aplicação diária por programa

1. A prévia resolve template ativo/não arquivado, programa ativo e aulas do dia com `workout_program_id` exatamente igual ao programa escolhido. O snapshot também inclui versão/estado do WOD presente e política de aprovação de cada aula.
2. `prepare_program_apply()` cria `WodApplyIntent` do autor com snapshot, fingerprint e expiração de 30 minutos. O fingerprint cobre o escopo e os dados relevantes da prévia.
3. `confirm_program_apply()` trava a intenção e os registros usados, exige mesmo autor e fingerprint, recompõe o snapshot e rejeita mudanças com `409 stale_preview`. Uma intenção já confirmada devolve o payload persistido com `idempotent_replay=true`, sem criar outro WOD.
4. A confirmação usa transação e caminho compartilhado de aplicação. `replace_empty` preserva qualquer WOD existente; `overwrite` só substitui WOD em `draft` e preserva `pending_approval`, `published` e `rejected`. Aulas `completed` e `canceled` são preservadas e reportadas como ignoradas.
5. O token de undo é complementar e temporário. A confirmação permanece registrada em `WodApplyIntent`; o estado necessário para desfazer depende do cache por 60 segundos. Se o cache falha após o commit, a resposta durável indica undo indisponível.

Implementação: [wod_preview_contracts.py](../../operations/services/wod_preview_contracts.py), [wod_apply_intents.py](../../operations/services/wod_apply_intents.py) e [wod_day_apply_executor.py](../../operations/services/wod_day_apply_executor.py). Persistência: `WodApplyIntent` em [student_app/models.py](../../student_app/models.py).

## Aplicação diária legada por `ClassType`

O adapter legado continua intencionalmente separado: consulta aulas `scheduled`, `open` e `completed` pela data e `ClassType`; se dois `WorkoutProgram` compartilham o tipo, ambos podem entrar no alcance. A rota de prévia mostra o alcance, mas a execução não usa `WodApplyIntent` nem valida um fingerprint entre prévia e escrita. O executor legado não ativa `skip_completed`; portanto, mantém o comportamento anterior para aulas concluídas. Canceladas não entram na consulta.

Manter esse caminho por compatibilidade enquanto clientes legados o usarem. Mudanças futuras de alcance ou tratamento de aulas concluídas precisam migrar o consumidor para a rota por programa ou versionar explicitamente o contrato.

## Plano semanal e projeção

1. Smart Paste salva texto original e payload estruturado no `WeeklyWodPlan`; erros de parsing bloqueiam a confirmação, e itens podem ser revisados antes dela. Normalizador externo é opcional; sua falha não deve confirmar conteúdo incompleto.
2. `save_weekly_plan_revision()` atualiza apenas se `revision` ainda for a esperada e incrementa o contador no mesmo `UPDATE`. Conflito entre abas é apresentado como revisão desatualizada. A view também valida versão enviada para revisão/confirmação.
3. `confirm_plan` confirma o plano. `confirm_and_project` prepara e mostra uma prévia da semana, mas ainda não distribui. Prévia e gravação da projeção são ações posteriores separadas.
4. A UI exige plano `confirmed`, autor correspondente, semana/tipos selecionados e token assinado da prévia. O token liga ator, plano, semana, tipos, UUID de intenção e fingerprint dos destinos/política.
5. Ao distribuir, o serviço trava plano, programa, estrutura, aulas e WODs existentes; recompõe preview/fingerprint e recusa estado stale. A rota Smart Paste passa explicitamente `exclude_completed=True`: aulas canceladas, concluídas, sem dia no plano ou com WOD existente são ignoradas; só entradas `ready` criam `SessionWorkout`. Se houver movimentos sem compatibilidade validada ou vídeo de referência, o POST também exige o aceite explícito da UI.
6. `ReplicationBatch.idempotency_key` é único. Replay da mesma chave e requisição/autor devolve o lote anterior; chave de outro autor ou com fingerprint incompatível é recusada. Depois do commit, a view monta uma prévia pós-escrita para não apresentar o mesmo destino como novamente pronto.
7. Undo semanal atua no `ReplicationBatch` escolhido pelo plano carregado pelo autor, não no undo cache diário.

Implementação: [workout_board_views.py](../../operations/workout_board_views.py), [wod_weekly_revision.py](../../operations/services/wod_weekly_revision.py), [wod_projection.py](../../operations/services/wod_projection.py) e modelos `WeeklyWodPlan`, `ReplicationBatch` e `SessionWorkout` em [student_app/models.py](../../student_app/models.py).

### Modalidade e compatibilidade semanal

Quando `WeeklyWodPlan.workout_program_id` existe, o filtro de destino semanal usa esse FK; o `ClassType` selecionado não deve ampliar a distribuição para outro programa. Isso permite que dois programas customizados compartilhem `ClassType=cross`. Plano legado sem FK usa o filtro de `ClassType` como fallback. Não converter slug/nome de modalidade customizada em `ClassType` para inferir programa.

**Decisão de callsite:** `build_projection_preview()` e `project_plan_to_sessions()` mantêm `exclude_completed=False` como default de serviço; o fluxo novo da UI passa `True` explicitamente. O inventário local encontrou quatro chamadas de preview e uma de projeção na view Smart Paste, todas explícitas, além de chamadas diretas de teste e um uso em `student_app/tests.py` sem aula concluída na fixture. Mantemos a diferença explícita para não mudar silenciosamente o comportamento de chamadas diretas; isso não declara o serviço como API externa estável. Ao adicionar um novo callsite de produto, informar o valor deliberadamente.

## Mapa de validação

Os resultados históricos do checkout combinado não validam esta branch extraída.
Consultar [validação P01](../testing/pr-p01-validation-2026-10-26.md) para comandos,
resultados e limites desta entrega. O [corpus](../testing/wod-input-contract-corpus.md)
define expectativas; não implica execução integral de cada cenário.

- Diário: `tests/test_wod_day_apply_flow.py`, `tests/test_wod_apply_intents.py`.
- Semanal e concorrência: `tests/test_wod_projection.py`, `tests/test_wod_projection_concurrency.py`, `tests/test_wod_confirmation_concurrency.py`.
- Parser, revisão e ACL: `tests/test_workout_smart_paste.py`.
- Recuperação e isolamento de draft: `tests/test_wod_confirmation_concurrency.py`.

P02 acrescenta testes de browser e workflow Chromium/WebKit. Piloto com coaches,
iPhone físico, provider real e ativação de limpeza continuam gates separados.
