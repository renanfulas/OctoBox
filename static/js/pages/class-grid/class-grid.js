/*
ARQUIVO: comportamento da pagina de grade de aulas.

POR QUE ELE EXISTE:
- retira do template a logica interativa pesada da grade.
- concentra validacao e modais da grade num modulo de pagina.
*/

(function() {
  var plannerForm = document.querySelector('form[data-class-grid-planner]');
  var plannerStartDateField = document.getElementById('id_start_date');
  var plannerEndDateField = document.getElementById('id_end_date');
  var plannerStartTimeField = document.getElementById('id_start_time');
  var plannerDurationField = document.getElementById('id_duration_minutes');
  var plannerCapacityField = document.getElementById('id_capacity');
  var sequenceCountField = document.getElementById('id_sequence_count');
  var sequenceCountLiveCopy = document.getElementById('sequence-count-live-copy');
  var dialog = document.getElementById('class-monthly-modal');
  var closeButton = document.getElementById('close-monthly-calendar');

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

  if (dialog && dialog.showModal) {
    document.querySelectorAll('[data-action="open-monthly-calendar"]').forEach(function(trigger) {
      trigger.addEventListener('click', function(event) {
        event.preventDefault();
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
  }

  var weeklyDialog = document.getElementById('class-weekly-modal');
  var weeklyCloseButton = document.getElementById('close-weekly-modal');
  var weeklyFullView = document.getElementById('weekly-modal-full-view');
  var weeklyDayView = document.getElementById('weekly-modal-day-view');
  var weeklyModalTitle = document.getElementById('class-weekly-modal-title');
  var weeklyDayGrid = weeklyDayView ? weeklyDayView.querySelector('[data-slot="class-grid-weekly-modal-day-grid"]') : null;

  function setElementHidden(element, shouldHide) {
    if (!element) {
      return;
    }

    element.hidden = shouldHide;
  }

  function setWeeklyModalMode(mode) {
    var isDayMode = mode === 'day';

    setElementHidden(weeklyFullView, isDayMode);
    setElementHidden(weeklyDayView, !isDayMode);
  }

  function resetWeeklyModalDayView() {
    if (!weeklyDayGrid) {
      return;
    }

    weeklyDayGrid.replaceChildren();
  }

  function openWeeklyModal(mode, dayCard) {
    if (!weeklyDialog || !weeklyDialog.showModal) {
      return;
    }

    if (mode === 'day' && dayCard) {
      setWeeklyModalMode('day');
      resetWeeklyModalDayView();
      if (weeklyDayGrid) {
        var clone = dayCard.cloneNode(true);
        clone.classList.add('is-modal-clone');
        clone.classList.remove('is-interactive');
        clone.removeAttribute('role');
        clone.removeAttribute('tabindex');
        weeklyDayGrid.appendChild(clone);
      }
      var dayLabel = dayCard.querySelector('.eyebrow');
      var dayDate = dayCard.querySelector('strong');
      if (weeklyModalTitle) {
        weeklyModalTitle.textContent = (dayLabel ? dayLabel.textContent : '') + ' ' + (dayDate ? dayDate.textContent : '');
      }
    } else {
      setWeeklyModalMode('full');
      resetWeeklyModalDayView();
      if (weeklyModalTitle) {
        weeklyModalTitle.textContent = 'Grade Semanal';
      }
    }

    weeklyDialog.showModal();
  }

  document.querySelectorAll('[data-action="open-weekly-modal-full"]').forEach(function(trigger) {
    trigger.addEventListener('click', function(event) {
      if (event.target.closest('a, button') && event.target !== trigger) {
        return;
      }
      event.preventDefault();
      openWeeklyModal('full');
    });

    if (trigger.getAttribute('role') === 'button') {
      trigger.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openWeeklyModal('full');
        }
      });
    }
  });

  document.querySelectorAll('#weekly-board [data-day-date]').forEach(function(card) {
    card.addEventListener('click', function(event) {
      if (event.target.closest('a, button, form')) {
        return;
      }
      openWeeklyModal('day', card);
    });
    card.addEventListener('keydown', function(event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openWeeklyModal('day', card);
      }
    });
  });

  if (weeklyCloseButton) {
    weeklyCloseButton.addEventListener('click', function() {
      setWeeklyModalMode('full');
      resetWeeklyModalDayView();
      weeklyDialog.close();
    });
  }

  if (weeklyDialog) {
    weeklyDialog.addEventListener('click', function(event) {
      var overflowToggle = event.target.closest('[data-action="toggle-weekly-day-overflow"]');
      if (overflowToggle) {
        var overflowNote = overflowToggle.closest('.weekly-day-overflow-note');
        var overflowList = overflowNote ? overflowNote.nextElementSibling : null;
        var isExpanded = overflowToggle.getAttribute('aria-expanded') === 'true';

        if (overflowList && overflowList.classList.contains('weekly-day-overflow-list')) {
          overflowList.hidden = isExpanded;
          overflowToggle.setAttribute('aria-expanded', isExpanded ? 'false' : 'true');
          overflowToggle.textContent = isExpanded ? 'Ver mais' : 'Ver menos';
        }

        event.preventDefault();
        return;
      }
    });

    weeklyDialog.addEventListener('click', function(event) {
      var panel = weeklyDialog.querySelector('.class-monthly-modal-panel');
      if (panel && !panel.contains(event.target)) {
        setWeeklyModalMode('full');
        resetWeeklyModalDayView();
        weeklyDialog.close();
      }
    });
    weeklyDialog.addEventListener('close', function() {
      setWeeklyModalMode('full');
      resetWeeklyModalDayView();
      if (weeklyModalTitle) {
        weeklyModalTitle.textContent = 'Grade Semanal';
      }
    });
  }
}());
