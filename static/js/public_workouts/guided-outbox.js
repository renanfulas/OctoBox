(function () {
  'use strict';

  // Uma conexão por escopo vive com a página: com o write-ahead, cada série online
  // faz ~9 transações e abrir o banco em cada uma atrasava o recibo.
  var connections = {};

  function drop(scope, connection, db) {
    if (connections[scope] === connection) delete connections[scope];
    if (db) db.close();
  }

  // O banco é particionado pelo identificador da conta autenticada. A fila
  // nunca é drenada sob outra sessão, mesmo em aparelho compartilhado.
  function open(scope) {
    if (!scope || !window.indexedDB) return Promise.reject(new Error('Armazenamento local indisponível.'));
    if (connections[scope]) return connections[scope];
    var connection = new Promise(function (resolve, reject) {
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
        var db = request.result;
        // Outra aba subindo a versão ou "Apagar dados" do shell offline: solta já.
        db.onversionchange = function () { drop(scope, connection, db); };
        // Fechada pelo navegador (ex.: iOS derruba o servidor do IndexedDB).
        db.onclose = function () { drop(scope, connection); };
        resolve(db);
      };
      request.onerror = function () { reject(request.error); };
    });
    connections[scope] = connection;
    connection.catch(function () { drop(scope, connection); });
    return connection;
  }

  // `work` monta os pedidos na transação e devolve quem lê o resultado no fim.
  function run(scope, storeNames, mode, abortMessage, work) {
    function attempt(retry) {
      var connection = open(scope);
      return connection.then(function (db) {
        var tx;
        try {
          tx = db.transaction(storeNames, mode);
        } catch (error) {
          drop(scope, connection, db);
          // A conexão guardada fechou sem evento: reabre uma vez.
          if (retry && error && error.name === 'InvalidStateError') return attempt(false);
          throw error;
        }
        return new Promise(function (resolve, reject) {
          var read;
          tx.onerror = function (event) { drop(scope, connection, db); reject(tx.error || event.target.error); };
          tx.onabort = function () { drop(scope, connection, db); reject(tx.error || new Error(abortMessage)); };
          tx.oncomplete = function () { resolve(read ? read() : undefined); };
          read = work(tx);
        });
      });
    }
    return attempt(true);
  }

  // Sair da página não deixa conexão aberta no bfcache; a volta reabre sob demanda.
  window.addEventListener('pagehide', function () {
    Object.keys(connections).forEach(function (scope) {
      var connection = connections[scope];
      connection.then(function (db) { drop(scope, connection, db); }, function () {});
    });
  });

  function transact(scope, storeName, mode, method, value) {
    return run(scope, storeName, mode, 'Gravação local cancelada.', function (tx) {
      var request = tx.objectStore(storeName)[method](value);
      return function () { return request.result; };
    });
  }

  function queue(scope, command) {
    return run(scope, ['commands', 'state'], 'readwrite', 'Fila local cancelada.', function (tx) {
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
      return function () { return command; };
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
    // A leitura e a escrita compartilham a transação com a fila: outra aba
    // não pode trocar a ficha entre a verificação e a gravação.
    return run(scope, ['state', 'commands'], 'readwrite', 'Plano local não foi salvo.', function (tx) {
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
      return function () { return saved; };
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
    return run(scope, 'state', 'readwrite', 'Lease local cancelado.', function (tx) {
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
      return function () { return granted; };
    });
  }

  function releaseLease(scope, owner) {
    return run(scope, 'state', 'readwrite', 'Lease local cancelado.', function (tx) {
      var store = tx.objectStore('state');
      var request = store.get('drain-lease');
      request.onsuccess = function () {
        if (request.result && request.result.owner === owner) store.delete('drain-lease');
      };
    });
  }

  window.CurvaGuidedOutbox = {
    queue: queue, list: list, remove: remove, save: save, restore: restore, clear: clear,
    savePlan: savePlan, restorePlan: restorePlan,
    mapSession: mapSession, lookupSession: lookupSession,
    acquireLease: acquireLease, releaseLease: releaseLease,
  };
}());
