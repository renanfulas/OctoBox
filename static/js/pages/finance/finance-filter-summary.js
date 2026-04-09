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

    if (!form || !summaryTitle) {
        return;
    }

    function getSelectedLabel(selectEl) {
        if (!selectEl || !selectEl.selectedIndex || selectEl.selectedIndex <= 0) {
            return null;
        }

        return selectEl.options[selectEl.selectedIndex].text;
    }

    function updateSummary() {
        var parts = [];
        var selects = form.querySelectorAll('select');

        selects.forEach(function(selectEl) {
            var label = getSelectedLabel(selectEl);
            if (label && label !== '---------' && label !== 'Todos' && label !== '') {
                parts.push(label);
            }
        });

        if (parts.length > 0) {
            var joinedParts = parts.join(' | ');
            summaryTitle.textContent = 'Recorte ativo: ' + joinedParts;
            if (statusNode) {
                statusNode.textContent = 'Recorte financeiro atualizado para ' + joinedParts + '.';
            }
            return;
        }

        summaryTitle.textContent = 'Resumo do Recorte Ativo';
        if (statusNode) {
            statusNode.textContent = 'Recorte financeiro sem filtros especificos.';
        }
    }

    form.addEventListener('change', updateSummary);
    updateSummary();
});
