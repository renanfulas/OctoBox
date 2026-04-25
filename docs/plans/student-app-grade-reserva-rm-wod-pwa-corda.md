# Student App — Grade / Reserva / RM / WOD / PWA (Plano Corda)

Data: 2026-04-24  
Branch: fixes sobre `claude/inspiring-pike-58d069`

---

## Diagnóstico por área

### 1. Grade — filtro por dia (Semana)

**Bug:** A view `StudentGradeView` / `GetStudentDashboard` busca `ClassSession` sem filtro de data — retorna todas as próximas sessões. O seletor de pílulas (Hoje/Sáb/Dom…) existe no template, mas **não filtra** — a lista abaixo mostra sempre todas.

**Bug 2 (Grade sidebar):** A aba "Grade" (sidebar item) mostra todas as próximas aulas por vários dias em vez de mostrar apenas hoje + amanhã. E ainda permite reservar/fazer check-in — deveria ser somente leitura.

**Causa:** `GetStudentDashboard.execute()` (`use_cases.py:233`) busca `next_sessions` com `status__in=['scheduled','open']` sem filtro de `scheduled_at__date`. Nenhum mecanismo de passagem do dia selecionado existe.

---

### 2. Reserva — dupla reserva no mesmo dia

**Bug:** É possível reservar duas aulas diferentes no mesmo dia. `unique_student_session` (`model_definitions.py:135`) garante apenas unicidade por `(student, session)`, não por `(student, date)`.

**Bug 2 — Cancelar não reabre:** O workflow `confirm_student_attendance()` (`attendance_workflows.py:52`) JÁ faz reativação (CANCELED → BOOKED). O problema é no template: quando status == CANCELED, o botão "Reservar" não é exibido — só "Cancelado" como label sem ação.

**Bug 3 — Sem reserva não mostra botão claro:** Aulas sem reserva (status inexistente) mostram "Sem reserva" mas o botão "Reservar" não aparece sempre que esperado.

---

### 3. RM — display

**Bug 1 — Casas decimais:** Exibe `150,00 kg`. Deve ser `Back Squat 150kg` (inteiro quando sem fração; `Back Squat 150,5kg` quando tem).

**Bug 2 — Edição inline aberta:** Form de edição está exposto por default. Deve ser somente-leitura com ícone SVG de lápis que abre o form.

---

### 4. WOD por ClassSession

**Missing:** Clicar em um card de aula na Grade/Semana não abre o WOD daquela sessão. A view `StudentWodView` usa `target_session = dashboard.active_wod_session or dashboard.focal_session` — não aceita `session_id` como param.

---

### 5. PWA card persistente

**Bug:** `renderActivationUI()` (`pwa.js:280`) só esconde o card quando `activationComplete = true` (standalone + notificação granted + push subscription ativa). Se o usuário nega notificação ou está em browser normal, o card fica visível para sempre. Não há flag de dismiss em localStorage.

---

## Plano Corda — 6 Waves

---

### Wave 1 — Grade: filtro de dia correto (Semana view)

**Arquivo alvo:** `student_app/application/use_cases.py` + template `grade.html` (ou semana.html)

**Backend:**
1. Aceitar query param `?date=2026-04-24` na `StudentGradeView`.
2. Passar `selected_date` para `GetStudentDashboard` (ou novo método `get_sessions_for_date(student, date)`).
3. Query:
   ```python
   sessions = ClassSession.objects.filter(
       box=student.box,
       status__in=['scheduled', 'open'],
       scheduled_at__date=selected_date,
   ).order_by('scheduled_at')
   ```
4. Default: `selected_date = date.today()`.

**Frontend:**
- Pílulas de dia geram link `?date=YYYY-MM-DD` (não JS toggle).
- Pílula ativa = `selected_date` atual.
- Se `sessions` for vazio → mostra "Sem aulas neste dia."
- **Não mostrar** "Próximas aulas" misturadas — apenas o dia selecionado.

**Critério de done:** Clicar "Sab" mostra só sábado; "Hoje" mostra só hoje; vazio quando sem aulas.

---

### Wave 2 — Grade sidebar: somente leitura + Hoje/Amanhã

**Arquivo alvo:** `student_app/views/shell_views.py` (StudentGradeView) + `templates/student_app/grade.html`

**Backend:**
1. `GetStudentDashboard` (ou novo helper) retorna dois grupos:
   - `today_sessions`: `scheduled_at__date = today`
   - `tomorrow_sessions`: `scheduled_at__date = today + timedelta(days=1)`
2. Não retornar sessões além de amanhã para esta view.

**Frontend:**
- Seção "Próximas" → aulas de hoje (com hora).
- Seção "Amanhã" → aulas do dia seguinte (apenas).
- **Remover** todos os botões "Reservar" e "Check-in" desta aba.
- Cada card de aula é clicável e abre o WOD da sessão (Wave 4).
- Adicionar subtítulo discreto: "Aqui você acompanha sua rotina. Reserve na aba Agenda."

**Critério de done:** Aba Grade mostra hoje + amanhã, sem botões de ação, cada card abre WOD.

---

### Wave 3 — Reserva: uma aula por dia + cancelar reabre

**Arquivo alvo:** `student_app/workflows/attendance_workflows.py` + template de aulas

**3a — Uma aula por dia:**
```python
# em confirm_student_attendance(), antes de criar:
same_day_booked = Attendance.objects.filter(
    student=student,
    session__scheduled_at__date=session.scheduled_at.date(),
    status__in=[AttendanceStatus.BOOKED, AttendanceStatus.CHECKED_IN],
).exclude(session=session).exists()

if same_day_booked:
    raise ValidationError("Você já tem uma aula reservada neste dia.")
```
- Erro exibido como toast no template (não 500).

**3b — Cancelar reabre vaga:**
- Workflow JÁ permite (CANCELED → BOOKED via `confirm_student_attendance()`). 
- Fix no template: quando `attendance.status == CANCELED`, renderizar botão "Reservar novamente" que chama o mesmo endpoint de confirmação.
- Remover label estático "Cancelado" sem ação.

**3c — Estado claro por card:**

| Status | Label | Botão |
|---|---|---|
| Sem attendance | "Sem reserva" | **[Reservar]** |
| BOOKED | "Reservado" | **[Cancelar]** |
| CHECKED_IN | "Check-in feito" | — |
| CHECKED_OUT | "Finalizado" | — |
| CANCELED | "Cancelada" | **[Reservar novamente]** |
| ABSENT | "Faltou" | — |

**Critério de done:** Não cria 2 reservas no mesmo dia; cancelada volta a ter botão de reservar.

---

### Wave 4 — WOD por ClassSession (reaproveitamento)

**Arquivo alvo:** `student_app/views/wod_context.py` + `student_app/views/shell_views.py` + URL

**Arquitetura de reaproveitamento:**
- `build_student_wod_context()` já aceita `target_session`. Basta expor via query param.
- Adicionar param opcional `?session_id=UUID` na `StudentWodView`:
  ```python
  session_id = request.GET.get('session_id')
  if session_id:
      target_session = get_object_or_404(ClassSession, pk=session_id, box=student.box)
  else:
      target_session = dashboard.active_wod_session or dashboard.focal_session
  ```
- Mesmo template `wod.html`, zero duplicação.
- URL permanece `/aluno/wod/`.

**Frontend (cards de aula):**
- Cada card de aula na Grade (Wave 2) e na Semana (Wave 1) vira link para:
  `/aluno/wod/?session_id={{ session.pk }}`
- Se a sessão não tem WOD publicado → exibe "Treino ainda não publicado."

**Critério de done:** Clicar em qualquer card abre o WOD daquela sessão específica; sem WOD → mensagem amigável.

---

### Wave 5 — RM: somente leitura + formato limpo

**Arquivo alvo:** `templates/student_app/_partials/_rm_list.html` + filtro de template ou view

**5a — Formato sem casas decimais desnecessárias:**
```python
# templatetag ou filtro inline:
def format_rm(value):
    if value == int(value):
        return f"{int(value)}kg"
    return f"{value:g}kg"
```
Exibe: `Back Squat 150kg` / `Snatch 67,5kg`

**5b — Somente leitura por default:**
- Default: mostra nome do exercício + valor formatado. Sem input.
- SVG ícone de lápis (à direita do card) com `title="Editar RM"`.
- Clique no lápis: mostra o form inline (HTMX `hx-get` ou toggle de classe CSS).
- Fora do modo edição: form oculto (`hidden`).
- Após salvar: HTMX retorna o card atualizado em somente-leitura.

**Critério de done:** Landing na aba RM mostra só leitura; lápis abre edição; valor sem `.00`.

---

### Wave 6 — PWA card: dismiss persistente

**Arquivo alvo:** `static/js/student_app/pwa.js`

**Fix:**
```javascript
const PWA_DISMISS_KEY = 'octobox_pwa_card_dismissed';

// Em renderActivationUI(), antes de mostrar:
function shouldShowActivationCard(state) {
  if (state.activationComplete) return false;
  if (localStorage.getItem(PWA_DISMISS_KEY) === '1') return false;
  return true;
}

// Botão "X" / "Agora não" no card chama:
function dismissPwaCard() {
  localStorage.setItem(PWA_DISMISS_KEY, '1');
  activationElement.hidden = true;
}
```

**Regras:**
- Dismiss persiste via `localStorage` (sobrevive refresh).
- Se usuário depois instalar o app (standalone), `activationComplete = true` → card some definitivamente e chave é removida do localStorage.
- Card **não** reaparece a cada visita.
- Adicionar botão "Agora não" ou ícone `×` visível no card (não existe hoje).

**Critério de done:** Clicar "Agora não" → card some e não reaparece em refresh. Instalar app → card some permanentemente.

---

## Ordem de execução recomendada

```
Wave 6 (PWA)     → isolado, zero risco, 30min
Wave 5 (RM)      → isolado, zero risco, 45min
Wave 3 (Reserva) → risco médio (validação), requer teste
Wave 1 (Semana)  → risco médio (query change), requer teste
Wave 2 (Grade)   → depende de Wave 1 (shared query logic)
Wave 4 (WOD)     → depende de Wave 2 (card links)
```

---

## Arquivos que serão tocados

| Arquivo | Wave(s) | Tipo de mudança |
|---|---|---|
| `student_app/application/use_cases.py` | 1, 2 | Query filter por data |
| `student_app/views/shell_views.py` | 1, 2, 4 | Param `?date`, `?session_id`, grupos hoje/amanhã |
| `student_app/views/wod_context.py` | 4 | Accept `target_session` override |
| `student_app/workflows/attendance_workflows.py` | 3 | Validação 1-por-dia |
| `templates/student_app/grade.html` | 2 | Hoje/Amanhã, sem botões |
| `templates/student_app/semana.html` (ou equivalente) | 1 | Links de pílula, lista filtrada |
| `templates/student_app/_partials/_session_card.html` | 3 | Estado por status + botões corretos |
| `templates/student_app/_partials/_rm_list.html` | 5 | Somente-leitura + lápis + formato |
| `static/js/student_app/pwa.js` | 6 | Dismiss localStorage |
| `templates/student_app/_partials/_pwa_activation.html` | 6 | Botão "Agora não" |

---

## Contratos que NÃO mudam

- `SessionWorkout`, `SessionWorkoutBlock`, `SessionWorkoutMovement` — somente leitura no lado aluno.
- `StudentWodView` URL permanece `/aluno/wod/` — só recebe `?session_id` como param adicional.
- `Attendance` model — sem migração de schema. Apenas nova validação no workflow.
- Fluxo DRAFT → PUBLISHED do WOD — inalterado.

---

## Decisões registradas

- **Filtro de dia via query param (não JS):** URL shareable, sem estado oculto, funciona sem JS. Pílulas viram `<a href="?date=...">` simples.
- **Uma aula por dia enforced no workflow, não só no model:** Migration de constraint seria bloqueante e difícil de retrocompatibilizar. Validação no workflow é suficiente e reversível.
- **WOD por `session_id` via GET param:** Reutiliza 100% do template e context builder existentes. Sem view duplicada.
- **PWA dismiss em localStorage:** Sem backend call extra. Simples, funciona offline.
- **RM somente-leitura com HTMX toggle:** Sem page reload, consistente com padrão existente do app.
