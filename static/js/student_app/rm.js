(function () {
  function sanitizeThreeDigitDecimal(input) {
    if (!input) {
      return;
    }
    var raw = String(input.value || '').replace(',', '.');
    var parts = raw.split('.');
    var integerPart = parts[0].replace(/\D/g, '').slice(0, 3);
    var decimalPart = parts.length > 1 ? parts.slice(1).join('').replace(/\D/g, '').slice(0, 1) : '';
    var normalized = integerPart;
    if (parts.length > 1 && decimalPart) {
      normalized += '.' + decimalPart;
    }
    input.value = normalized;
  }

  function snapStepValue(input, minValue, maxValue, stepValue) {
    if (!input) {
      return;
    }
    var current = parseNumber(input.value);
    var clamped = Math.max(minValue, Math.min(maxValue, current || minValue));
    var snapped = Math.round(clamped / stepValue) * stepValue;
    input.value = String(Math.max(minValue, Math.min(maxValue, snapped)));
  }

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
    if (!base.value) {
      base.value = '0';
    }
    sanitizeThreeDigitDecimal(base);
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
    base.addEventListener('input', function () {
      sanitizeThreeDigitDecimal(base);
      render();
    });
    base.addEventListener('blur', function () {
      sanitizeThreeDigitDecimal(base);
      render();
    });
    percent.addEventListener('input', render);
    percent.addEventListener('change', function () {
      snapStepValue(percent, 40, 100, 5);
      render();
    });
    percent.addEventListener('blur', function () {
      snapStepValue(percent, 40, 100, 5);
      render();
    });
    render();
  }

  document.querySelectorAll('[data-max-integer-digits="3"]').forEach(function (input) {
    input.addEventListener('input', function () {
      sanitizeThreeDigitDecimal(input);
    });
    input.addEventListener('blur', function () {
      sanitizeThreeDigitDecimal(input);
    });
  });

  document.querySelectorAll('[data-ui="student-rm-calculator"]').forEach(bindCalculator);
}());
