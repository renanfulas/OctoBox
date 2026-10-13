const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/guided-sync.js'), 'utf8');
const sandbox = { window: {}, setTimeout() {}, setInterval() { return 1; }, clearInterval() {} };
vm.runInNewContext(source, sandbox);

function fixture(initial, send) {
  const commands = new Map(initial.map((item) => [item.key, item]));
  const mappings = new Map();
  const events = [];
  const outbox = {
    queue(_scope, item) { commands.set(item.key, item); return Promise.resolve(item); },
    list() { return Promise.resolve(Array.from(commands.values())); },
    remove(_scope, key) { commands.delete(key); return Promise.resolve(); },
    mapSession(_scope, local, server) { mappings.set(local, server); return Promise.resolve(); },
    lookupSession(_scope, local) { return Promise.resolve(mappings.get(local)); },
    acquireLease() { return Promise.resolve(true); },
    releaseLease() { return Promise.resolve(); },
    clear() { events.push('cleared'); return Promise.resolve(); },
  };
  const sync = sandbox.window.CurvaGuidedSync.create({
    outbox, scope: 'account:plan', newId: () => 'owner', isOnline: () => true,
    request: send, hasActiveSession: () => false,
    onConflict: (command) => events.push('conflict:' + command.key),
    onStartMapped: (local, server) => events.push('mapped:' + local + ':' + server),
    onEndConfirmed: () => events.push('ended'),
    onDrained: () => events.push('drained'),
    onError: (error) => events.push('error:' + error.message),
  });
  sync.hydrate(initial);
  return { sync, commands, mappings, events };
}

test('replay preserva ordem e remapeia sessão local antes da série e do fim', async () => {
  const sent = [];
  const initial = [
    { key: 'end', sequence: 3, payload: { action: 'complete', session_id: 'local' } },
    { key: 'set', sequence: 2, payload: { action: 'set', session_id: 'local', movement_index: 0, set_number: 1 } },
    { key: 'start', sequence: 1, payload: { action: 'start', local_session_id: 'local' } },
  ];
  const { sync, commands, events } = fixture(initial, (method, payload) => {
    if (method === 'GET') return Promise.resolve({ session: null });
    sent.push(payload);
    return Promise.resolve(payload.action === 'start' ? { session_id: 'server' } : {});
  });
  await sync.drain();
  assert.deepEqual(sent.map((item) => item.action), ['start', 'set', 'complete']);
  assert.equal(sent[1].session_id, 'server');
  assert.equal(sent[2].session_id, 'server');
  assert.equal(commands.size, 0);
  assert.equal(sync.pendingCount(), 0);
  assert.deepEqual(events.slice(0, 3), ['mapped:local:server', 'ended', 'cleared']);
});

test('409 bloqueia sem perder comando, permite trocar por correção na mesma posição', async () => {
  let fail = true;
  const initial = [{ key: 'set', sequence: 1, payload: { action: 'set', session_id: 'server', movement_index: 0, set_number: 1 } }];
  const { sync, commands, events } = fixture(initial, (method) => {
    if (method === 'GET') return Promise.resolve({ session: null });
    if (fail) return Promise.reject({ status: 409, message: 'série já existe' });
    return Promise.resolve({});
  });
  await sync.drain();
  assert.equal(commands.get('set').blocked, true);
  assert.equal(sync.blocked().key, 'set');
  assert.equal(events.includes('conflict:set'), true);
  await sync.replaceBlocked({ action: 'correct', session_id: 'server', movement_index: 0, set_number: 1, command_key: 'new' });
  assert.equal(commands.has('set'), false);
  assert.equal(Array.from(commands.values())[0].sequence, 1);
  fail = false;
  await sync.drain();
  assert.equal(commands.size, 0);
});

test('401 mantém a fila e o comando continua pendente', async () => {
  const initial = [{ key: 'set', sequence: 1, payload: { action: 'set', session_id: 'server' } }];
  const { sync, commands } = fixture(initial, () => Promise.reject({ status: 401, message: 'login' }));
  await sync.drain();
  assert.equal(commands.size, 1);
  assert.equal(sync.pendingCount(), 1);
  assert.equal(sync.blocked(), null);
});

test('lease ocupado por outra aba não apaga pendências locais', async () => {
  const initial = [{ key: 'set', sequence: 1, payload: { action: 'set', session_id: 'server' } }];
  const { sync, commands, events } = fixture(initial, () => Promise.reject(new Error('não deve enviar')));
  sync.hydrate(initial);
  const before = sync.pendingCount();
  // Um segundo dispositivo/aba está drenando. O coordenador atual apenas agenda nova tentativa.
  const outbox = { acquireLease: () => Promise.resolve(false) };
  // O fake de outbox da fixture fica encapsulado; validamos a decisão usando outra instância.
  const busySync = sandbox.window.CurvaGuidedSync.create({
    outbox, scope: 'account:plan', newId: () => 'other', isOnline: () => true,
    request: () => Promise.reject(new Error('não deve enviar')),
    hasActiveSession: () => false,
    onError: (error) => events.push('error:' + error.message),
  });
  busySync.hydrate(initial);
  await busySync.drain();
  assert.equal(before, 1);
  assert.equal(busySync.pendingCount(), 1);
  assert.equal(commands.size, 1);
  assert.equal(events.length, 0);
});
