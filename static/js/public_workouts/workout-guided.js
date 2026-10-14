(function () {
  'use strict';

  var root = document.querySelector('[data-workout-guided]');
  if (!root) return;
  var panel = root.closest('[data-workout-tab-panel]');
  var startButton = root.querySelector('[data-workout-guided-start]');
  var active = root.querySelector('[data-workout-guided-active]');
  var status = root.querySelector('[data-workout-guided-status]');
  var progress = root.querySelector('[data-workout-guided-progress]');
  var stepLabel = root.querySelector('[data-workout-guided-step]');
  var source = root.querySelector('[data-workout-guided-source]');
  var topTargetPanel = root.querySelector('[data-workout-guided-top-target]');
  var topTargetSummary = root.querySelector('[data-workout-guided-top-summary]');
  var topTargetInput = root.querySelector('[data-workout-guided-top-input]');
  var topTargetApply = root.querySelector('[data-workout-guided-top-apply]');
  var guidedLoads = window.CurvaGuidedLoads;
  var timerLabel = root.querySelector('[data-workout-guided-timer]');
  var restTimer = window.CurvaGuidedTimer.create(timerLabel);
  var weightField = root.querySelector('[data-workout-guided-weight]');
  var repsField = root.querySelector('[data-workout-guided-reps]');
  var rirField = root.querySelector('[data-workout-guided-rir]');
  var fields = root.querySelector('[data-workout-guided-fields]');
  var setButton = root.querySelector('[data-workout-guided-set]');
  var finishButton = root.querySelector('[data-workout-guided-finish]');
  var partialButton = root.querySelector('[data-workout-guided-partial]');
  var cancelButton = root.querySelector('[data-workout-guided-cancel]');
  var skipButton = root.querySelector('[data-workout-guided-skip]');
  var undoSkipButton = root.querySelector('[data-workout-guided-undo-skip]');
  var correction = root.querySelector('[data-workout-guided-correction]');
  var conflictPanel = root.querySelector('[data-workout-guided-conflict]');
  var conflictMessage = root.querySelector('[data-workout-guided-conflict-message]');
  var conflictExport = root.querySelector('[data-workout-guided-conflict-export]');
  var conflictServer = root.querySelector('[data-workout-guided-conflict-server]');
  var conflictCorrect = root.querySelector('[data-workout-guided-conflict-correct]');
  var correctToggle = root.querySelector('[data-workout-guided-correct-toggle]');
  var correctTarget = root.querySelector('[data-workout-guided-correct-target]');
  var correctWeight = root.querySelector('[data-workout-guided-correct-weight]');
  var correctReps = root.querySelector('[data-workout-guided-correct-reps]');
  var correctRir = root.querySelector('[data-workout-guided-correct-rir]');
  var correctSave = root.querySelector('[data-workout-guided-correct-save]');
  var extraButton = root.querySelector('[data-workout-guided-extra]');
  var scope = root.dataset.accountScope && document.body.dataset.planSlug
    ? root.dataset.accountScope + ':' + document.body.dataset.planSlug : '';
  var outbox = window.CurvaGuidedOutbox;
  var request = window.CurvaGuidedApi.create(root.dataset.sessionUrl, root.dataset.accountScope);
  var sessionId = null;
  var movements = [];
  var recorded = new Set();
  var recordedDetails = new Map();
  var skipped = new Set();
  var lastFreeformIndex = null;
  var lastSkipped = null;
  var current = null;
  var currentStepIdentity = null;
  var topTargets = {};
  var topTargetMovementIndex = null;
  var sync = window.CurvaGuidedSync.create({
    outbox: outbox, scope: scope, request: request, newId: newId,
    isOnline: function () { return navigator.onLine; },
    hasActiveSession: function () { return !!sessionId; },
    onConflict: showConflict,
    onStartMapped: function (localId, serverId) {
      if (sessionId === localId) {
        if (currentStepIdentity && currentStepIdentity.indexOf(localId + ':') === 0) {
          currentStepIdentity = serverId + currentStepIdentity.slice(localId.length);
        }
        sessionId = serverId;
        snapshot();
        restTimer.remap(localId, serverId);
      }
    },
    onEndConfirmed: function () {
      active.hidden = true;
      startButton.hidden = false;
      startButton.disabled = false;
      sessionId = null;
    },
    onRefreshed: function (result) {
      if (result.session) activate(result.session);
      else if (sessionId) {
        sessionId = null;
        restTimer.stop();
        active.hidden = true;
        startButton.hidden = false;
        startButton.disabled = false;
        return outbox.clear(scope);
      }
    },
    onDrained: function (result) {
      if (sessionId) paintStep();
      if (result.cleared) status.textContent = 'Tudo enviado ao Curva.';
    },
    onError: function (error) {
      status.textContent = error.status === 401 ? 'Entre novamente na mesma conta para enviar o treino.'
        : (error.retryable ? 'Envio pendente. Tentaremos novamente quando a conexão voltar.'
          : 'Envio pendente: ' + error.message);
    },
  });

  function stored(storage, method, key, value) {
    try { return storage[method](key, value); } catch (_) { return null; }
  }

  function snapshot() {
    if (!sessionId || !outbox) return Promise.resolve();
    return outbox.save(scope, {
      session_id: sessionId, day_id: selectedDayId(), program_version: root.dataset.programVersion,
      recorded: Array.from(recorded, function (item) {
        var parts = item.split(':');
        return Object.assign({ movement_index: Number(parts[0]), set_number: Number(parts[1]) }, recordedDetails.get(item) || {});
      }),
      skipped: Array.from(skipped),
      top_targets: topTargets,
    });
  }

  function pendingLabel() {
    return sync.pendingCount() ? ' · ' + sync.pendingCount() + ' pendente(s) de envio' : '';
  }

  var commandOrder = window.CurvaGuidedSync.commandOrder;
  var deliver = sync.deliver;
  var drain = sync.drain;

  function showConflict(command) {
    conflictPanel.hidden = false;
    conflictMessage.textContent = command.error || 'O servidor não aceitou este registro.';
    conflictCorrect.hidden = command.payload.action !== 'set' || command.error_status !== 409;
    conflictServer.textContent = command.payload.action === 'start'
      ? 'Exportar e abrir a ficha atual' : 'Usar registro do servidor';
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

  function selectedDayId() {
    var tab = panel.querySelector('.workout-day-tab.is-active');
    return tab ? (tab.getAttribute('aria-controls') || '').replace(/^workout-day-/, '') : '';
  }

  function buildMovements(dayId) {
    var day = document.getElementById('workout-day-' + dayId);
    if (!day) return [];
    return Array.prototype.map.call(day.querySelectorAll('.workout-movement-card'), function (card) {
      var series = [];
      try { series = JSON.parse(card.dataset.guidedSeries || '[]'); } catch (_) { series = []; }
      series.forEach(function (row) { row.base_weight_kg = row.weight_kg; });
      var label = card.querySelector('.workout-movement-copy strong');
      return {
        slug: card.dataset.movementSlug, label: label ? label.textContent.trim() : 'Exercício',
        loadKind: card.dataset.loadKind, allowLoad: card.dataset.allowLoadRegistration !== 'false',
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

  var key = window.CurvaGuidedState.key;
  function startKey(dayId) { return 'curva-start:' + location.pathname + ':' + dayId; }

  function newId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    var bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    var hex = Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, '0'); }).join('');
    return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
  }

  function paintStep() {
    var draft = { weight: weightField.value, reps: repsField.value, rir: rirField.value };
    var state = window.CurvaGuidedState.project(
      movements, recorded, skipped, sync.pendingCount(), lastSkipped, lastFreeformIndex
    );
    var next = state.next;
    current = next;
    var nextIdentity = next ? sessionId + ':' + selectedDayId() + ':' + key(next.movementIndex, next.setNumber) : null;
    var sameStep = !!nextIdentity && nextIdentity === currentStepIdentity;
    currentStepIdentity = nextIdentity;
    progress.textContent = state.recordedCount + ' série(s) registrada(s) · até ' + state.total + ' no guia' + pendingLabel();
    fields.hidden = !next;
    topTargetPanel.hidden = !next || !next.movement.allowLoad || next.movement.loadKind === 'fixed_kg'
      || !next.movement.series.some(function (row) {
      return row.top_factor != null;
    });
    setButton.hidden = !next;
    finishButton.hidden = !state.canFinish;
    skipButton.hidden = !next;
    undoSkipButton.hidden = !state.canUndoSkip;
    correctToggle.hidden = !state.canCorrect;
    extraButton.hidden = !state.canAddExtra;
    if (!next) {
      stepLabel.textContent = 'Todas as séries registradas';
      source.textContent = 'Confira o treino e finalize para enviar ao Curva.';
      return;
    }
    if (!topTargetPanel.hidden) {
      var target = next.movement.topTargetKg;
      topTargetSummary.textContent = target == null
        ? 'Definir carga alvo da Top · opcional'
        : 'Carga alvo da Top: ' + target + ' kg · ajustar';
      if (topTargetMovementIndex !== next.movementIndex) {
        topTargetInput.value = target == null ? '' : target;
        topTargetPanel.open = target == null && next.series.weight_kg == null;
        topTargetMovementIndex = next.movementIndex;
      }
    }
    var roles = { warmup: 'Preparação', feeder: 'Aproximação', top_set: 'Série principal', max_set: 'Série máxima', legacy_unknown: 'Série livre' };
    stepLabel.textContent = next.movement.label + ' · ' + (roles[next.series.role] || 'Série') + ' ' + next.setNumber + '/' + next.movement.series.length;
    var sources = {
      fixed_kg: 'Carga prescrita; ajuste se necessário.',
      percentage: 'Percentual do RM prescrito. Informe a carga realizada se não há kg sugerido.',
      phase_progressive: 'Sugestão da fase atual; ajuste se necessário.',
      rir_estimate: 'Estimativa de carga; ajuste se necessário.',
      last_observed: 'Referência da última sessão, não uma prescrição. Ajuste conforme necessário.',
      free: 'Sem referência em kg. Informe uma carga apenas se fizer sentido.',
    };
    source.textContent = next.movement.allowLoad ? (sources[next.movement.loadKind] || '') : 'Exercício sem registro de carga.';
    var stageSources = {
      manual: 'Carga escolhida por você.',
      fixed_kg: 'Carga definida pelo profissional; registre o que realizou.',
      percent_of_top: 'Carga de aproximação calculada a partir da Top; ajuste se necessário.',
      percent_of_rm: 'Carga calculada a partir do RM; ajuste se necessário.',
      suggested_top: 'Referência editável para a série principal.',
    };
    if (next.series.load_source && next.movement.allowLoad) {
      source.textContent = stageSources[next.series.load_source] || source.textContent;
    }
    if (!next.series.load_source && next.movement.loadKind === 'percentage' && next.series.weight_kg != null) {
      source.textContent = 'Carga calculada a partir do RM; ajuste se necessário.';
    }
    if (next.movement.topTargetKg != null && next.series.top_factor != null) {
      source.textContent = 'Sugestão a partir da carga alvo que você definiu para a Top; registre o peso que realizou.';
    }
    if (next.series.reps != null) {
      source.textContent += ' Meta: ' + next.series.reps
        + (next.series.reps_max && next.series.reps_max !== next.series.reps ? '–' + next.series.reps_max : '')
        + ' repetições.';
    }
    if (next.movement.freeform) source.textContent += ' Quantidade livre: registre o que fez; o profissional verá que não havia contagem estruturada.';
    else if (next.series.required === false) source.textContent += ' Série opcional dentro da faixa prescrita.';
    if (!next.movement.allowLoad && next.series.reps == null) source.textContent += ' Toque em registrar ao concluir a série.';
    weightField.closest('label').hidden = !next.movement.allowLoad;
    weightField.value = sameStep ? draft.weight
      : (next.movement.allowLoad && next.series.weight_kg != null ? next.series.weight_kg : '');
    repsField.value = sameStep ? draft.reps : '';
    rirField.value = sameStep ? draft.rir : '';
  }

  function activate(session) {
    if (session.ended_at || session.completed_at) {
      stored(sessionStorage, 'removeItem', startKey(session.day_id));
      status.textContent = 'Este treino já foi concluído.';
      startButton.disabled = false;
      return;
    }
    if (String(session.program_version) !== root.dataset.programVersion) {
      stored(sessionStorage, 'removeItem', startKey(session.day_id));
      status.textContent = 'O programa foi atualizado. Comece um treino com a versão atual.';
      startButton.disabled = false;
      return;
    }
    var tab = panel.querySelector('[data-workout-tab-target="workout-day-' + session.day_id + '"]');
    if (tab && !tab.classList.contains('is-active')) tab.click();
    movements = buildMovements(session.day_id);
    if (!movements.length) {
      status.textContent = 'Não foi possível montar este treino. Atualize a página.';
      startButton.disabled = false;
      return;
    }
    var newSession = sessionId !== session.session_id;
    if (newSession) topTargets = session.top_targets || {};
    sessionId = session.session_id;
    if (newSession) topTargetMovementIndex = null;
    Object.keys(topTargets).forEach(function (index) {
      var movement = movements[Number(index)];
      var target = guidedLoads.parseTarget(topTargets[index]);
      if (movement && target != null) guidedLoads.applyTopTarget(movement, target);
    });
    recorded = new Set((session.recorded || []).map(function (item) {
      return key(item.movement_index, item.set_number);
    }));
    recordedDetails = new Map((session.recorded || []).map(function (item) {
      return [key(item.movement_index, item.set_number), {
        weight_kg: item.weight_kg, reps: item.reps, rir: item.rir,
      }];
    }));
    skipped = new Set(session.skipped || []);
    lastSkipped = Array.from(skipped).pop() || null;
    lastFreeformIndex = null;
    movements.forEach(function (movement, index) {
      if (!movement.freeform) return;
      var performed = Array.from(recorded).filter(function (item) {
        return item.indexOf(index + ':') === 0;
      });
      if (performed.length) lastFreeformIndex = index;
      var maximum = Math.max(1, ...performed.concat(Array.from(skipped).filter(function (item) {
        return item.indexOf(index + ':') === 0;
      })).map(function (item) { return Number(item.split(':')[1]); }));
      while (movement.series.length < maximum) {
        movement.series.push(Object.assign({}, movement.series[0], { set_number: movement.series.length + 1 }));
      }
    });
    startButton.hidden = true;
    active.hidden = false;
    correction.hidden = true;
    status.textContent = recorded.size ? 'Sessão retomada. Continue de onde parou.' : 'Sessão iniciada. Registre cada série para avançar.';
    paintStep();
    restTimer.attach(sessionId);
    snapshot().catch(function () { status.textContent = 'Armazenamento local indisponível; mantenha conexão para registrar.'; });
  }

  startButton.addEventListener('click', function () {
    var dayId = selectedDayId();
    if (!dayId) { status.textContent = 'Escolha um dia de treino para começar.'; return; }
    if (!buildMovements(dayId).length) { status.textContent = 'Este dia ainda não tem séries guiáveis.'; return; }
    var keyName = startKey(dayId);
    var id = stored(sessionStorage, 'getItem', keyName) || newId();
    stored(sessionStorage, 'setItem', keyName, id);
    startButton.disabled = true;
    var startPayload = {
      action: 'start', day_id: dayId, start_key: id,
      program_version: root.dataset.programVersion, local_session_id: id,
    };
    request('POST', startPayload)
      .then(activate)
      .catch(function (error) {
        if (!error.retryable || !outbox || !scope || !root.dataset.programVersion) {
          status.textContent = error.message;
          startButton.disabled = false;
          return;
        }
        return sync.queue(startPayload).then(function () {
          activate({ session_id: id, day_id: dayId, program_version: root.dataset.programVersion,
            recorded: [], skipped: [] });
          status.textContent = 'Treino iniciado neste aparelho. O início será confirmado ao voltar a conexão.';
          if (navigator.onLine) setTimeout(drain, 5000);
        }).catch(function () {
          status.textContent = 'Não foi possível guardar o início neste aparelho.';
          startButton.disabled = false;
        });
      });
  });

  topTargetApply.addEventListener('click', function () {
    if (!current) return;
    var raw = topTargetInput.value.trim();
    var target = raw ? guidedLoads.parseTarget(raw) : null;
    if (raw && target == null) {
      status.textContent = 'Informe uma carga alvo entre 0,01 e 9.999,99 kg, com até duas casas decimais.';
      return;
    }
    var movement = current.movement;
    var previousSuggestion = current.series.weight_kg;
    var currentDraft = weightField.value;
    guidedLoads.applyTopTarget(movement, target);
    if (target == null) delete topTargets[current.movementIndex];
    else topTargets[current.movementIndex] = target;
    if (!currentDraft || (previousSuggestion != null && currentDraft === String(previousSuggestion))) {
      weightField.value = current.series.weight_kg == null ? '' : current.series.weight_kg;
    }
    topTargetSummary.textContent = target == null
      ? 'Definir carga alvo da Top · opcional'
      : 'Carga alvo da Top: ' + target + ' kg · ajustar';
    topTargetPanel.open = false;
    paintStep();
    status.textContent = target == null
      ? 'Alvo pessoal removido. Você pode ajustar cada carga.'
      : 'Sugestões de carga atualizadas neste treino. Ajuste o peso realizado em cada série.';
    snapshot().catch(function () {
      status.textContent = 'Sugestão aplicada, mas não foi possível guardar o alvo neste aparelho.';
    });
  });

  setButton.addEventListener('click', function () {
    if (!current || !sessionId) return;
    var weight = current.movement.allowLoad ? weightField.value : '';
    var reps = repsField.value;
    if (current.series.reps != null && !reps) { status.textContent = 'Informe quantas repetições você realizou.'; return; }
    if (!weight && !reps && (current.movement.allowLoad || current.series.reps != null)) {
      status.textContent = 'Informe a carga ou as repetições realizadas.'; return;
    }
    setButton.disabled = true;
    var completedStep = current;
    deliver({
      action: 'set', session_id: sessionId,
      movement_slug: completedStep.movement.slug, movement_index: completedStep.movementIndex,
      set_number: completedStep.setNumber, set_role: completedStep.series.role,
      weight_kg: weight, reps: reps, rir: rirField.value,
    }).then(function (result) {
      var completedKey = key(completedStep.movementIndex, completedStep.setNumber);
      recorded.add(completedKey);
      recordedDetails.set(completedKey, { weight_kg: weight || null, reps: reps || null, rir: rirField.value || null });
      lastFreeformIndex = completedStep.movement.freeform ? completedStep.movementIndex : null;
      status.textContent = result.queued ? 'Série salva neste aparelho. Enviaremos ao voltar a internet.' : 'Série registrada no Curva.';
      paintStep();
      if (current && completedStep.series.rest_seconds == null) restTimer.start(90);
      else if (current && completedStep.series.rest_seconds > 0) restTimer.start(completedStep.series.rest_seconds);
      return snapshot();
    }).catch(function (error) {
      status.textContent = error.message;
    }).finally(function () { setButton.disabled = false; });
  });

  skipButton.addEventListener('click', function () {
    if (!current || !sessionId) return;
    var step = current;
    skipButton.disabled = true;
    deliver({
      action: 'skip', session_id: sessionId,
      movement_slug: step.movement.slug, movement_index: step.movementIndex,
      set_number: step.setNumber, set_role: step.series.role,
    }).then(function (result) {
      lastSkipped = key(step.movementIndex, step.setNumber);
      skipped.add(lastSkipped);
      status.textContent = result.queued
        ? 'Pulo salvo neste aparelho; ainda não confirmado no Curva.'
        : (step.series.required ? 'Série pulada. Encerre como parcial para registrar o treino.' : 'Série opcional pulada.');
      paintStep();
      return snapshot();
    }).catch(function (error) { status.textContent = error.message; })
      .finally(function () { skipButton.disabled = false; });
  });

  undoSkipButton.addEventListener('click', function () {
    if (!lastSkipped || !sessionId) return;
    var parts = lastSkipped.split(':');
    var skippedKey = lastSkipped;
    undoSkipButton.disabled = true;
    deliver({
      action: 'unskip', session_id: sessionId,
      movement_index: Number(parts[0]), set_number: Number(parts[1]),
    }).then(function (result) {
      skipped.delete(skippedKey);
      lastSkipped = Array.from(skipped).pop() || null;
      status.textContent = result.queued ? 'Desfazer salvo neste aparelho; envio pendente.' : 'Série disponível novamente.';
      paintStep();
      return snapshot();
    }).catch(function (error) { status.textContent = error.message; })
      .finally(function () { undoSkipButton.disabled = false; });
  });

  extraButton.addEventListener('click', function () {
    if (lastFreeformIndex === null) return;
    var movement = movements[lastFreeformIndex];
    if (!movement || !movement.freeform || movement.series.length >= 30) return;
    movement.series.push(Object.assign({}, movement.series[0], { set_number: movement.series.length + 1 }));
    status.textContent = 'Série livre adicional pronta para registro.';
    paintStep();
  });

  function showCorrectionValues() {
    var values = recordedDetails.get(correctTarget.value) || {};
    correctWeight.value = values.weight_kg == null ? '' : values.weight_kg;
    correctReps.value = values.reps == null ? '' : values.reps;
    correctRir.value = values.rir == null ? '' : values.rir;
    var movement = movements[Number((correctTarget.value || '').split(':')[0])];
    correctWeight.closest('label').hidden = !!movement && !movement.allowLoad;
  }

  correctToggle.addEventListener('click', function () {
    correction.hidden = !correction.hidden;
    if (correction.hidden) return;
    correctTarget.replaceChildren();
    Array.from(recorded).forEach(function (item) {
      var parts = item.split(':');
      var movement = movements[Number(parts[0])];
      var option = document.createElement('option');
      option.value = item;
      option.textContent = (movement ? movement.label : 'Exercício') + ' · série ' + parts[1];
      correctTarget.appendChild(option);
    });
    showCorrectionValues();
  });
  correctTarget.addEventListener('change', showCorrectionValues);
  correctSave.addEventListener('click', function () {
    if (!sessionId || !correctTarget.value) return;
    var parts = correctTarget.value.split(':');
    var movement = movements[Number(parts[0])];
    if (!movement) return;
    correctSave.disabled = true;
    var payload = {
      action: 'correct', session_id: sessionId, command_key: newId(),
      movement_index: Number(parts[0]), set_number: Number(parts[1]),
      weight_kg: movement.allowLoad ? correctWeight.value : '',
      reps: correctReps.value, rir: correctRir.value,
    };
    deliver(payload).then(function (result) {
      recordedDetails.set(correctTarget.value, {
        weight_kg: payload.weight_kg || null, reps: payload.reps || null, rir: payload.rir || null,
      });
      status.textContent = result.queued
        ? 'Correção salva neste aparelho; ainda não confirmada no Curva.'
        : 'Série corrigida no Curva.';
      correction.hidden = true;
      return snapshot();
    }).catch(function (error) { status.textContent = error.message; })
      .finally(function () { correctSave.disabled = false; });
  });

  function endSession(outcome) {
    if (!sessionId) return;
    var button = outcome === 'partial' ? partialButton : (outcome === 'cancel' ? cancelButton : finishButton);
    button.disabled = true;
    deliver({ action: outcome, session_id: sessionId })
      .then(function (result) {
        restTimer.stop();
        stored(sessionStorage, 'removeItem', startKey(selectedDayId()));
        active.hidden = true;
        correction.hidden = true;
        startButton.hidden = false;
        startButton.disabled = result.queued;
        status.textContent = result.queued
          ? 'Encerramento salvo neste aparelho e pendente de envio. Mantenha esta conta para sincronizar.'
          : (outcome === 'partial' ? 'Treino parcial registrado no Curva.'
            : (outcome === 'cancel' ? 'Sessão cancelada no Curva.' : 'Treino concluído e registrado no Curva.'));
        sessionId = null;
        if (!result.queued && outbox) return outbox.clear(scope);
      }).catch(function (error) { status.textContent = error.message; })
      .finally(function () { button.disabled = false; });
  }

  finishButton.addEventListener('click', function () {
    endSession('complete');
  });
  partialButton.addEventListener('click', function () { endSession('partial'); });
  cancelButton.addEventListener('click', function () {
    if (window.confirm('Cancelar esta sessão? As séries já enviadas continuam no histórico como canceladas.')) endSession('cancel');
  });

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
      activate(saved);
      status.textContent = 'Treino iniciado neste aparelho; aguardando confirmação do servidor.';
      drain();
      return;
    }
    request('GET').then(function (result) {
      if (result.session) {
        if (saved && saved.session_id === result.session.session_id) {
          result.session.top_targets = saved.top_targets || {};
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
        }
        activate(result.session);
      }
      drain();
    }).catch(function () {
      if (saved) {
        activate(saved);
        status.textContent = 'Sem conexão. Continue neste aparelho; as séries serão enviadas depois.';
      }
    });
  }

  saveOfflinePlan();
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
    if (!document.hidden) drain();
  });
}());
