/*
ARQUIVO: efeitos cosmeticos do shell autenticado.

POR QUE ELE EXISTE:
- Mantem celebracoes fora da camada essencial do shell.
- Permite carregar efeitos depois que a interface principal ja esta pronta.
*/

(function() {
  var body = document.body;
  var financeAlert = document.querySelector('[data-ui="topbar-finance-alert"]');
  var intakeAlert = document.querySelector('[data-ui="topbar-intake-alert"]');
  var shellUserId = body ? body.dataset.shellUserId || 'anonymous' : 'anonymous';
  var celebrationStorageKey = 'octobox-shell-counts:' + shellUserId;

  if (!body) {
    return;
  }

  function readStorage(storage, key) {
    try {
      return storage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(storage, key, value) {
    try {
      storage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function parseCount(element) {
    var rawValue;
    var parsedValue;

    if (!element) {
      return 0;
    }

    rawValue = element.getAttribute('data-count-value') || '0';
    parsedValue = parseInt(rawValue, 10);
    return Number.isFinite(parsedValue) ? parsedValue : 0;
  }

  function ensureCelebrationStack() {
    var existingStack = document.querySelector('[data-ui="shell-celebration-stack"]');
    var stack;

    if (existingStack) {
      return existingStack;
    }

    stack = document.createElement('div');
    stack.className = 'shell-celebration-stack';
    stack.setAttribute('data-ui', 'shell-celebration-stack');
    document.body.appendChild(stack);
    return stack;
  }

  function emitConfettiBurst(container) {
    var burst = document.createElement('div');
    var index;
    var piece;

    burst.className = 'shell-celebration-burst';
    for (index = 0; index < 14; index += 1) {
      piece = document.createElement('span');
      piece.className = 'shell-celebration-piece';
      burst.appendChild(piece);
    }

    container.appendChild(burst);
  }

  function celebrateCountDrop(kind, previousCount, currentCount) {
    var stack;
    var toast;
    var eyebrow;
    var copy;
    var delta;
    var messages;
    var message;

    if (previousCount <= currentCount) {
      return;
    }

    stack = ensureCelebrationStack();
    toast = document.createElement('section');
    eyebrow = document.createElement('span');
    copy = document.createElement('span');
    delta = previousCount - currentCount;
    messages = {
      'overdue-payments': {
        eyebrow: 'Parabens',
        copy: delta === 1 ?
          'Um vencimento saiu da pressao. Bom avanco.' :
          delta + ' vencimentos sairam da pressao. Bom avanco.'
      },
      'pending-intakes': {
        eyebrow: 'Boa',
        copy: delta === 1 ?
          'Um intake saiu da fila. Bom avanco.' :
          delta + ' intakes sairam da fila. Bom avanco.'
      }
    };
    message = messages[kind];

    if (!message) {
      return;
    }

    toast.className = 'shell-celebration-toast';
    eyebrow.className = 'shell-celebration-eyebrow';
    copy.className = 'shell-celebration-copy';
    eyebrow.textContent = message.eyebrow;
    copy.textContent = message.copy;
    toast.appendChild(eyebrow);
    toast.appendChild(copy);
    emitConfettiBurst(toast);
    stack.appendChild(toast);

    window.setTimeout(function() {
      toast.classList.add('is-dismissing');
      window.setTimeout(function() {
        toast.remove();
      }, 240);
    }, 3200);
  }

  function syncShellCountCelebrations() {
    var currentCounts = {
      overduePayments: parseCount(financeAlert),
      pendingIntakes: parseCount(intakeAlert)
    };
    var previousCounts = null;

    try {
      previousCounts = JSON.parse(readStorage(window.sessionStorage, celebrationStorageKey) || 'null');
    } catch (error) {
      previousCounts = null;
    }

    if (previousCounts) {
      celebrateCountDrop('overdue-payments', previousCounts.overduePayments || 0, currentCounts.overduePayments);
      celebrateCountDrop('pending-intakes', previousCounts.pendingIntakes || 0, currentCounts.pendingIntakes);
    }

    writeStorage(window.sessionStorage, celebrationStorageKey, JSON.stringify(currentCounts));
  }

  syncShellCountCelebrations();
}());
