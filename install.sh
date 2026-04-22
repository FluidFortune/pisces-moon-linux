#!/usr/bin/env bash
# Pisces Moon OS — install.sh
# Copyright (C) 2026 Eric Becker / Fluid Fortune
# SPDX-License-Identifier: AGPL-3.0-or-later
# fluidfortune.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# See licenses/LICENSE-AGPL.txt for full terms.
#
# Dedicated to Jennifer Soto and Clark Beddows.
# ═══════════════════════════════════════════════════════════════════
#  PISCES MOON OS — INSTALL SCRIPT v0.3.1
#  Debian 13 (Trixie) + XFCE 4.18  —  FRESH MINIMAL INSTALL
#  Target: Fujitsu Stylistic Q508 (1280×800 touchscreen)
#
#  REQUIRES: Run via SSH from Mac or directly on Q508
#    chmod +x install.sh
#    sudo ./install.sh
#
#  PLACE IN SAME DIRECTORY:
#    pisces-moon-html-apps.zip   (required)
#    pisces-moon-1280x800.jpg    (optional — wallpaper)
#
#  Author: Eric Becker / FluidFortune.com / 2026
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────
CY='\033[0;36m'; GR='\033[0;32m'; YL='\033[0;33m'
RD='\033[0;31m'; NC='\033[0m'; BD='\033[1m'

step() { echo -e "\n${CY}▶${NC} ${BD}$1${NC}"; }
ok()   { echo -e "  ${GR}✓${NC} $1"; }
warn() { echo -e "  ${YL}⚠${NC}  $1"; }
info() { echo -e "    $1"; }

confirm() {
    local msg="$1" default="${2:-y}" reply
    read -rp "  ? $msg [$default] " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy]$ ]]
}

# ── Must run as root ─────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo -e "${RD}Run with sudo:${NC}  sudo ./install.sh"
    exit 1
fi

# ── Who is the real user (not root) ──────────────────────────────────
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${CY}${BD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CY}${BD}║     PISCES MOON OS  v0.3  —  INSTALLER       ║${NC}"
echo -e "${CY}${BD}║   Debian 13 + XFCE 4.18 + Q508 Tablet        ║${NC}"
echo -e "${CY}${BD}╚══════════════════════════════════════════════╝${NC}"
echo ""
ok "User: $REAL_USER  (home: $REAL_HOME)"
ok "Script dir: $SCRIPT_DIR"

# ── Touch screen detection ──────────────────────────────────────────────
# Auto-detect touchscreen via libinput. Works on any device.
# Falls back to user prompt if detection is ambiguous.
HAS_TOUCH=false
if command -v libinput &>/dev/null; then
    if libinput list-devices 2>/dev/null | grep -qi "touch"; then
        HAS_TOUCH=true
    fi
fi
# Fallback: check for known touch device entries in sysfs
if ! $HAS_TOUCH; then
    if ls /sys/class/input/*/capabilities/abs 2>/dev/null | xargs grep -l "$(printf '%0.s0' {1..6})0" &>/dev/null; then
        HAS_TOUCH=true
    fi
fi
# Manual override if auto-detect uncertain and no DISPLAY
if ! $HAS_TOUCH && [[ -z "${DISPLAY:-}" ]]; then
    if confirm "Does this device have a touchscreen?"; then
        HAS_TOUCH=true
    fi
fi
$HAS_TOUCH && ok "Touchscreen detected — libinput touch config will be applied" || ok "No touchscreen detected — skipping touch config"

# ══════════════════════════════════════════════════════════════════
# 1. SYSTEM PACKAGES
# ══════════════════════════════════════════════════════════════════
step "Installing system packages"

apt-get update -qq

apt-get install -y --no-install-recommends \
    `# Python` \
    python3 python3-pip python3-venv \
    python3-pygame python3-requests python3-pil \
    python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
    \
    `# Browser — Chromium for HTML apps` \
    chromium \
    \
    `# Touch keyboard` \
    onboard \
    \
    `# Network / CYBER tools` \
    nmap curl wget net-tools iproute2 \
    wireless-tools network-manager \
    \
    `# Audio` \
    pipewire pipewire-pulse wireplumber \
    alsa-utils \
    \
    `# Fonts` \
    fonts-dejavu fonts-liberation \
    \
    `# XFCE extras` \
    xfce4-terminal xfce4-goodies \
    xdg-utils xdg-user-dirs \
    \
    `# Ghost partition` \
    parted dosfstools cryptsetup util-linux \
    \
    `# Edge bridge deps` \
    python3-websockets python3-serial \
    \
    `# Utilities` \
    unzip ssh openssh-server \
    jq htop lsb-release \
    2>/dev/null \
    && ok "System packages installed" \
    || warn "Some packages may have failed — continuing"

# Enable SSH for future remote access
systemctl enable ssh 2>/dev/null && ok "SSH enabled" || true

# ══════════════════════════════════════════════════════════════════
# 2. PYTHON PACKAGES
# ══════════════════════════════════════════════════════════════════
step "Installing Python packages"

pip3 install --break-system-packages -q \
    requests websockets pyserial pillow psutil \
    && ok "Python packages installed" \
    || warn "Some pip packages may have failed"

# ══════════════════════════════════════════════════════════════════
# 3. DIRECTORY STRUCTURE
# ══════════════════════════════════════════════════════════════════
step "Creating directory structure"

mkdir -p /opt/pisces-moon/{html,apps,tools,docs}
chmod 755 /opt/pisces-moon

# ~/.pisces-moon — T-Deck compatible data layout
sudo -u "$REAL_USER" mkdir -p \
    "$REAL_HOME/.pisces-moon" \
    "$REAL_HOME/.pisces-moon/data/"{gemini,medical,survival,baseball,trails,wardrive} \
    "$REAL_HOME/.pisces-moon/"{logs,vault,music,recordings} \
    "$REAL_HOME/.pisces-moon/logs/wardrive"

ok "Created /opt/pisces-moon/"
ok "Created $REAL_HOME/.pisces-moon/ (T-Deck compatible)"

# ══════════════════════════════════════════════════════════════════
# 4. DEPLOY HTML APPS
# ══════════════════════════════════════════════════════════════════
step "Deploying HTML apps"

HTML_ZIP="$SCRIPT_DIR/pisces-moon-html-apps.zip"

if [[ -f "$HTML_ZIP" ]]; then
    rm -rf /tmp/pm-extract
    mkdir -p /tmp/pm-extract
    unzip -o -q "$HTML_ZIP" -d /tmp/pm-extract/

    # Handle zip with or without subdirectory wrapper
    if ls /tmp/pm-extract/pisces-moon-html/*.html &>/dev/null; then
        cp /tmp/pm-extract/pisces-moon-html/*.html /opt/pisces-moon/html/
    elif ls /tmp/pm-extract/*.html &>/dev/null; then
        cp /tmp/pm-extract/*.html /opt/pisces-moon/html/
    else
        # Look one level deeper
        find /tmp/pm-extract -name "*.html" -exec cp {} /opt/pisces-moon/html/ \;
    fi
    rm -rf /tmp/pm-extract

    chmod 644 /opt/pisces-moon/html/*.html
    HTML_COUNT=$(ls /opt/pisces-moon/html/*.html 2>/dev/null | wc -l)
    ok "Deployed $HTML_COUNT HTML apps to /opt/pisces-moon/html/"
else
    warn "HTML ZIP not found: $HTML_ZIP"
    warn "Place pisces-moon-html-apps.zip next to install.sh and re-run"
fi

# ══════════════════════════════════════════════════════════════════
# 5. EDGE BRIDGE
# ══════════════════════════════════════════════════════════════════
step "Installing edge bridge"

cat > /opt/pisces-moon/tools/edge_bridge.py << 'BRIDGE_EOF'
#!/usr/bin/env python3
"""
PISCES MOON OS — Edge Bridge v1.0
Relays T-Deck Plus serial data to HTML apps via WebSocket.

Run:  python3 /opt/pisces-moon/tools/edge_bridge.py
SSH:  python3 /opt/pisces-moon/tools/edge_bridge.py --port /dev/ttyUSB0

Listens: ws://localhost:5006
Author:  Eric Becker / FluidFortune.com / 2026
"""

import asyncio, json, argparse, logging, sys
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

logging.basicConfig(level=logging.INFO, format='[BRIDGE] %(message)s')
log = logging.getLogger('edge_bridge')

clients = set()
last_data = {}

async def broadcast(msg: dict):
    if not clients:
        return
    payload = json.dumps(msg)
    dead = set()
    for ws in clients:
        try:
            await ws.send(payload)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)

async def ws_handler(websocket, path=None):
    clients.add(websocket)
    log.info(f"Client connected ({len(clients)} total)")
    try:
        if last_data:
            await websocket.send(json.dumps({"type": "snapshot", "data": last_data}))
        async for message in websocket:
            try:
                cmd = json.loads(message)
                log.info(f"App cmd: {cmd}")
            except Exception:
                pass
    except Exception:
        pass
    finally:
        clients.discard(websocket)
        log.info(f"Client disconnected ({len(clients)} remaining)")

def find_tdeck():
    if not HAS_SERIAL:
        return None
    ESPRESSIF_VIDS = [0x303A, 0x10C4, 0x1A86]
    for port in serial.tools.list_ports.comports():
        if hasattr(port, 'vid') and port.vid in ESPRESSIF_VIDS:
            log.info(f"T-Deck detected: {port.device}")
            return port.device
    return None

def parse_line(line: str):
    line = line.strip()
    if not line:
        return None
    if line.startswith('{'):
        try:
            return json.loads(line)
        except Exception:
            pass
    parts = line.split(',')
    if len(parts) >= 11:
        try:
            return {
                "type": "wifi",
                "bssid": parts[0], "ssid": parts[1],
                "channel": int(parts[4]) if parts[4].isdigit() else 0,
                "rssi": int(parts[5]) if parts[5].lstrip('-').isdigit() else -99,
                "lat": float(parts[6]) if parts[6] else 0,
                "lon": float(parts[7]) if parts[7] else 0,
            }
        except Exception:
            pass
    if line.startswith('['):
        return {"type": "log", "msg": line, "ts": datetime.now().isoformat()}
    return None

async def serial_reader(port: str, baud: int):
    if not HAS_SERIAL:
        log.warning("pyserial not installed — serial disabled")
        while True:
            await asyncio.sleep(30)
        return
    log.info(f"Opening {port} @ {baud}")
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except Exception as e:
        log.error(f"Cannot open {port}: {e}")
        log.info("Running WebSocket-only mode")
        while True:
            await asyncio.sleep(30)
        return
    log.info(f"T-Deck connected on {port}")
    await broadcast({"type": "bridge", "status": "connected", "port": port})
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, ser.readline)
            if line:
                msg = parse_line(line.decode('utf-8', errors='replace'))
                if msg:
                    last_data[msg.get('type', 'raw')] = msg
                    await broadcast(msg)
        except Exception as e:
            log.warning(f"Serial error: {e}")
            await asyncio.sleep(1)

async def main(port, baud, ws_port):
    if not HAS_WS:
        log.error("websockets not installed: pip3 install websockets")
        return
    log.info(f"Edge Bridge starting — ws://localhost:{ws_port}")
    if not port:
        port = find_tdeck()
        if not port:
            log.warning("No T-Deck detected — WebSocket ready, awaiting serial")
    ws_server = await websockets.serve(ws_handler, "localhost", ws_port)
    log.info(f"WebSocket ready: ws://localhost:{ws_port}")
    await asyncio.gather(
        ws_server.wait_closed(),
        serial_reader(port or "", baud)
    )

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", default=None)
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--ws-port", type=int, default=5006)
    args = p.parse_args()
    try:
        asyncio.run(main(args.port, args.baud, args.ws_port))
    except KeyboardInterrupt:
        sys.exit(0)
BRIDGE_EOF

chmod +x /opt/pisces-moon/tools/edge_bridge.py
ok "Edge bridge installed"

# ══════════════════════════════════════════════════════════════════
# 6. DESKTOP ENTRIES
# ══════════════════════════════════════════════════════════════════
step "Installing desktop entries"

APPS_DIR="/usr/share/applications"

# Each entry: "Display Name|Comment|icon|filename"
declare -a APP_LIST=(
    "Wardrive Smelter|CYBER — WiFi wardrive analyzer|network-wireless|wardrive"
    "Net Scanner|CYBER — nmap network scanner|network-workgroup|net_scanner"
    "BT Radar|CYBER — Bluetooth device radar|bluetooth|bt_radar"
    "Beacon Spotter|CYBER — AirTag/tracker detection|security-high|beacon_spotter"
    "Pkt Sniffer|CYBER — Live packet capture|network-transmit|pkt_sniffer"
    "Hash Tool|CYBER — MD5/SHA hash calculator|accessories-calculator|hash_tool"
    "GPS|COMMS — GPS map and waypoints|applications-internet|gps_app"
    "WiFi Connect|COMMS — Network manager|network-wireless|wifi_app"
    "SSH Client|COMMS — SSH terminal|utilities-terminal|ssh_client"
    "Voice Terminal|COMMS — AI voice interface|audio-input-microphone|voice_terminal"
    "Mesh Messenger|COMMS — LoRa mesh messaging|network-transmit|mesh_messenger"
    "Notepad|TOOLS — Text editor|text-editor|notepad"
    "Calculator|TOOLS — Scientific calculator|accessories-calculator|calculator"
    "Clock|TOOLS — Clock, stopwatch, timer|clock|clock"
    "Calendar|TOOLS — Calendar and events|office-calendar|calendar"
    "Etch|TOOLS — Drawing canvas|applications-graphics|etch"
    "Filesystem|TOOLS — File browser|system-file-manager|filesystem"
    "Gemini Terminal|INTEL — AI chat|applications-internet|gemini_terminal"
    "Gemini Log|INTEL — Session archive|document-open-recent|gemini_log"
    "Baseball Intel|INTEL — AI baseball data|applications-internet|baseball"
    "Trails Intel|INTEL — AI trail finder|applications-internet|trails"
    "Medical Reference|INTEL — Medical reference|help-faq|medical_ref"
    "Survival Reference|INTEL — Field survival guide|help-faq|survival_ref"
    "Audio Player|MEDIA — Music player|audio-x-generic|audio_player"
    "Audio Recorder|MEDIA — Microphone recorder|audio-input-microphone|audio_recorder"
    "System Info|SYSTEM — System dashboard|preferences-system|system_info"
    "Ghost Partition|SYSTEM — Encrypted MicroSD|security-high|ghost_partition"
    "PIN Screen|SYSTEM — Lock screen|system-lock-screen|pin_screen"
    "About|SYSTEM — Platform info|dialog-information|about"
)

for entry in "${APP_LIST[@]}"; do
    IFS='|' read -r name comment icon file <<< "$entry"
    cat > "$APPS_DIR/pisces-${file//_/-}.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PM // $name
Comment=$comment
Exec=chromium --app=file:///opt/pisces-moon/html/${file}.html
Icon=$icon
Categories=PiscesMoon;
Terminal=false
StartupNotify=false
EOF
done

ok "Installed ${#APP_LIST[@]} desktop entries"

# ══════════════════════════════════════════════════════════════════
# 7. PISCES MOON MENU CATEGORY
# ══════════════════════════════════════════════════════════════════
step "Registering app category in XFCE menu"

mkdir -p /usr/share/desktop-directories

cat > /usr/share/desktop-directories/pisces-moon.directory << 'EOF'
[Desktop Entry]
Version=1.0
Type=Directory
Name=Pisces Moon
Comment=Field Intelligence Platform
Icon=applications-internet
EOF

# Merge into xdg menus
mkdir -p /etc/xdg/menus/applications-merged

cat > /etc/xdg/menus/applications-merged/pisces-moon.menu << 'EOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
  "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<Menu>
  <Name>Applications</Name>
  <Menu>
    <Name>Pisces Moon</Name>
    <Directory>pisces-moon.directory</Directory>
    <Include>
      <Category>PiscesMoon</Category>
    </Include>
  </Menu>
</Menu>
EOF

update-desktop-database "$APPS_DIR" 2>/dev/null || true
ok "Pisces Moon menu category registered"

# ══════════════════════════════════════════════════════════════════
# 8. XFCE APPEARANCE
# ══════════════════════════════════════════════════════════════════
step "Configuring XFCE appearance"

# Must run as real user with DISPLAY set
if [[ -n "${DISPLAY:-}" ]]; then
    sudo -u "$REAL_USER" bash << XFCE_EOF
    # Dark theme
    xfconf-query -c xsettings -p /Net/ThemeName -s "Adwaita-dark" 2>/dev/null || true
    # Monospace font
    xfconf-query -c xsettings -p /Gtk/FontName -s "Liberation Mono 11" 2>/dev/null || true
    # DPI — scaled for 10" 1280x800
    xfconf-query -c xsettings -p /Xft/DPI -s 120 2>/dev/null || true
    # Compositor on
    xfconf-query -c xfwm4 -p /general/use_compositing -s true 2>/dev/null || true
    echo "  XFCE settings applied"
XFCE_EOF
    ok "XFCE appearance configured (dark theme, DPI 120, compositor on)"
else
    warn "No DISPLAY — writing XFCE config files directly instead"
    # Write xfconf XML directly so it takes effect on next login
    XFCONF_DIR="$REAL_HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
    sudo -u "$REAL_USER" mkdir -p "$XFCONF_DIR"

    sudo -u "$REAL_USER" cat > "$XFCONF_DIR/xsettings.xml" << 'XSET_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xsettings" version="1.0">
  <property name="Net" type="empty">
    <property name="ThemeName" type="string" value="Adwaita-dark"/>
    <property name="IconThemeName" type="string" value="hicolor"/>
  </property>
  <property name="Gtk" type="empty">
    <property name="FontName" type="string" value="Liberation Mono 11"/>
    <property name="CursorThemeName" type="string" value="default"/>
  </property>
  <property name="Xft" type="empty">
    <property name="DPI" type="int" value="120"/>
    <property name="Antialias" type="int" value="1"/>
    <property name="HintStyle" type="string" value="hintfull"/>
  </property>
</channel>
XSET_EOF

    sudo -u "$REAL_USER" cat > "$XFCONF_DIR/xfwm4.xml" << 'XFWM_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0">
  <property name="general" type="empty">
    <property name="use_compositing" type="bool" value="true"/>
    <property name="theme" type="string" value="Default-hdpi"/>
  </property>
</channel>
XFWM_EOF
    ok "XFCE config files written (take effect on next login)"
fi

# ══════════════════════════════════════════════════════════════════
# 9. WALLPAPER
# ══════════════════════════════════════════════════════════════════
step "Setting wallpaper"

WALLPAPER_DIR="/usr/share/pixmaps/pisces-moon"
mkdir -p "$WALLPAPER_DIR"
WALLPAPER_DEST="$WALLPAPER_DIR/pisces-moon-1280x800.jpg"

if [[ -f "$SCRIPT_DIR/pisces-moon-1280x800.jpg" ]]; then
    cp "$SCRIPT_DIR/pisces-moon-1280x800.jpg" "$WALLPAPER_DEST"
    ok "Wallpaper installed from file"
else
    # Generate fallback dark grid wallpaper
    python3 - << 'PY_EOF' 2>/dev/null && true
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (1280, 800), color=(5, 10, 14))
    draw = ImageDraw.Draw(img)
    for x in range(0, 1280, 40):
        draw.line([(x,0),(x,800)], fill=(10,22,30), width=1)
    for y in range(0, 800, 40):
        draw.line([(0,y),(1280,y)], fill=(10,22,30), width=1)
    # Accent lines
    draw.line([(0,400),(1280,400)], fill=(0,50,70), width=1)
    draw.line([(640,0),(640,800)], fill=(0,50,70), width=1)
    img.save('/usr/share/pixmaps/pisces-moon/pisces-moon-1280x800.jpg', quality=95)
    print("  Fallback wallpaper generated")
except Exception as e:
    print(f"  Wallpaper generation failed: {e}")
PY_EOF
    ok "Fallback dark wallpaper generated"
    info "Replace with your own: cp yourfile.jpg $WALLPAPER_DEST"
fi

# Write wallpaper setting to xfconf XML (works with or without DISPLAY)
XFCONF_DIR="$REAL_HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
sudo -u "$REAL_USER" mkdir -p "$XFCONF_DIR"

sudo -u "$REAL_USER" cat > "$XFCONF_DIR/xfce4-desktop.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
          <property name="image-style" type="int" value="5"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.019608"/>
            <value type="double" value="0.039216"/>
            <value type="double" value="0.054902"/>
            <value type="double" value="1.000000"/>
          </property>
        </property>
      </property>
    </property>
  </property>
</channel>
EOF
ok "Wallpaper config written"

# ══════════════════════════════════════════════════════════════════
# 10. TOUCH KEYBOARD AUTOSTART
# ══════════════════════════════════════════════════════════════════
step "Configuring touch keyboard (Onboard)"

AUTOSTART_DIR="$REAL_HOME/.config/autostart"
sudo -u "$REAL_USER" mkdir -p "$AUTOSTART_DIR"

sudo -u "$REAL_USER" cat > "$AUTOSTART_DIR/onboard.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Onboard
Comment=Touch keyboard
Exec=onboard --size=800x200
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
ok "Onboard touch keyboard set to autostart (800x200 — usable on 10\" display)"

# ══════════════════════════════════════════════════════════════════
# 11. TOUCH INPUT (Q508)
# ══════════════════════════════════════════════════════════════════
step "Touch input configuration"

if $HAS_TOUCH; then
    mkdir -p /etc/X11/xorg.conf.d
    cat > /etc/X11/xorg.conf.d/40-pisces-touch.conf << 'EOF'
Section "InputClass"
    Identifier       "Pisces Moon Touch"
    MatchIsTouchscreen "on"
    Driver           "libinput"
    Option           "Tapping"            "on"
    Option           "TappingDrag"        "on"
    Option           "TappingDragLock"    "off"
    Option           "NaturalScrolling"   "off"
    Option           "DisableWhileTyping" "off"
    Option           "PalmDetection"      "on"
    Option           "ClickMethod"        "none"
EndSection
EOF
    ok "Touch config written — takes effect on next login"
else
    info "Skipped (non-Q508)"
fi

# ══════════════════════════════════════════════════════════════════
# 12. GEMINI API KEY
# ══════════════════════════════════════════════════════════════════
step "Gemini API key"

KEYFILE="$REAL_HOME/.pisces-moon/gemini.key"

if [[ -f "$KEYFILE" ]]; then
    ok "Key already exists: $KEYFILE"
elif confirm "Set Gemini API key now? (free at aistudio.google.com)"; then
    read -rp "  Paste key: " GEMINI_KEY
    if [[ -n "$GEMINI_KEY" ]]; then
        echo "$GEMINI_KEY" > "$KEYFILE"
        chown "$REAL_USER:$REAL_USER" "$KEYFILE"
        chmod 600 "$KEYFILE"
        ok "Key saved to $KEYFILE (chmod 600)"
    fi
else
    info "Add later:  echo 'YOUR_KEY' > $KEYFILE && chmod 600 $KEYFILE"
fi

# ══════════════════════════════════════════════════════════════════
# 13. EDGE BRIDGE AUTOSTART
# ══════════════════════════════════════════════════════════════════
step "Edge bridge autostart"

if confirm "Auto-start edge bridge on login? (T-Deck USB integration)"; then
    sudo -u "$REAL_USER" cat > "$AUTOSTART_DIR/pisces-edge-bridge.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Pisces Moon Edge Bridge
Comment=T-Deck USB relay for HTML apps
Exec=python3 /opt/pisces-moon/tools/edge_bridge.py
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
    ok "Edge bridge autostart enabled"
else
    info "Start manually: python3 /opt/pisces-moon/tools/edge_bridge.py"
fi

# ══════════════════════════════════════════════════════════════════
# 14. DESKTOP SHORTCUTS
# ══════════════════════════════════════════════════════════════════
step "Creating desktop shortcuts"

sudo -u "$REAL_USER" mkdir -p "$REAL_HOME/Desktop"

declare -A SHORTCUTS=(
    ["PM — Smelter"]="wardrive.html|network-wireless"
    ["PM — Gemini Terminal"]="gemini_terminal.html|applications-internet"
    ["PM — System Info"]="system_info.html|preferences-system"
    ["PM — Net Scanner"]="net_scanner.html|network-workgroup"
    ["PM — GPS"]="gps_app.html|applications-internet"
)

for name in "${!SHORTCUTS[@]}"; do
    IFS='|' read -r file icon <<< "${SHORTCUTS[$name]}"
    DFILE="$REAL_HOME/Desktop/${name// /-}.desktop"
    sudo -u "$REAL_USER" bash -c "cat > '$DFILE'" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$name
Exec=chromium --app=file:///opt/pisces-moon/html/$file
Icon=$icon
Terminal=false
EOF
    chown "$REAL_USER:$REAL_USER" "$DFILE"
    chmod +x "$DFILE"
done
ok "5 desktop shortcuts created"

# ══════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════
HTML_COUNT=$(ls /opt/pisces-moon/html/*.html 2>/dev/null | wc -l || echo 0)

echo ""
echo -e "${CY}${BD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CY}${BD}║           INSTALLATION COMPLETE               ║${NC}"
echo -e "${CY}${BD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GR}Installed:${NC}"
echo -e "  HTML apps:     /opt/pisces-moon/html/  ($HTML_COUNT apps)"
echo -e "  Edge bridge:   /opt/pisces-moon/tools/edge_bridge.py"
echo -e "  Menu:          Applications > Pisces Moon"
echo -e "  Data dir:      $REAL_HOME/.pisces-moon/"
echo -e "  Touch keyboard: Onboard (autostart)"
echo ""
echo -e "${YL}Log out and log back in — then everything is active.${NC}"
echo ""
echo -e "${CY}Open any app directly:${NC}"
echo -e "  chromium --app=file:///opt/pisces-moon/html/gemini_terminal.html"
echo -e "  chromium --app=file:///opt/pisces-moon/html/wardrive.html"
echo ""
echo -e "${NC}Pisces Moon OS v0.3 — Eric Becker / FluidFortune.com / 2026${NC}"
echo ""
