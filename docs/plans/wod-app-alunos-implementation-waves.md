<!--
ARQUIVO: plano de implementacao em ondas para o circuito WOD + app do aluno.

POR QUE ELE EXISTE:
- consolida em um unico documento as ondas de entrega que cobrem import de alunos, push, WhatsApp, PR workflow e challenge foundation.
- evita reescrita do escopo a cada nova conversa e mantem ordem de execucao explicita.
- registra a arquitetura real adotada (sem vocabulario que nao existe no codigo).

O QUE ESTE ARQUIVO FAZ:
1. fixa as decisoes arquiteturais que valem para todas as ondas.
2. detalha cada onda com objetivo, arquivos tocados, estado machine quando aplicavel, testes e criterio de done.
3. registra o fix paralelo de teste pre-existente que nao bloqueia ondas.
4. define a ordem de execucao recomendada.

TIPO DE DOCUMENTO:
- plano de execucao por ondas

AUTORIDADE:
- alta para o escopo das ondas listadas

DOCUMENTO PAI:
- [../architecture/architecture-growth-plan.md](../architecture/architecture-growth-plan.md)

QUANDO USAR:
- quando houver duvida sobre ordem de entrega, escopo de cada onda ou criterio de done.
- quando uma feature nova for proposta e precisar ser encaixada na trilha atual.

PONTOS CRITICOS:
- ondas sao incrementos atomicos de PR; nao quebrar uma onda no meio sem motivo claro.
- novos modelos nao nascem em boxcore; o pattern model_definitions/re-export so vale para dominios migrando para fora de boxcore.
- adapter externo (WhatsApp, push) e modulo fino, sem regra de negocio.
- toda notificacao precisa nascer com auditoria e fallback de canal.
-->

# Ondas de implementacao — WOD + app do aluno

## Regra de autoridade deste documento

1. este documento define a sequencia de ondas e o contrato de cada uma.
2. a arquitetura geral do projeto continua governada por [architecture-growth-plan.md](../architecture/architecture-growth-plan.md) e [domain-model-ownership-matrix.md](../architecture/domain-model-ownership-matrix.md).
3. o design system continua governado por [design-system-contract.md](../map/design-system-contract.md) e [css-guide.md](../experience/css-guide.md).

## Decisoes arquiteturais que valem para todas as ondas

1. **Modelo novo em app dono.** Nada de boxcore. O pattern `model_definitions.py -> models.py re-export` so vale para dominios em transicao (students, finance, operations, communications, auditing, onboarding). Modelos novos nativos vao direto em `<app>/models.py`. Referencia: `student_app/models.py` ja tem `StudentExerciseMax` nesse formato.
2. **Side effects via signal + listener.** Disparo nasce no signal do model alvo, listener no app dono da reacao. Referencia: `student_app/signals.py` e `student_identity/listeners.py`.
3. **Adapter externo fino.** Push e WhatsApp sao modulos sem regra de negocio. Recebem contexto de dominio, delegam ao canal, registram auditoria. Referencia: `student_identity/push_notifications.py`.
4. **Background jobs.** Toda execucao assincrona usa `shared_support/background_jobs.py`. O store atual e Redis + threading; a interface e Celery-swap-ready.
5. **Auditoria desde o inicio.** Cada disparo de canal (push ou WhatsApp) emite evento auditavel com origem, destino, template e resultado.
6. **Fallback de canal.** Falha de WhatsApp nao derruba push e vice-versa. Listener chama os dois canais de forma independente.

## Onda 0 — Botao de import em configuracoes operacionais (FEITO)

### Objetivo
Expor a UI de import de alunos em CSV a partir da tela de configuracoes operacionais, reusando o pipeline ja pronto (`StudentImportView` + `StudentImportProgressView`).

### Arquivos tocados
- [templates/guide/operational-settings.html](../../templates/guide/operational-settings.html) — card `#operational-settings-student-import` adicionado antes do card de convites do app do aluno; form com `action="{% url 'student-import' %}"`.

### Wiring confirmado
- `catalog/urls.py` ja tem `alunos/importar/` e `alunos/importar/progresso/<job_id>/`.
- `catalog/views/student_views.py::StudentImportView` ja chama `StudentImporter` com `job_id` e redireciona para a tela de progresso.
- `operations/services/student_importer.py` ja emite progresso via `update_job_progress` com `failed_items[].line` no formato esperado pelo JS.
- `templates/catalog/import-progress.html` + `static/js/pages/catalog/import-progress.js` ja estao completos.

### Criterio de done
- Card visivel para owner e dev (papeis ja autorizados na `OperationalSettingsView`).
- Submit redireciona para a tela de progresso.
- Progresso atualiza em tempo real.

### Status
Concluido nesta sessao.

---

## Onda A — WhatsApp adapter e 6 eventos de notificacao

### Objetivo
Subir o canal WhatsApp como adapter fino reusavel e cobrir 6 eventos de ciclo de vida do aluno em push e WhatsApp.

### Estimativa
4 dias-PR.

### Eventos cobertos
| Evento                  | Push | WhatsApp |
|-------------------------|:----:|:--------:|
| Aula cancelada          |  X   |    X     |
| Cobranca vencida        |  X   |    X     |
| Matricula aprovada      |  X   |    X     |
| Congelamento aprovado   |  X   |    X     |
| Pagamento confirmado    |  X   |    X     |
| WOD do dia              |  X   |    -     |

### Arquivos tocados
- `student_identity/push_notifications.py` — adicionar `send_overdue_charge_push`, `send_enrollment_approved_push`, `send_freeze_approved_push`, `send_payment_confirmed_push`, `send_wod_today_push`.
- `student_identity/whatsapp_notifications.py` (NOVO) — wrapper sobre `communications/`. Interface: `send_whatsapp_notification(student, template_key, context_vars) -> bool`.
- `student_identity/listeners.py` — 5 handlers novos, um por evento.
- `student_identity/apps.py` — registrar listeners em `ready()`.
- `operations/signals.py` ou `finance/signals.py` — adicionar signals `enrollment_approved`, `charge_overdue`, `freeze_approved`, `payment_confirmed` no save dos models alvo ou no webhook Stripe correspondente.

### Contrato do `whatsapp_notifications.py`
```python
def send_whatsapp_notification(student, template_key, context_vars) -> bool:
    """Adapter fino. Recebe contexto de dominio, delega ao canal de communications/."""
    if not student.phone:
        return False
    # delega ao dispatcher existente
    # registra evento de auditoria com (student_id, template_key, channel='whatsapp', result)
    # nao propaga excecao; retorna False em falha
```

### Padrao de listener
```python
def _on_charge_overdue(sender, charge, **kwargs):
    send_overdue_charge_push(charge)            # tenta push
    send_whatsapp_notification(                  # tenta whatsapp em paralelo
        student=charge.student,
        template_key='charge_overdue',
        context_vars={...},
    )
```

### Testes obrigatorios
- 1 teste por par (canal x evento) = 11 testes minimos.
- Mocks: `pywebpush` e dispatcher WhatsApp do `communications/`.
- Casos de borda: aluno sem telefone, push subscription inexistente, falha de WhatsApp nao derruba push.

### Criterio de done
- 6 eventos disparam push quando aplicavel.
- 5 eventos disparam WhatsApp quando aplicavel.
- Auditoria registra cada disparo.
- Falha em um canal nao quebra o outro.

---

## Onda B — Eventos cron e webhook Stripe

### Objetivo
Cobrir notificacoes baseadas em tempo (nao em acao do usuario) e capturar falhas de pagamento via webhook.

### Estimativa
1.5 dias-PR.

### Eventos cobertos
| Evento                | Canal           | Frequencia         |
|-----------------------|-----------------|--------------------|
| WOD de amanha         | Push            | diario 20h         |
| Plano vencendo em N dias | Push         | diario 9h          |
| Aniversario do box    | Push (broadcast)| diario 8h          |
| Falha Stripe          | WhatsApp dono   | webhook em tempo real |

### Arquivos tocados
- `student_identity/cron_notifications.py` (NOVO) — 3 funcoes: `notify_tomorrows_wod`, `notify_expiring_plans(days_ahead)`, `notify_box_anniversaries`.
- `operations/management/commands/send_scheduled_notifications.py` (NOVO) — invoca as 3 funcoes com argumentos de data.
- `integrations/stripe_listeners.py` (NOVO) — handler do webhook `invoice.payment_failed`.
- `config/celery_beat.py` ou cron do sistema — registrar 3 tasks periodicas.

### Decisao tecnica
1. Sem framework de cron novo. Reusa o que ja existe.
2. Se o projeto ja tiver Celery beat configurado, usar.
3. Caso contrario, management command + cron do sistema (cron Linux ou Task Scheduler em dev).
4. O webhook Stripe usa `submit_background_job` para isolar o disparo de WhatsApp do request HTTP do Stripe.

### Testes obrigatorios
- Snapshot dos querysets de cada cron funcao (filtragem correta).
- Mock de `now()` com `freezegun` para validar janelas de horario.
- Webhook Stripe: assinatura invalida -> 401, payload valido -> dispara WhatsApp.

### Criterio de done
- Management command roda em dry-run com saida legivel.
- Webhook Stripe responde em <500ms (disparo real fica no background).
- Logs de execucao auditaveis.

---

## Onda C — PR Verification Workflow

### Objetivo
Implementar o fluxo social de validacao de PR em aula: aluno marca PR -> teaser anonimo ao coach -> coach decide -> turma vota -> resultado broadcast ou rejeicao privada.

### Estimativa
10.5 dias-PR.

### Arquivos tocados
- `student_app/models.py` — adicionar `PrVerificationState` (TextChoices) e `PrVerificationRequest` (TimeStampedModel).
- `student_app/services/pr_aggregator.py` (NOVO) — funcoes `submit_pr_for_verification`, `record_class_vote`, `close_session_prs`.
- `student_app/signals.py` — receiver para `ClassSession.status='closed'` chamando `close_session_prs`.
- `student_app/views/pr_views.py` (NOVO) — POST submit (aluno), POST coach_decide, POST class_vote.
- `student_app/urls.py` — 3 rotas novas.
- `student_app/migrations/0019_prverificationrequest.py`.
- `student_identity/pr_notifications.py` (NOVO) — `send_pr_teaser_push(coach)`, `send_pr_result_push(student)`, `send_pr_broadcast_push(box)`.
- `templates/student_app/pr/pr_teaser.html` (NOVO).
- `templates/student_app/pr/pr_vote.html` (NOVO).
- `templates/student_app/pr/pr_result.html` (NOVO).
- `templates/student_app/pr/pr_broadcast.html` (NOVO).
- `static/css/student_app/screens/pr-verification.css` (NOVO).
- `static/js/pages/student_app/pr-verification.js` (NOVO).

### Modelo
```python
class PrVerificationState(models.TextChoices):
    PENDING_TEASER = 'pending_teaser', 'Aguardando teaser'
    PENDING_COACH  = 'pending_coach',  'Aguardando coach'
    PENDING_CLASS  = 'pending_class',  'Votacao aberta'
    VERIFIED       = 'verified',       'Verificado'
    REJECTED       = 'rejected',       'Recusado'
    DISCARDED      = 'discarded',      'Descartado'

class PrVerificationRequest(TimeStampedModel):
    student          = FK(Student, on_delete=CASCADE)
    session          = FK(ClassSession, on_delete=CASCADE)
    exercise_max     = FK(StudentExerciseMax, on_delete=CASCADE)
    weight_kg        = DecimalField(max_digits=6, decimal_places=2)
    previous_best_kg = DecimalField(max_digits=6, decimal_places=2, null=True)
    state            = CharField(max_length=24, choices=PrVerificationState.choices)
    coach_decision   = CharField(max_length=16, null=True)
    coach_decided_at = DateTimeField(null=True)
    rejection_reason = CharField(max_length=255, blank=True)
    class_vote_yes   = IntegerField(default=0)
    class_vote_no    = IntegerField(default=0)
    broadcast_sent_at = DateTimeField(null=True)

    class Meta:
        constraints = [UniqueConstraint(
            fields=['student', 'session', 'exercise_max'],
            condition=~Q(state__in=['verified', 'rejected', 'discarded']),
            name='unique_active_pr_verification',
        )]
```

### Estado machine
```
[aluno salva PR no app]
        |
   sem historico anterior?
        |
        +-- sim --> REJECTED imediato (push privado ao aluno com motivo)
        |
        +-- nao --> PENDING_TEASER
                        |
                        v
                push anonimo ao coach
                        |
                        v
                PENDING_COACH (timeout 23h -> DISCARDED)
                        |
                        +-- coach reject --> REJECTED (push privado, sem nome)
                        |
                        +-- coach accept -> PENDING_CLASS (notifica turma)
                                                |
                                                v
                                        [aula encerra: signal session_closed]
                                                |
                                        ratio_yes >= 0.5 ?
                                                |
                                                +-- sim --> VERIFIED -> broadcast box-wide
                                                |
                                                +-- nao --> DISCARDED (silencioso)
```

### Regra de unicidade
1. Apenas 1 request ativo por `(student, session, exercise_max)`.
2. Se o aluno salvar 2 PRs do mesmo exercicio na mesma aula, o segundo substitui o primeiro (state reset para `PENDING_TEASER`).
3. A constraint parcial garante isso a nivel de banco.

### Regra de privacidade
1. Teaser ao coach nao revela o nome do aluno; mostra apenas turma e exercicio.
2. Rejeicao nao expoe o nome para a turma; o aluno recebe motivo em canal privado.
3. Broadcast so dispara apos `VERIFIED` e ai sim revela nome.

### Testes obrigatorios
- timeout 23h sem decisao do coach -> `DISCARDED` (usar `freezegun`).
- ratio de votos >= 0.5 -> `VERIFIED`.
- ratio < 0.5 -> `DISCARDED`.
- aluno sem historico de RM -> `REJECTED` imediato.
- broadcast nao dispara enquanto state nao for `VERIFIED`.
- rejeicao nao vaza nome no payload publico.
- segundo PR no mesmo exercicio na mesma aula substitui o primeiro.

### Criterio de done
- Estados transitam corretamente nos 6 cenarios principais.
- Notificacoes saem nos 4 momentos certos (teaser, coach decidiu, broadcast, rejeicao privada).
- Templates renderizam usando `student-card` e variantes (`--feature` para broadcast, `--alert` para rejeicao).
- CSS local em `static/css/student_app/screens/pr-verification.css` nao redefine tokens nem hosts canonicos.
- Suite de testes verde.

---

## Onda D — Challenge foundation

### Objetivo
Criar schema e endpoints stub para challenges. Sem logica de negocio. Prepara o terreno para integracao futura com PR workflow.

### Estimativa
1 dia-PR.

### Arquivos tocados
- `student_app/models.py` — adicionar `Challenge` e `ChallengeEntry`.
- `student_app/views/challenge_views.py` (NOVO) — GET lista, GET detalhe.
- `student_app/urls.py` — 2 rotas novas.
- `student_app/migrations/0020_challenge.py`.
- `templates/student_app/challenges/challenge_list.html` (NOVO).
- `templates/student_app/challenges/challenge_detail.html` (NOVO).
- `static/css/student_app/screens/challenges.css` (NOVO).

### Modelo
```python
class Challenge(TimeStampedModel):
    title            = CharField(max_length=140)
    exercise_slug    = SlugField(max_length=64)
    target_weight_kg = DecimalField(max_digits=6, decimal_places=2)
    starts_at        = DateTimeField()
    ends_at          = DateTimeField()

class ChallengeEntry(TimeStampedModel):
    challenge   = FK(Challenge, on_delete=CASCADE, related_name='entries')
    student     = FK(Student, on_delete=CASCADE)
    weight_kg   = DecimalField(max_digits=6, decimal_places=2)
    verified_pr = FK('PrVerificationRequest', on_delete=SET_NULL, null=True, blank=True)
```

### Decisao tecnica
1. `verified_pr` fica `null=True` agora; integracao real entra em onda futura.
2. Endpoints sao apenas leitura nesta onda.
3. Nenhum signal, nenhum listener, nenhuma notificacao.

### Testes obrigatorios
- Migration aplica sem erro.
- `Challenge.objects.create(...)` funciona em fixture.
- GET lista retorna 200 para aluno autenticado.
- GET detalhe retorna 404 para challenge inexistente.

### Criterio de done
- Schema migrado.
- Endpoints respondem com payload vazio se nao houver dados.
- Templates renderizam estado vazio sem quebrar.

---

## Onda Smoke — Validacao visual por papel

### Objetivo
Confirmar que a sidebar, areas e fluxos criticos por papel continuam funcionando apos as ondas de notificacao e PR workflow.

### Estimativa
0.5 dia, dependente de servidor Django local + Chrome com extensao MCP conectada.

### Roteiro
Seguir [beta-role-test-agenda.md](../rollout/beta-role-test-agenda.md) na ordem:
1. Login como `owner` -> sidebar correta, dashboard, finance, operations.
2. Login como `manager` -> sidebar restrita, sem acessos elevados.
3. Login como `coach` -> workspace coach, WOD planner, grade.
4. Login como `reception` -> recepcao, financeiro restrito.
5. Login como `aluno` (`/aluno/`) -> home, WOD, RM, agenda, novos templates de PR.

### Evidencia
- Screenshot por papel por workspace.
- Lista de regressoes encontradas, se houver.

### Criterio de done
- Cada papel acessa apenas o que deveria.
- Nenhum 500 ou template error em fluxo critico.
- Notificacoes push aparecem para o aluno em pelo menos um cenario testado.

---

## Fix paralelo (nao bloqueia ondas)

### Sintoma
`boxcore/tests/test_import_students.py::ImportStudentsCsvCommandTests::test_import_creates_and_updates_students_by_phone` falha com `IntegrityError: UNIQUE constraint failed: boxcore_student.phone_lookup_index`.

### Diagnostico
1. Falha confirmada como pre-existente via `git stash` + run + `git stash pop`.
2. Causa esta no management command `import_students_csv.py`, nao no `StudentImporter` (que e o caminho usado pela UI).
3. O teste cria um aluno previamente, depois roda o command, e o `update_or_create` colide com o `phone_lookup_index` (blind index calculado a partir do telefone).

### Acao
PR isolado, fora das ondas. Investigar se o command precisa atualizar `phone_lookup_index` antes de salvar ou se o teste deve usar fixture diferente.

---

## Ordem de execucao recomendada

```
Hoje:           Onda 0 (FEITO)
Esta semana:    Onda A    -> 6 eventos de notificacao desbloqueiam de uma vez
Proximo ciclo:  Onda B    -> cron + Stripe webhook
Sprint:         Onda C    -> maior investimento, fluxo social
Buffer:         Onda D    -> schema only, baixo risco
Paralelo:       Onda Smoke quando servidor estiver disponivel
Em paralelo:    Fix do test_import_students em PR isolado
```

## Sinais de saude do plano

1. cada onda fecha em PR atomico sem bloquear a proxima.
2. nenhuma onda introduz import direto de boxcore para modelo novo.
3. todo disparo externo (push ou WhatsApp) tem auditoria correspondente.
4. testes de cada onda passam antes do merge da seguinte.
5. CSS novo do app do aluno mora em `static/css/student_app/` e nao redefine tokens ou hosts canonicos.

## Sinais de que o plano saiu do trilho

1. uma onda comecou a depender de outra que ainda nao terminou.
2. um modelo novo apareceu em `boxcore/models/`.
3. um listener virou lugar de regra de negocio.
4. um adapter de canal externo cresceu para tomar decisao de dominio.
5. CSS local de uma tela passou a redefinir token semantico ou host canonico.
