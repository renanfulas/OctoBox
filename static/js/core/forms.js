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

  function getDateYearDigits(field) {
    var parsed = Number(field.dataset.yearDigits || '4');
    return parsed === 2 ? 2 : 4;
  }

  function parseOptionalNumber(value) {
    if (value === undefined || value === null || value === '') {
      return null;
    }
    var parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
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

  function parseDateCandidate(value, field) {
    var yearDigits = getDateYearDigits(field);
    var maxDigits = 4 + yearDigits;
    var digits = digitsOnly(value).slice(0, maxDigits);
    if (!digits.length) {
      return { status: 'empty' };
    }
    if (digits.length < maxDigits) {
      return { status: 'incomplete' };
    }

    var day = Number(digits.slice(0, 2));
    var month = Number(digits.slice(2, 4));
    var rawYear = Number(digits.slice(4, maxDigits));
    if (Number.isNaN(day) || Number.isNaN(month) || Number.isNaN(rawYear)) {
      return { status: 'invalid' };
    }

    var fullYear = yearDigits === 2 ? 2000 + rawYear : rawYear;
    var minYear = parseOptionalNumber(field.dataset.minYear);
    var maxYear = parseOptionalNumber(field.dataset.maxYear);
    if ((minYear !== null && fullYear < minYear) || (maxYear !== null && fullYear > maxYear)) {
      return { status: 'range' };
    }

    var candidate = new Date(fullYear, month - 1, day);
    if (
      candidate.getFullYear() !== fullYear ||
      candidate.getMonth() !== month - 1 ||
      candidate.getDate() !== day
    ) {
      return { status: 'invalid' };
    }

    var yearText = yearDigits === 2 ? String(fullYear % 100).padStart(2, '0') : String(fullYear).padStart(4, '0');
    return {
      status: 'valid',
      value: String(day).padStart(2, '0') + '/' + String(month).padStart(2, '0') + '/' + yearText,
    };
  }

  function normalizeDateValue(value, field) {
    var parsed = parseDateCandidate(value, field);
    if (parsed.status === 'valid') {
      return parsed.value;
    }
    return formatDateValueForField(value, field);
  }

  function validateDateField(field, shouldValidateIncomplete) {
    var parsed = parseDateCandidate(field.value, field);
    var message = '';
    if (parsed.status === 'incomplete' && shouldValidateIncomplete) {
      message = field.dataset.dateIncompleteMessage || 'Use a data no formato dd/mm/aaaa.';
    } else if (parsed.status === 'invalid') {
      message = field.dataset.dateInvalidMessage || 'Informe uma data valida.';
    } else if (parsed.status === 'range') {
      message = field.dataset.dateRangeMessage || 'O ano precisa estar dentro do intervalo permitido.';
    }

    field.setCustomValidity(message);
    if (message) {
      field.setAttribute('aria-invalid', 'true');
    } else {
      field.removeAttribute('aria-invalid');
    }
    return !message;
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
        validateDateField(field, false);
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
        validateDateField(field, true);
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
