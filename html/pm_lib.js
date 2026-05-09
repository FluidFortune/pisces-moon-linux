/* Pisces Moon OS - pm_lib.js
 * Shared utility library used across the app suite.
 * Copyright (C) 2026 Eric Becker / Fluid Fortune
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Provides the global PM object that apps reference for:
 *   - HTML escaping
 *   - localStorage helpers
 *   - Time formatting
 *   - RSS/feed fetching with CORS fallbacks
 *   - Gemini AI calls
 *   - Generic helpers (uid, ago, etc.)
 *
 * Load before any app-specific scripts:
 *   <script src="pm_lib.js"></script>
 */

(function() {
'use strict';

const PM = {};

// ── HTML ESCAPING ─────────────────────────────────────────────
PM.esc = function(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
};

// ── LOCALSTORAGE WRAPPERS ─────────────────────────────────────
// Namespaced under "pm_" prefix to avoid clashes with other code
PM.save = function(key, value) {
    try {
        const k = 'pm_' + key;
        const v = typeof value === 'string' ? value : JSON.stringify(value);
        localStorage.setItem(k, v);
        return true;
    } catch (e) {
        console.warn('PM.save failed:', e);
        return false;
    }
};

PM.load = function(key, fallback) {
    try {
        const v = localStorage.getItem('pm_' + key);
        if (v == null) return fallback === undefined ? null : fallback;
        // Try JSON parse, fall back to raw string
        try { return JSON.parse(v); }
        catch (e) { return v; }
    } catch (e) {
        return fallback === undefined ? null : fallback;
    }
};

PM.remove = function(key) {
    try { localStorage.removeItem('pm_' + key); return true; }
    catch (e) { return false; }
};

// ── UNIQUE ID GENERATION ──────────────────────────────────────
PM.uid = function(prefix) {
    const id = (prefix || 'id') + '_' + Date.now() + '_' +
               Math.random().toString(36).substring(2, 9);
    return id;
};

// ── TIME FORMATTING ───────────────────────────────────────────
PM.ago = function(timestamp) {
    if (!timestamp) return 'never';
    const ms = Date.now() - (typeof timestamp === 'number' ? timestamp : new Date(timestamp).getTime());
    if (isNaN(ms)) return 'unknown';
    const s = Math.floor(ms / 1000);
    if (s < 5)      return 'just now';
    if (s < 60)     return s + 's ago';
    const m = Math.floor(s / 60);
    if (m < 60)     return m + 'm ago';
    const h = Math.floor(m / 60);
    if (h < 24)     return h + 'h ago';
    const d = Math.floor(h / 24);
    if (d < 7)      return d + 'd ago';
    const w = Math.floor(d / 7);
    if (w < 5)      return w + 'w ago';
    const mo = Math.floor(d / 30);
    if (mo < 12)    return mo + 'mo ago';
    return Math.floor(d / 365) + 'y ago';
};

PM.formatTime = function(timestamp) {
    if (!timestamp) return '';
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return '';
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return hh + ':' + mm;
};

PM.formatDuration = function(ms) {
    if (!ms || isNaN(ms)) return '0s';
    const s = Math.floor(ms / 1000);
    if (s < 60)   return s + 's';
    if (s < 3600) return Math.floor(s/60) + 'm ' + (s%60) + 's';
    return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
};

// ── RSSI QUALITY ──────────────────────────────────────────────
PM.rssiQuality = function(rssi) {
    if (rssi >= -50) return 'excellent';
    if (rssi >= -65) return 'good';
    if (rssi >= -75) return 'fair';
    if (rssi >= -85) return 'poor';
    return 'very poor';
};

// ── FETCH WITH TIMEOUT ────────────────────────────────────────
PM.fetchWithTimeout = function(url, options, timeoutMs) {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), timeoutMs || 15000);
    return fetch(url, Object.assign({}, options || {}, {
        signal: controller.signal,
    })).finally(() => clearTimeout(tid));
};

// ── CORS PROXIES (fallback chain for feed fetching) ──────────
// Note: these are public proxies - rate limited but useful when
// running from file:// where direct fetches are blocked.
PM.CORS_PROXIES = [
    '',  // try direct first
    'https://corsproxy.io/?',
    'https://api.codetabs.com/v1/proxy?quest=',
    'https://api.allorigins.win/raw?url=',
];

// ── FEED FETCHING (RSS, JSON) ─────────────────────────────────
PM.fetchFeeds = async function(urls, parser, opts) {
    opts = opts || {};
    const results = [];
    for (const url of urls) {
        const item = await PM._tryFetch(url, opts.timeout);
        if (item) {
            try {
                const parsed = parser ? parser(item, url) : item;
                if (Array.isArray(parsed))      results.push(...parsed);
                else if (parsed)                results.push(parsed);
            } catch (e) {
                console.warn('Feed parse failed for', url, e);
            }
        }
    }
    return results;
};

PM._tryFetch = async function(url, timeoutMs) {
    for (const proxy of PM.CORS_PROXIES) {
        try {
            const target = proxy ? proxy + encodeURIComponent(url) : url;
            const resp = await PM.fetchWithTimeout(target, {}, timeoutMs || 15000);
            if (!resp.ok) continue;
            const text = await resp.text();
            if (text && text.length > 50) return text;
        } catch (e) {
            // try next proxy
        }
    }
    return null;
};

// ── ERROR RENDERING ───────────────────────────────────────────
PM.renderError = function(container, message, hint) {
    const el = typeof container === 'string'
        ? document.getElementById(container)
        : container;
    if (!el) return;
    el.innerHTML =
        '<div style="padding:30px 20px;text-align:center;font-family:Share Tech Mono,monospace">' +
            '<div style="font-size:1.4rem;color:var(--accent4);margin-bottom:12px">⚠ ERROR</div>' +
            '<div style="font-size:.7rem;color:var(--text-bright);margin-bottom:8px">' +
                PM.esc(message || 'Something went wrong') +
            '</div>' +
            (hint ? '<div style="font-size:.6rem;color:var(--text-dim);margin-top:10px">' + PM.esc(hint) + '</div>' : '') +
        '</div>';
};

// ── GEMINI AI CALLS ───────────────────────────────────────────
// API key stored locally - never transmitted except to Google's API
// Read from localStorage. User configures via Gemini settings.
PM.gemini = async function(prompt, opts) {
    opts = opts || {};
    const key = PM.load('gemini_key', null) || PM.load('pm_gemini_key', null) || PM.load('gemini_api_key', null);
    if (!key) {
        throw new Error('Gemini API key not configured. Set it in Gemini Terminal settings.');
    }

    const model = opts.model || 'gemini-2.5-flash';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;

    const body = {
        contents: [{
            role: 'user',
            parts: [{ text: prompt }],
        }],
        generationConfig: {
            temperature:     opts.temperature || 0.7,
            maxOutputTokens: opts.maxTokens   || 2048,
        },
    };

    const resp = await PM.fetchWithTimeout(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }, opts.timeout || 30000);

    if (!resp.ok) {
        const errText = await resp.text().catch(() => '');
        throw new Error('Gemini API error: ' + resp.status + ' - ' + errText.substring(0, 200));
    }

    const data = await resp.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Empty Gemini response');
    return text;
};

// ── EXPORT ────────────────────────────────────────────────────
window.PM = PM;
})();
