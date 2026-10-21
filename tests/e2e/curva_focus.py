"""Espiões e gestos do aparelho para os e2e do modo foco da Curva."""

# Anota a frequência de cada bipe do modo foco e quantas vezes o áudio é religado.
SPY_AUDIO = """
(() => {
  window.__curvaBeeps = [];
  window.__curvaAudioResumes = 0;
  const Real = window.AudioContext;
  window.AudioContext = class extends Real {
    resume() { window.__curvaAudioResumes += 1; return super.resume(); }
    createOscillator() {
      const osc = super.createOscillator();
      const start = osc.start.bind(osc);
      osc.start = (...args) => { window.__curvaBeeps.push(Math.round(osc.frequency.value)); return start(...args); };
      return osc;
    }
  };
})();
"""
# Anota cada vibração pedida pelo modo foco.
SPY_VIBRATION = """
(() => {
  window.__curvaVibrations = [];
  Object.defineProperty(Navigator.prototype, 'vibrate', {
    configurable: true, writable: true,
    value(pattern) { window.__curvaVibrations.push(pattern); return true; },
  });
})();
"""
RESET_SPIES = '() => { window.__curvaBeeps = []; window.__curvaVibrations = []; }'
# Bloquear a tela: o navegador avisa a página com visibilitychange. No Android
# a página segue viva; no iPhone o PWA também congela (FREEZE_TIMERS).
LOCK_SCREEN = """() => {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  document.dispatchEvent(new Event('visibilitychange'));
}"""
UNLOCK_SCREEN = """() => {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  document.dispatchEvent(new Event('visibilitychange'));
}"""
# O iOS congela o PWA fora da tela: nenhum timer novo roda até ele voltar. O
# Chromium de teste ignora Page.setWebLifecycleState numa aba à vista, então os
# setTimeout ficam presos aqui e saem atrasados em THAW_TIMERS.
FREEZE_TIMERS = """() => {
  window.__curvaHeldTimers = [];
  window.__curvaSetTimeout = window.setTimeout;
  window.setTimeout = (fn, ms, ...args) => { window.__curvaHeldTimers.push(() => fn(...args)); return 0; };
}"""
THAW_TIMERS = """() => {
  window.setTimeout = window.__curvaSetTimeout;
  window.__curvaHeldTimers.splice(0).forEach((run) => window.setTimeout(run, 0));
}"""
