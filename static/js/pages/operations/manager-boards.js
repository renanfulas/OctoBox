/*
ARQUIVO: sincronizacao realtime nativa dos quatro boards do manager.

POR QUE ELE EXISTE:
- usa um stream SSE unico da superficie do manager
- recarrega o fragmento oficial sem reload completo quando algo critico muda
*/

(function () {
    const pageRoot = document.querySelector('.manager-scene');
    const MIN_REFRESH_INTERVAL_MS = 5000;

    if (!pageRoot) {
        return;
    }

    let managerEventSource = null;
    let pendingRefreshTimeout = 0;
    let isRefreshingBoards = false;
    let backgroundRefreshTimer = 0;
    let isStreamConnected = false;
    let lastRefreshAt = 0;
    const optimisticActions = new Map();
    const BACKGROUND_REFRESH_MS = 20000;
    const POST_SUBMIT_RECOVERY_DELAYS_MS = [220, 1200, 3200];
    const OPTIMISTIC_ACTION_STALE_MS = 12000;

    function getManagerBoards() {
        return pageRoot.querySelector('[data-panel="manager-board"]');
    }

    function getManagerSnapshotVersion() {
        return getManagerBoards()?.dataset.snapshotVersion || pageRoot.dataset.snapshotVersion || '';
    }

    function getManagerEventsStreamUrl() {
        return pageRoot.dataset.managerEventsStreamUrl || '';
    }

    function getManagerHistoryBoard() {
        return pageRoot.querySelector('[data-panel="manager-history-board"]');
    }

    function getLivePills() {
        return Array.from(pageRoot.querySelectorAll('[data-role="manager-live-pill"]'));
    }

    function escapeSelectorValue(value) {
        if (window.CSS && typeof window.CSS.escape === 'function') {
            return window.CSS.escape(value);
        }

        return String(value || '').replace(/["\\]/g, '\\$&');
    }

    function setLivePillState(text, state, pulse) {
        getLivePills().forEach((pill) => {
            pill.textContent = text;
            pill.classList.remove('warning', 'info', 'success', 'neutral', 'accent', 'is-pulsing');
            pill.classList.add(state || 'neutral');
            if (pulse) {
                pill.classList.add('is-pulsing');
            }
        });
    }

    function closeManagerEventStream() {
        if (!managerEventSource) {
            return;
        }

        try {
            managerEventSource.close();
        } catch (error) {
            // noop
        }

        managerEventSource = null;
        isStreamConnected = false;
    }

    function markRefreshCompleted() {
        lastRefreshAt = Date.now();
    }

    function shouldSkipRefresh(reason) {
        const now = Date.now();
        const isSoftRefresh = reason === 'background-refresh' || reason === 'focus-refresh' || reason === 'visibility-refresh';

        if (reason === 'background-refresh' && isStreamConnected) {
            return true;
        }

        if (isSoftRefresh && lastRefreshAt && (now - lastRefreshAt) < MIN_REFRESH_INTERVAL_MS) {
            return true;
        }

        return false;
    }

    function queueBoardsRefresh(reason) {
        if (shouldSkipRefresh(reason)) {
            return;
        }
        if (pendingRefreshTimeout) {
            window.clearTimeout(pendingRefreshTimeout);
        }
        pendingRefreshTimeout = window.setTimeout(() => {
            pendingRefreshTimeout = 0;
            refreshManagerBoards(reason);
        }, 140);
    }

    function queueRecoveryRefreshes(reason) {
        POST_SUBMIT_RECOVERY_DELAYS_MS.forEach((delay) => {
            window.setTimeout(() => {
                queueBoardsRefresh(reason);
            }, delay);
        });
    }

    function buildOptimisticEntry(form) {
        const subjectKey = form.dataset.contactSubjectKey || '';

        if (!subjectKey) {
            return null;
        }

        return {
            subjectKey,
            surfaceLabel: form.dataset.historySurfaceLabel || 'Operacao',
            subjectLabel: form.dataset.historySubjectLabel || 'Caso operacional',
            actionLabel: form.dataset.historyActionLabel || 'Contato aberto',
            channelLabel: form.dataset.historyChannelLabel || 'WhatsApp',
            startedAt: Date.now(),
        };
    }

    function markOptimisticRowsHidden(subjectKey) {
        if (!subjectKey) {
            return;
        }

        pageRoot.querySelectorAll(`[data-contact-subject-key="${escapeSelectorValue(subjectKey)}"]`).forEach((row) => {
            row.classList.add('manager-row-is-optimistic-hidden');
        });
    }

    function clearOptimisticRowsHidden(subjectKey) {
        if (!subjectKey) {
            return;
        }

        pageRoot.querySelectorAll(`[data-contact-subject-key="${escapeSelectorValue(subjectKey)}"]`).forEach((row) => {
            row.classList.remove('manager-row-is-optimistic-hidden');
        });
    }

    function ensureHistoryList() {
        const historyBoard = getManagerHistoryBoard();

        if (!historyBoard) {
            return null;
        }

        let historyList = historyBoard.querySelector('[data-role="manager-history-list"]');

        if (!historyList) {
            historyList = document.createElement('div');
            historyList.className = 'manager-history-list';
            historyList.setAttribute('aria-label', 'Pegadas recentes da gerencia');
            historyList.dataset.role = 'manager-history-list';
            historyBoard.appendChild(historyList);
        }

        const emptyState = historyBoard.querySelector('[data-role="manager-history-empty"]');

        if (emptyState) {
            emptyState.hidden = true;
        }

        return historyList;
    }

    function removeOptimisticHistoryItem(subjectKey) {
        const historyBoard = getManagerHistoryBoard();

        if (!historyBoard || !subjectKey) {
            return;
        }

        const pendingItem = historyBoard.querySelector(
            `[data-pending-subject-key="${escapeSelectorValue(subjectKey)}"]`
        );

        if (pendingItem) {
            pendingItem.remove();
        }

        const historyList = historyBoard.querySelector('[data-role="manager-history-list"]');
        const emptyState = historyBoard.querySelector('[data-role="manager-history-empty"]');

        if (historyList && historyList.children.length === 0 && emptyState) {
            emptyState.hidden = false;
        }
    }

    function upsertOptimisticHistoryItem(entry) {
        if (!entry?.subjectKey) {
            return;
        }

        const historyList = ensureHistoryList();

        if (!historyList) {
            return;
        }

        const existingItem = historyList.querySelector(
            `[data-pending-subject-key="${escapeSelectorValue(entry.subjectKey)}"]`
        );

        if (existingItem) {
            return;
        }

        const item = document.createElement('article');
        item.className = 'manager-history-item manager-history-item--pending';
        item.dataset.pendingSubjectKey = entry.subjectKey;
        item.innerHTML = `
            <div class="manager-history-item-head">
                <span class="pill info">${entry.surfaceLabel}</span>
                <span class="manager-history-item-time">agora</span>
            </div>
            <strong class="manager-history-item-title">${entry.subjectLabel}</strong>
            <p class="manager-history-item-copy">${entry.actionLabel} via ${entry.channelLabel}.</p>
        `;
        historyList.prepend(item);
    }

    function reconcileOptimisticState() {
        const now = Date.now();

        optimisticActions.forEach((entry, subjectKey) => {
            const escapedKey = escapeSelectorValue(subjectKey);
            const officialHistoryItem = pageRoot.querySelector(
                `[data-role="manager-history-list"] [data-subject-key="${escapedKey}"]`
            );

            if (officialHistoryItem) {
                removeOptimisticHistoryItem(subjectKey);
                clearOptimisticRowsHidden(subjectKey);
                optimisticActions.delete(subjectKey);
                return;
            }

            const matchingRows = pageRoot.querySelectorAll(
                `[data-contact-subject-key="${escapedKey}"]`
            );

            if (matchingRows.length === 0) {
                upsertOptimisticHistoryItem(entry);
                return;
            }

            if (now - entry.startedAt > OPTIMISTIC_ACTION_STALE_MS) {
                removeOptimisticHistoryItem(subjectKey);
                clearOptimisticRowsHidden(subjectKey);
                optimisticActions.delete(subjectKey);
                return;
            }

            markOptimisticRowsHidden(subjectKey);
            upsertOptimisticHistoryItem(entry);
        });
    }

    function connectManagerEventStream() {
        closeManagerEventStream();

        const streamUrl = getManagerEventsStreamUrl();

        if (!streamUrl || typeof window.EventSource !== 'function') {
            return;
        }

        managerEventSource = new window.EventSource(streamUrl);

        [
            'student.payment.updated',
            'student.enrollment.updated',
            'student.profile.updated',
            'intake.updated',
            'whatsapp_contact.updated',
        ].forEach((eventType) => {
            managerEventSource.addEventListener(eventType, () => {
                queueBoardsRefresh(eventType);
            });
        });

        managerEventSource.onerror = function () {
            isStreamConnected = false;
            scheduleBackgroundRefresh();
            setLivePillState('Reconectando', 'warning', true);
        };

        managerEventSource.onopen = function () {
            isStreamConnected = true;
            scheduleBackgroundRefresh();
            setLivePillState('Escuta pronta', 'neutral', false);
        };
    }

    function scheduleBackgroundRefresh() {
        if (backgroundRefreshTimer) {
            window.clearInterval(backgroundRefreshTimer);
            backgroundRefreshTimer = 0;
        }

        if (document.visibilityState !== 'visible' || isStreamConnected) {
            return;
        }

        backgroundRefreshTimer = window.setInterval(() => {
            refreshManagerBoards('background-refresh');
        }, BACKGROUND_REFRESH_MS);
    }

    async function refreshManagerBoards(reason) {
        const currentBoards = getManagerBoards();
        const refreshUrl = currentBoards?.dataset.refreshUrl;

        if (!currentBoards || !refreshUrl || isRefreshingBoards) {
            return;
        }

        isRefreshingBoards = true;
        setLivePillState('Sincronizando', 'info', true);

        try {
            const response = await fetch(refreshUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                throw new Error(`refresh-failed:${response.status}`);
            }

            const html = await response.text();
            const parser = new window.DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const nextBoards = doc.querySelector('[data-panel="manager-board"]');

            if (!nextBoards) {
                throw new Error('manager-board-missing');
            }

            const currentVersion = getManagerSnapshotVersion();
            const nextVersion = nextBoards.dataset.snapshotVersion || '';

            if (currentVersion && nextVersion && currentVersion === nextVersion) {
                markRefreshCompleted();
                reconcileOptimisticState();
                scheduleBackgroundRefresh();
                setLivePillState('Ja sincronizado', 'success', true);
                window.setTimeout(() => {
                    setLivePillState('Escuta pronta', 'neutral', false);
                }, 1800);
                return;
            }

            currentBoards.replaceWith(nextBoards);
            if (nextVersion) {
                pageRoot.dataset.snapshotVersion = nextVersion;
            }
            markRefreshCompleted();
            reconcileOptimisticState();
            scheduleBackgroundRefresh();
            setLivePillState(
                reason === 'student.profile.updated'
                    ? 'Contexto renovado'
                    : reason === 'background-refresh'
                        ? 'Leitura conferida'
                        : 'Atualizado agora',
                'success',
                true
            );
            window.setTimeout(() => {
                setLivePillState('Escuta pronta', 'neutral', false);
            }, 1800);
        } catch (error) {
            setLivePillState('Fallback local', 'warning', false);
        } finally {
            isRefreshingBoards = false;
        }
    }

    connectManagerEventStream();
    scheduleBackgroundRefresh();
    reconcileOptimisticState();
    document.addEventListener('visibilitychange', function () {
        scheduleBackgroundRefresh();
        if (document.visibilityState === 'visible') {
            queueBoardsRefresh('background-refresh');
        }
    });
    window.addEventListener('focus', function () {
        queueBoardsRefresh('background-refresh');
    });
    pageRoot.addEventListener('submit', function (event) {
        const form = event.target.closest('[data-action="manager-contact-submit"]');

        if (!form) {
            return;
        }

        const optimisticEntry = buildOptimisticEntry(form);

        if (optimisticEntry) {
            optimisticActions.set(optimisticEntry.subjectKey, optimisticEntry);
            markOptimisticRowsHidden(optimisticEntry.subjectKey);
            upsertOptimisticHistoryItem(optimisticEntry);
        }

        // O POST abre em nova aba; como o SSE local pode falhar, fazemos
        // uma pequena sequencia de refresh para capturar a mudanca assim que
        // a transacao terminar no backend.
        queueRecoveryRefreshes('manager-contact-submit');
    });
    window.addEventListener('beforeunload', function () {
        closeManagerEventStream();
        if (backgroundRefreshTimer) {
            window.clearInterval(backgroundRefreshTimer);
        }
    });
})();
