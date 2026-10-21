const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../static/js/public_workouts/load-sync.js'), 'utf8');
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);

function createStorage(initial) {
  const rows = new Map(initial.map((entry) => [entry.idempotency_key, entry]));
  return {
    rows,
    queueEntry(entry) { rows.set(entry.idempotency_key, entry); return Promise.resolve(entry); },
    removeEntry(key) { rows.delete(key); return Promise.resolve(); },
    listEntries() { return Promise.resolve(Array.from(rows.values())); },
  };
}

test('409 preserva a segunda correção offline e permite reaplicar sobre o registro atual', async () => {
  const storage = createStorage([
    { idempotency_key: 'primeira', supersedes_idempotency_key: 'original', movement_slug: 'supino', queued_at: 1 },
    { idempotency_key: 'segunda', supersedes_idempotency_key: 'original', movement_slug: 'supino', queued_at: 2 },
  ]);
  const sent = [];
  const blocked = [];
  const sync = sandbox.window.CurvaLoadSync.create({
    storage,
    planSlug: () => 'bruno',
    isOnline: () => true,
    api: { postLoad(_slug, entry) {
      sent.push(entry);
      if (entry.idempotency_key === 'segunda') return Promise.resolve({
        ok: false, status: 409,
        data: { error: 'registro já corrigido', active_record: { idempotency_key: 'primeira' } },
      });
      return Promise.resolve({ ok: true, status: 200, data: {} });
    } },
    onBlocked: (entry) => blocked.push(entry),
  });

  assert.equal((await sync.drain()).state, 'blocked');
  assert.equal(storage.rows.has('primeira'), false);
  assert.equal(storage.rows.get('segunda').sync_state, 'blocked');
  assert.equal(blocked.length, 1);
  const replacement = await sync.reapply('segunda', 'reaplicada');
  assert.equal(replacement.supersedes_idempotency_key, 'primeira');
  assert.equal(storage.rows.has('segunda'), false);
  assert.equal((await sync.drain()).state, 'drained');
  assert.equal(storage.rows.size, 0);
  assert.equal(sent[2].idempotency_key, 'reaplicada');
  assert.equal(Object.hasOwn(sent[2], 'queued_at'), false);
});

test('bloqueio reaparece offline sem perder entrada e 401 mantém a fila', async () => {
  const storage = createStorage([
    { idempotency_key: 'bloqueada', sync_state: 'blocked', movement_slug: 'remada', queued_at: 1 },
  ]);
  let online = false;
  const blocked = [];
  const sync = sandbox.window.CurvaLoadSync.create({
    storage, planSlug: () => 'bruno', isOnline: () => online,
    api: { postLoad: () => Promise.resolve({ ok: false, status: 401, data: {} }) },
    onBlocked: (entry) => blocked.push(entry),
  });
  assert.equal((await sync.drain()).state, 'blocked');
  assert.equal(blocked.length, 1);
  await sync.discard('bloqueada');
  await sync.enqueue({ idempotency_key: 'pendente', movement_slug: 'remada' });
  assert.equal((await sync.drain()).state, 'offline');
  online = true;
  assert.equal((await sync.drain()).state, 'retry_later');
  assert.equal(storage.rows.has('pendente'), true);
});
