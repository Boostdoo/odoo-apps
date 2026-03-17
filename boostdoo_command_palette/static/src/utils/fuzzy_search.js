/** @odoo-module **/
// Copyright 2026 Boostdoo

/**
 * Fuzzy search utilities for the Boostdoo Command Palette.
 *
 * Provides lightweight string matching that tolerates typos and partial input,
 * similar to VS Code's command palette behaviour.
 */

/**
 * Compute the Levenshtein edit distance between two strings.
 *
 * @param {string} a
 * @param {string} b
 * @returns {number}
 */
export function levenshteinDistance(a, b) {
    const m = a.length;
    const n = b.length;
    // dp[i][j] = edit distance between a[0..i-1] and b[0..j-1]
    const dp = Array.from({ length: m + 1 }, (_, i) =>
        Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
    );
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (a[i - 1] === b[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
            }
        }
    }
    return dp[m][n];
}

/**
 * Compute a similarity score between query and target in [0, 1].
 *
 * Score of 1 means exact match; 0 means completely different.
 *
 * @param {string} query
 * @param {string} target
 * @returns {number}
 */
export function similarityScore(query, target) {
    if (!query || !target) return 0;
    const q = query.toLowerCase();
    const t = target.toLowerCase();
    if (t.includes(q)) return 1; // substring match always wins
    const maxLen = Math.max(q.length, t.length);
    if (maxLen === 0) return 1;
    const dist = levenshteinDistance(q, t);
    return 1 - dist / maxLen;
}

/**
 * Return true when the query passes the fuzzy threshold against the target.
 *
 * @param {string} query
 * @param {string} target
 * @param {number} [threshold=0.4]
 * @returns {boolean}
 */
export function fuzzyMatch(query, target, threshold = 0.4) {
    return similarityScore(query, target) >= threshold;
}

/**
 * Filter and rank a list of items by fuzzy relevance.
 *
 * @param {string}   query       Search query typed by the user.
 * @param {Array}    items       Items to filter.
 * @param {Function} getLabel    Extracts the text to match from each item.
 * @param {number}   [threshold] Minimum score to include an item (0–1).
 * @returns {Array}  Sorted by descending relevance score.
 */
export function fuzzyFilter(query, items, getLabel, threshold = 0.4) {
    if (!query || !query.trim()) return items;
    return items
        .map((item) => ({ item, score: similarityScore(query.trim(), getLabel(item)) }))
        .filter(({ score }) => score >= threshold)
        .sort((a, b) => b.score - a.score)
        .map(({ item }) => item);
}
