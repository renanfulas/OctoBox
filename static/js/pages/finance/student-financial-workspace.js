/**
 * ARQUIVO: student-financial-workspace.js
 *
 * POR QUE ELE EXISTE:
 * - tira da template da ficha do aluno a delegacao de eventos do workspace financeiro.
 * - preserva drawers e gatilhos financeiros sem depender de script inline.
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. abre e fecha drawers locais do workspace financeiro.
 * 2. delega o submit do checkout de pagamento.
 * 3. encaminha acoes do ledger para os handlers globais quando existirem.
 */

(function () {
  'use strict';

  const root = document.querySelector('[data-student-financial-workspace]');
  if (!root) return;

  const overlay = root.querySelector('#drawer-overlay');
  const drawers = Array.from(root.querySelectorAll('.slide-over-panel'));
  const workspaceContent = root.querySelector('[data-financial-workspace-content]');
  const workspaceToggles = Array.from(root.querySelectorAll('[data-action="toggle-financial-workspace"]'));
  const studentId = root.getAttribute('data-student-id');
  const focusableSelector =
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
  let lastTrigger = null;

  function decoratePaymentForm() {
    const amountInput = document.querySelector('#student-payment-checkout-form [name="amount"]');
    if (amountInput) {
      amountInput.classList.add('student-payment-management-total__input');
      amountInput.placeholder = '0,00';
    }

    document
      .querySelectorAll('#student-payment-checkout-form [name="due_date"], #student-payment-checkout-form [name="reference"]')
      .forEach(function (input) {
        input.classList.add('student-payment-management-summary__input');
      });
  }

  function refreshWorkspaceUi() {
    decoratePaymentForm();
  }

  function setFinancialWorkspaceExpanded(expanded) {
    root.dataset.financialExpanded = expanded ? 'true' : 'false';

    if (workspaceContent) {
      workspaceContent.hidden = !expanded;
    }

    workspaceToggles.forEach(function (button) {
      button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      button.textContent = expanded
        ? button.getAttribute('data-label-collapse') || 'Minimizar'
        : button.getAttribute('data-label-expand') || 'Abrir';
    });
  }

  function ensureWorkspaceExpanded() {
    if (root.dataset.financialExpanded !== 'true') {
      setFinancialWorkspaceExpanded(true);
    }
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

    replaceFragment('student-page-header-slot', fragments.header);
    replaceFragment('student-page-payments-summary-slot', fragments.payments_summary);
    replaceFragment('student-financial-id-card-slot', fragments.id_card);
    replaceFragment('student-financial-kpis-slot', fragments.kpis);
    replaceFragment('student-financial-ledger-slot', fragments.ledger);
    replaceFragment('student-payment-management-content', fragments.management);
    replaceFragment('student-payment-checkout-content', fragments.checkout);
    replaceFragment('student-enrollment-management-content', fragments.enrollment);
    refreshWorkspaceUi();
  }

  function getCsrfToken() {
    const tokenInput = root.querySelector('input[name="csrfmiddlewaretoken"]');
    if (tokenInput) {
      return tokenInput.value;
    }

    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function handleJsonAction(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || payload.status !== 'success') {
      throw new Error(payload.message || 'Nao foi possivel concluir a acao agora.');
    }
    applyFinancialFragments(payload.fragments);
    return payload;
  }

  async function submitFinancialForm(form) {
    const formData = new FormData(form);
    const payload = await handleJsonAction(form.action, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCsrfToken(),
      },
      body: formData,
    });

    const statusMsg = document.getElementById('student-payment-checkout-status');
    if (statusMsg && payload.message) {
      statusMsg.hidden = false;
      statusMsg.textContent = payload.message;
    }
  }

  async function loadPaymentIntoDrawer(paymentId, trigger) {
    if (!studentId || !paymentId) {
      openDrawer('student-payment-checkout-slot', trigger);
      return;
    }

    const payload = await handleJsonAction(`/alunos/${studentId}/financeiro/cobranca/${paymentId}/drawer/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    openDrawer('student-payment-checkout-slot', trigger);
    const statusMsg = document.getElementById('student-payment-checkout-status');
    if (statusMsg && payload.message) {
      statusMsg.hidden = false;
      statusMsg.textContent = payload.message;
    }
  }

  function updatePaymentCheckoutStatus(methodValue) {
    const statusMsg = document.getElementById('student-payment-checkout-status');

    if (!statusMsg) {
      return;
    }

    statusMsg.hidden = false;
    statusMsg.textContent = methodValue === 'pix' ? 'Registrando o pagamento com Pix. Aguarde um instante.' : 'Registrando o pagamento. Aguarde um instante.';
  }

  function showPaymentSelectionStatus(dataset) {
    const statusMsg = document.getElementById('student-payment-checkout-status');
    if (!statusMsg) return;

    const details = [];
    if (dataset.paymentAmount) details.push('R$ ' + dataset.paymentAmount);
    if (dataset.paymentDue) details.push('vencimento ' + dataset.paymentDue);
    if (dataset.paymentStatus) details.push(dataset.paymentStatus.toLowerCase());

    if (!details.length) return;

    statusMsg.hidden = false;
    statusMsg.textContent = 'Cobranca pronta para revisar: ' + details.join(' • ') + '.';
  }

  function closeDrawers() {
    if (overlay) {
      overlay.classList.remove('is-active');
      overlay.setAttribute('aria-hidden', 'true');
    }

    drawers.forEach(function (drawer) {
      drawer.classList.remove('is-active');
      drawer.setAttribute('aria-hidden', 'true');
    });

    root.querySelectorAll('[data-action="open-drawer"][aria-expanded="true"]').forEach(function (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
    });

    if (lastTrigger && typeof lastTrigger.focus === 'function') {
      lastTrigger.focus();
      lastTrigger = null;
    }
  }

  function trapDrawerFocus(drawer, event) {
    if (event.key !== 'Tab') return;

    const focusables = Array.from(drawer.querySelectorAll(focusableSelector)).filter(function (element) {
      return element.offsetParent !== null || element === document.activeElement;
    });
    if (!focusables.length) return;

    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return;
    }

    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function focusDrawer(drawer) {
    const firstFocusable = drawer.querySelector(focusableSelector);
    if (firstFocusable) {
      firstFocusable.focus();
      return;
    }

    drawer.focus();
  }

  function openDrawer(drawerId, trigger) {
    if (!drawerId) return;

    const drawer = document.getElementById(drawerId);
    if (!drawer) return;

    ensureWorkspaceExpanded();
    lastTrigger = trigger || null;

    closeDrawers();

    if (overlay) {
      overlay.classList.add('is-active');
      overlay.setAttribute('aria-hidden', 'false');
    }

    drawer.classList.add('is-active');
    drawer.setAttribute('aria-hidden', 'false');
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'true');
    }

    focusDrawer(drawer);
  }

  window.openStudentFinancialDrawer = openDrawer;
  window.applyStudentFinancialFragments = applyFinancialFragments;

  root.addEventListener('click', function (event) {
    const workspaceToggle = event.target.closest('[data-action="toggle-financial-workspace"]');
    if (workspaceToggle) {
      const expanded = root.dataset.financialExpanded === 'true';
      if (expanded) {
        closeDrawers();
      }
      setFinancialWorkspaceExpanded(!expanded);
      if (!expanded) {
        root.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return;
    }

    const confirmTrigger = event.target.closest('button[type="submit"][data-confirm="true"]');
    if (confirmTrigger) {
      const confirmMessage =
        confirmTrigger.getAttribute('data-confirm-message') || 'Tem certeza que deseja continuar com esta acao?';
      if (!window.confirm(confirmMessage)) {
        event.preventDefault();
        return;
      }
    }

    const openDrawerTrigger = event.target.closest('[data-action="open-drawer"]');
    if (openDrawerTrigger) {
      openDrawer(openDrawerTrigger.getAttribute('data-drawer-id'), openDrawerTrigger);
      return;
    }

    const closeDrawerTrigger = event.target.closest('[data-action="close-drawers"]');
    if (closeDrawerTrigger) {
      closeDrawers();
      return;
    }

    const submitPaymentTrigger = event.target.closest('[data-action="submit-stripe"]');
    if (submitPaymentTrigger) {
      const methodValue = submitPaymentTrigger.getAttribute('data-method');
      const form = document.getElementById('student-payment-checkout-form');
      const methodField = document.querySelector('#student-payment-checkout-form [name="method"]');

      if (!form || !methodValue) return;

      if (methodField) {
        methodField.value = methodValue;
      }

      document.querySelectorAll('.student-payment-method-button').forEach(function (button) {
        button.classList.add('is-disabled');
        button.classList.remove('is-active');
        button.setAttribute('aria-disabled', 'true');
      });

      submitPaymentTrigger.classList.remove('is-disabled');
      submitPaymentTrigger.classList.add('is-active');
      submitPaymentTrigger.removeAttribute('aria-disabled');

      updatePaymentCheckoutStatus(methodValue);

      submitFinancialForm(form).catch(function (error) {
        const statusMsg = document.getElementById('student-payment-checkout-status');
        if (statusMsg) {
          statusMsg.hidden = false;
          statusMsg.textContent = error.message;
        }
      });
      return;
    }

    const editPaymentTrigger = event.target.closest('[data-action="edit-payment"]');
    if (editPaymentTrigger) {
      loadPaymentIntoDrawer(editPaymentTrigger.getAttribute('data-payment-id'), editPaymentTrigger).catch(function () {
        openDrawer('student-payment-checkout-slot', editPaymentTrigger);
        showPaymentSelectionStatus(editPaymentTrigger.dataset);
      });
      return;
    }

    const vacationFreezeTrigger = event.target.closest('[data-action="vacation-freeze"]');
    if (vacationFreezeTrigger && typeof window.openVacationFreeze === 'function') {
      window.openVacationFreeze();
    }
  });

  root.addEventListener('keydown', function (event) {
    const activeDrawer = drawers.find(function (drawer) {
      return drawer.classList.contains('is-active');
    });
    if (!activeDrawer) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closeDrawers();
      return;
    }

    trapDrawerFocus(activeDrawer, event);
  });

  root.addEventListener('submit', function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (!form.matches('#student-payment-checkout-form, .student-enrollment-management-form')) {
      return;
    }

    event.preventDefault();
    submitFinancialForm(form).catch(function (error) {
      window.alert(error.message);
    });
  });

  window.refreshStudentFinancialWorkspaceUi = refreshWorkspaceUi;
  setFinancialWorkspaceExpanded(root.dataset.financialExpanded === 'true');
  decoratePaymentForm();
})();
