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
    stripe_nao_configurado: 'Não foi possível iniciar o pagamento agora. Tente novamente em alguns minutos.',
  };

  function wireForm(form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();

      var button = form.querySelector('.curva-signup-submit');
      var statusEl = form.querySelector('.curva-signup-status');
      var email = form.querySelector('input[type="email"]').value.trim();
      var tier = form.getAttribute('data-tier');

      if (statusEl) {
        statusEl.textContent = '';
        statusEl.removeAttribute('data-state');
      }
      if (button) {
        button.disabled = true;
      }

      window
        .fetch(form.getAttribute('action'), {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: 'email=' + encodeURIComponent(email) + '&tier=' + encodeURIComponent(tier),
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
          if (statusEl) {
            statusEl.textContent = 'Tudo certo — abrindo o pagamento…';
            statusEl.setAttribute('data-state', 'ok');
          }
          window.location.href = result.data.checkout_url;
        })
        .catch(function (error) {
          if (statusEl) {
            statusEl.textContent = ERROR_MESSAGES[error && error.message] || 'Não foi possível continuar agora. Tente novamente.';
            statusEl.setAttribute('data-state', 'error');
          }
          if (button) {
            button.disabled = false;
          }
        });
    });
  }

  function init() {
    document.querySelectorAll('[data-curva-signup-form]').forEach(wireForm);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
