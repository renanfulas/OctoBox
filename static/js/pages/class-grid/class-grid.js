/*
ARQUIVO: comportamento da pagina de grade de aulas.

POR QUE ELE EXISTE:
- retira do template a logica interativa pesada da grade.
- concentra validacao, modal e reordenacao do workspace num modulo de pagina.
*/

(function() {
  var payloadElement = document.getElementById('current-page-behavior');
  var pagePayload = {};
  if (payloadElement) {
    try {
      pagePayload = JSON.parse(payloadElement.textContent || '{}');
    } catch (error) {
      pagePayload = {};
    }
  }

  var plannerForm = document.querySelector('form[data-class-grid-planner]');
  var plannerStartDateField = document.getElementById('id_start_date');
  var plannerEndDateField = document.getElementById('id_end_date');
  var plannerStartTimeField = document.getElementById('id_start_time');
  var plannerDurationField = document.getElementById('id_duration_minutes');
  var plannerCapacityField = document.getElementById('id_capacity');
  var sequenceCountField = document.getElementById('id_sequence_count');
  var sequenceCountLiveCopy = document.getElementById('sequence-count-live-copy');
  var dialog = document.getElementById('class-monthly-modal');
  var openButtons = [
    document.getElementById('open-monthly-calendar'),
    document.getElementById('open-monthly-calendar-preview')
  ].filter(Boolean);
  var closeButton = document.getElementById('close-monthly-calendar');
  var workspace = document.getElementById('class-grid-workspace');
  var resetLayoutButton = document.getElementById('reset-class-grid-layout');
  var storageKey = pagePayload.workspace_storage_key || (workspace ? workspace.dataset.storageKey : null);
  var defaultOrder = workspace ? Array.from(workspace.querySelectorAll('[data-panel-id]')).map(function(panel) {
    return panel.dataset.panelId;
  }) : [];

  var draggedPanel = null;
  var dragHandlePressed = false;

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function removeStorage(key) {
    try {
      window.localStorage.removeItem(key);
      return true;
    } catch (error) {
      return false;
    }
  }

  function isValidShortDate(value) {
    if (!/^\d{2}\/\d{2}\/\d{2}$/.test(value || '')) {
      return false;
    }

    var parts = value.split('/').map(Number);
    var day = parts[0];
    var month = parts[1];
    var year = 2000 + parts[2];
    var candidate = new Date(year, month - 1, day);
    return candidate.getFullYear() === year && candidate.getMonth() === month - 1 && candidate.getDate() === day;
  }

  function isValidTwentyFourHourTime(value) {
    return /^([01]\d|2[0-3]):[0-5]\d$/.test(value || '');
  }

  function parseShortDate(value) {
    if (!isValidShortDate(value)) {
      return null;
    }

    var parts = value.split('/').map(Number);
    return new Date(2000 + parts[2], parts[1] - 1, parts[0]);
  }

  function validatePlannerField(field, message) {
    if (!field) {
      return true;
    }

    field.setCustomValidity(message || '');
    return !message;
  }

  function validatePlannerDateField(field, requiredMessage, invalidMessage) {
    if (!field) {
      return true;
    }

    var value = (field.value || '').trim();
    if (!value) {
      return validatePlannerField(field, requiredMessage);
    }
    if (!isValidShortDate(value)) {
      return validatePlannerField(field, invalidMessage);
    }
    return validatePlannerField(field, '');
  }

  function validatePlannerTimeField(field) {
    if (!field) {
      return true;
    }

    var value = (field.value || '').trim();
    if (!value) {
      return validatePlannerField(field, 'Informe o horario inicial da aula.');
    }
    if (!isValidTwentyFourHourTime(value)) {
      return validatePlannerField(field, 'Use o horario em 24h no formato HH:MM. Ex.: 07:00.');
    }
    return validatePlannerField(field, '');
  }

  function validatePlannerPositiveIntegerField(field, emptyMessage, invalidMessage) {
    if (!field) {
      return true;
    }

    var value = (field.value || '').trim();
    if (!value) {
      return validatePlannerField(field, emptyMessage);
    }
    if (!/^\d+$/.test(value) || Number(value) <= 0) {
      return validatePlannerField(field, invalidMessage);
    }
    return validatePlannerField(field, '');
  }

  function validatePlannerDateRange() {
    if (!plannerStartDateField || !plannerEndDateField) {
      return true;
    }

    var startDate = parseShortDate(plannerStartDateField.value.trim());
    var endDate = parseShortDate(plannerEndDateField.value.trim());
    if (!startDate || !endDate) {
      return true;
    }
    if (endDate < startDate) {
      return validatePlannerField(plannerEndDateField, 'A data final precisa ser igual ou posterior ao primeiro dia.');
    }
    return validatePlannerField(plannerEndDateField, '');
  }

  function validatePlannerForm() {
    var validations = [
      validatePlannerDateField(plannerStartDateField, 'Informe o primeiro dia da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.'),
      validatePlannerDateField(plannerEndDateField, 'Informe a data final da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.'),
      validatePlannerTimeField(plannerStartTimeField),
      validatePlannerPositiveIntegerField(plannerDurationField, 'Informe a duracao da aula.', 'A duracao precisa ser um numero inteiro maior que zero.'),
      validatePlannerPositiveIntegerField(plannerCapacityField, 'Informe a capacidade da turma.', 'A capacidade precisa ser um numero inteiro maior que zero.'),
      validatePlannerDateRange()
    ];

    return validations.every(Boolean);
  }

  function bindPlannerField(field, inputHandler, blurHandler) {
    if (!field) {
      return;
    }

    if (inputHandler) {
      field.addEventListener('input', inputHandler);
    }

    if (blurHandler) {
      field.addEventListener('blur', blurHandler);
    }
  }

  bindPlannerField(plannerStartDateField, function() {
    validatePlannerDateField(plannerStartDateField, 'Informe o primeiro dia da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.');
    validatePlannerDateRange();
  }, function() {
    validatePlannerDateField(plannerStartDateField, 'Informe o primeiro dia da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.');
    validatePlannerDateRange();
  });

  bindPlannerField(plannerEndDateField, function() {
    validatePlannerDateField(plannerEndDateField, 'Informe a data final da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.');
    validatePlannerDateRange();
  }, function() {
    validatePlannerDateField(plannerEndDateField, 'Informe a data final da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.');
    validatePlannerDateRange();
  });

  bindPlannerField(plannerStartTimeField, function() {
    validatePlannerTimeField(plannerStartTimeField);
  }, function() {
    validatePlannerTimeField(plannerStartTimeField);
  });

  bindPlannerField(plannerDurationField, function() {
    validatePlannerPositiveIntegerField(plannerDurationField, 'Informe a duracao da aula.', 'A duracao precisa ser um numero inteiro maior que zero.');
  }, function() {
    validatePlannerPositiveIntegerField(plannerDurationField, 'Informe a duracao da aula.', 'A duracao precisa ser um numero inteiro maior que zero.');
  });

  bindPlannerField(plannerCapacityField, function() {
    validatePlannerPositiveIntegerField(plannerCapacityField, 'Informe a capacidade da turma.', 'A capacidade precisa ser um numero inteiro maior que zero.');
  }, function() {
    validatePlannerPositiveIntegerField(plannerCapacityField, 'Informe a capacidade da turma.', 'A capacidade precisa ser um numero inteiro maior que zero.');
  });

  if (plannerForm) {
    plannerForm.addEventListener('submit', function(event) {
      if (validatePlannerForm()) {
        return;
      }
      event.preventDefault();
      plannerForm.reportValidity();
    });
  }

  function syncSequenceCountCopy() {
    if (!sequenceCountField || !sequenceCountLiveCopy) {
      return;
    }

    var selectedValue = Number(sequenceCountField.value || 0);
    var totalClasses = selectedValue + 1;

    if (selectedValue <= 0) {
      sequenceCountLiveCopy.textContent = 'Vai criar 1 aula nesse horario base.';
      return;
    }

    sequenceCountLiveCopy.textContent = 'Vai criar ' + totalClasses + ' aulas seguidas a partir do horario inicial.';
  }

  syncSequenceCountCopy();
  if (sequenceCountField) {
    sequenceCountField.addEventListener('change', syncSequenceCountCopy);
  }

  function syncPanelButtons() {
    if (!workspace) {
      return;
    }

    var panels = Array.from(workspace.children).filter(function(panel) {
      return panel.hasAttribute('data-panel-id');
    });
    panels.forEach(function(panel, index) {
      panel.dataset.panelPosition = String(index + 1);
    });
  }

  function getWorkspacePanels() {
    if (!workspace) {
      return [];
    }

    return Array.from(workspace.querySelectorAll('[data-panel-id]'));
  }

  function getDragAfterElement(container, clientY) {
    var panels = Array.from(container.querySelectorAll('[data-panel-id]:not(.is-dragging)'));

    return panels.reduce(function(closest, panel) {
      var box = panel.getBoundingClientRect();
      var offset = clientY - box.top - box.height / 2;

      if (offset < 0 && offset > closest.offset) {
        return {
          offset: offset,
          element: panel
        };
      }

      return closest;
    }, {
      offset: Number.NEGATIVE_INFINITY,
      element: null
    }).element;
  }

  function persistWorkspaceOrder() {
    if (!workspace || !storageKey) {
      return;
    }

    var state = {};
    Array.from(workspace.querySelectorAll('[data-grid-slot]')).forEach(function(slot) {
      var slotId = slot.dataset.gridSlot;
      state[slotId] = Array.from(slot.children).filter(function(panel) {
        return panel.hasAttribute('data-panel-id');
      }).map(function(panel) {
        return panel.dataset.panelId;
      });
    });
    writeStorage(storageKey, JSON.stringify(state));
    syncPanelButtons();
  }

  function restoreWorkspaceOrder() {
    if (!workspace || !storageKey) {
      return;
    }

    var storedOrder = readStorage(storageKey);
    if (!storedOrder) {
      syncPanelButtons();
      return;
    }

    try {
      var state = JSON.parse(storedOrder);
      if (Array.isArray(state)) {
        removeStorage(storageKey);
        syncPanelButtons();
        return;
      }
      
      Object.keys(state).forEach(function(slotId) {
        var slot = workspace.querySelector('[data-grid-slot="' + slotId + '"]');
        if (!slot) return;
        state[slotId].forEach(function(id) {
          var panel = workspace.querySelector('[data-panel-id="' + id + '"]');
          if (panel) {
            slot.appendChild(panel);
          }
        });
      });
    } catch (error) {
      removeStorage(storageKey);
    }

    syncPanelButtons();
  }

  if (workspace) {
    restoreWorkspaceOrder();

    workspace.addEventListener('pointerdown', function(event) {
      dragHandlePressed = Boolean(event.target.closest('[data-drag-handle]'));
    });

    workspace.addEventListener('pointerup', function() {
      dragHandlePressed = false;
    });

    workspace.addEventListener('dragstart', function(event) {
      var panel = event.target.closest('[data-panel-id]');
      if (!panel || !dragHandlePressed) {
        event.preventDefault();
        return;
      }

      draggedPanel = panel;
      panel.classList.add('is-dragging');
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', panel.dataset.panelId || '');
      }
    });

    workspace.addEventListener('dragover', function(event) {
      if (!draggedPanel) {
        return;
      }

      var slot = event.target.closest('[data-grid-slot]');
      if (!slot) {
        return;
      }

      event.preventDefault();
      var afterElement = getDragAfterElement(slot, event.clientY);
      if (!afterElement) {
        slot.appendChild(draggedPanel);
        return;
      }
      slot.insertBefore(draggedPanel, afterElement);
    });

    workspace.addEventListener('drop', function(event) {
      if (!draggedPanel) {
        return;
      }

      event.preventDefault();
      persistWorkspaceOrder();
    });

    workspace.addEventListener('dragend', function() {
      if (!draggedPanel) {
        return;
      }

      draggedPanel.classList.remove('is-dragging');
      draggedPanel = null;
      dragHandlePressed = false;
      persistWorkspaceOrder();
    });

    workspace.addEventListener('keydown', function(event) {
      var handle = event.target.closest('[data-drag-handle]');
      if (!handle) {
        return;
      }

      var panel = handle.closest('[data-panel-id]');
      if (!panel) {
        return;
      }

      if (event.key === 'ArrowUp' && panel.previousElementSibling) {
        event.preventDefault();
        workspace.insertBefore(panel, panel.previousElementSibling);
        persistWorkspaceOrder();
        handle.focus();
      }

      if (event.key === 'ArrowDown' && panel.nextElementSibling) {
        event.preventDefault();
        workspace.insertBefore(panel.nextElementSibling, panel);
        persistWorkspaceOrder();
        handle.focus();
      }
    });
  }

  if (resetLayoutButton && workspace && storageKey) {
    resetLayoutButton.addEventListener('click', function() {
      removeStorage(storageKey);
      defaultOrder.forEach(function(id) {
        var panel = workspace.querySelector('[data-panel-id="' + id + '"]');
        if (panel) {
          workspace.appendChild(panel);
        }
      });
      syncPanelButtons();
    });
  }

  if (!dialog || !dialog.showModal) {
    syncPanelButtons();
    return;
  }

  openButtons.forEach(function(button) {
    button.addEventListener('click', function() {
      dialog.showModal();
    });
  });

  if (closeButton) {
    closeButton.addEventListener('click', function() {
      dialog.close();
    });
  }

  dialog.addEventListener('click', function(event) {
    var panel = dialog.querySelector('.class-monthly-modal-panel');
    if (panel && !panel.contains(event.target)) {
      dialog.close();
    }
  });

  /* ────────────────────────────────────────────────
     Visão semanal – modal de tela cheia
     ──────────────────────────────────────────────── */
  var weeklyDialog = document.getElementById('class-weekly-modal');
  var weeklyCloseButton = document.getElementById('close-weekly-modal');
  var weeklyFullView = document.getElementById('weekly-modal-full-view');
  var weeklyDayView = document.getElementById('weekly-modal-day-view');
  var weeklyModalTitle = document.getElementById('class-weekly-modal-title');
  var weeklyBoard = document.getElementById('weekly-board');

  function openWeeklyModal(mode, dayCard) {
    if (!weeklyDialog || !weeklyDialog.showModal) return;

    if (mode === 'day' && dayCard) {
      // Modo dia: esconde grade completa, mostra o dia clicado
      if (weeklyFullView) weeklyFullView.style.display = 'none';
      if (weeklyDayView) {
        weeklyDayView.style.display = 'block';
        weeklyDayView.innerHTML = '<div class="weekly-calendar-grid" style="grid-template-columns: 1fr; min-width: 0; max-width: 640px; margin: 0 auto;">' + dayCard.outerHTML + '</div>';
        // Remove o cursor pointer do clone dentro do modal
        var clone = weeklyDayView.querySelector('.weekly-day-card');
        if (clone) {
          clone.style.cursor = 'default';
          clone.style.minHeight = 'auto';
        }
      }
      var dayLabel = dayCard.querySelector('.eyebrow');
      var dayDate = dayCard.querySelector('strong');
      if (weeklyModalTitle) {
        weeklyModalTitle.textContent = (dayLabel ? dayLabel.textContent : '') + ' ' + (dayDate ? dayDate.textContent : '');
      }
    } else {
      // Modo completo: mostra grade inteira
      if (weeklyFullView) weeklyFullView.style.display = 'block';
      if (weeklyDayView) weeklyDayView.style.display = 'none';
      if (weeklyModalTitle) weeklyModalTitle.textContent = 'Grade completa';
    }

    weeklyDialog.showModal();
  }

  // Clique no header da visão semanal → abre grade completa
  if (weeklyBoard) {
    var weeklyHead = weeklyBoard.querySelector('.card-head');
    if (weeklyHead) {
      weeklyHead.style.cursor = 'pointer';
      weeklyHead.addEventListener('click', function(event) {
        // Não interceptar cliques em botões/links dentro do header
        if (event.target.closest('a, button')) return;
        openWeeklyModal('full');
      });
    }
  }

  // Clique em qualquer day card na visão semanal → abre aquele dia
  document.querySelectorAll('#weekly-board [data-day-date]').forEach(function(card) {
    card.addEventListener('click', function(event) {
      // Não interceptar cliques em botões/links (Editar, Excluir)
      if (event.target.closest('a, button, form')) return;
      openWeeklyModal('day', card);
    });
    card.addEventListener('keydown', function(event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openWeeklyModal('day', card);
      }
    });
  });

  // Fechar o modal semanal
  if (weeklyCloseButton) {
    weeklyCloseButton.addEventListener('click', function() {
      weeklyDialog.close();
    });
  }

  if (weeklyDialog) {
    weeklyDialog.addEventListener('click', function(event) {
      var panel = weeklyDialog.querySelector('.class-monthly-modal-panel');
      if (panel && !panel.contains(event.target)) {
        weeklyDialog.close();
      }
    });
  }

  /* ────────────────────────────────────────────────
     Click em botões de foco operacional (Abrir Modais)
     ──────────────────────────────────────────────── */
  document.querySelectorAll('.class-grid-focus-actions a').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      var href = btn.getAttribute('href');

      if (href === '#today-board') {
        e.preventDefault();
        var todayCard = document.querySelector('#weekly-board .weekly-day-card.is-today');
        if (todayCard && typeof openWeeklyModal === 'function') {
          openWeeklyModal('day', todayCard);
        } else if (typeof openWeeklyModal === 'function') {
          openWeeklyModal('full');
        }
      } else if (href === '#weekly-board') {
        e.preventDefault();
        if (typeof openWeeklyModal === 'function') {
          openWeeklyModal('full');
        }
      } else if (href === '#monthly-board' || href === '#planner-board') {
        e.preventDefault();
        if (dialog && typeof dialog.showModal === 'function') {
           dialog.showModal();
        }
      }
    });
  });

}());