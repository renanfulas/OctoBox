const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createApi(fetch) {
  const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/load-api.js'), 'utf8');
  const sandbox = { window: { fetch }, document: { cookie: 'theme=dark; csrftoken=token%20value' } };
  vm.runInNewContext(source, sandbox);
  return sandbox.window.CurvaLoadApi;
}

test('envia carga com CSRF e devolve o recibo HTTP para o controlador', async () => {
  let request;
  const api = createApi((url, options) => {
    request = { url, options };
    return Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve('{"achievement":"top"}') });
  });
  const result = await api.postLoad('bruno', { weight_kg: 50 });
  assert.equal(request.url, '/renan/bruno/carga');
  assert.equal(request.options.credentials, 'same-origin');
  assert.equal(request.options.headers['X-CSRFToken'], 'token value');
  assert.equal(JSON.parse(request.options.body).weight_kg, 50);
  assert.equal(result.ok, true);
  assert.equal(result.data.achievement, 'top');
});

test('preserva status de conflito e erro de rede para a política de fila', async () => {
  const conflict = createApi(() => Promise.resolve({ ok: false, status: 409, text: () => Promise.resolve('erro') }));
  const result = await conflict.postLoad('bruno', {});
  assert.equal(result.status, 409);
  assert.equal(Object.keys(result.data).length, 0);

  const offline = createApi(() => Promise.reject(new Error('offline')));
  await assert.rejects(offline.postLoad('bruno', {}), /offline/);
});

test('lê última Top e retorna mapa vazio se o pacote falhar', async () => {
  const api = createApi(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ last_top_set_by_movement: { supino: 60 } }) }));
  const values = await api.lastTopSetByMovement('bruno');
  assert.equal(values.supino, 60);
  const unavailable = createApi(() => Promise.reject(new Error('offline')));
  assert.equal(Object.keys(await unavailable.lastTopSetByMovement('bruno')).length, 0);
});
