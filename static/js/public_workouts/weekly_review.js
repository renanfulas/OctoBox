/*
 * ARQUIVO: revisão semanal com IA (Entrega 4 — docs/plans/
 * public-workouts-produtizacao-corda.md, tabela de status da Frente B;
 * card automático na Início — achado do Renan sobre usar o Haiku no
 * resumo).
 *
 * POR QUE ELE EXISTE:
 * - build_weekly_review (public_workouts/services.py) so calcula os SINAIS
 *   deterministicos; PublicWorkoutWeeklyReviewView (student_app) expoe
 *   isso + a tentativa de texto via Claude Haiku, agora cacheada no
 *   MAXIMO 1x por conta por semana ISO
 *   (weekly_review_ai.get_or_create_cached_review_text) — o custo/
 *   latencia de LLM por page-load que antes bloqueava buscar isto
 *   automaticamente deixou de se aplicar, porque so a PRIMEIRA visita da
 *   semana chama a IA de verdade; o resto le cache.
 * - Duplo modo, decidido pela PRESENCA do botao (nunca um atributo novo
 *   pra isso): card da aba Cargas tem `[data-workout-weekly-review-
 *   generate]` -- so busca no clique, como sempre. Card da aba Início
 *   nao tem botao -- busca sozinho ao carregar a pagina.
 *
 * PONTOS CRITICOS:
 * - `review_text` pode vir `null` (sem IA configurada, sem sinal, timeout,
 *   erro) — resposta 200 valida, nao erro. O card manual (Cargas) sempre
 *   mostra uma mensagem neutra nesse caso. O card automatico (Início) usa
 *   `data-workout-weekly-review-silent-empty`: sem texto, fica escondido
 *   e calado -- a Início nunca deveria abrir mostrando "sem sinal ainda"
 *   pra quem nem pediu.
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
    var silentWhenEmpty = root.hasAttribute('data-workout-weekly-review-silent-empty');
    if (!url) { return; }

    function setStatus(message) {
      if (silentWhenEmpty) { return; }
      if (statusEl) { statusEl.textContent = message; }
    }

    function fetchReview() {
      if (button) { button.disabled = true; }
      setStatus('Gerando…');

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
            setStatus('');
            root.hidden = false;
          } else {
            setStatus('Ainda não há sinal suficiente para gerar uma revisão.');
          }
        })
        .catch(function () {
          setStatus('Não foi possível gerar a revisão agora.');
        })
        .finally(function () {
          if (button) { button.disabled = false; }
        });
    }

    if (button) {
      button.addEventListener('click', fetchReview);
    } else {
      fetchReview();
    }
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
