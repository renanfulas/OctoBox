/* Coordena a fila de cargas. IndexedDB, HTTP e UI entram por portas explícitas. */
(function () {
  'use strict';

  var LOCAL_FIELDS = ['queued_at', 'sync_state', 'sync_error', 'blocked_at', 'active_record'];

  function sendable(entry) {
    var payload = Object.assign({}, entry);
    LOCAL_FIELDS.forEach(function (field) { delete payload[field]; });
    return payload;
  }

  function ordered(entries) {
    return entries.map(function (entry, index) { return { entry: entry, index: index }; })
      .sort(function (a, b) {
        var aTime = a.entry.queued_at == null ? -1 : a.entry.queued_at;
        var bTime = b.entry.queued_at == null ? -1 : b.entry.queued_at;
        return aTime - bTime || a.index - b.index;
      }).map(function (item) { return item.entry; });
  }

  function create(options) {
    var api = options.api;
    var storage = options.storage;
    var draining = null;

    function enqueue(entry) {
      return storage.queueEntry(Object.assign({ queued_at: Date.now() }, entry));
    }

    function block(entry, result) {
      var blocked = Object.assign({}, entry, {
        queued_at: entry.queued_at == null ? Date.now() : entry.queued_at,
        sync_state: 'blocked',
        sync_error: result.data && result.data.error || 'O servidor não aceitou este registro.',
        blocked_at: Date.now(),
        active_record: result.data && result.data.active_record || null,
      });
      return storage.queueEntry(blocked).then(function () {
        if (options.onBlocked) options.onBlocked(blocked);
        return blocked;
      });
    }

    function drain() {
      if (draining) return draining;
      if (!options.planSlug()) return Promise.resolve({ state: 'no_plan' });
      draining = (async function () {
        var entries = ordered(await storage.listEntries());
        var isBatch = entries.length > 1;
        for (var i = 0; i < entries.length; i++) {
          var entry = entries[i];
          if (entry.sync_state === 'blocked') {
            if (options.onBlocked) options.onBlocked(entry);
            return { state: 'blocked', entry: entry };
          }
          if (!options.isOnline()) {
            if (options.onDeferred) options.onDeferred(entry, { status: 0 });
            return { state: 'offline', entry: entry };
          }
          var result;
          try {
            result = await api.postLoad(options.planSlug(), sendable(entry));
          } catch (_) {
            if (options.onDeferred) options.onDeferred(entry, { status: 0 });
            return { state: 'retry_later', entry: entry };
          }
          if (result.ok) {
            await storage.removeEntry(entry.idempotency_key);
            if (options.onConfirmed) options.onConfirmed(entry, result.data, isBatch);
            continue;
          }
          if (result.status === 400 || result.status === 409) {
            var blocked = await block(entry, result);
            return { state: 'blocked', entry: blocked };
          }
          if (options.onDeferred) options.onDeferred(entry, result);
          return { state: 'retry_later', entry: entry };
        }
        return { state: 'drained' };
      })().finally(function () { draining = null; });
      return draining;
    }

    function reapply(blockedKey, newKey) {
      return storage.listEntries().then(function (entries) {
        var entry = entries.find(function (item) { return item.idempotency_key === blockedKey; });
        var target = entry && entry.active_record && entry.active_record.idempotency_key;
        if (!entry || entry.sync_state !== 'blocked' || !target) {
          throw new Error('Não há registro atual para reaplicar esta correção.');
        }
        var replacement = Object.assign(sendable(entry), {
          idempotency_key: newKey,
          supersedes_idempotency_key: target,
          queued_at: entry.queued_at,
        });
        return storage.queueEntry(replacement).then(function () {
          return storage.removeEntry(blockedKey);
        }).then(function () { return replacement; });
      });
    }

    function discard(blockedKey) {
      return storage.listEntries().then(function (entries) {
        var entry = entries.find(function (item) { return item.idempotency_key === blockedKey; });
        if (!entry || entry.sync_state !== 'blocked') throw new Error('Conflito local não encontrado.');
        return storage.removeEntry(blockedKey);
      });
    }

    return { enqueue: enqueue, block: block, drain: drain, reapply: reapply,
      discard: discard, listEntries: storage.listEntries };
  }

  window.CurvaLoadSync = { create: create, sendable: sendable };
})();
