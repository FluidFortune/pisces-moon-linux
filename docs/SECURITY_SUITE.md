<!--
  Pisces Moon OS — SECURITY_SUITE.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON OS — SECURITY SUITE
## Complete Field Intelligence Platform
### Version 0.5 — May 2026

**Eric Becker / Fluid Fortune / fluidfortune.com**
*The Clark Beddows Protocol — Local Intelligence. Your machine, your rules.*

---

> "Kali Linux requires a laptop, a full OS install, apt-get, a Python environment, Wireshark, aircrack-ng, kismet, and a user who knows what they're doing. Pisces Moon runs in Chrome on a $70 tablet. The receipt is still $70."

---

## WHAT THIS IS

Pisces Moon is a field intelligence platform — 14 specialized security tools that run as standard HTML files in any modern browser. No installation. No dependencies. No app store. No vendor. Open the file, do the work.

The security suite was designed to run on three platforms simultaneously from the same codebase:

- **Linux / XFCE** — native Chromium windows, edge bridge to hardware
- **Android** — self-contained APK with built-in USB bridge, no Termux required
- **Windows / macOS** — any Chromium-based browser, or wrapped as native apps via Trojan Horse

All 14 apps share a common transport abstraction (`pm_transport.js`) that auto-detects the available hardware connection and uses it transparently. The app developer — and the user — never has to think about which transport is in use.

---

## THE 14 SECURITY APPS

---

### 1. WARDRIVE
**File:** `wardrive.html`
**Category:** RF Intelligence / Passive Reconnaissance

**What it does:**
Passive WiFi network mapping with GPS correlation. Scans all 14 WiFi channels simultaneously, logs every detected network with BSSID, SSID, signal strength, channel, security type, and GPS coordinates. The flagship intelligence collection tool.

**Visualizations:**
- Live Leaflet map — networks appear as colored markers as they're detected, color-coded green (strong) → orange → red (weak) by signal strength
- Scrolling channel waterfall — heat map showing signal activity across channels 1-14 over time
- Security type donut chart — real-time breakdown of OPEN / WPA / WPA2 / WPA3 / WEP
- RSSI distribution bar chart — how many networks at each signal strength tier
- Top channels bar chart — which channels are most congested

**Data output:**
- Auto-saves every 60 seconds in WiGLE-compatible CSV format
- Manual save available at any time
- Files land at `/sdcard/PiscesMoon/wardrive_TIMESTAMP.csv` on Android
- Drop the CSV directly into Spadra Smelter for full intelligence analysis

**Hardware requirement:** T-Beam connected (WiFi scan command). GPS overlay requires GPS fix from T-Beam.

---

### 2. NET SCANNER
**File:** `net_scanner.html`
**Category:** Network Reconnaissance / Host Discovery

**What it does:**
Discovers all devices on the current local network, maps their open ports, identifies vendors by MAC OUI lookup, and runs automated threat detection. Equivalent to running nmap against a subnet but visualized in real time.

**Visualizations:**
- D3 force-directed topology map — devices as animated nodes, gateway at center, edges representing network relationships, node size scales with open port count, threat nodes highlighted in red
- Vendor distribution donut — who made the devices on this network
- Device detail panel — full port list, hostname, OS guess, first/last seen, scan count
- Latency sparkline — ping response time history for selected host

**Threat detection engine (6 threat types):**
1. **PORT SCAN** — device probing many different ports (>20 unique ports from one source)
2. **ARP STORM** — unusually high ARP traffic suggesting spoofing or network instability
3. **INSECURE SERVICE** — Telnet (23), FTP (21), RDP (3389), VNC (5900) detected open
4. **UNKNOWN VENDOR** — MAC address not in OUI database, possible spoofed MAC
5. **HIGH EXPOSURE** — more than 5 open ports on a single device
6. **BRIEF APPEARANCE** — device appeared and disappeared in under 30 seconds (scanner behavior)

**Data output:** Auto-saves host inventory as JSON every 60 seconds.

**Hardware requirement:** T-Beam or edge bridge for net scan commands. Visualization works in demo mode without hardware.

---

### 3. BT RADAR
**File:** `bt_radar.html`
**Category:** Bluetooth Intelligence / Device Tracking

**What it does:**
Passive Bluetooth Low Energy device scanner. Detects every BLE advertising device in range, tracks signal strength over time, identifies device vendors, and maintains a live count of unique devices seen. Works passively — no connection to detected devices required.

**Visualizations:**
- Animated bubble scatter — each detected device is a bubble, bubble size proportional to signal strength, bubbles drift with physics simulation, fade when device not recently seen
- Vendor breakdown donut — Apple vs Samsung vs Raspberry Pi vs Unknown, updates in real time
- RSSI distribution bar chart — signal strength histogram across all detected devices
- Per-device RSSI sparkline — select any device in the list to see its signal history
- Real-time RSSI bars — inline signal bars in the device list update live

**Tracking features:**
- New-devices-per-minute counter
- First seen / last seen timestamps
- Observation count per device
- Manufacturer data hex extraction
- Named vs unnamed device split

**Data output:** Save device inventory as JSON. Auto-save on interval.

**Hardware requirement:** T-Beam BLE scan mode.

---

### 4. BEACON SPOTTER
**File:** `beacon_spotter.html`
**Category:** BLE Beacon Intelligence

**What it does:**
Specialized detection and decoding of BLE beacon protocols. Where BT Radar tracks all BLE devices, Beacon Spotter specifically identifies and decodes beacon advertisement formats used by retail, asset tracking, and proximity systems.

**Supported beacon types:**
- iBeacon (Apple) — UUID, Major, Minor, TX Power
- Eddystone-URL / Eddystone-UID / Eddystone-TLM (Google)
- AltBeacon (Radius Networks)
- Generic proximity beacons

**Visualizations:**
- Signal strength waterfall — scrolling heat map showing beacon signal over time
- Beacon type distribution donut
- RSSI history sparkline for selected beacon
- Distance estimation based on RSSI and TX Power calibration

**Data output:** JSON save with full beacon decode data.

**Hardware requirement:** T-Beam BLE scan.

---

### 5. RF SPECTRUM ANALYZER
**File:** `rf_spectrum.html`
**Category:** Radio Frequency Analysis
**Note:** High bandwidth — USB/WebSocket transport only. BLE path insufficient for real-time RF data.

**What it does:**
Full radio frequency spectrum analyzer covering 433MHz, 868MHz, 915MHz, 2.4GHz, and 5GHz bands. Uses the T-Beam's SX1262 radio to sweep frequency ranges and display signal activity. Equivalent to a $200+ hardware spectrum analyzer.

**Visualizations:**
- Full scrolling waterfall display — the definitive spectrum visualization. Each row is a time slice, colors represent signal intensity from blue (weak) through green, yellow, orange, to red (strong). Reveals interference patterns invisible in single-sweep views.
- Live spectrum curve — current sweep as a filled gradient line with peak-hold overlay
- Peak hold line — maintains the highest observed signal at each frequency across the entire session
- Channel overlay — marks WiFi channels 1-14 on the 2.4GHz display, LoRa channels on 915/868MHz

**Anomaly detection:**
- **STRONG SIGNAL** — any signal more than 30dB above noise floor
- **JAMMING SUSPECTED** — signal more than 50dB above noise floor
- **BURST DETECTED** — sudden >25dB increase at a frequency
- **SIGNAL DROPOUT** — sudden >25dB decrease (device went offline or jamming started)

**Controls:**
- Band selector — switch between 2.4GHz WiFi, 5GHz WiFi, 915MHz LoRa, 868MHz LoRa, 433MHz ISM
- Waterfall / Spectrum / Both view modes
- Peak hold toggle
- Channel overlay toggle
- Cursor frequency readout on mouse hover
- Save snapshot as JSON

**Hardware requirement:** T-Beam SX1262 in frequency sweep mode. High bandwidth — requires USB or WebSocket transport.

---

### 6. PACKET SNIFFER
**File:** `pkt_sniffer.html`
**Category:** Network Traffic Analysis

**What it does:**
Captures raw network packets on the current WiFi connection and displays them with real-time protocol analysis. Provides a live view of network traffic without requiring Wireshark or tcpdump to be installed.

**Visualizations:**
- Traffic flow waterfall — rolling display of packet activity
- Protocol distribution donut — TCP vs UDP vs DNS vs HTTP breakdown
- RSSI sparkline — signal quality during capture

**Data output:** JSON save of captured packet summaries.

**Hardware requirement:** T-Beam in monitor mode or edge bridge with packet capture access.

---

### 7. PROBE INTEL
**File:** `probe_intel.html`
**Category:** WiFi Intelligence / Device Tracking

**What it does:**
Captures and analyzes WiFi probe requests — the packets devices broadcast when searching for previously connected networks. Probe analysis reveals what networks a device has connected to historically, even when no network is present.

**What probe requests reveal:**
- Previously connected network names (SSIDs)
- Device presence patterns (when someone arrives/leaves)
- Organization affiliations (corporate SSIDs in probes)
- Personal habits (home network names, café networks, hotel SSIDs)

**Visualizations:**
- Device and network distribution charts
- Timeline showing device activity windows
- Cross-reference: which devices are probing for the same networks (relationship mapping)
- OUI vendor lookup per probing device

**Threat context:** High probe density for a specific SSID indicates it's a high-value target for evil twin attacks. Networks being probed heavily from many devices are worth noting.

**Data output:** JSON save with full probe intelligence.

**Hardware requirement:** T-Beam in monitor mode.

---

### 8. PACKET ANALYSIS
**File:** `pkt_analysis.html`
**Category:** Deep Packet Inspection / Protocol Decoding
**Note:** High bandwidth — USB/WebSocket transport only.

**What it does:**
Full deep packet inspection with protocol hierarchy decoding. Equivalent to Wireshark's packet analysis workflow but running as a web app on any device. Decodes Ethernet → IP → TCP/UDP → Application layer protocols and displays structured field-by-field breakdowns.

**Protocol decoders:**
- Ethernet (MAC addresses, frame type)
- IP (source/destination, TTL, fragmentation)
- TCP (ports, flags, sequence numbers)
- UDP (ports, length)
- DNS (query domain, record type, response)
- HTTP (method, URL, host, response code)
- DHCP (message type, requested IP, hostname)
- MQTT (topic, QoS level)
- mDNS (local service discovery)
- ARP (who-has queries)
- ICMP (echo, type, code)

**Views:**
- **LIST** — Wireshark-style packet list with color-coded protocol column, filter bar, click-to-decode
- **CONVERSATIONS** — Groups packets by IP pair, shows total bytes and duration per conversation
- **ANOMALIES** — Flags suspicious patterns automatically

**Anomaly detection:**
- Port scan detection (>20 unique destination ports from one source)
- ARP storm detection (>20 ARP packets in last 50 captured)
- Insecure protocol usage (Telnet, FTP, HTTP flagged by name)

**Filter syntax:**
- `tcp` / `udp` / `dns` / `http` / `arp` / `icmp` — filter by protocol
- `ip=192.168.1.1` — filter by IP address
- `port=8080` — filter by port number
- Free text — searches all fields

**Bottom panel:**
- Protocol distribution donut
- Packets/second sparkline
- Packet size distribution bar chart
- Top talkers by bytes (top 6 IPs)

**Data output:** Saves last 1000 packets as JSON.

**Hardware requirement:** T-Beam or edge bridge with packet capture. USB/WebSocket only due to bandwidth requirements.

---

### 9. WPA HANDSHAKE CAPTURE
**File:** `wpa_handshake.html`
**Category:** Wireless Security Assessment

**What it does:**
Captures WPA2 4-way EAPOL handshakes for offline password assessment, and detects PMKID (a faster attack vector that doesn't require a client to be present). Exports in hashcat-compatible format for offline processing.

**How WPA2 cracking works:**
WPA2 uses a 4-way handshake to authenticate clients. If you capture this handshake, you can test whether a password matches offline without touching the network. This is a standard technique in authorized penetration testing. PMKID is an even newer method that only requires capturing a single packet from the access point, without waiting for a client connection.

**Visualizations:**
- Per-network frame capture tracker — 4 boxes showing which EAPOL frames (1/2/3/4) have been captured, color-coded green when captured
- PMKID capture indicator
- RSSI timeline during capture
- Channel distribution chart showing which channels have captured networks
- Per-network capture status badge (FULL / PARTIAL / PMKID / NONE)

**Export formats:**
- **Hashcat WPA*02** — the standard format for hashcat `-m 22000` mode, the current recommended approach for offline WPA2 assessment
- **HCCAPX** — legacy hashcat format for older tools
- **JSON session** — full session save including all metadata

**Deauth support:** Sends deauthentication frames to force a client to reconnect, triggering a new handshake capture. Standard penetration testing technique.

**Hardware requirement:** T-Beam in monitor mode with packet injection capability.

---

### 10. BLE GATT EXPLORER
**File:** `ble_gatt.html`
**Category:** Bluetooth Security Assessment / Device Analysis

**What it does:**
Full Bluetooth Low Energy Generic Attribute Profile (GATT) service explorer. Connects to any BLE device, discovers all services and characteristics, reads values, writes values, and subscribes to notifications. The BLE equivalent of a serial terminal.

**What GATT is:** BLE devices expose their functionality through a hierarchical structure. Services are functional groups (heart rate monitor, battery, environmental sensing). Characteristics are the actual data points within each service (current heart rate, battery percentage, temperature). GATT Explorer lets you browse and interact with all of these.

**Known service decoder:** 180+ standard Bluetooth SIG service and characteristic UUIDs decoded by name. Generic Access, Device Information, Battery, HID, Heart Rate, Environmental Sensing, Running Speed, and more all display with human-readable names.

**Operations:**
- **READ** — fetch the current value of any readable characteristic (displays hex, ASCII, and decimal)
- **WRITE HEX** — send raw hex bytes to a writable characteristic
- **WRITE ASCII** — send a text string to a writable characteristic
- **NOTIFY** — subscribe to a characteristic for continuous value updates

**Security display:**
- Connection security level (unauthenticated / authenticated / encrypted)
- Bonding status
- Negotiated MTU size

**Notification log:** All incoming notifications logged with timestamp, characteristic UUID, hex, and ASCII values. Persistent during the session.

**Device profile save:** Export the full GATT tree of a connected device as JSON for offline analysis.

**Hardware requirement:** T-Beam BLE in connect mode, or direct Web Bluetooth (Android Chrome/Chromium).

---

### 11. GHOST PARTITION
**File:** `ghost_partition.html`
**Category:** Secure Storage / Data Classification

**What it does:**
Hardware-secured encrypted storage partition with PIN authentication, data classification system, integrity verification, and nuclear data destruction. Based on the Ghost Partition architecture from Pisces Moon OS on the T-Deck Plus.

**PIN modes:**
- **Tactical PIN** — full access to all classified files
- **Student PIN** — access only to files classified as Student or Unclassified. Tactical files are hidden as if they don't exist.
- **3× wrong PIN** — automatic Nuke trigger

**Data classification levels:**
- ☢ **TACTICAL** — sensitive operational data, visible only in Tactical mode
- 👁 **DECOY** — files intended to be found, contain plausible but non-sensitive data
- 📚 **STUDENT** — training data, safe to expose in Student mode
- **UNCLASSIFIED** — no classification assigned

**Storage visualization:**
- Color-coded storage bar showing how much space each classification level uses
- Classification distribution donut chart
- Per-file integrity status (verified/unverified)

**Nuke function:**
Deletes only the index files that the OS uses to locate data. The raw bytes remain on storage but are permanently unreachable through the OS. Completes in under 100ms — fast enough to be operationally useful in a time-constrained seizure scenario. Based on the same threat model analysis documented in the Pisces Moon OS engineering record.

**Integrity verification:** Computes SHA256 hash of each file on verification and compares to stored hash. Detects tampering or corruption.

**No hardware requirement:** Ghost Partition runs entirely in the browser using localStorage for the web demo. On Android with the APK, it uses the native file bridge to write to protected storage.

---

### 12. USB DUCKY
**File:** `usb_ducky.html`
**Category:** HID Attack / Payload Delivery
**Transport:** USB HID (T-Beam in USB keyboard mode)

**What it does:**
Delivers DuckyScript keystroke injection payloads via USB HID. The T-Beam presents itself to the target computer as a USB keyboard. The target sees a keyboard. The payload types commands at the speed you configure.

**DuckyScript reference:**
```
DELAY 500          # Wait 500ms
STRING hello       # Type text literally
ENTER              # Press Enter key
GUI r              # Windows key + R (Run dialog)
GUI SPACE          # Cmd + Space (macOS Spotlight)
CTRL ALT t         # Ctrl+Alt+T (Linux terminal)
```

**Built-in quick payloads:**
- **Recon Windows** — opens PowerShell, runs whoami, hostname, ipconfig, net user
- **Recon macOS** — opens Terminal, runs whoami, hostname, ifconfig, id
- **Reverse Shell Template** — Python reverse shell with editable IP/PORT
- **WiFi Creds Dump** — Windows netsh command to export saved WiFi passwords

**Payload editor:** Full DuckyScript editor with line count, syntax display, save/load to local library, and per-payload OS targeting.

**Timing control:** Adjustable delay slider (0-500ms per keystroke) for matching target system response time.

**Execution log:** Real-time display of which commands are being sent, with timestamps.

---

### 13. BLE DUCKY
**File:** `ble_ducky.html`
**Category:** HID Attack / Payload Delivery
**Transport:** Bluetooth Low Energy HID

**What it does:**
Same DuckyScript payload delivery as USB Ducky but over Bluetooth HID. The T-Beam presents itself as a Bluetooth keyboard. No physical cable required — effective range depends on environment but typically 10-30 meters.

**Key difference from USB Ducky:**
The target must accept a Bluetooth keyboard pairing. On most systems this happens silently if the device is presented during a pairing window. On others it requires user confirmation. This is the primary operational constraint vs USB.

**Same payload library as USB Ducky** — payloads are transport-agnostic DuckyScript.

---

### 14. WIFI DUCKY
**File:** `wifi_ducky.html`
**Category:** HID Attack / Payload Delivery
**Transport:** WiFi Captive Portal

**What it does:**
Delivers payloads via a WiFi captive portal. The T-Beam creates a WiFi access point. When a target device connects, the captive portal intercepts their browser and serves a page that delivers the payload. Useful in scenarios where USB and Bluetooth are locked down but WiFi is available.

**Operational use case:** Conference rooms, hotel lobbies, public spaces where laptop USB ports may be physically blocked but the user will connect to available WiFi networks.

---

## THE SHARED LIBRARIES

All 14 apps depend on three shared files:

### `pm_transport.js` — Hardware Connection Abstraction
The magic layer that makes the same HTML app work on Linux, Android, and desktop. Auto-detects available transport in priority order:
1. Android native USB bridge (`window.PiscesAndroid`)
2. WebSocket to edge bridge (`ws://127.0.0.1:8080`)
3. Web Bluetooth (T-Beam BLE GATT)

Apps call `beam.connect()` and `beam.send()`. They never know which transport delivered the data.

### `pm_viz.js` — Visualization Library
All charts, maps, and real-time displays are drawn by this shared library:
- `RSSIWaterfall` — scrolling frequency/signal heat map
- `BarChart` — live horizontal and vertical bar charts
- `DonutChart` — protocol/vendor/classification distribution
- `BubbleScatter` — animated device bubble display with drift physics
- `Sparkline` — compact inline time series
- `GaugeArc` — signal strength arc gauge
- `LiveMap` — Leaflet.js map with live markers
- `Storage` — unified save to Android filesystem or browser download, WiGLE CSV export

### `pm_utils.js` — Shared Utilities
HTML escaping, localStorage wrapper, format helpers (bytes, time, duration), MAC vendor OUI lookup, signal quality labels.

---

## HOW IT WORKS ON LINUX

### Installation
```bash
# Unzip the package
unzip pisces-moon-linux-v0.5.zip

# Run the installer (sets up XFCE app entries, copies files to /opt/pisces-moon)
sudo ./install.sh

# Run the display fixes (battery indicator, wallpaper, right-click menu)
sudo ./install_fixes.sh
```

### Hardware connection
The T-Beam connects to the Linux machine via USB-C. The edge bridge converts the USB serial stream to a WebSocket that the HTML apps can consume.

```bash
# Start the hardware bridge (keep running in background)
python3 /opt/pisces-moon/tools/edge_bridge.py

# Each app auto-detects the WebSocket at ws://127.0.0.1:8080
```

### App launching
Each app launches as a standalone Chromium window with no browser chrome:
```bash
chromium --app=file:///opt/pisces-moon/html/wardrive.html
```

The XFCE menu entries created by `install.sh` handle this automatically. Each app appears in the Pisces Moon category with its icon.

### Data saves
On Linux, the `PMViz.Storage.save()` function triggers a browser download. Files land in your default Downloads folder unless a specific path is configured.

For automated saves (like wardrive's 60-second auto-save), a persistent download dialog will appear unless you've configured Chrome to auto-download to a folder. Recommended: set Chrome's download location to `/opt/pisces-moon/data/` and enable automatic downloads from file:// URLs.

---

## HOW IT WORKS ON ANDROID

### The APK
The Pisces Moon APK is a self-contained Android application that:
1. Loads all 46 HTML apps from its internal asset bundle
2. Displays them in a fullscreen WebView (Chromium rendering engine)
3. Bridges the WebView to the T-Beam via native Java USB serial code

No Termux. No Python. No extra apps. Install one APK, plug in the T-Beam, it works.

### Building the APK
1. Open the `apk-v2/` folder in Android Studio
2. Copy the contents of `html/` into `app/src/main/assets/html/`
3. Build → Generate Signed APK (or debug APK for testing)
4. Sideload: `adb install pisces-moon.apk`

### Hardware connection — USB path
1. Connect T-Beam to Android tablet via USB-C OTG cable
2. Android shows "Allow Pisces Moon to access [T-Beam]?" — tap Allow
3. The APK's native USB bridge opens the CDC serial interface
4. `pm_transport.js` detects `window.PiscesAndroid` and uses it automatically
5. Data flows: T-Beam → USB → APK Java bridge → WebView → HTML app

### Hardware connection — Bluetooth path
If OTG is unavailable or the tablet doesn't support USB host:
1. T-Beam firmware must implement the BLE GATT service (`ble_gatt_service.md`)
2. User taps "Connect" in any cyber app
3. Android system BLE pairing dialog appears
4. User selects "PiscesMoon-TBeam" from the list
5. `pm_transport.js` detects BLE availability and uses Web Bluetooth

### Data saves on Android
`PMViz.Storage.save()` calls `window.PiscesAndroid.saveFile(filename, content)` which writes to `/sdcard/PiscesMoon/` on the device's external storage.

Files are organized by app:
```
/sdcard/PiscesMoon/
├── wardrive_2026-05-03T14-22-00.csv     ← WiGLE format, Smelter-ready
├── netscan_2026-05-03T14-35-00.json
├── bt_radar_2026-05-03T15-01-00.json
├── pkt_analysis_2026-05-03T15-20-00.json
├── wpa_handshakes_2026-05-03T16-00-00.txt
└── rf_spectrum_2026-05-03T16-30-00.json
```

Pull files to Mac/PC via USB file transfer, ADB, or cloud sync for analysis.

### Recommended Android hardware
- Minimum: 3GB RAM, Android 7.0 (API 24), USB-C with OTG support
- Tested: Crelander 8.7" (6GB RAM, Unisoc T7300, Android 15)
- Optimal: Any tablet with Helio G99 + 8GB RAM (Alldocube iPlay 50 Mini Pro)
- GPS-dependent apps require tablet GPS or T-Beam GPS relay

---

## HOW IT WORKS ON WINDOWS AND MACOS

The same HTML files that run on Linux and Android work in any Chromium-based browser. This includes Chrome, Edge, Brave, and Opera on both Windows and macOS.

### Option 1: Direct in Browser (No install, no hardware)
1. Copy the `html/` folder anywhere on your machine
2. Open Chrome / Edge / Brave
3. Navigate to `file:///C:/path/to/html/wardrive.html` (Windows) or `file:///Users/you/html/wardrive.html` (macOS)
4. All passive apps work immediately — news, sports, medical reference, survival guide, recipes, trails
5. Cyber apps work in demo mode (simulated data) without hardware

### Option 2: With T-Beam via WebSocket Bridge
1. Install Python 3 (comes with macOS, download for Windows)
2. Connect T-Beam via USB-C
3. Install pyserial: `pip install pyserial websockets`
4. Run the edge bridge: `python3 edge_bridge.py`
5. Open any cyber app in Chrome
6. `pm_transport.js` detects the WebSocket at `ws://127.0.0.1:8080`
7. Live data flows from T-Beam to browser

This gives you full hardware capability on Windows and macOS without any OS-level installation. One Python script, one USB cable.

### Option 3: Trojan Horse (Native App Experience)
Trojan Horse (`github.com/FluidFortune/trojan-horse`) is a minimal WebKitGTK wrapper (~2MB) that turns any Pisces Moon HTML file into a native application. It exposes the `window.spadra` JavaScript bridge for filesystem and serial port access.

**What this gives you that the browser can't:**
- Direct serial port access without the edge bridge Python script
- Filesystem read/write at native paths
- Native desktop notifications
- App launcher integration (appears in Start Menu / Applications folder)
- No browser chrome — full screen, clean interface

**Installation:**
```bash
# macOS
brew install pisces-moon-trojan-horse   # (or build from source)
trojan-horse wardrive.html

# Windows (installer available)
trojan-horse.exe wardrive.html

# Linux
trojan-horse wardrive.html
```

**Building from source:**
```bash
git clone https://github.com/FluidFortune/trojan-horse
cd trojan-horse
./build.sh --platform=macos    # or windows, linux, android, ios
```

The application code never changes between platforms. The same `wardrive.html` that runs in Chrome also runs inside Trojan Horse on macOS with full hardware access. One codebase, five deployment targets.

### Option 4: Electron-style Packaging (Advanced)
For distribution as a standalone app without Trojan Horse:
1. Install Node.js and npm
2. `npm install -g electron`
3. Create a minimal `main.js` that loads your HTML
4. `electron-packager . --platform=win32` or `--platform=darwin`

This produces a distributable `.exe` (Windows) or `.app` (macOS) that includes a bundled Chromium. App size will be ~150-200MB vs ~2MB for Trojan Horse, but requires no runtime installation on the target machine.

### Browser compatibility
| Browser | Linux | macOS | Windows | Android | iOS |
|---------|-------|-------|---------|---------|-----|
| Chrome/Chromium | ✓ Full | ✓ Full | ✓ Full | ✓ Full | ✗ No Web BT |
| Edge | ✓ | ✓ | ✓ Full | ✓ | ✗ |
| Brave | ✓ | ✓ | ✓ | ✓ | ✗ |
| Firefox | ⚠ No Web BT | ⚠ | ⚠ | ⚠ | ✗ |
| Safari | ✗ | ✗ No Web BT | N/A | N/A | ✗ |

All apps work fully in any Chromium-based browser. Firefox works for passive apps but lacks Web Bluetooth support for cyber apps. Safari does not support Web Bluetooth on any platform.

---

## THE HARDWARE ECOSYSTEM

### T-Beam S3 Supreme (Sensor + Comms Brain)
The primary sensor node. Connects to Linux/Android/Desktop via USB-C or Bluetooth.

**Capabilities exposed to apps:**
- WiFi scanning (wardrive, net scanner, probe intel, WPA handshake)
- BLE scanning (BT radar, beacon spotter, BLE GATT)
- LoRa radio (RF spectrum, mesh communications)
- GPS (wardrive GPS tagging, GPS app)
- Environmental sensors (BME280: temperature, humidity, pressure)
- IMU (QMI8658: accelerometer, gyroscope)
- Battery status (AXP2101 PMU)

**Protocol:** All data transmitted as newline-terminated JSON over USB-CDC serial or BLE GATT characteristics.

---

## DATA PIPELINE — FROM FIELD TO ANALYSIS

```
T-Beam scans RF environment
         ↓
USB-C or BLE → HTML app receives JSON
         ↓
App visualizes in real time
         ↓
Auto-save every 60 seconds
         ↓
/sdcard/PiscesMoon/wardrive_TIMESTAMP.csv
         ↓
USB file transfer to Mac/PC
         ↓
Drop into Spadra Smelter (spadra-smelter.fluidfortune.com)
         ↓
Interactive heatmap + anomaly detection + OUI enrichment + export
```

Wardrive data saved by the Android app is WiGLE-compatible. Drop it into Smelter and receive:
- Interactive density heatmap
- Cluster markers for WiFi and BLE concentrations
- Evil twin and mobile hidden network anomaly detection
- MAC vendor enrichment from built-in OUI table
- GPS outlier filtering
- Export as CSV, printable map, or text anomaly report

---

## LICENSING

| Component | License | Who it's for |
|-----------|---------|-------------|
| `install.sh`, `install_fixes.sh` | AGPL-3.0 | Platform infrastructure — derivatives must open source |
| `edge_bridge.py` | AGPL-3.0 | Hardware bridge — derivatives must open source |
| APK source (`MainActivity.java`, etc.) | AGPL-3.0 | Native wrapper — derivatives must open source |
| All 14 HTML security apps | MIT | Use freely, modify freely, no copyleft requirement |
| `pm_transport.js`, `pm_viz.js`, `pm_utils.js` | MIT | Shared libraries — use in any project |
| `pm_shared.css` | MIT | Design system — use in any project |

The dual license is intentional. The platform infrastructure (AGPL) ensures that anyone who builds a commercial product on top of the Pisces Moon platform contributes their changes back. The application layer (MIT) has no such requirement — you can take `wardrive.html`, modify it for your use case, and never tell anyone. The tools are yours.

---

## VERSION HISTORY

| Version | Date | Highlights |
|---------|------|-----------|
| v0.1 | Feb 2026 | Initial prototype on T-Deck Plus |
| v0.2 | Mar 2026 | Q508 tablet support, 27 HTML apps |
| v0.3 | Apr 2026 | Cyber apps expansion, T-Deck edge bridge, dual licensing |
| v0.4 | Apr 2026 | 10 new intel apps, shared scraper library, Android Trojan Horse package |
| v0.5 | May 2026 | Unified architecture, transport abstraction, all 14 cyber apps upgraded with real-time visualization, self-contained Android APK with native USB bridge, auto-save to filesystem |

---

## CONTACT

**Eric Becker / Fluid Fortune**
forge@fluidfortune.com
fluidfortune.com

DEF CON 34 CFP Submission ID: 1349

*"The Ghost Engine never stops. The SPI Bus Treaty is why."*

*"A resource. Not a dependency."*

---

*Pisces Moon OS — Fluid Fortune — May 2026*
*Dedicated to Jennifer Soto and Clark Beddows*
*The Clark Beddows Protocol — Local Intelligence — Your machine, your rules*
