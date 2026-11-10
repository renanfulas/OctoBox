const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/sync-badge.js'), 'utf8',
);

// IndexedDB mínimo para o selo: open SEM versão, contagem por store.
// `counts` é mutável pelo teste: { [dbName]: { [storeName]: n } }.
function fakeIndexedDB(counts) {
  const opened = [];
  return {
    opened,
    factory: {
      open(name) {
        opened.push(name);
        const request = {};
        setImmediate(() => {
          const stores = counts[name] || {};
          request.result = {
            objectStoreNames: { contains: (store) => store in stores },
            transaction(store) {
              return {
                objectStore() {
                  const counter = {};
                  setImmediate(() => {
                    counter.result = stores[store];
                    counter.onsuccess();
                  });
                  return { count: () => counter };
                },
              };
            },
            close() {},
          };
          request.onsuccess();
        });
        return request;
      },
    },
  };
}

function load(options) {
  const counts = options.counts || {};
  const idb = fakeIndexedDB(counts);
  const badge = { hidden: true, textContent: '' };
  const documentListeners = {};
  const windowListeners = {};
  const document = {
    body: { dataset: { planSlug: options.slug, accountScope: options.accountScope } },
    hidden: false,
    querySelector: (selector) => (selector === '[data-sync-badge]' ? badge : null),
    addEventListener(type, fn) { documentListeners[type] = fn; },
    dispatchEvent(event) { if (documentListeners[event.type]) documentListeners[event.type](event); },
  };
  const navigator = { onLine: options.onLine !== false };
  const window = {
    indexedDB: idb.factory,
    addEventListener(type, fn) { windowListeners[type] = fn; },
    CurvaGuidedOutbox: options.outbox,
  };
  class CustomEvent { constructor(type) { this.type = type; } }
  vm.runInNewContext(source, { window, document, navigator, setTimeout, CustomEvent });
  return { window, document, navigator, badge, idb, counts, windowListeners };
}

test('sem conta autenticada o selo fica inerte', () => {
  const { window, badge } = load({ slug: 'bruno', accountScope: '', counts: {} });
  assert.equal(window.CurvaSyncBadge, undefined);
  assert.equal(badge.hidden, true);
});

test('fila vazia esconde o selo', async () => {
  const { window, badge, idb } = load({
    slug: 'bruno', accountScope: '990',
    counts: {
      'curva-guided:990:bruno': { commands: 0 },
      'public-workout-outbox:account:990': { 'pending-loads': 0 },
    },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, true);
  assert.equal(badge.textContent, '');
  // Lê os DOIS bancos: a fila do guiado e a outbox de cargas.
  assert.ok(idb.opened.includes('curva-guided:990:bruno'));
  assert.ok(idb.opened.includes('public-workout-outbox:account:990'));
});

test('soma guiado + cargas e mostra o total', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990',
    counts: {
      'curva-guided:990:bruno': { commands: 2 },
      'public-workout-outbox:account:990': { 'pending-loads': 1 },
    },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, false);
  assert.equal(badge.textContent, '3 registros a enviar');
});

test('singular e aviso de desconexão', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990', onLine: false,
    counts: { 'curva-guided:990:bruno': { commands: 1 } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '1 registro a enviar · sem conexão');
});

test('com o guiado na página, conta pela conexão dele sem abrir o banco de novo', async () => {
  const asked = [];
  const { window, badge, idb } = load({
    slug: 'bruno', accountScope: '990',
    outbox: { count: (scope) => { asked.push(scope); return Promise.resolve(2); } },
    counts: { 'public-workout-outbox:account:990': { 'pending-loads': 1 } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '3 registros a enviar');
  assert.ok(asked.includes('990:bruno'));
  assert.ok(!idb.opened.includes('curva-guided:990:bruno'));
});

test('banco sem o store (conta nova) conta zero sem quebrar', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990',
    counts: { 'curva-guided:990:bruno': {} },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, true);
});

test('curva:outbox-changed repinta o selo (com debounce)', async () => {
  const { window, document, badge, counts } = load({
    slug: 'bruno', accountScope: '990',
    counts: { 'curva-guided:990:bruno': { commands: 0 } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, true);
  counts['curva-guided:990:bruno'].commands = 2;
  document.dispatchEvent({ type: 'curva:outbox-changed' });
  document.dispatchEvent({ type: 'curva:outbox-changed' });
  await new Promise((resolve) => setTimeout(resolve, 260));
  assert.equal(badge.hidden, false);
  assert.equal(badge.textContent, '2 registros a enviar');
});

test('voltar a ficar online agenda a repintura', async () => {
  const { window, badge, counts, windowListeners } = load({
    slug: 'bruno', accountScope: '990', onLine: false,
    counts: { 'curva-guided:990:bruno': { commands: 1 } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '1 registro a enviar · sem conexão');
  assert.equal(typeof windowListeners.online, 'function');
  counts['curva-guided:990:bruno'].commands = 0;
  windowListeners.online();
  await new Promise((resolve) => setTimeout(resolve, 260));
  assert.equal(badge.hidden, true);
});
