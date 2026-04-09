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
  let selectedPaymentId = null;

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
<<<<<<< HEAD
    syncSelectedPaymentIdFromDom();
  }

  function getCheckoutForm() {
    return document.getElementById('student-payment-checkout-form');
  }

  function getCheckoutSelectedPaymentId() {
    const checkoutForm = getCheckoutForm();
    if (!checkoutForm) {
      return null;
    }

    const paymentField = checkoutForm.querySelector('[name="payment_id"]');
    const rawValue = paymentField ? paymentField.value : checkoutForm.closest('[data-selected-payment-id]')?.getAttribute('data-selected-payment-id');
    if (!rawValue) {
      return null;
    }

    const parsedValue = Number(rawValue);
    return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : null;
  }

  function syncSelectedPaymentIdFromDom() {
    selectedPaymentId = getCheckoutSelectedPaymentId();
  }

  function getPaymentMethodLabel(methodValue) {
    if (methodValue === 'pix') return 'Pix';
    if (methodValue === 'credit_card') return 'Credito';
    if (methodValue === 'debit_card') return 'Debito';
    if (methodValue === 'cash') return 'Dinheiro';
    return 'este metodo';
  }

  function buildPaymentConfirmationDialog() {
    const dialog = document.createElement('dialog');
    dialog.className = 'student-financial-confirm-dialog';
    dialog.innerHTML = [
      '<form method="dialog" class="student-financial-confirm-dialog__card">',
      '<div class="student-financial-confirm-dialog__copy">',
      '<span class="student-financial-confirm-dialog__kicker">Confirmacao</span>',
      '<h3 class="section-title-sm">Voce realmente quer fazer este pagamento?</h3>',
      '<p class="meta-text" data-payment-confirm-copy>Confirme para registrar o recebimento.</p>',
      '</div>',
      '<div class="student-financial-confirm-dialog__actions operation-hero-action-rail">',
      '<button type="button" class="button secondary" value="cancel" data-action="cancel-payment-confirm">Nao</button>',
      '<button type="submit" class="button" value="confirm">Sim</button>',
      '</div>',
      '</form>',
    ].join('');
    document.body.appendChild(dialog);
    return dialog;
  }

  function getPaymentConfirmationDialog() {
    return document.querySelector('.student-financial-confirm-dialog') || buildPaymentConfirmationDialog();
  }

  function askPaymentConfirmation(methodValue) {
    const dialog = getPaymentConfirmationDialog();
    const form = dialog.querySelector('form');
    const cancelButton = dialog.querySelector('[data-action="cancel-payment-confirm"]');
    const copy = dialog.querySelector('[data-payment-confirm-copy]');
    const methodLabel = getPaymentMethodLabel(methodValue);

    if (copy) {
      copy.textContent = 'Voce realmente quer fazer o pagamento com ' + methodLabel + '?';
    }

    return new Promise(function(resolve) {
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
        cleanup(true);
      }

      function onCancel(event) {
        if (event) {
          event.preventDefault();
        }
        cleanup(false);
      }

      form.addEventListener('submit', onSubmit);
      cancelButton.addEventListener('click', onCancel);
      dialog.addEventListener('cancel', onCancel);
      dialog.showModal();
      cancelButton.focus();
    });
  }

  function requestPaymentEditAccess() {
    const pageRoot = document.querySelector('[data-student-id]');
    if (!pageRoot || pageRoot.dataset.lockState === 'active') {
      return;
    }

    const statusMsg = document.getElementById('student-payment-checkout-status');
    if (statusMsg) {
      statusMsg.hidden = false;
      statusMsg.textContent = 'Liberando edicao para confirmar o pagamento...';
    }

    document.dispatchEvent(new CustomEvent('student-profile-edit-request'));
=======
>>>>>>> codex/student-page-refactor-and-ui-polish
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
<<<<<<< HEAD
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      const rawBody = await response.text();
      const snippet = rawBody ? rawBody.slice(0, 120).trim() : '';
      if (snippet.startsWith('<')) {
        var titleMatch = rawBody.match(/<title>(.*?)<\/title>/i);
        var pageTitle = titleMatch && titleMatch[1] ? titleMatch[1].replace(/\s+/g, ' ').trim() : 'HTML sem titulo identificado';
        var diagnosticParts = ['HTTP ' + response.status, pageTitle];
        if (response.redirected && response.url) {
          diagnosticParts.push('redirected: ' + response.url);
        }
        throw new Error('O servidor respondeu com HTML em vez de JSON. ' + diagnosticParts.join(' | '));
      }
      throw new Error('O servidor respondeu em um formato inesperado para esta acao. HTTP ' + response.status + '.');
    }

=======
>>>>>>> codex/student-page-refactor-and-ui-polish
    const payload = await response.json();
    if (!response.ok || payload.status !== 'success') {
      throw new Error(payload.message || 'Nao foi possivel concluir a acao agora.');
    }
    applyFinancialFragments(payload.fragments);
<<<<<<< HEAD
    if (typeof payload.selected_payment_id !== 'undefined') {
      selectedPaymentId = payload.selected_payment_id || null;
    } else {
      syncSelectedPaymentIdFromDom();
    }
=======
>>>>>>> codex/student-page-refactor-and-ui-polish
    return payload;
  }

  async function submitFinancialForm(form) {
    const formData = new FormData(form);
<<<<<<< HEAD
    const actionUrl = form.getAttribute('action') || form.action;
    const payload = await handleJsonAction(actionUrl, {
=======
    const payload = await handleJsonAction(form.action, {
>>>>>>> codex/student-page-refactor-and-ui-polish
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

<<<<<<< HEAD
    selectedPaymentId = Number(paymentId);
=======
>>>>>>> codex/student-page-refactor-and-ui-polish
    const payload = await handleJsonAction(`/alunos/${studentId}/financeiro/cobranca/${paymentId}/drawer/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

<<<<<<< HEAD
    if (payload.selected_payment_id && Number(payload.selected_payment_id) !== Number(paymentId)) {
      throw new Error('A cobranca carregada nao corresponde ao item selecionado.');
    }

=======
>>>>>>> codex/student-page-refactor-and-ui-polish
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

    if (drawerId === 'student-payment-checkout-slot') {
      requestPaymentEditAccess();
    }

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

      askPaymentConfirmation(methodValue).then(function(confirmed) {
        if (!confirmed) {
          return;
        }

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
      });
<<<<<<< HEAD
=======

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
>>>>>>> codex/student-page-refactor-and-ui-polish
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
