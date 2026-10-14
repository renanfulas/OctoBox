(function () {
  'use strict';

  function commandKey(payload) {
    return (payload.local_session_id || payload.session_id) + ':' + payload.action
      + (payload.movement_index == null ? '' : ':' + payload.movement_index + ':' + payload.set_number)
      + (payload.command_key ? ':' + payload.command_key : '');
  }

  function commandOrder(a, b) {
    return a.sequence != null && b.sequence != null
      ? a.sequence - b.sequence : a.created_at - b.created_at;
  }

  function create(options) {
    var outbox = options.outbox;
    var scope = options.scope;
    var request = options.request;
    var pending = new Set();
    var blockedCommand = null;
    var draining = false;
    var leaseOwner = options.newId();
    var leaseRenewal = null;
    var renewalInFlight = Promise.resolve();
    var leaseLost = false;

    function hydrate(commands) {
      pending = new Set(commands.map(function (item) { return item.key; }));
      blockedCommand = commands.find(function (item) { return item.blocked; }) || null;
      if (blockedCommand && options.onConflict) options.onConflict(blockedCommand);
    }

    function queue(payload) {
      var key = commandKey(payload);
      return outbox.queue(scope, { key: key, payload: payload, created_at: Date.now() }).then(function () {
        pending.add(key);
        return { queued: true };
      });
    }

    function deliver(payload) {
      if (pending.size && outbox && scope) {
        return queue(payload).then(function (result) { drain(); return result; });
      }
      return request('POST', payload).catch(function (error) {
        if (!error.retryable || !outbox || !scope) throw error;
        return queue(payload).then(function (result) {
          if (options.isOnline()) setTimeout(drain, 5000);
          return result;
        });
      });
    }

    function drain() {
      if (!outbox || !scope || draining || !options.isOnline()) return Promise.resolve();
      draining = true;
      var failed = false;
      var leaseGranted = false;
      var sawCommands = false;
      var hadPending = pending.size > 0;
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
        return outbox.list(scope);
      }).then(function (commands) {
        sawCommands = commands.length > 0;
        pending = new Set(commands.map(function (item) { return item.key; }));
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
            var sendPayload = Promise.resolve(command.payload);
            if (command.payload.action !== 'start' && command.payload.session_id) {
              sendPayload = outbox.lookupSession(scope, command.payload.session_id).then(function (mappedId) {
                return mappedId ? Object.assign({}, command.payload, { session_id: mappedId }) : command.payload;
              });
            }
            return sendPayload.then(function (payload) { return request('POST', payload); }).catch(function (error) {
              if (error.retryable || error.status === 401) throw error;
              command.blocked = true;
              command.error = error.message;
              command.error_status = error.status;
              blockedCommand = command;
              if (options.onConflict) options.onConflict(command);
              return outbox.queue(scope, command).then(function () { throw error; });
            }).then(function (result) {
              if (command.payload.action === 'start') {
                var localId = command.payload.local_session_id;
                return outbox.mapSession(scope, localId, result.session_id).then(function () {
                  if (options.onStartMapped) options.onStartMapped(localId, result.session_id);
                });
              }
            }).then(function () {
              return outbox.remove(scope, command.key).then(function () {
                pending.delete(command.key);
                if (['complete', 'partial', 'cancel'].indexOf(command.payload.action) !== -1) {
                  if (options.onEndConfirmed) options.onEndConfirmed();
                  return outbox.clear(scope);
                }
              });
            });
          });
        }, Promise.resolve());
      }).then(function () { return outbox.list(scope); }).then(function (remaining) {
        pending = new Set(remaining.map(function (item) { return item.key; }));
        if (!remaining.length && (sawCommands || options.hasActiveSession())) {
          return request('GET').then(function (result) {
            if (options.onRefreshed) return options.onRefreshed(result);
          });
        }
      }).then(function () {
        if (options.onDrained) options.onDrained({ cleared: !pending.size && (sawCommands || hadPending) });
      }).catch(function (error) {
        failed = true;
        if (!error.leaseBusy && options.onError) options.onError(error);
      }).finally(function () {
        if (leaseRenewal) clearInterval(leaseRenewal);
        leaseRenewal = null;
        return renewalInFlight.catch(function () {}).then(function () {
          return leaseGranted ? outbox.releaseLease(scope, leaseOwner) : null;
        }).catch(function () {}).then(function () {
          draining = false;
          if (!failed && leaseGranted) return outbox.list(scope).then(function (remaining) {
            if (remaining.length) drain();
          });
        }).catch(function () {});
      });
    }

    function removeBlocked() {
      if (!blockedCommand) return Promise.resolve();
      var command = blockedCommand;
      return outbox.remove(scope, command.key).then(function () {
        pending.delete(command.key);
        blockedCommand = null;
      });
    }

    function replaceBlocked(payload, newKey) {
      if (!blockedCommand) return Promise.reject(new Error('Conflito local não encontrado.'));
      var command = blockedCommand;
      var next = { key: newKey || commandKey(payload), payload: payload,
        created_at: command.created_at, sequence: command.sequence };
      return outbox.queue(scope, next).then(function () { return outbox.remove(scope, command.key); }).then(function () {
        pending.delete(command.key);
        pending.add(next.key);
        blockedCommand = null;
        return next;
      });
    }

    function forget(key) {
      return outbox.remove(scope, key).then(function () { pending.delete(key); });
    }

    function release() {
      if (leaseRenewal) clearInterval(leaseRenewal);
      leaseRenewal = null;
      if (!outbox || !scope) return Promise.resolve();
      return renewalInFlight.then(function () { return outbox.releaseLease(scope, leaseOwner); }).catch(function () {});
    }

    return { hydrate: hydrate, queue: queue, deliver: deliver, drain: drain,
      pendingCount: function () { return pending.size; }, blocked: function () { return blockedCommand; },
      removeBlocked: removeBlocked, replaceBlocked: replaceBlocked, forget: forget, release: release };
  }

  window.CurvaGuidedSync = { create: create, commandKey: commandKey, commandOrder: commandOrder };
}());
