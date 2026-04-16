/*
ARQUIVO: comportamento do card de cobranca curta da recepcao.

POR QUE ELE EXISTE:
- move o fluxo de WhatsApp para a camada de asset
- observa mutacoes criticas do board de cobranca curta sem reload completo
*/

(function () {
    const pageRoot = document.querySelector('[data-page="reception"]');
    const MIN_REFRESH_INTERVAL_MS = 5000;

    if (!pageRoot) {
        return;
    }

    let pendingRefreshTimeout = 0;
    let isRefreshingBoard = false;
    let hasDeferredRefresh = false;
    let backgroundRefreshTimer = 0;
    let operationsEventSource = null;
    let isStreamConnected = false;
    let lastRefreshAt = 0;
    const BACKGROUND_REFRESH_MS = 45000;

    function getReceptionPaymentBoard() {
        return pageRoot.querySelector('#reception-payment-board');
    }

    function getReceptionSnapshotVersion() {
        return getReceptionPaymentBoard()?.dataset.snapshotVersion || pageRoot.dataset.snapshotVersion || '';
    }

    function getReceptionLivePill() {
        return pageRoot.querySelector('[data-role="reception-payment-live-pill"]');
    }

    function getOperationsEventsStreamUrl() {
        return pageRoot.dataset.operationsEventsStreamUrl || '';
    }

    function setLivePillState(text, state, pulse) {
        const pill = getReceptionLivePill();

        if (!pill) {
            return;
        }

        pill.textContent = text;
        pill.classList.remove('warning', 'info', 'success', 'neutral', 'accent', 'is-pulsing');
        pill.classList.add(state || 'neutral');
        if (pulse) {
            pill.classList.add('is-pulsing');
        }
    }

    function buildReceptionWhatsAppMessage(button) {
        const studentName = button.dataset.studentName || 'aluno';
        const operatorName = button.dataset.operatorName || 'Equipe';
        const isLateTenDays = button.dataset.isLate10Days === '1';
        const lines = [
            `Oi, ${studentName}! Aqui e a ${operatorName} do Cross.`,
            '',
            'Tudo bem por ai?',
            '',
            'Passando so pra dar um toque: vi que ficou uma mensalidade em aberto aqui (pode ter escapado na correria mesmo, acontece!).',
        ];

        if (isLateTenDays) {
            lines.push('');
            lines.push('Pra nao correr risco de bloquear o acesso nos treinos, que tal regularizar?');
        }

        lines.push('');
        lines.push('Se quiser resolver agora, te mando a chave PIX na hora.');
        lines.push('Ou, se preferir, a gente acerta tranquilo no seu proximo treino.');
        lines.push('');
        lines.push('Qualquer coisa e so chamar, ta?');
        lines.push('A gente curte muito ter voce treinando com a gente!');

        return lines.join('\n');
    }

    function buildWhatsAppHref(button) {
        const cleanPhone = button.dataset.cleanPhone;

        if (!cleanPhone) {
            return '';
        }

        const message = buildReceptionWhatsAppMessage(button);
        return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(message)}`;
    }

    function registerOperationalContact(button) {
        const communicationUrl = button.dataset.communicationUrl;
        const studentId = button.dataset.studentId;
        const paymentId = button.dataset.paymentId;
        const form = button.closest('form');
        const csrfToken = form?.querySelector('[name=csrfmiddlewaretoken]')?.value;

        if (!communicationUrl || !studentId || !paymentId || !csrfToken) {
            return Promise.resolve();
        }

        const payload = new URLSearchParams({
            action_kind: button.dataset.actionKind || 'overdue',
            student_id: studentId,
            payment_id: paymentId,
        });

        return fetch(communicationUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: payload.toString(),
        }).catch(() => undefined);
    }

    function syncReceptionSubmitLabel(form) {
        const methodSelect = form.querySelector('[data-role="reception-payment-method"]');
        const submitButton = form.querySelector('[data-role="reception-payment-submit"]');

        if (!methodSelect || !submitButton) {
            return;
        }

        const isPix = methodSelect.value === 'pix';
        submitButton.textContent = isPix
            ? (submitButton.dataset.pixLabel || 'Receber com Pix')
            : (submitButton.dataset.defaultLabel || 'Confirmar pagamento');
    }

    function syncAllReceptionSubmitLabels() {
        pageRoot.querySelectorAll('[data-action="manage-reception-payment"]').forEach(syncReceptionSubmitLabel);
    }

    function isReceptionFormBeingEdited() {
        const activeElement = document.activeElement;
        return Boolean(activeElement && activeElement.closest('[data-action="manage-reception-payment"]'));
    }

    function closeOperationsEventStream() {
        if (!operationsEventSource) {
            return;
        }

        try {
            operationsEventSource.close();
        } catch (error) {
            // noop
        }

        operationsEventSource = null;
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

    function queueBoardRefresh(reason) {
        if (shouldSkipRefresh(reason)) {
            return;
        }

        if (pendingRefreshTimeout) {
            window.clearTimeout(pendingRefreshTimeout);
        }

        pendingRefreshTimeout = window.setTimeout(() => {
            pendingRefreshTimeout = 0;
            refreshReceptionPaymentBoard(reason);
        }, 140);
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
            refreshReceptionPaymentBoard('background-refresh');
        }, BACKGROUND_REFRESH_MS);
    }

    function connectOperationsEventStream() {
        closeOperationsEventStream();

        const streamUrl = getOperationsEventsStreamUrl();

        if (!streamUrl || typeof window.EventSource !== 'function') {
            setLivePillState('Fallback local', 'warning', false);
            return;
        }

        operationsEventSource = new window.EventSource(streamUrl);

        ['student.payment.updated', 'student.enrollment.updated', 'student.profile.updated'].forEach((eventType) => {
            operationsEventSource.addEventListener(eventType, function () {
                queueBoardRefresh(eventType);
            });
        });

        operationsEventSource.onerror = function () {
            isStreamConnected = false;
            scheduleBackgroundRefresh();
            setLivePillState('Reconectando', 'warning', true);
        };

        operationsEventSource.onopen = function () {
            isStreamConnected = true;
            scheduleBackgroundRefresh();
            setLivePillState('Escuta pronta', 'neutral', false);
        };
    }

    async function refreshReceptionPaymentBoard(reason) {
        const currentBoard = getReceptionPaymentBoard();
        const refreshUrl = currentBoard?.dataset.refreshUrl;

        if (!currentBoard || !refreshUrl || isRefreshingBoard) {
            return;
        }

        if (isReceptionFormBeingEdited()) {
            hasDeferredRefresh = true;
            setLivePillState('Atualizacao pendente', 'warning', true);
            return;
        }

        isRefreshingBoard = true;
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
            const nextBoard = doc.querySelector('#reception-payment-board');

            if (!nextBoard) {
                throw new Error('refresh-board-missing');
            }

            const currentVersion = getReceptionSnapshotVersion();
            const nextVersion = nextBoard.dataset.snapshotVersion || '';

            if (currentVersion && nextVersion && currentVersion === nextVersion) {
                hasDeferredRefresh = false;
                markRefreshCompleted();
                scheduleBackgroundRefresh();
                setLivePillState('Ja sincronizado', 'success', true);
                window.setTimeout(() => {
                    setLivePillState('Escuta pronta', 'neutral', false);
                }, 1800);
                return;
            }

            currentBoard.replaceWith(nextBoard);
            if (nextVersion) {
                pageRoot.dataset.snapshotVersion = nextVersion;
            }
            markRefreshCompleted();
            syncAllReceptionSubmitLabels();
            hasDeferredRefresh = false;
            scheduleBackgroundRefresh();
            setLivePillState(reason === 'manual-dirty-release' ? 'Fila atualizada' : 'Atualizado agora', 'success', true);
            window.setTimeout(() => {
                setLivePillState('Escuta pronta', 'neutral', false);
            }, 1800);
        } catch (error) {
            setLivePillState('Fallback local', 'warning', false);
        } finally {
            isRefreshingBoard = false;
        }
    }

    syncAllReceptionSubmitLabels();
    connectOperationsEventStream();
    scheduleBackgroundRefresh();

    pageRoot.addEventListener('change', function (event) {
        const methodSelect = event.target.closest('[data-role="reception-payment-method"]');

        if (methodSelect) {
            const form = methodSelect.closest('[data-action="manage-reception-payment"]');

            if (!form) {
                return;
            }

            syncReceptionSubmitLabel(form);
            return;
        }
    });

    pageRoot.addEventListener('focusout', function () {
        if (hasDeferredRefresh && !isReceptionFormBeingEdited()) {
            refreshReceptionPaymentBoard('manual-dirty-release');
        }
    });

    document.addEventListener('visibilitychange', function () {
        scheduleBackgroundRefresh();
        if (document.visibilityState === 'visible') {
            queueBoardRefresh('visibility-refresh');
        }
    });

    window.addEventListener('focus', function () {
        queueBoardRefresh('focus-refresh');
    });

    pageRoot.addEventListener('click', function (event) {
        const button = event.target.closest('[data-action="launch-reception-whatsapp"]');

        if (!button) {
            return;
        }

        event.preventDefault();

        const whatsappHref = buildWhatsAppHref(button);

        if (!whatsappHref) {
            return;
        }

        const popup = window.open(whatsappHref, '_blank', 'noopener');

        if (!popup) {
            window.open(whatsappHref, '_blank');
        }

        registerOperationalContact(button);
    });

    window.addEventListener('beforeunload', function () {
        closeOperationsEventStream();
        if (backgroundRefreshTimer) {
            window.clearInterval(backgroundRefreshTimer);
        }
    });
})();
