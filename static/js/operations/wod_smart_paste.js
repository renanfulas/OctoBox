/*
ARQUIVO: comportamentos leves da superficie de Smart Paste semanal.

POR QUE ELE EXISTE:
- endurece os campos de semana em dd/mm e oferece um atalho de calendario.
*/

(function () {
  var root = document.querySelector('.smart-paste-shell');
  if (!root) return;

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function bindSmartDateField(field) {
    if (!field || field.dataset.smartDateBound === 'true') return;
    field.dataset.smartDateBound = 'true';
    var includesYear = field.dataset.smartDateIncludeYear === 'true';
    var isHiddenField = field.type === 'hidden';
    if (!isHiddenField) {
      field.dataset.mask = 'date';
      field.dataset.yearDigits = includesYear ? '4' : '2';
    }
    if (!isHiddenField && window.OctoForms && typeof window.OctoForms.applyMaskedFields === 'function') {
      window.OctoForms.applyMaskedFields(field.parentNode || document);
    }

    var pickerId = field.dataset.pickerTarget || '';
    var picker = pickerId ? document.getElementById(pickerId) : null;
    var button = field.parentNode ? field.parentNode.querySelector('[data-smart-date-button]') : null;
    var displayId = field.dataset.displayTarget || '';
    var display = displayId ? document.getElementById(displayId) : null;

    function openTransientPicker() {
      if (!picker) return;

      // showPicker() precisa ser chamado no elemento REAL (não em clone):
      // clonar quebra o trusted-gesture context no Chrome/Edge.
      // Estratégia: posicionar o picker real perto do botão (para o calendário
      // abrir ali), remover hidden temporariamente, chamar showPicker(),
      // e restaurar o estado depois.

      var anchor = button || field;
      var rect = anchor ? anchor.getBoundingClientRect() : null;

      var hadHidden = picker.hasAttribute('hidden');
      var savedCssText = picker.style.cssText || '';

      // Âncora o picker perto do botão — o calendário nativo abre próximo ao input.
      // Importante: limpar clip/clip-path da classe .smart-paste-native-picker,
      // senão showPicker() falha (elemento percebido como "não renderizado").
      picker.style.cssText = [
        'position:fixed',
        rect ? 'left:' + Math.round(rect.left) + 'px' : 'left:0',
        rect ? 'top:' + Math.round(rect.bottom + 4) + 'px' : 'top:0',
        'width:1px',
        'height:1px',
        'opacity:0',
        'pointer-events:none',
        'z-index:9999',
        'clip:auto',
        'clip-path:none',
        'overflow:visible',
        'white-space:normal',
        'margin:0',
        'padding:0',
        'border:0'
      ].join(';');

      if (hadHidden) picker.removeAttribute('hidden');
      picker.removeAttribute('aria-hidden');

      // Força reflow síncrono — sem isso o primeiro clique abre no topo.
      void picker.offsetHeight;

      function restore() {
        picker.style.cssText = savedCssText;
        if (hadHidden) picker.setAttribute('hidden', '');
        picker.setAttribute('aria-hidden', 'true');
      }

      picker.addEventListener('change', restore, { once: true });
      picker.addEventListener('blur', function () {
        window.setTimeout(restore, 50);
      }, { once: true });

      if (typeof picker.showPicker === 'function') {
        try {
          picker.showPicker();
        } catch (e) {
          picker.click();
          picker.focus();
        }
      } else {
        picker.click();
        picker.focus();
      }
    }

    function formatDisplayValue(parts) {
      return includesYear
        ? pad(parts[2]) + '/' + pad(parts[1]) + '/' + parts[0]
        : pad(parts[2]) + '/' + pad(parts[1]);
    }

    function resolveClosestPickerYear(day, month) {
      var today = new Date();
      var currentYearCandidate = new Date(today.getFullYear(), Number(month) - 1, Number(day));
      var nextYearCandidate = new Date(today.getFullYear() + 1, Number(month) - 1, Number(day));
      var currentDistance = Math.abs(currentYearCandidate.getTime() - today.getTime());
      var nextDistance = Math.abs(nextYearCandidate.getTime() - today.getTime());
      return currentDistance <= nextDistance ? today.getFullYear() : today.getFullYear() + 1;
    }

    function syncFromPicker() {
      if (!picker || !picker.value) return;
      var parts = picker.value.split('-');
      if (parts.length !== 3) return;
      var formattedValue = formatDisplayValue(parts);
      field.value = formattedValue;
      if (display) display.textContent = formattedValue;
      field.dispatchEvent(new Event('input', { bubbles: true }));
      if (!isHiddenField) {
        field.dispatchEvent(new Event('blur', { bubbles: true }));
      }
    }

    function syncPickerFromText() {
      if (!picker) return;
      var normalized = String(field.value || '').replace(/\D/g, '');
      if (normalized.length < 4) return;
      var day = normalized.slice(0, 2);
      var month = normalized.slice(2, 4);
      var year = null;
      if (includesYear && normalized.length >= 8) {
        year = Number(normalized.slice(4, 8));
      }
      if (!year) {
        year = includesYear ? new Date().getFullYear() : resolveClosestPickerYear(day, month);
      }
      var candidate = new Date(year, Number(month) - 1, Number(day));
      if (
        candidate.getFullYear() === year &&
        candidate.getMonth() === Number(month) - 1 &&
        candidate.getDate() === Number(day)
      ) {
        picker.value = year + '-' + pad(month) + '-' + pad(day);
      }
    }

    if (picker) {
      picker.addEventListener('change', syncFromPicker);
      if (!isHiddenField) {
        field.addEventListener('blur', syncPickerFromText);
      }
    }

    // Se o campo está num monday-wrap, o smart_paste_week_monday.js gerencia
    // o botão — não bindamos aqui para evitar duplo disparo.
    var isMondayWrap = button && button.closest('[data-smart-date-monday-wrap]');
    if (button && picker && !isMondayWrap) {
      button.addEventListener('click', function () {
        openTransientPicker();
      });
    }

    if (picker && picker.value) {
      syncFromPicker();
    } else if (display && field.value) {
      display.textContent = field.value;
    }
  }

  function openReviewTarget(targetId) {
    if (!targetId) return;
    var reviewTarget = document.getElementById(String(targetId).replace(/^#/, ''));
    if (!reviewTarget) return;
    // If target lives inside a <dialog>, open the dialog first
    var parentDialog = reviewTarget.closest('dialog');
    if (parentDialog && !parentDialog.open) {
      parentDialog.showModal();
    }
    var parentBlock = reviewTarget.closest('[data-dialog-block]');
    if (parentBlock) {
      var parentBody = parentBlock.closest('.smart-paste-day-dialog__body');
      if (parentBody) {
        setFocusedBlock(parentBody, parentBlock.dataset.blockFocusId || '');
      }
    }
    if (reviewTarget.tagName === 'DETAILS') {
      reviewTarget.open = true;
    }
    reviewTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
    var focusField = reviewTarget.querySelector('input:not([type=hidden]), textarea, select');
    if (focusField) {
      window.setTimeout(function () { focusField.focus(); }, 180);
    }
  }

  function setFocusedBlock(body, focusId) {
    if (!body || !focusId) return;
    body.dataset.dialogMode = 'focused';
    body.dataset.focusedBlockId = focusId;
    var activeBlock = null;
    body.querySelectorAll('[data-dialog-block]').forEach(function (block) {
      var isActive = block.dataset.blockFocusId === focusId;
      if (isActive) activeBlock = block;
      block.classList.toggle('is-active', isActive);
      block.classList.toggle('is-hidden', !isActive);
      var surface = block.querySelector('[data-action="focus-block"]');
      var detail = block.querySelector('.smart-paste-block-detail');
      if (surface) surface.setAttribute('aria-expanded', isActive ? 'true' : 'false');
      if (detail) detail.hidden = !isActive;
    });
    if (activeBlock && typeof activeBlock.scrollIntoView === 'function') {
      activeBlock.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function clearFocusedBlock(body) {
    if (!body) return;
    body.dataset.dialogMode = 'overview';
    delete body.dataset.focusedBlockId;
    body.querySelectorAll('[data-dialog-block]').forEach(function (block) {
      block.classList.remove('is-active');
      block.classList.remove('is-hidden');
      var surface = block.querySelector('[data-action="focus-block"]');
      var detail = block.querySelector('.smart-paste-block-detail');
      if (surface) surface.setAttribute('aria-expanded', 'false');
      if (detail) {
        detail.hidden = true;
        detail.querySelectorAll('details').forEach(function (disclosure) {
          disclosure.open = false;
        });
      }
    });
    body.scrollTop = 0;
  }

  function bindReviewQueue(scope) {
    if (!scope) return;
    scope.querySelectorAll('[data-smart-paste-review-jump]').forEach(function (link) {
      if (link.dataset.smartPasteReviewJumpBound === 'true') return;
      link.dataset.smartPasteReviewJumpBound = 'true';
      link.addEventListener('click', function (event) {
        var href = link.getAttribute('href') || '';
        if (!href.startsWith('#')) return;
        event.preventDefault();
        openReviewTarget(href);
      });
    });
    var previewPanel = scope.matches('[data-smart-paste-preview-panel]') ? scope : scope.querySelector('[data-smart-paste-preview-panel]');
    if (previewPanel) {
      var autoOpenTarget = previewPanel.dataset.smartPasteAutoOpenTarget || '';
      if (autoOpenTarget) {
        openReviewTarget(autoOpenTarget);
      }
    }
  }

  function bindDayDialogs(scope) {
    if (!scope) return;
    scope.querySelectorAll('[data-action="open-day-dialog"]').forEach(function (btn) {
      if (btn.dataset.dayDialogBound === 'true') return;
      btn.dataset.dayDialogBound = 'true';
      btn.addEventListener('click', function () {
        var targetId = btn.dataset.target;
        if (!targetId) return;
        var dialog = document.getElementById(targetId);
        if (dialog && typeof dialog.showModal === 'function') {
          var body = dialog.querySelector('.smart-paste-day-dialog__body');
          if (body) clearFocusedBlock(body);
          dialog.showModal();
        }
      });
    });
    scope.querySelectorAll('[data-action="close-dialog"]').forEach(function (btn) {
      if (btn.dataset.closeDialogBound === 'true') return;
      btn.dataset.closeDialogBound = 'true';
      btn.addEventListener('click', function () {
        var dialog = btn.closest('dialog');
        if (dialog) {
          var body = dialog.querySelector('.smart-paste-day-dialog__body');
          if (body) clearFocusedBlock(body);
          dialog.close();
        }
      });
    });
    scope.querySelectorAll('[data-action="focus-block"]').forEach(function (btn) {
      if (btn.dataset.focusBlockBound === 'true') return;
      btn.dataset.focusBlockBound = 'true';
      btn.addEventListener('click', function () {
        var body = btn.closest('.smart-paste-day-dialog__body');
        var focusId = btn.dataset.target || '';
        setFocusedBlock(body, focusId);
      });
    });
    scope.querySelectorAll('[data-action="unfocus-block"]').forEach(function (btn) {
      if (btn.dataset.unfocusBlockBound === 'true') return;
      btn.dataset.unfocusBlockBound = 'true';
      btn.addEventListener('click', function () {
        var body = btn.closest('.smart-paste-day-dialog__body');
        clearFocusedBlock(body);
      });
    });
    // Copy day text to clipboard for GPT
    scope.querySelectorAll('[data-action="copy-gpt-text"]').forEach(function (btn) {
      if (btn.dataset.copyGptBound === 'true') return;
      btn.dataset.copyGptBound = 'true';
      btn.addEventListener('click', function () {
        var footer = btn.closest('footer');
        if (!footer) return;
        var source = footer.querySelector('[data-gpt-source]');
        if (!source) return;
        var text = source.value.trim();
        var feedback = btn.dataset.feedback || 'Copiado!';
        var original = btn.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            btn.textContent = feedback;
            btn.disabled = true;
            window.setTimeout(function () {
              btn.textContent = original;
              btn.disabled = false;
            }, 2000);
          });
        } else {
          source.select();
          document.execCommand('copy');
          btn.textContent = feedback;
          window.setTimeout(function () { btn.textContent = original; }, 2000);
        }
      });
    });
    // Close dialog on backdrop click
    scope.querySelectorAll('.smart-paste-day-dialog').forEach(function (dialog) {
      if (dialog.dataset.backdropBound === 'true') return;
      dialog.dataset.backdropBound = 'true';
      dialog.addEventListener('click', function (e) {
        if (e.target === dialog) {
          var body = dialog.querySelector('.smart-paste-day-dialog__body');
          if (body) clearFocusedBlock(body);
          dialog.close();
        }
      });
    });
  }

  function initializeScope(scope) {
    if (!scope) return;
    scope.querySelectorAll('[data-smart-date-input]').forEach(bindSmartDateField);
    bindReviewQueue(scope);
    bindDayDialogs(scope);
  }

  initializeScope(root);

  document.body.addEventListener('htmx:afterSwap', function (event) {
    initializeScope(event.target);
  });
})();
