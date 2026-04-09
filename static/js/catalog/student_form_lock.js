/**
 * ARQUIVO: student_form_lock.js
 *
 * POR QUE EXISTE:
 * - mantem a ficha em leitura por padrao e so pede lock ao entrar em edicao.
 * - preserva a hierarquia server-side existente sem confiar no cliente.
 * - renova o lock apenas enquanto a pessoa esta realmente editando.
 *
 * O QUE FAZ:
 * 1. consulta o estado atual do lock ao abrir a ficha.
 * 2. inicia a sessao de edicao sob demanda.
 * 3. envia heartbeat apenas durante a edicao ativa.
 * 4. libera o lock ao fechar a edicao ou sair da pagina.
 */

(function () {
  'use strict';

  const pageRoot = document.querySelector('[data-student-id]');
  if (!pageRoot) return;

  const studentId = pageRoot.dataset.studentId;
  const startUrl = pageRoot.dataset.studentEditStartUrl;
  const releaseUrl = pageRoot.dataset.studentEditReleaseUrl;
  const heartbeatUrl = pageRoot.dataset.studentLockHeartbeatUrl;
  const statusUrl = pageRoot.dataset.studentLockStatusUrl;
  const heartbeatIntervalMs = 5000;

  if (!studentId || !startUrl || !releaseUrl || !heartbeatUrl || !statusUrl) return;

  const blockedBanner = document.getElementById('student-lock-banner');
  const stolenBanner = document.getElementById('student-lock-stolen-banner');
  const stolenMsg = document.getElementById('student-lock-stolen-msg');
  const liveStatus = document.getElementById('student-lock-live-status');

  const guardedSelector = [
    'button[type="submit"]',
    'button[data-action="next-step"]',
    'button[data-action="submit-stripe"]',
    'button[data-action="split-payment"]',
    'button[data-action="vacation-freeze"]',
  ].join(', ');

  let heartbeatTimer = null;
  let lockState = 'idle';

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function dispatchLockState(detail) {
    document.dispatchEvent(new CustomEvent('student-profile-lock-state', { detail: detail }));
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

  function stopHeartbeat() {
    if (heartbeatTimer) {
      window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = window.setInterval(sendHeartbeat, heartbeatIntervalMs);
  }

  function applyReadOnlyState() {
    lockState = 'idle';
    pageRoot.dataset.lockState = 'idle';
    setGuardedState(true);
    hideBanner(blockedBanner);
    hideBanner(stolenBanner);
    dispatchLockState({ editable: false, source: 'lock-idle' });
  }

  function applyBlockedState(holder) {
    lockState = 'blocked';
    pageRoot.dataset.lockState = 'blocked';
    setGuardedState(true);

    if (blockedBanner && holder) {
      const nameSlot = blockedBanner.querySelector('[data-lock-holder-name]');
      const roleSlot = blockedBanner.querySelector('[data-lock-holder-role]');
      const copySlot = blockedBanner.querySelector('[data-lock-holder-copy]');
      const name = holder.user_display || 'Outro usuario';
      const role = holder.role_label || '';

      if (nameSlot) nameSlot.textContent = name;
      if (roleSlot) roleSlot.textContent = role ? `(${role})` : '';
      if (copySlot) {
        copySlot.textContent = 'esta editando este aluno. Fale com ele para coordenar ou aguarde a ficha ser liberada.';
      }
    }

    showBanner(blockedBanner);
    hideBanner(stolenBanner);
    dispatchLockState({ editable: false, source: 'lock-blocked' });
    announce('Edicao bloqueada por outro usuario. A ficha segue em leitura.');
  }

  function applyActiveState(mode) {
    lockState = 'active';
    pageRoot.dataset.lockState = 'active';
    setGuardedState(false);
    hideBanner(blockedBanner);
    hideBanner(stolenBanner);
    dispatchLockState({ editable: true, source: mode || 'lock-granted' });
    announce('Edicao liberada para voce.');
  }

  function applyStolenState(holder) {
    const name = holder && holder.user_display ? holder.user_display : 'Outro usuario';
    const role = holder && holder.role_label ? holder.role_label : '';
    const message =
      `${name}${role ? ' (' + role + ')' : ''} assumiu a edicao deste aluno. ` +
      'A ficha voltou para leitura e seus salvamentos serao rejeitados.';

    lockState = 'stolen';
    pageRoot.dataset.lockState = 'stolen';
    setGuardedState(true);
    hideBanner(blockedBanner);

    if (stolenMsg) {
      stolenMsg.textContent = message;
    }

    showBanner(stolenBanner);
    dispatchLockState({ editable: false, source: 'lock-stolen' });
    announce(message);
    stopHeartbeat();
  }

  function fetchJson(url, method) {
    return fetch(url, {
      method: method,
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    }).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (data) {
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  function syncInitialStatus() {
    fetchJson(statusUrl, 'GET')
      .then(function (result) {
        if (!result.ok) {
          applyReadOnlyState();
          return;
        }

        if (result.data.status === 'blocked') {
          applyBlockedState(result.data.holder);
          return;
        }

        applyReadOnlyState();
      })
      .catch(function () {
        applyReadOnlyState();
      });
  }

  function requestEditSession() {
    fetchJson(startUrl, 'POST')
      .then(function (result) {
        if (result.ok && result.data.status === 'granted') {
          applyActiveState(result.data.mode || 'lock-granted');
          startHeartbeat();
          return;
        }

        applyBlockedState((result.data || {}).holder);
      })
      .catch(function () {
        applyReadOnlyState();
        announce('Nao foi possivel iniciar a edicao agora. Tente novamente.');
      });
  }

  function releaseEditSession() {
    if (lockState !== 'active') {
      applyReadOnlyState();
      return;
    }

    fetchJson(releaseUrl, 'POST')
      .finally(function () {
        stopHeartbeat();
        applyReadOnlyState();
        announce('Edicao encerrada. A ficha voltou para leitura.');
      });
  }

  function sendHeartbeat() {
    if (lockState !== 'active') return;

    fetchJson(heartbeatUrl, 'POST')
      .then(function (result) {
        const data = result.data || {};

        if (data.status === 'active' || data.status === 'reacquired' || data.status === 'dev_bypass') {
          return;
        }

        if (data.status === 'blocked') {
          applyBlockedState(data.holder);
          stopHeartbeat();
          return;
        }

        if (data.status === 'stolen') {
          applyStolenState(data.holder);
        }
      })
      .catch(function () {
        // Degradacao silenciosa para nao travar a experiencia em falha de rede curta.
      });
  }

  document.addEventListener('student-profile-edit-request', function () {
    if (lockState === 'active') {
      return;
    }
    requestEditSession();
  });

  document.addEventListener('student-profile-edit-stop', function () {
    releaseEditSession();
  });

  window.addEventListener('beforeunload', function () {
    stopHeartbeat();
  });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      stopHeartbeat();
    } else if (lockState === 'active') {
      sendHeartbeat();
      startHeartbeat();
    } else {
      syncInitialStatus();
    }
  });

  syncInitialStatus();
})();
