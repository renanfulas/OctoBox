/*
ARQUIVO: command palette do WOD.

POR QUE ELE EXISTE:
- entrega Ctrl+K local para o corredor WOD sem conflitar com o atributo global de acao do shell.

O QUE ESTE ARQUIVO FAZ:
1. abre e fecha a palette com Ctrl+K/Esc.
2. executa comandos via `data-wod-command`.
3. aciona os formulários já existentes no item focado.

PONTOS CRITICOS:
- nunca usar o atributo global de acao do shell.
- nao capturar atalhos enquanto o usuario digita em campos.
*/

(function () {
    const palette = document.querySelector('[data-wod-command-palette]');
    const inbox = document.querySelector('[data-wod-inbox]');
    if (!palette || !inbox) return;

    const commandButtons = Array.from(palette.querySelectorAll('[data-wod-command]'));
    let previousFocus = null;

    function isTypingTarget(target) {
        return Boolean(target && target.closest('input, textarea, select'));
    }

    function getFocusedItem() {
        return inbox.querySelector('[data-wod-inbox-key].is-focused') || inbox.querySelector('[data-wod-inbox-key]');
    }

    function getActivePanel() {
        const focusedItem = getFocusedItem();
        if (!focusedItem) return null;
        return inbox.querySelector(`[data-wod-inbox-panel="${focusedItem.dataset.wodInboxKey}"]`);
    }

    function openPalette() {
        previousFocus = document.activeElement;
        palette.hidden = false;
        const firstCommand = palette.querySelector('[data-wod-command]:not([data-wod-command="close"])');
        if (firstCommand) firstCommand.focus();
    }

    function closePalette() {
        palette.hidden = true;
        if (previousFocus && typeof previousFocus.focus === 'function') {
            previousFocus.focus({ preventScroll: true });
        }
    }

    function clickButton(selector) {
        const panel = getActivePanel();
        const button = (panel ? panel.querySelector(selector) : null) || inbox.querySelector(selector);
        if (button) button.click();
    }

    function focusField(selector) {
        const panel = getActivePanel();
        const field = panel ? panel.querySelector(selector) : null;
        if (field) field.focus();
    }

    function navigate(direction) {
        const items = Array.from(inbox.querySelectorAll('[data-wod-inbox-key]'));
        const focusedItem = getFocusedItem();
        const currentIndex = Math.max(0, items.indexOf(focusedItem));
        const nextIndex = Math.max(0, Math.min(items.length - 1, currentIndex + direction));
        if (items[nextIndex]) items[nextIndex].click();
    }

    function runCommand(command) {
        if (command === 'close') {
            closePalette();
            return;
        }
        if (command === 'approve') clickButton('.coach-wod-approve-form button[type="submit"]');
        if (command === 'reject') focusField('.coach-wod-rejection-inline select[name="rejection_category"]');
        if (command === 'batch-approve') clickButton('.wod-inbox__batch-form button[type="submit"]');
        if (command === 'next') navigate(1);
        if (command === 'previous') navigate(-1);
        closePalette();
    }

    commandButtons.forEach((button) => {
        button.addEventListener('click', () => runCommand(button.dataset.wodCommand));
    });

    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            if (palette.hidden) openPalette();
            else closePalette();
            return;
        }

        if (event.key === 'Escape' && !palette.hidden) {
            event.preventDefault();
            closePalette();
            return;
        }

        if (!palette.hidden || isTypingTarget(event.target)) return;
    });
})();
