const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/guided-sync.js'), 'utf8');
const sandbox = { window: {}, setTimeout() {}, setInterval() { return 1; }, clearInterval() {} };
vm.runInNewContext(source, sandbox);

function fixture(initial, send, extra = {}) {
  const commands = new Map(initial.map((item) => [item.key, item]));
  const mappings = new Map();
  const events = [];
  const confirmed = [];
  const network = { online: true };
  let nextSequence = 100;
  const outbox = {
    // Como o IndexedDB real: a sequência nasce na mesma transação da gravação.
    queue(_scope, item) {
      if (item.sequence == null) item.sequence = nextSequence++;
      commands.set(item.key, item);
      return Promise.resolve(item);
    },
    // slowList: a leitura é tirada na chamada e entregue depois, como um getAll do IndexedDB.
    list() {
      const snapshot = Array.from(commands.values());
      return extra.slowList ? new Promise((resolve) => setImmediate(() => resolve(snapshot))) : Promise.resolve(snapshot);
    },
    remove(_scope, key) { commands.delete(key); return Promise.resolve(); },
    mapSession(_scope, local, server) { mappings.set(local, server); return Promise.resolve(); },
    lookupSession(_scope, local) { return Promise.resolve(mappings.get(local)); },
    acquireLease() { return Promise.resolve(true); },
    releaseLease() { return Promise.resolve(); },
    clear() { events.push('cleared'); return Promise.resolve(); },
  };
  const sync = sandbox.window.CurvaGuidedSync.create({
    outbox, scope: 'account:plan', newId: () => 'owner', isOnline: () => network.online,
    request: send, hasActiveSession: () => false,
    onConflict: (command) => events.push('conflict:' + command.key),
    onSent: (payload) => confirmed.push(payload.action + ':' + payload.movement_index + ':' + payload.set_number),
    onStartMapped: (local, server) => events.push('mapped:' + local + ':' + server),
    onEndConfirmed: () => events.push('ended'),
    onDrained: (result) => events.push(result.backlog ? 'drained:backlog' : 'drained'),
    onError: (error) => events.push('error:' + error.message),
    ...extra,
  });
  sync.hydrate(initial);
  return { sync, commands, mappings, events, confirmed, network };
}

function setPayload(movementIndex, setNumber, extra = {}) {
  return {
    action: 'set', session_id: 'server', movement_slug: 'agachamento', movement_index: movementIndex,
    set_number: setNumber, set_role: 'top_set', weight_kg: '50', reps: '8', rir: '', ...extra,
  };
}

// Tudo no fake resolve em microtarefas; setImmediate só roda depois delas.
const flush = () => new Promise((resolve) => setImmediate(resolve));

function recorder(handlers = {}) {
  const calls = [];
  const send = (method, payload) => {
    calls.push(method === 'GET' ? 'GET' : 'POST:' + payload.action
      + (payload.movement_index == null ? '' : ':' + payload.movement_index + ':' + payload.set_number));
    const handler = handlers[method === 'GET' ? 'GET' : payload.action];
    if (handler) return handler(payload);
    return Promise.resolve(method === 'GET' ? { session: null } : { ok: true, created: true });
  };
  return { calls, send };
}

const writeAhead = { writeAhead: true, hasActiveSession: () => true };

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

test('write-ahead: série online grava antes, devolve na hora e gera exatamente 1 POST', async () => {
  let answer;
  const { calls, send } = recorder({ set: () => new Promise((resolve) => { answer = resolve; }) });
  const { sync, commands, events, confirmed } = fixture([], send, writeAhead);
  const result = await sync.deliver(setPayload(0, 1));
  assert.equal(result.queued, true);
  assert.equal(result.local, true);
  // Gravado no aparelho antes de qualquer resposta do servidor.
  assert.equal(commands.size, 1);
  await flush();
  assert.deepEqual(calls, ['POST:set:0:1']);
  assert.equal(sync.pendingCount(), 1);
  assert.equal(sync.backlogCount(), 0, 'envio em curso não aparece como "aguardando envio"');
  answer({ ok: true, created: true, set_id: 7 });
  await sync.idle();
  // Mesmo com sessão ativa, recibo simples não pede GET /sessao.
  assert.deepEqual(calls, ['POST:set:0:1']);
  assert.equal(commands.size, 0);
  assert.deepEqual(confirmed, ['set:0:1']);
  assert.deepEqual(events, ['drained']);
});

test('write-ahead: toques rápidos saem em ordem, uma vez cada, e o toque duplo vira um comando', async () => {
  const { calls, send } = recorder();
  const { sync, commands, network } = fixture([], send, writeAhead);
  await Promise.all([
    sync.deliver(setPayload(0, 1)),
    sync.deliver({ action: 'skip', session_id: 'server', movement_slug: 'agachamento', movement_index: 0, set_number: 2, set_role: 'top_set' }),
    sync.deliver(setPayload(1, 1)),
    sync.deliver({ action: 'unskip', session_id: 'server', movement_index: 0, set_number: 2 }),
  ]);
  await sync.idle();
  assert.deepEqual(calls, ['POST:set:0:1', 'POST:skip:0:2', 'POST:set:1:1', 'POST:unskip:0:2']);
  assert.equal(commands.size, 0);

  network.online = false;
  await sync.deliver(setPayload(2, 1));
  await sync.deliver(setPayload(2, 1));
  assert.equal(commands.size, 1, 'mesma chave movimento:série substitui o comando, não duplica');
  assert.equal(sync.backlogCount(), 1, 'offline, a série gravada é atraso de verdade');
  network.online = true;
  calls.length = 0;
  // Reconexão (drain padrão) mantém o GET de reconciliação.
  await sync.drain();
  assert.deepEqual(calls, ['POST:set:2:1', 'GET']);
});

test('write-ahead: aba fechada logo depois do toque não perde a série', async () => {
  // A aba morre com o POST no ar: a resposta nunca chega.
  const first = fixture([], () => new Promise(() => {}), writeAhead);
  await first.sync.deliver(setPayload(0, 1, { weight_kg: '62.5' }));
  await flush();
  const survived = Array.from(first.commands.values());
  assert.equal(survived.length, 1);
  assert.equal(survived[0].payload.weight_kg, '62.5');

  // A próxima aba abre a mesma fila: reenvia uma vez (o servidor é idempotente por movimento:série).
  const { calls, send } = recorder({ set: () => Promise.resolve({ ok: true, created: false }) });
  const reopened = fixture(survived, send, writeAhead);
  await reopened.sync.drain();
  assert.deepEqual(calls, ['POST:set:0:1', 'GET']);
  assert.equal(reopened.commands.size, 0);
  assert.deepEqual(reopened.events, ['drained:backlog']);
});

test('write-ahead: 4xx bloqueia o comando na fila sem perdê-lo nem enviar os seguintes', async () => {
  const timers = [];
  const original = sandbox.setTimeout;
  sandbox.setTimeout = (_fn, ms) => { timers.push(ms); };
  try {
    const { calls, send } = recorder({ set: (payload) => (payload.set_number === 1
      ? Promise.reject({ status: 400, message: 'serie invalida' }) : Promise.resolve({ ok: true })) });
    const { sync, commands, events } = fixture([], send, writeAhead);
    const first = await sync.deliver(setPayload(0, 1));
    const second = await sync.deliver(setPayload(0, 2));
    await sync.idle();
    assert.equal(first.local && second.local, true);
    assert.deepEqual(calls, ['POST:set:0:1']);
    assert.equal(commands.size, 2);
    const key = sandbox.window.CurvaGuidedSync.commandKey(setPayload(0, 1));
    assert.equal(commands.get(key).blocked, true);
    assert.equal(commands.get(key).error_status, 400);
    assert.equal(sync.blocked().key, key);
    assert.equal(sync.pendingCount(), 2);
    assert.equal(events.includes('conflict:' + key), true);
    assert.deepEqual(timers, [], '4xx não é reenviado sozinho');
  } finally {
    sandbox.setTimeout = original;
  }
});

test('write-ahead: série gravada durante uma drenagem não some da contagem nem é dada como enviada', async () => {
  const { calls, send } = recorder();
  const drained = [];
  const { sync, commands } = fixture([], send, {
    ...writeAhead, slowList: true, onDrained: (result) => drained.push(result.cleared),
  });
  await sync.deliver(setPayload(0, 1));
  // A leitura da fila já saiu sem a segunda série; ela é gravada antes da resposta.
  await sync.deliver(setPayload(0, 2));
  assert.equal(sync.pendingCount(), 2);
  await new Promise((resolve) => setImmediate(resolve));
  // A primeira já foi enviada; a lista antiga (só com ela) não apagou a segunda.
  assert.equal(commands.size, 1);
  assert.equal(sync.pendingCount(), 1);
  await sync.idle();
  assert.deepEqual(calls, ['POST:set:0:1', 'POST:set:0:2']);
  assert.deepEqual(drained, [false, true], 'só fica "limpo" depois da segunda série');
  assert.equal(commands.size, 0);
});

test('write-ahead: start ainda local é mapeado e pede GET depois da série', async () => {
  const { calls, send } = recorder({ start: () => Promise.resolve({ session_id: 'server' }) });
  const { sync, events } = fixture([], send, writeAhead);
  await sync.queue({ action: 'start', local_session_id: 'local', day_id: 'a', start_key: 'local' });
  await sync.deliver(setPayload(0, 1, { session_id: 'local' }));
  await sync.idle();
  assert.deepEqual(calls, ['POST:start', 'POST:set:0:1', 'GET']);
  assert.equal(events[0], 'mapped:local:server');
});

test('write-ahead: falha de rede vira atraso, agenda nova tentativa e reconcilia ao voltar', async () => {
  const timers = [];
  const original = sandbox.setTimeout;
  sandbox.setTimeout = (_fn, ms) => { timers.push(ms); };
  try {
    let down = true;
    const { calls, send } = recorder({ set: () => (down
      ? Promise.reject({ retryable: true, message: 'rede caiu' }) : Promise.resolve({ ok: true })) });
    const { sync, commands, events } = fixture([], send, writeAhead);
    await sync.deliver(setPayload(0, 1));
    await sync.idle();
    assert.equal(commands.size, 1);
    assert.equal(sync.backlogCount(), 1);
    assert.deepEqual(timers, [5000]);
    assert.equal(events.includes('error:rede caiu'), true);
    down = false;
    await sync.drain();
    assert.deepEqual(calls, ['POST:set:0:1', 'POST:set:0:1', 'GET']);
    assert.equal(commands.size, 0);
    assert.equal(events.at(-1), 'drained:backlog');
  } finally {
    sandbox.setTimeout = original;
  }
});

test('write-ahead: encerrar logo após a série espera o envio em curso e vai direto ao servidor', async () => {
  let answer;
  const { calls, send } = recorder({ set: () => new Promise((resolve) => { answer = resolve; }) });
  const { sync, commands } = fixture([], send, writeAhead);
  await sync.deliver(setPayload(0, 1));
  const ending = sync.deliver({ action: 'complete', session_id: 'server' });
  await flush();
  assert.deepEqual(calls, ['POST:set:0:1']);
  assert.equal(commands.size, 1, 'o encerramento não entrou na fila como se estivesse offline');
  answer({ ok: true });
  const result = await ending;
  assert.equal(result.queued, undefined);
  assert.deepEqual(calls, ['POST:set:0:1', 'POST:complete']);
  assert.equal(commands.size, 0);
});

test('write-ahead: encerrar com série pendente e nenhuma drenagem ativa drena antes e não vira offline', async () => {
  const { calls, send } = recorder();
  const pendingKey = sandbox.window.CurvaGuidedSync.commandKey(setPayload(0, 1));
  const { sync, commands } = fixture([{ key: pendingKey, sequence: 1, payload: setPayload(0, 1) }], send, writeAhead);
  const result = await sync.deliver({ action: 'complete', session_id: 'server' });
  assert.equal(result.queued, undefined, 'o encerramento não pode cair na fila com a rede de pé');
  // O GET é a reconciliação de uma pendência que veio de antes (não é `fresh`).
  assert.deepEqual(calls, ['POST:set:0:1', 'GET', 'POST:complete']);
  assert.equal(commands.size, 0);
});

test('write-ahead: se a drenagem não esvazia a fila, o encerramento entra na fila uma vez só', async () => {
  const { calls, send } = recorder({ set: () => Promise.reject(Object.assign(new Error('rede'), { retryable: true })) });
  const pendingKey = sandbox.window.CurvaGuidedSync.commandKey(setPayload(0, 1));
  const { sync, commands } = fixture([{ key: pendingKey, sequence: 1, payload: setPayload(0, 1) }], send, writeAhead);
  const result = await sync.deliver({ action: 'complete', session_id: 'server' });
  assert.equal(result.queued, true);
  assert.equal(commands.size, 2);
  assert.deepEqual(calls.filter((call) => call === 'POST:complete'), []);
});

test('sem write-ahead o envio continua direto e a drenagem continua pedindo GET', async () => {
  const { calls, send } = recorder();
  const online = fixture([], send, { hasActiveSession: () => true });
  const result = await online.sync.deliver(setPayload(0, 1));
  assert.equal(result.queued, undefined);
  assert.deepEqual(calls, ['POST:set:0:1']);
  assert.equal(online.commands.size, 0);

  calls.length = 0;
  const pendingKey = sandbox.window.CurvaGuidedSync.commandKey(setPayload(0, 2));
  const backlog = fixture([{ key: pendingKey, sequence: 1, payload: setPayload(0, 2) }], send, { hasActiveSession: () => true });
  await backlog.sync.deliver(setPayload(0, 3));
  await backlog.sync.idle();
  assert.deepEqual(calls, ['POST:set:0:2', 'POST:set:0:3', 'GET']);
});

test('applyQueued dobra séries, correções e pulos ainda na fila sobre a sessão', () => {
  const session = {
    session_id: 'server', day_id: 'a',
    recorded: [{ movement_index: 0, set_number: 1, weight_kg: '50.00', reps: 8, rir: null }],
    skipped: ['1:1'],
  };
  const commands = [
    { key: 'c', sequence: 3, payload: { action: 'correct', movement_index: 0, set_number: 1, weight_kg: '55', reps: '8', rir: '' } },
    { key: 'a', sequence: 1, payload: setPayload(0, 2, { weight_kg: '', reps: '10', rir: '2' }) },
    { key: 'b', sequence: 2, payload: { action: 'skip', movement_index: 1, set_number: 2 } },
    { key: 'd', sequence: 4, payload: { action: 'unskip', movement_index: 1, set_number: 1 } },
    { key: 'e', sequence: 5, payload: { action: 'complete', session_id: 'server' } },
  ];
  const merged = JSON.parse(JSON.stringify(sandbox.window.CurvaGuidedSync.applyQueued(session, commands)));
  assert.deepEqual(merged.recorded, [
    { movement_index: 0, set_number: 1, weight_kg: '55', reps: '8', rir: null },
    { movement_index: 0, set_number: 2, weight_kg: null, reps: '10', rir: '2' },
  ]);
  assert.deepEqual(merged.skipped, ['1:2']);
  assert.equal(merged.session_id, 'server');
  assert.equal(session.recorded.length, 1, 'não altera a sessão recebida');
});
