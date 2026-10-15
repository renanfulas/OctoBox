/* Relógio do descanso do treino guiado.
 *
 * Guarda horário final e duração total por sessão no localStorage: recarregar,
 * abrir o vídeo do MuscleWiki ou minimizar não perde o descanso. Não desenha —
 * quem pinta é o anel (guided-ring.js) e o lançador, via onTick/onEnd.
 * Tempo, armazenamento e agendamento são injetáveis para os testes em Node.
 */
(function () {
  'use strict';

  var PREFIX = 'curva-rest:';

  function browserStorage() {
    try { return window.localStorage; } catch (_) { return null; }
  }

  function create(options) {
    options = options || {};
    var storage = options.storage === undefined ? browserStorage() : options.storage;
    var now = options.now || function () { return Date.now(); };
    var schedule = options.setTimeout || function (fn, ms) { return setTimeout(fn, ms); };
    var cancel = options.clearTimeout || function (id) { clearTimeout(id); };
    var onTick = options.onTick || function () {};
    var onEnd = options.onEnd || function () {};
    var sessionId = null;
    var state = null;
    var handle = null;

    function read(id) {
      try {
        var raw = storage && storage.getItem(PREFIX + id);
        if (!raw) return null;
        var parsed = JSON.parse(raw);
        if (typeof parsed === 'number') return { endAt: parsed, total: Math.max(1, Math.ceil((parsed - now()) / 1000)) };
        return parsed && parsed.endAt ? { endAt: Number(parsed.endAt), total: Number(parsed.total) || 1 } : null;
      } catch (_) { return null; }
    }
    function write(id, value) {
      try { if (storage) storage.setItem(PREFIX + id, JSON.stringify(value)); } catch (_) { /* armazenamento cheio ou bloqueado */ }
    }
    function remove(id) {
      try { if (storage) storage.removeItem(PREFIX + id); } catch (_) { /* idem */ }
    }

    function remainingMs() { return state ? Math.max(0, state.endAt - now()) : 0; }
    function seconds() { return Math.ceil(remainingMs() / 1000); }

    function loop() {
      cancel(handle);
      handle = null;
      if (!state) return;
      var remaining = remainingMs();
      if (remaining <= 0) {
        state = null;
        if (sessionId) remove(sessionId);
        onEnd();
        return;
      }
      onTick(Math.ceil(remaining / 1000));
      handle = schedule(loop, (remaining % 1000) || 1000);
    }

    function clear() {
      cancel(handle);
      handle = null;
      state = null;
      if (sessionId) remove(sessionId);
    }

    return {
      attach: function (id) {
        cancel(handle);
        sessionId = id;
        state = id ? read(id) : null;
        if (state && state.endAt <= now()) { state = null; remove(id); }
        loop();
      },
      start: function (totalSeconds) {
        if (!sessionId || !(totalSeconds > 0)) return;
        state = { endAt: now() + totalSeconds * 1000, total: totalSeconds };
        write(sessionId, state);
        loop();
      },
      add: function (extraSeconds) {
        if (!state) return;
        state = { endAt: state.endAt + extraSeconds * 1000, total: state.total + extraSeconds };
        if (sessionId) write(sessionId, state);
        loop();
      },
      skip: clear,
      stop: function () { clear(); sessionId = null; },
      resync: loop,
      remap: function (oldId, newId) {
        var value = read(oldId) || state;
        remove(oldId);
        sessionId = newId;
        state = value;
        if (value) write(newId, value);
        loop();
      },
      snapshot: function () {
        return state ? { endAt: state.endAt, total: state.total, remainingMs: remainingMs(), seconds: seconds() } : null;
      },
      isRunning: function () { return !!state && remainingMs() > 0; },
    };
  }

  window.CurvaGuidedTimer = { create: create };
}());
