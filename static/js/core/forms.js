/*
ARQUIVO: politicas globais leves para campos mascarados.

POR QUE ELE EXISTE:
- separa normalizacao de inputs do shell visual, mantendo custo isolado.
*/

(function() {
  var maskedFields = document.querySelectorAll('input[data-mask], textarea[data-mask]');
  if (!maskedFields.length) {
    return;
  }

  function digitsOnly(value) {
    return String(value || '').replace(/\D/g, '');
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getDateYearDigits(field) {
    var parsed = Number(field.dataset.yearDigits || '4');
    return parsed === 2 ? 2 : 4;
  }

  function formatDateValueForField(value, field) {
    var yearDigits = getDateYearDigits(field);
    var maxDigits = 4 + yearDigits;
    var digits = digitsOnly(value).slice(0, maxDigits);
    if (digits.length <= 2) {
      return digits;
    }
    if (digits.length <= 4) {
      return digits.slice(0, 2) + '/' + digits.slice(2);
    }
    return digits.slice(0, 2) + '/' + digits.slice(2, 4) + '/' + digits.slice(4, maxDigits);
  }

  function normalizeDateValue(value, field) {
    var yearDigits = getDateYearDigits(field);
    var maxDigits = 4 + yearDigits;
    var digits = digitsOnly(value).slice(0, maxDigits);
    if (digits.length < maxDigits) {
      return formatDateValueForField(digits, field);
    }

    var rawDay = Number(digits.slice(0, 2));
    var rawMonth = Number(digits.slice(2, 4));
    var rawYear = Number(digits.slice(4, maxDigits));
    if (Number.isNaN(rawDay) || Number.isNaN(rawMonth) || Number.isNaN(rawYear)) {
      return formatDateValueForField(digits, field);
    }

    var month = clamp(rawMonth || 1, 1, 12);
    var fullYear = yearDigits === 2 ? 2000 + clamp(rawYear, 0, 99) : clamp(rawYear, 1900, 9999);
    var maxDay = new Date(fullYear, month, 0).getDate();
    var day = clamp(rawDay || 1, 1, maxDay);
    var yearText = yearDigits === 2 ? String(fullYear % 100).padStart(2, '0') : String(fullYear).padStart(4, '0');
    return String(day).padStart(2, '0') + '/' + String(month).padStart(2, '0') + '/' + yearText;
  }

  function formatTimeTyping(value) {
    var digits = digitsOnly(value).slice(0, 4);
    if (digits.length <= 2) {
      return digits;
    }
    if (digits.length === 3) {
      return digits.slice(0, 1) + ':' + digits.slice(1, 3);
    }
    return digits.slice(0, 2) + ':' + digits.slice(2, 4);
  }

  function normalizeTimeValue(value) {
    var rawValue = String(value || '').trim();
    if (!rawValue) {
      return rawValue;
    }

    var hourText = '';
    var minuteText = '';

    if (rawValue.indexOf(':') >= 0) {
      var parts = rawValue.split(':', 2);
      hourText = digitsOnly(parts[0]);
      minuteText = digitsOnly(parts[1]);
      if (!hourText) {
        return rawValue;
      }
      if (!minuteText) {
        minuteText = '00';
      } else if (minuteText.length === 1) {
        minuteText = minuteText + '0';
      } else {
        minuteText = minuteText.slice(0, 2);
      }
    } else {
      var digits = digitsOnly(rawValue);
      if (!digits) {
        return rawValue;
      }
      if (digits.length <= 2) {
        hourText = digits;
        minuteText = '00';
      } else if (digits.length === 3) {
        hourText = digits.slice(0, 1);
        minuteText = digits.slice(1, 3);
      } else {
        hourText = digits.slice(0, 2);
        minuteText = digits.slice(2, 4);
      }
    }

    var hour = Number(hourText);
    var minute = Number(minuteText);
    if (Number.isNaN(hour) || Number.isNaN(minute) || hour > 23 || minute > 59) {
      return rawValue;
    }

    return String(hour).padStart(2, '0') + ':' + String(minute).padStart(2, '0');
  }

  function formatCpfValue(value) {
    var digits = digitsOnly(value).slice(0, 11);
    if (digits.length <= 3) {
      return digits;
    }
    if (digits.length <= 6) {
      return digits.slice(0, 3) + '.' + digits.slice(3);
    }
    if (digits.length <= 9) {
      return digits.slice(0, 3) + '.' + digits.slice(3, 6) + '.' + digits.slice(6);
    }
    return digits.slice(0, 3) + '.' + digits.slice(3, 6) + '.' + digits.slice(6, 9) + '-' + digits.slice(9);
  }

  function normalizeCurrencyValue(value, isBlur, field) {
    var rawValue = String(value || '').replace(',', '.');
    var integerLimit = Number(field && field.dataset.currencyMaxIntegerDigits || '4');
    var decimalPlaces = Number(field && field.dataset.decimalPlaces || '2');
    var sanitized = rawValue.replace(/[^\d.]/g, '');
    var firstDotIndex = sanitized.indexOf('.');
    var hasDecimalSeparator = firstDotIndex >= 0;
    var rawInteger = hasDecimalSeparator ? sanitized.slice(0, firstDotIndex) : sanitized;
    var rawDecimal = hasDecimalSeparator ? sanitized.slice(firstDotIndex + 1).replace(/\./g, '') : '';
    var integerPart = digitsOnly(rawInteger).slice(0, integerLimit);
    var decimalPart = digitsOnly(rawDecimal).slice(0, decimalPlaces);

    var normalized = integerPart;
    if (hasDecimalSeparator) {
      normalized += '.' + decimalPart;
    }

    if (!isBlur || !normalized || normalized === '.') {
      return normalized;
    }

    var parsedValue = Number(normalized);
    if (Number.isNaN(parsedValue)) {
      return normalized;
    }

    var maxValue = Number('9'.repeat(integerLimit) + (decimalPlaces > 0 ? '.' + '9'.repeat(decimalPlaces) : ''));
    return Math.min(parsedValue, maxValue).toFixed(decimalPlaces);
  }

  maskedFields.forEach(function(field) {
    field.addEventListener('input', function() {
      if (field.dataset.mask === 'date' && field.type !== 'date') {
        field.value = formatDateValueForField(field.value, field);
        return;
      }

      if (field.dataset.mask === 'time') {
        field.value = formatTimeTyping(field.value);
        return;
      }

      if (field.dataset.mask === 'cpf') {
        field.value = formatCpfValue(field.value);
        return;
      }

      if (field.dataset.mask === 'phone') {
        field.value = digitsOnly(field.value).slice(0, 20);
        return;
      }

      if (field.dataset.mask === 'integer') {
        field.value = digitsOnly(field.value).slice(0, Number(field.dataset.maxDigits || '20'));
        return;
      }

      if (field.dataset.mask === 'currency') {
        field.value = normalizeCurrencyValue(field.value, false, field);
      }
    });

    field.addEventListener('blur', function() {
      if (field.dataset.mask === 'date' && field.type !== 'date') {
        field.value = normalizeDateValue(field.value, field);
        return;
      }

      if (field.dataset.mask === 'time') {
        field.value = normalizeTimeValue(field.value);
        return;
      }

      if (field.dataset.mask === 'currency') {
        field.value = normalizeCurrencyValue(field.value, true, field);
      }
    });
  });
}());