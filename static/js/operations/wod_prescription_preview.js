/*
ARQUIVO: preview local da prescricao no editor WOD.

POR QUE ELE EXISTE:
- traduz a combinacao de movimento, sets/reps e carga em leitura humana imediata.

O QUE ESTE ARQUIVO FAZ:
1. observa formularios de movimento no editor.
2. monta label local de prescricao.
3. sinaliza quando o movimento tem base de RM no catalogo local.

PONTOS CRITICOS:
- nao substituir validacao do backend.
- nao prometer carga recomendada numerica por aluno nesta etapa.
*/

(function () {
    const catalogNode = document.getElementById('wod-movement-catalog');
    const rosterNode = document.getElementById('wod-movement-rm-roster');
    let catalog = [];
    let roster = [];
    if (catalogNode) {
        try {
            catalog = JSON.parse(catalogNode.textContent || '[]');
        } catch (error) {
            catalog = [];
        }
    }
    if (rosterNode) {
        try {
            roster = JSON.parse(rosterNode.textContent || '[]');
        } catch (error) {
            roster = [];
        }
    }

    const bySlug = new Map();
    const byLabel = new Map();
    const rosterBySlug = new Map();
    catalog.forEach((item) => {
        bySlug.set(String(item.slug || '').toLowerCase(), item);
        byLabel.set(String(item.label || '').toLowerCase(), item);
    });
    roster.forEach((item) => {
        rosterBySlug.set(String(item.slug || '').toLowerCase(), item);
    });

    function roundToIncrement(value, increment) {
        return Math.round(value / increment) * increment;
    }

    function buildPrescriptionLabel(form) {
        const sets = form.querySelector('[name="sets"]')?.value;
        const reps = form.querySelector('[name="reps"]')?.value;
        const loadType = form.querySelector('[name="load_type"]')?.value;
        const loadValue = form.querySelector('[name="load_value"]')?.value;
        const bits = [];

        if (sets) bits.push(`${sets} series`);
        if (reps) bits.push(`${reps} reps`);

        if (loadType === 'percentage_of_rm' && loadValue) bits.push(`@ ${loadValue}% do RM`);
        else if (loadType === 'fixed_kg' && loadValue) bits.push(`@ ${loadValue} kg`);
        else if (loadType === 'free') bits.push('carga livre');

        return bits.join(' · ') || 'Sem detalhe de prescricao ainda.';
    }

    function buildContext(form) {
        const slug = String(form.querySelector('[name="movement_slug"]')?.value || '').trim().toLowerCase();
        const label = String(form.querySelector('[name="movement_label"]')?.value || '').trim().toLowerCase();
        const loadType = form.querySelector('[name="load_type"]')?.value;
        const matched = bySlug.get(slug) || byLabel.get(label);

        if (loadType === 'percentage_of_rm' && matched?.has_rm_data) {
            return 'Movimento com base de RM na turma: o preview por aluno aparece no painel RM da aula.';
        }
        if (loadType === 'percentage_of_rm') {
            return 'Percentual de RM sem base conhecida na turma: a carga final depende do RM cadastrado por aluno.';
        }
        if (loadType === 'fixed_kg') {
            return 'Carga fechada: o aluno recebe uma prescricao direta em kg.';
        }
        if (loadType === 'free') {
            return 'Carga livre: o coach deixa o ajuste final para leitura de esforco e contexto da aula.';
        }
        return 'Defina o tipo de carga para completar a leitura.';
    }

    function updatePreview(form) {
        const panel = form.querySelector('[data-wod-prescription-preview]');
        if (!panel) return;
        const labelNode = panel.querySelector('[data-wod-prescription-label]');
        const contextNode = panel.querySelector('[data-wod-prescription-context]');
        const suggestionNode = panel.querySelector('[data-wod-prescription-suggestion]');
        const loadingNode = panel.querySelector('[data-wod-prescription-loading]');
        const backendNode = panel.querySelector('[data-wod-prescription-source="backend"]');
        const localNode = panel.querySelector('[data-wod-prescription-source="local"]');
        const studentsNode = panel.querySelector('[data-wod-prescription-students]');
        const missingNode = panel.querySelector('[data-wod-prescription-missing]');
        const missingCopyNode = panel.querySelector('[data-wod-prescription-missing-copy]');
        const slug = String(form.querySelector('[name="movement_slug"]')?.value || '').trim().toLowerCase();
        const loadType = form.querySelector('[name="load_type"]')?.value;
        const loadValue = Number(form.querySelector('[name="load_value"]')?.value || 0);
        if (labelNode) labelNode.textContent = buildPrescriptionLabel(form);
        if (contextNode) contextNode.textContent = buildContext(form);
        if (suggestionNode) suggestionNode.hidden = form.dataset.wodSuggestedLoadType !== 'percentage_of_rm';
        if (loadingNode) loadingNode.hidden = true;
        if (backendNode) backendNode.hidden = true;
        if (localNode) localNode.hidden = false;

        if (!studentsNode || !missingNode || !missingCopyNode) return;
        studentsNode.hidden = true;
        missingNode.hidden = true;
        studentsNode.innerHTML = '';

        const rosterEntry = rosterBySlug.get(slug);
        if (loadType !== 'percentage_of_rm') return;
        if (!rosterEntry || !Array.isArray(rosterEntry.students) || !rosterEntry.students.length) {
            missingNode.hidden = false;
            missingCopyNode.textContent = 'Sem RM registrado para este movimento na turma.';
            return;
        }
        if (!loadValue) {
            missingNode.hidden = false;
            missingCopyNode.textContent = 'Defina o percentual para estimar a carga por aluno.';
            return;
        }

        const topStudents = rosterEntry.students.slice(0, 4);
        studentsNode.innerHTML = topStudents
            .map((student) => {
                const rm = Number(student.one_rep_max_kg || 0);
                const recommended = roundToIncrement((rm * loadValue) / 100, 2.5).toFixed(2);
                return `
                    <article class="coach-wod-detail-card">
                        <p class="eyebrow">${student.name}</p>
                        <strong>${recommended} kg</strong>
                        <p>RM base: ${student.one_rep_max_kg} kg</p>
                    </article>
                `;
            })
            .join('');
        studentsNode.hidden = false;
    }

    async function hydrateFromBackend(form) {
        const endpoint = form.dataset.wodPrescriptionEndpoint;
        if (!endpoint) return;
        const slug = String(form.querySelector('[name="movement_slug"]')?.value || '').trim();
        const loadType = String(form.querySelector('[name="load_type"]')?.value || '').trim();
        const loadValue = String(form.querySelector('[name="load_value"]')?.value || '').trim();
        const panel = form.querySelector('[data-wod-prescription-preview]');
        const studentsNode = panel?.querySelector('[data-wod-prescription-students]');
        const missingNode = panel?.querySelector('[data-wod-prescription-missing]');
        const missingCopyNode = panel?.querySelector('[data-wod-prescription-missing-copy]');
        const contextNode = panel?.querySelector('[data-wod-prescription-context]');
        const loadingNode = panel?.querySelector('[data-wod-prescription-loading]');
        const backendNode = panel?.querySelector('[data-wod-prescription-source="backend"]');
        const localNode = panel?.querySelector('[data-wod-prescription-source="local"]');

        if (!endpoint || !slug || loadType !== 'percentage_of_rm' || !loadValue || !panel || !studentsNode || !missingNode || !missingCopyNode) {
            return;
        }

        const requestId = String(Date.now() + Math.random());
        form.dataset.wodPreviewRequestId = requestId;
        if (loadingNode) loadingNode.hidden = false;
        if (backendNode) backendNode.hidden = true;

        try {
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('movement_slug', slug);
            url.searchParams.set('load_type', loadType);
            url.searchParams.set('load_value', loadValue);
            const response = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
            if (!response.ok || form.dataset.wodPreviewRequestId !== requestId) return;
            const payload = await response.json();
            if (form.dataset.wodPreviewRequestId !== requestId) return;

            if (contextNode && payload.summary) contextNode.textContent = payload.summary;
            if (loadingNode) loadingNode.hidden = true;
            if (backendNode) backendNode.hidden = false;
            if (localNode) localNode.hidden = true;
            studentsNode.innerHTML = '';
            studentsNode.hidden = true;
            missingNode.hidden = true;

            if (Array.isArray(payload.students) && payload.students.length) {
                studentsNode.innerHTML = payload.students
                    .map(
                        (student) => `
                            <article class="coach-wod-detail-card">
                                <p class="eyebrow">${student.name}</p>
                                <strong>${student.rounded_load_label}</strong>
                                <p>RM base: ${student.one_rep_max_label}</p>
                                <p>${student.observation}</p>
                            </article>
                        `
                    )
                    .join('');
                studentsNode.hidden = false;
            } else if (Array.isArray(payload.missing_students) && payload.missing_students.length) {
                missingCopyNode.textContent = `Sem RM registrado: ${payload.missing_students.join(', ')}${payload.missing_students_remaining ? ` e mais ${payload.missing_students_remaining} aluno(s).` : '.'}`;
                missingNode.hidden = false;
            }
        } catch (error) {
            if (loadingNode) loadingNode.hidden = true;
            if (backendNode) backendNode.hidden = true;
            if (localNode) localNode.hidden = false;
            return;
        }
    }

    document.querySelectorAll('form').forEach((form) => {
        if (!form.querySelector('[name="movement_slug"]') || !form.querySelector('[name="load_type"]')) return;
        ['input', 'change', 'blur'].forEach((eventName) => {
            form.addEventListener(
                eventName,
                () => {
                    updatePreview(form);
                    hydrateFromBackend(form);
                },
                true
            );
        });
        updatePreview(form);
        hydrateFromBackend(form);
    });
})();
