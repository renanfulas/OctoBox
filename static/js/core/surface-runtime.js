/**
 * ARQUIVO: kernel minimo de runtime de superficie para cache local e invalidacao.
 *
 * POR QUE ELE EXISTE:
 * - tira de cada pagina a infraestrutura repetida de cache, versao e sincronizacao entre abas.
 * - cria uma base pequena e segura para reaproveitamento de leitura no frontend autenticado.
 *
 * O QUE ESTE ARQUIVO FAZ:
 * 1. normaliza leitura do contrato de superficie vindo do `current-page-behavior`.
 * 2. oferece cache em memoria e `sessionStorage` por superficie.
 * 3. propaga invalidacao entre abas quando disponivel.
 *
 * PONTOS CRITICOS:
 * - este runtime nao substitui a validacao do backend.
 * - o cache em disco continua opt-in por contrato.
 */
(function(global) {
    var memoryCache = new Map();
    var channelRegistry = new Map();

    function supportsSessionStorage() {
        try {
            return typeof global.sessionStorage !== 'undefined';
        } catch (error) {
            return false;
        }
    }

    function readSessionJson(key) {
        if (!supportsSessionStorage()) {
            return null;
        }

        try {
            var rawValue = global.sessionStorage.getItem(key);
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
            global.sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            // Degradacao silenciosa se storage estiver indisponivel ou cheio.
        }
    }

    function removeSessionKey(key) {
        if (!supportsSessionStorage()) {
            return;
        }

        try {
            global.sessionStorage.removeItem(key);
        } catch (error) {
            // Degradacao silenciosa.
        }
    }

    function buildChannelName(surfaceKey) {
        return 'octobox.surface-runtime.' + String(surfaceKey || 'generic');
    }

    function getBroadcastChannel(surfaceKey) {
        if (typeof global.BroadcastChannel !== 'function') {
            return null;
        }

        var channelName = buildChannelName(surfaceKey);
        if (!channelRegistry.has(channelName)) {
            channelRegistry.set(channelName, new global.BroadcastChannel(channelName));
        }
        return channelRegistry.get(channelName);
    }

    function clonePlainObject(value) {
        if (!value || typeof value !== 'object') {
            return value;
        }

        try {
            return JSON.parse(JSON.stringify(value));
        } catch (error) {
            return value;
        }
    }

    function createSurfaceRuntime(contract) {
        var resolvedContract = contract || {};
        var surfaceBehavior = resolvedContract.surface_behavior || {};
        var scope = surfaceBehavior.scope || {};
        var cacheConfig = surfaceBehavior.cache || {};
        var invalidationConfig = surfaceBehavior.invalidation || {};
        var safetyConfig = surfaceBehavior.safety || {};
        var surfaceKey = String(surfaceBehavior.surface_key || 'generic');
        var runtimeContractVersion = String(surfaceBehavior.runtime_contract_version || 'v1');
        var roleSlug = String(scope.role_slug || '');
        var storageTier = String(scope.storage_tier || 'session');
        var canPersistToDisk = Boolean(safetyConfig.persist_to_disk) && storageTier === 'persistent';
        var channel = invalidationConfig.cross_tab_sync ? getBroadcastChannel(surfaceKey) : null;

        function buildBaseStorageKey(suffix) {
            return [
                'octobox',
                'surface',
                runtimeContractVersion,
                surfaceKey,
                roleSlug || 'anonymous',
                suffix || 'state',
            ].join('.');
        }

        function readMemoryEntry(suffix) {
            return memoryCache.get(buildBaseStorageKey(suffix)) || null;
        }

        function writeMemoryEntry(suffix, value) {
            memoryCache.set(buildBaseStorageKey(suffix), clonePlainObject(value));
        }

        function removeMemoryEntry(suffix) {
            memoryCache.delete(buildBaseStorageKey(suffix));
        }

        function readCacheEntry(suffix) {
            var memoryEntry = readMemoryEntry(suffix);
            if (memoryEntry) {
                return memoryEntry;
            }

            if (!canPersistToDisk && storageTier !== 'session') {
                return null;
            }

            var sessionEntry = readSessionJson(buildBaseStorageKey(suffix));
            if (sessionEntry) {
                writeMemoryEntry(suffix, sessionEntry);
            }
            return sessionEntry;
        }

        function writeCacheEntry(suffix, value) {
            writeMemoryEntry(suffix, value);

            if (!canPersistToDisk && storageTier !== 'session') {
                return;
            }
            writeSessionJson(buildBaseStorageKey(suffix), value);
        }

        function removeCacheEntry(suffix) {
            removeMemoryEntry(suffix);
            removeSessionKey(buildBaseStorageKey(suffix));
        }

        function isFresh(entry, options) {
            if (!entry || typeof entry !== 'object') {
                return false;
            }

            var resolvedOptions = options || {};
            var expectedRefreshToken = resolvedOptions.refreshToken;
            var expectedSnapshotVersion = resolvedOptions.snapshotVersion;
            var ttlMs = Number(resolvedOptions.ttlMs || cacheConfig.ttl_ms || 0);

            if (expectedRefreshToken !== undefined && String(entry.refresh_token || '') !== String(expectedRefreshToken || '')) {
                return false;
            }

            if (expectedSnapshotVersion && String(entry.snapshot_version || '') !== String(expectedSnapshotVersion || '')) {
                return false;
            }

            if (ttlMs > 0 && entry.cached_at) {
                var ageMs = Date.now() - Number(entry.cached_at || 0);
                if (ageMs > ttlMs) {
                    return false;
                }
            }

            return true;
        }

        function buildCacheEnvelope(payload, extra) {
            var resolvedExtra = extra || {};
            return {
                cached_at: Date.now(),
                refresh_token: resolvedExtra.refreshToken !== undefined ? resolvedExtra.refreshToken : cacheConfig.refresh_token || '',
                snapshot_version: resolvedExtra.snapshotVersion !== undefined ? resolvedExtra.snapshotVersion : cacheConfig.snapshot_version || '',
                payload: payload,
            };
        }

        function broadcastInvalidation(reason, payload) {
            var message = {
                surface_key: surfaceKey,
                reason: reason || 'unknown',
                payload: payload || {},
                emitted_at: Date.now(),
            };

            if (channel) {
                try {
                    channel.postMessage(message);
                } catch (error) {
                    // segue com fallback abaixo
                }
            }

            if (supportsSessionStorage()) {
                try {
                    global.sessionStorage.setItem(
                        buildBaseStorageKey('last-invalidation'),
                        JSON.stringify(message)
                    );
                } catch (error) {
                    // degrade silenciosamente
                }
            }
        }

        function subscribeInvalidation(callback) {
            if (typeof callback !== 'function') {
                return function() {};
            }

            var onChannelMessage = function(event) {
                if (event && event.data && event.data.surface_key === surfaceKey) {
                    callback(event.data);
                }
            };
            var onStorage = function(event) {
                if (!event || event.key !== buildBaseStorageKey('last-invalidation') || !event.newValue) {
                    return;
                }
                try {
                    var payload = JSON.parse(event.newValue);
                    if (payload && payload.surface_key === surfaceKey) {
                        callback(payload);
                    }
                } catch (error) {
                    // ignore payload invalido
                }
            };

            if (channel) {
                channel.addEventListener('message', onChannelMessage);
            }
            global.addEventListener('storage', onStorage);

            return function unsubscribe() {
                if (channel) {
                    channel.removeEventListener('message', onChannelMessage);
                }
                global.removeEventListener('storage', onStorage);
            };
        }

        return {
            contract: resolvedContract,
            surfaceBehavior: surfaceBehavior,
            buildStorageKey: buildBaseStorageKey,
            readCacheEntry: readCacheEntry,
            writeCacheEntry: writeCacheEntry,
            removeCacheEntry: removeCacheEntry,
            isFresh: isFresh,
            buildCacheEnvelope: buildCacheEnvelope,
            broadcastInvalidation: broadcastInvalidation,
            subscribeInvalidation: subscribeInvalidation,
            purgeAllKnownState: function() {
                removeCacheEntry('state');
                removeCacheEntry('directory-search-index');
                removeCacheEntry('directory-search-stale');
                removeCacheEntry('last-invalidation');
            },
        };
    }

    global.OctoBoxSurfaceRuntime = {
        supportsSessionStorage: supportsSessionStorage,
        readSessionJson: readSessionJson,
        writeSessionJson: writeSessionJson,
        removeSessionKey: removeSessionKey,
        createSurfaceRuntime: createSurfaceRuntime,
    };
})(window);
