/**
 * ARQUIVO: student-financial-workspace.js
 *
 * POR QUE ELE EXISTE:
 * - tira da template da ficha do aluno a delegacao de eventos do workspace financeiro.
 * - preserva drawers e gatilhos financeiros sem depender de script inline.
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. abre e fecha drawers locais do workspace financeiro.
 * 2. delega o submit do terminal Stripe.
 * 3. encaminha acoes do ledger para os handlers globais quando existirem.
 */

(function () {
  'use strict';

  const root = document.querySelector('[data-student-financial-workspace]');
  if (!root) return;

  const overlay = root.querySelector('#drawer-overlay');
  const drawers = Array.from(root.querySelectorAll('.slide-over-panel'));
  const focusableSelector =
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
  let lastTrigger = null;

  function decoratePaymentForm() {
    const amountInput = document.querySelector('#stripe-payment-form [name="amount"]');
    if (amountInput) {
      amountInput.classList.add('student-payment-management-total__input');
      amountInput.placeholder = '0,00';
    }

    document
      .querySelectorAll('#stripe-payment-form [name="due_date"], #stripe-payment-form [name="reference"]')
      .forEach(function (input) {
        input.classList.add('student-payment-management-summary__input');
      });
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

  root.addEventListener('click', function (event) {
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

    const submitStripeTrigger = event.target.closest('[data-action="submit-stripe"]');
    if (submitStripeTrigger) {
      const methodValue = submitStripeTrigger.getAttribute('data-method');
      const form = document.getElementById('stripe-payment-form');
      const methodField = document.querySelector('#stripe-payment-form [name="method"]');
      const statusMsg = document.getElementById('stripe-status-message');

      if (!form || !methodValue) return;

      if (methodField) {
        methodField.value = methodValue;
      }

      document.querySelectorAll('.elite-stripe-btn').forEach(function (button) {
        button.classList.add('disabled');
        button.classList.remove('active');
        button.setAttribute('aria-disabled', 'true');
      });

      submitStripeTrigger.classList.remove('disabled');
      submitStripeTrigger.classList.add('active');
      submitStripeTrigger.removeAttribute('aria-disabled');

      if (statusMsg) {
        statusMsg.hidden = false;
        statusMsg.textContent = 'Processando...';
      }

      form.submit();
      return;
    }

    const editPaymentTrigger = event.target.closest('[data-action="edit-payment"]');
    if (editPaymentTrigger) {
      const paymentId = editPaymentTrigger.getAttribute('data-payment-id');
      if (typeof window.openEditPayment === 'function') {
        window.openEditPayment(paymentId);
      }
      return;
    }

    const splitPaymentTrigger = event.target.closest('[data-action="split-payment"]');
    if (splitPaymentTrigger) {
      const paymentId = splitPaymentTrigger.getAttribute('data-payment-id');
      if (typeof window.openSplitPayment === 'function') {
        window.openSplitPayment(paymentId);
      }
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

  decoratePaymentForm();
})();
