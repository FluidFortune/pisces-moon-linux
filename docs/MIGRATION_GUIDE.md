<!--
  Pisces Moon OS — MIGRATION_GUIDE.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# MIGRATION GUIDE: v0.4 CYBER APPS → v0.5 TRANSPORT ABSTRACTION

This guide shows how to convert each of the 14 v0.4 cyber apps (which hardcode WebSocket connections) to use the new `pm_transport.js` abstraction. After migration, the same HTML works on Linux (via WebSocket) AND Android (via Web Bluetooth) without code changes.

---

## THE OLD WAY (v0.4)

```javascript
// Hardcoded WebSocket — only works on Linux with edge_bridge.py
const ws = new WebSocket('ws://localhost:5006');
ws.onmessage = e => {
    try {
        const data = JSON.parse(e.data);
        handleData(data);
    } catch(_) {}
};
ws.onerror = () => console.log('No bridge');
```

Works on Linux. Doesn't work on Android (no edge bridge unless user installs Termux).

---

## THE NEW WAY (v0.5)

```html
<script src="pm_transport.js"></script>
<script>
const beam = new PMTransport({
    onMessage: data => handleData(data),
    onStatus:  s    => updateConnectionUI(s),
});

// Try to connect when user clicks a button
async function connect() {
    try {
        const result = await beam.connect();
        console.log("Connected via", result.mode);  // "websocket" or "bluetooth"
    } catch (e) {
        console.error("Connection failed:", e.message);
    }
}

// Send commands the same way regardless of transport
async function startScan() {
    await beam.send({cmd: "wifi_scan", params: {duration_sec: 30}});
}
</script>

<button onclick="connect()">Connect to T-Beam</button>
```

Works on Linux (auto-uses WebSocket). Works on Android (auto-uses Web Bluetooth). No code changes between platforms.

---

## STEP-BY-STEP MIGRATION

### Step 1: Add the script tag

At the top of each cyber app's `<script>` section, before any existing code:

```html
<script src="pm_transport.js"></script>
```

If your app uses a relative path that goes up directories, adjust accordingly. In the v0.5 layout, all apps and shared files live in the same directory.

### Step 2: Replace the WebSocket setup

Find the existing `new WebSocket(...)` code. In most v0.4 cyber apps it looks like:

```javascript
window.pm = (() => {
    const isTH = typeof window.spadra !== 'undefined';
    return {
        async readFile(p) { return isTH ? window.spadra.fs.read(p) : null; },
        onSerial(cb) {
            if (isTH && window.spadra.serial) { window.spadra.serial.onData(cb); return; }
            try {
                const ws = new WebSocket('ws://localhost:5006');
                ws.onmessage = e => { try { cb(JSON.parse(e.data)); } catch(_) {} };
                ws.onerror = () => {};
            } catch(_) {}
        },
    };
})();
```

Replace the entire shim with:

```javascript
let beam = null;

function initTransport(onData) {
    beam = new PMTransport({
        onMessage: data => onData(data),
        onStatus: s => {
            const el = document.getElementById('connStatus');
            if (el) el.textContent = s.message;
        },
    });
}
```

### Step 3: Add a connect button

The biggest behavioral change: Web Bluetooth requires an explicit user gesture to open the pairing dialog. You can no longer auto-connect on page load. Add a button:

```html
<button id="connectBtn" onclick="connectBeam()">Connect T-Beam</button>
<span id="connStatus">Not connected</span>
```

```javascript
async function connectBeam() {
    if (!beam) initTransport(handleScanData);
    try {
        await beam.connect();
        document.getElementById('connectBtn').textContent = 'Connected';
    } catch (e) {
        alert("Could not connect: " + e.message);
    }
}
```

If the app needs to auto-connect for the WebSocket-only use case (Linux, edge bridge always running), you can detect that:

```javascript
window.addEventListener('load', async () => {
    initTransport(handleScanData);
    // Try silent auto-connect — this works for WebSocket but not Bluetooth
    try {
        await beam.connect();
    } catch {
        // No silent connection possible — user must click the button
    }
});
```

### Step 4: Update the data handler

The data format from `pm_transport.js` is consistent across both transports. Most v0.4 apps already handle JSON objects, so this part needs minimal change. Make sure your handler expects the new envelope:

**v0.4 format (raw):**
```json
{"ssid":"NETGEAR","bssid":"a4:2b:b0:cf:d3:9a","rssi":-67}
```

**v0.5 format (enveloped by edge_bridge or BLE characteristic):**
```json
{"type":"wifi_scan","ssid":"NETGEAR","bssid":"a4:2b:b0:cf:d3:9a","rssi":-67,"timestamp":1714342890}
```

If your code already filters by type (most do via `data.type === 'wifi_scan'`), no change needed. Otherwise add the type field check.

### Step 5: Send commands via beam.send()

Anywhere your app needed to send commands to the T-Beam (start scan, stop scan, change channel), use:

```javascript
await beam.send({cmd: "wifi_scan", params: {duration_sec: 30}});
```

The transport layer handles dispatch. On WebSocket it sends JSON. On BLE it writes to the command characteristic.

---

## PER-APP MIGRATION CHECKLIST

The 14 cyber apps that need migration:

| App | Current transport | Migration complexity |
|-----|-------------------|---------------------|
| wardrive.html | WebSocket :5006 | Low — straightforward replacement |
| bt_radar.html | WebSocket :5006 | Low |
| pkt_sniffer.html | WebSocket :5006 | Low |
| beacon_spotter.html | WebSocket :5006 | Low |
| net_scanner.html | WebSocket + scapy | Medium — uses host network too |
| gps_app.html | WebSocket :5006 | Low |
| mesh_messenger.html | WebSocket :5006 | Medium — needs bidirectional |
| ble_gatt.html | WebSocket :5006 | Medium — already BLE-aware UI |
| wpa_handshake.html | WebSocket :5006 | Low |
| rf_spectrum.html | WebSocket :5006 | High — bandwidth-sensitive, may need WS-only |
| probe_intel.html | WebSocket :5006 | Low |
| pkt_analysis.html | WebSocket :5006 | High — bandwidth-sensitive |
| ble_ducky.html | WebSocket :5006 | Low |
| usb_ducky.html | WebSocket :5006 | Low |
| wifi_ducky.html | WebSocket :5006 | Low |

### Bandwidth-sensitive apps (rf_spectrum, pkt_analysis)

These apps stream high-volume data (raw RF samples, packet captures). Web Bluetooth's ~10-50 KB/s ceiling will choke them. For these specific apps:

```javascript
const beam = new PMTransport({mode: "websocket"});  // force WebSocket only
```

And in the UI, show a message: *"This app requires the desktop edge bridge — Web Bluetooth bandwidth is insufficient for live RF data."*

The WebSocket-only constraint is fine because these are inherently desktop-tier workflows anyway.

---

## TESTING THE MIGRATION

### On Linux (WebSocket path)

```bash
# Terminal 1: start the edge bridge
python3 /opt/pisces-moon/tools/edge_bridge.py

# Terminal 2: open the app
chromium --app=file:///opt/pisces-moon/html/wardrive.html
```

Click "Connect T-Beam." It should auto-detect the WebSocket and connect. Status should show "Connected via websocket."

### On Android (Web Bluetooth path)

```bash
# Build the v0.5 APK (see deploy-android/docs/ANDROID_GUIDE.md)
# Install on tablet
# Power up T-Beam with BLE GATT firmware
# Open Pisces Moon app, go to wardrive
```

Click "Connect T-Beam." System BLE pairing dialog opens. Pick your T-Beam from the list. Status should show "Connected via bluetooth."

### Confirming both work from the same HTML

After migration, the EXACT SAME `wardrive.html` file should work in both environments. If you have to maintain two copies, the migration was wrong — the whole point is one source of truth.

---

## ROLLBACK PLAN

If any app breaks after migration and you need to revert:

1. The original v0.4 hardcoded-WebSocket version still works on Linux
2. Keep both versions in source control (use a git branch)
3. The transport abstraction is opt-in per app — apps that haven't been migrated yet still work unchanged on Linux

There's no "big bang" required. Migrate one app, ship it, validate it on both platforms, then move to the next.

---

## RECOMMENDED MIGRATION ORDER

1. **wardrive.html** — most common use case, good first migration
2. **gps_app.html** — simple read-only data flow, easy validation
3. **bt_radar.html** — similar to wardrive, low risk
4. **beacon_spotter.html** — exercises the BLE filtering logic
5. **net_scanner.html** — tests bidirectional commands
6. **mesh_messenger.html** — tests bidirectional in production
7. The remaining apps in any order

After the first 3-4 are migrated and proven to work on both platforms, the rest are mostly mechanical repetition of the same pattern.

---

*Pisces Moon migration guide — Eric Becker / Fluid Fortune / 2026*
