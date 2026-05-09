/*
 * Pisces Moon OS — pm_stats.js
 * Analysis engine for RF intelligence data.
 *
 * Copyright (C) 2026 Eric Becker / Fluid Fortune
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * USAGE:
 *   <script src="pm_stats.js"></script>
 *
 * Provides PMStats global with clinical analysis primitives:
 *   - PMStats.summary(records)          — descriptive statistics
 *   - PMStats.dbscan(points, eps, min)  — spatial clustering
 *   - PMStats.signalDecay(records, ref) — empirical RSSI decay curve
 *   - PMStats.anomalies(records)        — full anomaly detection
 *   - PMStats.diff(setA, setB)          — session comparison
 *   - PMStats.haversine(a, b)           — meters between GPS points
 *   - PMStats.timeline(records, bin)    — temporal bucketing
 *   - PMStats.persistence(records)      — device persistence scoring
 *   - PMStats.channelHealth(records)    — congestion analysis
 *   - PMStats.vendorMix(records)        — vendor diversity index
 *
 * All functions take an array of normalized record objects:
 *   { bssid, ssid, rssi, channel, band, enc, vendor, lat, lon,
 *     firstseen, lastseen, source, timestamp }
 */

(function() {
'use strict';

const PMStats = {};

// ── DESCRIPTIVE STATISTICS ──────────────────────────────────────
PMStats.summary = function(records) {
    if (!records || !records.length) return null;

    const r = records;
    const rssi = r.map(x => parseInt(x.rssi) || 0).filter(v => v < 0);
    const ch   = r.map(x => parseInt(x.channel) || 0).filter(Boolean);

    const ssids   = new Set(r.map(x => x.ssid).filter(Boolean));
    const bssids  = new Set(r.map(x => x.bssid).filter(Boolean));
    const vendors = new Set(r.map(x => x.vendor).filter(Boolean));

    return {
        count:       r.length,
        unique_ssids:   ssids.size,
        unique_bssids:  bssids.size,
        unique_vendors: vendors.size,
        unique_channels: new Set(ch).size,
        rssi: rssi.length ? {
            mean:   _mean(rssi),
            median: _median(rssi),
            stdev:  _stdev(rssi),
            min:    Math.min(...rssi),
            max:    Math.max(...rssi),
            p25:    _percentile(rssi, 25),
            p75:    _percentile(rssi, 75),
        } : null,
        bands: {
            '2.4ghz': r.filter(x => x.band === '2.4GHz' ||
                (parseInt(x.channel) > 0 && parseInt(x.channel) <= 14)).length,
            '5ghz': r.filter(x => x.band === '5GHz' ||
                (parseInt(x.channel) > 14)).length,
        },
        encryption: _countBy(r, 'enc'),
        gps_tagged: r.filter(x => x.lat && x.lon &&
            Math.abs(x.lat) > 0.001).length,
        open_count: r.filter(x => x.enc === 'OPEN').length,
        wep_count:  r.filter(x => x.enc === 'WEP').length,
        wpa3_count: r.filter(x => x.enc === 'WPA3').length,
    };
};

// ── DBSCAN SPATIAL CLUSTERING ────────────────────────────────────
// Groups GPS-tagged records into spatial clusters.
// eps: max distance in meters between points in same cluster (default 50)
// minPts: minimum points to form a cluster (default 3)
PMStats.dbscan = function(records, eps, minPts) {
    eps = eps || 50;
    minPts = minPts || 3;

    const points = records.filter(r =>
        r.lat && r.lon && Math.abs(r.lat) > 0.001);
    if (points.length < minPts) return { clusters: [], noise: points };

    const labels = new Array(points.length).fill(0);  // 0 = unvisited
    let clusterId = 0;

    function regionQuery(idx) {
        const neighbors = [];
        for (let i = 0; i < points.length; i++) {
            if (i === idx) continue;
            if (PMStats.haversine(
                {lat: points[idx].lat, lon: points[idx].lon},
                {lat: points[i].lat, lon: points[i].lon}
            ) <= eps) {
                neighbors.push(i);
            }
        }
        return neighbors;
    }

    function expandCluster(idx, neighbors, cId) {
        labels[idx] = cId;
        const queue = [...neighbors];
        while (queue.length) {
            const ni = queue.shift();
            if (labels[ni] === -1) labels[ni] = cId;
            if (labels[ni] !== 0) continue;
            labels[ni] = cId;
            const newN = regionQuery(ni);
            if (newN.length >= minPts) queue.push(...newN);
        }
    }

    for (let i = 0; i < points.length; i++) {
        if (labels[i] !== 0) continue;
        const neighbors = regionQuery(i);
        if (neighbors.length < minPts) {
            labels[i] = -1; // noise
            continue;
        }
        clusterId++;
        expandCluster(i, neighbors, clusterId);
    }

    // Build cluster objects
    const clusters = {};
    const noise = [];
    points.forEach((p, i) => {
        if (labels[i] === -1) {
            noise.push(p);
        } else {
            const c = labels[i];
            if (!clusters[c]) clusters[c] = { id: c, points: [] };
            clusters[c].points.push(p);
        }
    });

    // Compute centroid + bounds for each cluster
    Object.values(clusters).forEach(c => {
        const lats = c.points.map(p => parseFloat(p.lat));
        const lons = c.points.map(p => parseFloat(p.lon));
        const rssi = c.points.map(p => parseInt(p.rssi) || -80);
        c.centroid = {
            lat: _mean(lats),
            lon: _mean(lons),
        };
        c.bounds = {
            minLat: Math.min(...lats), maxLat: Math.max(...lats),
            minLon: Math.min(...lons), maxLon: Math.max(...lons),
        };
        c.size = c.points.length;
        c.avg_rssi = _mean(rssi);
        c.density_m2 = c.size / Math.max(1, _bboxArea(c.bounds));
    });

    return {
        clusters: Object.values(clusters).sort((a,b) => b.size - a.size),
        noise: noise,
        cluster_count: Object.keys(clusters).length,
        noise_count: noise.length,
    };
};

// ── SIGNAL PROPAGATION DECAY ─────────────────────────────────────
// For a single BSSID with multiple GPS-tagged observations,
// compute the empirical RSSI decay curve as distance from strongest signal.
PMStats.signalDecay = function(records, bssid) {
    const obs = records.filter(r => r.bssid === bssid &&
        r.lat && r.lon && Math.abs(r.lat) > 0.001);
    if (obs.length < 3) return null;

    // Find strongest observation (assumed closest to AP)
    obs.sort((a,b) => parseInt(b.rssi) - parseInt(a.rssi));
    const ref = obs[0];

    const points = obs.map(o => ({
        distance: PMStats.haversine(
            {lat: ref.lat, lon: ref.lon},
            {lat: o.lat, lon: o.lon}
        ),
        rssi: parseInt(o.rssi),
    }));

    // Sort by distance, compute decay rate
    points.sort((a,b) => a.distance - b.distance);
    const distances = points.map(p => p.distance);
    const rssis = points.map(p => p.rssi);

    // Linear regression on log-distance vs RSSI
    const logD = distances.map(d => Math.log10(Math.max(1, d)));
    const reg = _linearRegression(logD, rssis);

    return {
        bssid: bssid,
        observations: points.length,
        ref_rssi: ref.rssi,
        max_distance_m: Math.max(...distances),
        decay_db_per_decade: reg.slope * 10,  // dB per 10x distance
        rssi_at_1m: reg.intercept,
        r_squared: reg.r2,
        points: points,
    };
};

// ── ANOMALY DETECTION ────────────────────────────────────────────
PMStats.anomalies = function(records) {
    const findings = [];

    // 1. Open networks
    const open = records.filter(r => r.enc === 'OPEN');
    if (open.length) findings.push({
        severity: 'high', type: 'open_networks',
        count: open.length,
        title: `${open.length} unencrypted network${open.length>1?'s':''}`,
        detail: 'Open networks transmit data in cleartext, visible to passive observers.',
        items: open.slice(0, 20),
    });

    // 2. WEP networks (broken since 2001)
    const wep = records.filter(r => r.enc === 'WEP');
    if (wep.length) findings.push({
        severity: 'high', type: 'wep_networks',
        count: wep.length,
        title: `${wep.length} network${wep.length>1?'s':''} using WEP`,
        detail: 'WEP encryption was broken in 2001. Effectively equivalent to open networks.',
        items: wep.slice(0, 20),
    });

    // 3. Potential evil twins (same SSID, different vendors)
    const ssidMap = {};
    records.forEach(r => {
        if (!r.ssid) return;
        if (!ssidMap[r.ssid]) ssidMap[r.ssid] = [];
        ssidMap[r.ssid].push(r);
    });
    const twins = [];
    Object.entries(ssidMap).forEach(([ssid, recs]) => {
        const vendors = new Set(recs.map(r => r.vendor).filter(Boolean));
        const bssids = new Set(recs.map(r => r.bssid));
        if (recs.length > 1 && bssids.size > 1 && vendors.size > 1) {
            twins.push({ ssid, count: recs.length, vendors: [...vendors],
                bssids: [...bssids] });
        }
    });
    if (twins.length) findings.push({
        severity: 'medium', type: 'evil_twins',
        count: twins.length,
        title: `${twins.length} potential evil twin${twins.length>1?'s':''}`,
        detail: 'Same SSID broadcast from BSSIDs with different vendors. May indicate spoofed access points.',
        items: twins.slice(0, 10),
    });

    // 4. Channel congestion (>10 networks on one channel)
    const chCounts = {};
    records.forEach(r => {
        if (r.channel) chCounts[r.channel] = (chCounts[r.channel]||0) + 1;
    });
    const congested = Object.entries(chCounts)
        .filter(([,c]) => c > 10)
        .sort((a,b) => b[1]-a[1]);
    if (congested.length) findings.push({
        severity: 'low', type: 'channel_congestion',
        count: congested.length,
        title: `Congestion on ${congested.length} channel${congested.length>1?'s':''}`,
        detail: 'Heavily occupied channels reduce throughput for all networks sharing them.',
        items: congested.map(([ch,n]) => ({ channel: ch, network_count: n })),
    });

    // 5. Hidden SSIDs (potential reconnaissance avoidance)
    const hidden = records.filter(r => !r.ssid || r.ssid === '');
    if (hidden.length > 5) findings.push({
        severity: 'low', type: 'hidden_ssids',
        count: hidden.length,
        title: `${hidden.length} hidden SSIDs`,
        detail: 'Networks not broadcasting their SSID. Common for management networks but also used to evade casual detection.',
    });

    // 6. WPS-enabled networks (cap. include "WPS")
    const wps = records.filter(r =>
        (r.enc || '').toUpperCase().includes('WPS'));
    if (wps.length) findings.push({
        severity: 'medium', type: 'wps_enabled',
        count: wps.length,
        title: `${wps.length} network${wps.length>1?'s':''} with WPS`,
        detail: 'WPS PIN brute-force vulnerability (Reaver/Bully) affects many WPS implementations.',
    });

    // 7. Anomalously strong signals (potential physical proximity)
    const veryStrong = records.filter(r => parseInt(r.rssi) > -40);
    if (veryStrong.length) findings.push({
        severity: 'info', type: 'strong_signals',
        count: veryStrong.length,
        title: `${veryStrong.length} very strong signal${veryStrong.length>1?'s':''} (>-40dBm)`,
        detail: 'Devices within ~3 meters. Useful for proximity analysis.',
    });

    return findings;
};

// ── SESSION COMPARISON / DIFF ────────────────────────────────────
PMStats.diff = function(setA, setB) {
    const aBssids = new Set(setA.map(r => r.bssid));
    const bBssids = new Set(setB.map(r => r.bssid));

    const onlyInA = setA.filter(r => !bBssids.has(r.bssid));
    const onlyInB = setB.filter(r => !aBssids.has(r.bssid));

    // Find networks in both — track signal/channel/encryption changes
    const changed = [];
    const aMap = {};
    setA.forEach(r => { if (!aMap[r.bssid]) aMap[r.bssid] = r; });

    setB.forEach(b => {
        const a = aMap[b.bssid];
        if (!a) return;
        const changes = {};
        const rA = parseInt(a.rssi)||0, rB = parseInt(b.rssi)||0;
        if (Math.abs(rA - rB) > 15) changes.rssi = { from: rA, to: rB };
        if (a.channel !== b.channel) changes.channel = { from: a.channel, to: b.channel };
        if (a.enc !== b.enc) changes.enc = { from: a.enc, to: b.enc };
        if (a.ssid !== b.ssid) changes.ssid = { from: a.ssid, to: b.ssid };
        if (Object.keys(changes).length) {
            changed.push({ bssid: b.bssid, ssid: b.ssid || a.ssid, changes });
        }
    });

    return {
        new_networks: onlyInB,           // appeared since session A
        gone_networks: onlyInA,          // disappeared
        changed_networks: changed,       // present in both, differ
        unchanged_count: setB.length - onlyInB.length - changed.length,
        a_total: setA.length,
        b_total: setB.length,
    };
};

// ── HAVERSINE DISTANCE (meters) ──────────────────────────────────
PMStats.haversine = function(a, b) {
    const R = 6371000; // earth radius meters
    const lat1 = parseFloat(a.lat) * Math.PI / 180;
    const lat2 = parseFloat(b.lat) * Math.PI / 180;
    const dLat = (parseFloat(b.lat) - parseFloat(a.lat)) * Math.PI / 180;
    const dLon = (parseFloat(b.lon) - parseFloat(a.lon)) * Math.PI / 180;
    const x = Math.sin(dLat/2) ** 2 +
              Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon/2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
};

// ── TEMPORAL BUCKETING ───────────────────────────────────────────
// Group records into time bins for time-series analysis
PMStats.timeline = function(records, binMinutes) {
    binMinutes = binMinutes || 5;
    const bins = {};
    records.forEach(r => {
        const ts = _parseTimestamp(r.firstseen) || _parseTimestamp(r.lastseen) || Date.now();
        const bin = Math.floor(ts / (binMinutes * 60 * 1000)) * (binMinutes * 60 * 1000);
        if (!bins[bin]) bins[bin] = [];
        bins[bin].push(r);
    });
    return Object.entries(bins).map(([t, recs]) => ({
        timestamp: parseInt(t),
        count: recs.length,
        unique_bssids: new Set(recs.map(r => r.bssid)).size,
        records: recs,
    })).sort((a,b) => a.timestamp - b.timestamp);
};

// ── DEVICE PERSISTENCE SCORING ───────────────────────────────────
// For BSSIDs seen multiple times, score how persistent they are.
PMStats.persistence = function(records) {
    const byBssid = {};
    records.forEach(r => {
        if (!byBssid[r.bssid]) byBssid[r.bssid] = [];
        byBssid[r.bssid].push(r);
    });

    return Object.entries(byBssid).map(([bssid, recs]) => {
        const rssis = recs.map(r => parseInt(r.rssi)||-80);
        return {
            bssid: bssid,
            ssid: recs[0].ssid,
            vendor: recs[0].vendor,
            sightings: recs.length,
            avg_rssi: _mean(rssis),
            rssi_variance: _stdev(rssis),
            persistence_score: Math.min(100, recs.length * 5),
        };
    }).sort((a,b) => b.sightings - a.sightings);
};

// ── CHANNEL HEALTH ───────────────────────────────────────────────
PMStats.channelHealth = function(records) {
    const ch24 = {};
    const ch5 = {};
    records.forEach(r => {
        const c = parseInt(r.channel);
        if (!c) return;
        if (c <= 14) ch24[c] = (ch24[c]||0) + 1;
        else ch5[c] = (ch5[c]||0) + 1;
    });

    // Best 2.4GHz channels are 1, 6, 11 (non-overlapping)
    const ideal24 = [1, 6, 11];
    const recommendation24 = ideal24
        .map(c => ({ ch: c, count: ch24[c] || 0 }))
        .sort((a,b) => a.count - b.count)[0];

    // 5GHz: lower count = less congested
    const ch5sorted = Object.entries(ch5)
        .map(([c,n]) => ({ch: parseInt(c), count: n}))
        .sort((a,b) => a.count - b.count);

    return {
        channels_24ghz: ch24,
        channels_5ghz: ch5,
        most_congested: Object.entries({...ch24, ...ch5})
            .sort((a,b) => b[1]-a[1]).slice(0,5)
            .map(([c,n]) => ({channel: parseInt(c), count: n})),
        recommended_24ghz: recommendation24,
        recommended_5ghz: ch5sorted[0] || null,
    };
};

// ── VENDOR DIVERSITY INDEX ───────────────────────────────────────
// Shannon entropy of vendor distribution. Higher = more diverse.
PMStats.vendorMix = function(records) {
    const counts = {};
    records.forEach(r => {
        const v = r.vendor || 'Unknown';
        counts[v] = (counts[v]||0) + 1;
    });

    const total = records.length;
    let entropy = 0;
    Object.values(counts).forEach(c => {
        const p = c / total;
        if (p > 0) entropy -= p * Math.log2(p);
    });

    const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]);
    const top = sorted[0];
    const dominantShare = top ? top[1] / total : 0;

    return {
        vendor_count: Object.keys(counts).length,
        shannon_entropy: entropy,
        max_entropy: Math.log2(Object.keys(counts).length),
        dominance: dominantShare,
        dominant_vendor: top ? top[0] : null,
        diversity_normalized: Object.keys(counts).length > 1
            ? entropy / Math.log2(Object.keys(counts).length) : 0,
    };
};

// ────────────────────────────────────────────────────────────────
// Internal helpers
// ────────────────────────────────────────────────────────────────
function _mean(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a,b) => a+b, 0) / arr.length;
}

function _median(arr) {
    if (!arr.length) return 0;
    const s = [...arr].sort((a,b) => a-b);
    const m = Math.floor(s.length/2);
    return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2;
}

function _stdev(arr) {
    if (arr.length < 2) return 0;
    const m = _mean(arr);
    return Math.sqrt(arr.map(x => (x-m)**2).reduce((a,b) => a+b, 0) / (arr.length-1));
}

function _percentile(arr, p) {
    if (!arr.length) return 0;
    const s = [...arr].sort((a,b) => a-b);
    const idx = (p/100) * (s.length - 1);
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (idx - lo);
}

function _countBy(arr, key) {
    const counts = {};
    arr.forEach(o => {
        const v = o[key] || 'Unknown';
        counts[v] = (counts[v]||0) + 1;
    });
    return counts;
}

function _bboxArea(b) {
    // Very rough: degrees → meters² approximation at mid-latitude
    const w = (b.maxLon - b.minLon) * 111000 *
              Math.cos((b.minLat + b.maxLat) / 2 * Math.PI / 180);
    const h = (b.maxLat - b.minLat) * 111000;
    return Math.max(1, w * h);
}

function _linearRegression(x, y) {
    const n = x.length;
    if (n < 2) return { slope: 0, intercept: 0, r2: 0 };
    const mx = _mean(x), my = _mean(y);
    let num = 0, denX = 0, denY = 0;
    for (let i = 0; i < n; i++) {
        num += (x[i] - mx) * (y[i] - my);
        denX += (x[i] - mx) ** 2;
        denY += (y[i] - my) ** 2;
    }
    const slope = denX === 0 ? 0 : num / denX;
    const intercept = my - slope * mx;
    const r2 = (denX === 0 || denY === 0) ? 0 : (num ** 2) / (denX * denY);
    return { slope, intercept, r2 };
}

function _parseTimestamp(ts) {
    if (!ts) return null;
    const n = parseInt(ts);
    if (n > 946684800000) return n;       // ms after 2000
    if (n > 946684800)    return n * 1000; // sec after 2000
    const d = new Date(ts);
    return isNaN(d.getTime()) ? null : d.getTime();
}

// Expose
window.PMStats = PMStats;
})();
