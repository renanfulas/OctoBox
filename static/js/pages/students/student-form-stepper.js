/**
 * Student Form Stepper
 * Handles the 2-step registration/update flow.
 */
document.addEventListener('DOMContentLoaded', () => {
    const formRoot = document.querySelector('[data-action="submit-student-form"]');
    if (!formRoot) return;

    const steps = formRoot.querySelectorAll('.step-container');
    const stepperItems = formRoot.querySelectorAll('.stepper-item');
    const nextBtn = formRoot.querySelector('[data-action="next-step"]');
    const backBtn = formRoot.querySelector('[data-action="prev-step"]');
    const submitBtn = formRoot.querySelector('[type="submit"]');
    const stepStatus = formRoot.querySelector('[data-stepper-status]');

    if (!steps.length || !stepperItems.length) return;

    let currentStep = 0;

    const stepMeta = [
        {
            nextLabel: 'Ir para plano e pagamento',
            status: 'Etapa atual: identificacao. Confirme nome, contato e perfil antes de avancar.',
        },
        {
            nextLabel: 'Continuar',
            status: 'Etapa atual: plano e pagamento. Revise o fechamento comercial antes de salvar.',
        },
    ];

    function focusCurrentStep() {
        const activeStep = steps[currentStep];
        if (!activeStep) return;

        const focusTarget = activeStep.querySelector('input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), summary');
        if (focusTarget && typeof focusTarget.focus === 'function') {
            focusTarget.focus();
        }
    }

    function updateSteps() {
        steps.forEach((step, index) => {
            if (index === currentStep) {
                step.classList.add('active');
                step.classList.remove('hidden');
                step.setAttribute('aria-hidden', 'false');
            } else {
                step.classList.remove('active');
                step.classList.add('hidden');
                step.setAttribute('aria-hidden', 'true');
            }
        });

        stepperItems.forEach((item, index) => {
            if (index === currentStep) {
                item.classList.add('active');
                item.classList.remove('completed');
                item.setAttribute('aria-current', 'step');
            } else if (index < currentStep) {
                item.classList.add('completed');
                item.classList.remove('active');
                item.removeAttribute('aria-current');
            } else {
                item.classList.remove('active', 'completed');
                item.removeAttribute('aria-current');
            }
        });

        if (backBtn) {
            backBtn.hidden = currentStep === 0;
        }

        if (nextBtn) {
            nextBtn.hidden = currentStep === steps.length - 1;
            nextBtn.textContent = stepMeta[currentStep]?.nextLabel || 'Continuar';
        }

        if (submitBtn) {
            submitBtn.hidden = currentStep !== steps.length - 1;
        }

        if (stepStatus) {
            stepStatus.textContent = stepMeta[currentStep]?.status || '';
        }
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const nameInput = formRoot.querySelector('input[name="full_name"]');

            if (nameInput && !nameInput.value) {
                nameInput.focus();
                nameInput.classList.add('is-invalid');
                return;
            }

            if (currentStep < steps.length - 1) {
                currentStep++;
                updateSteps();
                focusCurrentStep();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentStep > 0) {
                currentStep--;
                updateSteps();
                focusCurrentStep();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    updateSteps();

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.js-generate-payment-link');
        if (btn) {
            e.preventDefault();
            const paymentId = btn.getAttribute('data-payment-id');
            if (paymentId) {
                generatePaymentLink(paymentId);
            }
        }
    });
});

function selectPlanCard(planId) {
    const select = document.getElementById('id_selected_plan');
    if (!select) return;

    select.value = planId;

    document.querySelectorAll('.plan-card').forEach(card => {
        card.classList.toggle('is-selected-plan', card.getAttribute('data-plan-id') === planId);
    });

    select.dispatchEvent(new Event('change'));
}

document.addEventListener('click', (e) => {
    const planCard = e.target.closest('[data-action="select-plan"]');
    if (planCard) {
        const planId = planCard.getAttribute('data-plan-id');
        if (planId) selectPlanCard(planId);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const payloadElement = document.getElementById('current-page-behavior');
    if (payloadElement) {
        try {
            const pagePayload = JSON.parse(payloadElement.textContent || '{}');
            const planPriceMap = pagePayload.plan_price_map || {};

            const currencyFormatter = new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            });

            document.querySelectorAll('.plan-card').forEach(card => {
                const planId = card.getAttribute('data-plan-id');
                const priceDiv = card.querySelector('.plan-card-price');
                if (priceDiv && planPriceMap[planId]) {
                    priceDiv.textContent = currencyFormatter.format(planPriceMap[planId]);
                }
            });
        } catch (e) {
            console.error('Error parsing payload for plan prices:', e);
        }
    }

    const select = document.getElementById('id_selected_plan');
    if (select && select.value) {
        selectPlanCard(select.value);
    }
});

async function generatePaymentLink(paymentId) {
    const btn = document.querySelector(`[data-payment-id="${paymentId}"]`);
    if (!btn || btn.disabled) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span>Gerando...</span>';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/v1/finance/payment-link/${paymentId}/`);
        const data = await response.json();

        if (data.url) {
            await navigator.clipboard.writeText(data.url);
            btn.innerHTML = '<span>Link copiado!</span>';

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 3000);
        } else {
            throw new Error('Url not found');
        }
    } catch (err) {
        console.error('Erro ao gerar link:', err);
        btn.innerHTML = '<span>Erro</span>';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 3000);
    }
}
