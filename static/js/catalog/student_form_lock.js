/**
 * ARQUIVO: student_form_lock.js
 *
 * POR QUE EXISTE:
 * - Mantém o lock de edição vivo enquanto o usuário está ativo na ficha.
 * - Detecta quando outro usuário (de maior prioridade) assumiu o lock.
 * - Exibe banner contextual com nome e papel do detentor.
 *
 * O QUE FAZ:
 * 1. Heartbeat a cada 5s: renova o TTL do lock no Redis.
 * 2. Se lock foi tomado (status "stolen" ou "blocked"): exibe banner e para o heartbeat.
 * 3. Usa getCsrfToken() do cookie para autenticação CSRF nas requisições POST.
 *
 * PONTOS CRÍTICOS:
 * - Só executa na página de edição de aluno (data-student-id presente).
 * - Se o servidor estiver offline, o script degrada silenciosamente (sem erro visível).
 * - O banner "stolen" aparece em tempo real sem reload de página.
 */

(function () {
  'use strict';

  // Localiza o container principal com o ID do aluno
  const pageRoot = document.querySelector('[data-student-id]');
  if (!pageRoot) return; // Não estamos em uma ficha de edição

  const studentId = pageRoot.dataset.studentId;
  if (!studentId) return;

  const HEARTBEAT_URL = `/alunos/${studentId}/editar/lock/heartbeat/`;
  const HEARTBEAT_INTERVAL_MS = 5000; // 5 segundos

  const stolenBanner = document.getElementById('student-lock-stolen-banner');
  const stolenMsg = document.getElementById('student-lock-stolen-msg');

  let heartbeatTimer = null;
  let lockLost = false;

  // ---------------------------------------------------------------
  // CSRF Token (padrão Django)
  // ---------------------------------------------------------------
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  // ---------------------------------------------------------------
  // Banner de lock tomado
  // ---------------------------------------------------------------
  function showStolenBanner(holder) {
    if (!stolenBanner) return;
    if (holder && stolenMsg) {
      const name = holder.user_display || 'Outro usuário';
      const role = holder.role_label || '';
      stolenMsg.textContent =
        `${name} (${role}) assumiu a edição deste aluno. ` +
        `Suas alterações podem não ser salvas. Fale com ele para coordenar.`;
    }
    stolenBanner.style.display = 'flex';
    stolenBanner.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ---------------------------------------------------------------
  // Heartbeat
  // ---------------------------------------------------------------
  function sendHeartbeat() {
    if (lockLost) return; // Para de bater se o lock foi perdido

    fetch(HEARTBEAT_URL, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        if (!data) return;

        if (data.status === 'stolen' || data.status === 'blocked') {
          lockLost = true;
          clearInterval(heartbeatTimer);
          showStolenBanner(data.holder);
          return;
        }

        // active | reacquired | dev_bypass → continua normalmente
      })
      .catch(function () {
        // Servidor indisponível → degrada silenciosamente
      });
  }

  // ---------------------------------------------------------------
  // Inicia o heartbeat
  // ---------------------------------------------------------------
  heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);

  // Para o heartbeat quando o usuário sai da página
  window.addEventListener('beforeunload', function () {
    clearInterval(heartbeatTimer);
  });

  // Para o heartbeat quando a aba fica oculta (performance)
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      clearInterval(heartbeatTimer);
    } else if (!lockLost) {
      // Retoma ao voltar para a aba
      sendHeartbeat(); // batida imediata
      heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
    }
  });
})();
