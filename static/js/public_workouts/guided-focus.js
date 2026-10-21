/* View do modo foco do treino guiado (docs/plans/curva-treino-guiado-modo-foco-plan.md).
 *
 * Responsabilidade: abrir/fechar o <dialog>, alternar telas, preencher texto e
 * manter o rascunho da série em edição. Não faz fetch, não toca IndexedDB e não
 * decide fluxo: avisa o controlador (workout-guided.js) por CustomEvent
 * `guided:*` no próprio <dialog> e recebe um view model pronto em show().
 *
 * O rascunho é indexado pela série (movimento:série). Um refresh do servidor
 * repinta a tela sem apagar o que o aluno está digitando.
 */
(function () {
  'use strict';

  var HASH = '#treino-guiado';
  var SOUND_KEY = 'curva-guided-sound';

  function create(dialog, options) {
    options = options || {};
    var format = window.CurvaGuidedFormat;
    var Ring = window.CurvaGuidedRing;
    var screens = {};
    var current = null;
    var model = null;
    var draft = null;
    var correction = null;
    var countdownRun = null;
    var restToken = null;
    var beats = new Set();
    var announced = new Set();
    var historyPushed = false;
    var wakeLock = null;
    var toastTimer = null;
    var cancelArmed = null;
    var audio = null;
    var topPanelMovement = null;
    var goWord = options.goWord || 'GO';
    var period = options.period || null;

    function q(selector, root) { return (root || dialog).querySelector(selector); }
    function qa(selector, root) { return Array.prototype.slice.call((root || dialog).querySelectorAll(selector)); }
    function emit(name, detail) { dialog.dispatchEvent(new CustomEvent('guided:' + name, { detail: detail || {} })); }
    function reduced() {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }

    qa('[data-guided-screen]').forEach(function (section) { screens[section.dataset.guidedScreen] = section; });
    var chrome = q('[data-guided-chrome]');
    var progress = q('[data-guided-progress]');
    var countdownRing = Ring.create(q('[data-guided-ring="countdown"]'), { reducedMotion: reduced });
    var restRing = Ring.create(q('[data-guided-ring="rest"]'), { reducedMotion: reduced });
    var weightInput = q('[data-workout-guided-weight]');
    var repsInput = q('[data-workout-guided-reps]');
    var effort = q('[data-guided-effort]');
    var errorLine = q('[data-guided-error]');
    var live = q('[data-guided-live]');
    var toastEl = q('[data-guided-toast]');
    var soundSwitch = q('[data-guided-sound]');
    var timeInput = q('[data-guided-time]');
    var holdRing = Ring.create(q('[data-guided-ring="hold"]'), { reducedMotion: reduced });
    var holdRun = null;

    /* ---------- plataforma ---------- */
    // Ligado por padrão: só fica mudo para quem desligou no painel ('0').
    function storedSound() {
      try { return window.localStorage.getItem(SOUND_KEY) !== '0'; } catch (_) { return true; }
    }
    var soundOn = storedSound();
    soundSwitch.setAttribute('aria-checked', String(soundOn));

    function announce(text) {
      live.textContent = '';
      window.requestAnimationFrame(function () { live.textContent = text; });
    }
    function beep(frequency, duration) {
      if (!soundOn) return;
      try {
        audio = audio || new (window.AudioContext || window.webkitAudioContext)();
        var osc = audio.createOscillator();
        var gain = audio.createGain();
        osc.frequency.value = frequency;
        gain.gain.setValueAtTime(0.0001, audio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.22, audio.currentTime + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + duration);
        osc.connect(gain).connect(audio.destination);
        osc.start();
        osc.stop(audio.currentTime + duration + 0.02);
      } catch (_) { /* sem áudio */ }
    }
    // O iPhone só libera o áudio dentro de um toque. Como o som vem ligado,
    // abrir o guiado (o toque em "Iniciar") e cada toque nele destravam; o
    // toque seguinte também religa o áudio que o iOS suspende em segundo plano.
    function unlockAudio() {
      if (!soundOn || (audio && audio.state === 'running')) return;
      try {
        audio = audio || new (window.AudioContext || window.webkitAudioContext)();
        var resumed = audio.resume();
        if (resumed && resumed.catch) resumed.catch(function () { /* fora de um toque */ });
      } catch (_) { /* sem áudio */ }
    }
    function feedback(vibrateMs, frequency, duration) {
      try { if (navigator.vibrate) navigator.vibrate(vibrateMs); } catch (_) { /* sem vibração */ }
      beep(frequency, duration || 0.12);
    }
    function requestWake() {
      if (wakeLock || !navigator.wakeLock || document.visibilityState !== 'visible') return;
      navigator.wakeLock.request('screen').then(function (lock) {
        wakeLock = lock;
        lock.addEventListener('release', function () { wakeLock = null; });
      }).catch(function () { wakeLock = null; });
    }
    function releaseWake() {
      try { if (wakeLock) wakeLock.release(); } catch (_) { /* já liberado */ }
      wakeLock = null;
    }

    /* ---------- abrir / fechar ---------- */
    function open() {
      unlockAudio();
      if (!dialog.open) {
        try { dialog.showModal(); } catch (_) { dialog.setAttribute('open', ''); }
      }
      document.documentElement.classList.add('guided-focus-open');
      if (location.hash !== HASH) {
        try { history.pushState({ guidedFocus: true }, '', HASH); historyPushed = true; } catch (_) { historyPushed = false; }
      }
      requestWake();
    }
    function close(fromHistory) {
      stopCountdown();
      if (holdRun) holdRun.cancel();
      closeSheets();
      hideToast();
      if (dialog.open) dialog.close();
      document.documentElement.classList.remove('guided-focus-open');
      releaseWake();
      current = null;
      if (fromHistory || location.hash !== HASH) { historyPushed = false; return; }
      try {
        if (historyPushed) history.back();
        else history.replaceState(history.state, '', location.pathname + location.search);
      } catch (_) { /* histórico indisponível */ }
      historyPushed = false;
    }

    window.addEventListener('popstate', function () {
      if (dialog.open && location.hash !== HASH) { historyPushed = false; emit('minimize', { fromHistory: true }); }
    });
    dialog.addEventListener('cancel', function (event) {
      event.preventDefault();
      if (openSheetName()) closeSheets();
      else if (current && current !== 'countdown') emit('minimize');
    });
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && dialog.open) requestWake();
    });

    /* ---------- telas ---------- */
    function showScreen(name) {
      var changed = name !== current;
      current = name;
      Object.keys(screens).forEach(function (key) { screens[key].hidden = key !== name; });
      var withChrome = name !== 'countdown' && name !== 'finished' && name !== 'hold';
      chrome.hidden = !withChrome;
      progress.hidden = !withChrome || name === 'summary';
      return changed;
    }
    function focusScreen(name) {
      var section = screens[name];
      var target = q('[data-guided-title]', section) || q('button:not([hidden])', section);
      if (target) target.focus({ preventScroll: true });
    }

    function show(name, vm) {
      model = vm;
      open();
      var changed = showScreen(name);
      if (name !== 'countdown' && name !== 'finished' && name !== 'hold') paintProgress(vm);
      if (name === 'exercise') paintExercise(vm);
      else if (name === 'rest') paintRest(vm);
      else if (name === 'review') paintReview(vm);
      else if (name === 'summary') paintSummary(vm);
      else if (name === 'finished') paintFinished(vm);
      paintSync(vm);
      if (openSheetName() === 'workout') paintSheet(vm);
      if (changed) focusScreen(name);
    }

    function setTitle(section, movement) {
      var title = q('[data-guided-title]', section);
      var link = q('[data-guided-video]', section);
      q('[data-guided-name]', section).textContent = movement.label;
      title.toggleAttribute('data-long', movement.label.length > 24);
      if (movement.referenceUrl) {
        link.setAttribute('href', movement.referenceUrl);
        link.setAttribute('aria-label', movement.label + ': ver vídeo no MuscleWiki, abre em nova aba');
      } else {
        link.removeAttribute('href');
        link.removeAttribute('aria-label');
      }
    }

    function paintProgress(vm) {
      var total = vm.state.overview.length;
      var index = vm.progressIndex;
      q('[data-guided-progress-label]').textContent = index != null ? 'Exercício ' + (index + 1) + ' de ' + total : '';
      var holder = q('[data-guided-segments]');
      while (holder.children.length < total) {
        var segment = document.createElement('span');
        segment.className = 'guided-focus__segment';
        holder.appendChild(segment);
      }
      while (holder.children.length > total) holder.removeChild(holder.lastChild);
      vm.state.overview.forEach(function (item, position) {
        holder.children[position].classList.toggle('is-done', item.status === 'done');
        holder.children[position].classList.toggle('is-now', position === index);
      });
      var chip = q('[data-guided-rest-chip]');
      chip.hidden = !(vm.rest && (current === 'exercise' || current === 'review'));
      if (vm.rest) q('[data-guided-rest-chip-time]').textContent = format.clock(vm.rest.seconds);
    }

    function paintSync(vm) {
      qa('[data-guided-sync]').forEach(function (line) {
        line.textContent = vm.syncText || '';
        line.hidden = !vm.syncText;
      });
    }

    /* ---------- exercício e rascunho ---------- */
    function newDraft(vm, step) {
      var movement = step.movement;
      var series = step.series;
      var suggestion = movement.allowLoad && series.weight_kg != null && series.weight_kg !== '' ? Number(series.weight_kg) : null;
      var base = suggestion;
      var fromPrevious = false;
      if (movement.allowLoad) {
        for (var setNumber = step.setNumber - 1; setNumber >= 1; setNumber -= 1) {
          var previous = vm.recordedDetails.get(step.movementIndex + ':' + setNumber);
          var previousSeries = movement.series[setNumber - 1];
          if (previous && previousSeries && previousSeries.role === series.role && previous.weight_kg != null && previous.weight_kg !== '') {
            var previousWeight = Number(previous.weight_kg);
            if (previousWeight !== suggestion) { base = previousWeight; fromPrevious = true; }
            break;
          }
        }
      }
      return {
        key: step.movementIndex + ':' + step.setNumber, weight: base, base: base, fromPrevious: fromPrevious,
        suggestion: suggestion,
        reps: null, rir: null, invalidWeight: false, invalidReps: false, repsRequired: series.reps != null,
        // Isometria: o campo de tempo já vem com a meta (o alvo de cima da faixa).
        timed: format.isTimed(series), invalidDuration: false,
        duration: format.isTimed(series) ? Number(series.hold_seconds_max || series.hold_seconds) : null,
      };
    }
    /* A carga alvo da Top recalcula a sugestão da mesma série: o campo acompanha
       só se o aluno ainda não mexeu nele. */
    function followSuggestion(step) {
      var series = step.series;
      var suggestion = step.movement.allowLoad && series.weight_kg != null && series.weight_kg !== '' ? Number(series.weight_kg) : null;
      if (suggestion === draft.suggestion) return;
      var untouched = draft.weight == null || draft.weight === draft.base;
      draft.suggestion = suggestion;
      if (draft.fromPrevious) return;
      draft.base = suggestion;
      if (untouched) { draft.weight = suggestion; draft.invalidWeight = false; writeDraftInputs(); }
    }
    function paintTopTarget(vm) {
      var panel = q('[data-workout-guided-top-target]');
      var top = vm.topTarget;
      panel.hidden = !top;
      if (!top) return;
      q('[data-workout-guided-top-summary]').textContent = top.target == null
        ? 'Definir carga alvo da Top · opcional'
        : 'Carga alvo da Top: ' + format.kg(top.target) + ' · ajustar';
      if (topPanelMovement !== top.movementIndex) {
        topPanelMovement = top.movementIndex;
        q('[data-workout-guided-top-input]').value = top.target == null ? '' : format.decimal(top.target);
        panel.open = top.openByDefault;
      }
    }
    function todayIso() {
      var now = new Date();
      return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    }
    /* "Semana passada 100 kg → Hoje 107,5 kg · +8%": de onde veio a carga de hoje. */
    function paintPlan(plan) {
      var box = q('[data-guided-plan]');
      box.hidden = !plan;
      if (!plan) return;
      box.dataset.tone = plan.tone;
      q('[data-guided-plan-from-label]').textContent = plan.fromLabel;
      q('[data-guided-plan-from]').textContent = format.kg(plan.fromKg);
      q('[data-guided-plan-to-label]').textContent = plan.toLabel;
      q('[data-guided-plan-to]').textContent = format.kg(plan.toKg);
      q('[data-guided-plan-delta]').textContent = plan.delta;
      q('[data-guided-plan-why]').textContent = plan.why;
    }
    function writeDraftInputs() {
      weightInput.value = draft.weight == null ? '' : format.decimal(draft.weight);
      repsInput.value = draft.reps == null ? '' : String(draft.reps);
      timeInput.value = draft.duration == null ? '' : String(draft.duration);
    }
    function paintDraft() {
      if (!model || !model.current || !draft) return;
      var movement = model.current.movement;
      var series = model.current.series;
      q('[data-workout-guided-set]').textContent = format.ctaText(movement, draft);
      var plan = format.loadPlan(movement, series, { period: period, today: todayIso() });
      paintPlan(plan);
      var source = format.weightSource(movement, series, draft);
      // Com a conta à vista no quadro acima, a linha embaixo só lembra que dá para ajustar.
      if (plan && draft.weight != null && draft.weight === draft.base && !draft.fromPrevious) {
        source = { text: 'Calculada automaticamente · ajuste se precisar', reset: null };
      }
      q('[data-guided-weight-source]').textContent = source.text;
      var reset = q('[data-guided-weight-reset]');
      reset.hidden = !source.reset;
      reset.textContent = source.reset || '';
      q('[data-guided-reps-hint]').textContent = draft.reps == null && series.reps != null
        ? 'Toque em + para preencher a meta (' + series.reps + ')' : '';
      q('[data-guided-effort-value]').textContent = format.rirText(draft.rir);
      qa('[data-guided-rir]').forEach(function (chip) {
        chip.setAttribute('aria-pressed', String(Number(chip.dataset.guidedRir) === draft.rir));
      });
    }
    function setError(text) {
      errorLine.textContent = text || '';
      errorLine.hidden = !text;
    }

    function timedKey(vm, setKey) {
      var parts = String(setKey || '').split(':').map(Number);
      var movement = vm.movements[parts[0]];
      return !!movement && format.isTimed(movement.series[parts[1] - 1]);
    }
    function paintExercise(vm) {
      var step = vm.current;
      var section = screens.exercise;
      var movement = step.movement;
      setTitle(section, movement);
      q('[data-guided-set-label]', section).textContent = format.setLabel(movement, step.series, step.setNumber);
      q('[data-guided-meta]', section).textContent = format.metaText(movement, step.series);
      var timed = format.isTimed(step.series);
      q('[data-guided-weight-field]', section).hidden = !movement.allowLoad || timed;
      q('[data-guided-no-load]', section).hidden = movement.allowLoad || timed;
      q('[data-guided-time-field]', section).hidden = !timed;
      q('[data-guided-reps-field]', section).hidden = timed;
      q('[data-guided-time-direct]', section).hidden = !timed;
      q('[data-guided-time-target]', section).textContent = timed ? 'meta ' + format.holdText(step.series) : '';
      effort.hidden = timed;
      q('[data-guided-reps-target]', section).textContent = step.series.reps != null ? 'meta ' + format.repsText(step.series) : '';
      var stepKey = step.movementIndex + ':' + step.setNumber;
      if (!draft || draft.key !== stepKey) {
        draft = newDraft(vm, step);
        writeDraftInputs();
        effort.open = false;
        setError('');
      } else {
        followSuggestion(step);
      }
      paintTopTarget(vm);
      q('[data-guided-correct-last]', section).hidden = !vm.lastRecordedKey || timedKey(vm, vm.lastRecordedKey);
      paintDraft();
    }

    function validDuration() {
      if (draft.invalidDuration || draft.duration == null) {
        setError('Informe o tempo em segundos (1 a 3600).');
        timeInput.focus();
        return false;
      }
      setError('');
      return true;
    }
    /* Isometria: a própria tela roda o 3-2-1 e o cronômetro e, no fim, registra
       a série com o tempo sustentado (o controlador só recebe o 'record'). */
    function startHold(setKey, seconds) {
      var label = model.current.movement.label;
      hold({ seconds: seconds, name: label, label: label + ' · ' + format.seconds(seconds) }).then(function (result) {
        if (!result) { show('exercise', model); return; }
        emit('record', { key: setKey, weight: null, reps: null, rir: null, duration: result.seconds });
      });
    }
    function submitSet() {
      if (!model || !model.current || !draft) return;
      var movement = model.current.movement;
      if (draft.timed) {
        if (validDuration()) startHold(draft.key, draft.duration);
        return;
      }
      if (draft.invalidWeight) { setError('Confira a carga: use números com até duas casas decimais.'); weightInput.focus(); return; }
      if (draft.invalidReps) { setError('Repetições precisam ser um número inteiro.'); repsInput.focus(); return; }
      if (draft.repsRequired && draft.reps == null) { setError('Informe quantas repetições você fez.'); repsInput.focus(); return; }
      if (draft.weight == null && draft.reps == null && movement.allowLoad) {
        setError('Informe a carga ou as repetições realizadas.'); return;
      }
      setError('');
      emit('record', {
        key: draft.key, weight: movement.allowLoad ? draft.weight : null, reps: draft.reps, rir: draft.rir,
      });
    }

    timeInput.addEventListener('input', function () {
      if (!draft) return;
      var parsed = format.parseSeconds(timeInput.value);
      draft.invalidDuration = parsed === undefined;
      draft.duration = parsed === undefined ? null : parsed;
      paintDraft();
    });
    weightInput.addEventListener('input', function () {
      if (!draft) return;
      var parsed = format.parseWeight(weightInput.value);
      draft.invalidWeight = parsed === undefined;
      draft.weight = parsed === undefined ? null : parsed;
      paintDraft();
    });
    // O que o aluno digitou fica como digitou (ponto ou vírgula); só os steppers
    // e as sugestões escrevem o número no formato brasileiro.
    repsInput.addEventListener('input', function () {
      if (!draft) return;
      var parsed = format.parseReps(repsInput.value);
      draft.invalidReps = parsed === undefined;
      draft.reps = parsed === undefined ? null : parsed;
      if (draft.reps != null) setError('');
      paintDraft();
    });
    [weightInput, repsInput].forEach(function (input) {
      input.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') { event.preventDefault(); submitSet(); }
      });
    });
    effort.addEventListener('toggle', function () { if (draft) draft.effortOpen = effort.open; });
    q('[data-workout-guided-top-input]').addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      q('[data-workout-guided-top-apply]').click();
    });

    function stepValue(kind, direction) {
      if (kind === 'time') {
        if (!draft || !draft.timed) return;
        var currentSeconds = draft.duration == null ? 0 : draft.duration;
        draft.duration = Math.min(3600, Math.max(5, Math.round((currentSeconds + direction * 5) / 5) * 5));
        draft.invalidDuration = false;
        setError('');
        writeDraftInputs();
        paintDraft();
        return;
      }
      if (kind === 'weight' || kind === 'reps') {
        if (!draft || !model || !model.current) return;
        var series = model.current.series;
        if (kind === 'weight') {
          var step = model.current.movement.loadStep || 2.5;
          if (draft.weight == null) {
            if (direction < 0) return;
            draft.weight = series.weight_kg != null && series.weight_kg !== '' ? Number(series.weight_kg) : step;
          } else {
            draft.weight = format.stepWeight(draft.weight, direction * step);
          }
          draft.invalidWeight = false;
        } else {
          if (draft.reps == null) {
            if (direction < 0) return;
            draft.reps = series.reps != null ? series.reps : 1;
          } else {
            draft.reps = Math.min(999, Math.max(1, draft.reps + direction));
          }
          draft.invalidReps = false;
          setError('');
        }
        writeDraftInputs();
        paintDraft();
        return;
      }
      if (!correction) return;
      if (kind === 'correct-weight') {
        var correctionStep = correction.movement.loadStep || 2.5;
        if (correction.weight == null) {
          if (direction < 0) return;
          correction.weight = correctionStep;
        } else {
          correction.weight = format.stepWeight(correction.weight, direction * correctionStep);
        }
        q('[data-workout-guided-correct-weight]').value = format.decimal(correction.weight);
      } else {
        correction.reps = correction.reps == null ? (direction > 0 ? 1 : null) : Math.min(999, Math.max(1, correction.reps + direction));
        q('[data-workout-guided-correct-reps]').value = correction.reps == null ? '' : String(correction.reps);
      }
    }

    /* ---------- descanso ---------- */
    function paintRest(vm) {
      var section = screens.rest;
      var receipt = vm.receipt;
      q('[data-guided-receipt]', section).textContent = receipt ? format.valueText(receipt.movement, receipt.entry, false) : '';
      var status = q('[data-guided-receipt-status]', section);
      status.className = 'guided-ring__status';
      status.textContent = '';
      if (receipt) {
        if (receipt.sync === 'saved') { status.classList.add('is-saved'); status.textContent = '✓ Salvo'; }
        else if (receipt.sync === 'local') { status.classList.add('is-local'); status.textContent = 'Salvo no aparelho'; }
        else if (receipt.sync === 'blocked') { status.classList.add('is-blocked'); status.textContent = 'Não foi aceito'; }
        else status.textContent = 'Salvando…';
      }
      var next = q('[data-guided-next]', section);
      next.hidden = !vm.current;
      if (vm.current) {
        var movement = vm.current.movement;
        var series = vm.current.series;
        q('[data-guided-next-name]', section).textContent = movement.label;
        var parts = [format.setLabel(movement, series, vm.current.setNumber)];
        if (movement.allowLoad && series.weight_kg != null && series.weight_kg !== '') parts.push(format.kg(series.weight_kg));
        if (series.reps != null) parts.push('meta ' + format.repsText(series));
        q('[data-guided-next-detail]', section).textContent = parts.join(' · ');
      }
      q('[data-workout-guided-extra]', section).hidden = !(receipt && receipt.canAddFreeform);
      if (!vm.rest) return;
      var token = vm.rest.token;
      if (token !== restToken) {
        restToken = token;
        beats = new Set();
        announced = new Set();
        restRing.drain(vm.rest.remainingMs, vm.rest.totalMs);
        restRing.setText(format.clock(vm.rest.seconds));
      }
    }

    // quiet: o push do fim do descanso está agendado e avisa por conta dele
    // (guided-rest-alert.js); o anel segue contando, sem bipe nem vibração.
    function restTick(rest, quiet) {
      qa('[data-guided-rest-chip-time]').forEach(function (element) { element.textContent = format.clock(rest.seconds); });
      [60, 30, 10].forEach(function (mark) {
        if (rest.seconds === mark && rest.totalMs > mark * 1000 && !announced.has(mark)) {
          announced.add(mark);
          announce(mark + ' segundos de descanso');
        }
      });
      if (current !== 'rest' || !dialog.open) return;
      if (rest.seconds <= 3) {
        if (!beats.has(rest.seconds)) {
          beats.add(rest.seconds);
          restRing.beat(rest.seconds);
          if (!quiet) feedback(30, 660);
        }
        return;
      }
      restRing.setText(format.clock(rest.seconds));
      restRing.showRemaining(rest.remainingMs, rest.totalMs);
    }

    function restAdded(rest) {
      restToken = rest.token;
      beats = new Set();
      restRing.drain(rest.remainingMs, rest.totalMs);
      restRing.setText(format.clock(rest.seconds));
    }

    function restDone(quiet) {
      return new Promise(function (resolve) {
        if (current !== 'rest' || !dialog.open) {
          if (dialog.open) toast('Descanso concluído');
          resolve();
          return;
        }
        restRing.go(goWord);
        if (!quiet) feedback(140, 990, 0.24);
        announce('Descanso concluído. Valendo.');
        window.setTimeout(resolve, reduced() ? 350 : 650);
      });
    }

    /* ---------- contagem ---------- */
    function stopCountdown() {
      if (countdownRun) countdownRun.cancel();
      countdownRun = null;
    }
    function countdown(firstLabel, options) {
      options = options || {};
      return new Promise(function (resolve) {
        open();
        showScreen('countdown');
        q('[data-guided-first-prefix]').textContent = options.prefix || 'Primeiro:';
        q('[data-guided-first-name]').textContent = firstLabel || '';
        q('[data-guided-countdown-hint]').textContent = 'Toque para começar agora';
        countdownRing.reset();
        countdownRing.setText('3');
        focusScreen('countdown');
        announce(options.announce || 'Treino começa em 3 segundos');
        stopCountdown();
        countdownRun = Ring.countdown({
          from: 3, goHoldMs: reduced() ? 350 : 650,
          onBeat: function (number) { countdownRing.beat(number); feedback(30, 660); },
          onGo: function () { countdownRing.go(goWord); feedback(90, 990, 0.24); announce('Valendo'); },
          onDone: function (result) { countdownRun = null; resolve(result); },
        });
      });
    }
    /* Isometria: 3, 2, 1 e o cronômetro corre no anel até zerar, ou até o aluno
       parar (registra o tempo sustentado). Cancelar volta ao exercício sem registrar. */
    function hold(options) {
      var total = options.seconds;
      return countdown(options.label, { prefix: 'Segure:', announce: 'Começa em 3 segundos' }).then(function () {
        return new Promise(function (resolve) {
          showScreen('hold');
          q('[data-guided-hold-name]').textContent = options.name || '';
          q('[data-guided-hold-goal]').textContent = 'Meta ' + format.seconds(total);
          var started = Date.now();
          var endAt = started + total * 1000;
          var beeped = new Set();
          function finish(result) {
            if (!holdRun) return;
            window.clearInterval(holdRun.timer);
            holdRun = null;
            resolve(result);
          }
          function tick() {
            var remainingMs = Math.max(0, endAt - Date.now());
            var secondsLeft = Math.ceil(remainingMs / 1000);
            holdRing.setText(format.clock(secondsLeft));
            holdRing.showRemaining(remainingMs, total * 1000);
            if (secondsLeft > 0 && secondsLeft <= 3 && !beeped.has(secondsLeft)) {
              beeped.add(secondsLeft);
              feedback(30, 660);
            }
            if (remainingMs > 0) return;
            feedback(140, 990, 0.24);
            announce('Tempo concluído');
            finish({ seconds: total, completed: true });
          }
          holdRun = {
            timer: window.setInterval(tick, 200),
            stop: function () {
              var held = Math.min(total, Math.max(1, Math.round((Date.now() - started) / 1000)));
              finish({ seconds: held, completed: false });
            },
            cancel: function () { finish(null); },
          };
          holdRing.drain(total * 1000, total * 1000);
          tick();
          focusScreen('hold');
          announce(format.spokenDuration(total) + ', valendo');
        });
      });
    }
    function countdownHint(text) {
      q('[data-guided-countdown-hint]').textContent = text;
      if (current === 'countdown') countdownRing.go(goWord);
    }

    /* ---------- revisão, resumo e fim ---------- */
    function statusIcon(status, now) {
      var ns = 'http://www.w3.org/2000/svg';
      var svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('viewBox', '0 0 26 26');
      svg.setAttribute('class', 'guided-status-icon');
      svg.setAttribute('aria-hidden', 'true');
      function add(tag, attributes) {
        var node = document.createElementNS(ns, tag);
        Object.keys(attributes).forEach(function (name) { node.setAttribute(name, attributes[name]); });
        svg.appendChild(node);
      }
      if (status === 'done') {
        add('circle', { cx: 13, cy: 13, r: 12, style: 'fill:var(--brand)' });
        add('path', { d: 'm8 13.5 3.3 3.3L18.5 9.5', style: 'fill:none;stroke:var(--gf-on-brand);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round' });
      } else if (now) {
        add('circle', { cx: 13, cy: 13, r: 10.5, style: 'fill:none;stroke:var(--brand);stroke-width:3' });
        add('circle', { cx: 13, cy: 13, r: 4.5, style: 'fill:var(--brand)' });
      } else if (status === 'skipped' || status === 'incomplete') {
        add('circle', { cx: 13, cy: 13, r: 10.5, style: 'fill:none;stroke:var(--gf-muted);stroke-width:2.5' });
        add('path', { d: 'M8.5 13h9', style: 'stroke:var(--gf-muted);stroke-width:2.5;stroke-linecap:round' });
      } else if (status === 'started') {
        add('circle', { cx: 13, cy: 13, r: 10.5, style: 'fill:none;stroke:var(--gf-track);stroke-width:3' });
        add('path', { d: 'M13 2.5a10.5 10.5 0 0 1 0 21', style: 'fill:none;stroke:var(--brand);stroke-width:3;stroke-linecap:round' });
      } else {
        add('circle', { cx: 13, cy: 13, r: 10.5, style: 'fill:none;stroke:var(--gf-track);stroke-width:3' });
      }
      return svg;
    }
    function element(tag, className, text) {
      var node = document.createElement(tag);
      if (className) node.className = className;
      if (text != null) node.textContent = text;
      return node;
    }
    function movementName(label, done) {
      var wrapper = element('span', 'guided-sheet__row-name');
      if (!done) { wrapper.textContent = label; return wrapper; }
      wrapper.appendChild(element('span', 'guided-done-name', label));
      wrapper.appendChild(element('span', 'guided-sr', ', concluído'));
      return wrapper;
    }
    function countText(item, isNow) {
      var text = item.done + '/' + item.total;
      if (item.status === 'skipped') text = 'Pulado';
      else if (item.status === 'incomplete') text = item.done + '/' + item.total + ' · ' + item.skipped + (item.skipped > 1 ? ' puladas' : ' pulada');
      return isNow ? 'Agora · ' + item.done + '/' + item.total : text;
    }

    function paintReview(vm) {
      var section = screens.review;
      var review = vm.review;
      setTitle(section, review.movement);
      var status = q('[data-guided-review-status]', section);
      status.textContent = review.statusText;
      status.classList.toggle('is-muted', review.status !== 'done');
      var list = q('[data-guided-review-sets]', section);
      list.replaceChildren();
      review.sets.forEach(function (row) {
        var item = element('li', 'guided-review__set');
        item.appendChild(element('span', 'guided-review__set-name', row.label));
        item.appendChild(element('span', 'guided-review__set-value' + (row.entry ? '' : ' is-muted'), row.valueText));
        if (row.entry) {
          var button = element('button', 'guided-link', 'Corrigir');
          button.type = 'button';
          button.dataset.guidedCorrect = row.key;
          item.appendChild(button);
        } else {
          item.appendChild(element('span'));
        }
        list.appendChild(item);
      });
      var nextLine = q('[data-guided-review-next]', section);
      nextLine.hidden = !review.nextLabel;
      nextLine.textContent = review.nextLabel ? 'Próximo: ' + review.nextLabel : '';
      q('[data-guided-review-continue]', section).textContent = review.nextLabel ? 'Ir para o próximo' : 'Ver resumo';
      var extra = q('[data-guided-review-extra]', section);
      extra.hidden = !review.extra;
      extra.textContent = review.extra ? review.extra.label : '';
      extra.dataset.action = review.extra ? review.extra.action : '';
    }

    function paintSummary(vm) {
      var section = screens.summary;
      var summary = vm.summary;
      q('[data-guided-title]', section).textContent = summary.title;
      q('[data-guided-stat="duration"]', section).textContent = summary.minutes + ' min';
      q('[data-guided-stat="sets"]', section).textContent = String(summary.sets);
      q('[data-guided-stat="movements"]', section).textContent = summary.doneMovements + ' de ' + summary.totalMovements;
      var list = q('[data-guided-summary-list]', section);
      list.replaceChildren();
      vm.state.overview.forEach(function (item, index) {
        var row = element('li', 'guided-summary__item');
        row.appendChild(statusIcon(item.status, false));
        var name = movementName(vm.movements[index].label, item.status === 'done');
        name.className = 'guided-summary__name';
        row.appendChild(name);
        row.appendChild(element('span', 'guided-count', countText(item, false)));
        list.appendChild(row);
      });
      q('[data-workout-guided-finish]', section).hidden = !summary.canFinish;
      q('[data-workout-guided-partial]', section).hidden = summary.canFinish;
      q('[data-guided-back]', section).hidden = !summary.hasPending;
    }

    function paintFinished(vm) {
      var section = screens.finished;
      var finished = vm.finished;
      q('[data-guided-title]', section).textContent = finished.title;
      q('[data-guided-finished-meta]', section).textContent = finished.meta;
      q('[data-guided-finished-ring]', section).hidden = finished.outcome === 'cancel';
    }

    /* ---------- folhas ---------- */
    function openSheetName() {
      var sheet = qa('[data-guided-sheet]').find(function (item) { return !item.hidden; });
      return sheet ? sheet.dataset.guidedSheet : null;
    }
    function setBackgroundInert(value) {
      [chrome, progress].concat(Object.keys(screens).map(function (key) { return screens[key]; })).forEach(function (node) {
        node.inert = value;
      });
    }
    function openSheet(name) {
      closeSheets();
      var sheet = q('[data-guided-sheet="' + name + '"]');
      sheet.hidden = false;
      setBackgroundInert(true);
      if (name === 'workout' && model) paintSheet(model);
      var first = q('[data-guided-autofocus]', sheet);
      if (first) first.focus({ preventScroll: true });
    }
    function closeSheets() {
      var wasOpen = openSheetName();
      qa('[data-guided-sheet]').forEach(function (sheet) { sheet.hidden = true; });
      setBackgroundInert(false);
      disarmCancel();
      correction = null;
      if (wasOpen === 'workout') {
        var opener = q('[data-guided-open-sheet]');
        if (opener && !chrome.hidden) opener.focus({ preventScroll: true });
      }
    }
    function disarmCancel() {
      clearTimeout(cancelArmed);
      cancelArmed = null;
      q('[data-workout-guided-cancel]').textContent = 'Cancelar sessão';
    }

    function paintSheet(vm) {
      var sheet = q('[data-guided-sheet="workout"]');
      var doneCount = vm.state.overview.filter(function (item) { return item.status === 'done'; }).length;
      q('[data-guided-sheet-title]', sheet).textContent = vm.dayTitle || 'Treino de hoje';
      q('[data-guided-sheet-summary]', sheet).textContent = vm.state.recordedCount + ' de ' + vm.state.total + ' séries · '
        + doneCount + ' de ' + vm.state.overview.length + ' exercícios concluídos';
      var nowIndex = current === 'review' ? vm.progressIndex : (current === 'summary' || !vm.current ? -1 : vm.current.movementIndex);
      var list = q('[data-guided-sheet-list]', sheet);
      list.replaceChildren();
      vm.state.overview.forEach(function (item, index) {
        var movement = vm.movements[index];
        var isNow = index === nowIndex;
        var li = element('li');
        var button = element('button', 'guided-sheet__row' + (isNow ? ' is-now' : ''));
        button.type = 'button';
        button.dataset.guidedJump = String(index);
        button.appendChild(statusIcon(item.status, isNow && item.status !== 'done'));
        var main = element('span', 'guided-sheet__row-main');
        main.appendChild(movementName(movement.label, item.status === 'done'));
        var heaviest = movement.series.reduce(function (max, series) {
          var weight = Number(series.weight_kg);
          return Number.isFinite(weight) && weight > max ? weight : max;
        }, 0);
        var sub = item.total + (item.total === 1 ? ' série' : ' séries');
        if (!movement.allowLoad) sub += ' · sem carga';
        else if (heaviest > 0) sub += ' · ' + format.kg(heaviest);
        main.appendChild(element('span', 'guided-sheet__row-sub', sub));
        button.appendChild(main);
        button.appendChild(element('span', 'guided-count', countText(item, isNow)));
        li.appendChild(button);
        list.appendChild(li);
      });
    }

    function openCorrection(data) {
      correction = { key: data.key, movement: data.movement, weight: data.entry.weight_kg == null || data.entry.weight_kg === '' ? null : Number(data.entry.weight_kg), reps: data.entry.reps == null ? null : Number(data.entry.reps) };
      var sheet = q('[data-guided-sheet="correction"]');
      q('[data-guided-correction-title]', sheet).textContent = 'Corrigir ' + data.label.toLowerCase();
      q('[data-guided-correction-name]', sheet).textContent = data.movement.label;
      q('[data-guided-correction-weight-field]', sheet).hidden = !data.movement.allowLoad;
      q('[data-workout-guided-correct-weight]', sheet).value = correction.weight == null ? '' : format.decimal(correction.weight);
      q('[data-workout-guided-correct-reps]', sheet).value = correction.reps == null ? '' : String(correction.reps);
      correctionError('');
      var keep = correction;
      openSheet('correction');
      correction = keep;
    }
    function correctionError(text) {
      var line = q('[data-guided-correction-error]');
      line.textContent = text || '';
      line.hidden = !text;
    }
    function submitCorrection() {
      if (!correction) return;
      var weight = format.parseWeight(q('[data-workout-guided-correct-weight]').value);
      var reps = format.parseReps(q('[data-workout-guided-correct-reps]').value);
      if (weight === undefined) { correctionError('Confira a carga: use números com até duas casas decimais.'); return; }
      if (reps === undefined || reps == null) { correctionError('Informe as repetições da série.'); return; }
      correctionError('');
      emit('correct', { key: correction.key, weight: correction.movement.allowLoad ? weight : null, reps: reps });
    }

    /* ---------- aviso ---------- */
    /* `persist`: avisos que pedem decisão (conflito da fila) só saem com a ação. */
    function toast(text, actionLabel, onAction, persist) {
      clearTimeout(toastTimer);
      q('[data-guided-toast-text]').textContent = text;
      var action = q('[data-guided-toast-action]');
      action.hidden = !actionLabel;
      action.textContent = actionLabel || '';
      action.onclick = actionLabel ? function () { hideToast(); onAction(); } : null;
      toastEl.hidden = false;
      if (!persist) toastTimer = setTimeout(hideToast, actionLabel ? 5000 : 3200);
    }
    function hideToast() {
      clearTimeout(toastTimer);
      toastEl.hidden = true;
    }

    /* ---------- eventos da tela ---------- */
    ['pointerup', 'touchend', 'click', 'keydown'].forEach(function (type) {
      dialog.addEventListener(type, unlockAudio, true);
    });
    dialog.addEventListener('click', function (event) {
      var target = event.target.closest('button, a');
      if (!target || !dialog.contains(target)) return;
      if (target.matches('[data-guided-countdown-skip]')) { if (countdownRun) countdownRun.skip(); return; }
      if (target.matches('[data-guided-hold-stop]')) { if (holdRun) holdRun.stop(); return; }
      if (target.matches('[data-guided-hold-cancel]')) { if (holdRun) holdRun.cancel(); return; }
      if (target.matches('[data-guided-time-direct]')) {
        // Fez a prancha sem o cronômetro do app: registra o tempo do campo direto.
        if (draft && draft.timed && validDuration()) {
          emit('record', { key: draft.key, weight: null, reps: null, rir: null, duration: draft.duration });
        }
        return;
      }
      if (target.matches('[data-guided-video]')) { emit('video'); return; }
      if (target.matches('[data-guided-minimize]')) { emit('minimize'); return; }
      if (target.matches('[data-guided-open-sheet]')) { openSheet('workout'); return; }
      if (target.matches('[data-guided-sheet-close]')) { closeSheets(); return; }
      if (target.matches('[data-guided-jump]')) { emit('jump', { index: Number(target.dataset.guidedJump) }); return; }
      if (target.matches('[data-guided-step]')) { stepValue(target.dataset.guidedStep, Number(target.dataset.delta)); return; }
      if (target.matches('[data-guided-rir]')) {
        if (!draft) return;
        var value = Number(target.dataset.guidedRir);
        draft.rir = draft.rir === value ? null : value;
        paintDraft();
        return;
      }
      if (target.matches('[data-guided-rir-clear]')) { if (draft) { draft.rir = null; effort.open = false; paintDraft(); } return; }
      if (target.matches('[data-guided-weight-reset]')) {
        if (draft) { draft.weight = draft.base; draft.invalidWeight = false; writeDraftInputs(); paintDraft(); }
        return;
      }
      if (target.matches('[data-workout-guided-set]')) { submitSet(); return; }
      if (target.matches('[data-workout-guided-top-apply]')) {
        setError('');
        emit('top-target', { raw: q('[data-workout-guided-top-input]').value });
        q('[data-workout-guided-top-target]').open = false;
        return;
      }
      if (target.matches('[data-workout-guided-skip]')) { emit('skip-set'); return; }
      if (target.matches('[data-guided-correct-last]')) { emit('correct-request', { key: model && model.lastRecordedKey }); return; }
      if (target.matches('[data-guided-correct]')) {
        // Série por tempo não tem carga/repetições para corrigir: refaz a série.
        if (model && timedKey(model, target.dataset.guidedCorrect)) { toast('Série por tempo: refaça a série para mudar o tempo.'); return; }
        emit('correct-request', { key: target.dataset.guidedCorrect });
        return;
      }
      if (target.matches('[data-workout-guided-correct-save]')) { submitCorrection(); return; }
      if (target.matches('[data-guided-skip-rest]')) { emit('skip-rest'); return; }
      if (target.matches('[data-guided-add-rest]')) { emit('add-rest'); return; }
      if (target.matches('[data-guided-rest-chip]')) { emit('to-rest'); return; }
      if (target.matches('[data-workout-guided-extra]')) { emit('extra'); return; }
      if (target.matches('[data-guided-review-continue]')) { emit('review-continue'); return; }
      if (target.matches('[data-guided-review-extra]')) { emit('review-extra', { action: target.dataset.action }); return; }
      if (target.matches('[data-guided-open-summary]')) { emit('open-summary'); return; }
      if (target.matches('[data-guided-back]')) { emit('back'); return; }
      if (target.matches('[data-workout-guided-finish]')) { emit('end', { outcome: 'complete' }); return; }
      if (target.matches('[data-workout-guided-partial]')) { emit('end', { outcome: 'partial' }); return; }
      if (target.matches('[data-workout-guided-cancel]')) {
        if (!cancelArmed) {
          target.textContent = 'Toque de novo para cancelar a sessão';
          cancelArmed = setTimeout(disarmCancel, 4000);
        } else {
          disarmCancel();
          emit('end', { outcome: 'cancel' });
        }
        return;
      }
      if (target.matches('[data-guided-sound]')) {
        soundOn = !soundOn;
        target.setAttribute('aria-checked', String(soundOn));
        try { window.localStorage.setItem(SOUND_KEY, soundOn ? '1' : '0'); } catch (_) { /* preferência só nesta visita */ }
        if (soundOn) {
          unlockAudio();
          beep(880, 0.08);
        }
        return;
      }
      if (target.matches('[data-guided-close]')) emit('close');
    });

    return {
      show: show,
      refresh: function (vm) { if (current && current !== 'countdown' && dialog.open) show(current, vm); else model = vm; },
      countdown: countdown,
      countdownHint: countdownHint,
      isHolding: function () { return !!holdRun; },
      restTick: restTick,
      restAdded: restAdded,
      restDone: restDone,
      openSheet: openSheet,
      closeSheets: closeSheets,
      openCorrection: openCorrection,
      correctionError: correctionError,
      error: setError,
      toast: toast,
      announce: announce,
      close: close,
      isOpen: function () { return dialog.open; },
      screen: function () { return current; },
    };
  }

  window.CurvaGuidedFocus = { create: create };
}());
