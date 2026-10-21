const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/load-plate-calculator.js'),
  'utf8',
);
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const calculator = sandbox.window.CurvaPlateCalculator;

test('monta o peso sem ultrapassar os pares disponíveis', () => {
  const result = calculator.computePlates(100, 20, { 20: 2 });
  assert.equal(result.status, 'ok');
  assert.equal(result.used[20], 2);
  assert.equal(calculator.computePlates(100, 20, { 20: 1 }).status, 'impossible');
});

test('distingue barra isolada e alvo abaixo da barra', () => {
  assert.equal(calculator.computePlates(20, 20, {}).status, 'bar_only');
  assert.equal(calculator.computePlates(15, 20, {}).status, 'below_bar');
});

test('sugere pesos alcançáveis sem alterar a meta original', () => {
  const pairs = { 20: 1, 10: 1, 5: 1, 2.5: 1 };
  assert.equal(calculator.computePlates(82.5, 20, pairs).status, 'impossible');
  assert.equal(calculator.findNearestAchievable(82.5, 20, pairs, -1), 80);
  assert.equal(calculator.findNearestAchievable(82.5, 20, pairs, 1), 85);
});
