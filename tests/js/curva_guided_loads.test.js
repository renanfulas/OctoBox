const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/guided-loads.js'), 'utf8',
);
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const loads = sandbox.window.CurvaGuidedLoads;

test('aceita kg decimal e rejeita carga inválida', () => {
  assert.equal(loads.parseTarget('82,5'), 82.5);
  assert.equal(loads.parseTarget(''), null);
  assert.equal(loads.parseTarget('0'), null);
  assert.equal(loads.parseTarget('10.999'), null);
  assert.equal(loads.parseTarget('Infinity'), null);
});

test('alvo da Top sugere Prep e Feeder, preserva carga fixa e permite limpar', () => {
  const movement = { series: [
    { top_factor: .4, rounding_step_kg: 2.5, base_weight_kg: null, weight_kg: null },
    { top_factor: .7, rounding_step_kg: 2.5, base_weight_kg: null, weight_kg: null },
    { top_factor: 1, rounding_step_kg: 2.5, base_weight_kg: null, weight_kg: null },
    { top_factor: null, rounding_step_kg: 2.5, base_weight_kg: 20, weight_kg: 20 },
  ] };
  loads.applyTopTarget(movement, 100);
  assert.deepEqual(movement.series.map((row) => row.weight_kg), [40, 70, 100, 20]);
  loads.applyTopTarget(movement, null);
  assert.deepEqual(movement.series.map((row) => row.weight_kg), [null, null, null, 20]);
});

test('arredondamento por passo acompanha o Python nos empates', () => {
  const movement = { series: [
    { top_factor: .5, rounding_step_kg: 2.5, base_weight_kg: null },
    { top_factor: .3, rounding_step_kg: 2.5, base_weight_kg: null },
  ] };
  loads.applyTopTarget(movement, 2.5);
  assert.equal(movement.series[0].weight_kg, 0);
  assert.equal(movement.series[1].weight_kg, 0);
});
