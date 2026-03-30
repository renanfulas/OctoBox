/*
ARQUIVO: comportamento da ficha leve do aluno.

POR QUE ELE EXISTE:
- retira do template a logica interativa da ficha.
- concentra plano conectado, parcelamento e foco automatico num modulo de pagina.
*/

(function() {
  var payloadElement = document.getElementById('current-page-behavior');
  var pagePayload = {};
  if (payloadElement) {
    try {
      pagePayload = JSON.parse(payloadElement.textContent || '{}');
    } catch (error) {
      console.error('Payload error:', error);
      pagePayload = {};
    }
  }

  var planPriceMap = pagePayload.plan_price_map || {};
  var planField = document.getElementById('id_selected_plan');
  var amountField = document.getElementById('id_initial_payment_amount');
  var planPriceField = document.getElementById('connected-plan-price');
  var billingStrategyField = document.getElementById('id_billing_strategy');
  var installmentTotalField = document.getElementById('id_installment_total');
  var installmentSelectorShell = document.getElementById('installment-selector-shell');
  var installmentSelector = document.getElementById('installment-selector');
  var installmentPreview = document.getElementById('installment-preview');
  var planSwapStatus = document.getElementById('plan-swap-status');
  var priceDeltaIndicator = document.getElementById('price-delta-indicator');

  var initialPlanId = planField ? planField.value : null;
  var initialPrice = (planField && planPriceMap) ? parseAmount(planPriceMap[initialPlanId]) : 0;
  var focusSections = pagePayload.focus_sections || {};
  var currencyFormatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  });
  var installmentRefreshFrame = null;

  function setElementHidden(element, shouldHide) {
    if (!element) {
      return;
    }

    element.hidden = shouldHide;
  }

  function setTextContent(element, value) {
    if (!element) {
      return;
    }

    element.textContent = value;
  }

  function resetPlanSwapFeedback() {
    if (planSwapStatus) {
      setElementHidden(planSwapStatus, true);
    }

    if (priceDeltaIndicator) {
      priceDeltaIndicator.className = 'price-delta-indicator text-xs text-bold';
      setTextContent(priceDeltaIndicator, '');
      setElementHidden(priceDeltaIndicator, true);
    }
  }

  function formatCurrency(value) {
    return currencyFormatter.format(value || 0);
  }

  function parseAmount(value) {
    if (!value) {
      return 0;
    }
    var strValue = String(value).trim();
    if (strValue.includes('.') && strValue.includes(',')) {
      strValue = strValue.replace(/\./g, '').replace(',', '.');
    } else if (strValue.includes(',')) {
      strValue = strValue.replace(',', '.');
    }

    var parsedValue = Number(strValue);
    return Number.isFinite(parsedValue) ? parsedValue : 0;
  }

  function updateInstallmentPreview() {
    if (!amountField || !installmentSelector || !installmentTotalField || !installmentPreview) {
      return;
    }

    var totalAmount = parseAmount(amountField.value);
    var installmentCount = Number(installmentSelector.value || 1);
    var installmentAmount = installmentCount > 0 ? totalAmount / installmentCount : totalAmount;

    installmentTotalField.value = String(installmentCount);
    installmentPreview.textContent = installmentCount + 'x ' + formatCurrency(installmentAmount);
  }

  function buildInstallmentOptions() {
    if (!amountField || !installmentSelector || !installmentTotalField) {
      return;
    }

    var totalAmount = parseAmount(amountField.value);
    var currentInstallmentTotal = Number(installmentTotalField.value || 1);
    var fragment = document.createDocumentFragment();
    installmentSelector.replaceChildren();

    for (var index = 1; index <= 12; index += 1) {
      var option = document.createElement('option');
      var installmentAmount = totalAmount > 0 ? totalAmount / index : 0;
      option.value = String(index);
      option.textContent = index + 'x de ' + formatCurrency(installmentAmount);
      option.selected = index === currentInstallmentTotal;
      fragment.appendChild(option);
    }

    installmentSelector.appendChild(fragment);

    updateInstallmentPreview();
  }

  function scheduleInstallmentRefresh() {
    if (installmentRefreshFrame !== null) {
      cancelAnimationFrame(installmentRefreshFrame);
    }

    installmentRefreshFrame = window.requestAnimationFrame(function() {
      installmentRefreshFrame = null;
      buildInstallmentOptions();
    });
  }

  function syncBillingStrategyState() {
    if (!billingStrategyField || !installmentSelectorShell || !installmentTotalField) {
      return;
    }

    var isInstallmentMode = billingStrategyField.value === 'installments';
    setElementHidden(installmentSelectorShell, !isInstallmentMode);

    if (isInstallmentMode) {
      scheduleInstallmentRefresh();
      return;
    }

    installmentTotalField.value = '1';
  }

  function syncConnectedPlanPrice() {
    if (!planField || !amountField || !planPriceField) {
      return;
    }

    var selectedPlanId = planField.value;
    var rawPrice = planPriceMap[selectedPlanId] || '';
    var selectedPrice = parseAmount(rawPrice);
    var planSwapPill = document.getElementById('plan-swap-pill');

    planPriceField.value = rawPrice ? formatCurrency(selectedPrice) : '--';

    if (rawPrice) {
      amountField.value = rawPrice;
    }

    if (planSwapStatus && priceDeltaIndicator) {
      if (!selectedPlanId || selectedPlanId === initialPlanId) {
        resetPlanSwapFeedback();
      } else {
        var delta = selectedPrice - initialPrice;
        setElementHidden(planSwapStatus, false);
        setElementHidden(priceDeltaIndicator, false);

        if (delta > 0) {
          if (planSwapPill) {
            planSwapPill.className = 'pill neon-tone-orange text-xs text-bold';
            planSwapPill.textContent = 'UPGRADE';
          }
          priceDeltaIndicator.className = 'price-delta-indicator text-xs text-bold is-positive';
          setTextContent(priceDeltaIndicator, '+' + formatCurrency(delta));
        } else if (delta < 0) {
          if (planSwapPill) {
            planSwapPill.className = 'pill neon-tone-emerald text-xs text-bold';
            planSwapPill.textContent = 'DOWNGRADE';
          }
          priceDeltaIndicator.className = 'price-delta-indicator text-xs text-bold is-negative';
          setTextContent(priceDeltaIndicator, '-' + formatCurrency(Math.abs(delta)));
        } else {
          if (planSwapPill) {
            planSwapPill.className = 'pill text-xs text-bold surface-tonal';
            planSwapPill.textContent = 'MESMO VALOR';
          }
          setTextContent(priceDeltaIndicator, '');
          setElementHidden(priceDeltaIndicator, true);
        }
      }
    }

    syncBillingStrategyState();
  }

  function applyFocusMode(modeKey) {
    var mode = focusSections[modeKey];
    if (!mode) {
      return;
    }

    (mode.open || []).forEach(function(id) {
      var detail = document.getElementById(id);
      if (detail) {
        detail.open = true;
      }
    });

    (mode.close || []).forEach(function(id) {
      var detail = document.getElementById(id);
      if (detail) {
        detail.open = false;
      }
    });

    if (mode.scroll_target) {
      var target = document.getElementById(mode.scroll_target);
      if (target) {
        setTimeout(function() {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }, 100);
      }
    }
  }

  function applyHashFocusMode() {
    var hash = window.location.hash;
    if (!hash || hash.indexOf('focus=') === -1) {
      return;
    }

    var focus = hash.replace('#', '').split('&').reduce(function(accumulator, pair) {
      var parts = pair.split('=');
      accumulator[parts[0]] = parts[1];
      return accumulator;
    }, {}).focus;

    if (!focus) {
      return;
    }

    applyFocusMode(focus);
    history.replaceState(null, '', window.location.pathname);
  }

  if (planField && amountField && planPriceField && billingStrategyField && installmentTotalField && installmentSelectorShell && installmentSelector && installmentPreview) {
    planField.addEventListener('change', syncConnectedPlanPrice);
    billingStrategyField.addEventListener('change', syncBillingStrategyState);
    amountField.addEventListener('input', function() {
      if (billingStrategyField.value === 'installments') {
        scheduleInstallmentRefresh();
      }
    });
    installmentSelector.addEventListener('change', updateInstallmentPreview);
    syncConnectedPlanPrice();
    syncBillingStrategyState();
  }

  resetPlanSwapFeedback();
  applyHashFocusMode();
}());
