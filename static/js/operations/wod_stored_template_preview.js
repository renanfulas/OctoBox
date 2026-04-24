/*
ARQUIVO: preview do template persistente no editor WOD.
*/

(function () {
    const payload = document.getElementById('wod-stored-template-options');
    const form = document.querySelector('[data-wod-stored-template-form]');
    const select = form?.querySelector('[data-wod-stored-template-select]');
    const preview = form?.querySelector('[data-wod-stored-template-preview]');
    if (!payload || !form || !select || !preview) return;

    let options = [];
    try {
        options = JSON.parse(payload.textContent || '[]');
    } catch (error) {
        options = [];
    }

    const byId = new Map(options.map((item) => [String(item.id), item]));
    const titleNode = preview.querySelector('[data-wod-stored-template-title]');
    const summaryNode = preview.querySelector('[data-wod-stored-template-summary]');
    const coachNode = preview.querySelector('[data-wod-stored-template-coach]');
    const blocksNode = preview.querySelector('[data-wod-stored-template-blocks]');
    const movementsNode = preview.querySelector('[data-wod-stored-template-movements]');
    const trustNode = preview.querySelector('[data-wod-stored-template-trust]');

    function updatePreview() {
        const selected = byId.get(String(select.value || ''));
        if (!selected) {
            if (titleNode) titleNode.textContent = 'Escolha um template salvo para ver o resumo.';
            if (summaryNode) summaryNode.textContent = 'Sem template persistente selecionado.';
            if (coachNode) coachNode.textContent = 'Sem autor';
            if (blocksNode) blocksNode.textContent = '0 blocos';
            if (movementsNode) movementsNode.textContent = '0 movimentos';
            if (trustNode) trustNode.textContent = 'Template em revisao';
            return;
        }
        if (titleNode) titleNode.textContent = selected.label;
        if (summaryNode) summaryNode.textContent = selected.summary || 'Template persistente disponivel.';
        if (coachNode) coachNode.textContent = `Autor ${selected.coach_label}`;
        if (blocksNode) blocksNode.textContent = `${selected.block_count || 0} bloco(s)`;
        if (movementsNode) movementsNode.textContent = `${selected.movement_count || 0} movimento(s)`;
        if (trustNode) trustNode.textContent = selected.is_trusted ? 'Template confiavel' : 'Template em revisao';
    }

    select.addEventListener('change', updatePreview);
    updatePreview();
})();
