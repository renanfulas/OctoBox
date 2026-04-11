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
    const handoffPanel = formRoot.querySelector('[data-student-form-handoff]');
    const initialStep = Math.max(1, Number.parseInt(formRoot.dataset.initialStep || '1', 10) || 1);

    if (!steps.length || !stepperItems.length) return;

    let currentStep = Math.min(initialStep, steps.length) - 1;

    const stepMeta = [
        {
            nextLabel: 'Ir para plano e pagamento',
<<<<<<< HEAD
=======
        },
        {
            nextLabel: 'Continuar',
>>>>>>> codex/student-page-refactor-and-ui-polish
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
        formRoot.setAttribute('data-current-step', String(currentStep + 1));

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
            const nextLabel = stepMeta[currentStep]?.nextLabel || '';
            nextBtn.hidden = currentStep !== 0 || !nextLabel;
            if (nextLabel) {
                nextBtn.textContent = nextLabel;
            }
        }

        if (submitBtn) {
            submitBtn.hidden = currentStep !== steps.length - 1;
        }

        if (handoffPanel) {
            handoffPanel.hidden = currentStep !== steps.length - 1;
        }
    }

    function jumpToStep(stepIndex) {
        const normalized = Math.max(0, Math.min(stepIndex, steps.length - 1));
        currentStep = normalized;
        updateSteps();
        focusCurrentStep();
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
                jumpToStep(currentStep + 1);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentStep > 0) {
                jumpToStep(currentStep - 1);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    updateSteps();

    document.addEventListener('click', (e) => {
        const stepLink = e.target.closest('[data-step-target]');
        if (!stepLink || !formRoot.contains(stepLink)) {
            return;
        }

        const requestedStep = Number.parseInt(stepLink.getAttribute('data-step-target') || '1', 10);
        if (!Number.isFinite(requestedStep) || requestedStep < 1) {
            return;
        }

        jumpToStep(requestedStep - 1);
    });

    document.addEventListener('keydown', (e) => {
        const stepLink = e.target.closest('[data-step-target]');
        if (!stepLink || !formRoot.contains(stepLink)) {
            return;
        }

        if (e.key !== 'Enter' && e.key !== ' ') {
            return;
        }

        e.preventDefault();

        const requestedStep = Number.parseInt(stepLink.getAttribute('data-step-target') || '1', 10);
        if (!Number.isFinite(requestedStep) || requestedStep < 1) {
            return;
        }

        jumpToStep(requestedStep - 1);
    });

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

<<<<<<< HEAD
=======
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
            console.error('Erro ao interpretar o payload dos preços do plano:', e);
        }
    }

    const select = document.getElementById('id_selected_plan');
    if (select && select.value) {
        selectPlanCard(select.value);
    }
});

>>>>>>> codex/student-page-refactor-and-ui-polish
async function generatePaymentLink(paymentId) {
    const btn = document.querySelector(`[data-payment-id="${paymentId}"]`);
    if (!btn || btn.disabled) return;

    const label = btn.querySelector('[data-payment-link-label]');
    const originalText = label ? label.textContent : btn.textContent;

    if (label) {
        label.textContent = 'Gerando...';
    } else {
        btn.textContent = 'Gerando...';
    }

    btn.disabled = true;

    try {
        const response = await fetch(`/api/v1/finance/payment-link/${paymentId}/`);
        const data = await response.json();

        if (data.url) {
            await navigator.clipboard.writeText(data.url);
            if (label) {
                label.textContent = 'Link copiado!';
            } else {
                btn.textContent = 'Link copiado!';
            }

            setTimeout(() => {
                if (label) {
                    label.textContent = originalText;
                } else {
                    btn.textContent = originalText;
                }
                btn.disabled = false;
            }, 3000);
        } else {
<<<<<<< HEAD
            throw new Error('URL nao encontrada');
=======
            throw new Error('URL n\u00e3o encontrada');
>>>>>>> codex/student-page-refactor-and-ui-polish
        }
    } catch (err) {
        console.error('Erro ao gerar link:', err);
        if (label) {
            label.textContent = 'Erro';
        } else {
            btn.textContent = 'Erro';
        }
        setTimeout(() => {
            if (label) {
                label.textContent = originalText;
            } else {
                btn.textContent = originalText;
            }
            btn.disabled = false;
        }, 3000);
    }
}
