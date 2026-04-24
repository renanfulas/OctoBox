/*
ARQUIVO: interacao leve do inbox de aprovacao WOD.

POR QUE ELE EXISTE:
- permite navegar na fila com teclado sem introduzir framework JS.

O QUE ESTE ARQUIVO FAZ:
1. alterna preview ativo ao clicar em um item da lista.
2. suporta j/k para navegar.
3. suporta Enter para aprovar somente quando o item nao exige confirmacao sensivel.

PONTOS CRITICOS:
- nao interceptar teclas dentro de inputs, selects ou textareas.
- manter fallback HTML funcional sem JavaScript.
*/

(function () {
    const root = document.querySelector('[data-wod-inbox]');
    if (!root) return;

    const items = Array.from(root.querySelectorAll('[data-wod-inbox-key]'));
    const panels = Array.from(root.querySelectorAll('[data-wod-inbox-panel]'));
    if (!items.length || !panels.length) return;

    root.classList.add('is-enhanced');

    let focusedIndex = Math.max(0, items.findIndex((item) => item.classList.contains('is-focused')));

    function isTypingTarget(target) {
        return Boolean(target && target.closest('input, textarea, select, button:not([data-wod-inbox-key])'));
    }

    function setFocusedItem(index, options) {
        const nextIndex = Math.max(0, Math.min(items.length - 1, index));
        const selectedItem = items[nextIndex];
        const selectedKey = selectedItem.dataset.wodInboxKey;

        items.forEach((item) => {
            const isSelected = item === selectedItem;
            item.classList.toggle('is-focused', isSelected);
            item.setAttribute('aria-selected', isSelected ? 'true' : 'false');
        });

        panels.forEach((panel) => {
            const isSelected = panel.dataset.wodInboxPanel === selectedKey;
            panel.hidden = !isSelected;
            panel.classList.toggle('is-active', isSelected);
        });

        focusedIndex = nextIndex;
        if (options && options.focus) {
            selectedItem.focus({ preventScroll: Boolean(options.preventScroll) });
        }
    }

    function approveFocusedIfSafe() {
        const item = items[focusedIndex];
        const panel = panels.find((candidate) => candidate.dataset.wodInboxPanel === item.dataset.wodInboxKey);
        if (!item || !panel || item.classList.contains('wod-inbox__item--sensitive')) return;
        if (panel.querySelector('input[name="confirm_sensitive_changes"]')) {
            const confirmation = panel.querySelector('input[name="confirm_sensitive_changes"]');
            confirmation.focus();
            return;
        }
        const approveButton = panel.querySelector('.coach-wod-approve-form button[type="submit"]');
        if (approveButton) approveButton.click();
    }

    items.forEach((item, index) => {
        item.addEventListener('click', () => setFocusedItem(index));
    });

    document.addEventListener('keydown', (event) => {
        if (isTypingTarget(event.target)) return;

        if (event.key === 'j' || event.key === 'ArrowDown') {
            event.preventDefault();
            setFocusedItem(focusedIndex + 1, { focus: true, preventScroll: true });
            return;
        }

        if (event.key === 'k' || event.key === 'ArrowUp') {
            event.preventDefault();
            setFocusedItem(focusedIndex - 1, { focus: true, preventScroll: true });
            return;
        }

        if (event.key === 'Enter') {
            event.preventDefault();
            approveFocusedIfSafe();
        }
    });

    setFocusedItem(focusedIndex);
})();
