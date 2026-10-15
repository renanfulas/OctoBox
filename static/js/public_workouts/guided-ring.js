/* Anel do modo foco: contagem 3-2-1-GO e descanso esvaziando.
 *
 * Componente visual: não conhece sessão, série nem rede. Opera sobre a marcação
 * já renderizada no servidor ([data-ring-progress] + [data-ring-value]).
 * Desenha só com o traço do SVG, transform e opacity; com movimento reduzido,
 * mostra o progresso estático. A sequência da contagem recebe o agendador por
 * injeção para ser testada em Node (tests/js/curva_guided_ring.test.js).
 */
(function () {
  'use strict';

  var RADIUS = 108;
  var CIRCUMFERENCE = 2 * Math.PI * RADIUS;

  function offsetFor(remainingMs, totalMs) {
    if (!(totalMs > 0)) return CIRCUMFERENCE;
    var fraction = Math.min(1, Math.max(0, remainingMs / totalMs));
    return CIRCUMFERENCE * (1 - fraction);
  }

  function countdown(options) {
    var from = options.from || 3;
    var schedule = options.setTimeout || function (fn, ms) { return setTimeout(fn, ms); };
    var cancel = options.clearTimeout || function (id) { clearTimeout(id); };
    var holdMs = options.goHoldMs == null ? 650 : options.goHoldMs;
    var current = from;
    var handle = null;
    var finished = false;

    function finish(skipped) {
      if (finished) return;
      finished = true;
      cancel(handle);
      if (options.onDone) options.onDone({ skipped: !!skipped });
    }
    function step() {
      if (finished) return;
      if (current > 0) {
        if (options.onBeat) options.onBeat(current);
        current -= 1;
        handle = schedule(step, 1000);
        return;
      }
      if (options.onGo) options.onGo();
      handle = schedule(function () { finish(false); }, holdMs);
    }
    handle = schedule(step, 0);
    return {
      skip: function () { finish(true); },
      cancel: function () { finished = true; cancel(handle); },
    };
  }

  function create(element, options) {
    options = options || {};
    var progress = element.querySelector('[data-ring-progress]');
    var value = element.querySelector('[data-ring-value]');
    var reduced = options.reducedMotion || function () { return false; };

    function cancelAnimations() {
      if (progress && progress.getAnimations) progress.getAnimations().forEach(function (item) { item.cancel(); });
    }
    function setOffset(offset) {
      if (progress) progress.style.strokeDashoffset = offset + 'px';
    }
    function sweep(from, to, duration) {
      cancelAnimations();
      setOffset(to);
      if (reduced() || !progress || !progress.animate) return;
      progress.animate(
        [{ strokeDashoffset: from + 'px' }, { strokeDashoffset: to + 'px' }],
        { duration: duration, easing: 'linear' }
      );
    }
    function pop(big) {
      if (reduced() || !value || !value.animate) return;
      var frames = big
        ? [{ transform: 'scale(.82)', opacity: 0 }, { transform: 'scale(1.08)', opacity: 1, offset: 0.6 }, { transform: 'scale(1)', opacity: 1 }]
        : [{ transform: 'scale(1.3)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }];
      value.animate(frames, { duration: big ? 340 : 180, easing: 'cubic-bezier(.2,.8,.2,1)' });
    }
    function mode(name) {
      element.classList.toggle('is-beat', name === 'beat');
      element.classList.toggle('is-go', name === 'go');
    }

    return {
      beat: function (number) {
        mode('beat');
        if (value) value.textContent = String(number);
        sweep(CIRCUMFERENCE, 0, 1000);
        pop(false);
      },
      go: function (word) {
        mode('go');
        if (value) value.textContent = word;
        cancelAnimations();
        setOffset(0);
        pop(true);
      },
      drain: function (remainingMs, totalMs) {
        mode('');
        sweep(offsetFor(remainingMs, totalMs), CIRCUMFERENCE, remainingMs);
        if (reduced()) setOffset(offsetFor(remainingMs, totalMs));
      },
      showRemaining: function (remainingMs, totalMs) {
        if (reduced()) setOffset(offsetFor(remainingMs, totalMs));
      },
      setText: function (text) { if (value) value.textContent = text; },
      full: function () { mode(''); cancelAnimations(); setOffset(0); },
      reset: function () { mode(''); cancelAnimations(); setOffset(CIRCUMFERENCE); },
    };
  }

  window.CurvaGuidedRing = {
    create: create, countdown: countdown, offsetFor: offsetFor, CIRCUMFERENCE: CIRCUMFERENCE,
  };
}());
