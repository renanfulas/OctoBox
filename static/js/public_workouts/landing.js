/*
 * ARQUIVO: CTAs de preço da landing do corredor (Entrega 5, Fase 3).
 *
 * POR QUE ELE EXISTE:
 * - cada card de preço tem seu próprio mini-formulário (e-mail + tier
 *   escondido). Ao submeter, POSTa em PublicWorkoutColdSignupView
 *   (/treinos/cadastro) e redireciona pro checkout_url da resposta —
 *   mesmo padrão de fetch+CSRF já usado em load_tracker.js
 *   (getCookie('csrftoken') -> header X-CSRFToken).
 * - erro nunca é genérico: mostra a mensagem que a view devolveu
 *   (email_ou_tier_invalido, stripe_nao_configurado) traduzida pro
 *   visitante, nunca um "algo deu errado" sem contexto.
 */

(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop()) : '';
  }

  var ERROR_MESSAGES = {
    email_ou_tier_invalido: 'Confira o e-mail digitado.',
    aceite_contrato_obrigatorio: 'Aceite os Termos e a Política de Privacidade para continuar.',
    stripe_nao_configurado: 'Não foi possível iniciar o pagamento agora. Tente novamente em alguns minutos.',
  };

  function eventId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 3 | 8)).toString(16);
    });
  }

  var tracked = new Set();
  function track(eventType, tier) {
    if (document.body.dataset.funnelEnabled !== 'true') return;
    var key = eventType + ':' + (tier || '');
    if (tracked.has(key)) return;
    tracked.add(key);
    try {
      window.fetch(document.body.dataset.funnelUrl, {
        method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
        body: JSON.stringify({event_type: eventType, client_event_id: eventId(), tier: tier || ''}),
      }).catch(function () { /* analytics never blocks the customer */ });
    } catch (error) { /* even a blocked fetch must not prevent signup */ }
  }

  function wireForm(form) {
    var formTier = form.getAttribute('data-tier');
    form.addEventListener('input', function () { track('signup_started', formTier); });
    form.addEventListener('invalid', function () { track('signup_invalid', formTier); }, true);
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (form.getAttribute('aria-busy') === 'true' || !form.reportValidity()) return;
      track('signup_submitted', formTier);

      var button = form.querySelector('.curva-signup-submit');
      var statusEl = form.querySelector('.curva-signup-status');
      var email = form.querySelector('input[type="email"]').value.trim();
      var tier = form.getAttribute('data-tier');
      var accepted = form.querySelector('input[name="accept_contract"]');
      var invite = form.querySelector('input[name="invite_token"]');
      var buttonLabel = button ? button.textContent : '';
      form.setAttribute('aria-busy', 'true');

      if (statusEl) {
        statusEl.textContent = '';
        statusEl.removeAttribute('data-state');
      }
      if (button) {
        button.disabled = true;
        button.textContent = 'Aguarde…';
      }

      window
        .fetch(form.getAttribute('action'), {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: 'email=' + encodeURIComponent(email) + '&tier=' + encodeURIComponent(tier) +
            '&accept_contract=' + encodeURIComponent(accepted && accepted.checked ? '1' : '') +
            '&invite_token=' + encodeURIComponent(invite ? invite.value : ''),
        })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok) {
            throw new Error(result.data && result.data.error);
          }
          if (result.data.waitlisted) {
            form.removeAttribute('aria-busy');
            if (statusEl) {
              statusEl.textContent = result.data.message;
              statusEl.setAttribute('data-state', 'ok');
            }
            if (button) {
              button.disabled = false;
              button.textContent = 'Prioridade registrada';
            }
            return;
          }
          if (!result.data.checkout_url) throw new Error('resposta_invalida');
          if (statusEl) {
            statusEl.textContent = result.data.login_required
              ? 'Conta encontrada — faça login com seu link seguro para continuar.'
              : 'Tudo certo — abrindo o pagamento…';
            statusEl.setAttribute('data-state', 'ok');
          }
          if (result.data.checkout_url) {
            if (!result.data.login_required && new URL(result.data.checkout_url, window.location.href).origin !== window.location.origin) {
              track('checkout_redirected', tier);
            }
            window.location.href = result.data.checkout_url;
          }
        })
        .catch(function (error) {
          track('signup_failed', formTier);
          form.removeAttribute('aria-busy');
          if (statusEl) {
            statusEl.textContent = ERROR_MESSAGES[error && error.message] || 'Não foi possível continuar agora. Tente novamente.';
            statusEl.setAttribute('data-state', 'error');
          }
          if (button) {
            button.disabled = false;
            button.textContent = buttonLabel;
          }
        });
    });
  }

  function init() {
    document.querySelectorAll('[data-curva-signup-form]').forEach(wireForm);
    document.querySelectorAll('a[href="#curva-precos"], .curva-plan-guide a').forEach(function (link) {
      link.addEventListener('click', function () { track('cta_clicked'); });
    });
    document.querySelectorAll('.curva-faq details').forEach(function (details) {
      details.addEventListener('toggle', function () { if (details.open) track('faq_opened'); });
    });
    var pricing = document.querySelectorAll('.curva-pricing-heading, .curva-price-card');
    if (document.body.dataset.funnelEnabled === 'true' && pricing.length && 'IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        if (entries.some(function (entry) { return entry.isIntersecting; }) && document.visibilityState === 'visible') {
          track('pricing_viewed');
          observer.disconnect();
        }
      }, {threshold: 0.1});
      function observePricing() {
        observer.disconnect();
        if (document.visibilityState === 'visible' && !tracked.has('pricing_viewed:')) {
          pricing.forEach(function (element) { observer.observe(element); });
        }
      }
      document.addEventListener('visibilitychange', observePricing);
      observePricing();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
