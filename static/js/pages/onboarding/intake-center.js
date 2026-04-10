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
        query: normalizeSearchText(searchInput.value),
        sortBy: null,
        sortDirection: sortPill.getAttribute('data-sort-direction') || 'desc',
        index: [],
        isUsingSearchIndex: false,
    };

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

    function persistSearchIndex(index) {
        var normalizedIndex = Array.isArray(index) ? index : [];
        searchState.index = normalizedIndex;
        writeSessionJson(intakeSearchCacheKey, {
            index: normalizedIndex,
            refresh_token: intakeSearchConfig.refresh_token || '',
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
            persistSearchIndex(intakeSearchConfig.index);
            return searchState.index;
        }

        var fallbackIndex = buildCurrentServerIndex();
        persistSearchIndex(fallbackIndex);
        return searchState.index;
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

        emptySearchRow.hidden = visibleCount !== 0 || !searchState.query;
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

        serverRows.forEach(function(row) {
            row.hidden = true;
        });

        if (emptySearchRow) {
            emptySearchRow.remove();
        }

        tbody.innerHTML = html;

        if (emptySearchRow) {
            tbody.appendChild(emptySearchRow);
        }

        searchState.isUsingSearchIndex = true;
    }

    function applyLocalQueueState() {
        if (!searchState.query) {
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
        searchState.query = normalizeSearchText(searchInput.value);
        applyLocalQueueState();
    });

    syncSortPill();
    applyLocalQueueState();
})();
