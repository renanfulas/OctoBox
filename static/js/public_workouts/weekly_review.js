/*
 * ARQUIVO: revisão semanal com IA (Entrega 4 — docs/plans/
 * public-workouts-produtizacao-corda.md, tabela de status da Frente B).
 *
 * POR QUE ELE EXISTE:
 * - build_weekly_review (public_workouts/services.py) so calcula os SINAIS
 *   deterministicos; PublicWorkoutWeeklyReviewView (student_app) expoe
 *   isso + a tentativa de texto via Claude Haiku
 *   (public_workouts/weekly_review_ai.py). Este arquivo so busca sob
 *   demanda (clique em "Gerar revisão") — nunca no carregamento da
 *   pagina, custo/latencia de LLM por page-load seria inaceitavel.
 *
 * PONTOS CRITICOS:
 * - `review_text` pode vir `null` (sem IA configurada, sem sinal, timeout,
 *   erro) — resposta 200 valida, nao erro. A tela sempre mostra uma
 *   mensagem neutra nesse caso, nunca quebra.
 * - GET simples, sem corpo — nao precisa de CSRF (so metodos que mudam
 *   estado exigem X-CSRFToken neste projeto, ver load_tracker.js).
 */

(function () {
  'use strict';

  function initWeeklyReview(root) {
    var url = root.getAttribute('data-weekly-review-url');
    var textEl = root.querySelector('[data-workout-weekly-review-text]');
    var statusEl = root.querySelector('[data-workout-weekly-review-status]');
    var button = root.querySelector('[data-workout-weekly-review-generate]');
    if (!url || !button) { return; }

    button.addEventListener('click', function () {
      button.disabled = true;
      if (statusEl) { statusEl.textContent = 'Gerando…'; }

      window.fetch(url, { credentials: 'same-origin' })
        .then(function (response) {
          if (!response.ok) { throw new Error('http-' + response.status); }
          return response.json();
        })
        .then(function (data) {
          if (data && data.review_text) {
            if (textEl) {
              textEl.textContent = data.review_text;
              textEl.hidden = false;
            }
            if (statusEl) { statusEl.textContent = ''; }
          } else if (statusEl) {
            statusEl.textContent = 'Ainda não há sinal suficiente para gerar uma revisão.';
          }
        })
        .catch(function () {
          if (statusEl) { statusEl.textContent = 'Não foi possível gerar a revisão agora.'; }
        })
        .finally(function () {
          button.disabled = false;
        });
    });
  }

  function init() {
    document.querySelectorAll('[data-workout-weekly-review]').forEach(initWeeklyReview);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
