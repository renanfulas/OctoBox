(function () {
  function parseNumber(value) {
    var normalized = String(value || '').replace(',', '.');
    var parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatKg(value) {
    if (!Number.isFinite(value) || value <= 0) {
      return '-- kg';
    }
    var rounded = Math.round(value * 2) / 2;
    if (rounded < 0.5) {
      return '-- kg';
    }
    return rounded.toFixed(1).replace('.0', '').replace('.', ',') + ' kg';
  }

  function bindCalculator(calculator) {
    var base = calculator.querySelector('[data-ui="student-rm-base"]');
    var percent = calculator.querySelector('[data-ui="student-rm-percent"]');
    var result = calculator.querySelector('[data-ui="student-rm-result"]');
    var feedback = calculator.querySelector('[data-ui="student-rm-feedback"]');
    if (!base || !percent || !result) {
      return;
    }
    function render() {
      var baseValue = parseNumber(base.value);
      var percentValue = parseNumber(percent.value);
      var loadValue = baseValue * percentValue / 100;
      var isInvalid = baseValue <= 0 || percentValue <= 0 || loadValue < 0.5;
      result.textContent = isInvalid ? '-- kg' : formatKg(loadValue);
      if (feedback) {
        feedback.hidden = !isInvalid;
      }
    }
    base.addEventListener('input', render);
    percent.addEventListener('change', render);
    render();
  }

  document.querySelectorAll('[data-ui="student-rm-calculator"]').forEach(bindCalculator);
}());
