/*
 * ARQUIVO: acoes da aba Perfil do corredor publico (/renan/<slug>) --
 * abrir o Customer Portal da Stripe, iniciar o PRIMEIRO checkout de um
 * cliente legado, atualizar status sem reload (payment_processing) e sair
 * da conta.
 *
 * PONTOS CRITICOS:
 * - `[data-workout-start-checkout]` (achado real, Rafael): cliente legado
 *   (seed_legacy_workout_accounts) tem assinatura com status=ACTIVE mas
 *   NUNCA tem stripe_customer_id -- "Pagamentos" caia num link morto pro
 *   hub /treinos/minha-conta, que nao mostra nada sobre pagamento porque
 *   get_customer_journey() so' trata payment_problem/payment_pending, nunca
 *   "ACTIVE sem checkout nenhum ainda". Dispara POST /treinos/subscribe
 *   (PublicWorkoutSubscribeView) com o `plan_slug` do proprio `/renan/<slug>`
 *   -- endpoint ja existia e ja tinha testes, so' nunca tinha sido ligado a
 *   nenhuma tela (ver docs/plans/public-workouts-produtizacao-corda.md).
 * - Mesmo padrao de getCookie/status de assessments.js/workout-shell.js --
 *   nao importado direto (abas independentes, cada JS so' sabe ler o DOM).
 */
(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop()) : '';
  }

  function setStatus(message, isError) {
    document.querySelectorAll('[data-action-status]').forEach(function (node) {
      node.textContent = message;
      node.dataset.state = isError ? 'error' : 'ok';
    });
  }

  document.querySelectorAll('[data-billing-portal]').forEach(function (button) {
    button.addEventListener('click', function () {
      button.disabled = true;
      setStatus('Abrindo o ambiente seguro da Stripe…', false);
      window.fetch('/treinos/billing-portal', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      })
        .then(function (response) {
          return response.json().then(function (data) { return { ok: response.ok, data: data }; });
        })
        .then(function (result) {
          if (!result.ok || !result.data.portal_url) { throw new Error('portal'); }
          window.location.href = result.data.portal_url;
        })
        .catch(function () {
          setStatus('Não foi possível abrir a assinatura agora. Tente novamente em instantes.', true);
          button.disabled = false;
        });
    });
  });

  document.querySelectorAll('[data-workout-start-checkout]').forEach(function (button) {
    var planSlug = button.getAttribute('data-checkout-plan-slug');
    if (!planSlug) { return; }

    button.addEventListener('click', function () {
      button.disabled = true;
      setStatus('Abrindo o checkout seguro da Stripe…', false);
      window.fetch('/treinos/subscribe', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'plan_slug=' + encodeURIComponent(planSlug),
      })
        .then(function (response) {
          return response.json().then(function (data) { return { ok: response.ok, data: data }; });
        })
        .then(function (result) {
          if (!result.ok || !result.data.checkout_url) { throw new Error('checkout'); }
          window.location.href = result.data.checkout_url;
        })
        .catch(function () {
          setStatus('Não foi possível abrir o pagamento agora. Tente novamente em instantes.', true);
          button.disabled = false;
        });
    });
  });

  document.querySelectorAll('[data-refresh-status]').forEach(function (button) {
    button.addEventListener('click', function () { window.location.reload(); });
  });

  if (document.body.dataset.journeyState === 'payment_processing') {
    window.setTimeout(function () {
      window.fetch('/treinos/minha-conta?format=json', { credentials: 'same-origin' })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.state !== 'payment_processing') { window.location.reload(); }
        });
    }, 3500);
  }
})();
