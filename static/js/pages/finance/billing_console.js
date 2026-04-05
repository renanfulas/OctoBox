/**
 * ARQUIVO: billing_console.js
 *
 * POR QUE ELE EXISTE:
 * - concentra as acoes sensiveis da gestao ampliada sem depender de prompt solto ou placeholder enganoso.
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. abre um dialogo simples para congelamento do aluno.
 * 2. coleta os dias de pausa com confirmacao explicita.
 * 3. envia a mutacao para a API e recarrega a pagina como fallback seguro desta onda.
 *
 * PONTOS CRITICOS:
 * - esta onda prioriza risco e confianca operacional, nao recomposicao fina de estado.
 * - o reload ainda existe como fallback consciente ate a onda de recomposicao da superficie.
 */
(function () {
  'use strict';

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + '=') {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function buildFreezeDialog() {
    const dialog = document.createElement('dialog');
    dialog.className = 'payment-freeze-dialog';
    dialog.innerHTML = `
      <form method="dialog" class="stack-16" style="min-width:min(420px,92vw);border:0;padding:0;">
        <div class="stack-8">
          <p class="eyebrow">Congelamento</p>
          <h3 class="section-title-sm">Marcar ferias ou congelar matricula</h3>
          <p class="meta-text">Confirme quantos dias o aluno ficara pausado. O sistema vai empurrar vencimentos pendentes e o fim do vinculo ativo.</p>
        </div>
        <label class="stack-4">
          <span class="field-label">Dias de congelamento</span>
          <input name="days" type="number" min="1" step="1" value="15" class="input" required />
        </label>
        <p class="meta-text" data-freeze-feedback hidden></p>
        <div class="actions actions-tight">
          <button type="button" class="button secondary" value="cancel">Cancelar</button>
          <button type="submit" class="button success" value="confirm">Confirmar congelamento</button>
        </div>
      </form>
    `;
    document.body.appendChild(dialog);
    return dialog;
  }

  function getFreezeDialog() {
    return document.querySelector('.payment-freeze-dialog') || buildFreezeDialog();
  }

  function replaceFragment(slotId, html) {
    const slot = document.getElementById(slotId);
    if (!slot || typeof html !== 'string') {
      return;
    }
    slot.innerHTML = html;
  }

  function applyFinancialFragments(fragments) {
    if (!fragments) {
      return;
    }

    replaceFragment('student-financial-id-card-slot', fragments.id_card);
    replaceFragment('student-financial-kpis-slot', fragments.kpis);
    replaceFragment('student-financial-ledger-slot', fragments.ledger);
    replaceFragment('student-payment-management-content', fragments.management);
    replaceFragment('student-payment-checkout-content', fragments.checkout);
    replaceFragment('student-enrollment-management-content', fragments.enrollment);

    if (typeof window.refreshStudentFinancialWorkspaceUi === 'function') {
      window.refreshStudentFinancialWorkspaceUi();
    }
  }

  function askFreezeDays() {
    const dialog = getFreezeDialog();
    const form = dialog.querySelector('form');
    const cancelButton = dialog.querySelector('button[value="cancel"]');
    const feedback = dialog.querySelector('[data-freeze-feedback]');

    feedback.hidden = true;
    feedback.textContent = '';

    return new Promise(function (resolve) {
      function cleanup(result) {
        form.removeEventListener('submit', onSubmit);
        cancelButton.removeEventListener('click', onCancel);
        dialog.removeEventListener('cancel', onCancel);
        if (dialog.open) {
          dialog.close();
        }
        resolve(result);
      }

      function onSubmit(event) {
        event.preventDefault();
        const days = parseInt(form.elements.days.value, 10);
        if (!days || days < 1) {
          feedback.hidden = false;
          feedback.textContent = 'Informe pelo menos 1 dia para continuar.';
          return;
        }
        cleanup(days);
      }

      function onCancel() {
        cleanup(null);
      }

      form.addEventListener('submit', onSubmit);
      cancelButton.addEventListener('click', onCancel);
      dialog.addEventListener('cancel', onCancel);
      dialog.showModal();
      form.elements.days.focus();
      form.elements.days.select();
    });
  }

  window.openVacationFreeze = async function () {
    const root = document.querySelector('[data-student-financial-workspace]');
    const studentId = root ? root.getAttribute('data-student-id') : '';
    if (!studentId) {
      window.alert('Nao foi possivel identificar o aluno desta ficha.');
      return;
    }

    const days = await askFreezeDays();
    if (!days) {
      return;
    }

    try {
      const response = await fetch('/api/v1/finance/freeze-student/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
          student_id: studentId,
          days: days,
        }),
      });

      const data = await response.json();
      if (!response.ok || data.status !== 'success') {
        window.alert(data.error || 'Nao foi possivel concluir o congelamento agora.');
        return;
      }

      applyFinancialFragments(data.fragments);
      window.alert('Congelamento confirmado. A pagina e os indicadores foram atualizados.');
    } catch (error) {
      console.error('Freeze Error:', error);
      window.alert('O congelamento falhou por erro tecnico. Tente novamente em instantes.');
    }
  };
})();
