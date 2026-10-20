(function () {
  'use strict';

  // Com `writeAhead`, estes comandos vão para a fila IndexedDB antes do envio:
  // a série sobrevive a uma aba fechada logo depois do toque.
  var WRITE_AHEAD = ['set', 'skip', 'unskip'];
  // Recibos que não mudam a sessão além do que o cliente já pintou. Drenar só
  // estes não pede GET /sessao, para manter 1 requisição por série online.
  var SIMPLE = ['set', 'skip', 'unskip', 'correct'];

  function commandKey(payload) {
    return (payload.local_session_id || payload.session_id) + ':' + payload.action
      + (payload.movement_index == null ? '' : ':' + payload.movement_index + ':' + payload.set_number)
      + (payload.command_key ? ':' + payload.command_key : '');
  }

  function commandOrder(a, b) {
    return a.sequence != null && b.sequence != null
      ? a.sequence - b.sequence : a.created_at - b.created_at;
  }

  function blank(value) { return value === '' || value == null ? null : value; }

  // A fila guarda o que o servidor ainda não confirmou, inclusive a série gravada
  // antes do envio quando a aba fechou antes do snapshot. Ela vence até drenar.
  function applyQueued(session, commands) {
    var recorded = new Map((session.recorded || []).map(function (item) {
      return [item.movement_index + ':' + item.set_number, item];
    }));
    var skipped = new Set(session.skipped || []);
    commands.slice().sort(commandOrder).forEach(function (item) {
      var payload = item.payload;
      if (payload.movement_index == null) return;
      var setKey = payload.movement_index + ':' + payload.set_number;
      if (payload.action === 'set' || payload.action === 'correct') {
        var entry = {
          movement_index: payload.movement_index, set_number: payload.set_number,
          weight_kg: blank(payload.weight_kg), reps: blank(payload.reps), rir: blank(payload.rir),
        };
        // Isometria: o tempo sustentado só existe em série por tempo.
        if (blank(payload.duration_seconds) !== null) entry.duration_seconds = blank(payload.duration_seconds);
        recorded.set(setKey, entry);
      }
      if (payload.action === 'skip') skipped.add(setKey);
      if (payload.action === 'unskip') skipped.delete(setKey);
    });
    return Object.assign({}, session, { recorded: Array.from(recorded.values()), skipped: Array.from(skipped) });
  }

  function create(options) {
    var outbox = options.outbox;
    var scope = options.scope;
    var request = options.request;
    var writeAhead = !!options.writeAhead;
    var pending = new Set();
    // Chaves gravadas online pelo write-ahead e ainda não recusadas: não são atraso.
    var fresh = new Set();
    var blockedCommand = null;
    var draining = false;
    var active = 0;
    var inFlight = Promise.resolve();
    var refreshWanted = false;
    // Versão de cada gravação: uma lista tirada antes dela não pode apagá-la de `pending`.
    var version = 0;
    var queuedAt = new Map();
    var leaseOwner = options.newId();
    var leaseRenewal = null;
    var renewalInFlight = Promise.resolve();
    var leaseLost = false;

    function hydrate(commands) {
      pending = new Set(commands.map(function (item) { return item.key; }));
      blockedCommand = commands.find(function (item) { return item.blocked; }) || null;
      if (blockedCommand && options.onConflict) options.onConflict(blockedCommand);
    }

    function queue(payload, viaWriteAhead) {
      var key = commandKey(payload);
      return outbox.queue(scope, { key: key, payload: payload, created_at: Date.now() }).then(function () {
        pending.add(key);
        queuedAt.set(key, ++version);
        if (viaWriteAhead === true && options.isOnline()) fresh.add(key);
        else fresh.delete(key);
        return { queued: true };
      });
    }

    function post(payload) {
      return request('POST', payload).catch(function (error) {
        if (!error.retryable || !outbox || !scope) throw error;
        return queue(payload).then(function (result) {
          if (options.isOnline()) setTimeout(drain, 5000);
          return result;
        });
      });
    }

    // `drained`: já esperamos a fila esvaziar uma vez; se ainda sobrou pendência,
    // o comando entra na fila em vez de esperar de novo (sem laço).
    function deliver(payload, drained) {
      if (writeAhead && outbox && scope) {
        if (WRITE_AHEAD.indexOf(payload.action) !== -1) {
          return queue(payload, true).then(function () {
            run(false);
            return { queued: true, local: true };
          }, function () { return post(payload); });
        }
        // Encerrar ou corrigir logo depois de uma série espera o envio dela,
        // em vez de cair na fila e parecer offline. Se nenhuma drenagem está
        // ativa (a anterior acabou de terminar ou foi recusada por `draining`),
        // dispara uma agora; sem isso o encerramento ficava "pendente de envio"
        // mesmo com a rede de pé.
        if (!drained && pending.size && (active || options.isOnline())) {
          return (active ? idle() : run(false)).then(function () { return deliver(payload, true); });
        }
      }
      if (pending.size && outbox && scope) {
        return queue(payload).then(function (result) { run(!writeAhead); return result; });
      }
      return post(payload);
    }

    function drain() { return run(true); }

    function settle(key) {
      pending.delete(key);
      fresh.delete(key);
      queuedAt.delete(key);
    }

    // Sincroniza `pending` com a fila sem perder o que foi gravado depois da leitura.
    function listPending() {
      var at = version;
      return outbox.list(scope).then(function (commands) {
        pending = new Set(commands.map(function (item) { return item.key; }));
        queuedAt.forEach(function (queued, key) { if (queued > at) pending.add(key); });
        return commands;
      });
    }

    function idle() {
      return active ? inFlight.then(idle) : Promise.resolve();
    }

    // refresh = false: drenagem disparada pelo write-ahead; só pede GET /sessao
    // quando houve atraso, `start`, encerramento ou um refresh pedido no meio.
    function run(refresh) {
      if (!outbox || !scope || !options.isOnline()) return Promise.resolve();
      if (draining) {
        if (refresh && writeAhead) refreshWanted = true;
        return Promise.resolve();
      }
      draining = true;
      active += 1;
      inFlight = drainOnce(refresh).finally(function () { active -= 1; });
      return inFlight;
    }

    function drainOnce(refresh) {
      var failed = false;
      var leaseGranted = false;
      var sawCommands = false;
      var hadPending = pending.size > 0;
      var backlog = Array.from(pending).some(function (key) { return !fresh.has(key); });
      var changedSession = false;
      leaseLost = false;
      return outbox.acquireLease(scope, leaseOwner, 12000).then(function (granted) {
        leaseGranted = granted;
        if (!granted) {
          setTimeout(drain, 3000);
          var busy = new Error('Outra aba está enviando a fila.');
          busy.leaseBusy = true;
          throw busy;
        }
        leaseRenewal = setInterval(function () {
          renewalInFlight = renewalInFlight.then(function () {
            return outbox.acquireLease(scope, leaseOwner, 12000);
          }).then(function (renewed) {
            if (!renewed) leaseLost = true;
          }).catch(function () { leaseLost = true; });
        }, 4000);
        return listPending();
      }).then(function (commands) {
        sawCommands = commands.length > 0;
        backlog = backlog || commands.some(function (item) { return !fresh.has(item.key); });
        commands.sort(commandOrder);
        return commands.reduce(function (chain, command) {
          return chain.then(function () {
            if (leaseLost) {
              var lost = new Error('Outra aba assumiu o envio.');
              lost.retryable = true;
              throw lost;
            }
            if (command.blocked) {
              blockedCommand = command;
              if (options.onConflict) options.onConflict(command);
              throw new Error(command.error || 'Registro pendente precisa de ação.');
            }
            var sent = command.payload;
            var response;
            var sendPayload = Promise.resolve(command.payload);
            if (command.payload.action !== 'start' && command.payload.session_id) {
              sendPayload = outbox.lookupSession(scope, command.payload.session_id).then(function (mappedId) {
                return mappedId ? Object.assign({}, command.payload, { session_id: mappedId }) : command.payload;
              });
            }
            return sendPayload.then(function (payload) { sent = payload; return request('POST', payload); }).catch(function (error) {
              if (error.retryable || error.status === 401) throw error;
              command.blocked = true;
              command.error = error.message;
              command.error_status = error.status;
              blockedCommand = command;
              fresh.delete(command.key);
              if (options.onConflict) options.onConflict(command);
              return outbox.queue(scope, command).then(function () { throw error; });
            }).then(function (result) {
              response = result;
              if (SIMPLE.indexOf(command.payload.action) === -1) changedSession = true;
              if (command.payload.action === 'start') {
                var localId = command.payload.local_session_id;
                return outbox.mapSession(scope, localId, result.session_id).then(function () {
                  if (options.onStartMapped) options.onStartMapped(localId, result.session_id);
                });
              }
            }).then(function () {
              return outbox.remove(scope, command.key).then(function () {
                settle(command.key);
                if (options.onSent) options.onSent(sent, response);
                if (['complete', 'partial', 'cancel'].indexOf(command.payload.action) !== -1) {
                  if (options.onEndConfirmed) options.onEndConfirmed();
                  return outbox.clear(scope);
                }
              });
            });
          });
        }, Promise.resolve());
      }).then(listPending).then(function () {
        if (pending.size || !(refresh || refreshWanted || backlog || changedSession)) return;
        refreshWanted = false;
        if (sawCommands || options.hasActiveSession()) {
          return request('GET').then(function (result) {
            if (options.onRefreshed) return options.onRefreshed(result);
          });
        }
      }).then(function () {
        if (options.onDrained) {
          options.onDrained({ cleared: !pending.size && (sawCommands || hadPending), backlog: backlog });
        }
      }).catch(function (error) {
        failed = true;
        if (error.leaseBusy) return;
        // O que falhou deixa de ser recém-gravado: vira atraso a reenviar.
        fresh.clear();
        if (!refresh && error.retryable && options.isOnline()) setTimeout(drain, 5000);
        if (options.onError) options.onError(error);
      }).finally(function () {
        if (leaseRenewal) clearInterval(leaseRenewal);
        leaseRenewal = null;
        return renewalInFlight.catch(function () {}).then(function () {
          return leaseGranted ? outbox.releaseLease(scope, leaseOwner) : null;
        }).catch(function () {}).then(function () {
          draining = false;
          if (!failed && leaseGranted) return listPending().then(function () {
            if (pending.size || refreshWanted) run(!writeAhead || refreshWanted);
          });
        }).catch(function () {});
      });
    }

    function removeBlocked() {
      if (!blockedCommand) return Promise.resolve();
      var command = blockedCommand;
      return outbox.remove(scope, command.key).then(function () {
        settle(command.key);
        blockedCommand = null;
      });
    }

    function replaceBlocked(payload, newKey) {
      if (!blockedCommand) return Promise.reject(new Error('Conflito local não encontrado.'));
      var command = blockedCommand;
      var next = { key: newKey || commandKey(payload), payload: payload,
        created_at: command.created_at, sequence: command.sequence };
      return outbox.queue(scope, next).then(function () { return outbox.remove(scope, command.key); }).then(function () {
        settle(command.key);
        pending.add(next.key);
        queuedAt.set(next.key, ++version);
        blockedCommand = null;
        return next;
      });
    }

    function forget(key) {
      return outbox.remove(scope, key).then(function () { settle(key); });
    }

    function release() {
      if (leaseRenewal) clearInterval(leaseRenewal);
      leaseRenewal = null;
      if (!outbox || !scope) return Promise.resolve();
      return renewalInFlight.then(function () { return outbox.releaseLease(scope, leaseOwner); }).catch(function () {});
    }

    return { hydrate: hydrate, queue: queue, deliver: deliver, drain: drain, idle: idle,
      pendingCount: function () { return pending.size; },
      backlogCount: function () {
        return Array.from(pending).filter(function (key) { return !fresh.has(key); }).length;
      },
      blocked: function () { return blockedCommand; },
      removeBlocked: removeBlocked, replaceBlocked: replaceBlocked, forget: forget, release: release };
  }

  window.CurvaGuidedSync = { create: create, commandKey: commandKey, commandOrder: commandOrder, applyQueued: applyQueued };
}());
