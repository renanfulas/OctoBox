/*
ARQUIVO: day-apply — comportamento do popover de template por dia e toast de undo.

O QUE FAZ:
1. botão [data-wod-day-apply-trigger] abre o <dialog> compartilhado, seta a data ativa.
2. busca em tempo real filtra os cards de template.
3. botão "Aplicar neste dia" faz POST JSON para wod-day-apply e fecha o dialog.
4. toast mostra resumo + contador de 60s; "Desfazer" faz POST para wod-day-apply-undo.
*/

(function () {
  'use strict';

  var APPLY_URL = document.querySelector('[data-wod-day-apply-toast]')
    ? document.querySelector('[data-wod-day-apply-toast] [data-wod-day-apply-undo-btn]')?.dataset.undoUrl
    : null;

  var applyUrl = '/operacao/wod/planner/dia/aplicar/';
  var dialog = document.querySelector('[data-wod-day-apply-dialog]');
  var toast = document.querySelector('[data-wod-day-apply-toast]');
  var toastMsg = toast ? toast.querySelector('[data-wod-day-apply-toast-msg]') : null;
  var countdownEl = toast ? toast.querySelector('[data-wod-day-apply-countdown]') : null;
  var undoBtn = toast ? toast.querySelector('[data-wod-day-apply-undo-btn]') : null;
  var closeToastBtn = toast ? toast.querySelector('[data-wod-day-apply-toast-close]') : null;
  var searchInput = dialog ? dialog.querySelector('[data-wod-day-apply-search]') : null;
  var cards = dialog ? Array.from(dialog.querySelectorAll('[data-wod-day-apply-card]')) : [];
  var emptyMsg = dialog ? dialog.querySelector('[data-wod-day-apply-empty]') : null;
  var dialogTitle = dialog ? dialog.querySelector('[data-wod-day-apply-dialog-title]') : null;
  var undoUrl = undoBtn ? undoBtn.dataset.undoUrl : '/operacao/wod/planner/dia/desfazer/';

  var activeDate = null;
  var countdownInterval = null;
  var currentUndoToken = null;

  function getCsrf() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  // ── Abrir dialog ──────────────────────────────────────────────────

  document.querySelectorAll('[data-wod-day-apply-trigger]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      activeDate = btn.dataset.date;
      var dayLabel = btn.dataset.dayLabel || 'este dia';
      if (dialogTitle) dialogTitle.textContent = 'Aplicar em ' + dayLabel;
      if (searchInput) {
        searchInput.value = '';
        filterCards('');
      }
      if (dialog) dialog.showModal();
    });
  });

  // ── Busca de templates ────────────────────────────────────────────

  function filterCards(query) {
    var q = query.trim().toLowerCase();
    var visible = 0;
    cards.forEach(function (card) {
      var name = (card.dataset.templateName || '').toLowerCase();
      var match = !q || name.includes(q);
      card.hidden = !match;
      if (match) visible++;
    });
    if (emptyMsg) emptyMsg.hidden = visible > 0;
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      filterCards(searchInput.value);
    });
  }

  // ── Fechar dialog com Esc (nativo do <dialog>) ────────────────────
  // O <dialog> já suporta Esc nativamente, nada a fazer.

  // ── Aplicar template ──────────────────────────────────────────────

  function getSelectedMode() {
    if (!dialog) return 'replace_empty';
    var checked = dialog.querySelector('[name=wod_day_apply_mode]:checked');
    return checked ? checked.value : 'replace_empty';
  }

  if (dialog) {
    dialog.querySelectorAll('[data-wod-day-apply-select]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var templateId = btn.dataset.templateId;
        var templateLabel = btn.dataset.templateLabel;
        var mode = getSelectedMode();
        if (!activeDate || !templateId) return;

        btn.disabled = true;
        btn.textContent = 'Aplicando...';

        var body = new URLSearchParams({
          csrfmiddlewaretoken: getCsrf(),
          target_date: activeDate,
          template_id: templateId,
          mode: mode,
        });

        fetch(applyUrl, { method: 'POST', body: body, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            dialog.close();
            btn.disabled = false;
            btn.textContent = 'Aplicar neste dia';
            if (data.ok) {
              showToast(data, templateLabel);
            } else {
              alert('Erro ao aplicar template. Tente novamente.');
            }
          })
          .catch(function () {
            btn.disabled = false;
            btn.textContent = 'Aplicar neste dia';
            alert('Erro de conexao. Tente novamente.');
          });
      });
    });
  }

  // ── Toast + undo ──────────────────────────────────────────────────

  function showToast(data, templateLabel) {
    if (!toast || !toastMsg) return;
    currentUndoToken = data.undo_token;

    var skipped = data.skipped_count > 0 ? ' · ' + data.skipped_count + ' pulada(s)' : '';
    toastMsg.textContent =
      '"' + templateLabel + '" aplicado em ' + data.applied_count + ' aula(s)' + skipped + '.';

    toast.hidden = false;
    startCountdown(60);
  }

  function startCountdown(seconds) {
    clearInterval(countdownInterval);
    var remaining = seconds;
    if (countdownEl) countdownEl.textContent = remaining;

    countdownInterval = setInterval(function () {
      remaining -= 1;
      if (countdownEl) countdownEl.textContent = remaining;
      if (remaining <= 0) {
        clearInterval(countdownInterval);
        dismissToast();
      }
    }, 1000);
  }

  function dismissToast() {
    if (toast) toast.hidden = true;
    currentUndoToken = null;
    clearInterval(countdownInterval);
  }

  if (undoBtn) {
    undoBtn.addEventListener('click', function () {
      if (!currentUndoToken) return;
      undoBtn.disabled = true;

      var body = new URLSearchParams({
        csrfmiddlewaretoken: getCsrf(),
        undo_token: currentUndoToken,
      });

      fetch(undoUrl, { method: 'POST', body: body, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          dismissToast();
          if (data.ok && data.undone_count > 0) {
            window.location.reload();
          } else if (!data.ok) {
            alert(data.reason || 'Janela de desfazer encerrada.');
          }
        })
        .catch(function () {
          undoBtn.disabled = false;
          alert('Erro ao desfazer. Tente novamente.');
        });
    });
  }

  if (closeToastBtn) {
    closeToastBtn.addEventListener('click', dismissToast);
  }
})();
