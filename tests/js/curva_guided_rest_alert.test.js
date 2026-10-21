const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/guided-rest-alert.js'), 'utf8');
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const RestAlert = sandbox.window.CurvaGuidedRestAlert;

const flush = () => new Promise((resolve) => setImmediate(resolve));

function fixture(extra = {}) {
  const clock = { now: 1_000_000 };
  const screen = { visible: true };
  const calls = [];
  const device = { endpoint: 'https://fcm.googleapis.com/fcm/send/device' };
  const alert = RestAlert.create({
    url: '/renan/bruno/push/descanso',
    now: () => clock.now,
    isVisible: () => screen.visible,
    endpoint: () => Promise.resolve(device.endpoint),
    describe: () => ({ exercise: 'Supino reto', setNumber: 3 }),
    send: (method, body, keepalive) => {
      calls.push({ method, body, keepalive });
      return extra.fail && extra.fail(method) ? Promise.reject(new Error('409')) : Promise.resolve();
    },
    ...extra.options,
  });
  return { alert, clock, screen, calls, device };
}

test('descanso começa: agenda no servidor pelo tempo restante, com exercício e série', async () => {
  const { alert, clock, calls } = fixture();
  alert.started('session-1', clock.now + 90_000);
  await flush();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, 'POST');
  assert.deepEqual({ ...calls[0].body }, {
    session_id: 'session-1', endpoint: 'https://fcm.googleapis.com/fcm/send/device',
    remaining_ms: 90_000, exercise: 'Supino reto', set_number: 3,
  });
  assert.equal(calls[0].keepalive, false);
  assert.equal(alert.covers(), true, 'push de pé: o fim é dele');
});

test('aparelho sem inscrição push não chama o servidor', async () => {
  const { alert, clock, calls, device } = fixture();
  device.endpoint = null;
  alert.started('session-1', clock.now + 90_000);
  await flush();
  assert.equal(alert.covers(), false, 'sem push, o bipe do app avisa');
  alert.tick(3000);
  alert.cleared();
  await flush();
  assert.equal(calls.length, 0);
});

test('+30 s reagenda e pular cancela, sempre na ordem dos toques', async () => {
  const { alert, clock, calls } = fixture();
  alert.started('session-1', clock.now + 60_000);
  await flush();
  alert.started('session-1', clock.now + 90_000);
  await flush();
  alert.cleared();
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST', 'POST', 'DELETE']);
  assert.equal(calls[1].body.remaining_ms, 90_000);
  assert.deepEqual({ ...calls[2].body }, { session_id: 'session-1' });
});

test('com a tela à vista perto do fim, o app cancela o push e toca o próprio bipe', async () => {
  const { alert, clock, calls } = fixture();
  alert.started('session-1', clock.now + 30_000);
  await flush();
  alert.tick(10_000);
  alert.tick(RestAlert.CANCEL_LEAD_MS + 1);
  await flush();
  assert.equal(calls.length, 1);
  assert.equal(alert.covers(), true);
  alert.tick(RestAlert.CANCEL_LEAD_MS);
  assert.equal(alert.covers(), false, 'o 3-2-1 volta para o app no mesmo tick');
  alert.tick(3000);
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST', 'DELETE']);
  alert.ended();
  assert.equal(alert.covers(), false);
  alert.cleared();
  await flush();
  assert.equal(calls.length, 2);
});

test('tela bloqueada perto do fim mantém o push agendado', async () => {
  const { alert, clock, screen, calls } = fixture();
  alert.started('session-1', clock.now + 30_000);
  await flush();
  screen.visible = false;
  alert.hidden();
  alert.tick(3000);
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST']);
  assert.equal(alert.covers(), true, 'tela bloqueada: o app não bipa por cima do push');
  alert.ended();
  assert.equal(alert.covers(), false);
});

test('saiu da tela depois do cancelamento: agenda de novo com keepalive enquanto houver tempo', async () => {
  const { alert, clock, screen, calls } = fixture();
  alert.started('session-1', clock.now + 30_000);
  await flush();
  clock.now += 26_500;
  alert.tick(3500);
  await flush();
  screen.visible = false;
  alert.hidden();
  await flush();
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST', 'DELETE', 'POST']);
  assert.equal(calls[0].body.remaining_ms, 30_000);
  assert.equal(calls[2].keepalive, true);
  assert.equal(calls[2].body.remaining_ms, 3500);
  assert.equal(alert.covers(), true);
});

test('no último segundo e meio não vale mais um push', async () => {
  const { alert, clock, screen, calls } = fixture();
  alert.started('session-1', clock.now + 30_000);
  await flush();
  clock.now += 26_500;
  alert.tick(3500);
  clock.now += 2_200;
  screen.visible = false;
  alert.hidden();
  await flush();
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST', 'DELETE']);
  assert.equal(alert.covers(), false, 'sem push a caminho, o bipe do app avisa mesmo com a tela bloqueada');
});

test('servidor recusou o agendamento: nada a cancelar perto do fim', async () => {
  const { alert, clock, calls } = fixture({ fail: (method) => method === 'POST' });
  alert.started('local-1', clock.now + 30_000);
  await flush();
  await flush();
  assert.equal(alert.covers(), false, 'agendamento recusado: o bipe do app avisa');
  alert.tick(3000);
  await flush();
  assert.deepEqual(calls.map((call) => call.method), ['POST']);
});

test('início offline ganhou id do servidor: agenda com o id novo', async () => {
  const { alert, clock, calls } = fixture({ fail: (method) => method === 'POST' && calls.length === 1 });
  alert.started('local-1', clock.now + 30_000);
  await flush();
  await flush();
  alert.remap('local-1', 'server-1');
  alert.remap('outra', 'server-2');
  await flush();
  await flush();
  assert.deepEqual(calls.map((call) => call.body.session_id), ['local-1', 'server-1']);
});

test('descanso que já acabou não agenda', async () => {
  const { alert, clock, calls } = fixture();
  alert.started('session-1', clock.now - 1);
  alert.started('session-1', clock.now + 1_000);
  alert.started(null, clock.now + 30_000);
  await flush();
  assert.equal(calls.length, 0);
});

test('sem URL (push não verificado) o módulo não faz nada', () => {
  const alert = RestAlert.create({});
  for (const method of ['started', 'cleared', 'ended', 'tick', 'hidden', 'remap', 'covers']) {
    assert.equal(typeof alert[method], 'function');
    alert[method]('session-1', Date.now() + 30_000);
  }
  assert.ok(!alert.covers());
});
