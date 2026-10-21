const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// sw.js é template Django: os laços viram linhas soltas e as variáveis, texto fixo.
const template = fs.readFileSync(path.join(__dirname, '../../templates/public_workouts/sw.js'), 'utf8');
const source = template
  .replace(/{%[^%]*%}/g, '')
  .replace(/{{\s*offline_url\s*}}/g, '/renan/offline/')
  .replace(/{{\s*app_scope\s*}}/g, '/renan/')
  .replace(/{{\s*slug\s*}}/g, 'bruno')
  .replace(/{{\s*asset_url\s*}}/g, '/static/app.js')
  .replace(/{{[^}]*}}/g, '1');

function worker(clients = []) {
  const listeners = {};
  const shown = [];
  const opened = [];
  const self = {
    location: { origin: 'https://app.test' },
    addEventListener: (name, handler) => { listeners[name] = handler; },
    skipWaiting() {},
    registration: { showNotification: (title, options) => { shown.push({ title, options }); return Promise.resolve(); } },
    clients: {
      claim() {},
      matchAll: () => Promise.resolve(clients),
      openWindow: (url) => { opened.push(url); return Promise.resolve(); },
    },
  };
  vm.runInNewContext(source, { self, URL, caches: {}, fetch() {}, Promise });
  async function dispatch(name, event) {
    const pending = [];
    listeners[name]({ ...event, waitUntil: (promise) => pending.push(promise) });
    await Promise.all(pending);
  }
  return { dispatch, shown, opened };
}

function client(url) {
  const calls = [];
  return {
    url, calls,
    focus() { calls.push('focus'); return Promise.resolve(this); },
    navigate(target) { calls.push('navigate:' + target); return Promise.resolve(this); },
  };
}

function pushEvent(payload) {
  return { data: { json: () => payload } };
}

test('push do descanso: tag fixa da sessão, renotify e vibração, com o tipo guardado para o toque', async () => {
  const sw = worker();
  await sw.dispatch('push', pushEvent({
    title: 'Descanso acabou', body: 'Supino reto, série 3', url: '/renan/bruno#treino-guiado',
    tag: 'curva-rest-abc', kind: 'rest', renotify: true, vibrate: [180, 90, 180],
  }));
  assert.equal(sw.shown.length, 1);
  const { title, options } = sw.shown[0];
  assert.equal(title, 'Descanso acabou');
  assert.equal(options.body, 'Supino reto, série 3');
  assert.equal(options.tag, 'curva-rest-abc');
  assert.equal(options.renotify, true);
  assert.deepEqual(Array.from(options.vibrate), [180, 90, 180]);
  assert.deepEqual({ ...options.data }, { url: '/renan/bruno#treino-guiado', kind: 'rest' });
});

test('outros avisos seguem sem renotify nem vibração própria', async () => {
  const sw = worker();
  await sw.dispatch('push', pushEvent({ title: 'Treino concluído', body: 'ok', url: '/renan/bruno', tag: 'workout-1' }));
  const { options } = sw.shown[0];
  assert.equal('renotify' in options, false);
  assert.equal('vibrate' in options, false);
});

test('tocar no aviso do descanso traz o app aberto para a frente sem recarregar o treino', async () => {
  const open = client('https://app.test/renan/bruno');
  const sw = worker([open]);
  await sw.dispatch('notificationclick', {
    notification: { close() {}, data: { url: '/renan/bruno#treino-guiado', kind: 'rest' } },
  });
  assert.deepEqual(open.calls, ['focus']);
  assert.deepEqual(sw.opened, []);
});

test('com o app fechado, o toque abre direto no modo foco', async () => {
  const sw = worker([]);
  await sw.dispatch('notificationclick', {
    notification: { close() {}, data: { url: '/renan/bruno#treino-guiado', kind: 'rest' } },
  });
  assert.deepEqual(sw.opened, ['https://app.test/renan/bruno#treino-guiado']);
});

test('aviso que não é do descanso continua navegando para a página do aviso', async () => {
  const open = client('https://app.test/renan/bruno');
  const sw = worker([open]);
  await sw.dispatch('notificationclick', {
    notification: { close() {}, data: { url: '/renan/bruno', kind: '' } },
  });
  assert.deepEqual(open.calls, ['navigate:https://app.test/renan/bruno', 'focus']);
});
