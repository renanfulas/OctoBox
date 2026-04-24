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
    return value.toFixed(1).replace('.', ',') + ' kg';
  }

  function bindCalculator(calculator) {
    var base = calculator.querySelector('[data-ui="student-rm-base"]');
    var percent = calculator.querySelector('[data-ui="student-rm-percent"]');
    var result = calculator.querySelector('[data-ui="student-rm-result"]');
    if (!base || !percent || !result) {
      return;
    }
    function render() {
      result.textContent = formatKg(parseNumber(base.value) * parseNumber(percent.value) / 100);
    }
    base.addEventListener('input', render);
    percent.addEventListener('input', render);
    render();
  }

  document.querySelectorAll('[data-ui="student-rm-calculator"]').forEach(bindCalculator);
}());
