/*
ARQUIVO: comportamento do card de cobranca curta da recepcao.

POR QUE ELE EXISTE:
- move o fluxo de WhatsApp para a camada de asset
- tira fetch e mensagem operacional de dentro do template
*/

(function () {
    const pageRoot = document.querySelector('[data-page="reception"]');

    if (!pageRoot) {
        return;
    }

    function buildReceptionWhatsAppMessage(button) {
        const studentName = button.dataset.studentName || 'aluno';
        const operatorName = button.dataset.operatorName || 'Equipe';
        const isLateTenDays = button.dataset.isLate10Days === '1';
        const lines = [
            `Oi, ${studentName}! Aqui e a ${operatorName} do Cross.`,
            '',
            'Tudo bem por ai?',
            '',
            'Passando so pra dar um toque: vi que ficou uma mensalidade em aberto aqui (pode ter escapado na correria mesmo, acontece!).',
        ];

        if (isLateTenDays) {
            lines.push('');
            lines.push('Pra nao correr risco de bloquear o acesso nos treinos, que tal regularizar?');
        }

        lines.push('');
        lines.push('Se quiser resolver agora, te mando a chave PIX na hora.');
        lines.push('Ou, se preferir, a gente acerta tranquilo no seu proximo treino.');
        lines.push('');
        lines.push('Qualquer coisa e so chamar, ta?');
        lines.push('A gente curte muito ter voce treinando com a gente!');

        return lines.join('\n');
    }

    function buildWhatsAppHref(button) {
        const cleanPhone = button.dataset.cleanPhone;

        if (!cleanPhone) {
            return '';
        }

        const message = buildReceptionWhatsAppMessage(button);
        return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message)}`;
    }

    function registerOperationalContact(button) {
        const communicationUrl = button.dataset.communicationUrl;
        const studentId = button.dataset.studentId;
        const paymentId = button.dataset.paymentId;
        const form = button.closest('form');
        const csrfToken = form?.querySelector('[name=csrfmiddlewaretoken]')?.value;

        if (!communicationUrl || !studentId || !paymentId || !csrfToken) {
            return Promise.resolve();
        }

        const payload = new URLSearchParams({
            action_kind: button.dataset.actionKind || 'overdue',
            student_id: studentId,
            payment_id: paymentId,
        });

        return fetch(communicationUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: payload.toString(),
        }).catch(() => undefined);
    }

    pageRoot.addEventListener('click', function (event) {
        const button = event.target.closest('[data-action="launch-reception-whatsapp"]');

        if (!button) {
            return;
        }

        event.preventDefault();

        const whatsappHref = buildWhatsAppHref(button);

        if (!whatsappHref) {
            return;
        }

        const popup = window.open(whatsappHref, '_blank', 'noopener');

        if (!popup) {
            window.open(whatsappHref, '_blank');
        }

        registerOperationalContact(button);
    });
})();
