/*
ARQUIVO: preview do template rapido no editor WOD.

POR QUE ELE EXISTE:
- evita aplicar template rapido sem contexto minimo de leitura.

O QUE ESTE ARQUIVO FAZ:
1. le o catalogo local de templates rapidos.
2. atualiza o resumo ao trocar a opcao selecionada.
*/

(function () {
    const payload = document.getElementById('wod-quick-template-options');
    const form = document.querySelector('[data-wod-quick-template-form]');
    const select = form?.querySelector('[data-wod-quick-template-select]');
    const preview = form?.querySelector('[data-wod-quick-template-preview]');
    if (!payload || !form || !select || !preview) return;

    let options = [];
    try {
        options = JSON.parse(payload.textContent || '[]');
    } catch (error) {
        options = [];
    }

    const byId = new Map(options.map((item) => [String(item.id), item]));
    const titleNode = preview.querySelector('[data-wod-quick-template-title]');
    const summaryNode = preview.querySelector('[data-wod-quick-template-summary]');
    const coachNode = preview.querySelector('[data-wod-quick-template-coach]');
    const blocksNode = preview.querySelector('[data-wod-quick-template-blocks]');
    const movementsNode = preview.querySelector('[data-wod-quick-template-movements]');

    function updatePreview() {
        const selected = byId.get(String(select.value || ''));
        if (!selected) {
            if (titleNode) titleNode.textContent = 'Escolha um template para ver o resumo.';
            if (summaryNode) summaryNode.textContent = 'Sem template selecionado.';
            if (coachNode) coachNode.textContent = 'Sem coach';
            if (blocksNode) blocksNode.textContent = '0 blocos';
            if (movementsNode) movementsNode.textContent = '0 movimentos';
            return;
        }
        if (titleNode) titleNode.textContent = selected.label;
        if (summaryNode) summaryNode.textContent = selected.summary || 'Template rapido disponivel.';
        if (coachNode) coachNode.textContent = `Coach ${selected.coach_label}`;
        if (blocksNode) blocksNode.textContent = `${selected.block_count || 0} bloco(s)`;
        if (movementsNode) movementsNode.textContent = `${selected.movement_count || 0} movimento(s)`;
    }

    select.addEventListener('change', updatePreview);
    updatePreview();
})();
