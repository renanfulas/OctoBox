const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/offline-data.js'), 'utf8');
const DAY = 86400000;

// IndexedDB mínimo: um pedido por volta do laço; a transação conclui depois.
function fakeIndexedDB() {
  const databases = new Map();
  return {
    databases,
    rows(name, store) {
      const data = databases.get(name);
      return data && data.stores.get(store) ? data.stores.get(store) : new Map();
    },
    open(name, version) {
      const request = {};
      setImmediate(() => {
        if (!databases.has(name)) databases.set(name, { version: 0, stores: new Map(), keyPaths: new Map() });
        const data = databases.get(name);
        const db = {
          objectStoreNames: { contains: (store) => data.stores.has(store) },
          createObjectStore: (store, options) => { data.stores.set(store, new Map()); data.keyPaths.set(store, options.keyPath); },
          close() {},
          transaction(storeName) {
            const rows = data.stores.get(storeName);
            const keyPath = data.keyPaths.get(storeName);
            const tx = {};
            const op = (fn) => ({ result: fn() });
            tx.objectStore = () => ({
              get: (key) => op(() => (rows.has(key) ? structuredClone(rows.get(key)) : undefined)),
              getAll: () => op(() => Array.from(rows.values(), (row) => structuredClone(row))),
              put: (value) => op(() => { rows.set(value[keyPath], structuredClone(value)); }),
              delete: (key) => op(() => { rows.delete(key); }),
              clear: () => op(() => { rows.clear(); }),
            });
            setImmediate(() => tx.oncomplete());
            return tx;
          },
        };
        request.result = db;
        if (data.version < version) {
          data.version = version;
          request.onupgradeneeded();
        }
        request.onsuccess();
      });
      return request;
    },
  };
}

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300, status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(body === undefined ? '' : JSON.stringify(body)),
  };
}

function load({ accountScope = '990', onLine = true, fetch, now = Date.UTC(2026, 10, 10, 12) } = {}) {
  const idb = fakeIndexedDB();
  const sent = [];
  const events = [];
  const windowListeners = {};
  const state = { now, fetch };
  const document = {
    body: { dataset: { accountScope } },
    cookie: 'csrftoken=tok',
    hidden: false,
    dispatchEvent(event) { events.push(event); },
    addEventListener() {},
  };
  const window = {
    indexedDB: idb,
    crypto: { randomUUID: () => 'uuid-' + (sent.length + events.length) },
    addEventListener(type, fn) { windowListeners[type] = fn; },
    fetch(url, options) {
      sent.push({ url, options });
      return state.fetch(url, options);
    },
  };
  class CustomEvent { constructor(type, init) { this.type = type; this.detail = init && init.detail; } }
  const navigator = { onLine };
  vm.runInNewContext(source, {
    window, document, navigator, CustomEvent, Promise, JSON, setImmediate,
    Date: { now: () => state.now }, Object, Array, Math,
  });
  const db = 'curva-offline-data:' + accountScope;
  return {
    api: window.CurvaOfflineData, idb, sent, events, state, navigator, windowListeners,
    reads: () => idb.rows(db, 'reads'), writes: () => idb.rows(db, 'writes'),
  };
}

const plain = (value) => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let i = 0; i < 20; i += 1) await new Promise(setImmediate); };
const URL_NUTRITION = '/renan/bruno/nutricao.json';

test('leitura online devolve a rede e guarda a cópia da conta', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(200, { meal_plan: { meals: [] } })) });
  const result = await view.api.readJson(URL_NUTRITION);
  assert.deepEqual(plain(result), { data: { meal_plan: { meals: [] } }, savedAt: null });
  await flush();
  assert.equal(view.reads().get(URL_NUTRITION).saved_at, view.state.now);
  // Partição por conta: o banco carrega a conta no nome.
  assert.ok(view.idb.databases.has('curva-offline-data:990'));
});

test('sem rede ou com 5xx a leitura devolve a cópia e diz de quando é', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(200, { meal_plan: 'v1' })) });
  await view.api.readJson(URL_NUTRITION);
  await flush();
  const savedAt = view.state.now;
  view.state.now += DAY;
  view.state.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
  assert.deepEqual(plain(await view.api.readJson(URL_NUTRITION)), { data: { meal_plan: 'v1' }, savedAt });
  view.state.fetch = () => Promise.resolve(jsonResponse(502));
  assert.deepEqual(plain(await view.api.readJson(URL_NUTRITION)), { data: { meal_plan: 'v1' }, savedAt });
});

test('cópia com mais de 30 dias não é usada', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(200, { meal_plan: 'v1' })) });
  await view.api.readJson(URL_NUTRITION);
  await flush();
  view.state.now += 31 * DAY;
  view.state.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
  await assert.rejects(view.api.readJson(URL_NUTRITION), /Failed to fetch/);
});

test('404/401 do servidor apagam a cópia daquela leitura', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(200, { meal_plan: 'v1' })) });
  await view.api.readJson(URL_NUTRITION);
  await flush();
  view.state.fetch = () => Promise.resolve(jsonResponse(404));
  await assert.rejects(view.api.readJson(URL_NUTRITION), /http-404/);
  assert.equal(view.reads().has(URL_NUTRITION), false);
});

test('escrita online: grava antes, envia com a idempotency_key e sai da fila', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(200, { id: 7 })) });
  await flush();
  const result = await view.api.submit({ kind: 'assessment', url: '/renan/bruno/avaliacoes', payload: { weight_kg: 80 } });
  assert.equal(result.state, 'sent');
  assert.equal(result.kind, 'assessment');
  const post = view.sent.find((item) => item.options && item.options.method === 'POST');
  assert.deepEqual(JSON.parse(post.options.body), { weight_kg: 80, idempotency_key: result.key });
  assert.equal(post.options.headers['X-CSRFToken'], 'tok');
  assert.equal(view.writes().size, 0);
  // Gravou e removeu: o selo de pendências repinta nas duas pontas.
  assert.equal(view.events.filter((event) => event.type === 'curva:outbox-changed').length, 2);
});

test('sem rede a escrita fica no aparelho e a drenagem envia a MESMA chave', async () => {
  const view = load({ fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  await flush();
  const queued = await view.api.submit({ kind: 'assessment', url: '/renan/bruno/avaliacoes', payload: { weight_kg: 80 } });
  assert.equal(queued.state, 'queued');
  assert.equal(view.writes().size, 1);
  assert.equal(await view.api.pending('assessment'), 1);
  view.state.fetch = () => Promise.resolve(jsonResponse(200, { id: 7 }));
  await view.windowListeners.online();
  assert.equal(view.writes().size, 0);
  const posts = view.sent.filter((item) => item.options && item.options.method === 'POST');
  assert.equal(posts.length, 2);
  assert.equal(JSON.parse(posts[0].options.body).idempotency_key, JSON.parse(posts[1].options.body).idempotency_key);
  const settled = view.events.filter((event) => event.type === 'curva:offline-write-settled');
  assert.equal(settled.length, 1);
  assert.equal(settled[0].detail.state, 'sent');
  assert.equal(settled[0].detail.kind, 'assessment');
});

test('401 mantém na fila (sobe depois do login); 400 é recusa definitiva', async () => {
  const view = load({ fetch: () => Promise.resolve(jsonResponse(401, { error: 'login necessario' })) });
  await flush();
  const expired = await view.api.submit({ kind: 'assessment', url: '/renan/bruno/avaliacoes', payload: {} });
  assert.equal(expired.state, 'queued');
  assert.equal(expired.status, 401);
  assert.equal(view.writes().size, 1);
  view.state.fetch = () => Promise.resolve(jsonResponse(400, { error: 'measured_at e obrigatorio' }));
  const rejected = await view.api.submit({ kind: 'assessment', url: '/renan/bruno/avaliacoes', payload: {} });
  assert.equal(rejected.state, 'rejected');
  assert.equal(rejected.data.error, 'measured_at e obrigatorio');
  assert.equal(view.writes().size, 1, 'só a recusada saiu');
});

test('drenagem segue a ordem e para no primeiro que continua sem rede', async () => {
  const view = load({ fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  await flush();
  await view.api.submit({ kind: 'assessment', key: 'a', url: '/renan/bruno/avaliacoes', payload: { n: 1 } });
  view.state.now += 1;
  await view.api.submit({ kind: 'assessment', key: 'b', url: '/renan/bruno/avaliacoes', payload: { n: 2 } });
  const before = view.sent.length;
  await view.api.drain();
  assert.equal(view.sent.length - before, 1, 'não insiste no segundo com a rede fora');
  let calls = 0;
  view.state.fetch = (url, options) => { calls += 1; return Promise.resolve(jsonResponse(200, JSON.parse(options.body))); };
  await view.api.drain();
  assert.equal(calls, 2);
  const order = view.sent.slice(-2).map((item) => JSON.parse(item.options.body).idempotency_key);
  assert.deepEqual(order, ['a', 'b']);
});

test('sem conta autenticada não há fila: falha de rede vira "failed"', async () => {
  const view = load({ accountScope: '', fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  const result = await view.api.submit({ kind: 'assessment', url: '/renan/bruno/avaliacoes', payload: {} });
  assert.equal(result.state, 'failed');
  assert.equal(view.idb.databases.size, 0);
});
