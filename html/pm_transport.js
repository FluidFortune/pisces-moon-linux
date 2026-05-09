// ═══════════════════════════════════════════════════════════════════════
// PISCES MOON OS — TRANSPORT ABSTRACTION LAYER
// Copyright (C) 2026 Eric Becker / Fluid Fortune
// SPDX-License-Identifier: AGPL-3.0-or-later
// fluidfortune.com
//
// PURPOSE:
//   Lets one HTML app talk to a T-Beam via EITHER:
//     - WebSocket (Linux desktop with edge_bridge.py running)
//     - Web Bluetooth (Android with BLE GATT firmware on T-Beam)
//   Without the app knowing or caring which transport is in use.
//
// USAGE:
//   const beam = new PMTransport({
//       onMessage: msg => handleData(msg),
//       onStatus: s => updateUI(s),
//   });
//   await beam.connect();      // auto-detects best transport
//   beam.send({cmd: "scan"});  // works the same on both transports
//
// AUTO-DETECTION ORDER:
//   1. If running in Trojan Horse APK (window.PiscesAndroid exists)
//      → prefer Web Bluetooth (no Termux required)
//   2. If WebSocket is available at ws://127.0.0.1:8080
//      → use WebSocket (Linux + edge_bridge.py)
//   3. If neither, prompt user to pick one or fail gracefully
//
// MANUAL OVERRIDE:
//   const beam = new PMTransport({mode: "bluetooth"});  // force BLE
//   const beam = new PMTransport({mode: "websocket"});  // force WS
// ═══════════════════════════════════════════════════════════════════════

const PM_BLE_SERVICE_UUID         = "8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a";
const PM_BLE_DATA_CHAR_UUID       = "8b5e0002-7c34-4a91-bd5c-1a2e9d6f8c4a";
const PM_BLE_COMMAND_CHAR_UUID    = "8b5e0003-7c34-4a91-bd5c-1a2e9d6f8c4a";
const PM_BLE_STATUS_CHAR_UUID     = "8b5e0004-7c34-4a91-bd5c-1a2e9d6f8c4a";

// Auto-detect bridge host — works on any device on the network.
// If served from file:// or localhost, use 127.0.0.1.
// If served from another host (Android tablet, ChromeOS, Q508, etc.),
// use whatever host served the page — that's where pm_bridge.py is running.
const PM_WS_DEFAULT_URL = (() => {
    const host = window.location.hostname;
    const bridgeHost = (!host || host === 'localhost' || host === '127.0.0.1')
        ? '127.0.0.1'
        : host;
    return `ws://${bridgeHost}:8080`;
})();

class PMTransport {
    /**
     * @param {Object} opts
     * @param {Function} opts.onMessage - Called for every data packet from T-Beam
     * @param {Function} opts.onStatus - Called when connection state changes
     * @param {string} [opts.mode] - "auto" | "websocket" | "bluetooth"
     * @param {string} [opts.wsUrl] - Override WebSocket URL
     */
    constructor(opts = {}) {
        this.onMessage = opts.onMessage || (() => {});
        this.onStatus  = opts.onStatus  || (() => {});
        this.mode      = opts.mode      || "auto";
        this.wsUrl     = opts.wsUrl     || PM_WS_DEFAULT_URL;

        // State
        this.transport = null;
        this.connected = false;
        this.activeMode = null;
        this.ws = null;
        this.bleDevice = null;
        this.bleServer = null;
        this.bleService = null;
        this.bleDataChar = null;
        this.bleCommandChar = null;
    }

    /**
     * Connect to the T-Beam. Auto-detects transport unless mode was set.
     * Returns a promise that resolves to {mode: "websocket"|"bluetooth"} on success.
     */
    async connect() {
        let chosenMode = this.mode;

        if (chosenMode === "auto") {
            chosenMode = await this._autoDetectBestTransport();
        }

        this._status("connecting", `Trying ${chosenMode}...`);

        try {
            if (chosenMode === "bluetooth") {
                await this._connectBluetooth();
            } else if (chosenMode === "websocket") {
                await this._connectWebSocket();
            } else {
                throw new Error(`Unknown transport mode: ${chosenMode}`);
            }

            this.activeMode = chosenMode;
            this.connected = true;
            this._status("connected", `Connected via ${chosenMode}`);
            return {mode: chosenMode};
        } catch (e) {
            this._status("error", e.message);
            throw e;
        }
    }

    /**
     * Send a command/message to the T-Beam.
     * @param {Object|string} data - JSON-serializable object or string
     */
    async send(data) {
        if (!this.connected) {
            throw new Error("Not connected. Call connect() first.");
        }

        const payload = typeof data === "string" ? data : JSON.stringify(data);

        if (this.activeMode === "websocket") {
            this.ws.send(payload);
        } else if (this.activeMode === "bluetooth") {
            // BLE characteristic writes have a max packet size (~512 bytes)
            // For larger payloads we'd chunk, but commands should be small.
            const encoder = new TextEncoder();
            const bytes = encoder.encode(payload);
            if (bytes.length > 512) {
                throw new Error("BLE command too large (max 512 bytes)");
            }
            await this.bleCommandChar.writeValue(bytes);
        }
    }

    /**
     * Cleanly disconnect.
     */
    async disconnect() {
        this.connected = false;
        if (this.ws) {
            try { this.ws.close(); } catch {}
            this.ws = null;
        }
        if (this.bleDevice && this.bleDevice.gatt.connected) {
            try { this.bleDevice.gatt.disconnect(); } catch {}
        }
        this.bleDevice = null;
        this.activeMode = null;
        this._status("disconnected", "Disconnected");
    }

    /**
     * Returns capabilities of the current connection.
     * Apps can check what's possible before trying.
     */
    capabilities() {
        return {
            connected: this.connected,
            mode: this.activeMode,
            bandwidth: this.activeMode === "websocket" ? "high" : "low",
            // BLE realistically handles ~10-50 KB/s; WebSocket much higher
            maxPacketSize: this.activeMode === "bluetooth" ? 512 : 65536,
            bidirectional: true,
        };
    }

    // ── PRIVATE ───────────────────────────────────────────────────────

    async _autoDetectBestTransport() {
        // Heuristic: if we're in the Pisces Moon Android APK, prefer BLE.
        // Otherwise, prefer WebSocket (Linux desktop with edge bridge).
        const isAndroidAPK = typeof window !== "undefined" &&
                             window.PiscesAndroid &&
                             typeof window.PiscesAndroid.bridgeAvailable === "function";

        if (isAndroidAPK) {
            // Check if Web Bluetooth is available
            if (navigator.bluetooth) return "bluetooth";
            // Fall back to WebSocket (Termux bridge running)
            return "websocket";
        }

        // Non-APK contexts (Linux desktop Chromium):
        // Try WebSocket first since edge_bridge.py is the Linux pattern
        const wsAvailable = await this._probeWebSocket();
        if (wsAvailable) return "websocket";

        // Fall back to Bluetooth if available
        if (navigator.bluetooth) return "bluetooth";

        throw new Error("No transport available. Start edge_bridge.py or pair via Bluetooth.");
    }

    async _probeWebSocket() {
        return new Promise(resolve => {
            try {
                const probe = new WebSocket(this.wsUrl);
                const timer = setTimeout(() => {
                    try { probe.close(); } catch {}
                    resolve(false);
                }, 1500);
                probe.onopen = () => {
                    clearTimeout(timer);
                    try { probe.close(); } catch {}
                    resolve(true);
                };
                probe.onerror = () => {
                    clearTimeout(timer);
                    resolve(false);
                };
            } catch {
                resolve(false);
            }
        });
    }

    async _connectWebSocket() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => resolve();
            this.ws.onerror = () => reject(new Error(`WebSocket failed at ${this.wsUrl}`));

            this.ws.onmessage = ev => {
                let data;
                try {
                    data = JSON.parse(ev.data);
                } catch {
                    data = {type: "raw", data: ev.data};
                }
                this.onMessage(data);
            };

            this.ws.onclose = () => {
                if (this.connected) {
                    this.connected = false;
                    this._status("disconnected", "WebSocket closed");
                }
            };
        });
    }

    async _connectBluetooth() {
        if (!navigator.bluetooth) {
            throw new Error("Web Bluetooth not supported in this browser");
        }

        // Show the system pairing dialog. User picks T-Beam from list.
        this.bleDevice = await navigator.bluetooth.requestDevice({
            filters: [
                {services: [PM_BLE_SERVICE_UUID]},
                {namePrefix: "PiscesMoon"},
                {namePrefix: "T-Beam"},
            ],
            optionalServices: [PM_BLE_SERVICE_UUID],
        });

        // Listen for unexpected disconnections
        this.bleDevice.addEventListener("gattserverdisconnected", () => {
            if (this.connected) {
                this.connected = false;
                this._status("disconnected", "T-Beam disconnected");
            }
        });

        // Connect to the GATT server on the T-Beam
        this.bleServer = await this.bleDevice.gatt.connect();
        this.bleService = await this.bleServer.getPrimaryService(PM_BLE_SERVICE_UUID);

        // Get the data characteristic (T-Beam → tablet)
        this.bleDataChar = await this.bleService.getCharacteristic(PM_BLE_DATA_CHAR_UUID);
        await this.bleDataChar.startNotifications();
        this.bleDataChar.addEventListener("characteristicvaluechanged", ev => {
            const decoder = new TextDecoder();
            const text = decoder.decode(ev.target.value);
            let data;
            try {
                data = JSON.parse(text);
            } catch {
                data = {type: "raw", data: text};
            }
            this.onMessage(data);
        });

        // Get the command characteristic (tablet → T-Beam)
        this.bleCommandChar = await this.bleService.getCharacteristic(PM_BLE_COMMAND_CHAR_UUID);

        // Optional: status characteristic
        try {
            const statusChar = await this.bleService.getCharacteristic(PM_BLE_STATUS_CHAR_UUID);
            await statusChar.startNotifications();
            statusChar.addEventListener("characteristicvaluechanged", ev => {
                const decoder = new TextDecoder();
                const text = decoder.decode(ev.target.value);
                this._status("device_status", text);
            });
        } catch {
            // Status char is optional
        }
    }

    _status(state, message) {
        this.onStatus({state, message, mode: this.activeMode, timestamp: Date.now()});
    }
}

// ── Convenience global ─────────────────────────────────────────────────
if (typeof window !== "undefined") {
    window.PMTransport = PMTransport;
    window.PM_BLE_SERVICE_UUID = PM_BLE_SERVICE_UUID;
}
