/*
ARQUIVO: autocomplete da busca global do shell.

POR QUE ELE EXISTE:
- separa a busca global da infraestrutura visual do shell.
*/

(function() {
  var MIN_QUERY_LENGTH = 2;
  var AUTOCOMPLETE_DEBOUNCE_MS = 200;
  var AUTOCOMPLETE_CACHE_TTL_MS = 30000;
  var AUTOCOMPLETE_CACHE_LIMIT = 12;

  var input = document.querySelector('[data-ui="global-search-input"]') || document.getElementById('global-search-input');
  var list = document.querySelector('[data-ui="global-search-results"]') || document.getElementById('search-autocomplete-list');
  var form = document.querySelector('[data-ui="global-search-form"]') || (input ? input.closest('form') : null);
  var status = document.querySelector('[data-ui="global-search-status"]');
  if (!input || !list || !form) {
    return;
  }

  var debounceTimer = null;
  var activeIndex = -1;
  var lastRequestId = 0;
  var activeRequestController = null;
  var activeQuery = '';
  var activeNormalizedQuery = '';
  var autocompleteUrl = form.getAttribute('data-autocomplete-url');
  var autocompleteCache = new Map();
  var telemetry = {
    cacheHits: 0,
    cacheMisses: 0,
    requestsSent: 0,
    requestsAvoided: 0,
    duplicateInFlightSuppressed: 0,
    emptyResults: 0,
    resultsRendered: 0,
    errors: 0,
    lastQuery: '',
    lastResultsCount: 0,
    lastRequestDurationMs: 0,
    recentRequestDurationMs: []
  };

  window.__octoboxGlobalSearchTelemetry = telemetry;
  
  if (!autocompleteUrl) {
    console.warn('Busca global desabilitada: data-autocomplete-url não encontrado no DOM. Roteamento de fallback removido.');
    return;
  }

  function shouldLogPerformanceTelemetry() {
    var params = new URLSearchParams(window.location.search || '');
    if (params.get('debug_performance') === '1') {
      return true;
    }

    try {
      return window.localStorage.getItem('octobox.debug.performance') === '1'
        || window.sessionStorage.getItem('octobox.debug.performance') === '1';
    } catch (error) {
      return false;
    }
  }

  function recordPerformanceSample(list, value) {
    if (!Array.isArray(list) || typeof value !== 'number' || Number.isNaN(value)) {
      return;
    }

    list.push(Math.round(value));
    if (list.length > 20) {
      list.splice(0, list.length - 20);
    }
  }

  function logPerformanceTelemetry(eventName, data) {
    if (!shouldLogPerformanceTelemetry() || !window.console || typeof window.console.debug !== 'function') {
      return;
    }

    window.console.debug('[OctoBox][GlobalSearch][Telemetry]', eventName, data || {});
  }

  function setStatus(message) {
    if (!status) {
      return;
    }

    status.textContent = message;
  }

  function clearList() {
    list.replaceChildren();
    input.removeAttribute('aria-activedescendant');
    activeIndex = -1;
  }

  function showList() {
    list.hidden = false;
    form.setAttribute('aria-expanded', 'true');
  }

  function hideList() {
    list.hidden = true;
    form.setAttribute('aria-expanded', 'false');
    clearList();
  }

  function abortPendingRequest() {
    if (!activeRequestController) {
      return;
    }

    activeRequestController.abort();
    activeRequestController = null;
    activeQuery = '';
    activeNormalizedQuery = '';
  }

  function normalizeQuery(query) {
    return (query || '').trim().toLowerCase();
  }

  function getCachedResults(query) {
    var entry = autocompleteCache.get(query);
    if (!entry) {
      return null;
    }

    if (Date.now() - entry.createdAt > AUTOCOMPLETE_CACHE_TTL_MS) {
      autocompleteCache.delete(query);
      return null;
    }

    return entry;
  }

  function setCachedResults(query, results) {
    if (!query) {
      return;
    }

    autocompleteCache.delete(query);
    autocompleteCache.set(query, {
      createdAt: Date.now(),
      results: Array.isArray(results) ? results : []
    });

    while (autocompleteCache.size > AUTOCOMPLETE_CACHE_LIMIT) {
      autocompleteCache.delete(autocompleteCache.keys().next().value);
    }
  }

  function renderResults(results) {
    clearList();
    if (!results.length) {
      telemetry.emptyResults += 1;
      telemetry.lastResultsCount = 0;
      setStatus('Nenhum resultado encontrado na busca global.');
      hideList();
      return;
    }

    results.forEach(function(item, index) {
      var li = document.createElement('li');
      var name = document.createElement('span');
      var meta = document.createElement('span');
      var destination = item.url + (item.status_raw === 'lead' ? '#focus=lead' : item.status_raw === 'active' ? '#focus=active' : '');
      li.setAttribute('role', 'option');
      li.setAttribute('data-url', destination);
      li.className = 'search-autocomplete-item';
      li.id = 'search-option-' + index;
      name.className = 'search-ac-name';
      name.textContent = item.name || '';
      meta.className = 'search-ac-meta';
      meta.textContent = (item.phone || '') + ' · ' + (item.status || '');
      li.appendChild(name);
      li.appendChild(meta);
      li.addEventListener('mousedown', function(event) {
        event.preventDefault();
        window.location.href = destination;
      });
      list.appendChild(li);
    });

    telemetry.resultsRendered += results.length;
    telemetry.lastResultsCount = results.length;
    setStatus(results.length + ' resultado(s) prontos para navegacao rapida.');
    showList();
  }

  function setActive(index) {
    var items = list.querySelectorAll('[role="option"]');
    items.forEach(function(element) {
      element.classList.remove('is-active');
      element.removeAttribute('aria-selected');
    });

    if (index < 0 || index >= items.length) {
      activeIndex = -1;
      input.removeAttribute('aria-activedescendant');
      return;
    }

    activeIndex = index;
    items[index].classList.add('is-active');
    items[index].setAttribute('aria-selected', 'true');
    input.setAttribute('aria-activedescendant', items[index].id);
    items[index].scrollIntoView({
      block: 'nearest'
    });
  }

  input.addEventListener('input', function() {
    var query = input.value.trim();
    var normalizedQuery = normalizeQuery(query);
    clearTimeout(debounceTimer);
    if (query.length < MIN_QUERY_LENGTH) {
      abortPendingRequest();
      setStatus(query.length ? 'Digite pelo menos 2 caracteres para abrir a busca global.' : '');
      hideList();
      return;
    }

    if (normalizedQuery === activeNormalizedQuery && activeRequestController) {
      telemetry.duplicateInFlightSuppressed += 1;
      telemetry.requestsAvoided += 1;
      logPerformanceTelemetry('duplicate-suppressed', {
        query: normalizedQuery
      });
      return;
    }

    debounceTimer = setTimeout(function() {
      var cachedEntry = getCachedResults(normalizedQuery);
      telemetry.lastQuery = normalizedQuery;
      if (cachedEntry) {
        telemetry.cacheHits += 1;
        telemetry.requestsAvoided += 1;
        activeQuery = query;
        activeNormalizedQuery = normalizedQuery;
        setStatus('Resultados recentes carregados do cache local.');
        logPerformanceTelemetry('cache-hit', {
          query: normalizedQuery,
          results: Array.isArray(cachedEntry.results) ? cachedEntry.results.length : 0,
          cache_age_ms: Date.now() - cachedEntry.createdAt
        });
        renderResults(cachedEntry.results || []);
        return;
      }

      telemetry.cacheMisses += 1;

      var requestId = lastRequestId + 1;
      var requestStartedAt = Date.now();
      lastRequestId = requestId;
      abortPendingRequest();
      activeRequestController = typeof AbortController === 'function' ? new AbortController() : null;
      activeQuery = query;
      activeNormalizedQuery = normalizedQuery;
      telemetry.requestsSent += 1;
      setStatus('Buscando alunos e contatos relacionados.');
      fetch(autocompleteUrl + '?q=' + encodeURIComponent(query), {
          credentials: 'same-origin',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          },
          signal: activeRequestController ? activeRequestController.signal : undefined
        })
        .then(function(response) {
          if (!response.ok) {
            throw new Error('autocomplete-request-failed');
          }

          return response.json();
        })
        .then(function(data) {
          if (requestId !== lastRequestId) {
            return;
          }

          activeRequestController = null;
          telemetry.lastRequestDurationMs = Date.now() - requestStartedAt;
          recordPerformanceSample(telemetry.recentRequestDurationMs, telemetry.lastRequestDurationMs);
          setCachedResults(normalizedQuery, data.results || []);
          logPerformanceTelemetry('network-response', {
            query: normalizedQuery,
            results: Array.isArray(data.results) ? data.results.length : 0,
            duration_ms: telemetry.lastRequestDurationMs
          });

          renderResults(data.results || []);
        })
        .catch(function(error) {
          if (error && error.name === 'AbortError') {
            return;
          }

          activeRequestController = null;
          activeQuery = '';
          activeNormalizedQuery = '';
          telemetry.errors += 1;
          setStatus('A busca global nao respondeu agora. Use Enter para abrir a lista completa.');
          logPerformanceTelemetry('network-error', {
            query: normalizedQuery
          });
          hideList();
        });
    }, AUTOCOMPLETE_DEBOUNCE_MS);
  });

  input.addEventListener('keydown', function(event) {
    var items = list.querySelectorAll('[role="option"]');
    if (!items.length || list.hidden) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive(activeIndex < items.length - 1 ? activeIndex + 1 : 0);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive(activeIndex > 0 ? activeIndex - 1 : items.length - 1);
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      window.location.href = items[activeIndex].dataset.url;
    } else if (event.key === 'Escape') {
      hideList();
    }
  });

  input.addEventListener('blur', function() {
    setTimeout(hideList, 150);
  });

  form.addEventListener('submit', function(event) {
    if (activeIndex < 0) {
      return;
    }

    var items = list.querySelectorAll('[role="option"]');
    if (items[activeIndex]) {
      event.preventDefault();
      window.location.href = items[activeIndex].dataset.url;
    }
  });
}());
