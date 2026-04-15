/*
ARQUIVO: carregador sob demanda da busca global.

POR QUE ELE EXISTE:
- Mantem o autocomplete fora do carregamento inicial do shell.
- Ativa a busca rica apenas quando o usuario demonstra intencao.

O QUE ESTE ARQUIVO FAZ:
1. Observa foco, ponteiro e digitacao no formulario da topbar.
2. Injeta `search.js` uma unica vez.
3. Preserva o fallback server-side quando o autocomplete nao carregar.
*/

(function() {
  var form = document.querySelector('[data-ui="global-search-form"]');
  var input = document.querySelector('[data-ui="global-search-input"]');
  var currentScript = document.currentScript;
  var isLoading = false;
  var isLoaded = false;

  if (!form || !input || !currentScript) {
    return;
  }

  function resolveSearchScriptUrl() {
    var loaderSrc = currentScript.getAttribute('src') || '';
    if (!loaderSrc) {
      return '';
    }

    return loaderSrc.replace(/search-loader\.js(\?.*)?$/, 'search.js$1');
  }

  function markState(state) {
    form.setAttribute('data-search-autocomplete-state', state);
  }

  function replayInputIfNeeded() {
    if (!input.value || input.value.trim().length < 2) {
      return;
    }

    input.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function loadAutocomplete() {
    var scriptUrl;
    var script;

    if (isLoaded || isLoading) {
      return;
    }

    scriptUrl = resolveSearchScriptUrl();
    if (!scriptUrl) {
      markState('unavailable');
      return;
    }

    isLoading = true;
    markState('loading');
    script = document.createElement('script');
    script.src = scriptUrl;
    script.async = true;
    script.onload = function() {
      isLoading = false;
      isLoaded = true;
      markState('ready');
      replayInputIfNeeded();
    };
    script.onerror = function() {
      isLoading = false;
      markState('fallback');
    };

    document.body.appendChild(script);
  }

  form.addEventListener('focusin', loadAutocomplete, { once: true });
  form.addEventListener('pointerdown', loadAutocomplete, { once: true });
  input.addEventListener('input', loadAutocomplete, { once: true });
}());
