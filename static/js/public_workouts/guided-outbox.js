(function () {
  'use strict';

  // O banco é particionado pelo identificador da conta autenticada. A fila
  // nunca é drenada sob outra sessão, mesmo em aparelho compartilhado.
  function open(scope) {
    if (!scope || !window.indexedDB) return Promise.reject(new Error('Armazenamento local indisponível.'));
    return new Promise(function (resolve, reject) {
      var request = indexedDB.open('curva-guided:' + scope, 2);
      request.onupgradeneeded = function () {
        if (!request.result.objectStoreNames.contains('commands')) {
          request.result.createObjectStore('commands', { keyPath: 'key' });
        }
        if (!request.result.objectStoreNames.contains('state')) {
          request.result.createObjectStore('state', { keyPath: 'key' });
        }
      };
      request.onsuccess = function () {
        request.result.onversionchange = function () { request.result.close(); };
        resolve(request.result);
      };
      request.onerror = function () { reject(request.error); };
    });
  }

  function transact(scope, storeName, mode, method, value) {
    return open(scope).then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(storeName, mode);
        var request = tx.objectStore(storeName)[method](value);
        var result;
        request.onsuccess = function () { result = request.result; };
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error || new Error('Gravação local cancelada.')); };
        tx.oncomplete = function () { db.close(); resolve(result); };
      });
    });
  }

  function queue(scope, command) {
    return open(scope).then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(['commands', 'state'], 'readwrite');
        var commands = tx.objectStore('commands');
        var state = tx.objectStore('state');
        if (command.sequence != null) {
          commands.put(command);
        } else {
          var request = state.get('next-sequence');
          request.onsuccess = function () {
            var next = request.result ? request.result.value : 1;
            command.sequence = next;
            state.put({ key: 'next-sequence', value: next + 1 });
            commands.put(command);
          };
        }
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error || new Error('Fila local cancelada.')); };
        tx.oncomplete = function () { db.close(); resolve(command); };
      });
    });
  }

  function list(scope) {
    return transact(scope, 'commands', 'readonly', 'getAll');
  }

  function remove(scope, key) {
    return transact(scope, 'commands', 'readwrite', 'delete', key);
  }

  function save(scope, snapshot) {
    return transact(scope, 'state', 'readwrite', 'put', { key: 'active', snapshot: snapshot });
  }

  function restore(scope) {
    return transact(scope, 'state', 'readonly', 'get', 'active').then(function (row) {
      return row ? row.snapshot : null;
    });
  }

  function clear(scope) {
    return transact(scope, 'state', 'readwrite', 'delete', 'active');
  }

  function savePlan(scope, plan) {
    return open(scope).then(function (db) {
      return new Promise(function (resolve, reject) {
        // A leitura e a escrita compartilham a transação com a fila: outra aba
        // não pode trocar a ficha entre a verificação e a gravação.
        var tx = db.transaction(['state', 'commands'], 'readwrite');
        var state = tx.objectStore('state');
        var oldPlan = state.get('plan');
        var active = state.get('active');
        var pending = tx.objectStore('commands').count();
        var completed = 0;
        var saved = false;
        function decide() {
          completed += 1;
          if (completed !== 3) return;
          var currentVersion = oldPlan.result && oldPlan.result.plan && oldPlan.result.plan.program_version;
          var activeVersion = active.result && active.result.snapshot && active.result.snapshot.program_version;
          var incomingVersion = String(plan.program_version);
          var protectedVersion = currentVersion != null ? currentVersion : activeVersion;
          if ((active.result || pending.result) &&
              (protectedVersion == null || String(protectedVersion) !== incomingVersion)) return;
          state.put({ key: 'plan', plan: plan });
          saved = true;
        }
        oldPlan.onsuccess = decide;
        active.onsuccess = decide;
        pending.onsuccess = decide;
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error || new Error('Plano local não foi salvo.')); };
        tx.oncomplete = function () { db.close(); resolve(saved); };
      });
    });
  }

  function restorePlan(scope) {
    return transact(scope, 'state', 'readonly', 'get', 'plan').then(function (row) {
      return row ? row.plan : null;
    });
  }

  function mapSession(scope, localId, serverId) {
    return transact(scope, 'state', 'readwrite', 'put', {
      key: 'session-map:' + localId, session_id: serverId,
    });
  }

  function lookupSession(scope, localId) {
    return transact(scope, 'state', 'readonly', 'get', 'session-map:' + localId).then(function (row) {
      return row ? row.session_id : null;
    });
  }

  function acquireLease(scope, owner, ttlMs) {
    return open(scope).then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction('state', 'readwrite');
        var store = tx.objectStore('state');
        var granted = false;
        var request = store.get('drain-lease');
        request.onsuccess = function () {
          var now = Date.now();
          var lease = request.result;
          if (!lease || lease.until <= now || lease.owner === owner) {
            store.put({ key: 'drain-lease', owner: owner, until: now + ttlMs });
            granted = true;
          }
        };
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error || new Error('Lease local cancelado.')); };
        tx.oncomplete = function () { db.close(); resolve(granted); };
      });
    });
  }

  function releaseLease(scope, owner) {
    return open(scope).then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction('state', 'readwrite');
        var store = tx.objectStore('state');
        var request = store.get('drain-lease');
        request.onsuccess = function () {
          if (request.result && request.result.owner === owner) store.delete('drain-lease');
        };
        tx.onerror = function () { db.close(); reject(tx.error); };
        tx.onabort = function () { db.close(); reject(tx.error || new Error('Lease local cancelado.')); };
        tx.oncomplete = function () { db.close(); resolve(); };
      });
    });
  }

  window.CurvaGuidedOutbox = {
    queue: queue, list: list, remove: remove, save: save, restore: restore, clear: clear,
    savePlan: savePlan, restorePlan: restorePlan,
    mapSession: mapSession, lookupSession: lookupSession,
    acquireLease: acquireLease, releaseLease: releaseLease,
  };
}());
