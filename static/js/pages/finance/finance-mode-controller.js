/**
 * ARQUIVO: finance-mode-controller.js
 *
 * POR QUE ELE EXISTE:
 * - transforma os cards de modo do Financeiro em um filtro local de boards,
 *   sem navegar por URL e sem interferir no contrato global dos KPIs.
 */

document.addEventListener('DOMContentLoaded', function() {
    var financeRoot = document.querySelector('[data-page="finance"]');
    if (!financeRoot) {
        return;
    }

    var modeGrid = financeRoot.querySelector('.finance-mode-grid');
    if (!modeGrid) {
        return;
    }

    var modeButtons = modeGrid.querySelectorAll('[data-finance-mode-button]');
    var modeSurfaces = financeRoot.querySelectorAll('[data-finance-mode-visibility]');
    if (!modeButtons.length || !modeSurfaces.length) {
        return;
    }

    function parseModes(value) {
        return (value || '')
            .split(/\s+/)
            .map(function(item) {
                return item.trim();
            })
            .filter(Boolean);
    }

    function applyMode(modeKey) {
        modeGrid.dataset.activeMode = modeKey;

        modeButtons.forEach(function(button) {
            var isActive = button.dataset.financeModeButton === modeKey;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });

        modeSurfaces.forEach(function(surface) {
            var allowedModes = parseModes(surface.dataset.financeModeVisibility);
            if (!allowedModes.length) {
                return;
            }

            surface.hidden = !allowedModes.includes(modeKey);
        });
    }

    modeButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            applyMode(this.dataset.financeModeButton);
        });
    });

    applyMode(modeGrid.dataset.activeMode || 'hybrid');
});
