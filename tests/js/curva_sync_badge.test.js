const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/sync-badge.js'), 'utf8',
);

const NOW = Date.UTC(2026, 10, 10, 12);
const HOUR = 3600000;

// IndexedDB mínimo para o selo: open SEM versão, getAll por store.
// `stores` é mutável pelo teste: { [dbName]: { [storeName]: rows[] } }.
function fakeIndexedDB(stores) {
  const opened = [];
  return {
    opened,
    factory: {
      open(name) {
        opened.push(name);
        const request = {};
        setImmediate(() => {
          const db = stores[name] || {};
          request.result = {
            objectStoreNames: { contains: (store) => store in db },
            transaction(store) {
              return {
                objectStore() {
                  const reader = {};
                  setImmediate(() => {
                    reader.result = db[store];
                    reader.onsuccess();
                  });
                  return { getAll: () => reader };
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

function element() {
  const attributes = {};
  const listeners = {};
  return {
    hidden: true, textContent: '', children: [], attributes, listeners,
    setAttribute(name, value) { attributes[name] = value; },
    addEventListener(type, fn) { listeners[type] = fn; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
  };
}

function load(options) {
  const stores = options.stores || {};
  const idb = fakeIndexedDB(stores);
  const badge = element();
  const panel = element();
  const documentListeners = {};
  const windowListeners = {};
  const document = {
    body: { dataset: { planSlug: options.slug, accountScope: options.accountScope } },
    hidden: false,
    querySelector: (selector) => ({ '[data-sync-badge]': badge, '[data-sync-panel]': panel })[selector] || null,
    createElement: () => ({ textContent: '', className: '' }),
    addEventListener(type, fn) { documentListeners[type] = fn; },
    dispatchEvent(event) { if (documentListeners[event.type]) documentListeners[event.type](event); },
  };
  const navigator = { onLine: options.onLine !== false };
  const window = {
    indexedDB: idb.factory,
    addEventListener(type, fn) { windowListeners[type] = fn; },
    CurvaGuidedOutbox: options.outbox,
    CurvaOfflineData: options.offlineData,
  };
  vm.runInNewContext(source, {
    window, document, navigator, setTimeout, Promise, Math, Date: { now: () => NOW },
  });
  return { window, document, navigator, badge, panel, idb, stores, windowListeners };
}

const GUIDED = 'curva-guided:990:bruno';
const LOADS = 'public-workout-outbox:account:990';
const rows = (n, at = NOW) => Array.from({ length: n }, (_, i) => ({ key: 'k' + i, created_at: at, queued_at: at }));
const panelText = (panel) => panel.children.map((child) => child.textContent);

test('sem conta autenticada o selo fica inerte', () => {
  const { window, badge } = load({ slug: 'bruno', accountScope: '', stores: {} });
  assert.equal(window.CurvaSyncBadge, undefined);
  assert.equal(badge.hidden, true);
});

test('filas vazias escondem o selo e o painel', async () => {
  const { window, badge, panel, idb } = load({
    slug: 'bruno', accountScope: '990',
    stores: { [GUIDED]: { commands: [] }, [LOADS]: { 'pending-loads': [] } },
  });
  assert.equal(await window.CurvaSyncBadge.refresh(), 0);
  assert.equal(badge.hidden, true);
  assert.equal(panel.hidden, true);
  assert.ok(idb.opened.includes(GUIDED));
  assert.ok(idb.opened.includes(LOADS));
});

test('soma as três filas e mostra o total', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990',
    stores: { [GUIDED]: { commands: rows(2) }, [LOADS]: { 'pending-loads': rows(1) } },
    offlineData: { list: () => Promise.resolve([{ key: 'a', kind: 'assessment', created_at: NOW }]) },
  });
  assert.equal(await window.CurvaSyncBadge.refresh(), 4);
  assert.equal(badge.hidden, false);
  assert.equal(badge.textContent, '4 registros a enviar');
});

test('aberturas do app na fila não contam como registro a enviar', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990',
    stores: { [GUIDED]: { commands: rows(1) } },
    offlineData: { list: () => Promise.resolve([
      { key: 'open:1', kind: 'open', created_at: NOW - 48 * HOUR },
      { key: 'a', kind: 'assessment', created_at: NOW },
    ]) },
  });
  assert.equal(await window.CurvaSyncBadge.refresh(), 2);
  assert.equal(badge.textContent, '2 registros a enviar');
});

test('singular e aviso de desconexão', async () => {
  const { window, badge } = load({
    slug: 'bruno', accountScope: '990', onLine: false,
    stores: { [GUIDED]: { commands: rows(1) } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '1 registro a enviar · sem conexão');
});

test('com o guiado na página, lê pela conexão dele sem abrir o banco de novo', async () => {
  const asked = [];
  const { window, badge, idb } = load({
    slug: 'bruno', accountScope: '990',
    outbox: { list: (scope) => { asked.push(scope); return Promise.resolve(rows(2)); } },
    stores: { [LOADS]: { 'pending-loads': rows(1) } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '3 registros a enviar');
  assert.ok(asked.includes('990:bruno'));
  assert.ok(!idb.opened.includes(GUIDED));
});

test('painel: contagem por fila e idade do mais antigo', async () => {
  const { window, panel } = load({
    slug: 'bruno', accountScope: '990',
    stores: { [GUIDED]: { commands: rows(3, NOW - 2 * HOUR) }, [LOADS]: { 'pending-loads': rows(1, NOW - HOUR) } },
    offlineData: { list: () => Promise.resolve([
      { key: 'a', kind: 'assessment', created_at: NOW - 26 * HOUR },
      { key: 'onboarding', kind: 'onboarding', created_at: NOW },
    ]) },
  });
  await window.CurvaSyncBadge.refresh();
  assert.deepEqual(panelText(panel), [
    'Treino guiado: 3 registros',
    'Cargas: 1 registro',
    'Avaliações: 1 avaliação',
    'Tutorial concluído, aguardando envio',
    'Mais antigo: há 1 dia',
    'Enviando assim que o servidor responder.',
  ]);
});

test('registro recusado pelo servidor pede revisão no selo e no painel', async () => {
  const { window, badge, panel } = load({
    slug: 'bruno', accountScope: '990', onLine: false,
    stores: {
      [GUIDED]: { commands: [{ key: 'g', created_at: NOW, blocked: true }] },
      [LOADS]: { 'pending-loads': [{ idempotency_key: 'l', queued_at: NOW, sync_state: 'blocked' }] },
    },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '2 registros a enviar · revisar');
  const warnings = panel.children.filter((child) => child.className === 'is-warning').map((child) => child.textContent);
  assert.deepEqual(warnings, [
    'Treino guiado: o servidor recusou 1 registro. Abra o treino guiado para revisar.',
    'Cargas: 1 registro precisa de revisão na aba Cargas.',
  ]);
  assert.match(panelText(panel).at(-1), /^Sem conexão\./);
});

test('tocar no selo abre e fecha o painel', async () => {
  const { window, badge, panel } = load({
    slug: 'bruno', accountScope: '990', stores: { [GUIDED]: { commands: rows(1) } },
  });
  await window.CurvaSyncBadge.refresh();
  badge.listeners.click();
  assert.equal(panel.hidden, false);
  assert.equal(badge.attributes['aria-expanded'], 'true');
  badge.listeners.click();
  assert.equal(panel.hidden, true);
  assert.equal(badge.attributes['aria-expanded'], 'false');
});

test('banco sem o store (conta nova) conta zero sem quebrar', async () => {
  const { window, badge } = load({ slug: 'bruno', accountScope: '990', stores: { [GUIDED]: {} } });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, true);
});

test('curva:outbox-changed repinta o selo (com debounce)', async () => {
  const { window, document, badge, stores } = load({
    slug: 'bruno', accountScope: '990', stores: { [GUIDED]: { commands: [] } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.hidden, true);
  stores[GUIDED].commands = rows(2);
  document.dispatchEvent({ type: 'curva:outbox-changed' });
  document.dispatchEvent({ type: 'curva:outbox-changed' });
  await new Promise((resolve) => setTimeout(resolve, 260));
  assert.equal(badge.hidden, false);
  assert.equal(badge.textContent, '2 registros a enviar');
});

test('voltar a ficar online agenda a repintura', async () => {
  const { window, badge, stores, windowListeners } = load({
    slug: 'bruno', accountScope: '990', onLine: false, stores: { [GUIDED]: { commands: rows(1) } },
  });
  await window.CurvaSyncBadge.refresh();
  assert.equal(badge.textContent, '1 registro a enviar · sem conexão');
  stores[GUIDED].commands = [];
  windowListeners.online();
  await new Promise((resolve) => setTimeout(resolve, 260));
  assert.equal(badge.hidden, true);
});
