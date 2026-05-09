<!--
  Pisces Moon Apps - README.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  fluidfortune.com
-->

# Pisces Moon — App Suite

**77 self-contained HTML apps. No installer. No accounts. No cloud.**

```
   PISCES  ☾   MOON
   ─────────────────────
   Drop the folder anywhere. Open webapptest.html. Done.
```

> Dedicated to Jennifer Soto and Clark Beddows.

---

## Quick start

1. **Unzip** `pisces-moon-apps.zip` to any folder — Desktop, Downloads, USB drive, anywhere.
2. **Open `webapptest.html`** in Chrome (Edge or Chromium-based browser also work; Safari has limitations).
3. **That's it.** All 77 apps load from the launcher.

For full WiFi intelligence (live scanning, packet capture, BLE), also run the bridge:

```sh
sudo python3 pm_bridge.py
```

(Bridge is a separate file. The apps work without it — they just won't have live radio data.)

---

## What you get

A glass-cinematic launcher with category filtering, live search, real-time clock, bridge status indicator, and an animated scanline. Click any app card to launch it in a new tab.

### Categories

**FEATURED** — Flagship apps that showcase what Pisces Moon does best
**CYBER** — WiFi/Bluetooth scanning, packet capture, security tools
**COMMS** — Mesh radio, SOS beacon, SSH, voice/AI terminals
**FIELD** — GPS, weather, trails, compass, tides, sun/moon, offline maps
**TOOLS** — Calculator, notepad, calendar, QR/barcode, password gen
**NEWS** — General, world, tech, finance, local news aggregators
**SPORTS** — NFL, NBA, NHL, MLS, baseball with live data
**MEDIA** — Audio recorder/player, video player, etch sketchpad
**GAMES** — Chess, Snake, Tetris, Galaga, Pac-Man, SimCity, more
**SYSTEM** — Vault, contacts, habits, system info, file browser

### Featured apps

| App | What it does |
|---|---|
| **Silas Creek Parkway** | WiFi intelligence dashboard — speed test, AP scan, LAN devices, packet capture |
| **Field Notes** | Encrypted local journal with markdown, tagging, full-text search |
| **Recipes** | JSON-LD recipe scraper with 6 default recipes; works offline after first scrape |
| **Trails** | 24 iconic US hiking trails with Leaflet maps and difficulty markers |
| **Medical Reference** | CPR, Heimlich, anaphylaxis, stroke, burns, hypothermia, more — no internet needed |
| **Survival Reference** | STOP protocol, shelter, water, fire, navigation, signaling, edible plants |

### Cyber tools

WiFi: WarDrive, Beacon Spotter, Probe Intel, WiFi Connect, WPA Handshake, WiFi Ducky
Packets: Packet Sniffer, Packet Analysis, RF Spectrum, Net Scanner, Port Scanner
Bluetooth: BT Radar, BLE GATT, BLE Ducky
Other: USB Ducky, Hash Tool, Ghost Partition, Spadra Smelter (CSV analyzer)

### Comms

Mesh Messenger, SOS Beacon, SSH Client, Voice Terminal, Gemini Terminal, Gemini Log

---

## Requirements

**Browser:** Chrome 100+ recommended. Edge, Chromium, Brave all work.
Safari works for most apps but has spotty WebSocket and limited Web Bluetooth support.

**For full functionality:** Run `pm_bridge.py` alongside the launcher (Python 3.11+, no pip dependencies).

**For live RF intelligence:** Connect a Pisces Moon edge node (T-Deck Plus or T-Beam) via USB-C. The bridge auto-detects it.

---

## How the bridge works

When `pm_bridge.py` is running on `ws://127.0.0.1:8080`, the bridge status pill in the launcher header turns green (BRIDGE ONLINE).

Apps that need radio data (Silas Creek, WarDrive, Beacon Spotter, BLE GATT, etc.) connect to the bridge automatically. Apps that just need internet (news, weather, sports, recipes) use your device's WiFi/ethernet directly — no bridge required.

**Bridge data sources, in order:**

1. **T-Deck Plus / T-Beam edge node** (if plugged in via USB) — richest data, GPS-tagged, monitor mode capture
2. **Native OS WiFi radio** (macOS CoreWLAN, Linux nmcli, Windows netsh) — full AP scan, no monitor mode
3. **No bridge running** — apps degrade gracefully to `navigator.connection` info where possible

The bridge protocol auto-detects which mode to use at startup. You don't configure anything.

---

## Privacy

Per the Clark Beddows Protocol:

- **No telemetry.** No app phones home. The launcher and apps run entirely client-side.
- **No accounts.** No registration, no login, nothing to sign up for.
- **Local storage only.** Notes, recipes, contacts, habits all live in browser localStorage. Export anytime.
- **Source visible.** Every app is a single HTML file. Open it in a text editor. Modify it.
- **Network calls are explicit.** When an app fetches from the internet (news, weather, sports, recipes), it's only the public APIs needed for that specific feature. No third-party trackers, no analytics SDKs.

---

## File layout

After unzipping you'll see:

```
pisces-moon-apps/
├── webapptest.html          ← OPEN THIS to launch the suite
├── silas_creek_parkway.html ← Flagship WiFi intelligence app
├── about.html, ... (76 more apps)
├── pm_transport.js          ← Bridge connection library (inlined into apps that need it)
├── pm_fonts.css             ← Shared typography
├── fonts/                   ← Orbitron, Share Tech Mono web fonts
└── lib/                     ← Leaflet (maps), jsQR, ZXing (barcode), QRCode
```

You can also open any individual app directly without the launcher — they're all standalone. For example, double-clicking `recipes.html` opens just that app.

---

## Keyboard shortcuts

In the launcher:
- `/` — focus the search bar
- `ESC` — clear the search
- Click any category pill to filter
- Click DEBUG button (in apps that have it) for live diagnostic log

---

## Browser data

Apps store data using browser localStorage scoped to the file location. To back up:

**Chrome on Mac:**
```sh
~/Library/Application Support/Google/Chrome/Default/Local Storage/leveldb/
```

**Easier:** Use the Export button most apps provide (Field Notes, Recipes, Habits, etc.) to download JSON/CSV.

To wipe all Pisces Moon data: open Chrome DevTools → Application tab → Local Storage → right-click → Clear.

---

## Troubleshooting

**Only Silas Creek Parkway works, others go nowhere**
You don't have the full app folder. Unzip `pisces-moon-apps.zip` and open `webapptest.html` from inside the unzipped folder. The launcher needs all 77 sibling HTML files to launch them.

**"BRIDGE OFFLINE" in the launcher header**
The bridge isn't running. Either start `pm_bridge.py` or just use the apps that don't need it (news, sports, recipes, games, tools — most of the suite).

**App opens but doesn't show data**
- Apps using internet APIs (news, weather, sports) need a live internet connection
- Apps using the bridge (WarDrive, Silas Creek Networks tab) need the bridge running
- Click the DEBUG button if available — it'll show what's happening

**Maps don't load (Trails, GPS, Offline Maps)**
Leaflet needs the `lib/` folder with map tile assets. Make sure you unzipped the full archive, not just the HTML files.

**Web Fonts look wrong**
Make sure the `fonts/` folder is in the same directory as the HTML files. The launcher and many apps use Orbitron and Share Tech Mono.

---

## On Android

Drop the unzipped folder anywhere on your phone (internal storage, SD card, Syncthing-synced folder). Open `webapptest.html` in Chrome. All apps that don't need the bridge work normally.

For bridge access on Android:
- **Bluetooth path:** Pair a T-Deck via Web Bluetooth — `pm_transport.js` falls back to BLE automatically when no WebSocket is available
- **USB-OTG path:** Plug T-Deck into phone via USB-C, T-Deck does the radio work
- **Termux path:** Install Termux + Python, run `pm_bridge.py` inside Termux (works but less elegant)

---

## On Windows

Same idea — unzip, open `webapptest.html` in Chrome. The bridge works on Windows via `netsh wlan show networks mode=bssid` for AP scans. Packet capture isn't supported natively on Windows; use a T-Deck if you need it.

---

## Updating

Replace the folder with a new zip. localStorage data is preserved per-origin (the file path), so as long as the folder name and location stay the same, your data persists.

---

## Licensing

AGPL-3.0-or-later. See `LICENSE` in the parent project. Commercial licenses available via fluidfortune.com.

The HTML apps are designed to be hackable. Open them in a text editor, study them, fork them, send pull requests. The whole suite is one HTML file per app — no build step, no transpilation, no framework lock-in.

---

## Credits

Built by **Eric Becker / Fluid Fortune** under the moniker "Court Jester of Vibe Coding."

Dedicated to **Jennifer Soto** and **Clark Beddows** (also known as Mark Meadows).

Bridge service named after **Silas Creek Parkway** in Winston-Salem, NC — inspired by Ben Folds Five's "Hospital Song."

Contact: fluidfortune.com

---

```
PISCES  ☾  MOON
77 apps. One folder. No friction.
```
