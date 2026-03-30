/**
 * ARQUIVO: student_form_lock.js
 *
 * POR QUE EXISTE:
 * - mantem o lock de edicao vivo enquanto o usuario esta ativo na ficha.
 * - detecta quando outro usuario de maior prioridade assumiu o lock.
 * - endurece o feedback da ficha quando a edicao deixa de ser segura.
 *
 * O QUE FAZ:
 * 1. envia heartbeat para renovar o lock atual.
 * 2. anuncia lock perdido ou retomado com feedback acessivel.
 * 3. bloqueia acoes sensiveis quando a ficha fica sem lock valido.
 */

(function () {
  'use strict';

  const pageRoot = document.querySelector('[data-student-id]');
  if (!pageRoot) return;

  const studentId = pageRoot.dataset.studentId;
  if (!studentId) return;

  const heartbeatUrl = `/alunos/${studentId}/editar/lock/heartbeat/`;
  const heartbeatIntervalMs = 5000;

  const blockedBanner = document.getElementById('student-lock-banner');
  const stolenBanner = document.getElementById('student-lock-stolen-banner');
  const stolenMsg = document.getElementById('student-lock-stolen-msg');
  const liveStatus = document.getElementById('student-lock-live-status');

  const guardedSelector = [
    'button[type="submit"]',
    'button[data-action="next-step"]',
    'button[data-action="open-drawer"]',
    'button[data-action="submit-stripe"]',
    'button[data-action="edit-payment"]',
    'button[data-action="split-payment"]',
    'button[data-action="vacation-freeze"]',
  ].join(', ');

  let heartbeatTimer = null;
  let lockLost = false;

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function setGuardedState(disabled) {
    pageRoot.querySelectorAll(guardedSelector).forEach(function (element) {
      element.disabled = disabled;
      element.toggleAttribute('aria-disabled', disabled);
      element.classList.toggle('is-lock-disabled', disabled);
    });
  }

  function announce(message) {
    if (!liveStatus) return;
    liveStatus.textContent = message || '';
  }

  function hideBanner(banner) {
    if (!banner) return;
    banner.hidden = true;
  }

  function showBanner(banner) {
    if (!banner) return;
    banner.hidden = false;
  }

  function applyBlockedState(holder) {
    pageRoot.dataset.lockState = 'blocked';
    setGuardedState(true);

    if (blockedBanner && holder) {
      const message = blockedBanner.querySelector('.lock-banner__message');
      if (message) {
        const name = holder.user_display || 'Outro usuario';
        const role = holder.role_label || '';
        message.innerHTML = `<strong>${name} (${role})</strong> esta editando este aluno. Fale com ele para coordenar ou aguarde a ficha ser liberada.`;
      }
    }

    showBanner(blockedBanner);
    hideBanner(stolenBanner);
    announce('Edicao bloqueada por outro usuario. Os comandos sensiveis ficaram desativados ate a ficha ser liberada.');
  }

  function applyActiveState() {
    pageRoot.dataset.lockState = 'active';
    setGuardedState(false);
    hideBanner(blockedBanner);
    hideBanner(stolenBanner);
    announce('Edicao liberada novamente para voce.');
  }

  function applyStolenState(holder) {
    if (!stolenBanner) return;

    const name = holder && holder.user_display ? holder.user_display : 'Outro usuario';
    const role = holder && holder.role_label ? holder.role_label : '';
    const message =
      `${name} (${role}) assumiu a edicao deste aluno. ` +
      'Suas alteracoes nao serao salvas. Fale com ele para coordenar.';

    lockLost = true;
    pageRoot.dataset.lockState = 'stolen';
    setGuardedState(true);
    hideBanner(blockedBanner);

    if (stolenMsg) {
      stolenMsg.textContent = message;
    }

    showBanner(stolenBanner);
    stolenBanner.scrollIntoView({ behavior: 'smooth', block: 'start' });
    announce(message);
  }

  function sendHeartbeat() {
    if (lockLost) return;

    fetch(heartbeatUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (data) {
        if (!data) return;

        if (data.status === 'stolen') {
          clearInterval(heartbeatTimer);
          applyStolenState(data.holder);
          return;
        }

        if (data.status === 'blocked') {
          applyBlockedState(data.holder);
          return;
        }

        if (data.status === 'active' || data.status === 'reacquired' || data.status === 'dev_bypass') {
          applyActiveState();
        }
      })
      .catch(function () {
        // Degradacao silenciosa.
      });
  }

  if (blockedBanner) {
    applyBlockedState();
  } else {
    applyActiveState();
  }

  heartbeatTimer = setInterval(sendHeartbeat, heartbeatIntervalMs);

  window.addEventListener('beforeunload', function () {
    clearInterval(heartbeatTimer);
  });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      clearInterval(heartbeatTimer);
    } else if (!lockLost) {
      sendHeartbeat();
      heartbeatTimer = setInterval(sendHeartbeat, heartbeatIntervalMs);
    }
  });
})();
