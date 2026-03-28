/**
 * OctoBox Billing Console - Master Control JS
 * Handles high-performance financial interactions for the student cockpit.
 */
(function() {
    window.openEditPayment = function(paymentId) {
        console.log("Opening edit for payment:", paymentId);
        // We trigger the standard payment management drawer
        // But in a real system, we would fetch the data and fill the form
        // For now, let's open the existing payment management drawer
        openDrawer('financial-payment-management-slot');
    };

    window.openSplitPayment = function(paymentId) {
        alert("Função 'Parcelar' acionada para o ID: " + paymentId + "\nEsta função será integrada na próxima versão Beta.");
    };

    window.openVacationFreeze = async function() {
        // Simple Prompt for days (UX Elite would use a custom modal, but let's keep it fast)
        const days = prompt("Quantos dias de congelamento/férias o aluno terá?", "15");
        if (!days || isNaN(days)) return;

        const studentId = document.querySelector('.student-financial-cockpit')?.dataset.studentId || 
                          window.location.pathname.split('/').filter(Boolean).pop();

        if (!studentId) {
            alert("Erro: ID do aluno não encontrado.");
            return;
        }

        try {
            const response = await fetch('/api/v1/finance/freeze-student/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    student_id: studentId,
                    days: parseInt(days)
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                alert("✨ Brilhante! Aluno congelado com sucesso.\nA página será atualizada para exibir as novas datas.");
                window.location.reload();
            } else {
                alert("Erro ao congelar aluno: " + (data.error || 'Erro desconhecido'));
            }
        } catch (error) {
            console.error("Freeze Error:", error);
            alert("Erro técnico ao processar congelamento.");
        }
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
})();
