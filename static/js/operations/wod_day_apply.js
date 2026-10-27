/*
ARQUIVO: day-apply — comportamento do popover de template por dia e toast de undo.

O QUE FAZ:
1. botão [data-wod-day-apply-trigger] abre o <dialog> compartilhado, seta a data ativa.
2. busca em tempo real filtra os cards de template.
3. seleção gera prévia durável por programa; confirmação envia intent_id + fingerprint
   para wod-day-program-confirm, sem reenviar o payload do WOD.
4. toast oferece um undo complementar de 60s via wod-day-apply-undo; essa janela
   temporária não é a fonte de idempotência nem de recuperação da confirmação.
*/

(function () {
  'use strict';

  if (window.__octoboxWodDayApplyBound) return;
  window.__octoboxWodDayApplyBound = true;

  var dialog = document.querySelector('[data-wod-day-apply-dialog]');
  var applyUrl = dialog ? dialog.dataset.applyUrl : null;
  var previewUrl = dialog ? dialog.dataset.previewUrl : null;
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
  var program = dialog ? dialog.querySelector('[data-wod-day-apply-program]') : null;
  var errorMsg = dialog ? dialog.querySelector('[data-wod-day-apply-error]') : null;
  var review = dialog ? dialog.querySelector('[data-wod-day-apply-review]') : null;
  var reviewTitle = review ? review.querySelector('[data-wod-day-apply-review-title]') : null;
  var reviewSummary = review ? review.querySelector('[data-wod-day-apply-review-summary]') : null;
  var reviewWarning = review ? review.querySelector('[data-wod-day-apply-review-warning]') : null;
  var reviewList = review ? review.querySelector('[data-wod-day-apply-review-list]') : null;
  var confirmBtn = review ? review.querySelector('[data-wod-day-apply-confirm]') : null;
  var applying = false;
  var selectedTemplate = null;
  var selectedPreview = null;
  var previewRequestId = 0;
  var storageKey = 'octobox:wod-day-apply:' + (toast ? toast.dataset.undoContext : '');
  var countdownInterval = null;
  var currentUndoToken = null;

  function getCsrf() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  // ── Abrir dialog ──────────────────────────────────────────────────

  function openDialogForTrigger(btn) {
    if (!btn || !dialog) return;
    activeDate = btn.dataset.date;
    resetReview();
    if (errorMsg) errorMsg.hidden = true;
    var dayLabel = btn.dataset.dayLabel || 'este dia';
    if (dialogTitle) dialogTitle.textContent = 'Aplicar em ' + dayLabel;
    if (searchInput) {
      searchInput.value = '';
      filterCards('');
    }
    if (!dialog.open) {
      dialog.showModal();
    }
  }

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

  function resetReview() {
    previewRequestId += 1;
    selectedTemplate = null;
    selectedPreview = null;
    if (review) review.hidden = true;
    if (reviewList) reviewList.replaceChildren();
    if (errorMsg) errorMsg.hidden = true;
  }

  function postForm(url, body) {
    return fetch(url, { method: 'POST', body: body, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (response) {
        var contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) throw new Error('Sua sessão expirou. Entre novamente e tente de novo.');
        return response.json();
      });
  }

  function buildBody(templateId) {
    return new URLSearchParams({
      csrfmiddlewaretoken: getCsrf(),
      target_date: activeDate,
      template_id: templateId,
      mode: getSelectedMode(),
      workout_program_id: program.value,
    });
  }

  function previewTemplate(btn) {
    if (!activeDate || !previewUrl || applying) return;
    if (!program || !program.value) {
      if (errorMsg) {
        errorMsg.textContent = 'Escolha o programa antes de conferir os destinos.';
        errorMsg.hidden = false;
      }
      if (program) program.focus();
      return;
    }
    resetReview();
    var requestId = previewRequestId;
    applying = true;
    btn.disabled = true;
    btn.textContent = 'Conferindo...';
    postForm(previewUrl, buildBody(btn.dataset.templateId))
      .then(function (data) {
        if (requestId !== previewRequestId) return;
        if (!data.ok) throw new Error(data.reason || 'Não foi possível conferir as aulas.');
        selectedTemplate = btn;
        selectedPreview = { intentId: data.intent_id, fingerprint: data.fingerprint };
        if (reviewTitle) reviewTitle.textContent = 'Confira: ' + data.template;
        if (reviewSummary) reviewSummary.textContent = data.ready_count + ' aula(s) receberão o template; ' + data.preserved_count + ' WOD(s) preservado(s).';
        var warnings = [];
        if (data.completed_count) warnings.push(data.completed_count + ' aula(s) concluída(s) serão preservadas.');
        if (reviewWarning) {
          reviewWarning.textContent = warnings.join(' ');
          reviewWarning.hidden = !warnings.length;
        }
        (data.entries || []).forEach(function (entry) {
          var item = document.createElement('li');
          var name = document.createElement('strong');
          var detail = document.createElement('span');
          name.textContent = entry.scheduled_at + ' · ' + entry.title + ' · ' + entry.program;
          detail.textContent = entry.reason;
          item.append(name, detail);
          reviewList.appendChild(item);
        });
        if (!data.entries.length) {
          var empty = document.createElement('li');
          empty.textContent = 'Nenhuma aula deste tipo encontrada neste dia.';
          reviewList.appendChild(empty);
        }
        if (confirmBtn) confirmBtn.disabled = !data.ready_count;
        if (review) review.hidden = false;
        if (confirmBtn && data.ready_count) confirmBtn.focus();
      })
      .catch(function (error) {
        if (errorMsg) {
          errorMsg.textContent = error.message || 'Erro de conexão ao conferir aulas.';
          errorMsg.hidden = false;
        }
      })
      .finally(function () {
        applying = false;
        btn.disabled = false;
        btn.textContent = 'Conferir aulas deste dia';
      });
  }

  function applyTemplate(btn) {
    var templateId = btn.dataset.templateId;
    var templateLabel = btn.dataset.templateLabel;
    if (!selectedTemplate || !selectedPreview || !activeDate || !templateId || !applyUrl) return;
    if (applying) return;
    if (!program || !program.value) {
      if (errorMsg) {
        errorMsg.textContent = 'Escolha a modalidade antes de aplicar o WOD.';
        errorMsg.hidden = false;
      }
      if (program) program.focus();
      return;
    }

    applying = true;
    btn.disabled = true;
    if (confirmBtn) confirmBtn.textContent = 'Aplicando...';

    var body = new URLSearchParams({
      csrfmiddlewaretoken: getCsrf(),
      intent_id: selectedPreview.intentId,
      fingerprint: selectedPreview.fingerprint,
    });

    postForm(applyUrl, body)
      .then(function (data) {
        applying = false;
        btn.disabled = false;
        if (confirmBtn) confirmBtn.textContent = 'Aplicar agora';
        if (data.ok) {
          dialog.close();
          var undoRemaining = data.undo_expires_at
            ? Math.max(0, Math.ceil((Date.parse(data.undo_expires_at) - Date.now()) / 1000))
            : (data.undo_unavailable ? 0 : 60);
          if (data.applied_count > 0) {
            try {
              sessionStorage.setItem(storageKey, JSON.stringify({ data: data, label: templateLabel, expires: Date.now() + (undoRemaining || 10) * 1000 }));
              window.location.reload();
              return;
            } catch (error) {
              // Se o storage estiver bloqueado, mantém o desfazer nesta página.
            }
          }
          try { sessionStorage.removeItem(storageKey); } catch (error) { /* Storage opcional. */ }
          showToast(data, templateLabel, undoRemaining || 10);
        } else {
          if (data.code === 'stale_preview' || data.code === 'idempotency_key_reused') {
            resetReview();
          }
          if (errorMsg) {
            errorMsg.textContent = data.reason || 'Não foi possível aplicar. Confira o programa e tente novamente.';
            errorMsg.hidden = false;
          }
        }
      })
      .catch(function () {
        applying = false;
        btn.disabled = false;
        if (confirmBtn) confirmBtn.textContent = 'Aplicar agora';
        if (errorMsg) {
          errorMsg.textContent = 'Erro de conexão. Confira a sessão e tente novamente.';
          errorMsg.hidden = false;
        }
      });
  }

  document.addEventListener('click', function (event) {
    var triggerBtn = event.target.closest('[data-wod-day-apply-trigger]');
    if (triggerBtn) {
      event.preventDefault();
      openDialogForTrigger(triggerBtn);
      return;
    }

    var applyBtn = event.target.closest('[data-wod-day-apply-select]');
    if (applyBtn) {
      event.preventDefault();
      previewTemplate(applyBtn);
    }
  });

  if (confirmBtn) confirmBtn.addEventListener('click', function () {
    if (selectedTemplate) applyTemplate(selectedTemplate);
  });
  if (program) program.addEventListener('change', resetReview);
  if (dialog) dialog.querySelectorAll('[name=wod_day_apply_mode]').forEach(function (radio) {
    radio.addEventListener('change', resetReview);
  });

  // ── Toast + undo ──────────────────────────────────────────────────

  function showToast(data, templateLabel, seconds) {
    if (!toast || !toastMsg) return;
    var undoRemaining = data.undo_expires_at
      ? Math.max(0, Math.ceil((Date.parse(data.undo_expires_at) - Date.now()) / 1000))
      : (data.undo_unavailable ? 0 : seconds);
    currentUndoToken = undoRemaining > 0 ? data.undo_token : null;
    if (undoBtn) {
      undoBtn.hidden = !currentUndoToken;
      undoBtn.disabled = false;
    }

    var skipped = data.skipped_count > 0 ? ' · ' + data.skipped_count + ' pulada(s)' : '';
    toastMsg.textContent =
      '"' + templateLabel + '" aplicado em ' + data.applied_count + ' aula(s)' + skipped + '.' +
      (data.idempotent_replay ? ' Confirmação recuperada.' : '') +
      (data.undo_unavailable ? ' Desfazer indisponível por falha temporária.' : '') +
      (data.undo_token && !currentUndoToken ? ' A janela de desfazer terminou.' : '');

    toast.hidden = false;
    startCountdown(currentUndoToken ? Math.min(seconds, undoRemaining) : seconds);
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
    try { sessionStorage.removeItem(storageKey); } catch (error) { /* Storage opcional. */ }
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
          undoBtn.disabled = false;
          if (data.ok) {
            dismissToast();
            window.location.reload();
          } else {
            if (toastMsg) toastMsg.textContent = data.reason || 'Janela de desfazer encerrada.';
            undoBtn.hidden = true;
            currentUndoToken = null;
            clearInterval(countdownInterval);
            try { sessionStorage.removeItem(storageKey); } catch (error) { /* Storage opcional. */ }
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

  try {
    var saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null');
    if (saved && saved.expires > Date.now()) {
      showToast(saved.data, saved.label, Math.ceil((saved.expires - Date.now()) / 1000));
    } else {
      sessionStorage.removeItem(storageKey);
    }
  } catch (error) { /* Storage opcional. */ }
})();
