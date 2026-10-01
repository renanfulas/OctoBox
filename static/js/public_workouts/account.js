/*
 * ARQUIVO: acoes da aba Perfil do corredor publico (/renan/<slug>) --
 * abrir o Customer Portal da Stripe, iniciar o checkout de valor
 * negociado de um cliente legado, atualizar status sem reload
 * (payment_processing) e sair da conta.
 *
 * PONTOS CRITICOS:
 * - `[data-workout-start-custom-checkout]` (achado real, Rafael): cliente
 *   legado (seed_legacy_workout_accounts) tem assinatura ACTIVE mas NUNCA
 *   tem stripe_customer_id -- "Pagamentos" caia num link morto pro hub
 *   /treinos/minha-conta, que nao mostra nada sobre pagamento porque
 *   get_customer_journey() so' trata payment_problem/payment_pending,
 *   nunca "ACTIVE sem Stripe nenhum ainda". So' aparece quando o Renan ja'
 *   preencheu `custom_monthly_price` no admin (PublicWorkoutSubscriptionAdmin)
 *   -- dispara POST /treinos/checkout-personalizado (PublicWorkoutCustom
 *   CheckoutView), que fecha o loop sem ele precisar copiar/colar link no
 *   WhatsApp (a acao de admin "Gerar link..." continua existindo como
 *   fallback manual). Sem o valor definido, o template mostra "Fale com o
 *   Renan" em vez deste botao.
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

  function wireCheckoutButton(selector, url, loadingMessage, errorMessage) {
    document.querySelectorAll(selector).forEach(function (button) {
      button.addEventListener('click', function () {
        button.disabled = true;
        setStatus(loadingMessage, false);
        window.fetch(url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        })
          .then(function (response) {
            return response.json().then(function (data) { return { ok: response.ok, data: data }; });
          })
          .then(function (result) {
            var redirectUrl = result.data.portal_url || result.data.checkout_url;
            if (!result.ok || !redirectUrl) { throw new Error('checkout'); }
            window.location.href = redirectUrl;
          })
          .catch(function () {
            setStatus(errorMessage, true);
            button.disabled = false;
          });
      });
    });
  }

  wireCheckoutButton(
    '[data-billing-portal]', '/treinos/billing-portal',
    'Abrindo o ambiente seguro da Stripe…',
    'Não foi possível abrir a assinatura agora. Tente novamente em instantes.',
  );
  wireCheckoutButton(
    '[data-workout-start-custom-checkout]', '/treinos/checkout-personalizado',
    'Abrindo o checkout seguro da Stripe…',
    'Não foi possível abrir o pagamento agora. Tente novamente em instantes.',
  );

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
