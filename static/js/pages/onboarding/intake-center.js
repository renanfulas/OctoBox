(function() {
    function supportsSessionStorage() {
        if (window.OctoBoxSurfaceRuntime && typeof window.OctoBoxSurfaceRuntime.supportsSessionStorage === 'function') {
            return window.OctoBoxSurfaceRuntime.supportsSessionStorage();
        }
        try {
            return typeof window.sessionStorage !== 'undefined';
        } catch (error) {
            return false;
        }
    }

    function readSessionJson(key) {
        if (surfaceRuntime) {
            if (key === intakeSearchCacheKey) {
                return surfaceRuntime.readCacheEntry('intake-search-index');
            }
            if (key === intakeSearchStaleKey) {
                return surfaceRuntime.readCacheEntry('intake-search-stale');
            }
        }
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
        if (surfaceRuntime) {
            if (key === intakeSearchCacheKey) {
                surfaceRuntime.writeCacheEntry('intake-search-index', value);
                return;
            }
            if (key === intakeSearchStaleKey) {
                surfaceRuntime.writeCacheEntry('intake-search-stale', value);
                return;
            }
        }
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
    var surfaceRuntimeContract = pageBehavior.surface_runtime || {};
    var surfaceRuntime = window.OctoBoxSurfaceRuntime && typeof window.OctoBoxSurfaceRuntime.createSurfaceRuntime === 'function'
        ? window.OctoBoxSurfaceRuntime.createSurfaceRuntime(surfaceRuntimeContract)
        : null;
    var initialServerFilterKey = getActiveServerFilterKey();

    if (!queueBoard || !tbody || !filterForm || !searchInput || !sortPill) {
        return;
    }

    var serverRows = Array.prototype.slice.call(tbody.querySelectorAll('.intake-directory-row'));
    var intakeSearchCacheKey = surfaceRuntime
        ? surfaceRuntime.buildStorageKey('intake-search-index')
        : 'octobox.intake.queue.search-index.v1.' + String(intakeSearchConfig.cache_key || 'all');
    var intakeSearchStaleKey = surfaceRuntime
        ? surfaceRuntime.buildStorageKey('intake-search-stale')
        : 'octobox.intake.queue.search-index.stale.v1.' + String(intakeSearchConfig.cache_key || 'all');
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

    if (surfaceRuntime && typeof surfaceRuntime.subscribeInvalidation === 'function') {
        surfaceRuntime.subscribeInvalidation(function(invalidationEvent) {
            if (!invalidationEvent || invalidationEvent.payload && invalidationEvent.payload.scope !== 'intake-search') {
                return;
            }
            searchState.index = [];
            searchState.idleHydrationCompleted = false;
            writeSessionJson(intakeSearchStaleKey, {
                stale: true,
                marked_at: Date.now(),
                reason: invalidationEvent.reason || 'cross-tab',
            });
        });
    }

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
            return {
                id: Number(row.getAttribute('data-intake-id') || 0),
                full_name: row.getAttribute('data-full-name') || '',
                channel_label: row.getAttribute('data-channel-label') || '',
                source_key: row.getAttribute('data-source-key') || '',
                source_label: row.getAttribute('data-source-label') || '',
                registration_age_days: Number(row.getAttribute('data-registration-age-days') || '0'),
                registration_age_label: row.getAttribute('data-registration-age-label') || '',
                semantic_stage: row.getAttribute('data-semantic-stage') || '',
                semantic_label: row.getAttribute('data-semantic-label') || '',
                conversion_reason: row.getAttribute('data-conversion-reason') || '',
                created_today: row.getAttribute('data-created-today') === 'true',
                assigned: row.getAttribute('data-assigned') === 'true',
                assigned_label: row.getAttribute('data-assigned-label') || 'Aguardando',
                whatsapp_href: row.getAttribute('data-whatsapp-href') || '',
                conversion: {
                    action_type: row.getAttribute('data-conversion-action-type') || '',
                    action_label: row.getAttribute('data-conversion-action-label') || '',
                    href: row.getAttribute('data-conversion-action-href') || '',
                    requires_post: row.getAttribute('data-conversion-action-post') === 'true',
                },
                permissions: {
                    can_reject: row.getAttribute('data-can-reject') === 'true',
                    can_send_whatsapp_invite: row.getAttribute('data-can-send-whatsapp-invite') === 'true',
                },
            };
        });
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getCsrfToken() {
        var csrfNode = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return csrfNode ? String(csrfNode.value || '') : '';
    }

    function getQueueReturnQuery() {
        var currentParams = new URLSearchParams(window.location.search || '');
        if (!currentParams.has('panel')) {
            currentParams.set('panel', 'tab-intake-queue');
        }
        return currentParams.toString();
    }

    function buildAvatarTone(entryId) {
        var tones = ['orange', 'blue', 'purple', 'teal', 'pink', 'indigo'];
        var normalizedId = Math.abs(Number(entryId || 0)) || 0;
        return tones[normalizedId % tones.length];
    }

    function buildSemanticPillClass(entry) {
        if (String(entry.semantic_stage || '') === 'new-leads') {
            return 'student-status-pill--blue';
        }
        if (String(entry.semantic_stage || '') === 'lead-open') {
            return 'student-status-pill--orange';
        }
        return 'student-status-pill--gray';
    }

    function buildConversionActionHtml(entry) {
        if (!entry || !entry.conversion) {
            return '';
        }

        if (entry.conversion.href) {
            return '<a class="button intake-convert-button" href="' + escapeHtml(entry.conversion.href) + '">' + escapeHtml(entry.conversion.action_label) + '</a>';
        }

        if (entry.conversion.requires_post) {
            return [
                '<form method="post" class="intake-row-form" data-action="intake-queue-actions">',
                '<input type="hidden" name="csrfmiddlewaretoken" value="', escapeHtml(getCsrfToken()), '">',
                '<input type="hidden" name="intake_id" value="', escapeHtml(entry.id), '">',
                '<input type="hidden" name="return_query" value="', escapeHtml(getQueueReturnQuery()), '">',
                '<button class="button intake-convert-button" type="submit" name="action" value="move-to-conversation">',
                escapeHtml(entry.conversion.action_label),
                '</button>',
                '</form>',
            ].join('');
        }

        return '';
    }

    function buildRejectActionHtml(entry) {
        if (!entry || !entry.permissions || !entry.permissions.can_reject) {
            return '';
        }

        return [
            '<form method="post" class="intake-row-form" data-action="intake-queue-actions">',
            '<input type="hidden" name="csrfmiddlewaretoken" value="', escapeHtml(getCsrfToken()), '">',
            '<input type="hidden" name="intake_id" value="', escapeHtml(entry.id), '">',
            '<input type="hidden" name="return_query" value="', escapeHtml(getQueueReturnQuery()), '">',
            '<button class="button secondary" type="submit" name="action" value="reject-intake">Recusar</button>',
            '</form>',
        ].join('');
    }

    function buildWhatsappActionHtml(entry) {
        if (!entry || !entry.permissions || !entry.permissions.can_send_whatsapp_invite) {
            return '';
        }

        return [
            '<form method="post" class="intake-row-form" data-action="intake-queue-actions">',
            '<input type="hidden" name="csrfmiddlewaretoken" value="', escapeHtml(getCsrfToken()), '">',
            '<input type="hidden" name="intake_id" value="', escapeHtml(entry.id), '">',
            '<input type="hidden" name="return_query" value="', escapeHtml(getQueueReturnQuery()), '">',
            '<button class="button secondary" type="submit" name="action" value="send-whatsapp-invite">Convidar 1 clique</button>',
            '</form>',
        ].join('');
    }

    function buildWhatsappLinkHtml(entry) {
        if (!entry || !entry.whatsapp_href) {
            return '';
        }

        return [
            '<div class="intake-whatsapp-slot">',
            '<a class="button secondary intake-whatsapp-button" href="', escapeHtml(entry.whatsapp_href), '" target="_blank" rel="noopener" aria-label="Conversar com ', escapeHtml(entry.full_name), ' no WhatsApp" title="Conversar no WhatsApp">',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" aria-hidden="true" focusable="false">',
            '<path fill="currentColor" d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-5.5-2.8-23.2-8.5-44.2-27.1-16.4-14.6-27.4-32.7-30.6-38.2-3.2-5.6-.3-8.6 2.4-11.4 2.5-2.5 5.5-6.5 8.3-9.8 2.8-3.3 3.7-5.6 5.5-9.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 13.2 5.8 23.5 9.2 31.5 11.8 13.3 4.2 25.4 3.6 35 2.2 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.7z"/>',
            '</svg>',
            '</a>',
            '</div>',
        ].join('');
    }

    function buildSearchRowHtml(entry) {
        var initials = String(entry.full_name || '').trim().slice(0, 2).toUpperCase() || '--';
        return [
            '<tr class="intake-directory-row" data-intake-id="', escapeHtml(entry.id), '" data-registration-age-days="', escapeHtml(entry.registration_age_days), '" data-search-index="', escapeHtml(entry.full_name), '" data-semantic-stage="', escapeHtml(entry.semantic_stage), '" data-created-today="', entry.created_today ? 'true' : 'false', '" data-assigned="', entry.assigned ? 'true' : 'false', '">',
            '<td class="intake-queue-col--contact" data-label="Contato">',
            '<div class="intake-contact-identity">',
            '<div class="avatar-circle avatar-', buildAvatarTone(entry.id), ' intake-contact-avatar">', escapeHtml(initials), '</div>',
            '<div class="intake-contact-copy"><strong class="intake-contact-name">', escapeHtml(entry.full_name), '</strong><span class="intake-contact-channel">', escapeHtml(entry.channel_label), '</span></div>',
            '</div></td>',
            '<td class="intake-queue-col--source" data-label="Origem"><span class="intake-table-text">', escapeHtml(entry.source_label), '</span></td>',
            '<td class="intake-queue-col--stage" data-label="Leitura"><div class="intake-reading-stack"><span class="student-status-pill ', buildSemanticPillClass(entry), '">', escapeHtml(entry.semantic_label), '</span><span class="intake-reading-note">', escapeHtml(entry.conversion_reason), '</span></div></td>',
            '<td class="intake-queue-col--owner" data-label="Responsavel"><span class="intake-table-text">', escapeHtml(entry.assigned_label || 'Aguardando'), '</span></td>',
            '<td class="intake-queue-col--registration" data-label="Registro"><span class="intake-table-text">', escapeHtml(entry.registration_age_label), '</span></td>',
            '<td class="intake-queue-col--actions" data-label="Proxima acao"><div class="operation-hero-action-rail intake-row-actions">',
            buildConversionActionHtml(entry),
            buildRejectActionHtml(entry),
            buildWhatsappActionHtml(entry),
            buildWhatsappLinkHtml(entry),
            '</div></td></tr>',
        ].join('');
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
            cached_at: Date.now(),
            refresh_token: intakeSearchConfig.refresh_token || '',
            has_next: searchState.hasNext,
            next_offset: searchState.nextOffset,
            total: searchState.total,
            saved_at: Date.now(),
        });
        writeSessionJson(intakeSearchStaleKey, {
            stale: false,
            marked_at: '',
        });
        syncDevPanel();
    }

    function isSearchIndexStale() {
        var staleState = readSessionJson(intakeSearchStaleKey);
        return Boolean(staleState && staleState.stale);
    }

    function getSearchIndexFromCache() {
        var cacheEntry = readSessionJson(intakeSearchCacheKey);
        if (!cacheEntry || !Array.isArray(cacheEntry.index)) {
            return [];
        }

        if (surfaceRuntime && typeof surfaceRuntime.isFresh === 'function') {
            if (!surfaceRuntime.isFresh(cacheEntry, { refreshToken: intakeSearchConfig.refresh_token }) || isSearchIndexStale()) {
                return [];
            }
        } else {
            if ((cacheEntry.refresh_token || '') !== String(intakeSearchConfig.refresh_token || '') || isSearchIndexStale()) {
                return [];
            }
        }

        searchState.hasNext = Object.prototype.hasOwnProperty.call(cacheEntry, 'has_next') ? Boolean(cacheEntry.has_next) : Boolean(intakeSearchConfig.has_next);
        searchState.nextOffset = Object.prototype.hasOwnProperty.call(cacheEntry, 'next_offset') ? cacheEntry.next_offset : (intakeSearchConfig.next_offset || null);
        searchState.total = Number(cacheEntry.total || intakeSearchConfig.total || cacheEntry.index.length || 0);
        return cacheEntry.index;
    }

    function getSearchIndex() {
        if (isSearchIndexStale()) {
            searchState.index = [];
        }

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
            return buildSearchRowHtml(entry);
        }).join('');
        var nextPageLabel = 'Carregar proximas ' + String(intakeSearchConfig.page_size || 50) + ' entradas';
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
                '<tr data-intake-search-next-row><td colspan="6" class="table-empty-cell p-6 text-center"><button type="button" class="button secondary" data-intake-search-next>' + escapeHtml(nextPageLabel) + '</button></td></tr>'
            );
        }

        if (emptySearchRow) {
            tbody.appendChild(emptySearchRow);
        }

        searchState.isUsingSearchIndex = true;
    }

    function markSearchIndexStale(reason) {
        var stalePayload = {
            stale: true,
            marked_at: Date.now(),
            reason: reason || 'mutation',
        };
        writeSessionJson(intakeSearchStaleKey, stalePayload);
        if (surfaceRuntime && typeof surfaceRuntime.broadcastInvalidation === 'function') {
            surfaceRuntime.broadcastInvalidation(reason || 'mutation', {
                scope: 'intake-search',
                refresh_token: String(intakeSearchConfig.refresh_token || ''),
            });
        }
    }

    function applyLocalQueueState() {
        if (isSearchIndexStale() && (searchState.query || searchState.listAllCommand || searchState.filterKey)) {
            window.location.assign(window.location.pathname + window.location.search);
            return;
        }

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

    pageRoot.addEventListener('submit', function(event) {
        var targetForm = event.target;
        if (!targetForm || !(targetForm instanceof HTMLFormElement)) {
            return;
        }
        if (targetForm.matches('.intake-row-form') || targetForm.getAttribute('data-form-kind') === 'intake-quick-create') {
            markSearchIndexStale('mutation');
        }
    }, true);

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
