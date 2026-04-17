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
  let quickSaleSuggestionTimer = null;
  let quickSaleSuggestionController = null;

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

  function decorateQuickSaleForm() {
    const descriptionInput = document.querySelector('#student-quick-sale-form [name="description"]');
    if (descriptionInput) {
      descriptionInput.classList.add('student-payment-management-summary__input');
    }

    const amountInput = document.querySelector('#student-quick-sale-form [name="amount"]');
    if (amountInput) {
      amountInput.classList.add('student-payment-management-total__input');
      amountInput.placeholder = '0,00';
    }

    document
      .querySelectorAll('#student-quick-sale-form [name="reference"], #student-quick-sale-form [name="notes"]')
      .forEach(function (input) {
        input.classList.add('student-payment-management-summary__input');
      });
  }

  function refreshWorkspaceUi() {
    decoratePaymentForm();
    decorateQuickSaleForm();
    if (window.OctoForms && typeof window.OctoForms.applyMaskedFields === 'function') {
      window.OctoForms.applyMaskedFields(document);
    }
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
    replaceFragment('student-quick-sale-content', fragments.quick_sales);
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

    const payload = await response.json();
    if (!response.ok || payload.status !== 'success') {
      throw new Error(payload.message || 'Nao foi possivel concluir a acao agora.');
    }
    applyFinancialFragments(payload.fragments);
    if (typeof payload.selected_payment_id !== 'undefined') {
      selectedPaymentId = payload.selected_payment_id || null;
    } else {
      syncSelectedPaymentIdFromDom();
    }
    return payload;
  }

  async function submitFinancialForm(form) {
    const formData = new FormData(form);
    const actionUrl = form.getAttribute('action') || form.action;
    const payload = await handleJsonAction(actionUrl, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCsrfToken(),
      },
      body: formData,
    });

    const statusMsg = form.id === 'student-quick-sale-form'
      ? document.getElementById('student-quick-sale-status')
      : document.getElementById('student-payment-checkout-status');
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

    selectedPaymentId = Number(paymentId);
    const payload = await handleJsonAction(`/alunos/${studentId}/financeiro/cobranca/${paymentId}/drawer/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    if (payload.selected_payment_id && Number(payload.selected_payment_id) !== Number(paymentId)) {
      throw new Error('A cobranca carregada nao corresponde ao item selecionado.');
    }

    openDrawer('student-payment-checkout-slot', trigger);
    const statusMsg = document.getElementById('student-payment-checkout-status');
    if (statusMsg && payload.message) {
      statusMsg.hidden = false;
      statusMsg.textContent = payload.message;
    }
  }

  async function loadCheckoutDrawer(trigger) {
    if (!studentId) {
      openDrawer('student-payment-checkout-slot', trigger);
      return;
    }

    const payload = await handleJsonAction(`/alunos/${studentId}/financeiro/cobranca/drawer/`, {
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

  async function loadStandalonePaymentDrawer(trigger) {
    if (!studentId) {
      openDrawer('student-payment-checkout-slot', trigger);
      return;
    }

    selectedPaymentId = null;
    const payload = await handleJsonAction(`/alunos/${studentId}/financeiro/cobranca/avulsa/drawer/`, {
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

  async function loadQuickSaleDrawer(trigger) {
    if (!studentId) {
      openDrawer('student-quick-sale-slot', trigger);
      return;
    }

    const payload = await handleJsonAction(`/alunos/${studentId}/pagamentos-rapidos/drawer/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    openDrawer('student-quick-sale-slot', trigger);
    const statusMsg = document.getElementById('student-quick-sale-status');
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

  function updateQuickSaleStatus(message) {
    const statusMsg = document.getElementById('student-quick-sale-status');
    if (!statusMsg) {
      return;
    }
    statusMsg.hidden = false;
    statusMsg.textContent = message;
  }

  function setQuickSaleRecognition(mode, copy) {
    const rootElement = document.getElementById('student-quick-sale-recognition');
    const badge = document.getElementById('student-quick-sale-recognition-badge');
    const text = document.getElementById('student-quick-sale-recognition-copy');
    if (!rootElement || !badge || !text) {
      return;
    }

    rootElement.dataset.mode = mode;
    rootElement.classList.remove(
      'student-quick-sale-recognition--manual',
      'student-quick-sale-recognition--recognized',
      'student-quick-sale-recognition--suggested'
    );
    rootElement.classList.add('student-quick-sale-recognition--' + mode);

    if (mode === 'recognized') {
      badge.textContent = 'Reconhecido';
    } else if (mode === 'suggested') {
      badge.textContent = 'Sugestao';
    } else {
      badge.textContent = 'Manual';
    }
    text.textContent = copy;
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getQuickSaleAutocompleteElements() {
    return {
      panel: document.getElementById('student-quick-sale-autocomplete'),
      results: document.getElementById('student-quick-sale-suggestions'),
    };
  }

  function hideQuickSaleSuggestions() {
    const elements = getQuickSaleAutocompleteElements();
    if (elements.panel) {
      elements.panel.hidden = true;
    }
    if (elements.results) {
      elements.results.innerHTML = '';
    }
  }

  function renderQuickSaleSuggestions(memory) {
    const elements = getQuickSaleAutocompleteElements();
    if (!elements.panel || !elements.results) {
      return;
    }

    const match = memory && memory.match ? memory.match : null;
    const suggestions = match && Array.isArray(match.suggestions) ? match.suggestions : [];

    if (!match || (!suggestions.length && !match.resolved_template_id)) {
      hideQuickSaleSuggestions();
      setQuickSaleRecognition('manual', 'O sistema ainda nao reconheceu um produto salvo.');
      return;
    }

    const cards = [];

    if (match.resolved_template_id) {
      const exactLabel = match.resolution_mode === 'exact_alias' ? 'Alias reconhecido' : 'Produto reconhecido';
      const exactPrice = match.resolved_template_unit_price || '';
      const exactDescription = match.resolved_template_label || 'Produto salvo';
      cards.push(
        '<button class="student-quick-sale-suggestion is-recognized" type="button" data-action="apply-quick-sale-memory" data-template-id="' +
          escapeHtml(match.resolved_template_id) +
          '" data-description="' +
          escapeHtml(exactDescription) +
          '" data-amount="' +
          escapeHtml(exactPrice) +
          '">' +
          '<span class="student-quick-sale-suggestion__meta">' + escapeHtml(exactLabel) + '</span>' +
          '<strong>' + escapeHtml(exactDescription) + '</strong>' +
          (exactPrice ? '<span>R$ ' + escapeHtml(exactPrice) + '</span>' : '<span>Use o valor que voce digitar.</span>') +
        '</button>'
      );
    }

    suggestions.forEach(function (item) {
      cards.push(
        '<button class="student-quick-sale-suggestion" type="button" data-action="apply-quick-sale-memory" data-template-id="' +
          escapeHtml(item.template_id) +
          '" data-description="' +
          escapeHtml(item.label) +
          '" data-amount="' +
          escapeHtml(item.unit_price) +
          '">' +
          '<span class="student-quick-sale-suggestion__meta">Parecido com ' + escapeHtml(Math.round((item.confidence || 0) * 100)) + '%</span>' +
          '<strong>' + escapeHtml(item.label) + '</strong>' +
          '<span>R$ ' + escapeHtml(item.unit_price) + '</span>' +
        '</button>'
      );
    });

    if (!cards.length) {
      hideQuickSaleSuggestions();
      return;
    }

    elements.panel.hidden = false;
    elements.results.innerHTML = cards.join('');

    if (match.resolved_template_id) {
      setQuickSaleRecognition('recognized', 'Produto conhecido na base. Um clique preenche descricao e valor padrao.');
      return;
    }

    setQuickSaleRecognition('suggested', 'Existe algo parecido salvo. Revise a sugestao antes de confirmar.');
  }

  async function fetchQuickSaleSuggestions(query) {
    if (!studentId) {
      return null;
    }

    if (quickSaleSuggestionController) {
      quickSaleSuggestionController.abort();
    }

    quickSaleSuggestionController = new AbortController();
    const response = await fetch(`/alunos/${studentId}/pagamentos-rapidos/sugestoes/?q=${encodeURIComponent(query)}`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      signal: quickSaleSuggestionController.signal,
    });

    const payload = await response.json();
    if (!response.ok || payload.status !== 'success') {
      throw new Error(payload.message || 'Nao foi possivel carregar as sugestoes agora.');
    }
    return payload.memory;
  }

  function scheduleQuickSaleSuggestions(query) {
    const normalizedQuery = String(query || '').trim();
    if (quickSaleSuggestionTimer) {
      window.clearTimeout(quickSaleSuggestionTimer);
      quickSaleSuggestionTimer = null;
    }

    if (!normalizedQuery || normalizedQuery.length < 2) {
      if (quickSaleSuggestionController) {
        quickSaleSuggestionController.abort();
      }
      hideQuickSaleSuggestions();
      setQuickSaleRecognition('manual', 'O sistema ainda nao reconheceu um produto salvo.');
      return;
    }

    quickSaleSuggestionTimer = window.setTimeout(function () {
      fetchQuickSaleSuggestions(normalizedQuery)
        .then(function (memory) {
          renderQuickSaleSuggestions(memory);
          if (memory && memory.match && memory.match.resolved_template_id) {
            updateQuickSaleStatus('Produto reconhecido. Se quiser, clique na sugestao para preencher tudo mais rapido.');
          }
        })
        .catch(function (error) {
          if (error && error.name === 'AbortError') {
            return;
          }
          hideQuickSaleSuggestions();
        });
    }, 220);
  }

  function applyQuickSaleMemory(trigger) {
    const form = document.getElementById('student-quick-sale-form');
    if (!form || !trigger) {
      return;
    }

    const descriptionField = form.querySelector('[name="description"]');
    const amountField = form.querySelector('[name="amount"]');
    const templateField = form.querySelector('[name="template_id"]');
    const description = trigger.getAttribute('data-description') || '';
    const amount = trigger.getAttribute('data-amount') || '';
    const templateId = trigger.getAttribute('data-template-id') || '';

    if (descriptionField) {
      descriptionField.value = description;
    }
    if (amountField) {
      amountField.value = amount.replace('.', ',');
    }
    if (templateField) {
      templateField.value = templateId;
    }

    hideQuickSaleSuggestions();
    setQuickSaleRecognition(templateId ? 'recognized' : 'manual', templateId ? 'Produto reconhecido e carregado da memoria.' : 'Item preenchido manualmente.');
    updateQuickSaleStatus('Produto rapido carregado: ' + description + '. Ajuste o valor se quiser antes de confirmar.');
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

  window.openStudentFinancialDrawer = function (drawerId, trigger) {
    if (drawerId === 'student-payment-checkout-slot') {
      loadCheckoutDrawer(trigger).catch(function () {
        openDrawer(drawerId, trigger);
      });
      return;
    }

    if (drawerId === 'student-quick-sale-slot') {
      loadQuickSaleDrawer(trigger).catch(function () {
        openDrawer(drawerId, trigger);
      });
      return;
    }

    openDrawer(drawerId, trigger);
  };
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

    const openCheckoutTrigger = event.target.closest('[data-action="open-payment-checkout"]');
    if (openCheckoutTrigger) {
      loadCheckoutDrawer(openCheckoutTrigger).catch(function () {
        openDrawer('student-payment-checkout-slot', openCheckoutTrigger);
      });
      return;
    }

    const openQuickSaleTrigger = event.target.closest('[data-action="open-quick-sale-drawer"]');
    if (openQuickSaleTrigger) {
      loadQuickSaleDrawer(openQuickSaleTrigger).catch(function () {
        openDrawer('student-quick-sale-slot', openQuickSaleTrigger);
      });
      return;
    }

    const openStandaloneTrigger = event.target.closest('[data-action="open-standalone-payment"]');
    if (openStandaloneTrigger) {
      loadStandalonePaymentDrawer(openStandaloneTrigger).catch(function () {
        openDrawer('student-payment-checkout-slot', openStandaloneTrigger);
      });
      return;
    }

    const closeDrawerTrigger = event.target.closest('[data-action="close-drawers"]');
    if (closeDrawerTrigger) {
      closeDrawers();
      return;
    }

    const quickSaleMemoryTrigger = event.target.closest('[data-action="apply-quick-sale-memory"]');
    if (quickSaleMemoryTrigger) {
      applyQuickSaleMemory(quickSaleMemoryTrigger);
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
      return;
    }

    const submitQuickSaleTrigger = event.target.closest('[data-action="submit-quick-sale"]');
    if (submitQuickSaleTrigger) {
      const methodValue = submitQuickSaleTrigger.getAttribute('data-method');
      const form = document.getElementById('student-quick-sale-form');
      const methodField = document.querySelector('#student-quick-sale-form [name="method"]');

      if (!form || !methodValue) return;

      askPaymentConfirmation(methodValue).then(function (confirmed) {
        if (!confirmed) {
          return;
        }

        if (methodField) {
          methodField.value = methodValue;
        }

        document.querySelectorAll('#student-quick-sale-form .student-payment-method-button').forEach(function (button) {
          button.classList.add('is-disabled');
          button.classList.remove('is-active');
          button.setAttribute('aria-disabled', 'true');
        });

        submitQuickSaleTrigger.classList.remove('is-disabled');
        submitQuickSaleTrigger.classList.add('is-active');
        submitQuickSaleTrigger.removeAttribute('aria-disabled');

        updateQuickSaleStatus(methodValue === 'pix' ? 'Registrando o pagamento rapido com Pix. Aguarde um instante.' : 'Registrando o pagamento rapido. Aguarde um instante.');

        submitFinancialForm(form).catch(function (error) {
          updateQuickSaleStatus(error.message);
        });
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

  root.addEventListener('input', function (event) {
    const descriptionField = event.target.closest('#student-quick-sale-form [name="description"]');
    if (!descriptionField) {
      return;
    }

    const form = descriptionField.closest('form');
    const templateField = form ? form.querySelector('[name="template_id"]') : null;
    if (templateField) {
      templateField.value = '';
    }

    scheduleQuickSaleSuggestions(descriptionField.value);
  });

  root.addEventListener('submit', function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (!form.matches('#student-payment-checkout-form, #student-quick-sale-form, .student-enrollment-management-form, .student-quick-sale-status-form')) {
      return;
    }

    event.preventDefault();
    submitFinancialForm(form).catch(function (error) {
      window.alert(error.message);
    });
  });

  window.refreshStudentFinancialWorkspaceUi = refreshWorkspaceUi;
  setFinancialWorkspaceExpanded(root.dataset.financialExpanded === 'true');
  refreshWorkspaceUi();
})();
