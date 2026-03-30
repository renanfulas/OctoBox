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
    var summaryDesc = document.getElementById('finance-summary-description');
    var statusNode = document.getElementById('finance-filter-status');

    if (!form || !summaryTitle || !summaryDesc) {
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
            summaryDesc.textContent = 'Esse contexto orienta a leitura e prepara o fechamento operacional sem expor exportacoes na interface principal.';
            if (statusNode) {
                statusNode.textContent = 'Recorte financeiro atualizado para ' + joinedParts + '.';
            }
            return;
        }

        summaryTitle.textContent = 'Resumo do Recorte Ativo';
        summaryDesc.textContent = 'Confirme o recorte antes de seguir com cobranca, leitura e fechamento operacional.';
        if (statusNode) {
            statusNode.textContent = 'Recorte financeiro sem filtros especificos.';
        }
    }

    form.addEventListener('change', updateSummary);
    updateSummary();
});
