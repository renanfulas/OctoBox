const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/guided-outbox.js'), 'utf8');

// IndexedDB mínimo: pedidos em ordem, um por volta do laço, e a transação
// conclui quando a fila esvazia. Basta para contar aberturas e fechamentos.
function fakeIndexedDB() {
  const databases = new Map();
  const opened = [];
  const connections = [];
  const faults = { open: null, transaction: null };

  function invalidState() {
    const error = new Error('A conexão está fechando.');
    error.name = 'InvalidStateError';
    return error;
  }

  function transaction(data, names) {
    const tx = { error: null, oncomplete: null, onerror: null, onabort: null };
    const jobs = [];
    let scheduled = false;
    let fault = faults.transaction;
    faults.transaction = null;
    function schedule() {
      if (scheduled) return;
      scheduled = true;
      setImmediate(step);
    }
    function step() {
      scheduled = false;
      if (fault) {
        tx.error = fault;
        tx.onerror({ target: { error: fault } });
        tx.onabort();
        return;
      }
      const job = jobs.shift();
      if (!job) { tx.oncomplete(); return; }
      job();
      schedule();
    }
    tx.objectStore = (name) => {
      assert.ok(names.includes(name), 'store fora da transação: ' + name);
      const store = data.stores.get(name);
      const op = (fn) => {
        const request = { result: undefined, onsuccess: null };
        jobs.push(() => {
          request.result = fn();
          if (request.onsuccess) request.onsuccess({ target: request });
        });
        schedule();
        return request;
      };
      return {
        get: (key) => op(() => structuredClone(store.rows.get(key))),
        put: (value) => op(() => { store.rows.set(value[store.keyPath], structuredClone(value)); }),
        delete: (key) => op(() => { store.rows.delete(key); }),
        getAll: () => op(() => Array.from(store.rows.values(), (row) => structuredClone(row))),
        count: () => op(() => store.rows.size),
      };
    };
    schedule();
    return tx;
  }

  function connect(data) {
    const db = {
      closed: false, onversionchange: null, onclose: null,
      objectStoreNames: { contains: (name) => data.stores.has(name) },
      createObjectStore(name, options) { data.stores.set(name, { keyPath: options.keyPath, rows: new Map() }); },
      close() { db.closed = true; },
      transaction(names) {
        if (db.closed) throw invalidState();
        return transaction(data, [].concat(names));
      },
    };
    connections.push(db);
    return db;
  }

  const factory = {
    open(name, version) {
      opened.push(name);
      const request = { result: null, error: null, onupgradeneeded: null, onsuccess: null, onerror: null };
      setImmediate(() => {
        if (faults.open) {
          request.error = faults.open;
          faults.open = null;
          request.onerror();
          return;
        }
        if (!databases.has(name)) databases.set(name, { version: 0, stores: new Map() });
        const data = databases.get(name);
        request.result = connect(data);
        if (data.version < version) {
          data.version = version;
          request.onupgradeneeded();
        }
        request.onsuccess();
      });
      return request;
    },
  };
  return { factory, opened, connections, faults };
}

function load() {
  const idb = fakeIndexedDB();
  const listeners = {};
  const window = { indexedDB: idb.factory, addEventListener(type, fn) { listeners[type] = fn; } };
  vm.runInNewContext(source, { window, indexedDB: idb.factory, setImmediate });
  return { outbox: window.CurvaGuidedOutbox, idb, listeners };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test('uma série inteira reaproveita a mesma conexão', async () => {
  const { outbox, idb } = load();
  // A ordem do write-ahead: fila, snapshot, lease, lista, mapa, envio, remoção, release.
  await outbox.queue('conta', { key: 's:set:0:1', payload: { action: 'set' }, created_at: 1 });
  await outbox.save('conta', { recorded: [] });
  assert.equal(await outbox.acquireLease('conta', 'aba', 12000), true);
  assert.equal((await outbox.list('conta')).length, 1);
  assert.equal(await outbox.lookupSession('conta', 's'), null);
  await outbox.remove('conta', 's:set:0:1');
  await outbox.list('conta');
  await outbox.releaseLease('conta', 'aba');
  await outbox.list('conta');
  assert.deepEqual(idb.opened, ['curva-guided:conta']);
});

test('chamadas simultâneas antes da primeira abertura compartilham a conexão', async () => {
  const { outbox, idb } = load();
  await Promise.all([outbox.list('conta'), outbox.restore('conta'), outbox.acquireLease('conta', 'aba', 1000)]);
  assert.equal(idb.opened.length, 1);
});

test('cada conta tem o próprio banco', async () => {
  const { outbox, idb } = load();
  await outbox.queue('conta-a', { key: 'k', payload: {}, created_at: 1 });
  assert.deepEqual(await outbox.list('conta-b'), []);
  assert.equal((await outbox.list('conta-a')).length, 1);
  assert.deepEqual(idb.opened, ['curva-guided:conta-a', 'curva-guided:conta-b']);
});

test('sem escopo rejeita sem abrir banco', async () => {
  const { outbox, idb } = load();
  await assert.rejects(outbox.list(''), /Armazenamento local indisponível/);
  assert.deepEqual(idb.opened, []);
});

test('versionchange fecha a conexão e a próxima chamada reabre', async () => {
  const { outbox, idb } = load();
  await outbox.list('conta');
  idb.connections[0].onversionchange();
  assert.equal(idb.connections[0].closed, true);
  await outbox.list('conta');
  assert.equal(idb.opened.length, 2);
});

test('fechamento pelo navegador reabre na próxima chamada', async () => {
  const { outbox, idb } = load();
  await outbox.list('conta');
  idb.connections[0].closed = true;
  idb.connections[0].onclose();
  await outbox.list('conta');
  assert.equal(idb.opened.length, 2);
});

test('falha ao abrir não fica guardada', async () => {
  const { outbox, idb } = load();
  idb.faults.open = new Error('Sem espaço.');
  await assert.rejects(outbox.list('conta'), /Sem espaço/);
  await flush();
  assert.deepEqual(await outbox.list('conta'), []);
  assert.equal(idb.opened.length, 2);
});

test('conexão fechada sem evento reabre uma vez e conclui a gravação', async () => {
  const { outbox, idb } = load();
  await outbox.list('conta');
  idb.connections[0].close();
  await outbox.queue('conta', { key: 'k', payload: {}, created_at: 1 });
  assert.equal((await outbox.list('conta')).length, 1);
  assert.equal(idb.opened.length, 2);
});

test('erro na transação rejeita e solta a conexão', async () => {
  const { outbox, idb } = load();
  await outbox.list('conta');
  const quota = new Error('Cota excedida.');
  quota.name = 'QuotaExceededError';
  idb.faults.transaction = quota;
  await assert.rejects(outbox.save('conta', {}), /Cota excedida/);
  assert.equal(idb.connections[0].closed, true);
  await outbox.list('conta');
  assert.equal(idb.opened.length, 2);
});

test('pagehide fecha as conexões e a volta reabre sob demanda', async () => {
  const { outbox, idb, listeners } = load();
  await outbox.list('conta');
  listeners.pagehide();
  await flush();
  assert.equal(idb.connections[0].closed, true);
  await outbox.list('conta');
  assert.equal(idb.opened.length, 2);
});

test('fila numera em ordem e o lease continua exclusivo por dono', async () => {
  const { outbox } = load();
  const first = await outbox.queue('conta', { key: 'a', payload: {}, created_at: 1 });
  const second = await outbox.queue('conta', { key: 'b', payload: {}, created_at: 2 });
  assert.deepEqual([first.sequence, second.sequence], [1, 2]);
  assert.equal(await outbox.acquireLease('conta', 'aba-1', 60000), true);
  assert.equal(await outbox.acquireLease('conta', 'aba-2', 60000), false);
  await outbox.releaseLease('conta', 'aba-2');
  assert.equal(await outbox.acquireLease('conta', 'aba-2', 60000), false);
  await outbox.releaseLease('conta', 'aba-1');
  assert.equal(await outbox.acquireLease('conta', 'aba-2', 60000), true);
});

test('mapa de sessão e ficha voltam pelo mesmo banco', async () => {
  const { outbox, idb } = load();
  await outbox.mapSession('conta', 'local-1', 42);
  assert.equal(await outbox.lookupSession('conta', 'local-1'), 42);
  await outbox.savePlan('conta', { program_version: 3 });
  assert.deepEqual(await outbox.restorePlan('conta'), { program_version: 3 });
  await outbox.save('conta', { recorded: [1] });
  assert.deepEqual(await outbox.restore('conta'), { recorded: [1] });
  await outbox.clear('conta');
  assert.equal(await outbox.restore('conta'), null);
  assert.equal(idb.opened.length, 1);
});

test('savePlan protege a ficha do treino em andamento sem fechar a conexão', async () => {
  const { outbox, idb } = load();
  assert.equal(await outbox.savePlan('conta', { program_version: 3 }), true);
  await outbox.save('conta', { program_version: 3, recorded: [] });
  // Treino aberto na versão 3: outra versão não troca a ficha embaixo dele.
  assert.equal(await outbox.savePlan('conta', { program_version: 4 }), false);
  assert.deepEqual(await outbox.restorePlan('conta'), { program_version: 3 });
  assert.equal(await outbox.savePlan('conta', { program_version: 3, title: 'nova' }), true);
  await outbox.clear('conta');
  await outbox.queue('conta', { key: 'a', payload: {}, created_at: 1 });
  // Série ainda na fila também segura a versão.
  assert.equal(await outbox.savePlan('conta', { program_version: 4 }), false);
  assert.equal(idb.opened.length, 1);
});
