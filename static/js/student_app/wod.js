(function () {
  function parseNumber(value) {
    var normalized = String(value || '').replace(',', '.');
    var parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function snapPercentValue(input) {
    if (!input) {
      return;
    }
    var value = parseNumber(input.value);
    var clamped = Math.max(40, Math.min(100, value || 40));
    var snapped = Math.round(clamped / 5) * 5;
    input.value = String(Math.max(40, Math.min(100, snapped)));
  }

  var percentInput = document.querySelector('[data-ui="student-wod-percent"]');
  if (!percentInput) {
    return;
  }

  percentInput.addEventListener('change', function () {
    snapPercentValue(percentInput);
  });

  percentInput.addEventListener('blur', function () {
    snapPercentValue(percentInput);
  });
}());
