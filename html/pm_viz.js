/* Pisces Moon OS - pm_viz.js
 * Lightweight visualization library for the cybersec/intel apps.
 * Copyright (C) 2026 Eric Becker / Fluid Fortune
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Provides PMViz global with:
 *   - PMViz.C            - color palette constants
 *   - PMViz.rssiColor    - RSSI to color mapping
 *   - PMViz.Storage      - WiGLE CSV + auto-save helpers
 *   - PMViz.Sparkline    - small inline trend graphs
 *   - PMViz.BarChart     - vertical bar charts
 *   - PMViz.DonutChart   - circular distribution charts
 *   - PMViz.RSSIWaterfall - rolling RSSI strength heatmap
 *   - PMViz.LiveMap      - Leaflet map wrapper for live markers
 *   - PMViz.GaugeArc     - semicircle gauge
 *   - PMViz.BubbleScatter - bubble scatter plot
 *
 * No external deps except Leaflet (for LiveMap, optional).
 * All drawing uses native HTML5 Canvas / SVG / DOM.
 */

(function() {
'use strict';

const PMViz = {};

// ── COLOR PALETTE ─────────────────────────────────────────────
PMViz.C = {
    bg:      '#020608',
    bg2:     '#040c10',
    bg3:     '#071018',
    panel:   '#0a1520',
    border:  '#0f2535',

    accent:  '#00d4ff',  // cyan - primary data
    accent2: '#ff6b00',  // orange - secondary
    accent3: '#00ff88',  // green - good signal / online
    accent4: '#ff3366',  // red - threat / weak signal
    warn:    '#ffcc00',
    gold:    '#f4a820',
    purple:  '#a855f7',

    text:       '#7ab8d4',
    textBright: '#e8f6ff',
    textDim:    '#1e4a62',
    textMid:    '#4a7a92',
};

// ── RSSI COLOR MAPPING ────────────────────────────────────────
PMViz.rssiColor = function(rssi) {
    if (rssi >= -50) return PMViz.C.accent3;   // green - excellent
    if (rssi >= -65) return PMViz.C.gold;      // gold - good
    if (rssi >= -75) return PMViz.C.warn;      // yellow - fair
    if (rssi >= -85) return PMViz.C.accent2;   // orange - poor
    return PMViz.C.accent4;                    // red - very poor
};

PMViz.rssiQuality = function(rssi) {
    if (rssi >= -50) return 'excellent';
    if (rssi >= -65) return 'good';
    if (rssi >= -75) return 'fair';
    if (rssi >= -85) return 'poor';
    return 'very poor';
};

// ── STORAGE - WiGLE CSV + auto-save ──────────────────────────
PMViz.Storage = {
    toWigleCSV(networks) {
        const h1 = 'WigleWifi-1.4,appRelease=PiscesMoon,model=Web,'
                 + 'release=v0.5,device=PMOS,display=PMOS,board=PMOS,'
                 + 'brand=FluidFortune,star=Sol,body=Earth,subBody=0';
        const h2 = 'MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,'
                 + 'CurrentLatitude,CurrentLongitude,AltitudeMeters,'
                 + 'AccuracyMeters,Type';
        const rows = (networks || []).map(n => {
            const ts = new Date(n.firstSeen || n.lastSeen || Date.now())
                .toISOString().replace('T', ' ').slice(0, 19);
            const ssid = (n.ssid || '').replace(/,/g, '_').replace(/\n/g, ' ');
            const sec  = n.security || n.sec || (n.enc ? 'WPA' : 'OPEN') || 'UNKNOWN';
            return [
                n.bssid || n.mac || '',
                ssid,
                '[' + sec + ']',
                ts,
                n.channel || n.ch || 0,
                n.bestRSSI || n.rssi || -100,
                (n.lat || 0).toFixed(6),
                (n.lon || n.lng || 0).toFixed(6),
                (n.alt || n.alt_m || 0).toFixed(1),
                5,
                n.type === 'ble' ? 'BLE' : 'WIFI'
            ].join(',');
        });
        return [h1, h2, ...rows].join('\n');
    },

    save(prefix, content, ext) {
        const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = (prefix || 'pmos') + '_' + stamp + '.' + (ext || 'csv');
        const mime = ext === 'csv'  ? 'text/csv' :
                     ext === 'json' ? 'application/json' :
                     'text/plain';
        const blob = new Blob([content], { type: mime });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
        return filename;
    },

    autoSave(prefix, getContentFn, intervalSec, ext) {
        const id = setInterval(() => {
            try {
                const content = getContentFn();
                if (content) PMViz.Storage.save(prefix + '_auto', content, ext);
            } catch (e) {
                console.warn('AutoSave failed:', e);
            }
        }, (intervalSec || 60) * 1000);
        return id;
    },
};

// ── SPARKLINE - small inline trend graph ────────────────────
PMViz.Sparkline = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) { console.warn('Sparkline target not found'); return; }
        this.maxPoints  = opts.maxPoints  || 50;
        this.color      = opts.color      || PMViz.C.accent;
        this.colorFn    = opts.colorFn    || null;
        this.height     = opts.height     || 36;
        this.fill       = opts.fill !== false;
        this.data       = [];
        this._setup();
    }
    _setup() {
        this.el.style.position = 'relative';
        this.el.style.height = this.height + 'px';
        this.canvas = document.createElement('canvas');
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.display = 'block';
        this.el.innerHTML = '';
        this.el.appendChild(this.canvas);
        this._resize();
        window.addEventListener('resize', () => this._resize());
    }
    _resize() {
        if (!this.canvas) return;
        const r = this.el.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width  = r.width * dpr;
        this.canvas.height = r.height * dpr;
        this.ctx = this.canvas.getContext('2d');
        this.ctx.scale(dpr, dpr);
        this._draw();
    }
    push(value) {
        this.data.push(value);
        if (this.data.length > this.maxPoints) this.data.shift();
        this._draw();
    }
    set(values) {
        this.data = values.slice(-this.maxPoints);
        this._draw();
    }
    _draw() {
        if (!this.ctx || !this.data.length) return;
        const w = this.el.clientWidth, h = this.el.clientHeight;
        this.ctx.clearRect(0, 0, w, h);
        const min = Math.min(...this.data), max = Math.max(...this.data);
        const range = (max - min) || 1;
        const stepX = w / Math.max(1, this.data.length - 1);
        this.ctx.lineWidth = 1.5;
        this.ctx.strokeStyle = this.color;
        this.ctx.beginPath();
        this.data.forEach((v, i) => {
            const x = i * stepX;
            const y = h - ((v - min) / range) * (h - 2) - 1;
            if (i === 0) this.ctx.moveTo(x, y);
            else this.ctx.lineTo(x, y);
        });
        this.ctx.stroke();
        if (this.fill) {
            this.ctx.lineTo(w, h);
            this.ctx.lineTo(0, h);
            this.ctx.closePath();
            const grad = this.ctx.createLinearGradient(0, 0, 0, h);
            grad.addColorStop(0, this.color + '40');
            grad.addColorStop(1, this.color + '00');
            this.ctx.fillStyle = grad;
            this.ctx.fill();
        }
    }
    clear() { this.data = []; this._draw(); }
};

// ── BAR CHART - vertical bars ─────────────────────────────────
PMViz.BarChart = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) { console.warn('BarChart target not found'); return; }
        this.color   = opts.color   || PMViz.C.accent;
        this.colorFn = opts.colorFn || null;
        this.height  = opts.height  || 120;
        this.showLabels = opts.showLabels !== false;
        this.data    = [];
        this.el.style.height = this.height + 'px';
        this.el.style.display = 'flex';
        this.el.style.alignItems = 'flex-end';
        this.el.style.gap = '2px';
        this.el.style.padding = '4px';
    }
    set(items) {
        this.data = items;
        this._render();
    }
    _render() {
        if (!this.data.length) {
            this.el.innerHTML = '';
            return;
        }
        const max = Math.max(...this.data.map(d => d.value));
        this.el.innerHTML = this.data.map(d => {
            const pct = max ? (d.value / max) * 100 : 0;
            const c = this.colorFn ? this.colorFn(d) : this.color;
            return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0">' +
                '<div title="' + (d.label || '') + ': ' + d.value + '" style="' +
                  'width:100%;height:' + pct + '%;' +
                  'background:linear-gradient(180deg,' + c + ',' + c + '40);' +
                  'border-top:1px solid ' + c + ';' +
                  'min-height:2px;border-radius:1px"></div>' +
                (this.showLabels ?
                  '<div style="font-size:.45rem;color:var(--text-dim);margin-top:3px;font-family:DM Mono,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:100%;text-align:center">' +
                    (d.label || '') + '</div>' : '') +
                '</div>';
        }).join('');
    }
    clear() { this.data = []; this.el.innerHTML = ''; }
};

// ── DONUT CHART - circular distribution ─────────────────────
PMViz.DonutChart = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) { console.warn('DonutChart target not found'); return; }
        this.size      = opts.size      || 120;
        this.thickness = opts.thickness || 14;
        this.colors    = opts.colors    ||
            [PMViz.C.accent, PMViz.C.accent3, PMViz.C.gold,
             PMViz.C.accent2, PMViz.C.accent4, PMViz.C.purple,
             PMViz.C.warn];
        this.data = [];
    }
    set(items) {
        this.data = items;
        this._render();
    }
    _render() {
        const total = this.data.reduce((s, d) => s + d.value, 0);
        if (!total) { this.el.innerHTML = ''; return; }
        const cx = this.size / 2, cy = this.size / 2;
        const r = (this.size - this.thickness) / 2;
        let angle = -Math.PI / 2;

        const arcs = this.data.map((d, i) => {
            const frac = d.value / total;
            const a2 = angle + frac * Math.PI * 2;
            const x1 = cx + r * Math.cos(angle), y1 = cy + r * Math.sin(angle);
            const x2 = cx + r * Math.cos(a2),   y2 = cy + r * Math.sin(a2);
            const large = frac > 0.5 ? 1 : 0;
            const path = `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
            const color = d.color || this.colors[i % this.colors.length];
            angle = a2;
            return `<path d="${path}" stroke="${color}" stroke-width="${this.thickness}" fill="none" stroke-linecap="butt"/>`;
        }).join('');

        const legend = this.data.map((d, i) => {
            const color = d.color || this.colors[i % this.colors.length];
            const pct   = ((d.value / total) * 100).toFixed(0);
            return `<div style="display:flex;align-items:center;gap:6px;font-size:.55rem;font-family:DM Mono,monospace;color:var(--text)">
              <div style="width:10px;height:10px;background:${color};border-radius:2px"></div>
              <span style="color:var(--text-bright)">${d.label}</span>
              <span style="margin-left:auto;color:var(--text-dim)">${d.value} (${pct}%)</span>
            </div>`;
        }).join('');

        this.el.innerHTML = `
          <div style="display:flex;align-items:center;gap:14px">
            <svg width="${this.size}" height="${this.size}" viewBox="0 0 ${this.size} ${this.size}">${arcs}</svg>
            <div style="flex:1;display:flex;flex-direction:column;gap:5px">${legend}</div>
          </div>`;
    }
    clear() { this.data = []; this.el.innerHTML = ''; }
};

// ── RSSI WATERFALL - rolling heatmap ─────────────────────────
PMViz.RSSIWaterfall = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) { console.warn('RSSIWaterfall target not found'); return; }
        this.channels = opts.channels || 14;
        this.history  = opts.history  || 60;
        this.height   = opts.height   || 140;
        this.grid     = [];
        for (let i = 0; i < this.history; i++) {
            this.grid.push(new Array(this.channels).fill(-100));
        }
        this._setup();
    }
    _setup() {
        this.el.style.height = this.height + 'px';
        this.canvas = document.createElement('canvas');
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.display = 'block';
        this.el.innerHTML = '';
        this.el.appendChild(this.canvas);
        this._resize();
        window.addEventListener('resize', () => this._resize());
    }
    _resize() {
        const r = this.el.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width  = r.width * dpr;
        this.canvas.height = r.height * dpr;
        this.ctx = this.canvas.getContext('2d');
        this.ctx.scale(dpr, dpr);
        this._draw();
    }
    push(channelData) {
        // channelData: {channel: rssi, ...}
        const row = new Array(this.channels).fill(-100);
        Object.entries(channelData || {}).forEach(([ch, rssi]) => {
            const i = parseInt(ch) - 1;
            if (i >= 0 && i < this.channels) row[i] = rssi;
        });
        this.grid.push(row);
        while (this.grid.length > this.history) this.grid.shift();
        this._draw();
    }
    _draw() {
        if (!this.ctx) return;
        const w = this.el.clientWidth, h = this.el.clientHeight;
        this.ctx.clearRect(0, 0, w, h);
        const cellW = w / this.channels;
        const cellH = h / this.history;
        for (let y = 0; y < this.grid.length; y++) {
            for (let x = 0; x < this.channels; x++) {
                const rssi = this.grid[y][x];
                if (rssi <= -100) continue;
                const intensity = Math.max(0, Math.min(1, (rssi + 100) / 70));
                this.ctx.fillStyle = PMViz.rssiColor(rssi);
                this.ctx.globalAlpha = intensity * 0.9;
                this.ctx.fillRect(x * cellW, (this.history - y - 1) * cellH, cellW, cellH);
            }
        }
        this.ctx.globalAlpha = 1;
    }
    clear() {
        this.grid = [];
        for (let i = 0; i < this.history; i++)
            this.grid.push(new Array(this.channels).fill(-100));
        this._draw();
    }
};

// ── LIVE MAP - Leaflet wrapper ────────────────────────────────
PMViz.LiveMap = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) { console.warn('LiveMap target not found'); return; }
        this.markers = {};
        if (typeof L === 'undefined') {
            console.warn('Leaflet not loaded - LiveMap disabled');
            this.el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-dim);font-size:.6rem;font-family:DM Mono,monospace">Leaflet not available</div>';
            return;
        }
        this.map = L.map(this.el, {
            zoomControl: opts.zoomControl !== false,
            attributionControl: false,
        }).setView(opts.center || [34.05, -117.75], opts.zoom || 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
        }).addTo(this.map);
    }
    upsert(id, lat, lon, rssi, label, type) {
        if (!this.map) return;
        if (!lat || !lon) return;
        const color = PMViz.rssiColor(rssi || -80);
        if (this.markers[id]) {
            this.markers[id].setLatLng([lat, lon]);
            this.markers[id].setStyle({ color, fillColor: color });
        } else {
            this.markers[id] = L.circleMarker([lat, lon], {
                radius: type === 'ble' ? 4 : 6,
                color, fillColor: color, fillOpacity: 0.6, weight: 1.5,
            }).addTo(this.map).bindPopup(label || id);
        }
    }
    clear() {
        if (!this.map) return;
        Object.values(this.markers).forEach(m => this.map.removeLayer(m));
        this.markers = {};
    }
    updateGPS(lat, lon) {
        if (!this.map || !lat || !lon) return;
        // Add or update a "you are here" marker
        if (!this.gpsMarker) {
            this.gpsMarker = L.circleMarker([lat, lon], {
                radius: 8,
                color: '#00d4ff',
                fillColor: '#00d4ff',
                fillOpacity: 0.9,
                weight: 2,
            }).addTo(this.map).bindPopup('You are here');
        } else {
            this.gpsMarker.setLatLng([lat, lon]);
        }
        // Pan map to follow GPS unless explicitly disabled
        if (this.track !== false) {
            this.map.panTo([lat, lon], { animate: true, duration: 0.5 });
        }
    }
};

// ── GAUGE ARC - semicircle gauge ─────────────────────────────
PMViz.GaugeArc = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) return;
        this.min   = opts.min   || 0;
        this.max   = opts.max   || 100;
        this.size  = opts.size  || 120;
        this.color = opts.color || PMViz.C.accent;
        this.label = opts.label || '';
        this.value = 0;
        this._render();
    }
    set(value) { this.value = value; this._render(); }
    _render() {
        const range = this.max - this.min;
        const frac  = Math.max(0, Math.min(1, (this.value - this.min) / range));
        const a1 = Math.PI, a2 = a1 + Math.PI * frac;
        const cx = this.size / 2, cy = this.size * 0.7;
        const r = this.size * 0.4;
        const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
        const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
        const path = `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
        this.el.innerHTML = `
          <svg width="${this.size}" height="${this.size * 0.85}" viewBox="0 0 ${this.size} ${this.size * 0.85}">
            <path d="M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}"
                  stroke="${PMViz.C.border}" stroke-width="8" fill="none"/>
            <path d="${path}" stroke="${this.color}" stroke-width="8" fill="none" stroke-linecap="round"/>
            <text x="${cx}" y="${cy + 4}" text-anchor="middle" fill="${PMViz.C.textBright}"
                  font-family="Orbitron" font-weight="700" font-size="${this.size * 0.16}">${this.value}</text>
            <text x="${cx}" y="${cy + this.size * 0.16}" text-anchor="middle" fill="${PMViz.C.textDim}"
                  font-family="DM Mono" font-size="${this.size * 0.07}" letter-spacing="2">${this.label}</text>
          </svg>`;
    }
};

// ── BUBBLE SCATTER ────────────────────────────────────────────
PMViz.BubbleScatter = class {
    constructor(target, opts) {
        opts = opts || {};
        this.el = typeof target === 'string'
            ? document.getElementById(target) : target;
        if (!this.el) return;
        this.height = opts.height || 200;
        this.data = [];
        this.el.style.height = this.height + 'px';
        this.el.style.position = 'relative';
        this.el.style.background = PMViz.C.bg2;
        this.el.style.border = '1px solid ' + PMViz.C.border;
        this.el.style.borderRadius = '4px';
    }
    set(points) {
        this.data = points;
        this._render();
    }
    upsert(id, x, y, label) {
        // x typically RSSI, y is just an offset (we'll auto-spread vertically)
        const existing = this.data.findIndex(p => p.id === id);
        // Color based on RSSI strength (x value used as RSSI)
        const color = PMViz.rssiColor(x);
        const r = Math.max(3, Math.min(12, (x + 100) / 8));
        const point = {
            id,
            x: x,                                       // RSSI as x position
            y: existing >= 0 ? this.data[existing].y    // keep existing y
                              : Math.random() * 100,    // or assign random
            r,
            color,
            label,
        };
        if (existing >= 0) this.data[existing] = point;
        else this.data.push(point);
        this._render();
    }
    remove(id) {
        this.data = this.data.filter(p => p.id !== id);
        this._render();
    }
    _render() {
        if (!this.data.length) { this.el.innerHTML = ''; return; }
        const xs = this.data.map(p => p.x), ys = this.data.map(p => p.y);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const w = this.el.clientWidth, h = this.el.clientHeight;
        const rangeX = (maxX - minX) || 1, rangeY = (maxY - minY) || 1;
        this.el.innerHTML = this.data.map(p => {
            const px = ((p.x - minX) / rangeX) * (w - 30) + 15;
            const py = h - (((p.y - minY) / rangeY) * (h - 30) + 15);
            const r = p.r || 4;
            const c = p.color || PMViz.C.accent;
            return `<div title="${(p.label||'').replace(/"/g,'&quot;')}"
                      style="position:absolute;left:${px-r}px;top:${py-r}px;width:${r*2}px;height:${r*2}px;
                             background:${c};border-radius:50%;opacity:.7;
                             box-shadow:0 0 ${r*2}px ${c}40;cursor:pointer"></div>`;
        }).join('');
    }
};

// ── EXPORT ────────────────────────────────────────────────────
window.PMViz = PMViz;
})();
