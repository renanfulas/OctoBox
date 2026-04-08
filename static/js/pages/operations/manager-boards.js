/*
ARQUIVO: sincronizacao realtime nativa dos quatro boards do manager.

POR QUE ELE EXISTE:
- usa um stream SSE unico da superficie do manager
- recarrega o fragmento oficial sem reload completo quando algo critico muda
*/

(function () {
    const pageRoot = document.querySelector('.manager-scene');

    if (!pageRoot) {
        return;
    }

    let managerEventSource = null;
    let pendingRefreshTimeout = 0;
    let isRefreshingBoards = false;
    let backgroundRefreshTimer = 0;
    const BACKGROUND_REFRESH_MS = 20000;

    function getManagerBoards() {
        return pageRoot.querySelector('[data-panel="manager-board"]');
    }

    function getManagerEventsStreamUrl() {
        return pageRoot.dataset.managerEventsStreamUrl || '';
    }

    function getLivePills() {
        return Array.from(pageRoot.querySelectorAll('[data-role="manager-live-pill"]'));
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
    }

    function queueBoardsRefresh(reason) {
        if (pendingRefreshTimeout) {
            window.clearTimeout(pendingRefreshTimeout);
        }
        pendingRefreshTimeout = window.setTimeout(() => {
            pendingRefreshTimeout = 0;
            refreshManagerBoards(reason);
        }, 140);
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
            setLivePillState('Reconectando', 'warning', true);
        };

        managerEventSource.onopen = function () {
            setLivePillState('Escuta pronta', 'neutral', false);
        };
    }

    function scheduleBackgroundRefresh() {
        if (backgroundRefreshTimer) {
            window.clearInterval(backgroundRefreshTimer);
            backgroundRefreshTimer = 0;
        }

        if (document.visibilityState !== 'visible') {
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

            currentBoards.replaceWith(nextBoards);
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
    document.addEventListener('visibilitychange', function () {
        scheduleBackgroundRefresh();
        if (document.visibilityState === 'visible') {
            queueBoardsRefresh('background-refresh');
        }
    });
    window.addEventListener('focus', function () {
        queueBoardsRefresh('background-refresh');
    });
    window.addEventListener('beforeunload', function () {
        closeManagerEventStream();
        if (backgroundRefreshTimer) {
            window.clearInterval(backgroundRefreshTimer);
        }
    });
})();
