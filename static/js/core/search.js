/*
ARQUIVO: autocomplete da busca global do shell.

POR QUE ELE EXISTE:
- separa a busca global da infraestrutura visual do shell.
*/

(function() {
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
  var autocompleteUrl = form.getAttribute('data-autocomplete-url');
  
  if (!autocompleteUrl) {
    console.warn('Busca global desabilitada: data-autocomplete-url não encontrado no DOM. Roteamento de fallback removido.');
    return;
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
  }

  function renderResults(results) {
    clearList();
    if (!results.length) {
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
    clearTimeout(debounceTimer);
    if (query.length < 2) {
      abortPendingRequest();
      setStatus(query.length ? 'Digite pelo menos 2 caracteres para abrir a busca global.' : '');
      hideList();
      return;
    }

    debounceTimer = setTimeout(function() {
      var requestId = lastRequestId + 1;
      lastRequestId = requestId;
      abortPendingRequest();
      activeRequestController = typeof AbortController === 'function' ? new AbortController() : null;
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

          renderResults(data.results || []);
        })
        .catch(function(error) {
          if (error && error.name === 'AbortError') {
            return;
          }

          activeRequestController = null;
          setStatus('A busca global nao respondeu agora. Use Enter para abrir a lista completa.');
          hideList();
        });
    }, 200);
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
