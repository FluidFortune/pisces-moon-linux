<!--
  Pisces Moon OS - README.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# Pisces Moon OS

**Local-first field intelligence OS. No cloud, no telemetry, no gatekeepers.**

```
   PISCES  ☾   MOON
   --------------------------------
   Built on the Clark Beddows Protocol
   Runs on Debian, Android, ESP32, and beyond
   The user owns everything
```

> Dedicated to Jennifer Soto and Clark Beddows.

---

## Project status (May 2026)

This is an actively-developed project in mixed states of completion. The repository contains code at all maturity levels. Read this section before assuming any component "works" in the conventional sense.

### Working — production-ready or close to it

| Component | Status | Notes |
|-----------|--------|-------|
| **HTML app suite** (81 apps) | ✅ Working | Cross-platform, runs in any modern browser |
| **Clark Beddows Protocol architecture** | ✅ Stable | Local-first, WebSocket-based, 80 apps coordinate through one bridge |
| **Self-contained palette migration** | ✅ Complete | All 80 apps + Clinician have inline cyberpunk palette, render correctly without external CSS |
| **Linux installer** (`install.sh`) | ✅ Working | Tested on Debian 13 + XFCE 4.18, Q508 confirmed |
| **Install fixes script** (`install_fixes.sh`) | ✅ Working | Targeted patches for battery indicator, wallpaper, right-click menu |
| **Crelander debloat script** | ✅ Working | Tested on Crelander W87-EEA Android 15, F-Droid Termux confirmed |
| **WiGLE 1.4 CSV format compatibility** | ✅ Working | Full read/write, compatible with WiGLE.net database |
| **HTML apps over file://** | ✅ Working | Apps run standalone without any bridge for non-RF use cases |

### Partially working — functional but incomplete

| Component | Status | Notes |
|-----------|--------|-------|
| **pm_bridge.py v1.2** | ⚠️ ALPHA | Core scanning paths work on Mac/Linux/Android. Probe/LoRa relay is wired but waiting on T-Deck firmware events. PCAP relay and native GPS not implemented. |
| **The Clinician** | ⚠️ Functional, untested at scale | Phase 1-4 features built. Single data type tested (WiFi/WiGLE). BLE/Probe/LoRa importers exist but need real-world data validation. Lasso, time slider, DBSCAN clustering need field testing. |
| **Live Bridge integration in apps** | ⚠️ Works on Mac | Tested with T-Deck Plus on macOS Tahoe. Linux/Windows paths exist but not validated this cycle. |
| **Capacitor APK build** | ⚠️ UNTESTED | Project structure exists in `pisces-moon-capacitor.zip`. npm install + npx cap sync + Android Studio build not yet completed end-to-end. See "APK Compile Strategy" below. |
| **Trojan Horse desktop runtime** | ⚠️ Planned | Architecture documented, 8-week build plan deferred until Jennifer kernel matures. |

### Not working — known broken or incomplete

| Component | Status | Notes |
|-----------|--------|-------|
| **Project Jennifer (bare-metal kernel)** | ❌ Pre-alpha | Bootloader written, boots to black screen on Q508. EFI path issue. Develops in isolation in its own repo. |
| **PCAP file retrieval from T-Deck** | ❌ Not implemented | Architecturally complex. Serial transfer too slow at 921600 baud for >1MB captures. USB MSC mount requires firmware changes. |
| **Native GPS in pm_bridge** | ❌ Not implemented | Bridge currently relies on T-Deck GPS or browser geolocation. CoreLocation/gpsd integration deferred. |
| **WPS IE parsing in wardrive CSV** | ❌ Not implemented | T-Deck firmware's beacon_spotter.cpp parses WPS but doesn't route it to wardrive output. |
| **Raw wardrive observation mode** | ❌ Not implemented | T-Deck firmware deduplicates by BSSID. Architectural change needed for time-series analysis. Bridge is transparent — will log raw the moment firmware emits raw. |
| **Multi-T-Deck support** | ❌ Not implemented | Bridge manages one serial connection at a time. |
| **Luckfox 86Panel build environment** | 🔒 Private | Architecture redacted. Not in this repo. |
| **HiBy M300 audio APK** | 📋 Planned | Future side project. Snapdragon 665, Cirrus Logic CS43131. |

### Strategic directive (current cycle)

1. **Linux/Android development PAUSED** for the current cycle. Mac development continues. Existing Linux/Android code in the repo is **preserved** but **not actively maintained**.
2. **Pisces Moon OS continues** development — focus on The Clinician and sensor expansion. Whatever The Clinician needs, find a sensor for it.
3. **Project Jennifer** continues in vacuum. Boot-to-visible-output is the only milestone that matters there.

---

## The Clinician

Buried in this repo is **The Clinician** (`html/clinician.html`) — the flagship RF intelligence analysis platform that powers the Pisces Moon data science layer. It currently exists in this repo to establish copyright provenance under AGPL-3.0-or-later. The Clinician will receive its own dedicated repository once field testing is complete.

For now: it's here, it's AGPL-licensed, it's part of this codebase. See `clinician.html` for the application and `pm_stats.js` for the analysis engine. Both files include their own AGPL headers.

The Clinician imports:
- WiGLE 1.4 CSV (Pisces Moon wardrive)
- Pisces Moon BLE CSV (`ble_*.csv`)
- Pisces Moon Probe CSV (`probes_*.csv`)
- Pisces Moon LoRa CSV (`lora_*.csv`)
- Kali airodump CSV
- Generic WiFi CSV
- XLSX (via SheetJS)
- `.pmsession` archive bundles (via JSZip)
- Live Bridge WebSocket stream

It provides four panes (Data, Map, Statistics, Report) with shared selection state, lasso polygon selection, temporal time slider filtering, DBSCAN clustering, multi-session map overlay, and a configurable PDF report builder with seven multi-frame use case templates.

---

## APK Compile Strategy (UNTESTED)

The Pisces Moon Capacitor project bundles all 81 HTML apps + pm_bridge.py via Chaquopy into an Android APK. **This build path has not been validated end-to-end yet — proceed at your own risk.**

### Prerequisites
- Android Studio Hedgehog or later
- Node.js 20+ with npm
- Java JDK 17
- Android SDK with API level 34
- Chaquopy SDK 15.0 or later

### Build steps (theoretical, NOT VERIFIED)

```bash
# 1. Extract the Capacitor project archive
unzip pisces-moon-capacitor.zip
cd pisces-moon-capacitor

# 2. Install dependencies
npm install
npm install @capacitor/core @capacitor/android @capacitor/cli

# 3. Sync Capacitor (copies www/ into Android Studio project)
npx cap sync android

# 4. Open in Android Studio
npx cap open android

# 5. In Android Studio:
#    - Wait for Gradle sync to complete
#    - Verify Chaquopy plugin is recognized
#    - Build → Build Bundle(s) / APK(s) → Build APK(s)
#    - APK output: android/app/build/outputs/apk/debug/app-debug.apk
```

### Known unknowns

- Chaquopy embedding pm_bridge.py has not been tested under real Android runtime
- `MainActivity.java` starts a Chaquopy thread for the bridge; thread lifecycle untested
- Permissions for WiFi scanning may require Android 13+ runtime permission handling
- WebView access to `ws://localhost:8080` requires `android:usesCleartextTraffic="true"` (set in manifest)
- App size will be large (~50MB+) due to bundled Python runtime

### What we expect to work
- HTML app suite renders in WebView identically to desktop browsers
- WebSocket loopback to embedded bridge
- Shared filesystem under app's private storage

### What we expect to break
- BLE scanning (requires native Android Bluetooth APIs, not currently exposed to Python)
- Background operation (Android kills foreground services aggressively)
- USB OTG to T-Deck (USB host mode requires manifest permissions and may not be exposed by Chaquopy)

**File this as: it might work, it might not. Test it, file issues, send PRs.**

---

## Table of contents

1. [What is this?](#what-is-this)
2. [The Clark Beddows Protocol](#the-clark-beddows-protocol)
3. [Quick start (Linux)](#quick-start-linux)
4. [What you get after install](#what-you-get-after-install)
5. [Architecture](#architecture)
6. [Edge node bridge: how the apps see the world](#edge-node-bridge-how-the-apps-see-the-world)
7. [ESP32-S3 / T-Deck Plus integration](#esp32-s3--t-deck-plus-integration)
8. [Silas Creek Parkway: the WiFi intelligence app](#silas-creek-parkway-the-wifi-intelligence-app)
9. [System requirements](#system-requirements)
10. [Manual install / advanced setup](#manual-install--advanced-setup)
11. [Verifying the bridge](#verifying-the-bridge)
12. [Troubleshooting](#troubleshooting)
13. [Project layout](#project-layout)
14. [Updating](#updating)
15. [Uninstall](#uninstall)
16. [Privacy and data handling](#privacy-and-data-handling)
17. [Licensing](#licensing)
18. [Credits](#credits)

---

## What is this?

Pisces Moon is a portable operating system built around the **Clark Beddows Protocol**: local-first, no external gatekeepers, user data sovereignty. It's a single source tree that deploys to:

- **Linux** (Debian 13 + XFCE) on tablets and laptops, the focus of this README
- **Android** (APK wrapper, separate build under `android/`)
- **ESP32-S3 mesh nodes** (T-Deck Plus, T-Beam) via the bridge protocol described below

The user-facing apps are 76 self-contained HTML files. Each one is single-file, dependency-free where possible, and runs in a Chromium window with no browser chrome. No installer per app, no dependencies to track. Deploy with `cp`. Update with `git pull`.

The Linux distribution wraps these apps with a desktop environment, an XDG menu structure, an auto-starting bridge service that exposes WiFi and packet capture to the apps, and tooling to keep the whole thing self-contained on a single device.

---

## The Clark Beddows Protocol

Three rules. They shape every decision in this codebase.

1. **Local-first.** Computation, storage, and decision-making happen on the device. The app works offline. Cloud is optional, never required.
2. **No gatekeepers.** No required accounts. No telemetry. No "phone home." No SaaS dependencies that can be pulled out from under the user.
3. **User owns everything.** Data files live where the user can see them. Configuration is human-readable. Export is one click. Deletion is real.

If a feature can't satisfy these rules, it doesn't ship.

---

## Quick start (Linux)

You need a Debian 13 machine. Bookworm or newer. XFCE is recommended but other desktop environments work; you'll just lose the menu integration.

```bash
git clone https://github.com/FluidFortune/pisces-moon.git
cd pisces-moon
sudo ./install.sh
```

The install script:

- Installs apt dependencies (`chromium`, `network-manager`, `xfce4-panel-plugins`, others)
- Copies the HTML app tree to `/opt/pisces-moon/html/`
- Copies the bridge script to `/opt/pisces-moon/tools/silas_creek_bridge.py`
- Generates `.desktop` files in `/usr/share/applications/` for every app, organized by category
- Creates a systemd user service for the bridge and **enables it automatically**
- Configures Onboard (on-screen keyboard) autostart for tablet use
- Sets up XFCE panel plugins (battery, sound, etc.) if XFCE is detected

After install, log out and back in. Apps appear in your application menu under categories like `PiscesMoon-Cyber`, `PiscesMoon-Tools`, `PiscesMoon-Comms`, `PiscesMoon-Field`.

To run a single app from anywhere without the menu:

```bash
chromium --app=file:///opt/pisces-moon/html/about.html
```

---

## What you get after install

**76 single-file HTML apps**, organized into categories. Highlights:

- **Silas Creek Parkway** - WiFi intelligence (speed test, AP scan, LAN device discovery, packet capture). Documented separately below.
- **Field Notes** - encrypted local journal with markdown, tagging, search
- **Recipes** - JSON-LD scraping, 6 default recipes, no internet required after first scrape
- **Trails** - 24 iconic US hiking trails with Leaflet map and difficulty-coded markers
- **Medical Reference** - CPR, Heimlich, anaphylaxis, stroke, burns, hypothermia, heat stroke, poisoning, bleeding control
- **Survival Reference** - STOP protocol, shelter, water, fire, navigation, signaling, edible plants
- **News aggregators** - General, World, Tech, Finance, and Local (haversine ZIP-based radius)
- **Sports intel** - NFL, NBA, NHL, MLS with live data
- **Cyber tools** - WiFi scan, Bluetooth radar, packet sniffer, hash tool, BLE GATT explorer
- **Mesh comms** - SOS beacon, mesh messenger, beacon spotter (talks to ESP32-S3 nodes)
- **Games** - chess, Galaga, Pac-Man, Snake, SimCity-lite, Etch-a-Sketch
- **System utilities** - calculator, clock, calendar, notepad, weather, GPS, file manager

**One systemd user service** (`pisces-moon-bridge`) that auto-starts at login. This is the only background process the distribution adds.

**An XDG menu structure** so apps appear properly categorized in your desktop environment.

---

## Architecture

```
+-----------------------------------------------------------------------+
|  Pisces Moon Linux                                                    |
|                                                                       |
|  +-----------------------+   +-----------------------+                |
|  |  Chromium app windows |   |  XFCE desktop shell   |                |
|  |  (one per HTML app)   |   |  (panel, menu, etc.)  |                |
|  +-----------+-----------+   +-----------------------+                |
|              |                                                        |
|              | WebSocket ws://127.0.0.1:8080                          |
|              | (JSON commands & events)                               |
|              v                                                        |
|  +-------------------------------------------------------+            |
|  |   silas_creek_bridge.py  (systemd user service)       |            |
|  |                                                       |            |
|  |   Auto-detects mode at startup:                       |            |
|  |    1. Serial T-Beam/T-Deck attached?  -> RELAY mode   |            |
|  |    2. No serial device?               -> NATIVE mode  |            |
|  +---------+---------------------------------+-----------+            |
|            |                                 |                        |
|     RELAY mode                          NATIVE mode                   |
|            |                                 |                        |
|            v                                 v                        |
|  +-----------------+              +------------------------+          |
|  | USB serial @    |              | OS WiFi radio:         |          |
|  | 115200 baud     |              | - Linux: nmcli/iwlist  |          |
|  | reads JSON      |              | - macOS: CoreWLAN      |          |
|  | from ESP32      |              | - Windows: netsh       |          |
|  +-----------------+              | + tcpdump packet cap.  |          |
|                                   | + ARP scan for devices |          |
|                                   +------------------------+          |
+-----------------------------------------------------------------------+
              ^
              | (RELAY mode only)
              | USB cable
              |
+----------------------------------------------------------+
|   ESP32-S3 / T-Deck Plus / T-Beam                        |
|                                                          |
|   Pisces Moon firmware running:                          |
|    - 802.11 promiscuous mode capture                     |
|    - Probe request / beacon parser                       |
|    - GPS tagging (T-Beam only)                           |
|    - LoRa mesh radio (T-Beam only, optional)             |
|    - Outputs newline-delimited JSON over USB serial      |
+----------------------------------------------------------+
```

Three layers, three responsibilities:

1. **HTML apps** know nothing about hardware. They speak JSON over a WebSocket. They don't care if the data comes from an ESP32 or your laptop's WiFi card.
2. **Bridge service** abstracts the hardware. Same JSON output regardless of source. Auto-detects the best available source at startup.
3. **Edge node** (when present) provides richer data: monitor mode capture on hardware-locked platforms, GPS tagging, mesh radio.

---

## Edge node bridge: how the apps see the world

The bridge is `silas_creek_bridge.py` - a single-file Python program with **zero pip dependencies**. Everything uses the Python standard library. It runs as a systemd user service after install.

### What it exposes

A WebSocket server at `ws://127.0.0.1:8080`. Apps in Chromium connect to this and exchange JSON messages.

### Commands the bridge accepts

```json
{"cmd": "scan_start"}          // Start WiFi AP scan
{"cmd": "scan_stop"}           // Stop continuous scanning
{"cmd": "scan_devices"}        // ARP/ping sweep for LAN devices
{"cmd": "packet_start", "channel": 6}  // Start 802.11 mgmt frame capture
{"cmd": "packet_stop"}         // Stop packet capture
{"cmd": "packet_status"}       // Query capture state
{"cmd": "ping"}                // Health check
{"cmd": "status"}              // Bridge mode and capabilities
```

### Events the bridge broadcasts

```json
{"type": "wardrive", "ssid": "...", "bssid": "...", "rssi": -42, "ch": 6,
 "enc": true, "vendor": "Cisco", "source": "native"}

{"type": "arp", "ip": "192.168.1.42", "mac": "AA:BB:CC:DD:EE:FF",
 "hostname": "kitchen-tv", "vendor": "Sony", "ping": 3, "status": "online"}

{"type": "ble", "mac": "...", "name": "...", "vendor": "...", "rssi": -65}

{"type": "packet", "frame_type": "deauth", "src": "...", "dst": "...",
 "ssid": "...", "channel": 6, "rssi": -55}

{"type": "threat", "kind": "deauth_flood", "rate": 14, "severity": "critical"}

{"type": "scan_start", "source": "native"}
{"type": "scan_complete", "count": 12, "timestamp": "..."}
{"type": "bridge_status", "mode": "native|serial", "platform": "Linux"}
```

### Two operating modes

The bridge picks one of two modes at startup. The choice is automatic and the apps don't care which is active.

**RELAY mode** - an ESP32-S3 or T-Beam is plugged in via USB. The bridge reads the device's JSON output line by line and forwards it to connected WebSocket clients. The bridge handles the framing, the apps see clean JSON.

**NATIVE mode** - no edge node attached. The bridge uses the host operating system's own WiFi radio.

| Platform | WiFi scan | Packet capture |
|---|---|---|
| Linux (Debian 13) | `nmcli dev wifi list --rescan yes` (with `iwlist scan` fallback) | tcpdump on monitor interface (`mon0`), auto-created via `iw phy phy0 interface add` |
| macOS (Tahoe / 26) | CoreWLAN via inline Swift snippet (works around removal of `airport` CLI) | tcpdump with `-I` flag for monitor mode (hardware-locked on Apple Silicon - bridge gracefully reports unsupported) |
| Windows | `netsh wlan show networks mode=bssid` | Not supported in NATIVE mode - use a T-Beam |

LAN device discovery (the "what's connected to my WiFi" view) works in both modes via concurrent ping sweep + ARP table read. Pure stdlib, no nmap, no privileged sockets needed on Linux (reads `/proc/net/arp` directly).

---

## ESP32-S3 / T-Deck Plus integration

The Pisces Moon firmware (separate repo, contact for access) runs on three reference platforms:

- **LilyGo T-Deck Plus** - ESP32-S3, full QWERTY keyboard, color display, GPS, LoRa. The flagship handheld.
- **LilyGo T-Beam S3 Supreme** - ESP32-S3, GPS, LoRa, no display. Best as a wardriving / mesh node.
- **Bare ESP32-S3 dev boards** - for headless deployment.

### How the firmware talks to the bridge

The firmware operates in **promiscuous 802.11 mode** with the WiFi radio configured as a passive sniffer. As frames arrive, the firmware filters and parses them, then emits one JSON line per event to USB serial at 115200 baud.

Example output stream from a T-Beam:

```
{"type":"wardrive","ssid":"HOME-9F2A","bssid":"AA:BB:CC:DD:EE:FF","rssi":-67,"ch":6,"enc":true,"lat":35.7148,"lon":-79.4567,"ts":1740089123}
{"type":"wardrive","ssid":"","bssid":"11:22:33:44:55:66","rssi":-82,"ch":11,"enc":false,"lat":35.7148,"lon":-79.4567,"ts":1740089124}
{"type":"packet","frame_type":"probe_req","src":"de:ad:be:ef:00:01","ssid":"airport_wifi","channel":6,"rssi":-71}
{"type":"gps","lat":35.7148,"lon":-79.4567,"alt":234,"sats":9,"hdop":1.2}
```

The bridge in RELAY mode reads these lines and forwards them to WebSocket clients verbatim, only adding/normalizing the `vendor` field via OUI lookup if the firmware doesn't already provide it.

### Why the bridge

ESP32-S3 firmware can't host a WebSocket server with the throughput Pisces Moon apps need, and exposing the device directly to the LAN raises security questions. Putting the bridge in the middle gives you:

- One stable endpoint (`ws://127.0.0.1:8080`) regardless of edge hardware
- Hot-swappable edge nodes (unplug T-Beam, plug T-Deck, no app changes)
- Graceful fallback to native scan when no node is attached
- A place to add cross-cutting concerns (rate limiting, frame filtering, logging) without touching firmware

### Connecting an edge node

1. Flash the Pisces Moon firmware to your ESP32-S3 device (see firmware repo for instructions)
2. Plug it into your Linux machine via USB
3. Restart the bridge: `systemctl --user restart pisces-moon-bridge`
4. The bridge logs `Mode: SERIAL RELAY via /dev/ttyACM0` (or `/dev/ttyUSB0`)
5. Apps automatically pick up the richer data stream - they don't need to be restarted

The firmware presents itself as a USB CDC-ACM serial device. On Linux it shows up as `/dev/ttyACM0` or `/dev/ttyUSB0`. On macOS as `/dev/cu.usbmodem*`. The bridge scans common patterns and identifies the device by querying its USB descriptor.

### Mesh radio (T-Beam / T-Deck only)

When a LoRa-equipped node is connected, the bridge exposes additional message types:

- `mesh_in` - inbound LoRa message
- `mesh_out` - command to send a mesh message
- `mesh_peer` - peer announcement / heartbeat

These power the mesh messenger and SOS beacon apps. The mesh protocol is documented in `docs/MESH_APPS_DESCRIPTION.md`.

---

## Silas Creek Parkway: the WiFi intelligence app

This is the flagship demonstration of the bridge architecture. Open it from the menu (`PiscesMoon-Cyber > Silas Creek Parkway`) or directly:

```bash
chromium --app=file:///opt/pisces-moon/html/silas_creek_parkway.html
```

It has four tabs:

**SPEED** - Real Cloudflare speed tests (download via `speed.cloudflare.com/__down`, upload measured via `XMLHttpRequest` upload events to handle CORS restrictions on `file://` origins). Canvas charts for download/upload/ping over time, plus a download distribution histogram. GOOD/FAIR/POOR quality badges. CSV/JSON export. Auto-test interval.

**LOG** - Test history with timestamps and quality color coding.

**NETWORKS** - Two views toggled by buttons:
- *Networks*: nearby APs with SSID, BSSID, RSSI, channel, band (2.4G/5G), security, vendor, signal bar. Channel congestion chart at the bottom.
- *Devices*: connected LAN devices with IP, MAC, hostname, vendor, online status, ping latency. Device-type icons inferred from hostname/vendor.

**PACKETS** - Live 802.11 management frame stream. Frame types: probe-req, probe-resp, beacon, deauth, disassoc, auth, assoc-req/resp, action. Deauth flood detection (>=10/sec critical), probe storm detection (>=20/sec warning). Channel selector. Threat alert bar.

When the bridge isn't running, the NETWORKS tab gracefully degrades to showing what the browser can see via `navigator.connection` (effective type, downlink, RTT) and provides the exact command to start the bridge.

---

## System requirements

**Minimum:**
- Debian 13 (Trixie) or newer Debian-based distribution
- 2 GB RAM
- 4 GB free disk space
- WiFi adapter (built-in is fine)
- Python 3.11+

**Recommended:**
- 4 GB+ RAM if running multiple apps simultaneously
- A second WiFi adapter that supports monitor mode if you want concurrent network use + packet capture
- ESP32-S3 edge node for richer captures and GPS tagging

**Tested platforms:**
- Fujitsu Q508 tablet (Atom x5, primary test machine)
- Lenovo Yoga AMD
- Generic x86_64 laptops
- ARM64 (works but you'll need to source ARM64 versions of any closed-source components)

---

## Manual install / advanced setup

If you don't want to run `install.sh` as-is, the script is documented and idempotent. The key steps are:

```bash
# 1. Install dependencies
sudo apt install -y chromium network-manager onboard \
    xfce4-battery-plugin xfce4-pulseaudio-plugin python3

# 2. Copy app tree
sudo mkdir -p /opt/pisces-moon
sudo cp -r html tools /opt/pisces-moon/

# 3. Generate desktop files (script does this for all 76 apps)
# See scripts/install.sh lines ~150-300 for the loop

# 4. Set up bridge as user service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/pisces-moon-bridge.service <<'EOF'
[Unit]
Description=Pisces Moon bridge (T-Beam relay or native WiFi scan)
After=graphical-session.target network.target

[Service]
Type=simple
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/python3 /opt/pisces-moon/tools/silas_creek_bridge.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now pisces-moon-bridge
```

---

## Verifying the bridge

After install, confirm the bridge is healthy:

```bash
# Check service status
systemctl --user status pisces-moon-bridge

# View live logs
journalctl --user -u pisces-moon-bridge -f

# Test the WebSocket endpoint
python3 -c "
import socket
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('127.0.0.1', 8080))
    print('Bridge is listening on 8080')
except Exception as e:
    print(f'Cannot reach bridge: {e}')
"
```

You should see log lines like:

```
[INFO] Mode: NATIVE SCAN (Linux)
[INFO] WebSocket server listening on ws://127.0.0.1:8080
[INFO] CoreWLAN/Swift: found 9 networks
```

---

## Troubleshooting

**Bridge won't start:**
```bash
journalctl --user -u pisces-moon-bridge -n 50
```
Common cause: `nmcli` not installed. Run `sudo apt install network-manager`.

**App shows "EDGE OFFLINE" even though bridge is running:**
- Hard refresh the page (Ctrl+Shift+R)
- Open DevTools (F12), check Console for WebSocket errors
- Verify nothing else is on port 8080: `ss -tlnp | grep 8080`

**WiFi scan returns 0 networks:**
- Make sure NetworkManager owns your WiFi: `nmcli dev status`
- If you've manually configured `wpa_supplicant`, NetworkManager won't manage that interface
- On Linux, `nmcli` requires no special permissions for scan-only operations

**Packet capture says "not supported":**
- Linux: install `aircrack-ng` for `airmon-ng`, or just use tcpdump with raw monitor interface
- macOS Apple Silicon: hardware-locked, no software workaround
- Windows: connect a T-Beam edge node

**T-Beam not detected:**
- Check `dmesg | tail -20` for USB enumeration messages
- Verify the user is in the `dialout` group: `groups`. If not: `sudo usermod -aG dialout $USER` and log out / back in
- Manually test: `cat /dev/ttyACM0` (or `/dev/ttyUSB0`) - you should see streaming JSON

**Apps don't appear in menu:**
- Rebuild the desktop database: `sudo update-desktop-database /usr/share/applications/`
- Verify XDG_DATA_DIRS includes `/usr/share`: `echo $XDG_DATA_DIRS`

---

## Project layout

```
pisces-moon/
├── README.md                  This file
├── LICENSE                    AGPL-3.0-or-later
├── COMMERCIAL.md              Commercial licensing terms
├── CLA.md                     Contributor License Agreement
├── CONTRIBUTING.md            How to contribute
├── INSTALL.md                 Detailed install notes
├── NOTICE                     Third-party attributions
├── install.sh                 One-shot installer (run with sudo)
├── html/                      All 76 HTML apps
│   ├── silas_creek_parkway.html
│   ├── about.html
│   ├── ... (74 more)
├── tools/
│   └── silas_creek_bridge.py  The bridge service (no pip deps)
├── scripts/                   Install helpers
├── docs/
│   ├── ANDROID_GUIDE.md       Android APK build instructions
│   ├── BLE_GATT_SPEC.md       BLE GATT protocol for ESP32 mesh
│   ├── MESH_APPS_DESCRIPTION.md
│   ├── MIGRATION_GUIDE.md     Upgrading from prior versions
│   ├── SECURITY_SUITE.md      Cyber tools documentation
│   ├── SOS_MESH_README.md
│   ├── UNIFIED_ARCHITECTURE.md  Cross-platform architecture
│   └── UPGRADE_DESCRIPTIONS.md
└── android/                   Android APK source (separate build)
```

---

## Updating

```bash
cd pisces-moon
git pull
sudo ./install.sh
systemctl --user restart pisces-moon-bridge
```

The install script is idempotent - it overwrites existing files but doesn't touch user data (Field Notes, saved Recipes, etc. are stored in `~/.local/share/pisces-moon/`).

---

## Uninstall

```bash
systemctl --user disable --now pisces-moon-bridge
rm ~/.config/systemd/user/pisces-moon-bridge.service
sudo rm -rf /opt/pisces-moon
sudo rm /usr/share/applications/pisces-moon-*.desktop
sudo update-desktop-database /usr/share/applications/
```

User data in `~/.local/share/pisces-moon/` is preserved unless you remove it manually.

---

## Privacy and data handling

Per the Clark Beddows Protocol:

- **No telemetry.** The bridge does not phone home. The apps don't either. Network traffic from the install is limited to the speed test endpoints (Cloudflare) and any APIs you explicitly invoke (MLB, news scrapers).
- **Local storage only.** Field Notes, saved recipes, search history, app settings - all stored under `~/.local/share/pisces-moon/`. No cloud sync. Export with `tar czf backup.tar.gz ~/.local/share/pisces-moon/`.
- **No accounts.** No registration, no login, no API key prompts (except for optional features you opt into).
- **Source visible.** Every app is a single HTML file you can open in a text editor. The bridge is one Python file. Read it. Modify it.

---

## Licensing

Pisces Moon is **AGPL-3.0-or-later**. See `LICENSE` for the full text and `COMMERCIAL.md` for commercial licensing options.

A signed CLA is required for code contributions. See `CLA.md`.

The Clark Beddows Protocol itself is a philosophical framework, not a license. Use it freely; we'd appreciate attribution.

---

## Credits

**Built by Eric Becker / Fluid Fortune** under the moniker "Court Jester of Vibe Coding."

Dedicated to **Jennifer Soto** and **Clark Beddows** (also known as Mark Meadows).

Bridge service named after **Silas Creek Parkway** in Winston-Salem, NC - inspired by Ben Folds Five's "Hospital Song."

Contact: fluidfortune.com

---

```
PISCES  ☾  MOON
Local-first. No gatekeepers. The user owns everything.
```
