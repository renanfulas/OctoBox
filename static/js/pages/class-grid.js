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

  function onlyDigits(value) {
    return (value || '').replace(/\D/g, '');
  }

  function formatDateInput(value) {
    var digits = onlyDigits(value).slice(0, 6);
    if (digits.length <= 2) {
      return digits;
    }
    if (digits.length <= 4) {
      return digits.slice(0, 2) + '/' + digits.slice(2);
    }
    return digits.slice(0, 2) + '/' + digits.slice(2, 4) + '/' + digits.slice(4);
  }

  function formatTimeInput(value) {
    var digits = onlyDigits(value).slice(0, 4);
    if (digits.length <= 2) {
      return digits;
    }
    return digits.slice(0, 2) + ':' + digits.slice(2);
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
    plannerStartDateField.value = formatDateInput(plannerStartDateField.value);
    validatePlannerDateField(plannerStartDateField, 'Informe o primeiro dia da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.');
    validatePlannerDateRange();
  }, function() {
    validatePlannerDateField(plannerStartDateField, 'Informe o primeiro dia da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 11/03/26.');
    validatePlannerDateRange();
  });

  bindPlannerField(plannerEndDateField, function() {
    plannerEndDateField.value = formatDateInput(plannerEndDateField.value);
    validatePlannerDateField(plannerEndDateField, 'Informe a data final da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.');
    validatePlannerDateRange();
  }, function() {
    validatePlannerDateField(plannerEndDateField, 'Informe a data final da recorrencia.', 'Use a data no formato dd/mm/aa. Ex.: 08/04/26.');
    validatePlannerDateRange();
  });

  bindPlannerField(plannerStartTimeField, function() {
    plannerStartTimeField.value = formatTimeInput(plannerStartTimeField.value);
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

    var order = getWorkspacePanels().map(function(panel) {
      return panel.dataset.panelId;
    });
    localStorage.setItem(storageKey, JSON.stringify(order));
    syncPanelButtons();
  }

  function restoreWorkspaceOrder() {
    if (!workspace || !storageKey) {
      return;
    }

    var storedOrder = localStorage.getItem(storageKey);
    if (!storedOrder) {
      syncPanelButtons();
      return;
    }

    try {
      var ids = JSON.parse(storedOrder);
      ids.forEach(function(id) {
        var panel = workspace.querySelector('[data-panel-id="' + id + '"]');
        if (panel) {
          workspace.appendChild(panel);
        }
      });
    } catch (error) {
      localStorage.removeItem(storageKey);
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

      event.preventDefault();
      var afterElement = getDragAfterElement(workspace, event.clientY);
      if (!afterElement) {
        workspace.appendChild(draggedPanel);
        return;
      }
      workspace.insertBefore(draggedPanel, afterElement);
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
      localStorage.removeItem(storageKey);
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
}());