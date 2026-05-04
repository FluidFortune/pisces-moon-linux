<!--
  Pisces Moon OS — INSTALL.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Pisces Moon OS — Installation Guide

This guide covers installing Pisces Moon OS as a Linux distribution layer on top of Debian 13. For Android APK installation, see the separate `pisces-moon-apk-v0.5` package.

---

## Hardware requirements

**Minimum:**
- Any x86-64 machine with 2 GB RAM
- 8 GB of disk space
- 1024×600 or larger display (touchscreen recommended)

**Recommended:**
- Fujitsu Stylistic Q508 tablet (the primary development target — 1280×800 touchscreen, Atom x5-Z8550)
- 4 GB RAM
- 16 GB disk
- USB-OTG support (for T-Beam mesh integration)

**Tested platforms:**
- Fujitsu Q508 (Debian 13 + XFCE 4.18)
- MacBook with Asahi Linux (ARM via box64)
- Generic x86-64 laptops
- Spadra Server (Intel N150) — server use only

---

## Prerequisites

You need a working Debian 13 (Trixie) install with:

- A regular user account with sudo privileges
- Internet access during install (downloads ~500 MB of Debian packages)
- The Pisces Moon repo cloned locally

If you're starting from a blank machine, see [`docs/FROM_SCRATCH_GUIDE.md`](docs/FROM_SCRATCH_GUIDE.md) for the full Debian 13 install walkthrough.

---

## Installation

### Option 1: Clone and run (recommended)

```bash
# Clone the repo to your local machine
git clone https://github.com/FluidFortune/pisces-moon.git
cd pisces-moon

# Run the installer (requires sudo)
sudo ./install.sh

# After install completes, run the post-install fixes
sudo ./scripts/install_fixes.sh

# Log out and log back in for XFCE to pick up changes
```

### Option 2: From a downloaded zip

```bash
# Download the release zip
wget https://github.com/FluidFortune/pisces-moon/releases/download/v0.5.0/pisces-moon-linux-v0.5.zip

# Extract
unzip pisces-moon-linux-v0.5.zip
cd pisces-moon-linux-v0.5

# Run installer
sudo ./install.sh
sudo ./scripts/install_fixes.sh
```

### Option 3: Single-machine offline install

If the target machine has no network, do this on a machine that does:

```bash
git clone --depth 1 https://github.com/FluidFortune/pisces-moon.git
# Pre-download Debian packages used by install.sh:
# (see scripts/install.sh for the full list — apt-get download <pkg>)
tar czf pisces-moon-offline.tar.gz pisces-moon/ debs/
```

Copy the tarball to the target via USB, extract, and run `sudo ./install.sh` as normal. The installer detects pre-downloaded debs and uses them.

---

## What the installer does

1. **Creates `/opt/pisces-moon/`** with subdirectories `html/`, `apps/`, `tools/`, `docs/`
2. **Installs Debian packages**: xfce4, chromium, python3, network-manager, bluez, alsa-utils, fonts-dejavu/liberation, plus a curated set of XFCE plugins
3. **Copies all 76 HTML apps** to `/opt/pisces-moon/html/` along with `pm_fonts.css`, `pm_transport.js`, `lib/` (third-party JS), and `fonts/` (woff2 files)
4. **Installs `edge_bridge.py`** to `/opt/pisces-moon/tools/` (handles serial-to-WebSocket relay for cyber apps that talk to T-Beam)
5. **Generates desktop entries** in `~/.local/share/applications/` for every app — they show up in the XFCE app menu and right-click desktop menu under a "Pisces Moon" submenu, organized by category
6. **Configures Chromium app-mode launchers** — apps open as standalone windows (no browser chrome)
7. **Sets up systemd user service** for `edge_bridge.py` (optional autostart)

The post-install `scripts/install_fixes.sh` adds:
- Battery indicator in the XFCE panel
- Auto-applies the wallpaper (live, not just on next login)
- Repopulates the right-click desktop menu so all apps appear

---

## After install

### Launching apps

Three ways:

1. **Right-click the desktop** → Pisces Moon submenu → category → app
2. **XFCE app menu** (top-left or wherever you put it) → Pisces Moon
3. **Direct command line**:
   ```bash
   chromium --app=file:///opt/pisces-moon/html/flashlight.html
   ```

### First-launch behavior

Most apps just work. A few request additional permissions or setup:

| App | First-launch |
|---|---|
| `gps_app.html`, `sun_moon.html`, `tides.html`, `offline_maps.html`, `compass.html` (auto-decl) | Browser asks for location permission. Approve. |
| `barcode.html`, `qr_tool.html`, `flashlight.html` (torch), `audio_recorder.html` | Browser asks for camera/mic. Approve. |
| `gemini_terminal.html`, `recipes.html` (URL scraping) | Asks for a Gemini API key. Get one free from https://aistudio.google.com/app/apikey, paste it in. Stored locally. |
| `wardrive.html`, `net_scanner.html`, `pkt_sniffer.html`, `ble_gatt.html`, `port_scanner.html`, etc. (cyber suite) | Will show "DISCONNECTED" until you start the bridge. |
| `vault.html` | Sets a 4-8 digit PIN on first use. PIN unlocks AES-256-GCM encrypted store. |

### Starting the bridge (for cyber apps)

The cyber suite talks to a T-Beam over USB-serial via `edge_bridge.py`:

```bash
# Plug in T-Beam via USB
# Bridge auto-detects serial port
python3 /opt/pisces-moon/tools/edge_bridge.py

# Or specify port explicitly:
python3 /opt/pisces-moon/tools/edge_bridge.py --port /dev/ttyUSB0
```

The bridge listens on `ws://localhost:5006`. HTML apps connect automatically through `pm_transport.js`.

To start the bridge automatically at login:

```bash
systemctl --user enable pisces-moon-bridge
systemctl --user start pisces-moon-bridge
```

(The systemd unit was installed by `install.sh`.)

---

## Troubleshooting

### "Right-click menu shows no apps"

Run `sudo ./scripts/install_fixes.sh` — this rebuilds the XDG menu XML.

### "Apps open in regular browser tabs instead of standalone windows"

The desktop entries are pointing at `chromium` but you have `chromium-browser` or vice versa. Check `which chromium`. If it's missing, edit the desktop entries in `~/.local/share/applications/pm-*.desktop` to use the correct binary name.

### "Wallpaper doesn't apply"

```bash
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -s /opt/pisces-moon/wallpaper.jpg
```

(Adjust monitor name as needed — use `xfconf-query -c xfce4-desktop -lv` to list current paths.)

### "Cyber app shows DISCONNECTED forever"

1. Is `edge_bridge.py` running? `ps aux | grep edge_bridge`
2. Is the T-Beam plugged in and powered on? `ls /dev/ttyUSB*` should show a device
3. Is the user in the `dialout` group? `sudo usermod -a -G dialout $USER`, then log out/in
4. Check bridge logs: `journalctl --user -u pisces-moon-bridge -f`

### "Chromium says insecure / mixed content"

Some apps load HTTPS APIs (NOAA tides, OSM tiles). If your network blocks HTTPS to those domains, those apps will fail. The apps remain functional offline — they just can't fetch new data.

### "Fonts look like default monospace"

Verify the fonts deployed:
```bash
ls /opt/pisces-moon/html/fonts/
```
Should show 4 woff2 files. If missing, re-run `install.sh`.

If the fonts are present but still don't show, check that `pm_fonts.css` is also present in `/opt/pisces-moon/html/` and that your Chromium has font loading enabled (`chrome://settings/fonts`).

---

## Updating

```bash
cd pisces-moon
git pull
sudo ./install.sh   # idempotent — safe to re-run
```

The installer detects existing files and only updates what's changed. Your localStorage data (vault contents, contacts, notes, custom medical/survival pages, habits, etc.) is in browser storage and is **not** affected by reinstalls.

To wipe localStorage and start fresh:

```bash
# Quit all Pisces Moon app windows first
rm -rf ~/.config/chromium/Default/Local\ Storage/leveldb/*
```

(Warning: this also wipes any other Chromium app data.)

---

## Uninstalling

```bash
sudo rm -rf /opt/pisces-moon/
rm ~/.local/share/applications/pm-*.desktop
systemctl --user disable pisces-moon-bridge 2>/dev/null
```

XFCE itself, Chromium, and all the Debian packages are not removed — those are general-purpose system packages.

---

## Custom hardware setups

### Fujitsu Q508 (primary target)

The installer auto-detects Q508 by checking for the 1280×800 panel. If detected, it:
- Sets the rotation correctly
- Configures the on-screen keyboard
- Enables the touchscreen calibration
- Sets the panel layout for tablet use

If you have a Q508 but auto-detection fails, set `IS_Q508=true` at the top of `scripts/install.sh` before running.

### MacBook with Asahi Linux (ARM)

Chromium for ARM Linux is shipped as a snap package on Ubuntu but not standard Debian. Two options:

1. Install Firefox instead and patch the desktop entries:
   ```bash
   sed -i 's|chromium --app=|firefox --kiosk |g' ~/.local/share/applications/pm-*.desktop
   ```

2. Install x86 Chromium under `box64`:
   ```bash
   # Outside scope of this guide — see box64 docs
   ```

### Server-only deploy (no GUI)

For a headless server (like Spadra running Wozbot), skip XFCE entirely and just deploy the HTML files:

```bash
sudo mkdir -p /opt/pisces-moon/html
sudo cp -r html/. /opt/pisces-moon/html/
sudo python3 -m http.server 8080 --directory /opt/pisces-moon/html
# Now access via http://server-ip:8080/about.html from another machine
```

---

## Going further

- [`docs/UNIFIED_ARCHITECTURE.md`](docs/UNIFIED_ARCHITECTURE.md) — Linux + Android + T-Deck unified architecture
- [`docs/PM_PROTOCOL.md`](docs/PM_PROTOCOL.md) — Clark Beddows Protocol details
- [`docs/SECURITY_SUITE.md`](docs/SECURITY_SUITE.md) — Cyber suite usage and authorization notes
- [`docs/SOS_MESH_README.md`](docs/SOS_MESH_README.md) — SOS beacon and mesh architecture
- [`docs/ANDROID_GUIDE.md`](docs/ANDROID_GUIDE.md) — Android Trojan Horse setup (older v0.4 guide; v0.5 APK uses different architecture)

---

## Need help?

- Open a GitHub issue
- Email eric@fluidfortune.com (commercial / sensitive matters only)

— Eric Becker / Fluid Fortune / fluidfortune.com
