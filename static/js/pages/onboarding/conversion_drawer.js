/**
 * Conversion Drawer - Zero Friction Standard
 * Handles express conversion from Intake to Student + Payment.
 */
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.querySelector('.conversion-drawer-overlay');
    const drawer = document.querySelector('.conversion-drawer');
    const closeBtn = document.querySelector('.drawer-close');
    const convertBtns = document.querySelectorAll('[data-action="convert-intake-to-student"]');

    if (!drawer || !overlay) return;

    let selectedIntakeId = null;
    let selectedPlanId = null;

    function openDrawer(intakeData) {
        selectedIntakeId = intakeData.id;
        document.getElementById('drawer-student-name').textContent = intakeData.name;
        document.getElementById('drawer-student-phone').textContent = intakeData.phone;
        
        overlay.classList.add('active');
        drawer.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        overlay.classList.remove('active');
        drawer.classList.remove('active');
        document.body.style.overflow = '';
        // Reset success state if any
        const success = drawer.querySelector('.success-overlay');
        if (success) success.remove();
    }

    // Intercept "Convert" buttons
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="convert-intake-to-student"]');
        if (btn) {
            e.preventDefault();
            const card = btn.closest('.intake-card');
            const name = card.querySelector('strong').textContent;
            const phone = card.querySelector('.meta-text-sm').textContent.split('|')[0].trim();
            const id = card.querySelector('input[name="intake_id"]').value;

            openDrawer({ id, name, phone });
        }
    });

    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    if (overlay) overlay.addEventListener('click', closeDrawer);

    // Plan Selection logic
    window.selectDrawerPlan = function(planId) {
        selectedPlanId = planId;
        document.querySelectorAll('.drawer-plan-card').forEach(card => {
            if (card.getAttribute('data-plan-id') === planId) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
        
        // Enable buttons
        document.querySelectorAll('.drawer-footer button').forEach(b => b.disabled = false);
    };

    // Submission logic
    window.submitExpressConversion = async function(paymentMethod) {
        if (!selectedIntakeId || !selectedPlanId) return;

        const btn = event.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span>Processando...</span>';
        btn.disabled = true;

        try {
            const response = await fetch('/api/v1/onboarding/express-convert/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    intake_id: selectedIntakeId,
                    plan_id: selectedPlanId,
                    payment_method: paymentMethod
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                showSuccess(data);
            } else {
                throw new Error(data.error || 'Erro na conversão');
            }
        } catch (err) {
            alert('Erro: ' + err.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    };

    function showSuccess(data) {
        const studentName = document.getElementById('drawer-student-name').textContent;
        const messageTemplate = `Olá ${studentName}! Tudo pronto para seu treino no Box. Aqui está seu link seguro para finalizar a matrícula: ${data.payment_url}. Qualquer dúvida, estou aqui!`;
        
        const successDiv = document.createElement('div');
        successDiv.className = 'success-overlay';
        successDiv.innerHTML = `
            <div class="success-check-icon">✅</div>
            <h2 style="margin-bottom: 8px; font-weight: 700;">Matrícula Realizada!</h2>
            <p style="text-align: center; color: var(--text-600); margin-bottom: 8px;">
                ${data.message}
            </p>
            
            ${data.payment_url ? `
                <div class="whatsapp-template-box">
                    <p><strong>Mensagem do WhatsApp:</strong></p>
                    <p style="font-style: italic;">"${messageTemplate.substring(0, 100)}..."</p>
                </div>
                <button class="button" style="width: 100%; height: 50px; background: #25D366; border-color: #25D366;" onclick="copyAndNotify(this, '${messageTemplate}')">
                    <span>Copiar Mensagem de Venda 📲</span>
                </button>
            ` : ''}
            
            <button class="button secondary" style="width: 100%; margin-top: 12px;" onclick="location.reload()">
                Fechar e Atualizar Fila
            </button>
        `;
        drawer.appendChild(successDiv);
    }

    window.copyAndNotify = async function(btn, text) {
        const original = btn.innerHTML;
        try {
            await navigator.clipboard.writeText(text);
            btn.innerHTML = '<span>Mensagem Copiada! ✅</span>';
            setTimeout(() => btn.innerHTML = original, 3000);
        } catch (e) {
            btn.innerHTML = '<span>Erro ao copiar ❌</span>';
        }
    };
});
