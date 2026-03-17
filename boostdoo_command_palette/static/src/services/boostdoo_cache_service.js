/** @odoo-module **/
// Copyright 2026 Boostdoo

import { registry } from "@web/core/registry";

/**
 * Boostdoo Cache Service
 *
 * Provides a simple TTL-based in-memory cache used by the Command Palette to
 * avoid redundant RPC calls when reopening the palette within a short period.
 *
 * Cached namespaces:
 *   - "menus"    : app menu items from ir.ui.menu
 *   - "models"   : model names / display names
 *   - "commands" : custom commands from boostdoo.command.custom
 */

const CACHE_SERVICE_NAME = "boostdoo_cache_service";

/**
 * @typedef  {Object} CacheEntry
 * @property {*}      data        The cached payload.
 * @property {number} expiresAt   Unix timestamp (ms) when the entry expires.
 */

export const boostdooCacheService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        /** @type {Map<string, CacheEntry>} */
        const _store = new Map();

        /**
         * Retrieve a value from the cache.
         *
         * @param {string} key
         * @returns {*|null}  Cached value or null if missing / expired.
         */
        function get(key) {
            const entry = _store.get(key);
            if (!entry) return null;
            if (Date.now() > entry.expiresAt) {
                _store.delete(key);
                return null;
            }
            return entry.data;
        }

        /**
         * Store a value in the cache.
         *
         * @param {string} key
         * @param {*}      data
         * @param {number} [ttlSeconds=300]
         */
        function set(key, data, ttlSeconds = 300) {
            _store.set(key, { data, expiresAt: Date.now() + ttlSeconds * 1000 });
        }

        /**
         * Invalidate a specific cache key or, when called with no argument,
         * clear the entire cache.
         *
         * @param {string} [key]
         */
        function invalidate(key) {
            if (key) {
                _store.delete(key);
            } else {
                _store.clear();
            }
        }

        /**
         * Convenience: retrieve value if cached, otherwise execute `loader`,
         * cache the result and return it.
         *
         * @param {string}   key
         * @param {Function} loader        Async function that returns fresh data.
         * @param {number}   [ttlSeconds]
         * @returns {Promise<*>}
         */
        async function getOrLoad(key, loader, ttlSeconds = 300) {
            const cached = get(key);
            if (cached !== null) return cached;
            const data = await loader();
            set(key, data, ttlSeconds);
            return data;
        }

        return { get, set, invalidate, getOrLoad };
    },
};

registry.category("services").add(CACHE_SERVICE_NAME, boostdooCacheService);
