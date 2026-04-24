/*
ARQUIVO: navegacao por teclado do planner semanal de WOD.

POR QUE ELE EXISTE:
- melhora operacao do planner sem adicionar mutacoes novas.

O QUE ESTE ARQUIVO FAZ:
1. marca a grade como progressive-enhanced.
2. move foco entre celulas com setas.
3. ativa a acao principal com Enter ou espaco.

PONTOS CRITICOS:
- nao capturar teclado dentro de inputs, selects, textareas ou botoes.
- manter HTML nativo funcional sem JavaScript.
*/

(function () {
    const planner = document.querySelector('[data-wod-planner]');
    if (!planner) return;

    const cells = Array.from(planner.querySelectorAll('[data-wod-planner-cell]'));
    const spotlight = planner.querySelector('[data-wod-planner-spotlight]');
    if (!cells.length) return;

    const templatePickerTelemetryUrl = planner.dataset.templatePickerTelemetryUrl || '';
    const templatePicker = planner.querySelector('[data-wod-planner-template-picker]');
    const templatePickerCopy = templatePicker?.querySelector('[data-wod-planner-template-picker-copy]');
    const templatePickerTriggers = Array.from(planner.querySelectorAll('[data-wod-planner-template-picker-trigger]'));
    const templateApplyForms = Array.from(planner.querySelectorAll('[data-wod-planner-template-apply-form]'));
    let templatePickerSessionId = '';

    planner.classList.add('is-enhanced');

    function emitTemplatePickerEvent(eventName, payload) {
        if (!templatePickerTelemetryUrl || !eventName) return;
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
        formData.append('event_name', eventName);
        if (payload?.sessionId) formData.append('session_id', payload.sessionId);
        if (payload?.templateId) formData.append('template_id', payload.templateId);
        fetch(templatePickerTelemetryUrl, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
            keepalive: true,
        }).catch(() => {});
    }

    function isTypingTarget(target) {
        return Boolean(target && target.closest('input, textarea, select, button, a'));
    }

    function setFocusedCell(nextCell, options) {
        if (!nextCell) return;
        cells.forEach((cell) => {
            const isFocused = cell === nextCell;
            cell.classList.toggle('is-focused', isFocused);
            cell.tabIndex = isFocused ? 0 : -1;
        });
        updateSpotlight(nextCell);
        if (options && options.focus) {
            nextCell.focus({ preventScroll: Boolean(options.preventScroll) });
        }
    }

    function updateSpotlight(cell) {
        if (!spotlight || !cell) return;
        const mapping = {
            '[data-planner-spotlight-session]': cell.dataset.plannerSessionTitle || 'Sem sessao',
            '[data-planner-spotlight-slot]': cell.dataset.plannerSlotLabel || '-',
            '[data-planner-spotlight-status]': cell.dataset.plannerStatusLabel || '-',
            '[data-planner-spotlight-coach]': cell.dataset.plannerCoachLabel || '-',
            '[data-planner-spotlight-policy]': cell.dataset.plannerPolicyLabel || 'Politica nao registrada',
            '[data-planner-spotlight-workout]': cell.dataset.plannerWorkoutTitle || 'Sem WOD',
            '[data-planner-spotlight-summary]': cell.dataset.plannerSummary || '',
            '[data-planner-spotlight-primary]': cell.dataset.plannerPrimaryAction || '',
            '[data-planner-spotlight-secondary]': cell.dataset.plannerSecondaryAction || 'Sem acao secundaria',
        };
        Object.entries(mapping).forEach(([selector, value]) => {
            const node = spotlight.querySelector(selector);
            if (node) node.textContent = value;
        });
    }

    function openTemplatePicker(sessionId, sessionTitle) {
        if (!templatePicker || !sessionId) return;
        templatePickerSessionId = String(sessionId);
        if (templatePickerCopy) {
            templatePickerCopy.textContent = `Selecione um template confiavel para aplicar na aula ${sessionTitle || 'selecionada'}.`;
        }
        emitTemplatePickerEvent('opened', { sessionId });
        if (typeof templatePicker.showModal === 'function') templatePicker.showModal();
    }

    templatePickerTriggers.forEach((trigger) => {
        trigger.addEventListener('click', () => {
            openTemplatePicker(trigger.dataset.sessionId, trigger.closest('[data-wod-planner-cell]')?.dataset.plannerSessionTitle || 'selecionada');
        });
    });

    templateApplyForms.forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (!templatePickerSessionId) {
                event.preventDefault();
                return;
            }
            const templateId = form.dataset.templateId;
            emitTemplatePickerEvent('selected', { sessionId: templatePickerSessionId, templateId });
            form.action = `/operacao/wod/planner/celula/${templatePickerSessionId}/template-confiavel/${templateId}/`;
        });
    });

    function focusedIndex() {
        return Math.max(0, cells.findIndex((cell) => cell.classList.contains('is-focused')));
    }

    function moveFocusGrid(dayDelta, rowDelta) {
        const currentCell = cells[focusedIndex()];
        if (!currentCell) return;

        const currentDay = Number(currentCell.dataset.plannerDayIndex || 0);
        const currentRow = Number(currentCell.dataset.plannerRowIndex || 0);
        const targetDay = currentDay + dayDelta;
        const targetRow = currentRow + rowDelta;

        if (dayDelta !== 0) {
            const sameRowTarget = cells.find(
                (cell) =>
                    Number(cell.dataset.plannerDayIndex) === targetDay &&
                    Number(cell.dataset.plannerRowIndex) === currentRow
            );
            if (sameRowTarget) {
                setFocusedCell(sameRowTarget, { focus: true, preventScroll: true });
                return;
            }
            const dayCells = cells.filter((cell) => Number(cell.dataset.plannerDayIndex) === targetDay);
            if (dayCells.length) {
                const fallback = dayCells[Math.min(currentRow, dayCells.length - 1)];
                setFocusedCell(fallback, { focus: true, preventScroll: true });
            }
            return;
        }

        const sameDayTarget = cells.find(
            (cell) =>
                Number(cell.dataset.plannerDayIndex) === currentDay &&
                Number(cell.dataset.plannerRowIndex) === targetRow
        );
        if (sameDayTarget) {
            setFocusedCell(sameDayTarget, { focus: true, preventScroll: true });
        }
    }

    function openPrimaryAction() {
        const cell = cells[focusedIndex()];
        if (!cell) return;
        const primaryAction =
            cell.querySelector('.wod-planner__cell-action--primary') ||
            cell.querySelector('.wod-planner__cell-action');
        if (primaryAction) primaryAction.click();
    }

    cells.forEach((cell) => {
        cell.addEventListener('focus', () => setFocusedCell(cell));
        cell.addEventListener('click', (event) => {
            if (!event.target.closest('.wod-planner__cell-action, .wod-planner__cell-action-form')) {
                setFocusedCell(cell);
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (!planner.contains(document.activeElement) || isTypingTarget(event.target)) return;

        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
            event.preventDefault();
            if (event.key === 'ArrowRight') moveFocusGrid(1, 0);
            else moveFocusGrid(0, 1);
            return;
        }

        if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
            event.preventDefault();
            if (event.key === 'ArrowLeft') moveFocusGrid(-1, 0);
            else moveFocusGrid(0, -1);
            return;
        }

        if ((event.key === 't' || event.key === 'T') && templatePicker) {
            const cell = cells[focusedIndex()];
            if (cell?.dataset.plannerTemplatePickerEnabled === 'true') {
                event.preventDefault();
                openTemplatePicker(cell.dataset.plannerSessionId, cell.dataset.plannerSessionTitle);
                return;
            }
        }

        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openPrimaryAction();
        }
    });

    setFocusedCell(cells.find((cell) => cell.classList.contains('is-focused')) || cells[0]);
})();
