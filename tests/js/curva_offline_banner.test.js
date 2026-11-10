const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '../../static/js/public_workouts/offline-banner.js'), 'utf8',
);

function load({ snapshot, onLine }) {
  const copy = { textContent: '' };
  const reload = { hidden: true, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; } };
  const banner = {
    hidden: true, dataset: {},
    querySelector: (selector) => ({
      '[data-offline-banner-copy]': copy,
      '[data-offline-banner-reload]': reload,
    })[selector],
  };
  const windowListeners = {};
  const reloads = [];
  const navigator = { onLine };
  const window = {
    addEventListener(type, fn) { windowListeners[type] = fn; },
    location: { reload: () => reloads.push(true) },
  };
  const document = {
    body: { dataset: snapshot ? { offlineSnapshot: String(snapshot) } : {} },
    querySelector: (selector) => (selector === '[data-offline-banner]' ? banner : null),
  };
  vm.runInNewContext(source, { window, document, navigator, Date });
  return { banner, copy, reload, navigator, windowListeners, reloads };
}

test('página viva e online: faixa escondida', () => {
  const { banner } = load({ onLine: true });
  assert.equal(banner.hidden, true);
});

test('página viva perde a conexão: avisa e some quando ela volta', () => {
  const view = load({ onLine: true });
  view.navigator.onLine = false;
  view.windowListeners.offline();
  assert.equal(view.banner.hidden, false);
  assert.match(view.copy.textContent, /^Sem conexão\./);
  assert.equal(view.reload.hidden, true);
  view.navigator.onLine = true;
  view.windowListeners.online();
  assert.equal(view.banner.hidden, true);
});

test('cópia salva aberta sem rede mostra a data da cópia', () => {
  const savedAt = new Date(2026, 10, 8, 19, 42).getTime();
  const { banner, copy, reload } = load({ snapshot: savedAt, onLine: false });
  assert.equal(banner.hidden, false);
  assert.equal(banner.dataset.state, 'offline');
  assert.match(copy.textContent, /^Modo offline · treino salvo em 08\/11 às 19:42\./);
  assert.equal(reload.hidden, true);
});

test('cópia salva com a rede de volta oferece atualizar, sem recarregar sozinha', () => {
  const view = load({ snapshot: Date.now(), onLine: false });
  view.navigator.onLine = true;
  view.windowListeners.online();
  assert.equal(view.banner.hidden, false);
  assert.equal(view.banner.dataset.state, 'reconnected');
  assert.equal(view.reload.hidden, false);
  assert.deepEqual(view.reloads, []);
  view.reload.listeners.click();
  assert.deepEqual(view.reloads, [true]);
});
