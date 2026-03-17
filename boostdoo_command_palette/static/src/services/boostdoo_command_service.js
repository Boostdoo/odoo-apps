/** @odoo-module **/
// Copyright 2026 Boostdoo

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const COMMAND_SERVICE_NAME = "boostdoo_command_service";
const CATEGORY_BOOSTDOO = "boostdoo";

/** Parse a shortcut string like "ctrl+shift+i" into a comparable object. */
function _parseShortcut(shortcut) {
    const parts = shortcut.toLowerCase().split("+").map((s) => s.trim());
    return {
        ctrl:  parts.includes("ctrl"),
        alt:   parts.includes("alt"),
        shift: parts.includes("shift"),
        meta:  parts.includes("cmd") || parts.includes("meta"),
        key:   parts.find((p) => !["ctrl", "alt", "shift", "cmd", "meta"].includes(p)) || "",
    };
}

/** Return true when a KeyboardEvent matches a parsed shortcut. */
function _matchesShortcut(ev, parsed) {
    return (
        !!ev.ctrlKey  === parsed.ctrl  &&
        !!ev.altKey   === parsed.alt   &&
        !!ev.shiftKey === parsed.shift &&
        !!ev.metaKey  === parsed.meta  &&
        ev.key.toLowerCase() === parsed.key
    );
}

/**
 * Return true only when the user is actively typing inside a real input.
 * Avoids blocking shortcuts when focus is on a non-editable Odoo container
 * (Odoo 18 marks many layout divs as contentEditable="false").
 */
function _isTypingTarget(el) {
    if (!el) return false;
    const tag = el.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    // Only skip when the element is truly editable, not just a container
    return el.isContentEditable && String(el.contentEditable) === "true";
}

export const boostdooCommandService = {
    dependencies: ["command", "boostdoo_search_service", "orm", "action"],

    start(env, { command: commandService, boostdoo_search_service: searchService, orm, action: actionService }) {

        // ── Register Boostdoo category ─────────────────────────────────────
        const commandCategoryRegistry = registry.category("command_categories");
        if (!commandCategoryRegistry.contains(CATEGORY_BOOSTDOO)) {
            commandCategoryRegistry.add(CATEGORY_BOOSTDOO, {
                name: _t("Boostdoo"),
                namespace: "/",
            });
        }

        // ── Shortcut registration ──────────────────────────────────────────

        /** Active keydown handler — replaced on each reload. */
        let _shortcutHandler = null;

        /**
         * Load all active custom commands that have a shortcut defined and
         * register a global keydown listener for each one.
         */
        async function _registerCustomShortcuts() {
            if (_shortcutHandler) {
                document.removeEventListener("keydown", _shortcutHandler, { capture: true });
                _shortcutHandler = null;
            }

            let commands = [];
            try {
                commands = await orm.searchRead(
                    "boostdoo.command.custom",
                    [
                        ["active", "=", true],
                        ["shortcut", "!=", false],
                        ["shortcut", "!=", ""],
                    ],
                    ["id", "name", "shortcut", "action_id"]
                );
            } catch (_e) {
                return; // Silently abort if the model is not yet installed.
            }

            const bound = commands
                .filter((cmd) => cmd.shortcut && cmd.action_id)
                .map((cmd) => ({ ...cmd, _parsed: _parseShortcut(cmd.shortcut) }));

            if (!bound.length) return;

            _shortcutHandler = (ev) => {
                // Skip when the user is actively typing in an input/editor
                if (_isTypingTarget(document.activeElement)) return;
                // Skip IME composition events
                if (ev.isComposing) return;
                for (const cmd of bound) {
                    if (_matchesShortcut(ev, cmd._parsed)) {
                        ev.preventDefault();
                        ev.stopPropagation();
                        actionService.doAction(cmd.action_id[0]);
                        orm.call("boostdoo.command.history", "record_usage", [], {
                            command_key: `custom_${cmd.id}`,
                            command_name: cmd.name,
                        }).catch(() => {});
                        break;
                    }
                }
            };

            // capture: true ensures we fire before Odoo's own keydown handlers
            document.addEventListener("keydown", _shortcutHandler, { capture: true });
        }

        // Register shortcuts on service start, then refresh every 60 s so newly
        // saved custom commands become active without a full page reload.
        _registerCustomShortcuts();
        setInterval(() => _registerCustomShortcuts(), 60_000);

        // ── Public API ─────────────────────────────────────────────────────

        async function getCommands(query, maxResults = 10) {
            const results = await searchService.search(query, maxResults);
            return results.map((r) => ({
                name: r.name,
                category: CATEGORY_BOOSTDOO,
                action: r.action,
                _boostdoo: {
                    id: r.id,
                    description: r.description,
                    category: r.category,
                },
            }));
        }

        function registerRuntimeCommand(cmd) {
            return commandService.add(cmd.name, cmd.action, {
                category: CATEGORY_BOOSTDOO,
            });
        }

        /**
         * Call this after saving/deleting a custom command so shortcuts
         * are immediately re-registered without a page reload.
         */
        function reloadShortcuts() {
            _registerCustomShortcuts();
        }

        return { getCommands, registerRuntimeCommand, reloadShortcuts };
    },
};

registry.category("services").add(COMMAND_SERVICE_NAME, boostdooCommandService);
