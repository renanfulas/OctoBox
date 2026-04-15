/*
ARQUIVO: carregador de efeitos cosmeticos do shell.

POR QUE ELE EXISTE:
- Adia celebracoes ate o navegador ter uma janela ociosa.
- Mantem o shell essencial pequeno e previsivel.
*/

(function() {
  var currentScript = document.currentScript;

  if (!document.body || !currentScript) {
    return;
  }

  function resolveEffectsScriptUrl() {
    var loaderSrc = currentScript.getAttribute('src') || '';
    if (!loaderSrc) {
      return '';
    }

    return loaderSrc.replace(/shell-effects-loader\.js(\?.*)?$/, 'shell-effects.js$1');
  }

  function loadEffects() {
    var scriptUrl = resolveEffectsScriptUrl();
    var script;

    if (!scriptUrl) {
      return;
    }

    script = document.createElement('script');
    script.src = scriptUrl;
    script.async = true;
    document.body.appendChild(script);
  }

  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(loadEffects, { timeout: 1800 });
  } else {
    window.setTimeout(loadEffects, 900);
  }
}());
