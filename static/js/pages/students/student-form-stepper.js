/**
 * Student Form Stepper - SaaS Elite Standard
 * Handles the 2-step registration/update flow.
 */
document.addEventListener('DOMContentLoaded', () => {
    const steps = document.querySelectorAll('.step-container');
    const stepperItems = document.querySelectorAll('.stepper-item');
    const nextBtn = document.querySelector('[data-action="next-step"]');
    const backBtn = document.querySelector('[data-action="prev-step"]');
    const submitBtn = document.querySelector('[type="submit"]');

    if (!steps.length || !stepperItems.length) return;

    let currentStep = 0;

    function updateSteps() {
        steps.forEach((step, index) => {
            if (index === currentStep) {
                step.classList.add('active');
                step.classList.remove('hidden');
            } else {
                step.classList.remove('active');
                step.classList.add('hidden');
            }
        });

        stepperItems.forEach((item, index) => {
            if (index === currentStep) {
                item.classList.add('active');
                item.classList.remove('completed');
            } else if (index < currentStep) {
                item.classList.add('completed');
                item.classList.remove('active');
            } else {
                item.classList.remove('active', 'completed');
            }
        });

        // Toggle buttons via hidden attribute (no inline .style.display)
        if (currentStep === 0) {
            backBtn.hidden = true;
            nextBtn.hidden = false;
            submitBtn.hidden = true;
        } else if (currentStep === steps.length - 1) {
            backBtn.hidden = false;
            nextBtn.hidden = true;
            submitBtn.hidden = false;
        } else {
            backBtn.hidden = false;
            nextBtn.hidden = false;
            submitBtn.hidden = true;
        }
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            // Basic validation for Step 1
            const nameInput = document.querySelector('input[name="full_name"]');
            const phoneInput = document.querySelector('input[name="phone"]');
            
            if (nameInput && !nameInput.value) {
                nameInput.focus();
                nameInput.classList.add('is-invalid');
                return;
            }
            
            if (currentStep < steps.length - 1) {
                currentStep++;
                updateSteps();
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
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }

    // Initialize
    updateSteps();

    // Event Delegation for Payment Link Generation
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

/**
 * Visual Plan Selector
 */
function selectPlanCard(planId) {
    const select = document.getElementById('id_selected_plan');
    if (!select) return;

    // Update select value
    select.value = planId;
    
    // Toggle active class on cards (no inline .style.*)
    document.querySelectorAll('.plan-card').forEach(card => {
        card.classList.toggle('is-selected-plan', card.getAttribute('data-plan-id') === planId);
    });

    // Dispatch change event to trigger other UI updates (price calculation)
    select.dispatchEvent(new Event('change'));
}

// Event delegation: plan card selection via data-action
document.addEventListener('click', (e) => {
    const planCard = e.target.closest('[data-action="select-plan"]');
    if (planCard) {
        const planId = planCard.getAttribute('data-plan-id');
        if (planId) selectPlanCard(planId);
    }
});

// Handle initial selection if edit mode and populate prices
document.addEventListener('DOMContentLoaded', () => {
    // 1. Populate Prices
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

    // 2. Initial Selection
    const select = document.getElementById('id_selected_plan');
    if (select && select.value) {
        selectPlanCard(select.value);
    }
});

/**
 * Payment Link Generator
 */
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
            // Copy to clipboard
            await navigator.clipboard.writeText(data.url);
            btn.innerHTML = '<span>Link Copiado! ✅</span>';
            
            // Show a temporary success message
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 3000);
        } else {
            throw new Error('Url not found');
        }
    } catch (err) {
        console.error('Erro ao gerar link:', err);
        btn.innerHTML = '<span>Erro ❌</span>';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 3000);
    }
}

// generatePaymentLink is already called via event delegation above (L91-100)
// No window global needed.
