(function () {
  'use strict';

  var parts = location.pathname.split('/').filter(Boolean);
  if (parts[0] !== 'renan' || !parts[1] || parts[1] === 'offline') return;
  var slug = parts[1];
  var outbox = window.CurvaGuidedOutbox;
  if (!outbox) return;
  var scope;
  try { scope = localStorage.getItem('curva-guided-scope:' + slug); } catch (_) {}
  if (!scope || scope.split(':').pop() !== slug) return;

  var openButton = document.querySelector('[data-offline-open]');
  var guide = document.querySelector('[data-offline-guide]');
  var empty = document.querySelector('[data-offline-empty]');
  var dayField = document.querySelector('[data-offline-day]');
  var step = document.querySelector('[data-offline-step]');
  var target = document.querySelector('[data-offline-target]');
  var weight = document.querySelector('[data-offline-weight]');
  var reps = document.querySelector('[data-offline-reps]');
  var rir = document.querySelector('[data-offline-rir]');
  var status = document.querySelector('[data-offline-status]');
  var startButton = document.querySelector('[data-offline-start]');
  var setButton = document.querySelector('[data-offline-set]');
  var skipButton = document.querySelector('[data-offline-skip]');
  var finishButton = document.querySelector('[data-offline-finish]');
  var partialButton = document.querySelector('[data-offline-partial]');
  var plan = null;
  var saved = null;
  var commands = [];
  var current = null;

  function newId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    var bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    var hex = Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, '0'); }).join('');
    return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
  }
  function itemKey(index, number) { return index + ':' + number; }
  function selectedDay() {
    return plan.days.find(function (day) { return day.day_id === dayField.value; });
  }
  function commandKey(payload) {
    return (payload.local_session_id || payload.session_id) + ':' + payload.action
      + (payload.movement_index == null ? '' : ':' + payload.movement_index + ':' + payload.set_number);
  }
  function enqueue(payload) {
    var command = { key: commandKey(payload), payload: payload, created_at: Date.now() };
    return outbox.queue(scope, command).then(function () {
      commands.push(command);
      return command;
    });
  }
  function save() { return outbox.save(scope, saved); }
  function paint() {
    var day = selectedDay();
    var active = !!saved && !!day && saved.day_id === day.day_id;
    startButton.hidden = active;
    dayField.disabled = active;
    if (!day) { step.textContent = 'Dia indisponível'; return; }
    current = null;
    if (active) {
      day.movements.some(function (movement, movementIndex) {
        return movement.series.some(function (series, index) {
          var address = itemKey(movementIndex, index + 1);
          if (saved.recorded.some(function (row) { return itemKey(row.movement_index, row.set_number) === address; })
              || saved.skipped.includes(address)) return false;
          current = { movement: movement, movementIndex: movementIndex,
            setNumber: index + 1, series: series };
          return true;
        });
      });
    }
    setButton.hidden = !active || !current;
    skipButton.hidden = !active || !current;
    partialButton.hidden = !active;
    if (!active) {
      finishButton.hidden = true;
      step.textContent = 'Ficha de ' + day.day_id;
      target.textContent = 'Inicie para guardar cada série neste aparelho.';
      document.querySelector('.fields').hidden = true;
      return;
    }
    document.querySelector('.fields').hidden = !current;
    var requiredMissing = day.movements.some(function (movement, movementIndex) {
      return movement.series.some(function (series, index) {
        return series.required && !saved.recorded.some(function (row) {
          return row.movement_index === movementIndex && row.set_number === index + 1;
        });
      });
    });
    finishButton.hidden = !active || requiredMissing || !saved.recorded.length;
    if (!current) {
      step.textContent = 'Séries previstas registradas';
      target.textContent = 'Finalize ou encerre como parcial.';
      return;
    }
    step.textContent = current.movement.label + ' · série ' + current.setNumber;
    target.textContent = (current.series.reps == null ? 'Registre o que realizou.'
      : 'Meta: ' + current.series.reps + (current.series.reps_max !== current.series.reps
        ? '–' + current.series.reps_max : '') + ' repetições.')
      + ' Salvo neste aparelho até a sincronização.';
    weight.closest('label').hidden = !current.movement.allowLoad;
    weight.value = current.series.weight_kg == null ? '' : current.series.weight_kg;
    reps.value = '';
    rir.value = '';
  }

  openButton.hidden = false;
  openButton.addEventListener('click', function () {
    Promise.all([outbox.restorePlan(scope), outbox.restore(scope), outbox.list(scope)])
      .then(function (items) {
        plan = items[0];
        saved = items[1];
        commands = items[2];
        if (!plan || plan.plan_slug !== slug || Date.now() - plan.saved_at > 7 * 86400000) {
          status.textContent = 'A ficha salva expirou. Abra o app com internet para atualizá-la.';
          guide.hidden = false;
          return;
        }
        if (saved && String(saved.program_version) !== String(plan.program_version)) {
          status.textContent = 'O treino salvo usa outra versão. Abra o app com internet ou exporte o rascunho.';
          guide.hidden = false;
          return;
        }
        if (commands.some(function (item) {
          return ['complete', 'partial', 'cancel'].includes(item.payload.action);
        })) {
          status.textContent = 'Encerramento salvo. Abra o app com internet para enviar a fila.';
          guide.hidden = false;
          return;
        }
        dayField.replaceChildren();
        plan.days.forEach(function (day) {
          var option = document.createElement('option');
          option.value = day.day_id;
          option.textContent = day.day_id;
          dayField.appendChild(option);
        });
        if (saved) dayField.value = saved.day_id;
        guide.hidden = false;
        empty.hidden = true;
        document.querySelector('main ul').hidden = true;
        openButton.hidden = true;
        status.textContent = 'Treino local aberto. Ao voltar a internet, abra o app nesta mesma conta.';
        paint();
      }).catch(function () { status.textContent = 'Não foi possível abrir o treino salvo.'; guide.hidden = false; });
  });
  dayField.addEventListener('change', paint);
  startButton.addEventListener('click', function () {
    if (!plan || !selectedDay()) return;
    startButton.disabled = true;
    var id = newId();
    var payload = { action: 'start', day_id: selectedDay().day_id, start_key: id,
      program_version: plan.program_version, local_session_id: id };
    enqueue(payload).then(function () {
      saved = { session_id: id, day_id: payload.day_id,
        program_version: plan.program_version, recorded: [], skipped: [] };
      return save();
    }).then(function () {
      status.textContent = 'Início salvo neste aparelho.';
      paint();
    }).catch(function () { status.textContent = 'Não foi possível salvar o início.'; })
      .finally(function () { startButton.disabled = false; });
  });
  setButton.addEventListener('click', function () {
    if (!saved || !current) return;
    if (current.series.reps != null && !reps.value) {
      status.textContent = 'Informe as repetições realizadas.'; return;
    }
    if (!weight.value && !reps.value && (current.movement.allowLoad || current.series.reps != null)) {
      status.textContent = 'Informe carga ou repetições.'; return;
    }
    setButton.disabled = true;
    var done = current;
    var payload = { action: 'set', session_id: saved.session_id,
      movement_slug: done.movement.slug, movement_index: done.movementIndex,
      set_number: done.setNumber, set_role: done.series.role,
      weight_kg: done.movement.allowLoad ? weight.value : '', reps: reps.value, rir: rir.value };
    enqueue(payload).then(function () {
      saved.recorded.push({ movement_index: done.movementIndex, set_number: done.setNumber,
        weight_kg: payload.weight_kg || null, reps: payload.reps || null, rir: payload.rir || null });
      return save();
    }).then(function () { status.textContent = 'Série salva neste aparelho.'; paint(); })
      .catch(function () { status.textContent = 'Falha ao salvar a série. Tente novamente.'; })
      .finally(function () { setButton.disabled = false; });
  });
  skipButton.addEventListener('click', function () {
    if (!saved || !current) return;
    skipButton.disabled = true;
    var skippedStep = current;
    enqueue({ action: 'skip', session_id: saved.session_id,
      movement_slug: skippedStep.movement.slug, movement_index: skippedStep.movementIndex,
      set_number: skippedStep.setNumber, set_role: skippedStep.series.role }).then(function () {
      saved.skipped.push(itemKey(skippedStep.movementIndex, skippedStep.setNumber));
      return save();
    }).then(function () { status.textContent = 'Série pulada neste aparelho.'; paint(); })
      .catch(function () { status.textContent = 'Falha ao salvar o pulo.'; })
      .finally(function () { skipButton.disabled = false; });
  });
  function finish(action) {
    if (!saved) return;
    enqueue({ action: action, session_id: saved.session_id }).then(function () {
      return outbox.clear(scope);
    }).then(function () {
      saved = null;
      status.textContent = 'Encerramento guardado. Abra o app com internet nesta mesma conta para enviar.';
      setButton.hidden = true;
      skipButton.hidden = true;
      finishButton.hidden = true;
      partialButton.hidden = true;
      startButton.hidden = true;
    }).catch(function () { status.textContent = 'Falha ao salvar o encerramento.'; });
  }
  finishButton.addEventListener('click', function () { finish('complete'); });
  partialButton.addEventListener('click', function () { finish('partial'); });
  document.querySelector('[data-offline-export]').addEventListener('click', function () {
    outbox.list(scope).then(function (rows) {
      var data = JSON.stringify({ exported_at: new Date().toISOString(), scope: scope,
        plan: plan, state: saved, commands: rows }, null, 2);
      var url = URL.createObjectURL(new Blob([data], { type: 'application/json' }));
      var link = document.createElement('a');
      link.href = url;
      link.download = 'curva-treino-offline.json';
      link.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }).catch(function () { status.textContent = 'Não foi possível exportar.'; });
  });
  document.querySelector('[data-offline-delete]').addEventListener('click', function () {
    if (!window.confirm('Apagar a ficha e todos os registros pendentes deste aparelho? Esta ação não pode ser desfeita.')) return;
    var request = indexedDB.deleteDatabase('curva-guided:' + scope);
    request.onsuccess = function () {
      try { localStorage.removeItem('curva-guided-scope:' + slug); } catch (_) {}
      location.reload();
    };
    request.onerror = function () { status.textContent = 'Não foi possível apagar os dados locais.'; };
    request.onblocked = function () { status.textContent = 'Feche outras abas do Curva e tente novamente.'; };
  });
  window.addEventListener('online', function () {
    status.textContent = 'Conexão disponível. Abra /renan/' + slug + ' para enviar os registros.';
  });
}());
