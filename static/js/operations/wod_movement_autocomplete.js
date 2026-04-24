/*
ARQUIVO: autocomplete leve de movimentos no editor WOD.

POR QUE ELE EXISTE:
- reduz digitacao manual de slug/nome sem introduzir framework ou endpoint novo.

O QUE ESTE ARQUIVO FAZ:
1. le o catalogo local entregue pelo template.
2. sincroniza slug e label quando um dos campos bate com item conhecido.
3. usa datalist nativo do browser como camada de sugestao.

PONTOS CRITICOS:
- nunca bloquear digitacao livre.
- preencher o campo par apenas quando existir match exato.
*/

(function () {
    const payload = document.getElementById('wod-movement-catalog');
    if (!payload) return;

    let catalog = [];
    try {
        catalog = JSON.parse(payload.textContent || '[]');
    } catch (error) {
        catalog = [];
    }
    if (!catalog.length) return;

    const bySlug = new Map();
    const byLabel = new Map();
    catalog.forEach((item) => {
        bySlug.set(String(item.slug || '').toLowerCase(), item);
        byLabel.set(String(item.label || '').toLowerCase(), item);
    });

    function setSuggestedState(form, isSuggested) {
        form.dataset.wodSuggestedLoadType = isSuggested ? 'percentage_of_rm' : '';
        const badge = form.querySelector('[data-wod-prescription-suggestion]');
        if (badge) badge.hidden = !isSuggested;
    }

    function suggestLoadType(form, match) {
        if (!match || !match.has_rm_data) return;
        const loadTypeField = form.querySelector('[name="load_type"]');
        const loadValueField = form.querySelector('[name="load_value"]');
        if (!loadTypeField) return;

        const currentValue = String(loadTypeField.value || '').trim();
        const loadValue = String(loadValueField?.value || '').trim();
        const isDefaultish = currentValue === '' || currentValue === 'free';
        if (isDefaultish && !loadValue) {
            loadTypeField.value = 'percentage_of_rm';
            setSuggestedState(form, true);
            loadTypeField.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function syncPair(field, mode) {
        const form = field.closest('form');
        if (!form) return;

        const slugField = form.querySelector('[name="movement_slug"]');
        const labelField = form.querySelector('[name="movement_label"]');
        if (!slugField || !labelField) return;

        if (mode === 'slug') {
            const match = bySlug.get(String(slugField.value || '').trim().toLowerCase());
            if (match) {
                labelField.value = match.label;
                suggestLoadType(form, match);
            }
            return;
        }

        const match = byLabel.get(String(labelField.value || '').trim().toLowerCase());
        if (match) {
            slugField.value = match.slug;
            suggestLoadType(form, match);
        }
    }

    document.querySelectorAll('[data-wod-movement-slug="true"]').forEach((field) => {
        field.addEventListener('change', () => syncPair(field, 'slug'));
        field.addEventListener('blur', () => syncPair(field, 'slug'));
    });

    document.querySelectorAll('[data-wod-movement-label="true"]').forEach((field) => {
        field.addEventListener('change', () => syncPair(field, 'label'));
        field.addEventListener('blur', () => syncPair(field, 'label'));
    });

    document.querySelectorAll('form').forEach((form) => {
        const loadTypeField = form.querySelector('[name="load_type"]');
        if (!loadTypeField) return;
        loadTypeField.addEventListener('change', () => {
            if (loadTypeField.value !== 'percentage_of_rm') setSuggestedState(form, false);
        });
    });
})();
