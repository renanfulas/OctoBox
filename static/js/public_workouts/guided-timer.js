(function () {
  'use strict';

  function create(label) {
    var interval = null;
    var endAt = 0;
    var sessionId = null;

    function storageKey(id) { return 'curva-rest:' + id; }
    function read(id) {
      try { return Number(localStorage.getItem(storageKey(id)) || 0); } catch (_) { return 0; }
    }
    function write(id, value) {
      try { localStorage.setItem(storageKey(id), String(value)); } catch (_) {}
    }
    function remove(id) {
      try { localStorage.removeItem(storageKey(id)); } catch (_) {}
    }
    function paint() {
      clearInterval(interval);
      if (!sessionId) { label.hidden = true; return; }
      endAt = read(sessionId) || endAt;
      if (!endAt) { label.hidden = true; return; }
      label.hidden = false;
      function tick() {
        var remaining = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
        label.textContent = remaining
          ? 'Descanso · ' + Math.floor(remaining / 60) + ':' + String(remaining % 60).padStart(2, '0')
          : 'Descanso concluído';
        if (!remaining) {
          clearInterval(interval);
          endAt = 0;
          remove(sessionId);
        }
      }
      tick();
      interval = setInterval(tick, 1000);
    }
    return {
      attach: function (id) {
        if (sessionId !== id) endAt = 0;
        sessionId = id;
        paint();
      },
      start: function (seconds) {
        if (!sessionId || !seconds || seconds <= 0) return;
        endAt = Date.now() + seconds * 1000;
        write(sessionId, endAt);
        paint();
      },
      remap: function (oldId, newId) {
        var value = read(oldId) || endAt;
        remove(oldId);
        sessionId = newId;
        endAt = value;
        if (value) write(newId, value);
        paint();
      },
      stop: function () {
        clearInterval(interval);
        if (sessionId) remove(sessionId);
        sessionId = null;
        endAt = 0;
        label.hidden = true;
      },
    };
  }

  window.CurvaGuidedTimer = { create: create };
}());
