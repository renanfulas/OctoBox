## Evidence Map

- `operations/queries.py`
- `templates/operations/owner.html`
- `templates/operations/includes/owner/owner_primary_panel.html`
- `templates/operations/manager.html`
- `templates/includes/ui/shared/focus_sequence.html`
- `templates/operations/includes/manager/manager_boards_section.html`

## T1 findings

- Owner:
  - a entrada dominante existe por ordem de `owner_operational_focus|first`
  - `owner_priority_context` descreve a tese, mas nao sobe `entry_surface`, `entry_reason`, `secondary_surface`
  - o handoff da primeira leitura para os proximos passos ainda depende da ordem da lista
- Manager:
  - a entrada dominante existe por ordem de `manager_operational_focus`
  - `manager_priority_context` descreve a tese, mas nao sobe `entry_href`, `secondary_href` ou motivo estruturado de handoff
  - `focus_sequence.html` marca o primeiro card como principal por `forloop.first`, ou seja: a prioridade ainda e inferida pela ordem visual

## T2 decision

- Contrato canonico escolhido: `decision_entry_context`
- `priority_context` continua como tese de abertura
- `operational_focus` continua como trilha auxiliar
- prioridade deixa de depender semanticamente de:
  - `owner_operational_focus|first`
  - `forloop.first`
- ordem oficial da segunda onda:
  - 1: manager
  - 2: owner

## T3 implementation

- `operations/queries.py`
  - adicionou `_build_decision_entry_context()`
  - owner agora sobe `owner_decision_entry_context` e `owner_secondary_focus`
  - manager agora sobe `manager_decision_entry_context`
- `owner_primary_panel.html`
  - deixou de depender de `owner_operational_focus|first`
- `focus_sequence.html`
  - passou a aceitar `primary_href` para marcar a entrada dominante sem depender de `forloop.first`
- `manager.html`
  - passou a entregar `primary_href` vindo do payload

## T4 validation

- `python manage.py check` passou limpo
- owner principal nao depende mais de `owner_operational_focus|first`
- manager principal nao depende mais de `forloop.first` nos pontos em que o payload informa `primary_href`
- coach e recepcao continuam com fallback seguro do componente compartilhado
