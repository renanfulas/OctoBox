/* Coach de voz do treino guiado: a voz do Renan por cima da música do aluno.
 *
 * Plano: docs/plans/curva-coach-voz-guiada.md. As falas são MP3 gerados em
 * lote (scripts/coach_voice/build_coach_voice.py) e listados no manifest.json
 * do pacote; este módulo só escolhe quais tocar e quando.
 *
 * Regra de ouro: silêncio durante a série. A próxima série é anunciada no fim
 * do descanso (faltando ANNOUNCE_AT_MS), para o aluno montar a carga com calma.
 * Descanso curto demais para dois avisos anuncia logo depois do "Descansa".
 *
 * No iPhone o PWA não consegue abaixar nem pausar-e-retomar o Spotify (spike
 * de 2026-11-12): a voz toca por cima, em audioSession 'ambient', e o pacote
 * já sai mixado para "furar" a música. O bip antes de cada fala chama a
 * atenção. Áudio, relógio e armazenamento são injetáveis para os testes em Node.
 */
(function () {
  'use strict';

  var ANNOUNCE_AT_MS = 15000;
  // Abaixo disso o anúncio sai logo depois do "Descansa" (não cabem os dois).
  var SHORT_REST_MS = 25000;
  var GAP_MS = 150;
  var STORAGE_KEY = 'curva-coach-voice';

  function kgKey(kg) {
    return String(Math.round(Number(kg) * 100) / 100).replace('.', '_');
  }

  /* ---------- escolha das falas (puro) ---------- */
  function variants(manifest, event) {
    var prefix = event + '__v';
    return Object.keys(manifest.clips || {}).filter(function (id) { return id.indexOf(prefix) === 0; }).sort();
  }

  // Revezamento sem repetir: a variante menos usada na sessão, em ordem estável.
  function pick(manifest, event, used) {
    var options = variants(manifest, event);
    if (!options.length) return null;
    var choice = options.reduce(function (best, id) {
      return (used[id] || 0) < (used[best] || 0) ? id : best;
    }, options[0]);
    used[choice] = (used[choice] || 0) + 1;
    return choice;
  }

  function has(manifest, id) { return !!(manifest.clips && manifest.clips[id]); }

  // Falas que anunciam uma série: fase + carga + reps (+ "é a última").
  function setPhrases(manifest, step, used) {
    if (!step || !step.series || step.movement.freeform) return [];
    var series = step.series;
    var kg = Number(series.weight_kg);
    var hasKg = step.movement.allowLoad !== false && kg > 0;
    var ids = [];
    if (series.stage === 'top') {
      var top = 'set_top__kg' + kgKey(kg);
      ids.push(hasKg && has(manifest, top) ? top : pick(manifest, 'set_top_noload', used));
    } else {
      var intro = { prep: hasKg ? 'set_prep_loaded' : 'set_prep', feeder: 'set_feeder', max: 'set_max' }[series.stage]
        || 'set_plain';
      ids.push(pick(manifest, intro, used));
      if (hasKg) {
        var load = 'load__kg' + kgKey(kg);
        ids.push(has(manifest, load) ? load : pick(manifest, 'load_unknown', used));
      }
    }
    // Faixa de reps ("1-3") fica na tela: o pacote só tem número único.
    var reps = Number(series.reps);
    var exact = reps > 0 && (series.reps_max == null || Number(series.reps_max) === reps);
    if (exact && has(manifest, 'set_reps__r' + reps)) ids.push('set_reps__r' + reps);
    if (step.setNumber === step.movement.series.length) ids.push(pick(manifest, 'set_last', used));
    return ids.filter(function (id) { return id && has(manifest, id); });
  }

  /* ---------- reprodução ---------- */
  // Teto de uma fala: se o navegador não avisar o fim (pausa externa, aba em
  // segundo plano), a fila segue em vez de travar o resto do treino.
  var CLIP_TIMEOUT_MS = 12000;

  function browserAudio() {
    var element = new Audio();
    element.preload = 'auto';
    var ready = Promise.resolve();
    var unlocked = false;
    var busy = false;
    return {
      play: function (url) {
        return ready.then(function () {
          return new Promise(function (resolve) {
            var timer = null;
            var done = function () {
              clearTimeout(timer);
              element.removeEventListener('ended', done);
              element.removeEventListener('error', done);
              element.removeEventListener('pause', done);
              busy = false;
              resolve();
            };
            busy = true;
            element.addEventListener('ended', done);
            element.addEventListener('error', done);
            element.addEventListener('pause', done);
            timer = setTimeout(done, CLIP_TIMEOUT_MS);
            element.src = url;
            var playing = element.play();
            if (playing && playing.catch) playing.catch(done);
          });
        });
      },
      // Precisa rodar dentro do toque do aluno: o iOS só libera áudio assim.
      // Uma vez por página, e nunca por cima de uma fala: o desbloqueio troca a
      // fonte do player e pausaria a fala em andamento.
      unlock: function (url) {
        try { if (navigator.audioSession) navigator.audioSession.type = 'ambient'; } catch (_) { /* Safari antigo */ }
        if (unlocked || busy) return;
        unlocked = true;
        element.muted = true;
        element.src = url;
        var playing = element.play();
        ready = new Promise(function (resolve) {
          var restore = function () { element.pause(); element.muted = false; resolve(); };
          if (playing && playing.then) playing.then(restore, restore); else restore();
        });
      },
      stop: function () { element.pause(); },
    };
  }

  function browserStorage() {
    try { return window.localStorage; } catch (_) { return null; }
  }

  function create(options) {
    options = options || {};
    var base = options.baseUrl || '';
    var audio = options.audio || browserAudio();
    var storage = options.storage === undefined ? browserStorage() : options.storage;
    var wait = options.wait || function (ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); };
    var manifest = options.manifest || null;
    var used = {};
    var queue = [];
    var running = false;
    var pending = null; // próxima série a anunciar no fim do descanso

    function read(name) { try { return storage ? storage.getItem(name) : null; } catch (_) { return null; } }
    function write(name, value) { try { if (storage) storage.setItem(name, value); } catch (_) { /* aba anônima */ } }

    function enabled() { return !!manifest && read(STORAGE_KEY) === 'on'; }
    function url(id) { return base + manifest.clips[id].file; }

    function drain() {
      if (running || !queue.length) return Promise.resolve();
      running = true;
      var group = queue.shift();
      var chain = audio.play(base + (manifest.beep || 'bip.mp3')).then(function () { return wait(GAP_MS); });
      group.forEach(function (id) {
        chain = chain.then(function () { return audio.play(url(id)); }).then(function () { return wait(GAP_MS); });
      });
      return chain.catch(function () { /* voz é conforto: falha não trava o treino */ }).then(function () {
        running = false;
        return drain();
      });
    }

    function say(ids) {
      ids = (ids || []).filter(function (id) { return id && manifest && manifest.clips[id]; });
      if (!enabled() || !ids.length) return Promise.resolve();
      queue.push(ids);
      return drain();
    }

    function announcement(next, changed) {
      return (changed ? [pick(manifest, 'exercise_start', used)] : []).concat(setPhrases(manifest, next, used));
    }

    return {
      load: function () {
        if (manifest || !options.manifestUrl) return Promise.resolve(manifest);
        var fetcher = options.fetch || window.fetch.bind(window);
        return fetcher(options.manifestUrl).then(function (response) {
          if (!response.ok) throw new Error('coach-manifest-' + response.status);
          return response.json();
        }).then(function (data) { manifest = data; return data; }).catch(function () { return null; });
      },
      enabled: enabled,
      setEnabled: function (on) { write(STORAGE_KEY, on ? 'on' : 'off'); },
      available: function () { return !!manifest; },
      // URLs das falas que este treino pode usar, para o pré-cache offline.
      urlsFor: function (movements) {
        if (!manifest) return [];
        var ids = Object.keys(manifest.clips).filter(function (id) { return !/__(kg|r|s)\d/.test(id); });
        movements.forEach(function (movement) {
          movement.series.forEach(function (series) {
            if (series.weight_kg > 0) ids.push('set_top__kg' + kgKey(series.weight_kg), 'load__kg' + kgKey(series.weight_kg));
            if (series.reps > 0) ids.push('set_reps__r' + Number(series.reps));
            if (series.rest_seconds > 0) ids.push('rest_start__s' + Number(series.rest_seconds));
          });
          if (movement.supersetRestSeconds) ids.push('rest_start__s' + movement.supersetRestSeconds);
        });
        var unique = ids.filter(function (id, index) { return manifest.clips[id] && ids.indexOf(id) === index; });
        return [base + (manifest.beep || 'bip.mp3')].concat(unique.map(url));
      },
      unlock: function () { if (manifest) audio.unlock(base + (manifest.beep || 'bip.mp3')); },
      test: function () {
        var wasOn = read(STORAGE_KEY);
        write(STORAGE_KEY, 'on');
        var done = say(['set_top__kg82_5'].filter(function (id) { return has(manifest, id); })
          .concat(pick(manifest, 'set_logged', used)));
        write(STORAGE_KEY, wasOn || 'off');
        return done;
      },
      // Treino começou (dentro do toque): boas-vindas + 1ª série.
      started: function (first) {
        pending = null;
        if (!enabled()) return Promise.resolve();
        return say([pick(manifest, 'workout_start', used), pick(manifest, 'exercise_start', used)]
          .concat(setPhrases(manifest, first, used)));
      },
      // Série registrada: confirma, avisa o descanso e guarda o anúncio da próxima.
      setRecorded: function (detail) {
        pending = null;
        if (!enabled()) return Promise.resolve();
        var next = detail.next;
        var changed = !!next && next.movementIndex !== detail.step.movementIndex;
        var ids = [pick(manifest, 'set_logged', used)];
        if (!next) return say(ids);
        var rest = Number(detail.restSeconds) || 0;
        if (rest <= 0) {
          if (detail.superset) ids.push(pick(manifest, 'superset_next', used));
          return say(ids.concat(announcement(next, changed && !detail.superset)));
        }
        if (has(manifest, 'rest_start__s' + rest)) ids.push('rest_start__s' + rest);
        if (rest * 1000 < SHORT_REST_MS) return say(ids.concat(announcement(next, changed)));
        pending = { next: next, changed: changed };
        return say(ids);
      },
      // Tique do relógio do descanso: chegou a hora do anúncio da próxima.
      restTick: function (remainingMs) {
        if (!pending || remainingMs > ANNOUNCE_AT_MS) return Promise.resolve();
        var target = pending;
        pending = null;
        return say(announcement(target.next, target.changed));
      },
      // Pulou o descanso antes do anúncio: anuncia já.
      restSkipped: function () {
        if (!pending) return Promise.resolve();
        var target = pending;
        pending = null;
        return say(announcement(target.next, target.changed));
      },
      finished: function (outcome) {
        pending = null;
        queue.length = 0;
        if (outcome === 'complete') return say([pick(manifest, 'workout_end', used)]);
        audio.stop();
        return Promise.resolve();
      },
    };
  }

  window.CurvaGuidedVoice = {
    create: create, setPhrases: setPhrases, kgKey: kgKey,
    ANNOUNCE_AT_MS: ANNOUNCE_AT_MS, STORAGE_KEY: STORAGE_KEY,
  };
}());
