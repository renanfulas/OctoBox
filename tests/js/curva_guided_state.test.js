const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/guided-state.js'), 'utf8',
);
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const state = sandbox.window.CurvaGuidedState;
const movements = [{ label: 'Supino', series: [
  { role: 'feeder', required: false }, { role: 'top_set', required: true },
] }];

test('guia começa pela primeira série e só conclui após a obrigatória', () => {
  const initial = state.project(movements, new Set(), new Set(), 0, null, null);
  assert.equal(initial.next.setNumber, 1);
  assert.equal(initial.total, 2);
  assert.equal(initial.canFinish, false);

  const feederSkipped = state.project(movements, new Set(), new Set(['0:1']), 0, '0:1', null);
  assert.equal(feederSkipped.next.setNumber, 2);
  assert.equal(feederSkipped.canUndoSkip, true);
  assert.equal(feederSkipped.canFinish, false);

  const done = state.project(movements, new Set(['0:2']), new Set(['0:1']), 1, '0:1', null);
  assert.equal(done.next, null);
  assert.equal(done.canFinish, true);
  assert.equal(done.pendingCount, 1);
});

test('série obrigatória pulada permanece impedindo conclusão', () => {
  const projected = state.project(movements, new Set(['0:1']), new Set(['0:2']), 0, '0:2', null);
  assert.equal(projected.next, null);
  assert.equal(projected.requiredMissing, true);
  assert.equal(projected.canFinish, false);
});

test('série livre admite extras até o limite atual', () => {
  const freeform = [{ label: 'Livre', series: Array(29).fill({ required: false }) }];
  assert.equal(state.project(freeform, new Set(), new Set(), 0, null, 0).canAddExtra, true);
  freeform[0].series.push({ required: false });
  assert.equal(state.project(freeform, new Set(), new Set(), 0, null, 0).canAddExtra, false);
});
