(function() {
    function supportsSessionStorage() {
        try {
            return typeof window.sessionStorage !== 'undefined';
        } catch (error) {
            return false;
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

    function writeSessionJson(key, value) {
        if (!supportsSessionStorage()) {
            return;
        }

        try {
            window.sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            // Degradacao silenciosa se o storage estiver indisponivel.
        }
    }

    function normalizeSearchText(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    function isListAllSearchCommand(value) {
        return String(value || '').trim() === '/';
    }

    var payloadElement = document.getElementById('current-page-behavior');
    var pageBehavior = {};
    if (payloadElement) {
        try {
            pageBehavior = JSON.parse(payloadElement.textContent || '{}');
        } catch (error) {
            pageBehavior = {};
        }
    }

    var pageRoot = document.querySelector('[data-page="intake-center"]');
    if (!pageRoot) {
        return;
    }

    var queueBoard = pageRoot.querySelector('#intake-queue-board');
    var tbody = queueBoard ? queueBoard.querySelector('tbody') : null;
    var filterForm = pageRoot.querySelector('#intake-directory-filter-form');
    var searchInput = filterForm ? filterForm.querySelector('input[name="query"]') : null;
    var countNode = pageRoot.querySelector('.intake-queue-filter-count');
    var filterPills = Array.prototype.slice.call(pageRoot.querySelectorAll('[data-intake-filter]'));
    var sortPill = pageRoot.querySelector('[data-intake-sort="registration"]');
    var devPanel = pageRoot.querySelector('[data-intake-search-dev-panel]');
    var emptySearchRow = tbody ? tbody.querySelector('[data-intake-empty-search-row]') : null;
    var emptySearchMessage = emptySearchRow ? emptySearchRow.querySelector('td') : null;
    var intakeKpiCards = Array.prototype.slice.call(pageRoot.querySelectorAll('[data-slot="intake-interactive-kpi-card"]'));
    var intakeSearchConfig = pageBehavior.intake_search || {};
    var initialServerFilterKey = getActiveServerFilterKey();

    if (!queueBoard || !tbody || !filterForm || !searchInput || !sortPill) {
        return;
    }

    var serverRows = Array.prototype.slice.call(tbody.querySelectorAll('.intake-directory-row'));
    var intakeSearchCacheKey = 'octobox.intake.queue.search-index.v1.' + String(intakeSearchConfig.cache_key || 'all');
    var searchState = {
        query: '',
        listAllCommand: false,
        filterKey: '',
        sortBy: null,
        sortDirection: sortPill.getAttribute('data-sort-direction') || 'desc',
        index: [],
        isUsingSearchIndex: false,
        hasNext: Boolean(intakeSearchConfig.has_next),
        nextOffset: intakeSearchConfig.next_offset || null,
        total: Number(intakeSearchConfig.total || 0),
        isLoadingNext: false,
        isHydratingFilters: false,
        idleHydrationScheduled: false,
        idleHydrationCompleted: false,
    };
    var localZeroKpiState = {
        key: '',
        label: '',
    };
    var defaultEmptyMessage = emptySearchMessage ? emptySearchMessage.textContent : '';
    var performanceTelemetry = {
        idleHydrationScheduled: 0,
        idleHydrationStarted: 0,
        idleHydrationCompleted: 0,
        idleHydrationSkipped: 0,
        idleHydrationDurationMs: [],
        clickWaitsForHydration: 0,
        clickWaitDurationMs: [],
        manualNextPageLoads: 0,
        totalIndexEntries: Number(intakeSearchConfig.index && intakeSearchConfig.index.length ? intakeSearchConfig.index.length : 0),
        latestTotalEntries: Number(intakeSearchConfig.index && intakeSearchConfig.index.length ? intakeSearchConfig.index.length : 0),
    };

    window.__octoboxIntakeSearchTelemetry = performanceTelemetry;

    function getLastPerformanceSample(list) {
        if (!Array.isArray(list) || !list.length) {
            return 0;
        }
        return list[list.length - 1] || 0;
    }

    function syncDevPanel() {
        if (!devPanel) {
            return;
        }

        function writeMetric(name, value) {
            var node = devPanel.querySelector('[data-intake-search-metric="' + name + '"]');
            if (node) {
                node.textContent = String(value);
            }
        }

        writeMetric('entries', performanceTelemetry.latestTotalEntries);
        writeMetric('click-waits', performanceTelemetry.clickWaitsForHydration);
        writeMetric('idle-completed', performanceTelemetry.idleHydrationCompleted);
        writeMetric('idle-last-ms', getLastPerformanceSample(performanceTelemetry.idleHydrationDurationMs) + ' ms');
        writeMetric('click-last-ms', getLastPerformanceSample(performanceTelemetry.clickWaitDurationMs) + ' ms');
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

        window.console.debug('[OctoBox][Intake][SearchTelemetry]', eventName, data || {});
    }

    function setSearchStateFromInputValue(value) {
        searchState.listAllCommand = isListAllSearchCommand(value);
        searchState.query = searchState.listAllCommand ? '' : normalizeSearchText(value);
        if (searchState.listAllCommand) {
            searchState.sortBy = null;
            searchState.sortDirection = sortPill.getAttribute('data-sort-direction') || 'desc';
        }
    }

    function clearLocalZeroKpiState() {
        localZeroKpiState.key = '';
        localZeroKpiState.label = '';
    }

    function getActiveServerFilterKey() {
        var params = new URLSearchParams(window.location.search || '');
        if (params.get('semantic_stage') === 'new-leads' || params.get('status') === 'new') {
            return 'new-leads';
        }
        return '';
    }

    function buildCurrentServerIndex() {
        return serverRows.map(function(row) {
            var nameNode = row.querySelector('.intake-contact-name');
            return {
                id: Number(row.getAttribute('data-intake-id') || 0),
                full_name: nameNode ? nameNode.textContent.trim() : '',
                registration_age_days: Number(row.getAttribute('data-registration-age-days') || '0'),
                semantic_stage: row.getAttribute('data-semantic-stage') || '',
                created_today: row.getAttribute('data-created-today') === 'true',
                assigned: row.getAttribute('data-assigned') === 'true',
                row_html: row.outerHTML,
            };
        });
    }

    function persistSearchIndex(index, meta) {
        var normalizedIndex = Array.isArray(index) ? index : [];
        var resolvedMeta = meta || {};
        searchState.index = normalizedIndex;
        searchState.hasNext = typeof resolvedMeta.has_next === 'boolean' ? resolvedMeta.has_next : Boolean(searchState.hasNext);
        searchState.nextOffset = Object.prototype.hasOwnProperty.call(resolvedMeta, 'next_offset') ? resolvedMeta.next_offset : searchState.nextOffset;
        searchState.total = Number(resolvedMeta.total || searchState.total || normalizedIndex.length);
        performanceTelemetry.latestTotalEntries = normalizedIndex.length;
        performanceTelemetry.totalIndexEntries = Math.max(performanceTelemetry.totalIndexEntries, normalizedIndex.length);
        writeSessionJson(intakeSearchCacheKey, {
            index: normalizedIndex,
            refresh_token: intakeSearchConfig.refresh_token || '',
            has_next: searchState.hasNext,
            next_offset: searchState.nextOffset,
            total: searchState.total,
            saved_at: Date.now(),
        });
        syncDevPanel();
    }

    function getSearchIndexFromCache() {
        var cacheEntry = readSessionJson(intakeSearchCacheKey);
        if (!cacheEntry || !Array.isArray(cacheEntry.index)) {
            return [];
        }

        if ((cacheEntry.refresh_token || '') !== String(intakeSearchConfig.refresh_token || '')) {
            return [];
        }

        searchState.hasNext = Object.prototype.hasOwnProperty.call(cacheEntry, 'has_next') ? Boolean(cacheEntry.has_next) : Boolean(intakeSearchConfig.has_next);
        searchState.nextOffset = Object.prototype.hasOwnProperty.call(cacheEntry, 'next_offset') ? cacheEntry.next_offset : (intakeSearchConfig.next_offset || null);
        searchState.total = Number(cacheEntry.total || intakeSearchConfig.total || cacheEntry.index.length || 0);
        return cacheEntry.index;
    }

    function getSearchIndex() {
        if (searchState.index.length) {
            return searchState.index;
        }

        var cachedIndex = getSearchIndexFromCache();
        if (cachedIndex.length) {
            searchState.index = cachedIndex;
            return cachedIndex;
        }

        if (Array.isArray(intakeSearchConfig.index) && intakeSearchConfig.index.length) {
            persistSearchIndex(intakeSearchConfig.index, {
                has_next: Boolean(intakeSearchConfig.has_next),
                next_offset: intakeSearchConfig.next_offset || null,
                total: Number(intakeSearchConfig.total || intakeSearchConfig.index.length || 0),
            });
            return searchState.index;
        }

        var fallbackIndex = buildCurrentServerIndex();
        persistSearchIndex(fallbackIndex, {
            has_next: false,
            next_offset: null,
            total: fallbackIndex.length,
        });
        return searchState.index;
    }

    function buildNextSearchPageUrl() {
        if (!intakeSearchConfig.page_url || searchState.nextOffset === null || searchState.nextOffset === undefined) {
            return '';
        }

        var url = new URL(intakeSearchConfig.page_url, window.location.origin);
        var params = new URLSearchParams(window.location.search || '');
        params.delete('query');
        params.delete('panel');
        params.delete('offset');
        params.delete('status');
        params.delete('semantic_stage');
        params.delete('created_window');
        params.delete('assignment');
        params.forEach(function(value, key) {
            url.searchParams.append(key, value);
        });
        url.searchParams.set('offset', String(searchState.nextOffset));
        return url.toString();
    }

    function mergeSearchIndexPage(pageEntries) {
        var seenIds = new Set();
        var mergedEntries = [];

        getSearchIndex().concat(Array.isArray(pageEntries) ? pageEntries : []).forEach(function(entry) {
            var entryId = String(entry && entry.id ? entry.id : '');
            if (!entryId || seenIds.has(entryId)) {
                return;
            }
            seenIds.add(entryId);
            mergedEntries.push(entry);
        });

        return mergedEntries;
    }

    function loadNextSearchPage() {
        var nextUrl = buildNextSearchPageUrl();
        if (!nextUrl || searchState.isLoadingNext || !searchState.hasNext) {
            return Promise.resolve(false);
        }

        searchState.isLoadingNext = true;
        return fetch(nextUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Falha ao carregar proxima pagina de entradas.');
                }
                return response.json();
            })
            .then(function(payload) {
                var nextIndex = mergeSearchIndexPage(payload.index || []);
                if (String(payload.refresh_token || '') !== String(intakeSearchConfig.refresh_token || '')) {
                    nextIndex = Array.isArray(payload.index) ? payload.index : [];
                    intakeSearchConfig.refresh_token = payload.refresh_token || '';
                }
                persistSearchIndex(nextIndex, {
                    has_next: Boolean(payload.has_next),
                    next_offset: payload.next_offset || null,
                    total: Number(payload.total || nextIndex.length || 0),
                });
                return true;
            })
            .catch(function() {
                return false;
            })
            .finally(function() {
                searchState.isLoadingNext = false;
            });
    }

    function hydrateSearchIndexForLocalFilters() {
        if (!searchState.hasNext || searchState.isHydratingFilters) {
            return Promise.resolve(false);
        }

        searchState.isHydratingFilters = true;
        return (function loadRemainingPages() {
            if (!searchState.hasNext) {
                return Promise.resolve(true);
            }
            return loadNextSearchPage().then(function(didLoadPage) {
                if (!didLoadPage) {
                    return false;
                }
                return loadRemainingPages();
            });
        })().finally(function() {
            searchState.isHydratingFilters = false;
            if (!searchState.hasNext) {
                searchState.idleHydrationCompleted = true;
            }
        });
    }

    function shouldHydrateIntakeIndexInIdle() {
        return searchState.hasNext
            && !searchState.isHydratingFilters
            && !searchState.idleHydrationCompleted
            && !document.hidden;
    }

    function scheduleIdleIntakeHydration() {
        if (searchState.idleHydrationScheduled || !shouldHydrateIntakeIndexInIdle()) {
            performanceTelemetry.idleHydrationSkipped += 1;
            return;
        }

        searchState.idleHydrationScheduled = true;
        performanceTelemetry.idleHydrationScheduled += 1;
        logPerformanceTelemetry('idle-scheduled', {
            next_offset: searchState.nextOffset,
            loaded_entries: searchState.index.length,
        });

        function runIdleHydration() {
            searchState.idleHydrationScheduled = false;
            if (!shouldHydrateIntakeIndexInIdle()) {
                performanceTelemetry.idleHydrationSkipped += 1;
                return;
            }
            performanceTelemetry.idleHydrationStarted += 1;
            var startedAt = performance.now();
            hydrateSearchIndexForLocalFilters().then(function(didHydrate) {
                var durationMs = performance.now() - startedAt;
                recordPerformanceSample(performanceTelemetry.idleHydrationDurationMs, durationMs);
                if (didHydrate) {
                    performanceTelemetry.idleHydrationCompleted += 1;
                }
                syncDevPanel();
                logPerformanceTelemetry('idle-finished', {
                    hydrated: Boolean(didHydrate),
                    duration_ms: Math.round(durationMs),
                    loaded_entries: searchState.index.length,
                    has_next: searchState.hasNext,
                });
                if (didHydrate && searchState.isUsingSearchIndex) {
                    applyLocalQueueState();
                }
            });
        }

        if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(runIdleHydration, { timeout: 1500 });
            return;
        }

        window.setTimeout(runIdleHydration, 600);
    }

    function getRegistrationAgeValue(entry) {
        var parsedValue = Number(entry.registration_age_days || 0);
        return Number.isNaN(parsedValue) ? 0 : parsedValue;
    }

    function updateCount(visibleCount) {
        if (!countNode) {
            return;
        }

        countNode.textContent = visibleCount === 1 ? '1 entrada' : visibleCount + ' entradas';
        countNode.setAttribute('aria-label', 'Fila: ' + visibleCount + '.');
    }

    function syncEmptyState(visibleCount) {
        if (!emptySearchRow) {
            return;
        }

        if (emptySearchMessage) {
            emptySearchMessage.textContent = localZeroKpiState.key
                ? 'Nenhuma entrada combina com o KPI ' + localZeroKpiState.label + ' no momento.'
                : defaultEmptyMessage;
        }

        emptySearchRow.hidden = visibleCount !== 0 || (!localZeroKpiState.key && !searchState.query && !searchState.listAllCommand && !searchState.filterKey);
    }

    function syncSortPill() {
        var isActive = searchState.sortBy === 'registration';
        sortPill.textContent = 'Data ' + (searchState.sortDirection === 'asc' ? '\u2191' : '\u2193');
        sortPill.classList.toggle('is-active', isActive);
        sortPill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    }

    function syncFilterPills() {
        var activeFilterKey = searchState.filterKey || (!searchState.isUsingSearchIndex ? initialServerFilterKey : '');
        filterPills.forEach(function(pill) {
            var pillFilter = pill.getAttribute('data-intake-filter') || 'all';
            var isActive = pillFilter === 'all'
                ? !activeFilterKey
                : activeFilterKey === pillFilter;
            pill.classList.toggle('is-active', isActive);
            pill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });
    }

    function activateIntakePanel(panelId) {
        if (!panelId) {
            return;
        }

        var targetPanel = document.getElementById(panelId);
        if (!targetPanel) {
            return;
        }

        var container = targetPanel.closest('.interactive-tab-container');
        if (container) {
            Array.prototype.slice.call(container.children).forEach(function(child) {
                child.classList.remove('is-tab-active');
            });
        }

        targetPanel.classList.add('is-tab-active');
    }

    function syncIntakeKpiCards(selectedCard) {
        intakeKpiCards.forEach(function(card) {
            var isSelected = card === selectedCard;
            card.classList.toggle('is-selected-tab', isSelected);
            card.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
        });
    }

    function getKpiDisplayValue(card) {
        return Number(card ? (card.getAttribute('data-kpi-display-value') || '0') : '0');
    }

    function shouldResolveZeroKpiLocally(card) {
        return getKpiDisplayValue(card) <= 0;
    }

    function matchesFilterKey(entry) {
        if (!searchState.filterKey || searchState.filterKey === 'all') {
            return true;
        }
        if (searchState.filterKey === 'new-leads') {
            return String(entry.semantic_stage || '') === 'new-leads';
        }
        return true;
    }

    function sortEntries(entries) {
        entries.sort(function(leftEntry, rightEntry) {
            if (searchState.sortBy === 'registration') {
                var compare = getRegistrationAgeValue(leftEntry) - getRegistrationAgeValue(rightEntry);

                if (searchState.sortDirection === 'desc') {
                    compare *= -1;
                }

                if (compare !== 0) {
                    return compare;
                }
            }

            return String(leftEntry.full_name || '').localeCompare(String(rightEntry.full_name || ''), 'pt-BR');
        });
    }

    function restoreServerRows() {
        searchState.isUsingSearchIndex = false;
        tbody.innerHTML = '';
        serverRows.forEach(function(row) {
            row.hidden = false;
            tbody.appendChild(row);
        });
        if (emptySearchRow) {
            tbody.appendChild(emptySearchRow);
        }
    }

    function renderSearchRows(entries) {
        var html = entries.map(function(entry) {
            return entry.row_html || '';
        }).join('');
        var shouldShowNextPage = searchState.hasNext && (searchState.query || searchState.listAllCommand);

        serverRows.forEach(function(row) {
            row.hidden = true;
        });

        if (emptySearchRow) {
            emptySearchRow.remove();
        }

        tbody.innerHTML = html;
        if (shouldShowNextPage) {
            tbody.insertAdjacentHTML(
                'beforeend',
                '<tr data-intake-search-next-row><td colspan="6" class="table-empty-cell p-6 text-center"><button type="button" class="button secondary" data-intake-search-next>Carregar proximas 200 entradas</button></td></tr>'
            );
        }

        if (emptySearchRow) {
            tbody.appendChild(emptySearchRow);
        }

        searchState.isUsingSearchIndex = true;
    }

    function applyLocalQueueState() {
        if (localZeroKpiState.key) {
            restoreServerRows();
            serverRows.forEach(function(row) {
                row.hidden = true;
            });
            updateCount(0);
            syncEmptyState(0);
            return;
        }

        var shouldUseSearchIndex = searchState.query || searchState.listAllCommand || searchState.filterKey;
        if (!shouldUseSearchIndex) {
            restoreServerRows();

            var visibleRows = Array.prototype.slice.call(tbody.querySelectorAll('.intake-directory-row'));
            if (searchState.sortBy === 'registration') {
                var sortedServerEntries = visibleRows.map(function(row) {
                    var nameNode = row.querySelector('.intake-contact-name');
                    return {
                        full_name: nameNode ? nameNode.textContent.trim() : '',
                        registration_age_days: Number(row.getAttribute('data-registration-age-days') || '0'),
                        row: row,
                    };
                });
                sortEntries(sortedServerEntries);
                sortedServerEntries.forEach(function(entry) {
                    tbody.appendChild(entry.row);
                });
            }

            updateCount(visibleRows.length);
            syncEmptyState(visibleRows.length);
            return;
        }

        var filteredEntries = getSearchIndex().filter(function(entry) {
            if (!matchesFilterKey(entry)) {
                return false;
            }
            if (searchState.listAllCommand) {
                return true;
            }
            return normalizeSearchText(entry.full_name).indexOf(searchState.query) !== -1;
        });

        sortEntries(filteredEntries);
        renderSearchRows(filteredEntries);
        updateCount(filteredEntries.length);
        syncEmptyState(filteredEntries.length);
    }

    sortPill.addEventListener('click', function() {
        clearLocalZeroKpiState();
        if (searchState.sortBy === 'registration') {
            searchState.sortDirection = searchState.sortDirection === 'desc' ? 'asc' : 'desc';
        } else {
            searchState.sortBy = 'registration';
            searchState.sortDirection = sortPill.getAttribute('data-sort-direction') || 'desc';
        }

        syncSortPill();
        applyLocalQueueState();
    });

    searchInput.addEventListener('input', function() {
        clearLocalZeroKpiState();
        setSearchStateFromInputValue(searchInput.value);
        applyLocalQueueState();
    });

    filterForm.addEventListener('submit', function(event) {
        event.preventDefault();
        clearLocalZeroKpiState();
        setSearchStateFromInputValue(searchInput.value);
        applyLocalQueueState();
    });

    intakeKpiCards.forEach(function(card) {
        function handleKpiIntent(event) {
            if (!shouldResolveZeroKpiLocally(card)) {
                clearLocalZeroKpiState();
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            localZeroKpiState.key = card.getAttribute('data-intake-kpi-key') || '';
            localZeroKpiState.label = localZeroKpiState.key || 'selecionado';
            activateIntakePanel(card.getAttribute('data-target-panel') || 'tab-intake-queue');
            syncIntakeKpiCards(card);
            applyLocalQueueState();
        }

        card.addEventListener('click', handleKpiIntent, true);
        card.addEventListener('keydown', function(event) {
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            handleKpiIntent(event);
        });
    });

        filterPills.forEach(function(pill) {
        pill.addEventListener('click', function(event) {
            event.preventDefault();
            clearLocalZeroKpiState();
            var nextFilter = pill.getAttribute('data-intake-filter') || 'all';
            performanceTelemetry.clickWaitsForHydration += 1;
            var waitStartedAt = performance.now();
            hydrateSearchIndexForLocalFilters().then(function(didHydrate) {
                var waitDurationMs = performance.now() - waitStartedAt;
                recordPerformanceSample(performanceTelemetry.clickWaitDurationMs, waitDurationMs);
                syncDevPanel();
                logPerformanceTelemetry('click-wait-finished', {
                    next_filter: nextFilter,
                    hydrated: Boolean(didHydrate),
                    wait_duration_ms: Math.round(waitDurationMs),
                    loaded_entries: searchState.index.length,
                });
                if (didHydrate === false && searchState.hasNext) {
                    if (nextFilter === 'new-leads') {
                        window.location.assign('?panel=tab-intake-queue&semantic_stage=new-leads');
                    } else {
                        window.location.assign('?panel=tab-intake-queue');
                    }
                    return;
                }
                searchState.filterKey = nextFilter === 'all' ? '' : nextFilter;
                syncFilterPills();
                applyLocalQueueState();
            });
        });
    });

    tbody.addEventListener('click', function(event) {
        var nextButton = event.target.closest('[data-intake-search-next]');
        if (!nextButton) {
            return;
        }

        event.preventDefault();
        nextButton.disabled = true;
        nextButton.textContent = 'Carregando...';
        performanceTelemetry.manualNextPageLoads += 1;
        syncDevPanel();
        loadNextSearchPage().then(function() {
            logPerformanceTelemetry('manual-next-page-finished', {
                loaded_entries: searchState.index.length,
                has_next: searchState.hasNext,
            });
            applyLocalQueueState();
        });
    });

    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            scheduleIdleIntakeHydration();
        }
    });

    window.addEventListener('focus', function() {
        scheduleIdleIntakeHydration();
    });

    setSearchStateFromInputValue(searchInput.value);
    syncFilterPills();
    syncSortPill();
    applyLocalQueueState();
    syncDevPanel();
    scheduleIdleIntakeHydration();
})();
