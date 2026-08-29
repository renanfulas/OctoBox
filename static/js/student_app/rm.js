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
    var percentLabel = calculator.querySelector('[data-ui="student-rm-percent-label"]');
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
      if (percentLabel) {
        percentLabel.textContent = percentValue > 0 ? String(Math.round(percentValue)) : '--';
      }
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

    var chips = calculator.querySelectorAll('[data-rm-percent-chip]');
    function syncChips() {
      chips.forEach(function (chip) {
        chip.classList.toggle('is-active', chip.dataset.rmPercentChip === String(parseNumber(percent.value)));
      });
    }
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        percent.value = chip.dataset.rmPercentChip;
        render();
        syncChips();
      });
    });
    percent.addEventListener('input', syncChips);
    syncChips();
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

  var COMBINING_MARKS_PATTERN = new RegExp('[' + String.fromCharCode(0x0300) + '-' + String.fromCharCode(0x036f) + ']', 'g');

  function normalizeMovementText(value) {
    var normalized = String(value || '').normalize('NFKD').replace(COMBINING_MARKS_PATTERN, '');
    normalized = normalized.toLowerCase().replace(/[^a-z0-9\s]/g, ' ');
    return normalized.replace(/\s+/g, ' ').trim();
  }

  // Mesma ordem de prioridade do resolve_movement_slug (operations/services/wod_paste_parser.py):
  // alias exato (o mais longo em empate) primeiro, depois alias parcial (whole-word).
  function resolveMovementSlug(normalizedText, dictionary) {
    if (!normalizedText) {
      return null;
    }
    var exactMatch = null;
    var partialMatch = null;
    var padded = ' ' + normalizedText + ' ';
    dictionary.forEach(function (entry) {
      (entry.aliases || []).forEach(function (alias) {
        if (!alias) {
          return;
        }
        if (normalizedText === alias) {
          if (!exactMatch || alias.length > exactMatch.alias.length) {
            exactMatch = { slug: entry.slug, alias: alias };
          }
          return;
        }
        var endsWithAlias = normalizedText.slice(-(alias.length + 1)) === ' ' + alias;
        var startsWithAlias = normalizedText.slice(0, alias.length + 1) === alias + ' ';
        var containsAlias = padded.indexOf(' ' + alias + ' ') !== -1;
        if (endsWithAlias || startsWithAlias || containsAlias) {
          if (!partialMatch || alias.length > partialMatch.alias.length) {
            partialMatch = { slug: entry.slug, alias: alias };
          }
        }
      });
    });
    if (exactMatch) {
      return exactMatch.slug;
    }
    if (partialMatch) {
      return partialMatch.slug;
    }
    return null;
  }

  function findSuggestions(normalizedText, dictionary, limit) {
    if (normalizedText.length < 2) {
      return [];
    }
    var seenSlugs = {};
    var startsWith = [];
    var includes = [];
    dictionary.forEach(function (entry) {
      if (seenSlugs[entry.slug]) {
        return;
      }
      var bestAlias = null;
      (entry.aliases || []).forEach(function (alias) {
        if (!alias) {
          return;
        }
        if (alias.indexOf(normalizedText) === 0 && (!bestAlias || alias.length < bestAlias.length)) {
          bestAlias = alias;
        } else if (!bestAlias && alias.indexOf(normalizedText) !== -1) {
          bestAlias = alias;
        }
      });
      if (!bestAlias) {
        return;
      }
      seenSlugs[entry.slug] = true;
      (bestAlias.indexOf(normalizedText) === 0 ? startsWith : includes).push(entry);
    });
    return startsWith.concat(includes).slice(0, limit);
  }

  function readJsonScript(elementId) {
    var node = document.getElementById(elementId);
    if (!node) {
      return null;
    }
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return null;
    }
  }

  function formatKgPlain(value) {
    var rounded = Math.round(value * 2) / 2;
    return String(rounded).replace('.', ',');
  }

  function bindMovementAutocomplete(field) {
    var input = field.querySelector('[data-ui="student-rm-movement-input"]');
    var suggestList = field.querySelector('[data-ui="student-rm-suggest"]');
    var form = field.closest('form');
    var warning = form ? form.querySelector('[data-ui="student-rm-duplicate-warning"]') : null;
    if (!input || !suggestList) {
      return;
    }
    var dictionary = readJsonScript('rm-movement-dictionary') || [];
    var existingRecords = readJsonScript('rm-existing-records') || {};
    var activeIndex = -1;
    var currentOptions = [];

    function hideSuggestions() {
      suggestList.hidden = true;
      suggestList.innerHTML = '';
      activeIndex = -1;
      currentOptions = [];
      input.removeAttribute('aria-activedescendant');
      input.setAttribute('aria-expanded', 'false');
    }

    function renderSuggestions(options) {
      currentOptions = options;
      activeIndex = -1;
      if (!options.length) {
        hideSuggestions();
        return;
      }
      suggestList.innerHTML = '';
      options.forEach(function (entry, index) {
        var item = document.createElement('li');
        item.className = 'student-rm-suggest__item';
        item.id = 'rm-suggest-option-' + index;
        item.setAttribute('role', 'option');
        item.textContent = entry.label;
        item.addEventListener('mousedown', function (event) {
          event.preventDefault();
          selectSuggestion(entry);
        });
        suggestList.appendChild(item);
      });
      suggestList.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function setActiveOption(index) {
      var items = suggestList.querySelectorAll('.student-rm-suggest__item');
      items.forEach(function (item) {
        item.classList.remove('is-active');
      });
      if (index >= 0 && items[index]) {
        items[index].classList.add('is-active');
        input.setAttribute('aria-activedescendant', items[index].id);
        activeIndex = index;
      } else {
        input.removeAttribute('aria-activedescendant');
        activeIndex = -1;
      }
    }

    function selectSuggestion(entry) {
      input.value = entry.label;
      hideSuggestions();
      updateDuplicateWarning();
      input.focus();
    }

    function updateDuplicateWarning() {
      if (!warning) {
        return;
      }
      var normalized = normalizeMovementText(input.value);
      var slug = resolveMovementSlug(normalized, dictionary);
      var existing = slug ? existingRecords[slug] : null;
      if (existing) {
        warning.textContent = 'Voce ja tem RM de ' + existing.label + ': ' + formatKgPlain(existing.kg) + ' kg. Salvar vai atualizar esse valor.';
        warning.hidden = false;
      } else {
        warning.hidden = true;
        warning.textContent = '';
      }
    }

    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-autocomplete', 'list');

    input.addEventListener('input', function () {
      var normalized = normalizeMovementText(input.value);
      renderSuggestions(findSuggestions(normalized, dictionary, 6));
      updateDuplicateWarning();
    });

    input.addEventListener('blur', function () {
      window.setTimeout(hideSuggestions, 120);
    });

    input.addEventListener('keydown', function (event) {
      if (suggestList.hidden || !currentOptions.length) {
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveOption(Math.min(activeIndex + 1, currentOptions.length - 1));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveOption(Math.max(activeIndex - 1, 0));
      } else if (event.key === 'Enter') {
        if (activeIndex >= 0) {
          event.preventDefault();
          selectSuggestion(currentOptions[activeIndex]);
        }
      } else if (event.key === 'Escape') {
        hideSuggestions();
      }
    });

    updateDuplicateWarning();
  }

  document.querySelectorAll('[data-ui="student-rm-movement-field"]').forEach(bindMovementAutocomplete);
}());
