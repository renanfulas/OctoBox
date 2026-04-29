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
    field.dataset.mask = 'date';
    field.dataset.yearDigits = '2';
    if (window.OctoForms && typeof window.OctoForms.applyMaskedFields === 'function') {
      window.OctoForms.applyMaskedFields(field.parentNode || document);
    }

    var pickerId = field.dataset.pickerTarget || '';
    var picker = pickerId ? document.getElementById(pickerId) : null;
    var button = field.parentNode ? field.parentNode.querySelector('[data-smart-date-button]') : null;

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
      field.value = pad(parts[2]) + '/' + pad(parts[1]);
      field.dispatchEvent(new Event('input', { bubbles: true }));
      field.dispatchEvent(new Event('blur', { bubbles: true }));
    }

    function syncPickerFromText() {
      if (!picker) return;
      var normalized = String(field.value || '').replace(/\D/g, '');
      if (normalized.length < 4) return;
      var day = normalized.slice(0, 2);
      var month = normalized.slice(2, 4);
      var year = resolveClosestPickerYear(day, month);
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
      field.addEventListener('blur', syncPickerFromText);
    }

    if (button && picker) {
      button.addEventListener('click', function () {
        if (typeof picker.showPicker === 'function') {
          picker.showPicker();
        } else {
          picker.click();
          picker.focus();
        }
      });
    }
  }

  root.querySelectorAll('[data-smart-date-input]').forEach(bindSmartDateField);
})();
