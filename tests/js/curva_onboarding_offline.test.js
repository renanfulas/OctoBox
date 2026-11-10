const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/onboarding.js'), 'utf8');

function node() {
  const listeners = {};
  return {
    hidden: true, textContent: '', children: [], listeners,
    addEventListener(type, fn) { listeners[type] = fn; },
    setAttribute() {}, removeAttribute() {}, focus() {},
    appendChild(child) { this.children.push(child); },
  };
}

function load({ offlineData, autostart = 'true' }) {
  const root = node();
  const steps = [node(), node()];
  const dots = node();
  const buttons = { next: node(), back: node(), skip: node() };
  root.getAttribute = (name) => ({
    'data-onboarding-autostart': autostart, 'data-onboarding-complete-url': '/renan/bruno/onboarding',
  })[name];
  root.querySelectorAll = (selector) => (selector === '[data-onboarding-step]' ? steps : []);
  root.querySelector = (selector) => ({
    '[data-onboarding-dots]': dots, '.onboarding-wizard__card': node(),
    '[data-onboarding-next]': buttons.next, '[data-onboarding-back]': buttons.back,
    '[data-onboarding-skip]': buttons.skip,
  })[selector] || null;
  Object.defineProperty(dots, 'children', { get() { return this._kids || (this._kids = []); } });
  dots.appendChild = function (child) { this.children.push(child); };
  const submitted = [];
  const document = {
    cookie: '', activeElement: null, body: { style: {} },
    querySelector: (selector) => (selector === '[data-onboarding-wizard]' ? root : null),
    querySelectorAll: () => [],
    createElement: () => node(),
    addEventListener() {},
  };
  const window = {
    setTimeout: (fn) => fn(),
    fetch: () => Promise.resolve({}),
    CurvaOfflineData: offlineData && Object.assign({
      submit: (options) => { submitted.push(options); return Promise.resolve({ state: 'queued' }); },
    }, offlineData),
  };
  vm.runInNewContext(source, { window, document, Promise });
  return { root, buttons, submitted };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test('tutorial ainda não visto abre sozinho', async () => {
  const { root } = load({ offlineData: { pending: () => Promise.resolve(0) } });
  await flush();
  assert.equal(root.hidden, false);
});

test('marca de "concluído" na fila do aparelho: a cópia offline não reabre o tutorial', async () => {
  const { root, buttons, submitted } = load({ offlineData: { pending: () => Promise.resolve(1) } });
  await flush();
  assert.equal(root.hidden, true);
  // E não enfileira a marca de novo se o aluno reabrir e fechar.
  buttons.skip.listeners.click();
  assert.deepEqual(submitted, []);
});

test('fechar o tutorial manda a marca pela fila offline com chave fixa', async () => {
  const { buttons, submitted } = load({ offlineData: { pending: () => Promise.resolve(0) } });
  await flush();
  buttons.skip.listeners.click();
  assert.equal(submitted.length, 1);
  assert.equal(submitted[0].kind, 'onboarding');
  assert.equal(submitted[0].key, 'onboarding');
  assert.equal(submitted[0].url, '/renan/bruno/onboarding');
});
