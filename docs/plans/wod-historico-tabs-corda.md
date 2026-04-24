# WOD Histórico — Redesign em 3 Abas (Plano Corda)

## Problema

`/operacao/wod/historico/` mistura 4 intenções distintas em uma única surface:

1. "O que foi treinado?" (cards de WODs publicados)
2. "A coordenação está em dia?" (checkpoint semanal + governança)
3. "O que precisa da minha atenção agora?" (follow-ups, RM gaps, alertas)
4. Filtros de coach/motivo de publicação que se aplicam a contextos diferentes

Resultado: ~18 pills, 4 seções, 2 formulários, densidade visual que não comunica hierarquia.

## Objetivo

Separar por intenção de uso. Cada aba responde **uma pergunta**, tem **sua própria hierarquia de informação**, e os filtros relevantes para aquela aba apenas.

---

## Redesign — 3 Abas

### Estrutura de navegação

```
Histórico WOD
─────────────────────────────────────────────────────
[Publicados]  [Checkpoint semanal]  [Alertas & follow-ups]
 ▼ default
```

Implementação: `?aba=publicados|checkpoint|alertas` (query param). URL canônica sem param = `publicados`. Links diretos por aba funcionam.

---

### Aba 1 — Publicados (default)

**Pergunta que responde:** "O que foi treinado esta semana / período?"

**Subtítulo na UI:** `Registro dos treinos publicados por dia e tipo de aula.`

**Pills (máx 5):**
| Pill | Valor |
|---|---|
| Publicados (semana) | N |
| Coaches ativos | N |
| % com RM mapeado | N% |
| Aulas sem WOD | N |

**Conteúdo:**
- Filtros: coach, semana (date range picker), `ClassType`.
- Cards WOD por dia → blocos colapsáveis → movimentos. Mesma estrutura visual do editor, read-only.
- Badge de `ClassType` em cada card.
- Link direto para o editor daquele WOD (ícone lápis) se ainda editável.
- Agrupamento por semana: acordeão `Semana de 21 abr` com total de sessões.

**Filtros removidos desta aba:** `published_reason` (vai para Checkpoint).

---

### Aba 2 — Checkpoint semanal

**Pergunta que responde:** "A coordenação e governança estão em dia?"

**Subtítulo na UI:** `Status semanal da coordenação de treinos — revisão, aprovações e comprometimentos.`

**Pills (máx 5):**
| Pill | Valor |
|---|---|
| Status atual | label (ex: "Em dia") |
| Maturidade | label |
| Ações em aberto | N |
| Governance commitment | label |

**Conteúdo:**
- Formulário `WorkoutWeeklyCheckpointForm` (execution_status, responsible_role, closure_status, governance_commitment_status, notes).
- Checkpoint atual em destaque (card grande, borda de status).
- Histórico de checkpoints anteriores: lista colapsável, ordenada do mais recente.
- Filtro: `published_reason` (aqui faz sentido — governa o checkpoint).
- Weekly executive summary: label de tom + texto curto + pills de ajuste/melhoria/ação.

**Removido desta aba:** cards de WOD, RM gaps, follow-ups individuais.

---

### Aba 3 — Alertas & follow-ups

**Pergunta que responde:** "O que precisa da minha atenção agora?"

**Subtítulo na UI:** `Pendências operacionais, gaps de RM e ações de acompanhamento em aberto.`

**Pills (máx 5):**
| Pill | Valor |
|---|---|
| Críticos | N (vermelho) |
| Warnings | N (amarelo) |
| Follow-ups abertos | N |
| RM gaps | N |
| Memórias operacionais | N |

**Conteúdo:**
- Seção "Críticos" (colapsável, expandida por default se N > 0).
- Seção "Follow-ups abertos" — `SessionWorkoutFollowUpAction` pendentes, agrupados por WOD.
- Seção "RM gaps" — movimentos %RM sem max cadastrado, por aluno/turma.
- Seção "Memórias operacionais" — `SessionWorkoutOperationalMemory` ativas.
- Filtro: coach.

**Removido desta aba:** checkpoint, cards de WOD publicados, governance pills.

---

## Mapeamento atual → novo

| Componente atual | Aba destino |
|---|---|
| Cards WOD publicados | Publicados |
| Filtro coach + today_only | Publicados + Alertas (each aba tem seu próprio) |
| Filtro published_reason | Checkpoint |
| Pills: total sem_concerns, RM ready/gap | Publicados (RM ready) + Alertas (RM gap) |
| Pills: critical/warning/follow-up | Alertas |
| Weekly executive summary | Checkpoint |
| `WorkoutWeeklyCheckpointForm` | Checkpoint |
| Histórico de checkpoints | Checkpoint |
| `SessionWorkoutFollowUpAction` | Alertas |
| `SessionWorkoutOperationalMemory` | Alertas |
| Maturity/rhythm builders | Checkpoint (pills) |

---

## Arquitetura backend

### Separação dos builders (pré-requisito — Wave 1)

`build_workout_publication_history_context()` em `workout_publication_history_context.py` é monolítico. Quebrar em 3 funções puras, cada uma com seu próprio conjunto de queries:

```python
# workout_board_builders.py (já existe — adicionar aqui)

def build_published_wods_context(box, filters) -> dict:
    """Cards publicados, filtros coach/semana/ClassType, pills de publicação."""
    ...

def build_checkpoint_context(box, filters) -> dict:
    """Checkpoint semanal, histórico, executive summary, published_reason."""
    ...

def build_alerts_context(box, filters) -> dict:
    """Follow-ups, RM gaps, memórias operacionais, alertas críticos/warnings."""
    ...
```

Cada função retorna dict independente. `WorkoutPublicationHistoryView` delega para a função correta pelo `request.GET['aba']`.

### View router

```python
class WorkoutPublicationHistoryView(OperationBaseView):
    ABA_BUILDERS = {
        "publicados":  build_published_wods_context,
        "checkpoint":  build_checkpoint_context,
        "alertas":     build_alerts_context,
    }
    ABA_TEMPLATES = {
        "publicados":  "operations/wod_history/publicados.html",
        "checkpoint":  "operations/wod_history/checkpoint.html",
        "alertas":     "operations/wod_history/alertas.html",
    }
    DEFAULT_ABA = "publicados"

    def get(self, request, ...):
        aba = request.GET.get("aba", self.DEFAULT_ABA)
        if aba not in self.ABA_BUILDERS:
            aba = self.DEFAULT_ABA
        context = self.ABA_BUILDERS[aba](box=..., filters=...)
        context["aba_ativa"] = aba
        return render(request, self.ABA_TEMPLATES[aba], context)
```

Template base `wod_history_shell.html` renderiza a barra de abas + subtítulo + inclui o template da aba ativa.

---

## Waves de entrega

| Wave | Entregável | Critério de done | Risco |
|---|---|---|---|
| 0 | Este doc aprovado | — | — |
| 1 | Quebrar builder em 3 funções puras, output idêntico ao atual | Testes existentes continuam passando; output identical para `?aba=publicados` | Baixo |
| 2 | Router de aba + template shell + aba Publicados | Aba Publicados cobre 100% do que hoje aparece para WODs publicados | Médio |
| 3 | Aba Checkpoint | Formulário funcional; histórico de checkpoints; pills corretos | Médio |
| 4 | Aba Alertas & follow-ups | Follow-ups, RM gaps, memórias operacionais na aba correta | Médio |
| 5 | Telemetria de uso por aba + remoção do template monolítico antigo | Sem acesso ao template antigo; analytics de aba mais usada | Baixo |

---

## Subtítulos definitivos por aba (copy)

| Aba | Título | Subtítulo |
|---|---|---|
| Publicados | Treinos publicados | Registro dos treinos publicados por dia e tipo de aula. |
| Checkpoint semanal | Checkpoint semanal | Status da coordenação de treinos — revisões, aprovações e comprometimentos da semana. |
| Alertas & follow-ups | Alertas & pendências | O que precisa da sua atenção agora: gaps de RM, follow-ups abertos e alertas operacionais. |

---

## Arquivos a criar/alterar

| Arquivo | Ação |
|---|---|
| `operations/workspace_views.py` (ou `workout_publication_history_views.py`) | Refatorar `WorkoutPublicationHistoryView` com router |
| `operations/workout_board_builders.py` | Adicionar 3 funções puras; manter builders existentes |
| `operations/workout_publication_history_context.py` | Deprecar função monolítica; delegar para builders |
| `templates/operations/wod_history/shell.html` | Criar — barra de abas, subtítulo, área de conteúdo |
| `templates/operations/wod_history/publicados.html` | Criar |
| `templates/operations/wod_history/checkpoint.html` | Criar |
| `templates/operations/wod_history/alertas.html` | Criar |
| `operations/urls.py` | Manter rota existente; sem quebra de URL |

---

## Decisões registradas

- **URL sem quebra**: `?aba=` preserva a URL base existente. Qualquer bookmark já feito continua funcionando (vai para aba Publicados).
- **Builders puros primeiro (Wave 1)**: refatoração de lógica sem mudança de UI. Zero risco de regressão visual.
- **Template monolítico fica por 2 sprints**: removido só em Wave 5, após telemetria confirmar que ninguém o acessa diretamente.
- **Sem redesign de pills individuais**: reuso dos pills existentes, só redistribuídos. Não mudar conteúdo — só localização.
