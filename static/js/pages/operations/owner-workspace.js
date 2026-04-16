/*
ARQUIVO: reconciliacao leve do workspace do owner por snapshot_version.

POR QUE ELE EXISTE:
- oficializa o fallback de realtime do owner sem SSE dedicado.
- usa polling leve quando a pagina esta visivel para evitar leitura congelada.
*/

(function () {
    const BACKGROUND_REFRESH_MS = 45000;
    const MIN_REFRESH_INTERVAL_MS = 10000;
    let refreshTimer = 0;
    let pendingRefreshTimeout = 0;
    let isRefreshing = false;
    let lastRefreshAt = 0;

    function getOwnerScene() {
        return document.querySelector('.owner-scene[data-panel="owner-workspace-shell"]');
    }

    function getOwnerSnapshotVersion() {
        return getOwnerScene()?.dataset.snapshotVersion || '';
    }

    function queueRefresh(reason) {
        if (lastRefreshAt && (Date.now() - lastRefreshAt) < MIN_REFRESH_INTERVAL_MS) {
            return;
        }
        if (pendingRefreshTimeout) {
            window.clearTimeout(pendingRefreshTimeout);
        }

        pendingRefreshTimeout = window.setTimeout(() => {
            pendingRefreshTimeout = 0;
            refreshOwnerWorkspace(reason);
        }, 140);
    }

    function scheduleBackgroundRefresh() {
        if (refreshTimer) {
            window.clearInterval(refreshTimer);
            refreshTimer = 0;
        }

        if (document.visibilityState !== 'visible') {
            return;
        }

        refreshTimer = window.setInterval(() => {
            refreshOwnerWorkspace('background-refresh');
        }, BACKGROUND_REFRESH_MS);
    }

    async function refreshOwnerWorkspace(reason) {
        const currentScene = getOwnerScene();
        const refreshUrl = currentScene?.dataset.refreshUrl;

        if (!currentScene || !refreshUrl || isRefreshing) {
            return;
        }

        isRefreshing = true;

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
            const nextScene = doc.querySelector('.owner-scene[data-panel="owner-workspace-shell"]');

            if (!nextScene) {
                throw new Error('owner-workspace-missing');
            }

            const currentVersion = getOwnerSnapshotVersion();
            const nextVersion = nextScene.dataset.snapshotVersion || '';

            if (currentVersion && nextVersion && currentVersion === nextVersion) {
                lastRefreshAt = Date.now();
                scheduleBackgroundRefresh();
                return;
            }

            currentScene.replaceWith(nextScene);
            lastRefreshAt = Date.now();
            scheduleBackgroundRefresh();
        } catch (error) {
            if (reason === 'visibility-refresh') {
                scheduleBackgroundRefresh();
            }
        } finally {
            isRefreshing = false;
        }
    }

    if (!getOwnerScene()) {
        return;
    }

    scheduleBackgroundRefresh();
    document.addEventListener('visibilitychange', function () {
        scheduleBackgroundRefresh();
        if (document.visibilityState === 'visible') {
            queueRefresh('visibility-refresh');
        }
    });
    window.addEventListener('focus', function () {
        queueRefresh('focus-refresh');
    });
    window.addEventListener('beforeunload', function () {
        if (refreshTimer) {
            window.clearInterval(refreshTimer);
        }
    });
})();
