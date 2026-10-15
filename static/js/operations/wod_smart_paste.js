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
      showDayDialog(parentDialog);
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
    var scrollBody = reviewTarget.closest('.smart-paste-day-dialog__body');
    if (scrollBody) {
      scrollBody.scrollTop += reviewTarget.getBoundingClientRect().top - scrollBody.getBoundingClientRect().top - 16;
    } else {
      reviewTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
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
    if (activeBlock) {
      body.scrollTop += activeBlock.getBoundingClientRect().top - body.getBoundingClientRect().top;
    }
  }

  function restoreDayDialog(dialog) {
    var owner = dialog._smartPasteOwner;
    var returnFocus = dialog._smartPasteReturnFocus;
    dialog._smartPasteOwner = null;
    dialog._smartPasteReturnFocus = null;
    if (!owner) return;
    if (owner.isConnected) owner.appendChild(dialog);
    else dialog.remove();
    if (returnFocus && returnFocus.isConnected && typeof returnFocus.focus === 'function') {
      window.requestAnimationFrame(function () {
        if (returnFocus.isConnected) returnFocus.focus({ preventScroll: true });
      });
    }
  }

  function showDayDialog(dialog) {
    if (!dialog || typeof dialog.showModal !== 'function' || dialog.open) return;
    // Safari can anchor a modal inside the blurred preview card to its scroll
    // position. Put it directly under body while it is in the top layer.
    var owner = dialog.closest('[data-smart-paste-preview-panel], [data-smart-paste-projection-panel]');
    var activeElement = document.activeElement;
    dialog._smartPasteReturnFocus = activeElement && activeElement !== document.body && !dialog.contains(activeElement)
      ? activeElement
      : owner && owner.querySelector('[data-action="open-week-dialog"], [data-action="open-day-dialog"]');
    if (owner) {
      dialog._smartPasteOwner = owner;
      document.body.appendChild(dialog);
    }
    dialog.showModal();
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
          showDayDialog(dialog);
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
    // Close dialog on backdrop click
    scope.querySelectorAll('.smart-paste-day-dialog').forEach(function (dialog) {
      if (dialog.dataset.backdropBound === 'true') return;
      dialog.dataset.backdropBound = 'true';
      dialog.addEventListener('close', function () { restoreDayDialog(dialog); });
      dialog.addEventListener('click', function (e) {
        if (e.target === dialog) {
          var body = dialog.querySelector('.smart-paste-day-dialog__body');
          if (body) clearFocusedBlock(body);
          dialog.close();
        }
      });
    });
  }

  function bindProjectionDialog(scope) {
    if (!scope) return;
    var panel = scope.matches('[data-smart-paste-projection-panel]')
      ? scope
      : scope.querySelector('[data-smart-paste-projection-panel]');
    if (!panel) return;
    var dialog = panel.querySelector('.smart-paste-week-dialog');
    if (!dialog) return;
    var weekdayButtons = Array.from(dialog.querySelectorAll('[data-weekday-filter]'));
    var weekdayCards = Array.from(dialog.querySelectorAll('[data-weekday-index]'));
    var emptyWeekdayState = dialog.querySelector('[data-weekday-filter-empty]');
    weekdayButtons.forEach(function (button) {
      if (button.dataset.weekdayFilterBound === 'true') return;
      button.dataset.weekdayFilterBound = 'true';
      button.addEventListener('click', function () {
        var selectedWeekday = button.dataset.weekdayFilter;
        var visibleCards = 0;
        weekdayButtons.forEach(function (candidate) {
          var active = candidate === button;
          candidate.classList.toggle('is-active', active);
          candidate.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        weekdayCards.forEach(function (card) {
          var visible = selectedWeekday === 'all' || card.dataset.weekdayIndex === selectedWeekday;
          card.hidden = !visible;
          if (visible) visibleCards += 1;
        });
        if (emptyWeekdayState) emptyWeekdayState.hidden = selectedWeekday === 'all' || visibleCards > 0;
      });
    });
    var unlinkedAck = dialog.querySelector('[data-action="acknowledge-unlinked-movements"]');
    var distributeButton = dialog.querySelector('[data-action="distribute-week"]');
    if (unlinkedAck && distributeButton && distributeButton.dataset.ackBound !== 'true') {
      distributeButton.dataset.ackBound = 'true';
      function syncDistributionAcknowledgement() {
        var allowed = distributeButton.dataset.eligible === 'true' && unlinkedAck.checked;
        distributeButton.disabled = !allowed;
        if (allowed) distributeButton.removeAttribute('aria-disabled');
        else distributeButton.setAttribute('aria-disabled', 'true');
      }
      unlinkedAck.addEventListener('change', syncDistributionAcknowledgement);
      syncDistributionAcknowledgement();
    }

    function closeDialog() {
      if (dialog.open) dialog.close();
    }

    panel.querySelectorAll('[data-action="open-week-dialog"]').forEach(function (button) {
      if (button.dataset.weekDialogBound === 'true') return;
      button.dataset.weekDialogBound = 'true';
      button.addEventListener('click', function () { showDayDialog(dialog); });
    });
    dialog.querySelectorAll('[data-action="close-week-dialog"]').forEach(function (button) {
      if (button.dataset.weekDialogBound === 'true') return;
      button.dataset.weekDialogBound = 'true';
      button.addEventListener('click', closeDialog);
    });
    if (dialog.dataset.weekDialogBound !== 'true') {
      dialog.dataset.weekDialogBound = 'true';
      dialog.addEventListener('close', function () { restoreDayDialog(dialog); });
      dialog.addEventListener('click', function (event) {
        if (event.target === dialog) closeDialog();
      });
    }
    if (dialog.dataset.autoOpen === 'true') {
      dialog.dataset.autoOpen = 'false';
      showDayDialog(dialog);
    }
  }

  function bindConfirmationSourceGuard() {
    var sourceField = root.querySelector('.smart-paste-form textarea[name="source_text"]');
    var weekField = root.querySelector('.smart-paste-form [name="week_start"]');
    var labelField = root.querySelector('.smart-paste-form [name="label"]');
    if (!sourceField) return;
    root.querySelectorAll('form.smart-paste-confirm-form').forEach(function (form) {
      if (form.dataset.sourceGuardBound === 'true') return;
      var confirmedSource = form.querySelector('input[name="source_text"]');
      var confirmedWeek = form.querySelector('input[name="week_start"]');
      var confirmedLabel = form.querySelector('input[name="label"]');
      var notice = form.querySelector('[data-smart-paste-stale-source-notice]');
      if (!confirmedSource || !notice) return;
      var buttons = Array.prototype.slice.call(form.querySelectorAll('button[type="submit"]'));
      buttons.forEach(function (button) {
        button.dataset.sourceGuardBaseDisabled = button.disabled ? 'true' : 'false';
      });

      function normalizeWeek(value) {
        var match = String(value || '').trim().match(/^(\d{1,2})\/(\d{1,2})(?:\/\d{2,4})?$/);
        return match ? pad(match[1]) + '/' + pad(match[2]) : String(value || '').trim();
      }

      function syncState() {
        var stale = sourceField.value !== confirmedSource.value;
        if (weekField && confirmedWeek) {
          stale = stale || normalizeWeek(weekField.value) !== normalizeWeek(confirmedWeek.value);
        }
        if (labelField && confirmedLabel) {
          stale = stale || labelField.value !== confirmedLabel.value;
        }
        notice.hidden = !stale;
        buttons.forEach(function (button) {
          button.disabled = stale || button.dataset.sourceGuardBaseDisabled === 'true';
          if (button.disabled) button.setAttribute('aria-disabled', 'true');
          else button.removeAttribute('aria-disabled');
        });
        return stale;
      }

      sourceField.addEventListener('input', syncState);
      if (weekField) weekField.addEventListener('input', syncState);
      if (labelField) labelField.addEventListener('input', syncState);
      form.addEventListener('submit', function (event) {
        if (!syncState()) return;
        event.preventDefault();
        sourceField.focus();
        notice.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
      form.dataset.sourceGuardBound = 'true';
      syncState();
    });
  }

  function initializeScope(scope) {
    if (!scope) return;
    scope.querySelectorAll('[data-smart-date-input]').forEach(bindSmartDateField);
    bindDayDialogs(scope);
    bindProjectionDialog(scope);
    bindReviewQueue(scope);
    bindConfirmationSourceGuard();
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-action="use-custom-movement"]');
    if (!button || (!root.contains(button) && !button.closest('dialog.smart-paste-day-dialog'))) return;
    var form = button.closest('form');
    var slugField = form && form.querySelector('[name="movement_slug"]');
    if (!slugField) return;
    slugField.value = 'custom';
    slugField.dispatchEvent(new Event('input', { bubbles: true }));
    button.textContent = 'Nome original será mantido';
    button.setAttribute('aria-pressed', 'true');
  });

  initializeScope(root);

  document.body.addEventListener('htmx:beforeSwap', function (event) {
    if (!event.detail || !event.detail.target || !event.detail.target.matches('[data-smart-paste-preview-panel], [data-smart-paste-projection-panel]')) return;
    document.querySelectorAll('dialog.smart-paste-day-dialog, dialog.smart-paste-week-dialog').forEach(function (dialog) {
      if (!dialog._smartPasteOwner) return;
      if (dialog.open) dialog.close();
      restoreDayDialog(dialog);
    });
  });

  document.body.addEventListener('htmx:afterSwap', function (event) {
    initializeScope(event.target);
  });
})();
