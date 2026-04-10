/**
 * ARQUIVO: comportamentos locais do diretorio de alunos.
 *
 * POR QUE ELE EXISTE:
 * - automatiza a busca, filtros locais e mantem a navegacao por linha da tabela.
 */

document.addEventListener('DOMContentLoaded', function() {
    var payloadElement = document.getElementById('current-page-behavior');
    var pageBehavior = {};
    if (payloadElement) {
        try {
            pageBehavior = JSON.parse(payloadElement.textContent || '{}');
        } catch (error) {
            console.error('Student directory behavior payload error:', error);
            pageBehavior = {};
        }
    }

    var filterForm = document.getElementById('student-directory-filter-form');
    var searchInput = filterForm ? filterForm.querySelector('input[name="query"]') : null;
    var pills = Array.from(document.querySelectorAll('[data-student-filter], [data-student-sort]'));
    var rows = Array.from(document.querySelectorAll('[data-student-row]'));
    var tbody = document.querySelector('[data-student-directory-body]');
    var countNode = document.querySelector('[data-student-count]');
    var emptyState = document.querySelector('[data-student-empty-state]');
    var directoryFooter = document.querySelector('.student-directory-footer');
    var quickPanel = document.querySelector('[data-student-quick-panel]');
    var quickOverlay = document.querySelector('[data-student-quick-overlay]');
    var quickClose = document.querySelector('[data-student-quick-close]');
    var quickTabButtons = Array.from(document.querySelectorAll('[data-student-quick-tab]'));
    var quickFeedback = document.querySelector('[data-student-quick-feedback]');
    var prefetchConfig = pageBehavior.student_prefetch || {};
    var directorySearchConfig = pageBehavior.directory_search || {};
    var prefetchEnabled = prefetchConfig.enabled !== false;
    var prefetchHoverDelayMs = Number(prefetchConfig.hover_delay_ms || 120);
    var prefetchCacheTtlMs = Number(prefetchConfig.cache_ttl_ms || 120000);
    var idlePrefetchLimit = Number(prefetchConfig.idle_prefetch_limit || 3);
    var navigationHintKey = 'octobox.student.navigation-hint.v1';
    var prefetchedHrefSet = new Set();
    var prefetchedSnapshotSet = new Set();
    var inFlightSnapshotSet = new Set();
    var filterState = {
        filter: 'all',
        sortBy: '',
        sortDirection: 'desc',
        searchQuery: '',
    };
    var currentSearchParams = new URLSearchParams(window.location.search || '');
    var rowPrefetchTimers = new WeakMap();
    var searchSubmitTimerId = null;
    var serverRows = rows.slice();
    var directorySearchCacheKey = 'octobox.student.directory.search-index.v1.' + String(directorySearchConfig.cache_key || 'all');
    var directorySearchStaleKey = 'octobox.student.directory.search-index.stale.v1.' + String(directorySearchConfig.cache_key || 'all');
    var directorySearchState = {
        index: [],
        isUsingSearchIndex: false,
    };
    var quickPanelState = {
        studentId: null,
        isOpen: false,
        activeHref: '',
        activeRow: null,
        activeTab: '',
        fragmentsLoaded: {
            profile: false,
            financial: false,
        },
        liveRefreshTimerId: null,
        heartbeatTimerId: null,
        editSessionActive: false,
        refreshInFlight: false,
        lastFragmentRefreshAt: 0,
        eventSource: null,
        sseConnected: false,
        currentSnapshotVersion: '',
        currentProfileVersion: '',
        processedEventIds: [],
    };
    var realtimeTelemetry = {
        duplicateEventsIgnored: 0,
        staleEventsIgnored: 0,
        profileEventsDeferred: 0,
        conflictResponses: 0,
    };

    window.__octoboxStudentRealtimeTelemetry = realtimeTelemetry;

    function setDirectoryFooterVisibility(shouldShow) {
        if (!directoryFooter) {
            return;
        }

        directoryFooter.hidden = !shouldShow;
        directoryFooter.style.display = shouldShow ? '' : 'none';
    }

    function hasServerScopedFilters() {
        return currentSearchParams.has('student_status')
            || currentSearchParams.has('commercial_status')
            || currentSearchParams.has('payment_status')
            || currentSearchParams.has('created_window');
    }

    function buildDirectoryFilterUrl(nextFilter) {
        var nextParams = new URLSearchParams(window.location.search || '');
        var liveQueryValue = searchInput ? String(searchInput.value || '').trim() : '';

        nextParams.delete('student_status');
        nextParams.delete('commercial_status');
        nextParams.delete('payment_status');
        nextParams.delete('created_window');
        nextParams.delete('page');
        nextParams.delete('keep_open');

        if (liveQueryValue) {
            nextParams.set('query', liveQueryValue);
        } else {
            nextParams.delete('query');
        }

        if (nextFilter === 'active') {
            nextParams.set('student_status', 'active');
        } else if (nextFilter === 'inactive') {
            nextParams.set('student_status', 'inactive');
        } else if (nextFilter === 'overdue') {
            nextParams.set('payment_status', 'overdue');
        }

        var queryString = nextParams.toString();
        return window.location.pathname + (queryString ? ('?' + queryString) : '') + '#tab-students-directory';
    }

    function supportsSessionStorage() {
        try {
            return typeof window.sessionStorage !== 'undefined';
        } catch (error) {
            return false;
        }
    }

    function getSnapshotKey(studentId) {
        return 'octobox.student.snapshot.v1.' + studentId;
    }

    function writeSessionJson(key, value) {
        if (!supportsSessionStorage()) {
            return;
        }

        try {
            window.sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            // Degradacao silenciosa se storage estiver indisponivel ou cheio.
        }
    }

    function readSessionJson(key) {
        if (!supportsSessionStorage()) {
            return null;
        }

        try {
            var rawValue = window.sessionStorage.getItem(key);
            return rawValue ? JSON.parse(rawValue) : null;
        } catch (error) {
            return null;
        }
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getDirectorySearchIndexFromCache() {
        var cacheEntry = readSessionJson(directorySearchCacheKey);
        if (!cacheEntry || !Array.isArray(cacheEntry.index)) {
            return [];
        }

        if ((cacheEntry.refresh_token || '') !== String(directorySearchConfig.refresh_token || '')) {
            return [];
        }

        return cacheEntry.index;
    }

    function persistDirectorySearchIndex(index) {
        var normalizedIndex = Array.isArray(index) ? index : [];
        directorySearchState.index = normalizedIndex;
        writeSessionJson(directorySearchCacheKey, {
            index: normalizedIndex,
            refresh_token: directorySearchConfig.refresh_token || '',
            saved_at: Date.now(),
        });
        writeSessionJson(directorySearchStaleKey, {
            stale: false,
            marked_at: '',
        });
    }

    function isDirectorySearchStale() {
        var state = readSessionJson(directorySearchStaleKey);
        return Boolean(state && state.stale);
    }

    function markDirectorySearchIndexStale(reason) {
        writeSessionJson(directorySearchStaleKey, {
            stale: true,
            marked_at: Date.now(),
            reason: reason || 'mutation',
        });
    }

    function getDirectorySearchIndex() {
        if (directorySearchState.index.length) {
            return directorySearchState.index;
        }

        var cachedIndex = getDirectorySearchIndexFromCache();
        if (cachedIndex.length) {
            directorySearchState.index = cachedIndex;
            return cachedIndex;
        }

        if (Array.isArray(directorySearchConfig.index) && directorySearchConfig.index.length) {
            persistDirectorySearchIndex(directorySearchConfig.index);
            return directorySearchState.index;
        }

        return [];
    }

    function buildStudentHint(row) {
        var studentId = row.getAttribute('data-student-id');
        if (!studentId) {
            return null;
        }

        return {
            id: Number(studentId),
            href: row.getAttribute('data-href') || '',
            full_name: row.getAttribute('data-student-name') || '',
            contact: row.getAttribute('data-student-contact') || '',
            latest_plan_name: row.getAttribute('data-student-plan') || '',
            status: row.getAttribute('data-student-status') || '',
            payment_status: row.getAttribute('data-payment-status') || '',
            due_label: row.getAttribute('data-student-due-label') || '',
            presence_percent: Number(row.getAttribute('data-presence-percent') || '0'),
            cached_at: Date.now(),
            source: 'student-directory',
        };
    }

    function normalizeStudentSnapshot(rawSnapshot) {
        if (!rawSnapshot) {
            return null;
        }

        if (rawSnapshot.financial && rawSnapshot.presence) {
            return rawSnapshot;
        }

        return {
            id: rawSnapshot.id,
            full_name: rawSnapshot.full_name || '',
            email: rawSnapshot.email || '',
            phone: rawSnapshot.phone || rawSnapshot.contact || '',
            status: rawSnapshot.status || '',
            snapshot_version: rawSnapshot.snapshot_version || rawSnapshot.cached_at || '',
            profile_version: rawSnapshot.profile_version || '',
            financial: {
                latest_plan_name: rawSnapshot.latest_plan_name || '',
                latest_payment_status: rawSnapshot.payment_status || '',
                latest_payment_due_date: rawSnapshot.due_label || '',
                overdue_count: rawSnapshot.payment_status === 'overdue' ? 1 : 0,
                pending_count: rawSnapshot.payment_status === 'pending' ? 1 : 0,
            },
            presence: {
                percent_30d: Number(rawSnapshot.presence_percent || 0),
            },
            lock: rawSnapshot.lock || { status: 'free' },
            links: {
                edit: rawSnapshot.href || '',
            },
            generated_at: rawSnapshot.cached_at || '',
            source: rawSnapshot.source || 'student-directory-hint',
        };
    }

    function cacheStudentHint(row) {
        var hint = buildStudentHint(row);
        if (!hint) {
            return;
        }

        writeSessionJson(getSnapshotKey(hint.id), {
            expires_at: Date.now() + prefetchCacheTtlMs,
            payload: normalizeStudentSnapshot(hint),
        });
    }

    function cacheSnapshotPayload(snapshot) {
        if (!snapshot || !snapshot.id) {
            return;
        }

        writeSessionJson(getSnapshotKey(snapshot.id), {
            expires_at: Date.now() + prefetchCacheTtlMs,
            payload: normalizeStudentSnapshot(snapshot),
        });
    }

    function getCachedSnapshot(studentId) {
        var cacheEntry = readSessionJson(getSnapshotKey(studentId));
        if (!cacheEntry || !cacheEntry.payload) {
            return null;
        }

        if (cacheEntry.expires_at && Number(cacheEntry.expires_at) < Date.now()) {
            return null;
        }

        return normalizeStudentSnapshot(cacheEntry.payload);
    }

    function compareVersionValues(leftValue, rightValue) {
        var left = String(leftValue || '');
        var right = String(rightValue || '');
        if (!left && !right) {
            return 0;
        }
        if (!left) {
            return -1;
        }
        if (!right) {
            return 1;
        }
        if (left === right) {
            return 0;
        }
        return left > right ? 1 : -1;
    }

    function markEventProcessed(eventId) {
        if (!eventId) {
            return;
        }

        quickPanelState.processedEventIds.push(eventId);
        if (quickPanelState.processedEventIds.length > 40) {
            quickPanelState.processedEventIds = quickPanelState.processedEventIds.slice(-40);
        }
    }

    function hasProcessedEvent(eventId) {
        return Boolean(eventId) && quickPanelState.processedEventIds.indexOf(eventId) !== -1;
    }

    function bumpRealtimeTelemetry(fieldName) {
        if (!Object.prototype.hasOwnProperty.call(realtimeTelemetry, fieldName)) {
            return;
        }
        realtimeTelemetry[fieldName] += 1;
    }

    function markNavigationHint(row) {
        var hint = buildStudentHint(row);
        if (!hint) {
            return;
        }

        writeSessionJson(navigationHintKey, hint);
    }

    function prefetchStudentDocument(href) {
        var prefetchHref = href ? href.split('#')[0] : '';

        if (!prefetchEnabled || !prefetchHref || prefetchedHrefSet.has(prefetchHref)) {
            return;
        }

        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.as = 'document';
        link.href = prefetchHref;
        document.head.appendChild(link);
        prefetchedHrefSet.add(prefetchHref);
    }

    function getInitials(name) {
        return String(name || '')
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map(function(part) {
                return part.slice(0, 1).toUpperCase();
            })
            .join('') || '?';
    }

    function formatDueLabel(value) {
        if (!value) {
            return '';
        }

        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            var parts = value.split('-');
            return parts[2] + '/' + parts[1] + '/' + parts[0];
        }

        return value;
    }

    function getQuickPanelNode(selector) {
        return quickPanel ? quickPanel.querySelector(selector) : null;
    }

    function setQuickPanelText(selector, value) {
        var node = getQuickPanelNode(selector);
        if (node) {
            node.textContent = value;
        }
    }

    function setQuickPanelHref(selector, value) {
        var node = getQuickPanelNode(selector);
        if (node) {
            node.setAttribute('href', value || '#');
        }
    }

    function openQuickPanelFullRecord(options) {
        var fullRecordLink = getQuickPanelNode('[data-student-quick-open-financial]');
        var href = fullRecordLink ? (fullRecordLink.getAttribute('href') || '') : '';
        if (!href || href === '#') {
            return;
        }

        if (options && options.newTab) {
            window.open(href, '_blank', 'noopener');
            return;
        }

        window.location.assign(href);
    }

    function showQuickFeedback(message, tone) {
        if (!quickFeedback || !message) {
            return;
        }

        var toneClass = 'note-panel--info';
        if (tone === 'success') {
            toneClass = 'note-panel-success-soft';
        } else if (tone === 'error') {
            toneClass = 'note-panel-danger';
        } else if (tone === 'warm') {
            toneClass = 'note-panel-warm';
        }

        quickFeedback.hidden = false;
        quickFeedback.innerHTML = '<div class="note-panel ' + toneClass + '">' + message + '</div>';
    }

    function clearQuickFeedback() {
        if (!quickFeedback) {
            return;
        }

        quickFeedback.hidden = true;
        quickFeedback.innerHTML = '';
    }

    function getQuickSection(name) {
        return quickPanel ? quickPanel.querySelector('[data-student-quick-section="' + name + '"]') : null;
    }

    function getQuickFinancialRoot() {
        return getQuickPanelNode('[data-student-quick-financial]');
    }

    function getSignalState(snapshot) {
        var normalizedSnapshot = normalizeStudentSnapshot(snapshot) || {};
        var financial = normalizedSnapshot.financial || {};
        var presence = normalizedSnapshot.presence || {};
        var presenceValue = Number(presence.percent_30d || 0);
        var overdueCount = Number(financial.overdue_count || 0);
        var pendingCount = Number(financial.pending_count || 0);
        var latestPaymentStatus = financial.latest_payment_status || '';

        return {
            highFrequency: presenceValue >= 85,
            lowTraining: presenceValue > 0 && presenceValue < 45,
            financialRisk: overdueCount > 0 || latestPaymentStatus === 'overdue' || pendingCount >= 2 || latestPaymentStatus === 'pending',
        };
    }

    function syncQuickSignals(snapshot) {
        if (!quickPanel) {
            return;
        }

        var signalState = getSignalState(snapshot);
        var frequencySignal = getQuickPanelNode('[data-student-quick-signal="frequency"]');
        var trainingSignal = getQuickPanelNode('[data-student-quick-signal="training"]');
        var financialSignal = getQuickPanelNode('[data-student-quick-signal="financial"]');

        if (frequencySignal) {
            frequencySignal.hidden = !signalState.highFrequency;
            frequencySignal.className = 'student-quick-signal student-quick-signal--success';
        }

        if (trainingSignal) {
            trainingSignal.hidden = !signalState.lowTraining;
            trainingSignal.className = 'student-quick-signal student-quick-signal--warning';
        }

        if (financialSignal) {
            financialSignal.hidden = !signalState.financialRisk;
            financialSignal.className = 'student-quick-signal student-quick-signal--danger';
        }
    }

    function syncRowSignals(row, snapshot) {
        if (!row) {
            return;
        }

        var signalStrip = row.querySelector('[data-student-signal-strip]');
        if (!signalStrip) {
            return;
        }

        var signalState = getSignalState(snapshot);

        function toggleSignal(name, shouldShow, label, className) {
            var signalNode = signalStrip.querySelector('[data-student-signal="' + name + '"]');
            if (!shouldShow) {
                if (signalNode) {
                    signalNode.remove();
                }
                return;
            }

            if (!signalNode) {
                signalNode = document.createElement('span');
                signalNode.setAttribute('data-student-signal', name);
                signalStrip.appendChild(signalNode);
            }

            signalNode.className = className;
            signalNode.textContent = label;
        }

        toggleSignal('frequency', signalState.highFrequency, 'Alta frequencia', 'student-signal student-signal--success');
        toggleSignal('training', signalState.lowTraining, 'Baixo treino', 'student-signal student-signal--warning');
        toggleSignal('financial', signalState.financialRisk, 'Risco financeiro', 'student-signal student-signal--danger');
    }

    function setQuickLiveState(message, options) {
        var livePill = getQuickPanelNode('[data-student-quick-live-pill]');
        if (!livePill) {
            return;
        }

        var isActive = Boolean(message);
        livePill.hidden = !isActive;
        livePill.classList.toggle('is-pulsing', isActive && !(options && options.static));
        if (isActive) {
            livePill.textContent = message;
        }
    }

    function clearQuickLiveState() {
        setQuickLiveState('');
    }

    function activateQuickPanelTab(name) {
        quickPanelState.activeTab = name;
        var content = getQuickPanelNode('[data-student-quick-content]');
        quickTabButtons.forEach(function(button) {
            var isActive = button.getAttribute('data-student-quick-tab') === name;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });

        if (content) {
            var hasActiveTab = Boolean(name);
            content.hidden = !hasActiveTab;
            content.classList.toggle('is-idle', !hasActiveTab);
        }

        ['profile', 'financial'].forEach(function(sectionName) {
            var section = getQuickSection(sectionName);
            if (section) {
                section.classList.toggle('is-active', sectionName === name);
            }
        });
    }

    function hasLoadedQuickPanelFragments() {
        return Boolean(quickPanelState.fragmentsLoaded.profile || quickPanelState.fragmentsLoaded.financial);
    }

    function ensureQuickPanelTabContent(name, options) {
        if (!quickPanelState.isOpen || !quickPanelState.activeRow || !name) {
            return;
        }

        if (quickPanelState.fragmentsLoaded[name]) {
            if (options && options.refresh) {
                fetchDrawerFragments(quickPanelState.activeRow, {
                    skipLoading: Boolean(options.skipLoading),
                    financialOnly: name === 'financial' && Boolean(options.financialOnly),
                    targetTab: name,
                });
            }
            return;
        }

        fetchDrawerFragments(quickPanelState.activeRow, {
            skipLoading: Boolean(options && options.skipLoading),
            targetTab: name,
        });
    }

    function setQuickPanelChip(selector, value, tone) {
        var node = getQuickPanelNode(selector);
        if (!node) {
            return;
        }

        node.textContent = value;
        node.classList.remove('is-danger', 'is-warning', 'is-success', 'is-info');
        if (tone) {
            node.classList.add(tone);
        }
    }

    function describeLock(lock) {
        if (!lock || lock.status === 'free') {
            return { label: 'Lock livre', tone: 'is-success' };
        }

        if (lock.status === 'owner') {
            return { label: 'Lock seu', tone: 'is-info' };
        }

        if (lock.status === 'blocked') {
            var holder = lock.holder || {};
            var holderName = holder.user_display || 'Outro operador';
            return { label: 'Lock de ' + holderName, tone: 'is-warning' };
        }

        return { label: 'Lock em leitura', tone: '' };
    }

    function describePaymentTone(financial) {
        if ((financial.overdue_count || 0) > 0) {
            return { label: 'Atrasado', tone: 'is-danger' };
        }

        if ((financial.pending_count || 0) > 0) {
            return { label: 'Pendente', tone: 'is-warning' };
        }

        if (financial.latest_payment_status === 'paid') {
            return { label: 'Em dia', tone: 'is-success' };
        }

        return { label: 'Sem leitura', tone: '' };
    }

    function buildNextStepCopy(snapshot) {
        var financial = snapshot.financial || {};
        var lock = snapshot.lock || {};
        var presence = snapshot.presence || {};

        if ((financial.overdue_count || 0) > 0) {
            return 'Existe cobranca em atraso. O melhor atalho agora e abrir o financeiro e agir antes de entrar em edicao.';
        }

        if (lock.status === 'blocked') {
            return 'A ficha esta ocupada por outro operador. Voce pode ler o contexto agora e combinar a edicao com seguranca.';
        }

        if ((presence.percent_30d || 0) < 50) {
            return 'A frequencia recente caiu. Vale revisar contexto e decidir se a conversa agora e operacional ou comercial.';
        }

        return 'A base parece sob controle. Abra a ficha completa apenas se for realmente aprofundar ou editar algo.';
    }

    function populateQuickPanel(snapshot) {
        if (!quickPanel || !snapshot) {
            return;
        }

        var normalizedSnapshot = normalizeStudentSnapshot(snapshot);
        var financial = normalizedSnapshot.financial || {};
        var presence = normalizedSnapshot.presence || {};
        var lockDescriptor = describeLock(normalizedSnapshot.lock || {});
        var paymentDescriptor = describePaymentTone(financial);
        var dueLabel = formatDueLabel(financial.latest_payment_due_date || '');
        var dueCopy = dueLabel ? 'Vence em ' + dueLabel : 'Sem vencimento visivel';
        var overdueCount = financial.overdue_count || 0;
        var pendingCount = financial.pending_count || 0;

        setQuickPanelText('[data-student-quick-avatar]', getInitials(normalizedSnapshot.full_name));
        setQuickPanelText('[data-student-quick-name]', normalizedSnapshot.full_name || 'Aluno');
        setQuickPanelText('[data-student-quick-contact]', normalizedSnapshot.email || normalizedSnapshot.phone || 'Sem contato principal');
        setQuickPanelChip('[data-student-quick-status]', normalizedSnapshot.status || 'Sem status', normalizedSnapshot.status === 'active' ? 'is-success' : normalizedSnapshot.status === 'inactive' ? 'is-warning' : 'is-info');
        setQuickPanelChip('[data-student-quick-plan]', 'Plano ' + (financial.latest_plan_name || '--'), financial.latest_plan_name ? 'is-info' : '');
        setQuickPanelChip('[data-student-quick-lock]', lockDescriptor.label, lockDescriptor.tone);
        setQuickPanelText('[data-student-quick-payment-status]', paymentDescriptor.label);
        setQuickPanelText('[data-student-quick-presence]', String(presence.percent_30d || 0) + '%');
        setQuickPanelText('[data-student-quick-overdue]', String(overdueCount));
        setQuickPanelText('[data-student-quick-pending]', String(pendingCount));
        setQuickPanelText('[data-student-quick-next-step]', buildNextStepCopy(normalizedSnapshot));
        setQuickPanelHref('[data-student-quick-open-financial]', (normalizedSnapshot.links || {}).edit || quickPanelState.activeHref || '');
        syncQuickSignals(normalizedSnapshot);
    }

    function syncRowFromSnapshot(row, snapshot) {
        var normalizedSnapshot = normalizeStudentSnapshot(snapshot);
        if (!row || !normalizedSnapshot) {
            return;
        }

        var financial = normalizedSnapshot.financial || {};
        var presence = normalizedSnapshot.presence || {};
        row.setAttribute('data-student-name', normalizedSnapshot.full_name || '');
        row.setAttribute('data-student-contact', normalizedSnapshot.email || normalizedSnapshot.phone || '');
        row.setAttribute('data-student-plan', financial.latest_plan_name || '');
        row.setAttribute('data-student-status', normalizedSnapshot.status || '');
        row.setAttribute('data-payment-status', financial.latest_payment_status || '');
        row.setAttribute('data-presence-percent', String(presence.percent_30d || 0));
        row.setAttribute('data-student-due-label', formatDueLabel(financial.latest_payment_due_date || ''));
        row.setAttribute(
            'data-search-index',
            ((normalizedSnapshot.full_name || '') + ' ' + (normalizedSnapshot.email || normalizedSnapshot.phone || '') + ' ' + (financial.latest_plan_name || '--')).toLowerCase()
        );
        row.removeAttribute('data-search-normalized');

        var nameNode = row.querySelector('.student-name');
        if (nameNode) nameNode.textContent = normalizedSnapshot.full_name || '';

        var emailNode = row.querySelector('.student-email');
        if (emailNode) emailNode.textContent = normalizedSnapshot.email || normalizedSnapshot.phone || '';

        var planNode = row.querySelector('.student-plan-name');
        if (planNode) planNode.textContent = financial.latest_plan_name || '--';

        var presenceNode = row.querySelector('.student-presence-value');
        if (presenceNode) {
            presenceNode.textContent = String(presence.percent_30d || 0) + '%';
            presenceNode.classList.remove('is-high', 'is-mid', 'is-low');
            presenceNode.classList.add((presence.percent_30d || 0) >= 85 ? 'is-high' : (presence.percent_30d || 0) >= 60 ? 'is-mid' : 'is-low');
        }

        var paymentNode = row.querySelector('.student-payment-state');
        if (paymentNode) {
            paymentNode.className = 'student-payment-state';
            if (financial.latest_payment_status === 'overdue') {
                paymentNode.classList.add('student-payment-state--red');
                paymentNode.textContent = 'Atrasado';
            } else if (financial.latest_payment_status === 'pending') {
                paymentNode.classList.add('student-payment-state--orange');
                paymentNode.textContent = 'Pendente';
            } else if (financial.latest_payment_status === 'paid') {
                paymentNode.classList.add('student-payment-state--green');
                paymentNode.textContent = 'Em dia';
            } else {
                paymentNode.classList.add('student-payment-state--gray');
                paymentNode.textContent = 'Cancelado';
            }
        }

        var dueNode = row.querySelector('.student-due-date');
        if (dueNode) {
            dueNode.textContent = formatDueLabel(financial.latest_payment_due_date || '') || '--';
        }

        syncRowSignals(row, normalizedSnapshot);
    }

    function applySnapshotUpdate(snapshot) {
        if (!snapshot) {
            return;
        }

        var normalizedSnapshot = normalizeStudentSnapshot(snapshot);
        cacheSnapshotPayload(normalizedSnapshot);
        quickPanelState.currentSnapshotVersion = normalizedSnapshot.snapshot_version || quickPanelState.currentSnapshotVersion;
        quickPanelState.currentProfileVersion = normalizedSnapshot.profile_version || quickPanelState.currentProfileVersion;
        populateQuickPanel(normalizedSnapshot);
        syncRowFromSnapshot(quickPanelState.activeRow, normalizedSnapshot);
        applyLocalDirectoryState();
    }

    function stopQuickPanelReadPolling() {
        if (quickPanelState.liveRefreshTimerId) {
            window.clearInterval(quickPanelState.liveRefreshTimerId);
            quickPanelState.liveRefreshTimerId = null;
        }
    }

    function stopQuickPanelHeartbeat() {
        if (quickPanelState.heartbeatTimerId) {
            window.clearInterval(quickPanelState.heartbeatTimerId);
            quickPanelState.heartbeatTimerId = null;
        }
    }

    function disconnectQuickPanelEventStream() {
        if (quickPanelState.eventSource) {
            quickPanelState.eventSource.close();
            quickPanelState.eventSource = null;
        }
        quickPanelState.sseConnected = false;
    }

    function handleQuickPanelStreamPayload(payload) {
        if (!payload || Number(payload.student_id || 0) !== Number(quickPanelState.studentId || 0)) {
            return;
        }

        if (hasProcessedEvent(payload.event_id)) {
            bumpRealtimeTelemetry('duplicateEventsIgnored');
            return;
        }
        markEventProcessed(payload.event_id);

        var payloadSnapshotVersion = String(payload.snapshot_version || '');
        var payloadProfileVersion = String(payload.profile_version || '');

        if (payload.type === 'student.lock.preempted' && quickPanelState.editSessionActive) {
            handleLostDrawerLock({
                holder: ((payload.meta || {}).holder) || {},
            });
            return;
        }

        if (payload.type === 'student.payment.updated' || payload.type === 'student.enrollment.updated' || payload.type === 'student.profile.updated') {
            markDirectorySearchIndexStale(payload.type);
        }

        if (payload.type === 'student.profile.updated' && quickPanelState.editSessionActive) {
            if (payloadProfileVersion && compareVersionValues(payloadProfileVersion, quickPanelState.currentProfileVersion) <= 0) {
                bumpRealtimeTelemetry('staleEventsIgnored');
                return;
            }
            bumpRealtimeTelemetry('profileEventsDeferred');
            showQuickFeedback('A ficha mudou em outra frente enquanto voce edita. Vamos preservar seu rascunho e validar no salvar.', 'warm');
            setQuickLiveState('Mudanca externa detectada', { static: true });
            return;
        }

        if (payloadSnapshotVersion && compareVersionValues(payloadSnapshotVersion, quickPanelState.currentSnapshotVersion) < 0) {
            bumpRealtimeTelemetry('staleEventsIgnored');
            return;
        }

        setQuickLiveState('Atualizado em tempo real', { static: true });
        refreshQuickDrawerFromCurrentRow(
            quickPanelState.editSessionActive && (payload.type === 'student.payment.updated' || payload.type === 'student.enrollment.updated')
                ? {
                    forceFragments: true,
                    skipLoading: true,
                    financialOnly: true,
                }
                : {
                    forceFragments: true,
                    skipLoading: true,
                }
        );
        window.setTimeout(function() {
            if (quickPanelState.isOpen && !quickPanelState.editSessionActive) {
                clearQuickLiveState();
            }
        }, 1600);
    }

    function connectQuickPanelEventStream() {
        var streamUrl = getRowEndpoint(quickPanelState.activeRow, 'data-student-events-stream-url');
        if (!quickPanelState.isOpen || !streamUrl || typeof window.EventSource === 'undefined') {
            return;
        }

        disconnectQuickPanelEventStream();

        var eventSource = new window.EventSource(streamUrl);
        quickPanelState.eventSource = eventSource;

        function onStudentEvent(event) {
            try {
                handleQuickPanelStreamPayload(JSON.parse(event.data || '{}'));
            } catch (error) {
                return;
            }
        }

        eventSource.addEventListener('stream.ready', function() {
            quickPanelState.sseConnected = true;
        });
        eventSource.addEventListener('student.lock.acquired', onStudentEvent);
        eventSource.addEventListener('student.lock.released', onStudentEvent);
        eventSource.addEventListener('student.lock.preempted', onStudentEvent);
        eventSource.addEventListener('student.payment.updated', onStudentEvent);
        eventSource.addEventListener('student.enrollment.updated', onStudentEvent);
        eventSource.addEventListener('student.profile.updated', onStudentEvent);
        eventSource.onerror = function() {
            quickPanelState.sseConnected = false;
        };
    }

    function refreshQuickPanelReadState(options) {
        if (!quickPanelState.isOpen || !quickPanelState.activeRow || quickPanelState.editSessionActive || document.hidden || quickPanelState.refreshInFlight) {
            return;
        }

        quickPanelState.refreshInFlight = true;
        setQuickLiveState('Atualizando leitura');

        fetch(getRowEndpoint(quickPanelState.activeRow, 'data-student-lock-status-url'), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(response) {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then(function(lockPayload) {
                var cachedSnapshot = getCachedSnapshot(quickPanelState.studentId) || buildStudentHint(quickPanelState.activeRow);
                if (!lockPayload || !cachedSnapshot) {
                    return;
                }

                cachedSnapshot.lock = lockPayload.status === 'blocked'
                    ? { status: 'blocked', holder: lockPayload.holder || {} }
                    : lockPayload.status === 'owner'
                        ? { status: 'owner' }
                        : { status: 'free' };
                applySnapshotUpdate(cachedSnapshot);
            })
            .catch(function() {
                return null;
            })
            .finally(function() {
                fetchSnapshotForRow(quickPanelState.activeRow, { force: true });
                if (options && options.forceFragments && !quickPanelState.editSessionActive && hasLoadedQuickPanelFragments()) {
                    var now = Date.now();
                    if ((now - quickPanelState.lastFragmentRefreshAt) > 45000) {
                        quickPanelState.lastFragmentRefreshAt = now;
                        fetchDrawerFragments(quickPanelState.activeRow, {
                            skipLoading: true,
                            financialOnly: quickPanelState.fragmentsLoaded.financial && !quickPanelState.fragmentsLoaded.profile,
                            targetTab: quickPanelState.fragmentsLoaded.profile && !quickPanelState.fragmentsLoaded.financial
                                ? 'profile'
                                : quickPanelState.fragmentsLoaded.financial && !quickPanelState.fragmentsLoaded.profile
                                    ? 'financial'
                                    : '',
                        });
                    }
                }

                quickPanelState.refreshInFlight = false;
                clearQuickLiveState();
            });
    }

    function startQuickPanelReadPolling() {
        stopQuickPanelReadPolling();
        if (!quickPanelState.isOpen || quickPanelState.editSessionActive) {
            return;
        }

        quickPanelState.liveRefreshTimerId = window.setInterval(function() {
            refreshQuickPanelReadState({
                forceFragments: true,
            });
        }, 25000);
    }

    function handleLostDrawerLock(payload) {
        var profileForm = getQuickPanelNode('[data-student-quick-profile-slot] [data-student-profile-form]');
        if (profileForm) {
            setDrawerProfileReadonlyState(profileForm, true);
            syncDrawerEditToggle(profileForm, false);
        }

        quickPanelState.editSessionActive = false;
        stopQuickPanelHeartbeat();

        var holder = (payload && payload.holder) || {};
        var holderName = holder.user_display || 'outro operador';
        showQuickFeedback('A edicao mudou de maos e voltou para leitura. Agora quem segura a caneta e ' + holderName + '.', 'error');
        refreshQuickDrawerFromCurrentRow({ forceFragments: true });
        startQuickPanelReadPolling();
    }

    function heartbeatDrawerEditSession() {
        var heartbeatUrl = getRowEndpoint(quickPanelState.activeRow, 'data-student-lock-heartbeat-url');
        if (!quickPanelState.isOpen || !quickPanelState.editSessionActive || !heartbeatUrl || document.hidden) {
            return;
        }

        fetch(heartbeatUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(response) {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then(function(payload) {
                if (!payload) {
                    return;
                }

                if (payload.status === 'active' || payload.status === 'reacquired' || payload.status === 'dev_bypass') {
                    setQuickLiveState('Edicao sincronizada');
                    populateQuickPanel(Object.assign(getCachedSnapshot(quickPanelState.studentId) || {}, {
                        lock: { status: 'owner' },
                    }));
                    window.setTimeout(function() {
                        if (quickPanelState.editSessionActive) {
                            clearQuickLiveState();
                        }
                    }, 1200);
                    return;
                }

                if (payload.status === 'stolen' || payload.status === 'blocked') {
                    handleLostDrawerLock(payload);
                }
            })
            .catch(function() {
                clearQuickLiveState();
            });
    }

    function startQuickPanelHeartbeat() {
        stopQuickPanelHeartbeat();
        if (!quickPanelState.isOpen || !quickPanelState.editSessionActive) {
            return;
        }

        heartbeatDrawerEditSession();
        quickPanelState.heartbeatTimerId = window.setInterval(heartbeatDrawerEditSession, 8000);
    }

    function openQuickPanelForRow(row, snapshot) {
        if (!quickPanel || !quickOverlay) {
            return;
        }

        quickPanelState.studentId = Number(row.getAttribute('data-student-id') || '0');
        quickPanelState.activeHref = row.getAttribute('data-href') || '';
        quickPanelState.activeRow = row;
        quickPanelState.isOpen = true;
        quickPanelState.activeTab = '';
        quickPanelState.fragmentsLoaded = {
            profile: false,
            financial: false,
        };
        quickPanelState.editSessionActive = false;
        quickPanelState.lastFragmentRefreshAt = 0;
        quickPanelState.currentSnapshotVersion = '';
        quickPanelState.currentProfileVersion = '';
        quickPanelState.processedEventIds = [];

        clearQuickFeedback();
        clearQuickLiveState();
        var initialSnapshot = normalizeStudentSnapshot(snapshot || buildStudentHint(row));
        quickPanelState.currentSnapshotVersion = initialSnapshot ? (initialSnapshot.snapshot_version || '') : '';
        quickPanelState.currentProfileVersion = initialSnapshot ? (initialSnapshot.profile_version || '') : '';
        resetQuickPanelFragmentSlots();
        populateQuickPanel(initialSnapshot);
        activateQuickPanelTab('');
        quickOverlay.hidden = false;
        quickPanel.classList.add('is-open');
        quickPanel.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        quickPanel.focus();

        var quickUrl = '#student-' + quickPanelState.studentId;
        if (window.location.hash !== quickUrl) {
            history.pushState({ studentQuickPanel: true, studentId: quickPanelState.studentId }, '', quickUrl);
        }

        connectQuickPanelEventStream();
        startQuickPanelReadPolling();
    }

    function closeQuickPanel(options) {
        if (!quickPanel || !quickOverlay || !quickPanelState.isOpen) {
            return;
        }

        var activeProfileForm = quickPanel.querySelector('[data-student-quick-profile-slot] [data-student-profile-form]');
        if (activeProfileForm && !activeProfileForm.classList.contains('is-readonly')) {
            stopDrawerEditSession();
        }

        disconnectQuickPanelEventStream();
        stopQuickPanelReadPolling();
        stopQuickPanelHeartbeat();
        quickPanelState.isOpen = false;
        quickPanelState.studentId = null;
        quickPanelState.activeHref = '';
        quickPanelState.activeRow = null;
        quickPanelState.activeTab = '';
        quickPanelState.fragmentsLoaded = {
            profile: false,
            financial: false,
        };
        quickPanelState.editSessionActive = false;
        quickPanelState.refreshInFlight = false;
        quickPanelState.sseConnected = false;
        quickPanelState.currentSnapshotVersion = '';
        quickPanelState.currentProfileVersion = '';
        quickPanelState.processedEventIds = [];
        quickPanel.classList.remove('is-open');
        quickPanel.setAttribute('aria-hidden', 'true');
        quickOverlay.hidden = true;
        document.body.style.overflow = '';
        clearQuickLiveState();
        resetQuickPanelFragmentSlots();

        if (!(options && options.skipHistory) && String(window.location.hash || '').indexOf('#student-') === 0) {
            history.back();
        }
    }

    function warmStudentRow(row) {
        if (!row || row.hidden) {
            return;
        }

        cacheStudentHint(row);
        fetchSnapshotForRow(row);
        prefetchStudentDocument(row.getAttribute('data-href') || '');
    }

    function fetchSnapshotForRow(row, options) {
        var snapshotUrl = row.getAttribute('data-student-snapshot-url');
        var forceRefresh = Boolean(options && options.force);
        if (!snapshotUrl || ((!forceRefresh && prefetchedSnapshotSet.has(snapshotUrl)) || inFlightSnapshotSet.has(snapshotUrl))) {
            return;
        }

        inFlightSnapshotSet.add(snapshotUrl);

        fetch(snapshotUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(response) {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then(function(data) {
                if (!data || data.status !== 'ok' || !data.snapshot) {
                    return;
                }

                applySnapshotUpdate(data.snapshot);
                if (quickPanelState.isOpen && quickPanelState.studentId === Number(data.snapshot.id || 0)) {
                    populateQuickPanel(data.snapshot);
                }
                prefetchedSnapshotSet.add(snapshotUrl);
            })
            .catch(function() {
                // Se o prefetch JSON falhar, mantemos apenas o hint local e seguimos.
            })
            .finally(function() {
                inFlightSnapshotSet.delete(snapshotUrl);
            });
    }

    function getRowEndpoint(row, attributeName) {
        return row ? row.getAttribute(attributeName) || '' : '';
    }

    function setDrawerProfileReadonlyState(form, shouldLock) {
        if (!form) {
            return;
        }

        form.classList.toggle('is-readonly', shouldLock);
        form.querySelectorAll('input, textarea, select').forEach(function(field) {
            if (field.type === 'hidden') {
                return;
            }

            if (field.tagName === 'SELECT') {
                field.disabled = shouldLock;
                return;
            }

            field.readOnly = shouldLock;
        });

        form.querySelectorAll('button[type="submit"]').forEach(function(button) {
            button.disabled = shouldLock;
            button.hidden = shouldLock;
        });
    }

    function syncDrawerEditToggle(form, editable) {
        var editButton = form ? form.querySelector('[data-action="toggle-student-profile-edit"]') : null;
        if (!editButton) {
            return;
        }

        editButton.textContent = editable ? 'Encerrar edição' : 'Editar leitura';
        editButton.setAttribute('aria-pressed', editable ? 'true' : 'false');
    }

    function showDrawerFragmentsLoading() {
        var profileSlot = getQuickPanelNode('[data-student-quick-profile-slot]');
        var financialSlot = getQuickPanelNode('[data-student-quick-financial-slot]');
        if (profileSlot) {
            profileSlot.innerHTML = '<p class="student-quick-panel__copy">Carregando perfil...</p>';
        }
        if (financialSlot) {
            financialSlot.innerHTML = '<p class="student-quick-panel__copy">Carregando financeiro...</p>';
        }
    }

    function resetQuickPanelFragmentSlots() {
        showDrawerFragmentsLoading();
        closeQuickFinancialDrawers();
    }

    function mountDrawerFragments(payload) {
        if (!payload || !payload.fragments) {
            return;
        }

        var profileSlot = getQuickPanelNode('[data-student-quick-profile-slot]');
        var financialSlot = getQuickPanelNode('[data-student-quick-financial-slot]');

        if (profileSlot && typeof payload.fragments.profile === 'string') {
            profileSlot.innerHTML = payload.fragments.profile;
            quickPanelState.fragmentsLoaded.profile = true;
            var profileForm = profileSlot.querySelector('[data-student-profile-form]');
            if (profileForm) {
                setDrawerProfileReadonlyState(profileForm, !quickPanelState.editSessionActive);
                syncDrawerEditToggle(profileForm, quickPanelState.editSessionActive);
            }
        }

        if (financialSlot && typeof payload.fragments.financial === 'string') {
            financialSlot.innerHTML = payload.fragments.financial;
            quickPanelState.fragmentsLoaded.financial = true;
        }
    }

    function mountDrawerProfileFragment(payload) {
        if (!payload || !payload.fragments || typeof payload.fragments.profile !== 'string') {
            return;
        }

        var profileSlot = getQuickPanelNode('[data-student-quick-profile-slot]');
        if (profileSlot) {
            profileSlot.innerHTML = payload.fragments.profile;
            quickPanelState.fragmentsLoaded.profile = true;
            var profileForm = profileSlot.querySelector('[data-student-profile-form]');
            if (profileForm) {
                setDrawerProfileReadonlyState(profileForm, !quickPanelState.editSessionActive);
                syncDrawerEditToggle(profileForm, quickPanelState.editSessionActive);
            }
        }
    }

    function mountDrawerFinancialFragment(payload) {
        if (!payload || !payload.fragments || typeof payload.fragments.financial !== 'string') {
            return;
        }

        var financialSlot = getQuickPanelNode('[data-student-quick-financial-slot]');
        if (financialSlot) {
            financialSlot.innerHTML = payload.fragments.financial;
            quickPanelState.fragmentsLoaded.financial = true;
        }
    }

    function replaceQuickFinancialSlot(selector, html) {
        var slot = getQuickPanelNode(selector);
        if (slot && typeof html === 'string') {
            slot.innerHTML = html;
        }
    }

    function applyQuickFinancialFragments(fragments) {
        if (!fragments) {
            return;
        }

        replaceQuickFinancialSlot('[data-quick-financial-summary-slot]', fragments.quick_payments_summary || fragments.payments_summary);
        replaceQuickFinancialSlot('[data-quick-financial-ledger-slot]', fragments.quick_ledger || fragments.ledger);
    }

    function closeQuickFinancialDrawers() {
        if (!quickPanel) {
            return;
        }

        quickPanel.querySelectorAll('[data-quick-financial-drawer]').forEach(function(drawer) {
            drawer.hidden = true;
        });
    }

    function openQuickFinancialDrawer(name) {
        closeQuickFinancialDrawers();
        var drawer = getQuickPanelNode('[data-quick-financial-drawer="' + name + '"]');
        if (drawer) {
            drawer.hidden = false;
        }

        if (name === 'checkout') {
            startDrawerEditSession({ silent: true });
        }
    }

    function getCsrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function handleQuickFinancialJson(url, options) {
        return fetch(url, options).then(function(response) {
            var contentType = response.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                throw new Error('O servidor respondeu fora do contrato JSON esperado.');
            }

            return response.json().then(function(payload) {
                if (!response.ok || (payload.status !== 'success' && payload.status !== 'ok')) {
                    throw new Error(payload.message || 'Nao foi possivel concluir a acao financeira agora.');
                }
                return payload;
            });
        });
    }

    function buildQuickConfirmDialog() {
        var dialog = document.createElement('dialog');
        dialog.className = 'student-quick-confirm-dialog';
        dialog.innerHTML = [
            '<form method="dialog" class="student-quick-confirm-dialog__card">',
            '<div class="stack-8">',
            '<p class="eyebrow">Confirmacao</p>',
            '<h3 class="section-title-sm">Deseja continuar?</h3>',
            '<p class="meta-text" data-student-quick-confirm-copy>Confirme a acao antes de seguir.</p>',
            '</div>',
            '<div class="student-quick-confirm-dialog__actions">',
            '<button type="button" class="button secondary" value="cancel" data-student-quick-confirm-cancel>Nao</button>',
            '<button type="submit" class="button" value="confirm">Sim</button>',
            '</div>',
            '</form>',
        ].join('');
        document.body.appendChild(dialog);
        return dialog;
    }

    function getQuickConfirmDialog() {
        return document.querySelector('.student-quick-confirm-dialog') || buildQuickConfirmDialog();
    }

    function askQuickConfirmation(message) {
        var dialog = getQuickConfirmDialog();
        var form = dialog.querySelector('form');
        var cancelButton = dialog.querySelector('[data-student-quick-confirm-cancel]');
        var copy = dialog.querySelector('[data-student-quick-confirm-copy]');

        if (copy) {
            copy.textContent = message || 'Confirme a acao antes de seguir.';
        }

        return new Promise(function(resolve) {
            function cleanup(result) {
                form.removeEventListener('submit', onSubmit);
                cancelButton.removeEventListener('click', onCancel);
                dialog.removeEventListener('cancel', onCancel);
                if (dialog.open) {
                    dialog.close();
                }
                resolve(result);
            }

            function onSubmit(event) {
                event.preventDefault();
                cleanup(true);
            }

            function onCancel(event) {
                if (event) {
                    event.preventDefault();
                }
                cleanup(false);
            }

            form.addEventListener('submit', onSubmit);
            cancelButton.addEventListener('click', onCancel);
            dialog.addEventListener('cancel', onCancel);
            dialog.showModal();
            cancelButton.focus();
        });
    }

    function refreshQuickDrawerFromCurrentRow(options) {
        if (!quickPanelState.activeRow) {
            return;
        }

        fetchSnapshotForRow(quickPanelState.activeRow, { force: true });
        var shouldFetchFragments = options && options.forceFragments
            ? hasLoadedQuickPanelFragments() || quickPanelState.editSessionActive
            : true;
        if (!(options && options.skipFragments) && shouldFetchFragments) {
            fetchDrawerFragments(quickPanelState.activeRow, {
                skipLoading: Boolean(options && options.skipLoading),
                financialOnly: Boolean(options && options.financialOnly),
            });
        }
    }

    function submitQuickFinancialForm(form) {
        var formData = new FormData(form);
        handleQuickFinancialJson(form.getAttribute('action') || form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: formData,
        })
            .then(function(payload) {
                if (payload.fragments) {
                    applyQuickFinancialFragments(payload.fragments);
                }
                markDirectorySearchIndexStale('financial_mutation');
                showQuickFeedback(payload.message || 'Financeiro atualizado com sucesso.', 'success');
                refreshQuickDrawerFromCurrentRow();
            })
            .catch(function(error) {
                showQuickFeedback(error.message, 'error');
            });
    }

    function loadQuickPaymentIntoDrawer(paymentId, trigger) {
        if (!quickPanelState.studentId || !paymentId) {
            openQuickFinancialDrawer('checkout');
            return;
        }

        handleQuickFinancialJson('/alunos/' + quickPanelState.studentId + '/financeiro/cobranca/' + paymentId + '/drawer/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(payload) {
                if (payload.fragments) {
                    applyQuickFinancialFragments(payload.fragments);
                }
                openQuickFinancialDrawer('checkout');

                var statusMsg = getQuickPanelNode('#student-payment-checkout-status');
                if (statusMsg && payload.message) {
                    statusMsg.hidden = false;
                    statusMsg.textContent = payload.message;
                }
            })
            .catch(function() {
                openQuickFinancialDrawer('checkout');
                if (trigger && trigger.dataset) {
                    var statusMsg = getQuickPanelNode('#student-payment-checkout-status');
                    if (statusMsg) {
                        statusMsg.hidden = false;
                        statusMsg.textContent = 'Cobranca pronta para revisar.';
                    }
                }
            });
    }

    function fetchDrawerFragments(row, options) {
        var fragmentsUrl = getRowEndpoint(row, 'data-student-drawer-fragments-url');
        if (!fragmentsUrl) {
            return;
        }

        if (!(options && options.skipLoading)) {
            showDrawerFragmentsLoading();
        }

        fetch(fragmentsUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(response) {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then(function(payload) {
                if (!payload || payload.status !== 'ok') {
                    return;
                }

                applySnapshotUpdate(payload.snapshot);
                if (quickPanelState.isOpen && quickPanelState.studentId === Number(payload.snapshot.id || 0)) {
                    if (options && options.targetTab === 'profile') {
                        mountDrawerProfileFragment(payload);
                    } else if (options && options.financialOnly) {
                        mountDrawerFinancialFragment(payload);
                    } else if (options && options.targetTab === 'financial') {
                        mountDrawerFinancialFragment(payload);
                    } else {
                        mountDrawerFragments(payload);
                    }
                    quickPanelState.lastFragmentRefreshAt = Date.now();
                }
            })
            .catch(function() {
                // Se falhar, preservamos a leitura curta e a navegação completa continua disponivel.
            });
    }

    function startDrawerEditSession(options) {
        var row = quickPanelState.activeRow;
        var startUrl = getRowEndpoint(row, 'data-student-edit-start-url');
        var profileForm = getQuickPanelNode('[data-student-quick-profile-slot] [data-student-profile-form]');
        var shouldActivateProfile = !(options && options.skipActivateProfile);

        if (!startUrl) {
            return;
        }

        if (quickPanelState.editSessionActive) {
            if (profileForm) {
                setDrawerProfileReadonlyState(profileForm, false);
                syncDrawerEditToggle(profileForm, true);
            }
            if (shouldActivateProfile && profileForm) {
                activateQuickPanelTab('profile');
            }
            return;
        }

        if (options && options.silent) {
            var financialStatus = getQuickPanelNode('#student-payment-checkout-status');
            if (financialStatus) {
                financialStatus.hidden = false;
                financialStatus.textContent = 'Liberando edicao para confirmar o pagamento...';
            }
        }

        fetch(startUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/) ? decodeURIComponent(document.cookie.match(/csrftoken=([^;]+)/)[1]) : '',
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        })
            .then(function(response) {
                return response.json().catch(function() { return {}; }).then(function(data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function(result) {
                if (!result.ok || result.data.status !== 'granted') {
                    var holder = (result.data && result.data.holder) || {};
                    var holderCopy = holder.user_display ? ' ' + holder.user_display + ' ja esta com a prioridade.' : '';
                    showQuickFeedback('Nao foi possivel iniciar a edicao agora.' + holderCopy, 'error');
                    return;
                }

                stopQuickPanelReadPolling();
                quickPanelState.editSessionActive = true;
                if (profileForm) {
                    setDrawerProfileReadonlyState(profileForm, false);
                    syncDrawerEditToggle(profileForm, true);
                }
                populateQuickPanel(Object.assign(getCachedSnapshot(quickPanelState.studentId) || {}, {
                    lock: { status: 'owner' },
                }));
                if (!(options && options.silent)) {
                    showQuickFeedback('Edicao liberada para voce.', 'warm');
                }
                setQuickLiveState('Edicao ao vivo');
                if (shouldActivateProfile && profileForm) {
                    activateQuickPanelTab('profile');
                }
                startQuickPanelHeartbeat();
            });
    }

    function stopDrawerEditSession() {
        var row = quickPanelState.activeRow;
        var releaseUrl = getRowEndpoint(row, 'data-student-edit-release-url');
        var profileForm = getQuickPanelNode('[data-student-quick-profile-slot] [data-student-profile-form]');
        if (!profileForm) {
            return;
        }

        if (releaseUrl) {
            fetch(releaseUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/) ? decodeURIComponent(document.cookie.match(/csrftoken=([^;]+)/)[1]) : '',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            }).finally(function() {
                quickPanelState.editSessionActive = false;
                stopQuickPanelHeartbeat();
                setDrawerProfileReadonlyState(profileForm, true);
                syncDrawerEditToggle(profileForm, false);
                showQuickFeedback('Edicao encerrada. A ficha voltou para leitura.', 'warm');
                clearQuickLiveState();
                fetchSnapshotForRow(row, { force: true });
                startQuickPanelReadPolling();
            });
            return;
        }

        quickPanelState.editSessionActive = false;
        stopQuickPanelHeartbeat();
        setDrawerProfileReadonlyState(profileForm, true);
        syncDrawerEditToggle(profileForm, false);
        clearQuickLiveState();
        startQuickPanelReadPolling();
    }

    function submitDrawerProfileForm(form) {
        var row = quickPanelState.activeRow;
        var saveUrl = getRowEndpoint(row, 'data-student-drawer-profile-url');
        if (!saveUrl) {
            return;
        }

        var formData = new FormData(form);
        fetch(saveUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/) ? decodeURIComponent(document.cookie.match(/csrftoken=([^;]+)/)[1]) : '',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData,
            credentials: 'same-origin',
        })
            .then(function(response) {
                return response.json().catch(function() { return {}; }).then(function(data) {
                    return { ok: response.ok, status: response.status, data: data };
                });
            })
            .then(function(result) {
                if (!result.data) {
                    return;
                }

                if (result.data.snapshot) {
                    applySnapshotUpdate(result.data.snapshot);
                }

                if (result.data.fragments) {
                    mountDrawerFragments(result.data);
                    activateQuickPanelTab('profile');
                }

                if (result.ok) {
                    markDirectorySearchIndexStale('profile_mutation');
                    setQuickLiveState('Alteracoes salvas', { static: true });
                    window.setTimeout(function() {
                        if (quickPanelState.isOpen) {
                            clearQuickLiveState();
                        }
                    }, 1600);
                }

                showQuickFeedback(result.data.message || (result.ok ? 'Perfil atualizado com sucesso.' : 'Revise os campos destacados antes de salvar.'), result.ok ? 'success' : 'error');
                if (result.status === 409 || result.data.status === 'conflict') {
                    bumpRealtimeTelemetry('conflictResponses');
                    setDrawerProfileReadonlyState(form, true);
                    syncDrawerEditToggle(form, false);
                    quickPanelState.editSessionActive = false;
                    stopQuickPanelHeartbeat();
                    startQuickPanelReadPolling();
                }
            });
    }

    function scheduleRowWarmup(row) {
        if (!prefetchEnabled || !row) {
            return;
        }

        if (rowPrefetchTimers.has(row)) {
            window.clearTimeout(rowPrefetchTimers.get(row));
        }

        var timerId = window.setTimeout(function() {
            rowPrefetchTimers.delete(row);
            warmStudentRow(row);
        }, prefetchHoverDelayMs);

        rowPrefetchTimers.set(row, timerId);
    }

    function cancelRowWarmup(row) {
        if (!rowPrefetchTimers.has(row)) {
            return;
        }

        window.clearTimeout(rowPrefetchTimers.get(row));
        rowPrefetchTimers.delete(row);
    }

    function prefetchInitialRows() {
        if (!prefetchEnabled) {
            return;
        }

        var warmup = function() {
            rows
                .filter(function(row) { return !row.hidden; })
                .slice(0, idlePrefetchLimit)
                .forEach(function(row) {
                    warmStudentRow(row);
                });
        };

        if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(warmup, { timeout: 1200 });
            return;
        }

        window.setTimeout(warmup, 300);
    }

    function updateCount(visibleCount) {
        if (!countNode) {
            return;
        }
        countNode.textContent = visibleCount + ' alunos';
    }

    function syncEmptyState(visibleCount) {
        if (!emptyState) {
            return;
        }
        emptyState.parentElement.hidden = visibleCount !== 0;
    }

    function getPresenceValue(row) {
        return Number(row.getAttribute('data-presence-percent') || '0');
    }

    function normalizeSearchText(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    function getRowSearchIndex(row) {
        var cachedIndex = row.getAttribute('data-search-normalized');
        if (cachedIndex) {
            return cachedIndex;
        }

        var rawIndex = row.getAttribute('data-search-index')
            || row.getAttribute('data-student-name')
            || row.innerText
            || '';
        var normalizedIndex = normalizeSearchText(rawIndex);
        row.setAttribute('data-search-normalized', normalizedIndex);
        return normalizedIndex;
    }

    function getAvatarTone(studentId) {
        var tones = ['orange', 'blue', 'purple', 'teal', 'pink', 'indigo'];
        var index = Number(studentId || 0) % tones.length;
        return tones[index];
    }

    function formatDueShortLabel(value) {
        if (!value) {
            return '--';
        }

        var normalizedValue = String(value || '');
        if (/^\d{4}-\d{2}-\d{2}$/.test(normalizedValue)) {
            var isoParts = normalizedValue.split('-');
            return isoParts[2] + ' ' + ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][Number(isoParts[1]) - 1];
        }

        if (/^\d{2}\/\d{2}\/\d{4}$/.test(normalizedValue)) {
            var brParts = normalizedValue.split('/');
            return brParts[0] + ' ' + ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][Number(brParts[1]) - 1];
        }

        return normalizedValue;
    }

    function buildDirectorySearchIndexEntry(entry) {
        return {
            id: Number(entry.id || 0),
            full_name: entry.full_name || '',
            email: entry.email || '',
            phone: entry.phone || '',
            status: entry.status || '',
            latest_plan_name: entry.latest_plan_name || '',
            payment_status: entry.payment_status || '',
            presence_percent: Number(entry.presence_percent || 0),
            due_label: entry.due_label || '',
            href: entry.href || '',
            snapshot_url: entry.snapshot_url || '',
            events_stream_url: entry.events_stream_url || '',
            drawer_fragments_url: entry.drawer_fragments_url || '',
            drawer_profile_url: entry.drawer_profile_url || '',
            edit_start_url: entry.edit_start_url || '',
            edit_release_url: entry.edit_release_url || '',
            lock_heartbeat_url: entry.lock_heartbeat_url || '',
            lock_status_url: entry.lock_status_url || '',
        };
    }

    function buildDirectoryRowMarkup(entry) {
        var student = buildDirectorySearchIndexEntry(entry);
        var contact = student.email || student.phone || '';
        var signalMarkup = '';
        if (student.presence_percent >= 85) {
            signalMarkup += '<span class="student-signal student-signal--success" data-student-signal="frequency">Alta frequencia</span>';
        }
        if (student.presence_percent < 45) {
            signalMarkup += '<span class="student-signal student-signal--warning" data-student-signal="training">Baixo treino</span>';
        }
        if (student.payment_status === 'overdue' || student.payment_status === 'pending') {
            signalMarkup += '<span class="student-signal student-signal--danger" data-student-signal="financial">Risco financeiro</span>';
        }

        var statusMarkup = '<div class="student-status-pill student-status-pill--blue">Lead</div>';
        if (student.status === 'active') {
            statusMarkup = '<div class="student-status-pill student-status-pill--green">Ativo</div>';
        } else if (student.status === 'inactive') {
            statusMarkup = '<div class="student-status-pill student-status-pill--gray">Inativo</div>';
        } else if (student.status === 'paused') {
            statusMarkup = '<div class="student-status-pill student-status-pill--orange">Pausado</div>';
        }

        var paymentMarkup = '<span class="student-payment-state student-payment-state--gray">Cancelado</span>';
        if (student.payment_status === 'overdue') {
            paymentMarkup = '<span class="student-payment-state student-payment-state--red">Atrasado</span>';
        } else if (student.payment_status === 'pending') {
            paymentMarkup = '<span class="student-payment-state student-payment-state--orange">Pendente</span>';
        } else if (student.payment_status === 'paid') {
            paymentMarkup = '<span class="student-payment-state student-payment-state--green">Em dia</span>';
        }

        return '' +
            '<td class="student-cell student-cell--student" data-label="Aluno">' +
                '<div class="student-identity">' +
                    '<div class="avatar-circle avatar-' + escapeHtml(getAvatarTone(student.id)) + ' student-avatar-circle">' + escapeHtml(getInitials(student.full_name)) + '</div>' +
                    '<div class="student-identity-copy">' +
                        '<strong class="student-name">' + escapeHtml(student.full_name) + '</strong>' +
                        '<span class="student-email">' + escapeHtml(contact) + '</span>' +
                        '<div class="student-signal-strip" data-student-signal-strip>' + signalMarkup + '</div>' +
                        '<span class="visually-hidden">Pressione Enter para abrir a ficha.</span>' +
                    '</div>' +
                '</div>' +
            '</td>' +
            '<td class="student-cell" data-label="Plano"><span class="student-plan-name">' + escapeHtml(student.latest_plan_name || '--') + '</span></td>' +
            '<td class="student-cell" data-label="Status">' + statusMarkup + '</td>' +
            '<td class="student-cell student-cell--presence" data-label="Presenca"><span class="student-presence-value ' + (student.presence_percent >= 85 ? 'is-high' : student.presence_percent >= 60 ? 'is-mid' : 'is-low') + '">' + escapeHtml(String(student.presence_percent)) + '%</span></td>' +
            '<td class="student-cell" data-label="Pagamento">' + paymentMarkup + '</td>' +
            '<td class="student-cell student-cell--due-date" data-label="Vencimento"><span class="student-due-date">' + escapeHtml(formatDueShortLabel(student.due_label)) + '</span></td>';
    }

    function buildDirectoryRowFromIndex(entry) {
        var student = buildDirectorySearchIndexEntry(entry);
        var row = document.createElement('tr');
        row.className = 'student-row hover:bg-muted-soft cursor-pointer transition-all';
        row.setAttribute('data-student-row', '');
        row.setAttribute('data-href', student.href);
        row.setAttribute('data-student-snapshot-url', student.snapshot_url);
        row.setAttribute('data-student-events-stream-url', student.events_stream_url);
        row.setAttribute('data-student-drawer-fragments-url', student.drawer_fragments_url);
        row.setAttribute('data-student-drawer-profile-url', student.drawer_profile_url);
        row.setAttribute('data-student-edit-start-url', student.edit_start_url);
        row.setAttribute('data-student-edit-release-url', student.edit_release_url);
        row.setAttribute('data-student-lock-heartbeat-url', student.lock_heartbeat_url);
        row.setAttribute('data-student-lock-status-url', student.lock_status_url);
        row.setAttribute('data-student-id', String(student.id));
        row.setAttribute('data-student-name', student.full_name);
        row.setAttribute('data-student-contact', student.email || student.phone || '');
        row.setAttribute('data-student-plan', student.latest_plan_name || '');
        row.setAttribute('data-student-due-label', student.due_label || '');
        row.setAttribute('data-student-status', student.status || '');
        row.setAttribute('data-payment-status', student.payment_status || '');
        row.setAttribute('data-presence-percent', String(student.presence_percent || 0));
        row.setAttribute('data-search-index', (student.full_name + ' ' + (student.email || student.phone || '') + ' ' + (student.latest_plan_name || '--')).toLowerCase());
        row.setAttribute('tabindex', '0');
        row.setAttribute('role', 'link');
        row.setAttribute('aria-label', 'Abrir ficha de ' + student.full_name);
        row.innerHTML = buildDirectoryRowMarkup(student);
        return row;
    }

    function restoreServerRows() {
        if (!tbody) {
            return;
        }

        tbody.replaceChildren();
        serverRows.forEach(function(row) {
            tbody.appendChild(row);
        });
        rows = serverRows.slice();
        directorySearchState.isUsingSearchIndex = false;
        setDirectoryFooterVisibility(true);
    }

    function renderDirectorySearchRows() {
        var searchIndex = getDirectorySearchIndex().map(buildDirectorySearchIndexEntry);
        var filteredEntries = searchIndex.filter(function(entry) {
            var paymentStatus = entry.payment_status || '';
            var studentStatus = entry.status || '';
            var searchIndexValue = normalizeSearchText(entry.full_name + ' ' + (entry.email || entry.phone || '') + ' ' + (entry.latest_plan_name || '--'));
            var matchesQuery = !filterState.searchQuery || searchIndexValue.indexOf(filterState.searchQuery) !== -1;
            if (!matchesQuery) {
                return false;
            }

            if (filterState.filter === 'all') {
                return true;
            }
            if (filterState.filter === 'overdue') {
                return paymentStatus === 'overdue';
            }
            return studentStatus === filterState.filter;
        });

        if (filterState.sortBy === 'presence') {
            filteredEntries.sort(function(left, right) {
                var compare = Number(left.presence_percent || 0) - Number(right.presence_percent || 0);
                if (filterState.sortDirection === 'desc') {
                    compare *= -1;
                }
                if (compare !== 0) {
                    return compare;
                }
                return String(left.full_name || '').localeCompare(String(right.full_name || ''), 'pt-BR');
            });
        }

        tbody.replaceChildren();
        if (!filteredEntries.length) {
            var emptyRow = document.createElement('tr');
            emptyRow.innerHTML = '<td colspan="6" class="table-empty-cell p-10 text-center text-dimmed text-sm" data-student-empty-state>Nenhum aluno encontrado para este filtro.</td>';
            tbody.appendChild(emptyRow);
            rows = [];
            updateCount(0);
        } else {
            var renderedRows = filteredEntries.map(function(entry) {
                var row = buildDirectoryRowFromIndex(entry);
                bindRowInteractions(row);
                tbody.appendChild(row);
                return row;
            });
            rows = renderedRows;
            updateCount(renderedRows.length);
        }

        directorySearchState.isUsingSearchIndex = true;
        setDirectoryFooterVisibility(false);
    }

    function submitDirectorySearchForm() {
        if (!filterForm) {
            return;
        }

        if (searchSubmitTimerId) {
            window.clearTimeout(searchSubmitTimerId);
            searchSubmitTimerId = null;
        }

        if (typeof filterForm.requestSubmit === 'function') {
            filterForm.requestSubmit();
            return;
        }

        filterForm.submit();
    }

    function scheduleDirectorySearchSubmit() {
        if (!filterForm || !searchInput) {
            return;
        }

        var nextQuery = normalizeSearchText(searchInput.value);
        var currentQuery = normalizeSearchText(searchInput.defaultValue || '');
        if (nextQuery === currentQuery) {
            return;
        }

        if (searchSubmitTimerId) {
            window.clearTimeout(searchSubmitTimerId);
        }

        searchSubmitTimerId = window.setTimeout(function() {
            submitDirectorySearchForm();
        }, 280);
    }

    function bindRowInteractions(row) {
        if (!row) {
            return;
        }

        var studentId = row.getAttribute('data-student-id');

        function openRowTarget() {
            var cachedSnapshot = studentId ? getCachedSnapshot(studentId) : null;
            openQuickPanelForRow(row, cachedSnapshot);

            if (!cachedSnapshot) {
                fetchSnapshotForRow(row);
            }
        }

        row.addEventListener('mouseenter', function() {
            scheduleRowWarmup(row);
        });

        row.addEventListener('focus', function() {
            warmStudentRow(row);
        });

        row.addEventListener('touchstart', function() {
            warmStudentRow(row);
        }, { passive: true });

        row.addEventListener('mouseleave', function() {
            cancelRowWarmup(row);
        });

        row.addEventListener('click', function(event) {
            if (event.target.closest('[data-row-ignore-click], a, button, input, select, textarea, label')) {
                return;
            }

            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                markNavigationHint(row);
                window.open(row.getAttribute('data-href'), '_blank', 'noopener');
                return;
            }

            openRowTarget();
        });

        row.addEventListener('keydown', function(event) {
            if (event.target.closest('[data-row-ignore-click], a, button, input, select, textarea, label')) {
                return;
            }

            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }

            event.preventDefault();
            openRowTarget();
        });
    }

    function sortRowsIfNeeded(visibleRows) {
        if (!tbody) {
            return;
        }

        visibleRows.sort(function(a, b) {
            if (filterState.sortBy === 'presence') {
                var leftValue = getPresenceValue(a);
                var rightValue = getPresenceValue(b);
                var compare = leftValue - rightValue;

                if (filterState.sortDirection === 'desc') {
                    compare *= -1;
                }

                if (compare !== 0) {
                    return compare;
                }
            }

            var leftName = String(a.getAttribute('data-student-name') || a.innerText || '');
            var rightName = String(b.getAttribute('data-student-name') || b.innerText || '');
            return leftName.localeCompare(rightName, 'pt-BR');
        });

        visibleRows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }

    function matchesSearch(row) {
        if (!filterState.searchQuery) {
            return true;
        }

        return getRowSearchIndex(row).indexOf(filterState.searchQuery) !== -1;
    }

    function matchesFilter(row) {
        if (filterState.filter === 'all') {
            return true;
        }

        if (filterState.filter === 'overdue') {
            return row.getAttribute('data-payment-status') === 'overdue';
        }

        return row.getAttribute('data-student-status') === filterState.filter;
    }

    function applyLocalDirectoryState() {
        setDirectoryFooterVisibility(!filterState.searchQuery);

        if (filterState.searchQuery) {
            if (isDirectorySearchStale()) {
                scheduleDirectorySearchSubmit();
                return;
            }

            if (getDirectorySearchIndex().length) {
                renderDirectorySearchRows();
                return;
            }
        }

        if (directorySearchState.isUsingSearchIndex) {
            restoreServerRows();
        }

        var visibleRows = [];

        rows.forEach(function(row) {
            var isVisible = matchesFilter(row) && matchesSearch(row);
            row.hidden = !isVisible;
            if (isVisible) {
                visibleRows.push(row);
            }
        });

        sortRowsIfNeeded(visibleRows);
        updateCount(visibleRows.length);
        syncEmptyState(visibleRows.length);
    }

    function syncPills() {
        pills.forEach(function(pill) {
            var isPresence = pill.hasAttribute('data-student-sort');
            var isActive = false;

            if (isPresence) {
                isActive = filterState.sortBy === 'presence';
                pill.textContent = 'Presença ' + (filterState.sortDirection === 'asc' ? '↑' : '↓');
            } else {
                isActive = (pill.getAttribute('data-student-filter') || 'all') === filterState.filter;
            }

            pill.classList.toggle('is-active', isActive);
            pill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });
    }

    if (filterForm && searchInput) {
        filterForm.addEventListener('submit', function(event) {
            if (searchSubmitTimerId) {
                window.clearTimeout(searchSubmitTimerId);
                searchSubmitTimerId = null;
            }
        });

        searchInput.addEventListener('input', function() {
            filterState.searchQuery = normalizeSearchText(searchInput.value);
            if (!filterState.searchQuery && directorySearchState.isUsingSearchIndex) {
                restoreServerRows();
            }
            applyLocalDirectoryState();
        });

        filterState.searchQuery = normalizeSearchText(searchInput.value);
    }

    if (currentSearchParams.get('payment_status') === 'overdue') {
        filterState.filter = 'overdue';
    } else if (currentSearchParams.get('student_status') === 'inactive') {
        filterState.filter = 'inactive';
    } else if (currentSearchParams.get('student_status') === 'active') {
        filterState.filter = 'active';
    }

    pills.forEach(function(pill) {
        pill.addEventListener('click', function() {
            if (pill.hasAttribute('data-student-sort')) {
                if (filterState.sortBy === 'presence') {
                    filterState.sortDirection = filterState.sortDirection === 'desc' ? 'asc' : 'desc';
                } else {
                    filterState.sortBy = 'presence';
                    filterState.sortDirection = pill.getAttribute('data-sort-direction') || 'desc';
                }
            } else {
                var nextFilter = pill.getAttribute('data-student-filter') || 'all';
                if (filterState.filter === nextFilter && filterState.sortBy === 'presence') {
                    filterState.sortBy = '';
                    filterState.sortDirection = 'desc';
                    filterState.filter = nextFilter;
                    syncPills();
                    applyLocalDirectoryState();
                    return;
                }
                if (hasServerScopedFilters()) {
                    window.location.assign(buildDirectoryFilterUrl(nextFilter));
                    return;
                }
                filterState.filter = nextFilter;
            }

            syncPills();
            applyLocalDirectoryState();
        });
    });

    rows.forEach(bindRowInteractions);

    if (quickClose) {
        quickClose.addEventListener('click', function() {
            closeQuickPanel();
        });
    }

    if (quickOverlay) {
        quickOverlay.addEventListener('click', function() {
            closeQuickPanel();
        });
    }

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeQuickPanel();
        }
    });

    quickTabButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            var nextTab = button.getAttribute('data-student-quick-tab');
            activateQuickPanelTab(nextTab);

            if (!quickPanelState.isOpen) {
                return;
            }

            ensureQuickPanelTabContent(nextTab);

            if (quickPanelState.fragmentsLoaded[nextTab] && !quickPanelState.editSessionActive) {
                refreshQuickPanelReadState({ forceFragments: true });
            }
        });
    });

    if (quickPanel) {
        quickPanel.addEventListener('click', function(event) {
            var fullRecordRow = event.target.closest('[data-student-quick-open-full-record]');
            if (fullRecordRow) {
                event.preventDefault();
                openQuickPanelFullRecord({
                    newTab: event.metaKey || event.ctrlKey,
                });
                return;
            }

            var quickFinancialOpen = event.target.closest('[data-quick-financial-open]');
            if (quickFinancialOpen) {
                event.preventDefault();
                openQuickFinancialDrawer(quickFinancialOpen.getAttribute('data-quick-financial-open'));
                activateQuickPanelTab('financial');
                return;
            }

            var quickFinancialClose = event.target.closest('[data-quick-financial-close]');
            if (quickFinancialClose) {
                event.preventDefault();
                closeQuickFinancialDrawers();
                return;
            }

            var toggleEditButton = event.target.closest('[data-action="toggle-student-profile-edit"]');
            if (toggleEditButton) {
                event.preventDefault();
                var profileForm = quickPanel.querySelector('[data-student-quick-profile-slot] [data-student-profile-form]');
                if (!profileForm) {
                    return;
                }

                if (profileForm.classList.contains('is-readonly')) {
                    startDrawerEditSession();
                } else {
                    stopDrawerEditSession();
                }
                return;
            }

            var openDrawerTrigger = event.target.closest('[data-action="open-drawer"]');
            if (openDrawerTrigger) {
                event.preventDefault();
                var drawerId = openDrawerTrigger.getAttribute('data-drawer-id') || '';
                if (drawerId.indexOf('checkout') !== -1) {
                    openQuickFinancialDrawer('checkout');
                } else if (drawerId.indexOf('management') !== -1) {
                    openQuickFinancialDrawer('management');
                } else if (drawerId.indexOf('enrollment') !== -1) {
                    openQuickFinancialDrawer('enrollment');
                }
                activateQuickPanelTab('financial');
                return;
            }

            var closeDrawerTrigger = event.target.closest('[data-action="close-drawers"]');
            if (closeDrawerTrigger) {
                event.preventDefault();
                closeQuickFinancialDrawers();
                return;
            }

            var submitPaymentTrigger = event.target.closest('[data-action="submit-stripe"]');
            if (submitPaymentTrigger) {
                event.preventDefault();
                var methodValue = submitPaymentTrigger.getAttribute('data-method');
                var checkoutForm = quickPanel.querySelector('#student-payment-checkout-form');
                var methodField = quickPanel.querySelector('#student-payment-checkout-form [name="method"]');

                if (!checkoutForm || !methodValue) {
                    return;
                }

                askQuickConfirmation('Voce realmente quer fazer o pagamento com ' + getQuickPaymentMethodLabel(methodValue) + '?').then(function(confirmed) {
                    if (!confirmed) {
                        return;
                    }

                    if (methodField) {
                        methodField.value = methodValue;
                    }

                    quickPanel.querySelectorAll('.student-payment-method-button').forEach(function(button) {
                        button.classList.add('is-disabled');
                        button.classList.remove('is-active');
                        button.setAttribute('aria-disabled', 'true');
                    });

                    submitPaymentTrigger.classList.remove('is-disabled');
                    submitPaymentTrigger.classList.add('is-active');
                    submitPaymentTrigger.removeAttribute('aria-disabled');
                    submitQuickFinancialForm(checkoutForm);
                });
                return;
            }

            var editPaymentTrigger = event.target.closest('[data-action="edit-payment"]');
            if (editPaymentTrigger) {
                event.preventDefault();
                loadQuickPaymentIntoDrawer(editPaymentTrigger.getAttribute('data-payment-id'), editPaymentTrigger);
                activateQuickPanelTab('financial');
                return;
            }
        });

        quickPanel.addEventListener('submit', function(event) {
            var profileForm = event.target.closest('[data-student-profile-form]');
            if (profileForm) {
                event.preventDefault();
                submitDrawerProfileForm(profileForm);
                return;
            }

            var financialForm = event.target.closest('#student-payment-checkout-form, .student-enrollment-management-form');
            if (financialForm) {
                event.preventDefault();
                var confirmTrigger = event.submitter;
                if (confirmTrigger && confirmTrigger.getAttribute('data-confirm') === 'true') {
                    askQuickConfirmation(confirmTrigger.getAttribute('data-confirm-message') || 'Tem certeza que deseja continuar com esta acao?').then(function(confirmed) {
                        if (!confirmed) {
                            return;
                        }
                        submitQuickFinancialForm(financialForm);
                    });
                    return;
                }

                submitQuickFinancialForm(financialForm);
            }
        });
    }

    if (quickPanel) {
        quickPanel.addEventListener('keydown', function(event) {
            var fullRecordRow = event.target.closest('[data-student-quick-open-full-record]');
            if (!fullRecordRow) {
                return;
            }

            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }

            event.preventDefault();
            openQuickPanelFullRecord({
                newTab: event.metaKey || event.ctrlKey,
            });
        });
    }

    window.addEventListener('popstate', function() {
        if (!quickPanelState.isOpen) {
            return;
        }

        if (String(window.location.hash || '').indexOf('#student-') !== 0) {
            closeQuickPanel({ skipHistory: true });
        }
    });

    document.addEventListener('visibilitychange', function() {
        if (!quickPanelState.isOpen || document.hidden) {
            return;
        }

        if (quickPanelState.editSessionActive) {
            heartbeatDrawerEditSession();
            return;
        }

        refreshQuickPanelReadState({
            forceFragments: true,
        });
    });

    window.addEventListener('focus', function() {
        if (!quickPanelState.isOpen) {
            return;
        }

        if (quickPanelState.editSessionActive) {
            heartbeatDrawerEditSession();
            return;
        }

        refreshQuickPanelReadState({
            forceFragments: true,
        });
    });

    if (Array.isArray(directorySearchConfig.index) && directorySearchConfig.index.length) {
        persistDirectorySearchIndex(directorySearchConfig.index);
    } else {
        directorySearchState.index = getDirectorySearchIndexFromCache();
    }

    syncPills();
    applyLocalDirectoryState();
    prefetchInitialRows();
});
        function getQuickPaymentMethodLabel(methodValue) {
            if (methodValue === 'pix') return 'Pix';
            if (methodValue === 'credit_card') return 'Credito';
            if (methodValue === 'debit_card') return 'Debito';
            if (methodValue === 'cash') return 'Dinheiro';
            return 'este metodo';
        }
