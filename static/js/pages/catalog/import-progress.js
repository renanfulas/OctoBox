(function() {
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
    var pollingInterval = null;

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

      progressBar.style.width = percentage + '%';
      setText(percentageLabel, percentage + '%');
      setText(processedCount, progress + ' / ' + total);
      setText(failedCount, String(failures.length));

      if (!isFinished) {
        setText(statusLabel, 'Processando lote em background...');
        return;
      }

      clearInterval(pollingInterval);
      setText(statusLabel, job.status === 'completed' ? 'Concluido' : 'Falha fatal');
      statusLabel.className = job.status === 'completed' ? 'text-green-600 font-bold' : 'text-red-600 font-bold';
      progressBar.classList.remove('bg-indigo-500');
      progressBar.classList.add(job.status === 'completed' ? 'bg-green-500' : 'bg-red-500');
      completionActions.classList.remove('hidden');

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

    function pollProgress() {
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
        });
    }

    pollingInterval = setInterval(pollProgress, 1000);
    pollProgress();
  });
}());
