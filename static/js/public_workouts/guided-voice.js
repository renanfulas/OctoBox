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
 * Exceção: top set e AMRAP, quando o aluno toca "Contar comigo". O celular não
 * vê a repetição, então a voz DITA o ritmo (REP_MS por rep, mais lento perto
 * da falha) e o aluno acompanha: número no alto da subida, dica na descida.
 * "Parei" encerra e devolve quantas repetições foram contadas, menos a rep
 * anunciada há menos de STOP_GRACE_MS (o aluno larga a barra antes de tocar).
 *
 * Fala atrasada não toca: com o app em segundo plano o navegador congela os
 * timers, e na volta as reps vencidas sairiam em rajada. O número na tela
 * segue o relógio; a voz retoma na próxima rep no horário.
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

  /* ---------- contagem intra-série (puro) ---------- */
  var COUNT_MAX = 30;
  var REP_MS = 3000;
  // "Parei" até 2,5 s depois de uma rep anunciada não conta essa rep: quem parou
  // na 11ª ainda está largando a barra quando a voz diz "doze".
  var STOP_GRACE_MS = 2500;
  // Evento da contagem que acorda mais atrasado que isso (app em segundo plano,
  // tela bloqueada) atualiza a tela mas não fala.
  var LATE_MS = 1000;

  function countTarget(series) {
    var target = Number(series.reps_max || series.reps);
    return target >= 1 && target <= COUNT_MAX ? Math.round(target) : null;
  }

  // 'top' (conta até a meta e fecha) | 'max' (AMRAP: passa da meta até o "Parei") | null
  function countMode(step) {
    if (!step || !step.series || step.movement.freeform) return null;
    var series = step.series;
    if (series.hold_seconds != null && series.hold_seconds !== '') return null; // isometria tem cronômetro
    if (series.stage === 'max' || series.amrap === true) return 'max';
    return series.stage === 'top' && countTarget(series) ? 'top' : null;
  }

  // Roteiro: cada rep com a fala e o instante em que ela termina (ms desde o
  // "valendo"). A fala sai no alto da subida; na última da top set, o "sobe,
  // sobe" entra no fundo da descida (pushMs).
  function countPlan(manifest, step) {
    var mode = countMode(step);
    if (!mode || !manifest) return null;
    var goal = countTarget(step.series);
    var pivot = goal || 5; // AMRAP sem meta: depois da 5ª já é "passou da meta"
    var last = mode === 'top' ? goal : COUNT_MAX;
    var half = goal && goal >= 6 ? Math.floor(goal / 2) : null;
    var reps = [];
    var at = 0;
    var cue = 0;
    var beyond = 0;
    for (var n = 1; n <= last; n += 1) {
      var id;
      var dur = REP_MS;
      var push = null;
      if (mode === 'top' && n === goal) {
        id = 'count_last__r' + n; dur = 4000; push = at + 2000;
      } else if (mode === 'max' && n === goal) {
        id = 'count_goal__r' + n; dur = 3500;
      } else if (mode === 'max' && n === pivot + 1) {
        id = 'count_safety__r' + n; dur = 4000;
      } else if (mode === 'max' && n > pivot) {
        id = 'count_beyond__r' + n + '_v' + (beyond % 3 + 1); beyond += 1;
        dur = n - pivot >= 4 ? 5000 : (n - pivot === 3 ? 4500 : 4000);
      } else if (goal && goal >= 2 && n === goal - 1) {
        id = 'count_left1__r' + n; if (mode === 'top') dur = 3500;
      } else if (goal && goal >= 4 && n === goal - 2) {
        id = 'count_left2__r' + n;
      } else if (n === half) {
        id = 'count_half__r' + n;
      } else {
        id = 'count__r' + n + '_v' + (cue % 4 + 1); cue += 1;
      }
      if (!has(manifest, id)) id = has(manifest, 'count__r' + n + '_v1') ? 'count__r' + n + '_v1' : null;
      reps.push({ n: n, id: id, endMs: at + dur, pushMs: push });
      at += dur;
    }
    return { mode: mode, goal: goal, reps: reps };
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
    var now = options.now || function () { return Date.now(); };
    var counting = null; // contagem intra-série em andamento

    function read(name) { try { return storage ? storage.getItem(name) : null; } catch (_) { return null; } }
    function write(name, value) { try { if (storage) storage.setItem(name, value); } catch (_) { /* aba anônima */ } }

    function enabled() { return !!manifest && read(STORAGE_KEY) === 'on'; }
    function url(id) { return base + manifest.clips[id].file; }

    var current = null; // grupo tocando agora
    function drain() {
      if (running || !queue.length) return Promise.resolve();
      running = true;
      var group = current = queue.shift();
      // Grupo cortado (flush) para no meio: o resto das falas dele não toca.
      var step = function (run) { return function () { return group.cancelled ? null : run(); }; };
      var chain = Promise.resolve();
      if (group.beep) {
        chain = chain.then(step(function () { return audio.play(base + (manifest.beep || 'bip.mp3')); }))
          .then(step(function () { return wait(GAP_MS); }));
      }
      group.urls.forEach(function (address) {
        chain = chain.then(step(function () { return audio.play(address); }))
          .then(step(function () { return wait(group.gap); }));
      });
      return chain.catch(function () { /* voz é conforto: falha não trava o treino */ }).then(function () {
        current = null;
        running = false;
        group.done();
        return drain();
      });
    }

    // Resolve quando ESTE grupo terminou de tocar (ou foi cortado), não quando
    // entrou na fila: a contagem espera o preparo acabar antes do 3-2-1.
    function enqueue(group) {
      return new Promise(function (resolve) {
        group.done = resolve;
        queue.push(group);
        drain();
      });
    }

    function dropQueued() {
      queue.splice(0).forEach(function (group) { group.cancelled = true; group.done(); });
    }

    // Corta tudo, inclusive a fala em andamento.
    function flush() {
      dropQueued();
      if (current) current.cancelled = true;
      audio.stop();
    }

    function say(ids) {
      ids = (ids || []).filter(function (id) { return id && manifest && manifest.clips[id]; });
      if (!enabled() || !ids.length) return Promise.resolve();
      return enqueue({ urls: ids.map(url), beep: true, gap: GAP_MS });
    }

    // Sem bip e sem folga: contagem e bips do 3-2-1 têm hora marcada.
    function sound(urls) {
      urls = urls.filter(Boolean);
      if (!enabled() || !urls.length) return Promise.resolve();
      return enqueue({ urls: urls, beep: false, gap: 0 });
    }
    function clip(id) { return id && has(manifest, id) ? url(id) : null; }
    function asset(name) { return manifest[name] ? base + manifest[name] : null; }

    function stopCount() {
      if (!counting) return false;
      counting = null;
      flush();
      return true;
    }

    // Linha do tempo absoluta (now()), não soma de esperas: um atraso de uma
    // fala não empurra o ritmo das seguintes.
    var STOPPED = {};
    function runCount(plan, token, hooks) {
      var live = function () { return !!counting && counting.token === token; };
      var at = function (when, action) {
        return function () {
          if (!live()) throw STOPPED;
          return wait(Math.max(0, when - now())).then(function () {
            if (!live()) throw STOPPED;
            action(now() - when > LATE_MS, when);
          });
        };
      };
      // Som com hora marcada: atrasado, fica calado.
      var cue = function (late, urls) { if (!late) sound(urls); };
      var setup = pick(manifest, plan.mode === 'top' ? 'count_setup_top' : 'count_setup_max', used);
      return say([setup]).then(function () {
        if (!live()) throw STOPPED;
        var start = now();
        var go = start + 4200;
        var events = [1200, 2200, 3200].map(function (ms) {
          return { t: start + ms, run: function (late) { cue(late, [asset('tick')]); } };
        });
        events.push({ t: go, run: function (late) { cue(late, [asset('go'), clip(pick(manifest, 'count_go', used))]); } });
        plan.reps.forEach(function (rep) {
          if (rep.pushMs != null) {
            events.push({ t: go + rep.pushMs, run: function (late) { cue(late, [clip(pick(manifest, 'count_push', used))]); } });
          }
          events.push({ t: go + rep.endMs - 100, run: function (late, when) {
            counting.done = rep.n;
            counting.doneAt = when;
            cue(late, [clip(rep.id)]);
            if (hooks.onRep) hooks.onRep(rep.n);
          } });
        });
        if (plan.mode === 'top') {
          var end = go + plan.reps[plan.reps.length - 1].endMs;
          events.push({ t: end + 2000, run: function (late) { cue(late, [clip(pick(manifest, 'count_done_top', used))]); } });
        }
        events.sort(function (a, b) { return a.t - b.t; });
        return events.reduce(function (chain, event) { return chain.then(at(event.t, event.run)); }, Promise.resolve());
      }).then(function () {
        var done = counting.done;
        counting = null;
        if (hooks.onDone) hooks.onDone(done);
      }, function (error) {
        if (error !== STOPPED) { counting = null; throw error; }
      });
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
        var counts = false;
        movements.forEach(function (movement) {
          movement.series.forEach(function (series) {
            if (series.weight_kg > 0) ids.push('set_top__kg' + kgKey(series.weight_kg), 'load__kg' + kgKey(series.weight_kg));
            if (series.reps > 0) ids.push('set_reps__r' + Number(series.reps));
            if (series.rest_seconds > 0) ids.push('rest_start__s' + Number(series.rest_seconds));
          });
          if (movement.supersetRestSeconds) ids.push('rest_start__s' + movement.supersetRestSeconds);
          // Top set / AMRAP: o roteiro inteiro da contagem + o "fechou em N" de cada rep.
          movement.series.forEach(function (series, index) {
            var plan = countPlan(manifest, { movement: movement, series: series, setNumber: index + 1 });
            if (!plan) return;
            counts = true;
            plan.reps.forEach(function (rep) { ids.push(rep.id, 'count_stop__r' + rep.n); });
          });
        });
        if (!counts) ids = ids.filter(function (id) { return id.indexOf('count_') !== 0; });
        var unique = ids.filter(function (id, index) { return manifest.clips[id] && ids.indexOf(id) === index; });
        var sounds = [base + (manifest.beep || 'bip.mp3')];
        if (counts) sounds = sounds.concat([manifest.tick, manifest.go].filter(Boolean).map(function (name) { return base + name; }));
        return sounds.concat(unique.map(url));
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
      // Contagem intra-série: só top set / AMRAP, com a voz ligada.
      countable: function (step) { return enabled() && !!countPlan(manifest, step); },
      counting: function () { return !!counting; },
      // Toque "Contar comigo" (dentro do toque: libera o áudio no iOS).
      // hooks.onRep(n) a cada repetição ditada; hooks.onDone(n) quando a top set fecha.
      countStart: function (step, hooks) {
        var plan = enabled() ? countPlan(manifest, step) : null;
        if (!plan) return Promise.resolve();
        stopCount();
        // O aluno já está na barra: o anúncio da série que ainda toca sai da frente
        // do preparo (senão o 3-2-1 entra na fila atrás dele e o áudio atrasa).
        flush();
        pending = null;
        var token = {};
        counting = { token: token, done: 0, doneAt: 0 };
        return runCount(plan, token, hooks || {}).catch(function () { /* voz é conforto */ });
      },
      // "Parei": para a contagem e devolve quantas repetições o aluno fez — a
      // voz contou `done`, mas a anunciada há menos de STOP_GRACE_MS não vale.
      countStop: function () {
        var done = counting ? counting.done : 0;
        if (done > 0 && now() - counting.doneAt < STOP_GRACE_MS) done -= 1;
        if (!stopCount()) return 0;
        if (done > 0) sound([clip('count_stop__r' + done)]);
        return done;
      },
      countCancel: function () { stopCount(); },
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
        stopCount();
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
        counting = null;
        if (outcome === 'complete') {
          dropQueued();
          return say([pick(manifest, 'workout_end', used)]);
        }
        flush();
        return Promise.resolve();
      },
    };
  }

  // Liga o coach à tela do treino guiado (workout-guided.js): toggle do lançador,
  // "Contar comigo" no foco e pré-cache das falas. `host` diz qual é a série atual;
  // sem pacote publicado (data-coach-voice-manifest) tudo vira no-op.
  function attach(root, dialog, host) {
    var voice = root.dataset.coachVoiceManifest ? create({
      manifestUrl: root.dataset.coachVoiceManifest, baseUrl: root.dataset.coachVoiceBase,
    }) : null;
    var countBox = voice ? dialog.querySelector('[data-guided-count]') : null;
    var countKey = null;
    function call(method) {
      if (!voice) return;
      var args = Array.prototype.slice.call(arguments, 1);
      try { voice[method].apply(voice, args); } catch (_) { /* voz é conforto: nunca trava o treino */ }
    }
    function paint() {
      if (!countBox) return;
      var counting = voice.counting();
      var step = host.step();
      // Saiu da série que estava contando (registrou, pulou, minimizou): a voz para.
      if (counting && (!host.inExercise() || !step || countKey !== host.key(step))) {
        voice.countCancel();
        counting = false;
      }
      countBox.hidden = !(host.inExercise() && !!step && (counting || voice.countable(step)));
      countBox.querySelector('[data-guided-count-start]').hidden = counting;
      countBox.querySelector('[data-guided-count-live]').hidden = !counting;
    }
    var box = voice ? root.querySelector('[data-coach-voice]') : null;
    if (box) {
      var toggle = box.querySelector('[data-coach-voice-toggle]');
      var help = box.querySelector('[data-coach-voice-help]');
      voice.load().then(function (manifest) {
        if (!manifest) return; // pacote fora do ar: o lançador segue sem a opção
        box.hidden = false;
        toggle.checked = voice.enabled();
        help.hidden = !toggle.checked;
      });
      toggle.addEventListener('change', function () {
        voice.setEnabled(toggle.checked);
        help.hidden = !toggle.checked;
        if (toggle.checked) voice.unlock();
      });
      box.querySelector('[data-coach-voice-test]').addEventListener('click', function () {
        voice.unlock();
        voice.test();
      });
    }
    if (countBox) {
      var value = countBox.querySelector('[data-guided-count-value]');
      var unit = countBox.querySelector('[data-guided-count-unit]');
      var live = countBox.querySelector('[data-guided-count-live]');
      var show = function (n) { value.textContent = String(n); if (unit) unit.textContent = host.repWord(n); };
      countBox.querySelector('[data-guided-count-start]').addEventListener('click', function () {
        var step = host.step();
        if (!step) return;
        voice.unlock();
        var setKey = countKey = host.key(step);
        show(0);
        voice.countStart(step, {
          onRep: show,
          onDone: function (n) { host.fillReps(setKey, n); paint(); },
        });
        paint();
        countBox.querySelector('[data-guided-count-stop]').focus({ preventScroll: true });
      });
      // Durante a contagem a tela inteira é o "Parei": o aluno acabou de largar a
      // barra e não vai mirar num botão. O botão continua lá para teclado/leitor.
      live.addEventListener('click', function () {
        if (!voice.counting()) return;
        host.fillReps(countKey, voice.countStop());
        paint();
      });
    }
    // As falas deste treino passam pelo service worker, que as guarda para o
    // modo offline (cache curva-coach-audio-*). Uma por vez: rede de academia.
    function precache(preview) {
      if (!voice || !voice.enabled() || !window.fetch) return;
      voice.urlsFor(preview).reduce(function (chain, url) {
        return chain.then(function () { return fetch(url, { credentials: 'same-origin' }).catch(function () {}); });
      }, Promise.resolve());
    }
    return { call: call, paint: paint, precache: precache };
  }

  window.CurvaGuidedVoice = {
    create: create, attach: attach, setPhrases: setPhrases, kgKey: kgKey, countPlan: countPlan, countMode: countMode,
    ANNOUNCE_AT_MS: ANNOUNCE_AT_MS, STORAGE_KEY: STORAGE_KEY, STOP_GRACE_MS: STOP_GRACE_MS, LATE_MS: LATE_MS,
  };
}());
