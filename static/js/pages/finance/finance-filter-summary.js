/**
 * ARQUIVO: resumo acessivel do recorte financeiro.
 *
 * POR QUE ELE EXISTE:
 * - move o resumo dinamico de filtros do template para um JS estatico.
 * - expoe atualizacoes do recorte com aria-live para leitura assistida.
 */

document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('finance-filter-form');
    var summaryTitle = document.getElementById('finance-summary-title');
    var statusNode = document.getElementById('finance-filter-status');
    var summaryGrid = document.querySelector('[data-finance-filter-summary-grid]');
    var summaryCurrent = document.querySelector('[data-finance-filter-current]');

    if (!form || !summaryTitle || !summaryGrid || !summaryCurrent) {
        return;
    }

    function getSelectedLabel(selectEl) {
        if (!selectEl || selectEl.selectedIndex < 0) {
            return '';
        }

        var selectedText = selectEl.options[selectEl.selectedIndex].text || '';
        if (selectedText === '---------' || selectedText === '') {
            return '';
        }

        return selectedText;
    }

    function getFallbackValue(selectEl) {
        if (!selectEl) {
            return '';
        }

        var key = selectEl.name;
        if (key === 'months') {
            return '6 meses';
        }
        if (key === 'plan') {
            return 'Todos os planos';
        }
        if (key === 'payment_status' || key === 'payment_method' || key === 'queue_focus') {
            return 'Todos';
        }
        return '';
    }

    function updateSummaryValue(key, value) {
        var node = summaryGrid.querySelector('[data-finance-filter-key="' + key + '"] .finance-filter-summary-value');
        if (!node) {
            return;
        }

        node.textContent = value;
    }

    function updateSummary() {
        var parts = [];
        var selects = form.querySelectorAll('select');

        selects.forEach(function(selectEl) {
            var label = getSelectedLabel(selectEl);
            var value = label || getFallbackValue(selectEl);
            updateSummaryValue(selectEl.name, value);

            if (label && label !== 'Todos') {
                parts.push(label);
            }
        });

        if (parts.length > 0) {
            var joinedParts = parts.join(' | ');
            summaryTitle.textContent = 'Recorte ativo: ' + joinedParts;
            summaryCurrent.textContent = 'Recorte atual: ' + joinedParts;
            if (statusNode) {
                statusNode.textContent = 'Recorte financeiro atualizado para ' + joinedParts + '.';
            }
            return;
        }

        summaryTitle.textContent = 'Resumo do Recorte Ativo';
        summaryCurrent.textContent = 'Recorte atual: padrao da leitura financeira.';
        if (statusNode) {
            statusNode.textContent = 'Recorte financeiro sem filtros especificos.';
        }
    }

    form.addEventListener('change', updateSummary);
    updateSummary();
});
