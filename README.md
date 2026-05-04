<!--
  Pisces Moon OS — README.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# Pisces Moon OS

**Local-first field intelligence OS. No cloud, no telemetry, no gatekeepers.**

```
   PISCES  ☾   MOON
   ─────────────────
   76 HTML apps. Zero install friction.
   Runs on Debian, Android, and beyond.
```

> Dedicated to Jennifer Soto and Clark Beddows.

---

## What is this?

Pisces Moon is a portable operating system built around the **Clark Beddows Protocol**: local-first, no external gatekeepers, the user owns everything. It's a single source tree that deploys to:

- **Linux** (Debian 13 + XFCE) on tablets and laptops
- **Android** (APK wrapper, separate build)

Additional embedded targets (mesh nodes, panels, keyboard terminals) are in active development under separate private repos. Contact for collaboration.

The user-facing apps are 76 self-contained HTML files. Each one is single-file, dependency-free where possible, and runs in a Chromium window with no chrome. No installer per app, no dependencies to track. Deploy with `cp`. Update with `git pull`.

---

## Quick start (Linux)

```bash
git clone https://github.com/FluidFortune/pisces-moon.git
cd pisces-moon
sudo ./install.sh
```

Logout and back in. Apps appear in your application menu under `PiscesMoon-Cyber`, `PiscesMoon-Tools`, etc.

Or run a single app from anywhere:

```bash
chromium --app=file:///opt/pisces-moon/html/about.html
```

Full installation guide: [`INSTALL.md`](INSTALL.md).

---

## App suite (76 apps)

| Category | Apps |
|---|---|
| **CYBER** (15) | Wardrive Smelter, Net Scanner, BT Radar, Beacon Spotter, Pkt Sniffer / Analysis, Hash Tool, Probe Intel, RF Spectrum, BLE GATT, BLE/USB/WiFi Ducky, WPA Handshake, Port Scanner |
| **COMMS** (7) | GPS, WiFi Connect, SSH Client, Voice Terminal, Mesh Messenger, SOS Beacon, Contacts |
| **TOOLS** (13) | Notepad, Calculator, Clock, Calendar, Etch, Filesystem, Field Notes, Flashlight, Compass, Pass Gen, Vault, QR Tool, Barcode |
| **INTEL** (12) | Gemini Terminal, Gemini Log, Baseball, Trails, Medical Ref, Survival Ref, Weather, Recipes, Sun & Moon, Tides, Body Metrics, Habits |
| **NEWS** (5) | General, World, Tech, Finance, Local |
| **SPORTS** (4) | NFL, NBA, NHL, MLS |
| **GAMES** (8) | SimCity, Pac-Man, Galaga, Chess, Snake, Tetris, Minesweeper, Breakout |
| **MEDIA** (3) | Audio Player, Audio Recorder, Video Player |
| **MAPS** (1) | Offline Maps |
| **SYSTEM** (4) | System Info, Ghost Partition, PIN Screen, About |
| **FLUID FORTUNE** (4) | Punky, Little Soul, Static, Spadra Smelter |

Every app follows a consistent design language (Share Tech Mono / Orbitron, dark scanline aesthetic, three-column layout for intel apps) and persists state to `localStorage` under namespaced `pm_*` keys.

---

## Repo layout

```
pisces-moon/
├── README.md                  ← You are here
├── INSTALL.md                 ← Linux install guide
├── LICENSE                    ← Full AGPL-3.0 text
├── NOTICE                     ← Third-party attributions
├── CLA.md                     ← Contributor License Agreement
├── COMMERCIAL.md              ← Commercial licensing path
├── install.sh                 ← Top-level wrapper (calls scripts/install.sh)
│
├── html/                      ← The 76 HTML apps + assets
│   ├── *.html
│   ├── pm_fonts.css
│   ├── pm_transport.js
│   ├── lib/                   ← Bundled JS libs (Leaflet, ZXing, jsQR, qrcode)
│   └── fonts/                 ← Local woff2 fonts
│
├── scripts/                   ← Install scripts
│   ├── install.sh             ← Main installer (called from top-level wrapper)
│   ├── install_fixes.sh       ← Display fixes (battery, wallpaper, menu)
│   └── debloat_crelander.sh   ← ADB script to debloat Crelander Android tablet
│
├── tools/                     ← Runtime utilities
│   └── edge_bridge.py         ← Hardware serial → WebSocket relay
│
├── android/                   ← Android-specific code (full APK in separate package)
│   └── SmsGateway.java        ← SMS service for sos_beacon mesh-over-SMS
│
└── docs/                      ← Architecture & deployment docs
    ├── UNIFIED_ARCHITECTURE.md
    ├── ANDROID_GUIDE.md
    ├── BLE_GATT_SPEC.md
    ├── SOS_MESH_README.md
    ├── SECURITY_SUITE.md
    ├── MIGRATION_GUIDE.md
    ├── MESH_APPS_DESCRIPTION.md
    └── UPGRADE_DESCRIPTIONS.md
```

---

## What works offline

Everything except where it explicitly can't:

✅ All 76 HTML apps (the runtime is just Chromium pointed at file:// URLs)
✅ All fonts (woff2 bundled in `html/fonts/`)
✅ All JS libraries (Leaflet, ZXing, jsQR, qrcodejs bundled in `html/lib/`)
✅ Medical reference (16 protocols)
✅ Survival reference (14 sections)
✅ Trails database (24 iconic US trails with offline maps)
✅ Sun/moon calculations (pure math, zero deps)
✅ Body metrics calculations
✅ Vault (AES-256-GCM, PBKDF2, all client-side)
✅ Passgen (Web Crypto API)

These need network at runtime:

🌐 Tides (NOAA CO-OPS) · Weather (NWS) · News feeds · Sports scores · Map tile fetch (cached after first load) · Barcode product lookup · Gemini AI

All HTTPS endpoints are explicitly listed in the Android `network_security_config.xml`. No telemetry. No analytics. No cookies.

---

## Hardware

Primary development & test devices:

- **Fujitsu Stylistic Q508** — primary Linux test machine (Atom x5, 1280×800 touchscreen)
- **MacBook Neo (Apple A18 Pro)** — general dev work
- **Crelander Android tablet** — Android APK target
- **Spadra Server (Intel N150)** — server-side (runs Wozbot)

The whole point is portability. Most apps don't care what they're running on.

---

## License

**AGPL-3.0-or-later** (see [`LICENSE`](LICENSE)) for all original code.

Bundled third-party libraries retain their own permissive licenses (BSD-2-Clause for Leaflet, Apache-2.0 for ZXing/jsQR, MIT for qrcodejs, OFL-1.1 for fonts) — see [`NOTICE`](NOTICE) for attribution.

**Commercial licenses available** for organizations that need to integrate Pisces Moon into closed-source products. See [`COMMERCIAL.md`](COMMERCIAL.md) or contact eric@fluidfortune.com.

Contributions are accepted under the terms of the [`CLA.md`](CLA.md) Contributor License Agreement.

The names "Pisces Moon", "Fluid Fortune", "Clark Beddows Protocol", "Punky", "Little Soul", "Static", "Spadra Smelter", and "Wozbot" are trademarks. Forks must rebrand.

---

## Credits

Pisces Moon OS is built by **Eric Becker** under the banner of **Fluid Fortune** (fluidfortune.com).

It is dedicated to **Jennifer Soto** and to **Clark Beddows** (a.k.a. Mark Meadows), whose protocol gives this work its center.

The Court Jester of Vibe Coding, signing off.
