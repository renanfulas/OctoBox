const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/app-open.js'), 'utf8');
const MIN = 60000;

function load({ snapshot, accountScope = '990', hidden = false }) {
  const submitted = [];
  const listeners = {};
  const clock = { now: Date.UTC(2026, 10, 10, 19) };
  const dataset = { planSlug: 'bruno', accountScope };
  if (snapshot) dataset.offlineSnapshot = String(snapshot);
  const document = {
    hidden, body: { dataset },
    addEventListener(type, fn) { listeners[type] = fn; },
  };
  const window = {
    CurvaOfflineData: { submit(options) { submitted.push(options); return Promise.resolve({ state: 'queued' }); } },
  };
  vm.runInNewContext(source, { window, document, Date: { now: () => clock.now } });
  function setHidden(value) { document.hidden = value; listeners.visibilitychange(); }
  return { submitted, clock, setHidden, window };
}

test('página viva: o servidor já contou a abertura, o app não manda nada', () => {
  const { submitted } = load({});
  assert.deepEqual(submitted, []);
});

test('cópia offline: enfileira a abertura com o horário do aparelho', () => {
  const { submitted, clock } = load({ snapshot: 1 });
  assert.equal(submitted.length, 1);
  assert.equal(submitted[0].kind, 'open');
  assert.equal(submitted[0].url, '/renan/bruno/abertura');
  assert.equal(submitted[0].payload.opened_at, clock.now);
  assert.equal(submitted[0].key, 'open:' + clock.now);
});

test('voltar ao app depois de 30 min fora conta como abertura; voltar logo, não', () => {
  const { submitted, clock, setHidden } = load({});
  setHidden(true);
  clock.now += 10 * MIN;
  setHidden(false);
  assert.equal(submitted.length, 0);
  setHidden(true);
  clock.now += 30 * MIN;
  setHidden(false);
  assert.equal(submitted.length, 1);
  assert.equal(submitted[0].payload.opened_at, clock.now);
});

test('sem conta autenticada fica inerte', () => {
  const { submitted, window } = load({ snapshot: 1, accountScope: '' });
  assert.deepEqual(submitted, []);
  assert.equal(window.CurvaAppOpen, undefined);
});
