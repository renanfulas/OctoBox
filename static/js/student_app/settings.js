(function () {
  function sanitizeThreeDigitInteger(input) {
    if (!input) {
      return;
    }
    var digits = String(input.value || '').replace(/\D/g, '').slice(0, 3);
    input.value = digits;
  }

  var daysInput = document.querySelector('input[name="days"][data-max-integer-digits="3"]');
  if (!daysInput) {
    return;
  }

  daysInput.addEventListener('input', function () {
    sanitizeThreeDigitInteger(daysInput);
  });

  daysInput.addEventListener('blur', function () {
    sanitizeThreeDigitInteger(daysInput);
  });

  document.querySelectorAll('[data-freeze-days]').forEach(function (button) {
    button.addEventListener('click', function () {
      daysInput.value = button.getAttribute('data-freeze-days') || '';
      daysInput.focus();
    });
  });
}());
