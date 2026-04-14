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
    var sortPill = pageRoot.querySelector('[data-intake-sort="registration"]');
    var emptySearchRow = tbody ? tbody.querySelector('[data-intake-empty-search-row]') : null;
    var intakeSearchConfig = pageBehavior.intake_search || {};

    if (!queueBoard || !tbody || !filterForm || !searchInput || !sortPill) {
        return;
    }

    var serverRows = Array.prototype.slice.call(tbody.querySelectorAll('.intake-directory-row'));
    var intakeSearchCacheKey = 'octobox.intake.queue.search-index.v1.' + String(intakeSearchConfig.cache_key || 'all');
    var searchState = {
        query: '',
        listAllCommand: false,
        sortBy: null,
        sortDirection: sortPill.getAttribute('data-sort-direction') || 'desc',
        index: [],
        isUsingSearchIndex: false,
        hasNext: Boolean(intakeSearchConfig.has_next),
        nextOffset: intakeSearchConfig.next_offset || null,
        total: Number(intakeSearchConfig.total || 0),
        isLoadingNext: false,
    };

    function setSearchStateFromInputValue(value) {
        searchState.listAllCommand = isListAllSearchCommand(value);
        searchState.query = searchState.listAllCommand ? '' : normalizeSearchText(value);
        if (searchState.listAllCommand) {
            searchState.sortBy = null;
            searchState.sortDirection = sortPill.getAttribute('data-sort-direction') || 'desc';
        }
    }

    function buildCurrentServerIndex() {
        return serverRows.map(function(row) {
            var nameNode = row.querySelector('.intake-contact-name');
            return {
                id: Number(row.getAttribute('data-intake-id') || 0),
                full_name: nameNode ? nameNode.textContent.trim() : '',
                registration_age_days: Number(row.getAttribute('data-registration-age-days') || '0'),
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
        writeSessionJson(intakeSearchCacheKey, {
            index: normalizedIndex,
            refresh_token: intakeSearchConfig.refresh_token || '',
            has_next: searchState.hasNext,
            next_offset: searchState.nextOffset,
            total: searchState.total,
            saved_at: Date.now(),
        });
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

        emptySearchRow.hidden = visibleCount !== 0 || (!searchState.query && !searchState.listAllCommand);
    }

    function syncSortPill() {
        var isActive = searchState.sortBy === 'registration';
        sortPill.textContent = 'Data ' + (searchState.sortDirection === 'asc' ? '\u2191' : '\u2193');
        sortPill.classList.toggle('is-active', isActive);
        sortPill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
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
        var shouldUseSearchIndex = searchState.query || searchState.listAllCommand;
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
        setSearchStateFromInputValue(searchInput.value);
        applyLocalQueueState();
    });

    filterForm.addEventListener('submit', function(event) {
        event.preventDefault();
        setSearchStateFromInputValue(searchInput.value);
        applyLocalQueueState();
    });

    tbody.addEventListener('click', function(event) {
        var nextButton = event.target.closest('[data-intake-search-next]');
        if (!nextButton) {
            return;
        }

        event.preventDefault();
        nextButton.disabled = true;
        nextButton.textContent = 'Carregando...';
        loadNextSearchPage().then(function() {
            applyLocalQueueState();
        });
    });

    setSearchStateFromInputValue(searchInput.value);
    syncSortPill();
    applyLocalQueueState();
})();
