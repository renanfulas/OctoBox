/*
 * ARQUIVO: wizard de primeiro login do corredor (workout.html).
 *
 * POR QUE ELE EXISTE:
 * - pedido direto do usuario: ensinar o que cada aba do bottom nav faz,
 *   como ver o treino, como registrar carga e como atualizar pagamento,
 *   logo no primeiro acesso de verdade (depois do e-mail de boas-vindas).
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. Abre o wizard automaticamente se data-onboarding-autostart="true"
 *    (PublicWorkoutAccount.onboarding_completed_at ainda None).
 * 2. Navega entre os passos (Proximo/Voltar/Pular/fechar).
 * 3. No ultimo passo ou ao pular, marca o onboarding como visto via
 *    POST /renan/<slug>/onboarding (PublicWorkoutOnboardingCompleteView)
 *    — fire-and-forget: falha de rede nunca trava a navegacao, so' tenta
 *    de novo no proximo login (onboarding_completed_at so' muda no servidor
 *    se a tentativa chegar e for bem-sucedida).
 * 4. "Ver tutorial de novo" (botao na aba Perfil, data-ui=replay-onboarding)
 *    reabre do passo 0 sem repetir o POST se ja' foi marcado.
 *
 * PONTOS CRITICOS:
 * - Mesmo padrao de getCookie/fetch de account.js/assessments.js — nao
 *   importado direto (cada aba independente, cada JS so' sabe ler o DOM).
 * - Foco: ao abrir, move pro card (acessibilidade); ao fechar, devolve pro
 *   elemento que tinha foco antes (normalmente nenhum, no autostart).
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-onboarding-wizard]');
  if (!root) { return; }

  var steps = Array.prototype.slice.call(root.querySelectorAll('[data-onboarding-step]'));
  var dotsContainer = root.querySelector('[data-onboarding-dots]');
  var card = root.querySelector('.onboarding-wizard__card');
  var nextButton = root.querySelector('[data-onboarding-next]');
  var backButton = root.querySelector('[data-onboarding-back]');
  var skipButton = root.querySelector('[data-onboarding-skip]');
  var dismissTargets = root.querySelectorAll('[data-onboarding-dismiss]');
  var completeUrl = root.getAttribute('data-onboarding-complete-url') || '';
  var current = 0;
  var completed = false;
  var lastFocused = null;

  steps.forEach(function () {
    var dot = document.createElement('span');
    dotsContainer.appendChild(dot);
  });
  var dots = Array.prototype.slice.call(dotsContainer.children);

  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop()) : '';
  }

  function markComplete() {
    if (completed || !completeUrl) { return; }
    completed = true;
    window.fetch(completeUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    }).catch(function () { completed = false; });
  }

  function render() {
    steps.forEach(function (step, index) {
      step.hidden = index !== current;
    });
    dots.forEach(function (dot, index) {
      if (index === current) {
        dot.setAttribute('data-active', '');
      } else {
        dot.removeAttribute('data-active');
      }
    });
    backButton.hidden = current === 0;
    nextButton.textContent = current === steps.length - 1 ? 'Começar a usar' : 'Próximo';
  }

  function open() {
    lastFocused = document.activeElement;
    current = 0;
    render();
    root.hidden = false;
    document.body.style.overflow = 'hidden';
    if (card) { card.focus(); }
  }

  function close() {
    root.hidden = true;
    document.body.style.overflow = '';
    markComplete();
    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus();
    }
  }

  nextButton.addEventListener('click', function () {
    if (current === steps.length - 1) {
      close();
      return;
    }
    current += 1;
    render();
  });

  backButton.addEventListener('click', function () {
    if (current === 0) { return; }
    current -= 1;
    render();
  });

  skipButton.addEventListener('click', close);

  dismissTargets.forEach(function (target) {
    target.addEventListener('click', close);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !root.hidden) { close(); }
  });

  document.querySelectorAll('[data-ui="replay-onboarding"]').forEach(function (button) {
    button.addEventListener('click', open);
  });

  if (card) { card.setAttribute('tabindex', '-1'); }

  if (root.getAttribute('data-onboarding-autostart') === 'true') {
    window.setTimeout(open, 400);
  }
})();
