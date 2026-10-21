(function () {
  'use strict';

  function parseTarget(value) {
    var text = String(value == null ? '' : value).trim().replace(',', '.');
    if (!/^\d+(?:\.\d{1,2})?$/.test(text)) return null;
    var number = Number(text);
    return Number.isFinite(number) && number > 0 && number <= 9999.99 ? number : null;
  }

  function roundToStep(value, step) {
    var quotient = value / step;
    var lower = Math.floor(quotient);
    var fraction = quotient - lower;
    var nearest = fraction > .5 + 1e-9 || (Math.abs(fraction - .5) <= 1e-9 && lower % 2)
      ? lower + 1 : lower;
    return Math.round(nearest * step * 100) / 100;
  }

  function applyTopTarget(movement, target) {
    movement.topTargetKg = target;
    movement.series.forEach(function (row) {
      if (row.top_factor == null) return;
      var step = Number(row.rounding_step_kg) || 2.5;
      row.weight_kg = target == null ? row.base_weight_kg
        : roundToStep(target * Number(row.top_factor), step);
    });
  }

  window.CurvaGuidedLoads = {
    parseTarget: parseTarget,
    applyTopTarget: applyTopTarget,
  };
}());
