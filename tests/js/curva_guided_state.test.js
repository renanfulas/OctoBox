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

const day = [
  { label: 'Supino', series: [{ required: true }, { required: true }] },
  { label: 'Remada', series: [{ required: true }, { required: true }] },
  { label: 'Elevação', series: [{ required: true }, { required: false }] },
  { label: 'Livre', series: [{ role: 'legacy_unknown', required: false }] },
];

test('cursor de foco troca a série atual sem marcar nada como pulado', () => {
  const projected = state.project(day, new Set(['0:1']), new Set(), 0, null, null, { focusIndex: 2 });
  assert.equal(projected.next.movementIndex, 0);
  assert.equal(projected.current.movementIndex, 2);
  assert.equal(projected.current.setNumber, 1);
  assert.equal(projected.upNext.movementIndex, 2);
  assert.equal(projected.upNext.setNumber, 2);
  assert.equal(projected.overview[0].status, 'started');
  assert.equal(projected.overview[1].status, 'pending');
  assert.equal(projected.overview[1].skipped, 0);
});

test('depois do exercício focado, "a seguir" volta para a primeira pendente', () => {
  const recorded = new Set(['0:1', '2:1']);
  const projected = state.project(day, recorded, new Set(), 0, null, null, { focusIndex: 2 });
  assert.equal(projected.current.movementIndex, 2);
  assert.equal(projected.current.setNumber, 2);
  assert.equal(projected.upNext.movementIndex, 0);
  assert.equal(projected.upNext.setNumber, 2);
});

test('foco em exercício sem pendência cai na ordem natural', () => {
  const recorded = new Set(['0:1', '0:2']);
  const projected = state.project(day, recorded, new Set(), 0, null, null, { focusIndex: 0 });
  assert.equal(projected.current.movementIndex, 1);
  assert.equal(projected.overview[0].status, 'done');
});

test('concluído pede as obrigatórias; opcional pendente não impede o risco', () => {
  const projected = state.project(day, new Set(['2:1']), new Set(), 0, null, null);
  assert.equal(projected.overview[2].status, 'done');
  assert.equal(projected.overview[2].firstPending.setNumber, 2);
});

test('exercício só pulado não fica concluído; parcial com pulo fica incompleto', () => {
  const projected = state.project(day, new Set(['1:1']), new Set(['0:1', '0:2', '1:2']), 0, null, null);
  assert.equal(projected.overview[0].status, 'skipped');
  assert.equal(projected.overview[1].status, 'incomplete');
  assert.equal(projected.overview[1].skipped, 1);
  assert.equal(projected.missing, 4);
});

test('série livre conta como concluída com uma série feita', () => {
  const projected = state.project(day, new Set(['3:1']), new Set(), 0, null, null);
  assert.equal(projected.overview[3].status, 'done');
  assert.equal(projected.overview[3].firstPending, null);
});

test('série livre admite extras até o limite atual', () => {
  const freeform = [{ label: 'Livre', series: Array(29).fill({ required: false }) }];
  assert.equal(state.project(freeform, new Set(), new Set(), 0, null, 0).canAddExtra, true);
  freeform[0].series.push({ required: false });
  assert.equal(state.project(freeform, new Set(), new Set(), 0, null, 0).canAddExtra, false);
});
