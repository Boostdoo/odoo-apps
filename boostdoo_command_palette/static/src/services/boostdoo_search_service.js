/** @odoo-module **/
// Copyright 2026 Boostdoo

import { registry } from "@web/core/registry";
import { fuzzyFilter } from "../utils/fuzzy_search";

/**
 * Models searched when the user types a query of 2+ characters.
 * Failures (model not installed, no access) are silently ignored.
 */
const SEARCHABLE_MODELS = [
    { model: "res.partner",     label: "Contact"        },
    { model: "product.product", label: "Product"        },
    { model: "account.move",    label: "Invoice / Bill" },
    { model: "sale.order",      label: "Sale Order"     },
    { model: "purchase.order",  label: "Purchase Order" },
    { model: "stock.picking",   label: "Transfer"       },
    { model: "project.task",    label: "Task"           },
    { model: "crm.lead",        label: "Lead"           },
    { model: "hr.employee",     label: "Employee"       },
];

/**
 * Boostdoo Search Service
 *
 * Orchestrates multi-source search across:
 *   - App menu items  (ir.ui.menu via menuService)
 *   - Custom commands (boostdoo.command.custom via RPC)
 *   - Recent history  (boostdoo.command.history from cache)
 *
 * Returns a unified, ranked list of CommandResult objects consumed by the
 * Command Palette component.
 */

const SEARCH_SERVICE_NAME = "boostdoo_search_service";

/**
 * @typedef {Object} CommandResult
 * @property {string}   id          Unique identifier for deduplication.
 * @property {string}   name        Display label.
 * @property {string}   description Short description / hint.
 * @property {string}   category    "menu" | "custom" | "history" | "favorite"
 * @property {Function} action      Callback executed when the item is selected.
 * @property {number}   [score]     Relevance score (higher = better).
 */

export const boostdooSearchService = {
    dependencies: ["orm", "menu", "boostdoo_cache_service", "action"],

    start(env, { orm, menu, boostdoo_cache_service: cache, action: actionService }) {
        const CACHE_TTL = 300;

        // ─── Loaders ────────────────────────────────────────────────────────────

        async function _loadCustomCommands() {
            return cache.getOrLoad(
                "boostdoo_custom_commands",
                () => orm.searchRead(
                    "boostdoo.command.custom",
                    [["active", "=", true]],
                    ["id", "name", "description", "action_id", "shortcut"],
                    { limit: 200 }
                ),
                CACHE_TTL
            );
        }

        async function _loadHistory() {
            return cache.getOrLoad(
                "boostdoo_history",
                () => orm.searchRead(
                    "boostdoo.command.history",
                    [],
                    ["command_key", "command_name", "use_count"],
                    { limit: 20, order: "use_count desc" }
                ),
                60
            );
        }

        async function _loadFavorites() {
            return cache.getOrLoad(
                "boostdoo_favorites",
                () => orm.searchRead(
                    "boostdoo.command.favorite",
                    [],
                    ["command_key", "name", "sequence"],
                    { order: "sequence asc" }
                ),
                CACHE_TTL
            );
        }

        // ─── Action resolver ────────────────────────────────────────────────────

        /**
         * Resolve a stored command_key back into an executable action.
         * Conventions:
         *   menu_{id}              → navigate to ir.ui.menu
         *   custom_{id}            → execute boostdoo.command.custom
         *   record|{model}|{id}    → open record form view
         */
        function _resolveKeyAction(key) {
            if (!key) return () => {};

            if (key.startsWith("menu_")) {
                const menuId = parseInt(key.slice(5), 10);
                return () => {
                    const found = _findMenuById(menuId, menu.getApps());
                    if (found) menu.selectMenu(found);
                };
            }

            if (key.startsWith("custom_")) {
                const cmdId = parseInt(key.slice(7), 10);
                return () => {
                    const cached = cache.get("boostdoo_custom_commands") || [];
                    const cmd = cached.find((c) => c.id === cmdId);
                    if (cmd && cmd.action_id) actionService.doAction(cmd.action_id[0]);
                };
            }

            if (key.startsWith("record|")) {
                const [, model, rawId] = key.split("|");
                const resId = parseInt(rawId, 10);
                return () => actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: model,
                    res_id: resId,
                    views: [[false, "form"]],
                    target: "current",
                });
            }

            return () => {};
        }

        /** Recursive lookup of a menu item by id. */
        function _findMenuById(id, items) {
            for (const item of items || []) {
                if (item.id === id) return item;
                const found = _findMenuById(id, item.childrenTree);
                if (found) return found;
            }
            return null;
        }

        // ─── Source builders ────────────────────────────────────────────────────

        /**
         * Flatten all menus (apps + children) into a searchable list.
         * Apps themselves are included so typing "Accounting" finds the app.
         */
        function _menuResults(query) {
            function flatten(items, parentName) {
                return (items || []).flatMap((item) => [
                    {
                        id: `menu_${item.id}`,
                        name: item.name,
                        description: parentName || "App",
                        category: "menu",
                        action: () => menu.selectMenu(item),
                    },
                    ...flatten(item.childrenTree, item.name),
                ]);
            }
            return fuzzyFilter(query, flatten(menu.getApps()), (r) => r.name);
        }

        async function _customResults(query, allCustom) {
            return fuzzyFilter(
                query,
                allCustom.map((cmd) => ({
                    id: `custom_${cmd.id}`,
                    name: cmd.name,
                    description: cmd.description || (cmd.action_id && cmd.action_id[1]) || "",
                    category: "custom",
                    action: () => {
                        if (cmd.action_id) actionService.doAction(cmd.action_id[0]);
                        orm.call("boostdoo.command.history", "record_usage", [], {
                            command_key: `custom_${cmd.id}`,
                            command_name: cmd.name,
                        }).catch(() => {});
                        cache.invalidate("boostdoo_history");
                    },
                })),
                (r) => r.name
            );
        }

        /**
         * Search actual Odoo records via name_search.
         * Each model is searched in parallel; failures are silently ignored.
         * Only triggered when query length >= 2 to avoid noise.
         */
        async function _recordResults(query) {
            if (!query || query.trim().length < 2) return [];

            const settled = await Promise.allSettled(
                SEARCHABLE_MODELS.map(async (spec) => {
                    const records = await orm.call(spec.model, "name_search", [], {
                        name: query.trim(),
                        limit: 3,
                    });
                    return records.map(([id, name]) => ({
                        id: `record|${spec.model}|${id}`,
                        name,
                        description: spec.label,
                        category: "record",
                        action: () => {
                            actionService.doAction({
                                type: "ir.actions.act_window",
                                res_model: spec.model,
                                res_id: id,
                                views: [[false, "form"]],
                                target: "current",
                            });
                            orm.call("boostdoo.command.history", "record_usage", [], {
                                command_key: `record|${spec.model}|${id}`,
                                command_name: `${spec.label}: ${name}`,
                            }).catch(() => {});
                            cache.invalidate("boostdoo_history");
                        },
                    }));
                })
            );

            return settled
                .filter((r) => r.status === "fulfilled")
                .flatMap((r) => r.value);
        }

        // ─── Public API ─────────────────────────────────────────────────────────

        async function search(query, maxResults = 10) {
            const [customCommands, history, favorites, recordResults] = await Promise.all([
                _loadCustomCommands(),
                _loadHistory(),
                _loadFavorites(),
                _recordResults(query),
            ]);

            // Deduplication by id — first occurrence wins
            const seen = new Set();
            function dedup(results) {
                return results.filter((r) => {
                    if (seen.has(r.id)) return false;
                    seen.add(r.id);
                    return true;
                });
            }

            // Priority order: favorites → history → records → menus → custom
            const allResults = [
                ...dedup(
                    favorites
                        .filter((f) => !query || f.name.toLowerCase().includes(query.toLowerCase()))
                        .map((f) => ({
                            id: `fav_${f.command_key}`,
                            name: f.name,
                            description: "⭐ Favorite",
                            category: "favorite",
                            action: _resolveKeyAction(f.command_key),
                        }))
                ),
                ...dedup(
                    history
                        .filter((h) => !query || h.command_name.toLowerCase().includes(query.toLowerCase()))
                        .map((h) => ({
                            id: `hist_${h.command_key}`,
                            name: h.command_name,
                            description: `🕒 ${h.use_count}×`,
                            category: "history",
                            action: _resolveKeyAction(h.command_key),
                        }))
                ),
                ...dedup(recordResults),
                ...dedup(_menuResults(query)),
                ...dedup(await _customResults(query, customCommands)),
            ];

            return allResults.slice(0, maxResults);
        }

        function invalidateCache() {
            cache.invalidate("boostdoo_custom_commands");
            cache.invalidate("boostdoo_history");
            cache.invalidate("boostdoo_favorites");
        }

        return { search, invalidateCache };
    },
};

registry.category("services").add(SEARCH_SERVICE_NAME, boostdooSearchService);
