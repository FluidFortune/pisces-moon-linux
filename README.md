# PISCES MOON OS — LINUX XFCE BRANCH
### v0.3 — April 2026

**A resource. Not a dependency.**

Pisces Moon Linux is the desktop/field branch of Pisces Moon OS — a local-first
intelligence platform built on the principle that your machine should work for you
without asking permission from anyone else.

This branch targets x86-64 and ARM devices running Debian 13 (Trixie) or compatible
distributions with XFCE. The HTML apps run in Chromium `--app=` mode as frameless
windows. When the Trojan Horse WebKitGTK wrapper ships, the `Exec=` line in each
`.desktop` file swaps out and every app upgrades automatically.

---

## HARDWARE TARGETS

### Primary (XFCE Branch)
| Device | CPU | RAM | Notes |
|--------|-----|-----|-------|
| Crelander P8 | Intel N150 | 16GB | Primary target |
| Chuwi Minibook X | Intel N150 | 16GB | Primary target |
| Surface Pro 7 | Intel Core | 8-16GB | linux-surface kernel recommended |
| Any x86-64 laptop | — | 4GB+ | Install script handles it |

### Extended (ARM)
| Device | CPU | RAM | Notes |
|--------|-----|-----|-------|
| Raspberry Pi 4/5 | ARM Cortex-A72/A76 | 4GB+ | Debian arm64, see ARM section |
| Any ARM64 SBC | — | 2GB+ | Debian arm64 + XFCE |

### Legacy / Low-Spec
| Device | CPU | RAM | Notes |
|--------|-----|-----|-------|
| ASUS i5 4th gen laptop | Intel Core i5 | 8GB+ | Full experience |
| MacBook Air 2017 | Intel Core i5 | 8GB | Broadcom WiFi needs extra step |
| Fujitsu Stylistic Q508 | Intel Atom X5 | 4GB | See Q508 note |

The install script is hardware-agnostic. It detects what it finds and configures
accordingly. Touch screens get libinput config. Non-touch machines skip it silently.

---

## QUICK START — x86-64

### Prerequisites
- Debian 13 (Trixie) minimal install with XFCE
  - Or Ubuntu 24.04 LTS with XFCE (`sudo apt install xfce4`)
  - Or any Debian-based distro with XFCE
- Internet connection for package installation
- `sudo` access

### Installation
```bash
# 1. Download or clone this package
# 2. Place install.sh and pisces-moon-html-apps.zip in the same directory
# 3. Run:

chmod +x install.sh
sudo ./install.sh
```

Log out and log back in. Everything activates on next login.

### What the installer does
1. Installs system packages (Chromium, Python 3, networking tools, audio)
2. Auto-detects touchscreen → applies libinput config if found
3. Deploys 37 HTML apps to `/opt/pisces-moon/html/`
4. Installs the edge bridge service (T-Deck / T-Beam USB integration)
5. Sets wallpaper (custom or generated dark grid fallback)
6. Creates desktop shortcuts for key apps
7. Configures Onboard touch keyboard (if touch device detected)
8. Optionally sets Gemini API key

### Manual app launch
```bash
chromium --app=file:///opt/pisces-moon/html/wardrive.html
chromium --app=file:///opt/pisces-moon/html/gemini_terminal.html
chromium --app=file:///opt/pisces-moon/html/baseball.html
```

---

## QUICK START — ARM (Raspberry Pi / Debian arm64)

Pisces Moon Linux runs on ARM **without any porting required.**

The HTML apps are pure HTML/CSS/JavaScript — they run identically in Chromium
on ARM as they do on x86-64. The install script is also architecture-agnostic.

### Tested ARM configurations
- Raspberry Pi 4 (4GB/8GB) — Raspberry Pi OS (64-bit) or Debian Bookworm arm64
- Raspberry Pi 5 — Raspberry Pi OS (64-bit)
- Generic ARM64 SBC running Debian arm64

### ARM installation
**Identical to x86-64:**
```bash
chmod +x install.sh
sudo ./install.sh
```

The script detects ARM and skips any x86-specific steps automatically.

### ARM performance notes
- **Raspberry Pi 4** — Full experience. All 37 apps run smoothly. Chromium
  is heavier on the Pi than on N150, but perfectly usable.
- **Raspberry Pi 5** — Faster than most x86-64 laptops for this workload.
- **Older Pi (Pi 3, Pi 2)** — 32-bit only, not tested. May work with 32-bit
  Raspbian but not officially supported.
- **Apple Silicon (M1/M2/M3)** — Runs under Asahi Linux or Debian ARM.
  Chromium works. Not tested but should work fine.

### What does NOT work on ARM
All Pisces Moon Linux features work on ARM64. No exceptions.

### Debian arm64 setup (Pi 4/5)
```bash
# If starting from Raspberry Pi OS Lite (64-bit):
sudo apt update
sudo apt install -y xfce4 xfce4-goodies lightdm
sudo systemctl set-default graphical.target
sudo reboot

# Then run the Pisces Moon installer as normal
```

---

## SPECIAL CASES

### MacBook Air 2017 (Broadcom WiFi)
The MacBook Air 2017 uses a Broadcom BCM4360 WiFi chip that requires a
proprietary driver not included in the standard Debian kernel.

```bash
# After base Debian install, before running Pisces Moon installer:
sudo apt install -y broadcom-sta-dkms
sudo modprobe wl
```

Alternatively, use a USB WiFi adapter during installation to get online,
then install the Broadcom driver.

### Fujitsu Stylistic Q508
The Q508 (Intel Atom X5, 4GB RAM, 1280×800 touch) is not the primary target
for the XFCE branch but will run the full suite. Touch works via the Goodix
controller with the standard libinput config the installer applies.

Performance is noticeably slower than N150-class hardware. All apps run,
some heavier operations (wardrive map rendering, baseball stats loading)
may feel sluggish.

### Surface Pro 7
Install the linux-surface kernel for proper touch, pen, and battery support:
```bash
# Add linux-surface repo and install
# https://github.com/linux-surface/linux-surface/wiki/Installation-and-Setup
```
After linux-surface is installed, run the Pisces Moon installer normally.
Touch will be detected and configured automatically.

---

## APP INVENTORY (37 apps)

### CYBER Suite (14 apps)
| App | File | Description |
|-----|------|-------------|
| Wardrive / Smelter | wardrive.html | WiFi AP scanner and mapper |
| BT Radar | bt_radar.html | BLE device scanner |
| Packet Sniffer | pkt_sniffer.html | 802.11 frame capture |
| Beacon Spotter | beacon_spotter.html | Hidden network detection |
| Net Scanner | net_scanner.html | nmap frontend |
| Hash Tool | hash_tool.html | MD5/SHA-1/SHA-256 calculator |
| BLE GATT Explorer | ble_gatt.html | BLE service/characteristic enumeration |
| WPA Handshake | wpa_handshake.html | EAPOL capture → .hccapx export |
| RF Spectrum | rf_spectrum.html | RF spectrum waterfall analyzer |
| Probe Intel | probe_intel.html | WiFi probe request intelligence |
| Offline Pkt Analysis | pkt_analysis.html | Session log rules engine |
| BLE Ducky | ble_ducky.html | Wireless BLE HID injection |
| USB Ducky | usb_ducky.html | Local HID injection (xdotool/ydotool) |
| WiFi Ducky | wifi_ducky.html | Network payload delivery + C2 |

### COMMS (6 apps)
| App | File | Description |
|-----|------|-------------|
| WiFi Connect | wifi_app.html | Network manager |
| GPS | gps_app.html | GPS display and logging |
| Mesh Messenger | mesh_messenger.html | LoRa mesh messaging |
| Voice Terminal | voice_terminal.html | STT/TTS terminal |
| SSH Client | ssh_client.html | SSH session manager |
| Pin Screen | pin_screen.html | Authentication screen |

### INTEL (6 apps)
| App | File | Description |
|-----|------|-------------|
| Gemini Terminal | gemini_terminal.html | AI chat terminal |
| Gemini Log | gemini_log.html | Session history browser |
| Baseball Intel | baseball.html | Full MLB intelligence hub |
| Trails | trails.html | Trail/route reference |
| Medical Reference | medical_ref.html | Medical reference database |
| Survival Reference | survival_ref.html | Survival reference database |

### TOOLS (7 apps)
| App | File | Description |
|-----|------|-------------|
| Notepad | notepad.html | Text editor with SD/file save |
| Calculator | calculator.html | Scientific calculator |
| Clock | clock.html | Clock + stopwatch + NTP sync |
| Calendar | calendar.html | Calendar with NTP |
| Etch | etch.html | Drawing canvas |
| Filesystem | filesystem.html | File manager |
| Ghost Partition | ghost_partition.html | Encrypted partition manager |

### MEDIA (2 apps)
| App | File | Description |
|-----|------|-------------|
| Audio Player | audio_player.html | MP3/FLAC/AAC/OGG player |
| Audio Recorder | audio_recorder.html | Microphone recorder |

### SYSTEM (2 apps)
| App | File | Description |
|-----|------|-------------|
| System Info | system_info.html | Hardware/OS diagnostics |
| About | about.html | About Pisces Moon OS |

---

## EDGE BRIDGE (T-Deck / T-Beam USB Integration)

The edge bridge connects a USB-attached ESP32 device (T-Deck Plus or T-Beam S3)
to the HTML apps via WebSocket on `ws://localhost:5006`.

```bash
# Start manually
python3 /opt/pisces-moon/tools/edge_bridge.py

# Or with specific port
python3 /opt/pisces-moon/tools/edge_bridge.py --port /dev/ttyUSB0

# Enable autostart at login (installer asks this)
# File: ~/.config/autostart/pisces-edge-bridge.desktop
```

HTML apps check for the bridge on load. If unavailable, they fall back to
demo/simulated mode automatically — no errors, no crashes.

---

## DIRECTORY STRUCTURE

```
pisces-moon-linux/
├── install.sh                  ← Main installer (run this first)
├── README.md                   ← This file
├── html/                       ← All 37 HTML apps
│   ├── wardrive.html
│   ├── baseball.html
│   ├── ble_gatt.html
│   └── ... (37 total)
├── tools/
│   ├── edge_bridge.py          ← USB serial ↔ WebSocket bridge
├── licenses/
│   ├── LICENSE-AGPL.txt        ← Platform license (install.sh, tools)
│   └── LICENSE-MIT.txt         ← App license (html/ directory)
└── docs/
    └── (additional documentation)
```

---

## GEMINI API KEY

Several apps use the Google Gemini API for AI features. The key is free for
personal use at aistudio.google.com (15 requests/minute, 1M tokens/day).

```bash
# Set your key
echo 'YOUR_KEY_HERE' > ~/.pisces-moon/gemini.key
chmod 600 ~/.pisces-moon/gemini.key
```

The installer will prompt for this. You can skip it and add it later.

---

## DATA DIRECTORY

All app data lives in `~/.pisces-moon/` — compatible with the T-Deck Plus
SD card layout for easy sync between devices.

```
~/.pisces-moon/
├── gemini.key          ← Gemini API key (chmod 600)
├── data/
│   ├── gemini/         ← AI session logs
│   ├── medical/        ← Medical reference data
│   ├── survival/       ← Survival reference data
│   ├── baseball/       ← MLB player cache
│   ├── wardrive/       ← Wardrive logs
│   └── trails/         ← Trail data
├── logs/
│   └── wardrive/       ← Wardrive session logs
├── vault/              ← Encrypted/sensitive data
│   └── memories/       ← AI session vault
├── music/              ← Audio files for player
└── recordings/         ← Audio recordings
```

---

## LICENSING

| Component | License | Applies To |
|-----------|---------|------------|
| Platform | AGPL-3.0 | install.sh, edge_bridge.py, all build/tool scripts |
| Applications | MIT | All files in html/ directory |

**AGPL-3.0** — If you modify and deploy the platform (including as a networked
service), you must publish your modifications under the same terms.

**MIT** — The individual HTML apps may be used, modified, and distributed
freely including in commercial projects, with attribution.

Full license texts in `licenses/`.

Contributor License Agreement (CLA) required for contributions to the main
repository. Contact fluidfortune.com.

---

## PHILOSOPHY

> *The internet should be a resource, not a dependency.*
> *Intelligence runs on your metal.*

Pisces Moon OS is built on the Clark Beddows Protocol:
- **Local first** — works without internet, better with it
- **No gatekeepers** — no accounts, no subscriptions, no permissions
- **You own everything** — your data stays on your hardware
- **Open architecture** — every component is inspectable and replaceable

The XFCE branch extends this to any machine that can run Debian.
The laptop in your bag, the tablet on your desk, the SBC in your backpack —
same OS, same apps, same data format, different form factor.

---

## CREDITS

**Author:** Eric Becker / Fluid Fortune  
**Website:** fluidfortune.com  
**Version:** v0.3 — April 2026  

Dedicated to Jennifer Soto and Clark Beddows.

*The Clark Beddows Protocol. Your machine, your rules.*

---

## CHANGELOG

**v0.3 — April 2026 (XFCE Branch)**
- Removed Q508-specific assumptions from install.sh
- Added support for N150-class hardware (Crelander P8, Chuwi Minibook X)
- Added ARM64 support (Raspberry Pi 4/5, Debian arm64)
- 8 new CYBER apps: BLE GATT Explorer, WPA Handshake, RF Spectrum,
  Probe Intel, Offline Pkt Analysis, BLE Ducky, USB Ducky, WiFi Ducky
- Baseball Intel rebuilt as full intelligence hub (live MLB API, AI analyst)
- Player search with current season + career stats + biography
- RSS news feed with multi-source fallback and native XML parsing
- License headers added to all files (AGPL platform / MIT apps)

**v0.2 — March 2026**
- Initial XFCE branch from T-Deck Plus codebase
- 29 HTML apps ported from ESP32 C++ originals
- install.sh with Q508 touch config

**v0.1 — February 2026**
- T-Deck Plus v1.0.0 "The Arsenal" — 47 apps, 7 categories
