/* Controlador do treino guiado Curva.
 *
 * Dono da sessão: comandos (start/set/skip/unskip/correct/complete/partial/cancel),
 * fila offline (CurvaGuidedSync), cursor do "Ver treino todo" e relógio do descanso.
 * Não pinta a execução: monta um view model e entrega ao modo foco
 * (CurvaGuidedFocus), que avisa as ações por eventos `guided:*`.
 * Regras puras ficam em guided-state.js; textos em guided-format.js.
 */
(function () {
  'use strict';

  var root = document.querySelector('[data-workout-guided]');
  var dialog = document.querySelector('[data-guided-focus]');
  if (!root || !dialog) return;
  var panel = root.closest('[data-workout-tab-panel]');
  var startButton = root.querySelector('[data-workout-guided-start]');
  var resumeButton = root.querySelector('[data-guided-resume]');
  var status = root.querySelector('[data-workout-guided-status]');
  var launchTitle = root.querySelector('[data-guided-launch-title]');
  var launchText = root.querySelector('[data-guided-launch-text]');
  var launchMeta = root.querySelector('[data-guided-launch-meta]');
  var conflictPanel = root.querySelector('[data-workout-guided-conflict]');
  var conflictMessage = root.querySelector('[data-workout-guided-conflict-message]');
  var conflictExport = root.querySelector('[data-workout-guided-conflict-export]');
  var conflictServer = root.querySelector('[data-workout-guided-conflict-server]');
  var conflictCorrect = root.querySelector('[data-workout-guided-conflict-correct]');
  var format = window.CurvaGuidedFormat;
  var focus = window.CurvaGuidedFocus.create(dialog);
  var scope = root.dataset.accountScope && document.body.dataset.planSlug
    ? root.dataset.accountScope + ':' + document.body.dataset.planSlug : '';
  var outbox = window.CurvaGuidedOutbox;
  var request = window.CurvaGuidedApi.create(root.dataset.sessionUrl, root.dataset.accountScope);
  var key = window.CurvaGuidedState.key;

  var sessionId = null;
  var movements = [];
  var recorded = new Set();
  var recordedDetails = new Map();
  var setSync = new Map();
  var skipped = new Set();
  var lastFreeformIndex = null;
  var lastSkipped = null;
  var focusIndex = null;
  var reviewIndex = null;
  var screen = 'exercise';
  var receiptKey = null;
  var startedAt = null;
  var startLocal = false;
  var dayTitle = '';
  var ended = null;

  var timer = window.CurvaGuidedTimer.create({
    onTick: function () {
      var rest = restModel();
      if (rest) focus.restTick(rest);
      paintLauncher();
    },
    onEnd: restEnded,
  });

  var sync = window.CurvaGuidedSync.create({
    outbox: outbox, scope: scope, request: request, newId: newId,
    isOnline: function () { return navigator.onLine; },
    hasActiveSession: function () { return !!sessionId; },
    onConflict: showConflict,
    onStartMapped: function (localId, serverId) {
      if (sessionId === localId) {
        sessionId = serverId;
        startLocal = false;
        snapshot();
        timer.remap(localId, serverId);
        render();
      }
    },
    onEndConfirmed: function () {
      sessionId = null;
      startButton.disabled = false;
      paintLauncher();
    },
    onRefreshed: function (result) {
      if (result.session) activate(result.session);
      else if (sessionId) {
        sessionId = null;
        timer.stop();
        if (focus.isOpen() && screen !== 'finished') focus.close();
        startButton.disabled = false;
        paintLauncher();
        return outbox.clear(scope);
      }
    },
    onDrained: function (result) {
      if (result.cleared) {
        startLocal = false;
        setSync.forEach(function (value, setKey) { if (value === 'local') setSync.set(setKey, 'saved'); });
        status.textContent = 'Tudo enviado ao Curva.';
        if (focus.isOpen()) focus.toast('Tudo enviado ao Curva');
      }
      render();
    },
    onError: function (error) {
      status.textContent = error.status === 401 ? 'Entre novamente na mesma conta para enviar o treino.'
        : (error.retryable ? 'Envio pendente. Tentaremos novamente quando a conexão voltar.'
          : 'Envio pendente: ' + error.message);
    },
  });
  var commandOrder = window.CurvaGuidedSync.commandOrder;
  var deliver = sync.deliver;
  var drain = sync.drain;

  function stored(storage, method, name, value) {
    try { return storage[method](name, value); } catch (_) { return null; }
  }

  function newId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    var bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    var hex = Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, '0'); }).join('');
    return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
  }

  function startKey(dayId) { return 'curva-start:' + location.pathname + ':' + dayId; }

  /* ---------- estado e view model ---------- */
  function project() {
    return window.CurvaGuidedState.project(
      movements, recorded, skipped, sync.pendingCount(), lastSkipped, lastFreeformIndex, { focusIndex: focusIndex }
    );
  }

  function restModel() {
    var rest = timer.snapshot();
    return rest ? {
      seconds: rest.seconds, remainingMs: rest.remainingMs, totalMs: rest.total * 1000,
      token: rest.endAt - rest.total * 1000,
    } : null;
  }

  function lastRecordedKey() {
    var keys = Array.from(recorded);
    return keys.length ? keys[keys.length - 1] : null;
  }

  function syncText() {
    if (startLocal) return 'Treino iniciado neste aparelho · confirmamos ao voltar a internet';
    var pending = sync.pendingCount();
    if (!pending) return '';
    return pending + (pending > 1 ? ' registros aguardando' : ' registro aguardando') + ' envio · ficam salvos neste aparelho';
  }

  function elapsedMinutes() {
    return Math.max(1, Math.round((Date.now() - (startedAt || Date.now())) / 60000));
  }

  function reviewModel(state) {
    if (reviewIndex === null || !movements[reviewIndex]) return null;
    var movement = movements[reviewIndex];
    var item = state.overview[reviewIndex];
    var statusText = 'Concluído · ' + item.done + ' de ' + item.total + (item.total === 1 ? ' série' : ' séries');
    if (item.status === 'skipped') statusText = 'Exercício pulado';
    else if (item.status === 'incomplete') statusText = item.done + ' de ' + item.total + ' séries · ' + item.skipped + (item.skipped > 1 ? ' puladas' : ' pulada');
    else if (item.status !== 'done') statusText = item.done + ' de ' + item.total + ' séries';
    var extra = null;
    if (movement.freeform && item.status === 'done' && movement.series.length < 30) extra = { action: 'freeform', label: 'Adicionar outra série' };
    else if (item.status === 'done' && item.firstPending) extra = { action: 'optional', label: 'Fazer a série opcional' };
    else if (item.skipped) extra = { action: 'redo', label: 'Fazer as séries puladas agora' };
    return {
      movement: movement, status: item.status, statusText: statusText, extra: extra,
      nextLabel: state.next ? movements[state.next.movementIndex].label : '',
      sets: movement.series.map(function (series, index) {
        var setKey = key(reviewIndex, index + 1);
        var entry = recorded.has(setKey) ? (recordedDetails.get(setKey) || {}) : null;
        return {
          key: setKey, label: format.setShortLabel(movement, index + 1), entry: entry,
          valueText: entry ? format.valueText(movement, entry) : (skipped.has(setKey) ? 'Pulada' : (series.required ? 'Pendente' : 'Opcional')),
        };
      }),
    };
  }

  function summaryModel(state) {
    var freeformMissing = state.overview.some(function (item, index) { return movements[index].freeform && item.done === 0; });
    var missing = state.missing + (freeformMissing ? 1 : 0);
    return {
      title: !missing ? 'Treino concluído'
        : (state.missing === 1 || (!state.missing && freeformMissing) ? 'Falta 1 série obrigatória' : 'Faltam ' + missing + ' séries obrigatórias'),
      minutes: elapsedMinutes(), sets: state.recordedCount,
      doneMovements: state.overview.filter(function (item) { return item.status === 'done'; }).length,
      totalMovements: state.overview.length,
      canFinish: state.canFinish && !freeformMissing,
      hasPending: !!state.next,
    };
  }

  function viewModel() {
    var state = project();
    var receiptMovement = receiptKey ? movements[Number(receiptKey.split(':')[0])] : null;
    var progressIndex = screen === 'review' && reviewIndex !== null ? reviewIndex
      : (state.current ? state.current.movementIndex : (receiptMovement ? movements.indexOf(receiptMovement) : null));
    return {
      movements: movements, state: state, current: state.current, recordedDetails: recordedDetails,
      dayTitle: dayTitle, progressIndex: progressIndex, rest: restModel(), syncText: syncText(),
      lastRecordedKey: lastRecordedKey(),
      receipt: receiptMovement && recordedDetails.has(receiptKey) ? {
        movement: receiptMovement, entry: recordedDetails.get(receiptKey), sync: setSync.get(receiptKey) || 'saved',
        canAddFreeform: receiptMovement.freeform && receiptMovement.series.length < 30,
      } : null,
      review: screen === 'review' ? reviewModel(state) : null,
      summary: summaryModel(state),
      finished: ended,
    };
  }

  function render() {
    paintLauncher();
    if (!focus.isOpen() || focus.screen() === 'countdown') return;
    var vm = viewModel();
    if (screen === 'exercise' && !vm.current) screen = 'summary';
    if (screen === 'rest' && !vm.rest) screen = vm.current ? 'exercise' : 'summary';
    if (screen === 'review' && !vm.review) screen = vm.current ? 'exercise' : 'summary';
    focus.show(screen, vm);
  }

  function openFocus(nextScreen) {
    screen = nextScreen;
    var vm = viewModel();
    focus.show(screen, vm);
    render();
  }

  function paintLauncher() {
    var state = movements.length ? project() : null;
    var rest = timer.snapshot();
    // Sinal lido pelo widget de carga da grade (load_tracker.js): com sessão guiada
    // aberta, a série é registrada pelo guia para não duplicar o LoadLog.
    root.toggleAttribute('data-guided-session-active', !!sessionId);
    if (sessionId) {
      var index = state && state.current ? state.current.movementIndex + 1 : movements.length;
      launchTitle.textContent = 'Treino em andamento';
      launchText.textContent = dayTitle ? dayTitle + ' · continue de onde parou.' : 'Continue de onde parou.';
      launchMeta.hidden = false;
      launchMeta.textContent = 'Exercício ' + index + ' de ' + movements.length + ' · '
        + (state ? state.recordedCount + ' de ' + state.total + ' séries' : '')
        + (rest ? ' · descanso ' + format.clock(rest.seconds) : '');
      startButton.hidden = true;
      resumeButton.hidden = false;
      return;
    }
    launchTitle.textContent = 'Treino guiado';
    launchText.textContent = 'Uma série por vez, com a carga sugerida e o descanso cronometrado.';
    launchMeta.hidden = true;
    startButton.hidden = false;
    resumeButton.hidden = true;
  }

  function snapshot() {
    if (!sessionId || !outbox) return Promise.resolve();
    return outbox.save(scope, {
      session_id: sessionId, day_id: selectedDayId(), program_version: root.dataset.programVersion,
      started_at: startedAt ? new Date(startedAt).toISOString() : null,
      focus_movement_index: focusIndex,
      recorded: Array.from(recorded, function (item) {
        var parts = item.split(':');
        return Object.assign({ movement_index: Number(parts[0]), set_number: Number(parts[1]) }, recordedDetails.get(item) || {});
      }),
      skipped: Array.from(skipped),
    });
  }

  /* ---------- conflito da fila ---------- */
  function showConflict(command) {
    conflictPanel.hidden = false;
    conflictMessage.textContent = command.error || 'O servidor não aceitou este registro.';
    conflictCorrect.hidden = command.payload.action !== 'set' || command.error_status !== 409;
    conflictServer.textContent = command.payload.action === 'start'
      ? 'Exportar e abrir a ficha atual' : 'Usar registro do servidor';
    if (focus.isOpen()) {
      focus.toast('Um registro precisa de atenção', 'Resolver', function () {
        minimize();
        conflictPanel.scrollIntoView({ block: 'center' });
      }, true);
    }
  }

  function exportDraft() {
    return outbox.list(scope).then(function (commands) {
      var data = JSON.stringify({ exported_at: new Date().toISOString(), scope: scope, commands: commands }, null, 2);
      var url = URL.createObjectURL(new Blob([data], { type: 'application/json' }));
      var link = document.createElement('a');
      link.href = url;
      link.download = 'curva-treino-pendente.json';
      link.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      return commands;
    });
  }

  conflictExport.addEventListener('click', function () {
    exportDraft().catch(function () { status.textContent = 'Não foi possível exportar o rascunho local.'; });
  });

  conflictServer.addEventListener('click', function () {
    var command = sync.blocked();
    if (!command) return;
    var question = command.payload.action === 'start'
      ? 'Exportar o rascunho, descartar esta fila e abrir a ficha atual?'
      : 'Descartar este comando local e usar o registro do servidor?';
    if (!window.confirm(question)) return;
    if (command.payload.action === 'start') {
      var localId = command.payload.local_session_id;
      exportDraft().then(function (commands) {
        var sameSession = commands.filter(function (item) {
          return item.payload.local_session_id === localId || item.payload.session_id === localId;
        });
        return sameSession.reduce(function (chain, item) {
          return chain.then(function () { return sync.forget(item.key); });
        }, Promise.resolve());
      }).then(function () { return outbox.clear(scope); }).then(function () {
        location.reload();
      }).catch(function () {
        status.textContent = 'Não foi possível exportar e limpar a fila. Seus dados locais foram preservados.';
      });
      return;
    }
    sync.removeBlocked().then(function () {
      conflictPanel.hidden = true;
      return request('GET');
    }).then(function (result) {
      if (result.session) activate(result.session);
      return snapshot();
    }).then(drain).catch(function (error) { status.textContent = error.message; });
  });

  conflictCorrect.addEventListener('click', function () {
    var command = sync.blocked();
    if (!command || command.payload.action !== 'set') return;
    var replacement = Object.assign({}, command.payload, { action: 'correct', command_key: newId() });
    sync.replaceBlocked(replacement).then(function () {
      conflictPanel.hidden = true;
      status.textContent = 'Correção preparada; enviando em ordem.';
      return drain();
    }).catch(function (error) { status.textContent = error.message; });
  });

  /* ---------- ficha do dia ---------- */
  function selectedDayId() {
    var tab = panel.querySelector('.workout-day-tab.is-active');
    return tab ? (tab.getAttribute('aria-controls') || '').replace(/^workout-day-/, '') : '';
  }

  function dayLabel(dayId) {
    var tab = panel.querySelector('[data-workout-tab-target="workout-day-' + dayId + '"]');
    if (!tab) return '';
    var day = tab.querySelector('.workout-day-tab__day');
    var keyword = tab.querySelector('.workout-day-tab__keyword');
    return [day && day.textContent.trim(), keyword && keyword.textContent.trim()].filter(Boolean).join(' · ');
  }

  function buildMovements(dayId) {
    var day = document.getElementById('workout-day-' + dayId);
    if (!day) return [];
    return Array.prototype.map.call(day.querySelectorAll('.workout-movement-card'), function (card) {
      var series = [];
      try { series = JSON.parse(card.dataset.guidedSeries || '[]'); } catch (_) { series = []; }
      var heading = card.querySelector('.workout-movement-copy strong');
      return {
        slug: card.dataset.movementSlug,
        label: card.dataset.movementLabel || (heading ? heading.textContent.trim() : 'Exercício'),
        referenceUrl: card.dataset.referenceUrl || '',
        rirSpec: card.dataset.rirSpec || '',
        loadKind: card.dataset.loadKind, loadStep: 2.5,
        allowLoad: card.dataset.allowLoadRegistration !== 'false',
        series: series, freeform: series.length === 1 && series[0].role === 'legacy_unknown',
      };
    }).filter(function (movement) { return movement.series.length > 0; });
  }

  function saveOfflinePlan() {
    if (!outbox || !scope || !root.dataset.programVersion) return;
    var dayTabs = panel.querySelectorAll('.workout-day-tab[aria-controls]');
    var days = Array.prototype.map.call(dayTabs, function (tab) {
      var dayId = (tab.getAttribute('aria-controls') || '').replace(/^workout-day-/, '');
      return { day_id: dayId, movements: buildMovements(dayId) };
    }).filter(function (day) { return day.day_id && day.movements.length; });
    if (!days.length) return;
    outbox.savePlan(scope, {
      plan_slug: document.body.dataset.planSlug,
      program_version: root.dataset.programVersion,
      session_url: root.dataset.sessionUrl,
      saved_at: Date.now(), days: days,
    }).then(function () {
      stored(localStorage, 'setItem', 'curva-guided-scope:' + document.body.dataset.planSlug, scope);
    }).catch(function () {});
  }

  /* ---------- sessão ---------- */
  function resumeScreen() {
    if (timer.isRunning()) return 'rest';
    if (screen === 'review' && reviewIndex !== null) return 'review';
    return project().next ? 'exercise' : 'summary';
  }

  function activate(session, options) {
    options = options || {};
    if (session.ended_at || session.completed_at) {
      stored(sessionStorage, 'removeItem', startKey(session.day_id));
      status.textContent = 'Este treino já foi concluído.';
      startButton.disabled = false;
      if (options.open) focus.close();
      return;
    }
    if (String(session.program_version) !== root.dataset.programVersion) {
      stored(sessionStorage, 'removeItem', startKey(session.day_id));
      status.textContent = 'O programa foi atualizado. Comece um treino com a versão atual.';
      startButton.disabled = false;
      if (options.open) focus.close();
      return;
    }
    var tab = panel.querySelector('[data-workout-tab-target="workout-day-' + session.day_id + '"]');
    if (tab && !tab.classList.contains('is-active')) tab.click();
    var sameSession = sessionId === session.session_id;
    movements = buildMovements(session.day_id);
    if (!movements.length) {
      status.textContent = 'Não foi possível montar este treino. Atualize a página.';
      startButton.disabled = false;
      if (options.open) focus.close();
      return;
    }
    sessionId = session.session_id;
    dayTitle = dayLabel(session.day_id);
    startedAt = Date.parse(session.started_at || '') || startedAt || Date.now();
    recorded = new Set((session.recorded || []).map(function (item) {
      return key(item.movement_index, item.set_number);
    }));
    recordedDetails = new Map((session.recorded || []).map(function (item) {
      return [key(item.movement_index, item.set_number), {
        weight_kg: item.weight_kg, reps: item.reps, rir: item.rir,
      }];
    }));
    recorded.forEach(function (setKey) { if (!setSync.has(setKey)) setSync.set(setKey, 'saved'); });
    skipped = new Set(session.skipped || []);
    lastSkipped = Array.from(skipped).pop() || null;
    lastFreeformIndex = null;
    movements.forEach(function (movement, index) {
      if (!movement.freeform) return;
      var performed = Array.from(recorded).filter(function (item) { return item.indexOf(index + ':') === 0; });
      if (performed.length) lastFreeformIndex = index;
      var maximum = Math.max.apply(null, [1].concat(performed.concat(Array.from(skipped).filter(function (item) {
        return item.indexOf(index + ':') === 0;
      })).map(function (item) { return Number(item.split(':')[1]); })));
      while (movement.series.length < maximum) {
        movement.series.push(Object.assign({}, movement.series[0], { set_number: movement.series.length + 1 }));
      }
    });
    if (!sameSession) {
      focusIndex = session.focus_movement_index != null && movements[session.focus_movement_index] ? session.focus_movement_index : null;
      reviewIndex = null;
      receiptKey = null;
      ended = null;
      timer.attach(sessionId);
      status.textContent = recorded.size ? 'Sessão retomada. Continue de onde parou.' : 'Sessão iniciada. Registre cada série para avançar.';
    }
    startButton.disabled = false;
    if (options.open) openFocus(resumeScreen());
    else render();
    snapshot().catch(function () { status.textContent = 'Armazenamento local indisponível; mantenha conexão para registrar.'; });
  }

  function startSession() {
    var dayId = selectedDayId();
    if (!dayId) { status.textContent = 'Escolha um dia de treino para começar.'; return; }
    var preview = buildMovements(dayId);
    if (!preview.length) { status.textContent = 'Este dia ainda não tem séries guiáveis.'; return; }
    var keyName = startKey(dayId);
    var id = stored(sessionStorage, 'getItem', keyName) || newId();
    stored(sessionStorage, 'setItem', keyName, id);
    startButton.disabled = true;
    ended = null;
    screen = 'exercise';
    var startPayload = {
      action: 'start', day_id: dayId, start_key: id,
      program_version: root.dataset.programVersion, local_session_id: id,
    };
    // O POST sai no toque; os ~3 s da contagem cobrem a latência do início.
    var settled = false;
    var started = request('POST', startPayload).then(
      function (session) { settled = true; return { session: session }; },
      function (error) { settled = true; return { error: error }; }
    );
    focus.countdown(preview[0].label).then(function () {
      if (settled) return started;
      focus.countdownHint('Conectando ao Curva…');
      var timeout = new Promise(function (resolve) {
        setTimeout(function () {
          var error = new Error('Sem resposta do servidor.');
          error.retryable = true;
          resolve({ error: error });
        }, 8000);
      });
      return Promise.race([started, timeout]);
    }).then(function (outcome) {
      if (outcome.session) { activate(outcome.session, { open: true }); return; }
      var error = outcome.error;
      if (!error.retryable || !outbox || !scope || !root.dataset.programVersion) {
        focus.close();
        status.textContent = error.message;
        startButton.disabled = false;
        return;
      }
      return sync.queue(startPayload).then(function () {
        startLocal = true;
        activate({
          session_id: id, day_id: dayId, program_version: root.dataset.programVersion,
          started_at: new Date().toISOString(), recorded: [], skipped: [],
        }, { open: true });
        status.textContent = 'Treino iniciado neste aparelho. O início será confirmado ao voltar a conexão.';
        if (navigator.onLine) setTimeout(drain, 5000);
      }).catch(function () {
        focus.close();
        status.textContent = 'Não foi possível guardar o início neste aparelho.';
        startButton.disabled = false;
      });
    });
  }

  function minimize(options) {
    focus.close(options && options.fromHistory);
    paintLauncher();
    if (!resumeButton.hidden) resumeButton.focus({ preventScroll: true });
  }

  function resume() {
    if (!sessionId) return;
    openFocus(resumeScreen());
  }

  /* ---------- série ---------- */
  function clearFocusIfDone() {
    if (focusIndex !== null && !project().overview[focusIndex].firstPending) focusIndex = null;
  }

  function nextScreenAfterSet() {
    return project().next ? 'exercise' : 'summary';
  }

  function recordSet(detail) {
    var step = project().current;
    if (!step || !sessionId) return;
    var setKey = key(step.movementIndex, step.setNumber);
    if (detail.key !== setKey) return;
    var payload = {
      action: 'set', session_id: sessionId,
      movement_slug: step.movement.slug, movement_index: step.movementIndex,
      set_number: step.setNumber, set_role: step.series.role,
      weight_kg: detail.weight == null ? '' : String(detail.weight),
      reps: detail.reps == null ? '' : String(detail.reps),
      rir: detail.rir == null ? '' : String(detail.rir),
    };
    // Transição otimista: o descanso começa no toque; o recibo só vira "Salvo"
    // com a resposta do servidor ou "Salvo no aparelho" quando entra na fila.
    recorded.add(setKey);
    recordedDetails.set(setKey, { weight_kg: detail.weight, reps: detail.reps, rir: detail.rir });
    setSync.set(setKey, 'saving');
    lastFreeformIndex = step.movement.freeform ? step.movementIndex : null;
    lastSkipped = null;
    receiptKey = setKey;
    clearFocusIfDone();
    var restSeconds = step.series.rest_seconds == null ? 90 : Number(step.series.rest_seconds);
    if (!project().next) { timer.skip(); screen = 'summary'; }
    else if (restSeconds > 0) { timer.start(restSeconds); screen = 'rest'; }
    else { timer.skip(); screen = 'exercise'; }
    render();
    focus.announce(screen === 'rest'
      ? 'Série registrada. Descanso de ' + format.spokenDuration(restSeconds) + '.'
      : 'Série registrada.');
    deliver(payload).then(function (result) {
      setSync.set(setKey, result.queued ? 'local' : 'saved');
      status.textContent = result.queued ? 'Série salva neste aparelho. Enviaremos ao voltar a internet.' : 'Série registrada no Curva.';
      render();
      return snapshot();
    }).catch(function (error) {
      recorded.delete(setKey);
      recordedDetails.delete(setKey);
      setSync.delete(setKey);
      if (receiptKey === setKey) { receiptKey = null; timer.skip(); }
      var next = project().next;
      focusIndex = next && next.movementIndex === step.movementIndex ? null : step.movementIndex;
      screen = 'exercise';
      status.textContent = error.message;
      render();
      focus.error('Série não registrada: ' + error.message);
    });
  }

  function skipSet() {
    var step = project().current;
    if (!step || !sessionId) return;
    var setKey = key(step.movementIndex, step.setNumber);
    deliver({
      action: 'skip', session_id: sessionId,
      movement_slug: step.movement.slug, movement_index: step.movementIndex,
      set_number: step.setNumber, set_role: step.series.role,
    }).then(function (result) {
      lastSkipped = setKey;
      skipped.add(setKey);
      clearFocusIfDone();
      status.textContent = result.queued
        ? 'Pulo salvo neste aparelho; ainda não confirmado no Curva.'
        : (step.series.required ? 'Série pulada. Encerre como parcial para registrar o treino.' : 'Série opcional pulada.');
      screen = nextScreenAfterSet();
      render();
      focus.toast('Série pulada', 'Desfazer', undoSkip);
      return snapshot();
    }).catch(function (error) { focus.error(error.message); status.textContent = error.message; });
  }

  function unskip(setKey) {
    var parts = setKey.split(':');
    return deliver({
      action: 'unskip', session_id: sessionId,
      movement_index: Number(parts[0]), set_number: Number(parts[1]),
    }).then(function (result) {
      skipped.delete(setKey);
      if (lastSkipped === setKey) lastSkipped = Array.from(skipped).pop() || null;
      return result;
    });
  }

  function undoSkip() {
    if (!lastSkipped || !sessionId) return;
    var setKey = lastSkipped;
    unskip(setKey).then(function (result) {
      var movementIndex = Number(setKey.split(':')[0]);
      var next = project().next;
      focusIndex = next && next.movementIndex === movementIndex ? null : movementIndex;
      screen = 'exercise';
      status.textContent = result.queued ? 'Desfazer salvo neste aparelho; envio pendente.' : 'Série disponível novamente.';
      render();
      return snapshot();
    }).catch(function (error) { focus.error(error.message); status.textContent = error.message; });
  }

  function addFreeformSeries(movementIndex) {
    var movement = movements[movementIndex];
    if (!movement || !movement.freeform || movement.series.length >= 30) return;
    movement.series.push(Object.assign({}, movement.series[0], { set_number: movement.series.length + 1 }));
    var next = project().next;
    focusIndex = next && next.movementIndex === movementIndex ? null : movementIndex;
    timer.skip();
    screen = 'exercise';
    render();
  }

  function requestCorrection(setKey) {
    if (!setKey || !recorded.has(setKey)) return;
    var movementIndex = Number(setKey.split(':')[0]);
    var movement = movements[movementIndex];
    focus.openCorrection({
      key: setKey, movement: movement, entry: recordedDetails.get(setKey) || {},
      label: format.setShortLabel(movement, Number(setKey.split(':')[1])),
    });
  }

  function saveCorrection(detail) {
    var parts = detail.key.split(':');
    var previous = recordedDetails.get(detail.key) || {};
    var payload = {
      action: 'correct', session_id: sessionId, command_key: newId(),
      movement_index: Number(parts[0]), set_number: Number(parts[1]),
      weight_kg: detail.weight == null ? '' : String(detail.weight),
      reps: String(detail.reps), rir: previous.rir == null ? '' : String(previous.rir),
    };
    deliver(payload).then(function (result) {
      recordedDetails.set(detail.key, { weight_kg: detail.weight, reps: detail.reps, rir: previous.rir == null ? null : previous.rir });
      setSync.set(detail.key, result.queued ? 'local' : 'saved');
      status.textContent = result.queued ? 'Correção salva neste aparelho; ainda não confirmada no Curva.' : 'Série corrigida no Curva.';
      focus.closeSheets();
      render();
      focus.toast(result.queued ? 'Correção salva no aparelho' : 'Correção salva');
      return snapshot();
    }).catch(function (error) { focus.correctionError(error.message); });
  }

  function endSession(outcome) {
    if (!sessionId) return;
    deliver({ action: outcome, session_id: sessionId }).then(function (result) {
      var titles = { complete: 'Treino registrado no Curva', partial: 'Treino parcial registrado', cancel: 'Sessão cancelada' };
      timer.stop();
      stored(sessionStorage, 'removeItem', startKey(selectedDayId()));
      ended = {
        outcome: outcome,
        title: result.queued ? 'Treino encerrado neste aparelho' : titles[outcome],
        meta: recorded.size + (recorded.size === 1 ? ' série · ' : ' séries · ') + elapsedMinutes() + ' min'
          + (result.queued ? ' · envio ao voltar a internet' : ''),
      };
      status.textContent = result.queued
        ? 'Encerramento salvo neste aparelho e pendente de envio. Mantenha esta conta para sincronizar.'
        : (outcome === 'partial' ? 'Treino parcial registrado no Curva.'
          : (outcome === 'cancel' ? 'Sessão cancelada no Curva.' : 'Treino concluído e registrado no Curva.'));
      sessionId = null;
      startLocal = false;
      focusIndex = null;
      reviewIndex = null;
      receiptKey = null;
      startButton.disabled = result.queued;
      focus.closeSheets();
      screen = 'finished';
      if (focus.isOpen()) focus.show('finished', viewModel());
      paintLauncher();
      if (!result.queued && outbox) return outbox.clear(scope);
    }).catch(function (error) {
      focus.toast(error.message);
      status.textContent = error.message;
    });
  }

  /* ---------- descanso ---------- */
  function restEnded() {
    paintLauncher();
    if (!focus.isOpen()) return;
    if (screen === 'rest') {
      focus.restDone().then(function () {
        if (screen !== 'rest') return;
        screen = nextScreenAfterSet();
        render();
      });
      return;
    }
    focus.toast('Descanso concluído');
    render();
  }

  /* ---------- eventos do modo foco ---------- */
  function on(name, handler) {
    dialog.addEventListener('guided:' + name, function (event) { handler(event.detail || {}); });
  }

  on('record', recordSet);
  on('skip-set', skipSet);
  on('skip-rest', function () {
    timer.skip();
    screen = nextScreenAfterSet();
    render();
    focus.announce('Descanso pulado');
  });
  on('add-rest', function () {
    timer.add(30);
    var rest = restModel();
    if (rest) focus.restAdded(rest);
    paintLauncher();
    focus.announce('Mais 30 segundos de descanso');
  });
  on('to-rest', function () { if (timer.isRunning()) { screen = 'rest'; render(); } });
  on('extra', function () { if (receiptKey) addFreeformSeries(Number(receiptKey.split(':')[0])); });
  on('jump', function (detail) {
    var state = project();
    var item = state.overview[detail.index];
    if (!item) return;
    focus.closeSheets();
    if (item.status === 'done' || !item.firstPending) {
      reviewIndex = detail.index;
      screen = 'review';
    } else {
      focusIndex = state.next && state.next.movementIndex === detail.index ? null : detail.index;
      reviewIndex = null;
      screen = 'exercise';
    }
    render();
    snapshot();
  });
  on('review-continue', function () {
    focusIndex = null;
    reviewIndex = null;
    screen = nextScreenAfterSet();
    render();
  });
  on('review-extra', function (detail) {
    var index = reviewIndex;
    if (index === null) return;
    if (detail.action === 'freeform') { addFreeformSeries(index); return; }
    if (detail.action === 'optional') {
      focusIndex = index;
      screen = 'exercise';
      render();
      return;
    }
    if (detail.action === 'redo') {
      var keys = Array.from(skipped).filter(function (item) { return item.indexOf(index + ':') === 0; });
      keys.reduce(function (chain, item) {
        return chain.then(function () { return unskip(item); });
      }, Promise.resolve()).then(function () {
        focusIndex = index;
        reviewIndex = null;
        screen = 'exercise';
        render();
        return snapshot();
      }).catch(function (error) { focus.toast(error.message); });
    }
  });
  on('correct-request', function (detail) { requestCorrection(detail.key); });
  on('correct', saveCorrection);
  on('open-summary', function () {
    focus.closeSheets();
    screen = 'summary';
    render();
  });
  on('back', function () {
    if (project().next) {
      focusIndex = null;
      screen = 'exercise';
      render();
    } else {
      focus.openSheet('workout');
    }
  });
  on('end', function (detail) { endSession(detail.outcome); });
  on('minimize', minimize);
  on('close', function () {
    ended = null;
    screen = 'exercise';
    focus.close();
    paintLauncher();
    startButton.focus({ preventScroll: true });
  });

  startButton.addEventListener('click', startSession);
  resumeButton.addEventListener('click', resume);

  /* ---------- retomada ao abrir ---------- */
  function initialize(saved, commands) {
    sync.hydrate(commands);
    var pendingEnd = commands.some(function (item) {
      return ['complete', 'partial', 'cancel'].indexOf(item.payload.action) !== -1;
    });
    if (pendingEnd) {
      startButton.disabled = true;
      status.textContent = 'Treino encerrado neste aparelho. Aguardando envio das séries e do encerramento.';
      drain();
      return;
    }
    if (saved && commands.some(function (item) { return item.payload.action === 'start'; })) {
      startLocal = true;
      activate(saved, { open: location.hash === '#treino-guiado' });
      status.textContent = 'Treino iniciado neste aparelho; aguardando confirmação do servidor.';
      drain();
      return;
    }
    request('GET').then(function (result) {
      if (result.session) {
        if (saved && saved.session_id === result.session.session_id) {
          var union = new Map((result.session.recorded || []).concat(saved.recorded || []).map(function (item) {
            return [key(item.movement_index, item.set_number), item];
          }));
          result.session.recorded = Array.from(union.values());
          var serverSkipped = new Set(result.session.skipped || []);
          commands.slice().sort(commandOrder).forEach(function (item) {
            var payload = item.payload;
            var itemKey = key(payload.movement_index, payload.set_number);
            if (payload.action === 'skip') serverSkipped.add(itemKey);
            if (payload.action === 'unskip') serverSkipped.delete(itemKey);
          });
          result.session.skipped = Array.from(serverSkipped);
          result.session.focus_movement_index = saved.focus_movement_index;
        }
        activate(result.session, { open: location.hash === '#treino-guiado' });
      } else if (location.hash === '#treino-guiado') {
        history.replaceState(history.state, '', location.pathname + location.search);
      }
      drain();
    }).catch(function () {
      if (saved) {
        activate(saved, { open: location.hash === '#treino-guiado' });
        status.textContent = 'Sem conexão. Continue neste aparelho; as séries serão enviadas depois.';
      }
    });
  }

  saveOfflinePlan();
  paintLauncher();
  if (outbox && scope) {
    Promise.all([outbox.restore(scope), outbox.list(scope)]).then(function (items) {
      initialize(items[0], items[1]);
    }).catch(function () { initialize(null, []); });
  } else initialize(null, []);
  window.addEventListener('online', drain);
  window.addEventListener('pagehide', function () {
    sync.release();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) return;
    drain();
    timer.resync();
  });
}());
