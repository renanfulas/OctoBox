/* Configuração e montagem de anilhas para o widget de carga. */
(function () {
  'use strict';

  /* ══ CALCULADORA DE ANILHAS (plano curva-carga-completa..., §5) ═══ */
  // So' aparece no widget quando o template ja confirmou os dois
  // metadados curados (movement_shows_plate_calculator) -- este modulo
  // so' cuida da MATEMATICA e da config local, nunca decide SE aparece.

  var PLATE_STORAGE_KEY = 'curva-plate-config';
  var DEFAULT_PLATE_SIZES = [20, 15, 10, 5, 2.5, 1.25];
  var DEFAULT_PAIRS_PER_SIZE = 4;
  var DEFAULT_BAR_KG = 20;

  function safeLocalStorage() {
    try { return window.localStorage; } catch (e) { return null; }
  }

  function defaultPairs() {
    var pairs = {};
    DEFAULT_PLATE_SIZES.forEach(function (size) { pairs[size] = DEFAULT_PAIRS_PER_SIZE; });
    return pairs;
  }

  function loadPlateConfig() {
    var ls = safeLocalStorage();
    if (!ls) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
    try {
      var raw = ls.getItem(PLATE_STORAGE_KEY);
      if (!raw) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
      return {
        barKg: isFinite(parsed.barKg) ? parsed.barKg : DEFAULT_BAR_KG,
        pairs: parsed.pairs && typeof parsed.pairs === 'object' ? parsed.pairs : defaultPairs(),
      };
    } catch (e) { return { barKg: DEFAULT_BAR_KG, pairs: defaultPairs() }; }
  }

  function savePlateConfig(config) {
    var ls = safeLocalStorage();
    if (!ls) { return; }
    try { ls.setItem(PLATE_STORAGE_KEY, JSON.stringify(config)); } catch (e) {}
  }

  // Algoritmo deterministico maior-pra-menor, respeitando pares
  // disponiveis (plano §5.3, caso 1) -- nunca assume estoque infinito.
  function computePlates(totalKg, barKg, pairs) {
    if (!isFinite(totalKg) || !isFinite(barKg)) { return { status: 'invalid' }; }
    if (totalKg < barKg - 0.01) { return { status: 'below_bar' }; }
    if (Math.abs(totalKg - barKg) < 0.01) { return { status: 'bar_only' }; }

    var perSide = Math.round(((totalKg - barKg) / 2) * 100) / 100;
    var remaining = perSide;
    var used = {};
    var sizes = Object.keys(pairs).map(Number).sort(function (a, b) { return b - a; });
    for (var i = 0; i < sizes.length; i++) {
      var size = sizes[i];
      var available = pairs[size] || 0;
      var count = 0;
      while (remaining >= size - 0.01 && count < available) {
        remaining = Math.round((remaining - size) * 100) / 100;
        count++;
      }
      if (count > 0) { used[size] = count; }
    }
    if (remaining > 0.01) { return { status: 'impossible' }; }
    return { status: 'ok', used: used, perSide: perSide };
  }

  // Caso 4 do plano: quando o alvo e' impossivel com o estoque, procura o
  // mais proximo alcancavel pra baixo/cima -- nunca arredonda escondido,
  // so' sugere.
  function findNearestAchievable(totalKg, barKg, pairs, direction) {
    var step = 0.5;
    for (var delta = step; delta <= 40; delta += step) {
      var candidate = Math.round((totalKg + direction * delta) * 100) / 100;
      if (candidate < barKg - 0.01) { break; }
      var result = computePlates(candidate, barKg, pairs);
      if (result.status === 'ok' || result.status === 'bar_only') { return candidate; }
    }
    return null;
  }

  function renderPlateInventoryRows(container, pairs, fmtNumber) {
    container.innerHTML = DEFAULT_PLATE_SIZES.map(function (size) {
      var count = pairs[size] != null ? pairs[size] : 0;
      return '<div class="workout-load-input__plate-row">' +
        '<span class="workout-load-input__mini-label">' + fmtNumber(size) + ' kg</span>' +
        '<input type="number" inputmode="numeric" step="1" min="0" class="workout-load-input__reps-field" ' +
          'data-plate-size="' + size + '" value="' + count + '" ' +
          'aria-label="Pares de ' + fmtNumber(size) + ' quilos disponíveis">' +
        '</div>';
    }).join('');
  }

  function wire(widget, hooks) {
    var fmtNumber = hooks.fmtNumber;
    var parseWeightField = hooks.parseWeightField;
    var markDirty = hooks.markDirty;
    var updateSaveLabel = hooks.updateSaveLabel;
    var scheduleDraftSave = hooks.scheduleDraftSave;
    var calc = widget.querySelector('[data-workout-plate-calculator]');
    if (!calc) { return; }
    var weightField = widget.querySelector('[data-workout-load-field]');
    var targetDisplay = calc.querySelector('[data-plate-target-display]');
    var barOptions = calc.querySelector('[data-plate-bar-options]');
    var barOtherToggle = calc.querySelector('[data-plate-bar-other-toggle]');
    var barOtherField = calc.querySelector('[data-plate-bar-other-field]');
    var inventoryContainer = calc.querySelector('[data-plate-inventory]');
    var resultEl = calc.querySelector('[data-plate-result]');
    var checkEl = calc.querySelector('[data-plate-check]');
    var useBtn = calc.querySelector('[data-plate-use-total]');
    if (!weightField || !targetDisplay || !barOptions || !inventoryContainer || !resultEl || !checkEl || !useBtn) { return; }

    var config = loadPlateConfig();
    var target = 0;

    function currentBarKg() {
      var activePill = barOptions.querySelector('.is-selected');
      if (activePill) { return parseFloat(activePill.getAttribute('data-bar-value')); }
      var other = parseFloat((barOtherField.value || '').replace(',', '.'));
      return isFinite(other) && other >= 0 ? other : config.barKg;
    }

    function currentPairs() {
      var pairs = {};
      inventoryContainer.querySelectorAll('[data-plate-size]').forEach(function (input) {
        var size = parseFloat(input.getAttribute('data-plate-size'));
        var count = parseInt(input.value, 10);
        pairs[size] = isFinite(count) && count >= 0 ? count : 0;
      });
      return pairs;
    }

    function persistConfig() {
      config = { barKg: currentBarKg(), pairs: currentPairs() };
      savePlateConfig(config);
    }

    function renderResult(result, barKg, pairs) {
      if (result.status === 'below_bar') {
        resultEl.textContent = 'O total precisa incluir a barra (' + fmtNumber(barKg) + ' kg) — ajuste a barra ou o peso alvo.';
        checkEl.textContent = '';
        useBtn.hidden = true;
        return;
      }
      if (result.status === 'bar_only') {
        resultEl.textContent = 'Somente a barra.';
        checkEl.textContent = '';
        useBtn.hidden = false;
        return;
      }
      if (result.status === 'impossible') {
        var below = findNearestAchievable(target, barKg, pairs, -1);
        var above = findNearestAchievable(target, barKg, pairs, 1);
        var alternatives = [];
        if (below !== null) { alternatives.push(fmtNumber(below) + ' kg'); }
        if (above !== null) { alternatives.push(fmtNumber(above) + ' kg'); }
        resultEl.textContent = 'Não é possível montar ' + fmtNumber(target) + ' kg com o estoque configurado.';
        checkEl.textContent = alternatives.length ? ('Mais próximo: ' + alternatives.join(' ou ') + '.') : 'Ajuste o estoque de anilhas.';
        useBtn.hidden = true;
        return;
      }
      var sizes = Object.keys(result.used).map(Number).sort(function (a, b) { return b - a; });
      var perSideParts = [];
      sizes.forEach(function (size) {
        for (var i = 0; i < result.used[size]; i++) { perSideParts.push(fmtNumber(size)); }
      });
      var totalPlatesKg = sizes.reduce(function (sum, size) { return sum + size * result.used[size] * 2; }, 0);
      resultEl.textContent = 'De cada lado: ' + perSideParts.join(' + ') + ' kg';
      checkEl.textContent = fmtNumber(barKg) + ' kg de barra + 2 × ' + fmtNumber(result.perSide) + ' kg = ' + fmtNumber(barKg + totalPlatesKg) + ' kg';
      useBtn.hidden = false;
    }

    function recompute() {
      targetDisplay.textContent = fmtNumber(target);
      var barKg = currentBarKg();
      var pairs = currentPairs();
      renderResult(computePlates(target, barKg, pairs), barKg, pairs);
    }

    renderPlateInventoryRows(inventoryContainer, config.pairs, fmtNumber);
    barOptions.querySelectorAll('[data-bar-value]').forEach(function (pill) {
      if (parseFloat(pill.getAttribute('data-bar-value')) === config.barKg) { pill.classList.add('is-selected'); }
      pill.addEventListener('click', function () {
        barOptions.querySelectorAll('[data-bar-value]').forEach(function (p) { p.classList.remove('is-selected'); });
        pill.classList.add('is-selected');
        barOtherField.value = '';
        barOtherField.hidden = true;
        persistConfig();
        recompute();
      });
    });
    if (barOtherToggle && barOtherField) {
      barOtherToggle.addEventListener('click', function () {
        barOtherField.hidden = !barOtherField.hidden;
        if (!barOtherField.hidden) {
          barOptions.querySelectorAll('[data-bar-value]').forEach(function (p) { p.classList.remove('is-selected'); });
          barOtherField.focus();
        }
      });
      barOtherField.addEventListener('input', function () { persistConfig(); recompute(); });
    }
    inventoryContainer.addEventListener('input', function () { persistConfig(); recompute(); });

    calc.querySelectorAll('[data-plate-target-step]').forEach(function (stepBtn) {
      var delta = parseFloat(stepBtn.getAttribute('data-plate-target-step'));
      stepBtn.addEventListener('click', function () {
        target = Math.max(0, Math.round((target + delta) * 100) / 100);
        recompute();
      });
    });

    useBtn.addEventListener('click', function () {
      // "Usar X kg" aplica ao RASCUNHO (marca dirty, agenda o auto-save
      // de rascunho) -- nunca salva sozinho (plano §5.2: "Nunca salva
      // automaticamente").
      weightField.value = target;
      markDirty(weightField);
      updateSaveLabel(widget);
      scheduleDraftSave(widget);
    });

    calc.addEventListener('toggle', function () {
      if (!calc.open) { return; }
      // "Abrir não altera carga" -- só semeia o alvo da calculadora com o
      // peso atual do rascunho; nada é escrito de volta até "Usar".
      var weightParsed = parseWeightField(weightField);
      target = weightParsed.ok && weightParsed.value !== null ? weightParsed.value : 0;
      recompute();
    });
  }

  window.CurvaPlateCalculator = { wire: wire, computePlates: computePlates, findNearestAchievable: findNearestAchievable };
}());
