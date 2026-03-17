/** @odoo-module **/
// Copyright 2026 Boostdoo

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/** Debounce helper — delays fn by `wait` ms, cancels previous pending call. */
function debounce(fn, wait) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), wait);
    };
}

/**
 * BoostdooCommandPalette
 *
 * OWL component that renders the Boostdoo Command Palette overlay.
 * It wraps the native Odoo 18 command experience by:
 *   - Intercepting the configured keyboard shortcut (default: ctrl+k)
 *   - Fetching unified results via boostdoo_search_service
 *   - Displaying results with category badges (favorite / history / menu / custom)
 *   - Recording usage via boostdoo_command_service
 */

export class BoostdooCommandPalette extends Component {
    static template = "boostdoo_command_palette.CommandPaletteExtension";
    static props = {};

    setup() {
        this.searchService = useService("boostdoo_search_service");
        this.commandService = useService("boostdoo_command_service");
        this.orm = useService("orm");

        this.inputRef = useRef("input");

        this.state = useState({
            open: false,
            query: "",
            results: [],
            selectedIndex: 0,
            loading: false,
        });

        // Debounce search input to avoid firing an RPC on every keystroke
        this._debouncedFetch = debounce((query) => this._fetchResults(query), 180);

        // Bind keyboard handlers
        this._onKeyDown = this._onKeyDown.bind(this);
        this._onGlobalKeyDown = this._onGlobalKeyDown.bind(this);

        onMounted(() => {
            // capture:true so ctrl+k is caught before Odoo's own handlers
            document.addEventListener("keydown", this._onGlobalKeyDown, { capture: true });
        });

        onWillUnmount(() => {
            document.removeEventListener("keydown", this._onGlobalKeyDown, { capture: true });
        });
    }

    // ── Keyboard handling ───────────────────────────────────────────────────

    /** Listen globally for the palette trigger shortcut. */
    _onGlobalKeyDown(ev) {
        // ctrl+k (Windows/Linux) or cmd+k (Mac)
        if ((ev.ctrlKey || ev.metaKey) && ev.key === "k") {
            ev.preventDefault();
            this._togglePalette();
        }
    }

    /** Handle keyboard navigation inside the palette. */
    _onKeyDown(ev) {
        const { results, selectedIndex } = this.state;
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.state.selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.state.selectedIndex = Math.max(selectedIndex - 1, 0);
                break;
            case "Enter":
                ev.preventDefault();
                if (results[selectedIndex]) {
                    this._executeResult(results[selectedIndex]);
                }
                break;
            case "Escape":
                ev.preventDefault();
                this._closePalette();
                break;
        }
    }

    // ── Palette lifecycle ───────────────────────────────────────────────────

    _togglePalette() {
        if (this.state.open) {
            this._closePalette();
        } else {
            this._openPalette();
        }
    }

    async _openPalette() {
        this.state.open = true;
        this.state.query = "";
        this.state.selectedIndex = 0;
        await this._fetchResults("");
        // Focus input on next tick
        setTimeout(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        }, 0);
    }

    _closePalette() {
        this.state.open = false;
        this.state.query = "";
        this.state.results = [];
    }

    // ── Search ──────────────────────────────────────────────────────────────

    _onInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        this.state.selectedIndex = 0;
        this.state.loading = true;
        this._debouncedFetch(query);
    }

    async _fetchResults(query) {
        this.state.loading = true;
        try {
            const results = await this.searchService.search(query, 10);
            this.state.results = results;
        } catch (_e) {
            this.state.results = [];
        } finally {
            this.state.loading = false;
        }
    }

    // ── Execution ───────────────────────────────────────────────────────────

    _executeResult(result) {
        this._closePalette();
        if (typeof result.action === "function") {
            result.action();
        }
    }

    _onResultClick(result) {
        this._executeResult(result);
    }

    _onResultMouseEnter(index) {
        this.state.selectedIndex = index;
    }

    // ── Category label helper ───────────────────────────────────────────────

    get categoryLabels() {
        return {
            favorite: _t("Favorite"),
            history:  _t("Recent"),
            record:   _t("Record"),
            menu:     _t("Menu"),
            custom:   _t("Custom"),
        };
    }
}

// Register the component so it can be added to the main webclient.
registry.category("main_components").add("BoostdooCommandPalette", {
    Component: BoostdooCommandPalette,
});
