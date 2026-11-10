const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// F1 offline-first: a página do dono vai para o IndexedDB (nunca Cache
// Storage) e volta sem rede. sw.js é template Django: laços somem e as
// variáveis viram texto fixo, como em curva_service_worker_push.test.js.
const template = fs.readFileSync(path.join(__dirname, '../../templates/public_workouts/sw.js'), 'utf8');
const source = template
  .replace(/{%[^%]*%}/g, '')
  .replace(/{{\s*offline_url\s*}}/g, '/renan/offline/')
  .replace(/{{\s*app_scope\s*}}/g, '/renan/')
  .replace(/{{\s*slug\s*}}/g, 'bruno')
  .replace(/{{\s*asset_url\s*}}/g, '/static/app.js')
  .replace(/{{[^}]*}}/g, '1');

const PAGE_HTML = '<!DOCTYPE html><html><head></head><body data-plan-slug="bruno" data-account-scope="990"><main>Treino do Bruno</main></body></html>';
const DAY = 86400000;

function fakeIndexedDB() {
  const databases = new Map();
  return {
    rows(name) {
      const data = databases.get(name);
      return data && data.stores.get('pages') ? data.stores.get('pages') : new Map();
    },
    open(name, version) {
      const request = {};
      setImmediate(() => {
        if (!databases.has(name)) databases.set(name, { version: 0, stores: new Map() });
        const data = databases.get(name);
        const db = {
          objectStoreNames: { contains: (store) => data.stores.has(store) },
          createObjectStore: (store) => { data.stores.set(store, new Map()); },
          close() {},
          transaction(storeName) {
            const rows = data.stores.get(storeName);
            const tx = {};
            const op = (fn) => ({ result: fn() });
            tx.objectStore = () => ({
              get: (key) => op(() => (rows.has(key) ? structuredClone(rows.get(key)) : undefined)),
              put: (value) => op(() => { rows.set(value.slug, structuredClone(value)); }),
              delete: (key) => op(() => { rows.delete(key); }),
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

class FakeResponse {
  constructor(body, init = {}) {
    this.body = body;
    this.status = init.status === undefined ? 200 : init.status;
    this.type = init.type || 'basic';
    this.ok = this.status >= 200 && this.status < 300;
    this.init = init;
    const headers = {};
    Object.entries(init.headers || {}).forEach(([name, value]) => { headers[name.toLowerCase()] = value; });
    this.headers = { get: (name) => (name.toLowerCase() in headers ? headers[name.toLowerCase()] : null) };
  }
  clone() { return new FakeResponse(this.body, this.init); }
  text() { return Promise.resolve(this.body); }
}

function worker(options = {}) {
  const listeners = {};
  const idb = fakeIndexedDB();
  const timers = [];
  const state = { now: options.now || Date.UTC(2026, 10, 10, 12) };
  const offlinePage = new FakeResponse('OFFLINE');
  const context = {
    self: {
      location: { origin: 'https://app.test' },
      addEventListener: (name, handler) => { listeners[name] = handler; },
      skipWaiting() {},
      clients: { claim() {} },
    },
    URL, Promise,
    Date: { now: () => state.now },
    indexedDB: idb,
    Response: FakeResponse,
    caches: { match: () => Promise.resolve(offlinePage), open: () => Promise.resolve({}) },
    fetch: (request) => options.fetch(request),
    setTimeout: (fn, delay) => { timers.push({ fn, delay }); return timers.length; },
  };
  vm.runInNewContext(source, context);

  function navigate(url, method = 'GET') {
    const pending = [];
    let responded = null;
    listeners.fetch({
      request: { url: 'https://app.test' + url, method, mode: 'navigate' },
      respondWith: (promise) => { responded = promise; },
      waitUntil: (promise) => { pending.push(promise); },
    });
    return { responded, settled: () => Promise.all(pending) };
  }

  async function seed(record) {
    const request = idb.open('curva-offline-pages', 1);
    await new Promise((resolve) => {
      request.onupgradeneeded = () => request.result.createObjectStore('pages', { keyPath: 'slug' });
      request.onsuccess = resolve;
    });
    const tx = request.result.transaction('pages');
    tx.objectStore('pages').put(record);
    await new Promise((resolve) => { tx.oncomplete = resolve; });
  }

  return { navigate, seed, idb, timers, state, offlinePage };
}

function ownerPage() {
  return new FakeResponse(PAGE_HTML, { headers: { 'X-Curva-Offline-Scope': '990', 'Content-Type': 'text/html' } });
}

const pages = (sw) => sw.idb.rows('curva-offline-pages');

test('visita online do dono devolve a rede e guarda a página no IndexedDB', async () => {
  const fresh = ownerPage();
  const sw = worker({ fetch: () => Promise.resolve(fresh) });
  const visit = sw.navigate('/renan/bruno?source=pwa');
  assert.equal(await visit.responded, fresh);
  await visit.settled();
  const record = pages(sw).get('bruno');
  assert.equal(record.scope, '990');
  assert.equal(record.html, PAGE_HTML);
  assert.equal(record.saved_at, sw.state.now);
});

test('sem rede, a página salva abre marcada como cópia', async () => {
  const sw = worker({ fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now - DAY });
  const response = await sw.navigate('/renan/bruno').responded;
  const html = await response.text();
  assert.match(html, new RegExp(`<body data-offline-snapshot="${sw.state.now - DAY}" data-plan-slug="bruno"`));
  assert.match(html, /Treino do Bruno/);
  assert.equal(response.headers.get('Content-Type'), 'text/html; charset=utf-8');
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
});

test('sem rede e sem cópia cai na página offline de emergência', async () => {
  const sw = worker({ fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  assert.equal(await sw.navigate('/renan/bruno').responded, sw.offlinePage);
});

test('cópia com mais de 30 dias expira e é apagada', async () => {
  const sw = worker({ fetch: () => Promise.reject(new TypeError('Failed to fetch')) });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now - 31 * DAY });
  assert.equal(await sw.navigate('/renan/bruno').responded, sw.offlinePage);
  assert.equal(pages(sw).has('bruno'), false);
});

test('servidor sem a marca (pagamento bloqueado, sem login) apaga a cópia', async () => {
  const blocked = new FakeResponse('<html><body>Pagamento pendente</body></html>', { headers: { 'Content-Type': 'text/html' } });
  const sw = worker({ fetch: () => Promise.resolve(blocked) });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now });
  const visit = sw.navigate('/renan/bruno');
  assert.equal(await visit.responded, blocked);
  await visit.settled();
  assert.equal(pages(sw).has('bruno'), false);
});

test('redirecionamento para o login e 404 de posse apagam a cópia', async () => {
  for (const response of [new FakeResponse('', { status: 0, type: 'opaqueredirect' }), new FakeResponse('', { status: 404 })]) {
    const sw = worker({ fetch: () => Promise.resolve(response) });
    await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now });
    const visit = sw.navigate('/renan/bruno');
    await visit.responded;
    await visit.settled();
    assert.equal(pages(sw).has('bruno'), false, `status ${response.status}`);
  }
});

test('servidor fora do ar (5xx) abre a cópia e não a apaga', async () => {
  const sw = worker({ fetch: () => Promise.resolve(new FakeResponse('Bad gateway', { status: 502 })) });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now });
  const visit = sw.navigate('/renan/bruno');
  assert.match(await (await visit.responded).text(), /data-offline-snapshot/);
  await visit.settled();
  assert.equal(pages(sw).has('bruno'), true);
});

test('rede sem resposta: depois do prazo abre a cópia; a resposta tardia só atualiza a cópia', async () => {
  let answer;
  const sw = worker({ fetch: () => new Promise((resolve) => { answer = resolve; }) });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now - DAY });
  const visit = sw.navigate('/renan/bruno');
  while (!sw.timers.length) await new Promise(setImmediate);
  assert.equal(sw.timers[0].delay, 5000);
  sw.timers[0].fn();
  assert.match(await (await visit.responded).text(), /data-offline-snapshot/);
  answer(new FakeResponse(PAGE_HTML.replace('Treino do Bruno', 'Treino novo'), { headers: { 'X-Curva-Offline-Scope': '990' } }));
  await visit.settled();
  assert.match(pages(sw).get('bruno').html, /Treino novo/);
  assert.equal(pages(sw).get('bruno').saved_at, sw.state.now);
});

test('sem cópia salva, a rede lenta não tem prazo', async () => {
  let answer;
  const sw = worker({ fetch: () => new Promise((resolve) => { answer = resolve; }) });
  const visit = sw.navigate('/renan/bruno');
  for (let i = 0; i < 5; i += 1) await new Promise(setImmediate);
  assert.equal(sw.timers.length, 0);
  const fresh = ownerPage();
  answer(fresh);
  assert.equal(await visit.responded, fresh);
});

test('"Sair da conta" apaga a cópia sem interceptar o POST', async () => {
  const sw = worker({ fetch: () => assert.fail('o POST segue direto para a rede') });
  await sw.seed({ slug: 'bruno', scope: '990', html: PAGE_HTML, saved_at: sw.state.now });
  const signOut = sw.navigate('/renan/bruno/sair', 'POST');
  assert.equal(signOut.responded, null);
  await signOut.settled();
  assert.equal(pages(sw).has('bruno'), false);
});

test('página offline genérica e JSON de saúde não entram no IndexedDB', async () => {
  const sw = worker({ fetch: () => Promise.resolve(ownerPage()) });
  const offline = sw.navigate('/renan/offline/');
  await offline.responded;
  await offline.settled();
  const json = sw.navigate('/renan/bruno/avaliacoes.json');
  assert.equal(json.responded, null);
  assert.equal(pages(sw).size, 0);
});
