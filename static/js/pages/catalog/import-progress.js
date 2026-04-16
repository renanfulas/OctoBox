(function() {
  var BASE_POLLING_DELAY_MS = 1000;
  var STABLE_POLLING_DELAY_MS = 3000;
  var HIDDEN_POLLING_DELAY_MS = 15000;
  var MAX_ERROR_POLLING_DELAY_MS = 5000;

  function setText(node, value) {
    if (!node) {
      return;
    }

    node.textContent = value;
  }

  function setElementHidden(node, shouldHide) {
    if (!node) {
      return;
    }

    node.hidden = shouldHide;
  }

  function setVisualWidth(node, value) {
    if (!node) {
      return;
    }

    node.dataset.visualWidth = String(value);
    if (window.OctoDynamicVisuals && typeof window.OctoDynamicVisuals.applyElement === 'function') {
      window.OctoDynamicVisuals.applyElement(node);
    }
  }

  function setStatusTone(node, tone) {
    if (!node) {
      return;
    }

    node.classList.remove('is-running', 'is-success', 'is-danger');
    node.classList.add(tone);
  }

  function buildFailureItem(failure) {
    var item = document.createElement('li');
    var line = failure && failure.line ? failure.line : '?';
    var error = failure && failure.error ? failure.error : 'Falha nao detalhada.';

    item.textContent = 'Linha ' + line + ': ' + error;
    return item;
  }

  document.addEventListener('DOMContentLoaded', function() {
    var root = document.querySelector('[data-page="import-progress"]');
    if (!root) {
      return;
    }

    var progressApiUrl = root.getAttribute('data-progress-url');
    var progressBar = document.getElementById('progress-bar');
    var percentageLabel = document.getElementById('progress-percentage-label');
    var statusLabel = document.getElementById('progress-status-label');
    var processedCount = document.getElementById('processed-count');
    var failedCount = document.getElementById('failed-count');
    var completionActions = document.getElementById('completion-actions');
    var errorContainer = document.getElementById('error-report-container');
    var errorList = document.getElementById('error-list');
    var pollingDelayMs = BASE_POLLING_DELAY_MS;
    var pollingTimeout = null;
    var consecutiveStablePolls = 0;
    var lastProgressValue = -1;
    var lastStatusValue = '';

    if (!progressApiUrl || !progressBar || !percentageLabel || !statusLabel || !processedCount || !failedCount || !completionActions || !errorContainer || !errorList) {
      return;
    }

    function updateUI(data) {
      var job = data.job || {};
      var progress = job.progress || 0;
      var total = job.total || 1;
      var percentage = Math.min(Math.round((progress / total) * 100), 100);
      var failures = Array.isArray(job.failed_items) ? job.failed_items : [];
      var isFinished = job.status === 'completed' || job.status === 'failed';

      setVisualWidth(progressBar, percentage);
      setText(percentageLabel, percentage + '%');
      setText(processedCount, progress + ' / ' + total);
      setText(failedCount, String(failures.length));

      if (progress === lastProgressValue && job.status === lastStatusValue) {
        consecutiveStablePolls += 1;
      } else {
        consecutiveStablePolls = 0;
      }

      lastProgressValue = progress;
      lastStatusValue = job.status || '';

      if (!isFinished) {
        setText(statusLabel, 'Processando lote em background...');
        setStatusTone(statusLabel, 'is-running');
        setStatusTone(progressBar, 'is-running');
        pollingDelayMs = consecutiveStablePolls >= 5 ? STABLE_POLLING_DELAY_MS : BASE_POLLING_DELAY_MS;
        return;
      }

      stopPolling();
      setText(statusLabel, job.status === 'completed' ? 'Concluido' : 'Falha fatal');
      setStatusTone(statusLabel, job.status === 'completed' ? 'is-success' : 'is-danger');
      setStatusTone(progressBar, job.status === 'completed' ? 'is-success' : 'is-danger');
      setElementHidden(completionActions, false);

      if (!failures.length) {
        errorList.replaceChildren();
        setElementHidden(errorContainer, true);
        return;
      }

      errorList.replaceChildren();
      failures.forEach(function(failure) {
        errorList.appendChild(buildFailureItem(failure));
      });
      setElementHidden(errorContainer, false);
    }

    function stopPolling() {
      if (pollingTimeout) {
        clearTimeout(pollingTimeout);
        pollingTimeout = null;
      }
    }

    function isJobFinished() {
      return lastStatusValue === 'completed' || lastStatusValue === 'failed';
    }

    function getNextPollingDelay() {
      if (document.hidden) {
        return HIDDEN_POLLING_DELAY_MS;
      }

      return pollingDelayMs;
    }

    function scheduleNextPoll(options) {
      var force = options && options.force;
      if (pollingTimeout || isJobFinished()) {
        return;
      }

      if (document.hidden && !force) {
        return;
      }

      pollingTimeout = setTimeout(function() {
        pollingTimeout = null;
        pollProgress();
      }, getNextPollingDelay());
    }

    function pollProgress() {
      if (document.hidden) {
        scheduleNextPoll({
          force: true
        });
        return;
      }

      fetch(progressApiUrl)
        .then(function(response) {
          return response.json();
        })
        .then(function(data) {
          if (data.job) {
            updateUI(data);
          }
        })
        .catch(function(error) {
          console.error('Polling error:', error);
          pollingDelayMs = Math.min(pollingDelayMs + BASE_POLLING_DELAY_MS, MAX_ERROR_POLLING_DELAY_MS);
        })
        .finally(function() {
          if (!isJobFinished()) {
            scheduleNextPoll();
          }
        });
    }

    document.addEventListener('visibilitychange', function() {
      if (document.hidden) {
        stopPolling();
        scheduleNextPoll({
          force: true
        });
        return;
      }

      stopPolling();
      pollProgress();
    });

    pollProgress();
  });
}());
