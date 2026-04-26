(function () {
  'use strict';

  var WOD_BASE = '/aluno/wod/';

  // ── Navegação direta (1 aula no dia) ───────────────────────────
  document.querySelectorAll('[data-wod-href]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      window.location.href = btn.getAttribute('data-wod-href');
    });
    // Acessibilidade: Enter/Space
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        window.location.href = btn.getAttribute('data-wod-href');
      }
    });
  });

  // ── Bottom sheet (múltiplas aulas no dia) ──────────────────────
  var picker       = document.getElementById('studentMonthPicker');
  var pickerList   = document.getElementById('studentMonthPickerList');
  var pickerClose  = document.getElementById('studentMonthPickerClose');
  var pickerBackdrop = document.getElementById('studentMonthPickerBackdrop');

  if (!picker) return;

  function openPicker(btn) {
    var dataEl = btn.querySelector('.student-month-day__sessions-data');
    if (!dataEl) return;

    pickerList.innerHTML = '';

    dataEl.querySelectorAll('[data-session-id]').forEach(function (s) {
      var a = document.createElement('a');
      a.href = WOD_BASE + '?session_id=' + s.dataset.sessionId;
      a.className = 'student-month-picker__item';

      var timeSpan = document.createElement('span');
      timeSpan.className = 'student-month-picker__item-time';
      timeSpan.textContent = s.dataset.sessionTime;

      var titleSpan = document.createElement('span');
      titleSpan.className = 'student-month-picker__item-title';
      titleSpan.textContent = s.dataset.sessionTitle;

      var statusSpan = document.createElement('span');
      statusSpan.className = 'student-month-picker__item-status';
      statusSpan.textContent = s.dataset.sessionRuntimeStatus || s.dataset.sessionStatus;

      a.appendChild(timeSpan);
      a.appendChild(titleSpan);
      a.appendChild(statusSpan);
      pickerList.appendChild(a);
    });

    picker.hidden = false;
    document.body.style.overflow = 'hidden';

    // Foca o primeiro item para acessibilidade
    var firstItem = pickerList.querySelector('a');
    if (firstItem) firstItem.focus();
  }

  function closePicker() {
    picker.hidden = true;
    document.body.style.overflow = '';
  }

  document.querySelectorAll('[data-day-picker]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      openPicker(btn);
    });
  });

  pickerClose.addEventListener('click', closePicker);
  pickerBackdrop.addEventListener('click', closePicker);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !picker.hidden) closePicker();
  });
})();
