#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  PISCES MOON OS — INSTALL SCRIPT v0.5
#  Copyright (C) 2026 Eric Becker / Fluid Fortune
#  SPDX-License-Identifier: AGPL-3.0-or-later
#
#  Debian 13 (Trixie) + XFCE 4.18 — FRESH MINIMAL INSTALL
#  Primary target: Fujitsu Stylistic Q508 (1280×800 touchscreen)
#  Also tested: generic x86-64 laptops, MacBook Asahi (with caveats)
#
#  USAGE:
#    sudo ./install.sh
#
#  Run from the root of the cloned repo, OR from the scripts/ directory.
#  Auto-detects the html/ folder relative to this script.
#
#  WHAT IT DOES:
#    1. apt install: XFCE 4.18, Chromium, fonts, network tools, etc.
#    2. Deploys html/ to /opt/pisces-moon/html/ (with lib/ and fonts/)
#    3. Generates ~70 .desktop launchers (one per app)
#    4. Sets dark wallpaper, configures XFCE panel, touchscreen calibration
#    5. Auto-detects Q508 hardware and applies tablet-specific tweaks
#
#  IDEMPOTENT — safe to re-run after updates.
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Locate repo root ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find html/ — search current dir, parent, parent's parent
if [[ -d "$SCRIPT_DIR/html" ]]; then
    REPO_ROOT="$SCRIPT_DIR"
elif [[ -d "$SCRIPT_DIR/../html" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [[ -d "$SCRIPT_DIR/../../html" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
    echo "ERROR: Cannot find html/ folder. Run this from the repo root."
    exit 1
fi

HTML_SRC="$REPO_ROOT/html"

# ── Colors ─────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

step()  { echo -e "\n${CYAN}[STEP]${NC} $1"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail()  { echo -e "${RED}  ✗${NC} $1"; }
info()  { echo -e "${BLUE}  ℹ${NC} $1"; }

# ── Sanity checks ──────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root: sudo ./install.sh"
    exit 1
fi

if [[ ! -d "$HTML_SRC" ]]; then
    fail "html/ folder not found at $HTML_SRC"
    exit 1
fi

# Find the unprivileged user (the one who ran sudo)
TARGET_USER="${SUDO_USER:-}"
if [[ -z "$TARGET_USER" || "$TARGET_USER" == "root" ]]; then
    TARGET_USER="$(getent passwd 1000 | cut -d: -f1)"
fi
if [[ -z "$TARGET_USER" ]]; then
    fail "Cannot determine target user. Set SUDO_USER or pass via env."
    exit 1
fi
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

info "Repo root:    $REPO_ROOT"
info "Target user:  $TARGET_USER"
info "Target home:  $TARGET_HOME"

# ── 1. APT packages ────────────────────────────────────────────────
step "Installing system packages"

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq

apt-get install -y --no-install-recommends \
    `# XFCE desktop + display manager` \
    xfce4 xfce4-goodies lightdm lightdm-gtk-greeter \
    xfce4-power-manager xfce4-battery-plugin \
    `# Browser (the runtime for all HTML apps)` \
    chromium \
    `# Fonts (fallback if our bundled woff2 fail)` \
    fonts-dejavu fonts-liberation fonts-noto-color-emoji \
    `# Network + dev tools` \
    unzip ssh openssh-server curl wget git jq imagemagick \
    network-manager network-manager-gnome \
    `# Touchscreen support (Q508 + others)` \
    xinput xserver-xorg-input-libinput xinput-calibrator \
    `# Audio (audio_player + audio_recorder)` \
    pulseaudio pavucontrol \
    `# On-screen keyboard for tablet use` \
    onboard \
    `# Python for edge_bridge.py` \
    python3 python3-pip python3-websockets python3-serial \
    `# Misc useful` \
    htop neofetch ranger \
    > /tmp/pm-apt.log 2>&1 || warn "Some packages may have failed — see /tmp/pm-apt.log"

ok "System packages installed"

# ── 2. Create directory structure ──────────────────────────────────
step "Creating /opt/pisces-moon/"

mkdir -p /opt/pisces-moon/{html,html/lib,html/fonts,html/lib/images,tools,docs,share}
chmod 755 /opt/pisces-moon /opt/pisces-moon/html

ok "Directory structure created"

# ── 3. Deploy HTML apps ────────────────────────────────────────────
step "Deploying HTML apps from $HTML_SRC"

# Copy all HTML files
cp "$HTML_SRC"/*.html /opt/pisces-moon/html/
cp "$HTML_SRC"/pm_fonts.css /opt/pisces-moon/html/ 2>/dev/null || warn "pm_fonts.css missing"
cp "$HTML_SRC"/pm_transport.js /opt/pisces-moon/html/ 2>/dev/null || warn "pm_transport.js missing"

# Lib bundle (Leaflet, ZXing, jsQR, qrcodejs)
if [[ -d "$HTML_SRC/lib" ]]; then
    cp "$HTML_SRC"/lib/*.js  /opt/pisces-moon/html/lib/  2>/dev/null || true
    cp "$HTML_SRC"/lib/*.css /opt/pisces-moon/html/lib/  2>/dev/null || true
    if [[ -d "$HTML_SRC/lib/images" ]]; then
        cp "$HTML_SRC"/lib/images/*.png /opt/pisces-moon/html/lib/images/ 2>/dev/null || true
    fi
    ok "Deployed lib bundle"
else
    warn "lib/ folder missing — barcode and offline_maps apps will not work"
fi

# Fonts
if [[ -d "$HTML_SRC/fonts" ]]; then
    cp "$HTML_SRC"/fonts/*.woff2 /opt/pisces-moon/html/fonts/ 2>/dev/null || true
    ok "Deployed fonts"
else
    warn "fonts/ folder missing — apps will fall back to monospace"
fi

# Set permissions
chmod 644 /opt/pisces-moon/html/*.html
chmod -R a+r /opt/pisces-moon/html/

HTML_COUNT=$(ls /opt/pisces-moon/html/*.html 2>/dev/null | wc -l)
ok "Deployed $HTML_COUNT HTML apps"

# ── 4. Deploy tools (edge_bridge.py, etc.) ─────────────────────────
step "Deploying tools"

if [[ -f "$REPO_ROOT/tools/edge_bridge.py" ]]; then
    cp "$REPO_ROOT/tools/edge_bridge.py" /opt/pisces-moon/tools/
    chmod 755 /opt/pisces-moon/tools/edge_bridge.py
    ok "Deployed edge_bridge.py"
fi

# Copy LICENSE + NOTICE so users on the deployed system can find them
cp "$REPO_ROOT/LICENSE"  /opt/pisces-moon/LICENSE  2>/dev/null || true
cp "$REPO_ROOT/NOTICE"   /opt/pisces-moon/NOTICE   2>/dev/null || true
cp "$REPO_ROOT/README.md" /opt/pisces-moon/README.md 2>/dev/null || true

# ── 5. Wallpaper ───────────────────────────────────────────────────
step "Setting wallpaper"

WALLPAPER_DEST="/opt/pisces-moon/share/wallpaper.jpg"
mkdir -p /opt/pisces-moon/share

# Look for a custom wallpaper in the repo
WALLPAPER_SRC=""
for candidate in "$REPO_ROOT"/pisces-moon-*.jpg "$REPO_ROOT/share/wallpaper.jpg" "$REPO_ROOT/wallpaper.jpg"; do
    if [[ -f "$candidate" ]]; then
        WALLPAPER_SRC="$candidate"
        break
    fi
done

if [[ -n "$WALLPAPER_SRC" ]]; then
    cp "$WALLPAPER_SRC" "$WALLPAPER_DEST"
    ok "Used custom wallpaper: $(basename "$WALLPAPER_SRC")"
else
    if command -v convert >/dev/null 2>&1; then
        convert -size 1280x800 \
            gradient:'#050a0e-#0c1620' \
            -fill '#1a3a50' -draw 'line 0,400 1280,400' \
            -fill '#00d4ff' -gravity center \
            -font 'DejaVu-Sans-Mono' -pointsize 36 \
            -annotate +0-50 'PISCES MOON' \
            -fill '#7ab8d4' -pointsize 14 \
            -annotate +0+0 'fluidfortune.com' \
            "$WALLPAPER_DEST" 2>/dev/null \
            && ok "Generated fallback wallpaper" \
            || warn "ImageMagick failed — solid color wallpaper instead"
    else
        warn "ImageMagick not found — install: apt install imagemagick"
    fi
fi

# Apply via xfconf
sudo -u "$TARGET_USER" mkdir -p "$TARGET_HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
cat > "$TARGET_HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml" <<XFCONFEOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorLVDS-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
        </property>
      </property>
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
          <property name="image-style" type="int" value="5"/>
        </property>
      </property>
    </property>
  </property>
</channel>
XFCONFEOF

chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/xfce4"
ok "Wallpaper config written"

# ── 6. Generate .desktop launchers ─────────────────────────────────
step "Generating .desktop launchers"

LAUNCHER_DIR="$TARGET_HOME/.local/share/applications"
sudo -u "$TARGET_USER" mkdir -p "$LAUNCHER_DIR"

# App registry: "Display Name" → "filename|icon|category"
declare -A APPS=(
    # CYBER
    ["PM — Smelter"]="wardrive.html|network-wireless|cyber"
    ["PM — Net Scanner"]="net_scanner.html|network-workgroup|cyber"
    ["PM — BT Radar"]="bt_radar.html|bluetooth|cyber"
    ["PM — Beacon Spotter"]="beacon_spotter.html|network-wireless|cyber"
    ["PM — Pkt Sniffer"]="pkt_sniffer.html|network-wired|cyber"
    ["PM — Pkt Analysis"]="pkt_analysis.html|preferences-system|cyber"
    ["PM — Hash Tool"]="hash_tool.html|security-high|cyber"
    ["PM — Probe Intel"]="probe_intel.html|preferences-system|cyber"
    ["PM — RF Spectrum"]="rf_spectrum.html|preferences-system|cyber"
    ["PM — BLE GATT"]="ble_gatt.html|bluetooth|cyber"
    ["PM — BLE Ducky"]="ble_ducky.html|input-keyboard|cyber"
    ["PM — USB Ducky"]="usb_ducky.html|input-keyboard|cyber"
    ["PM — WiFi Ducky"]="wifi_ducky.html|input-keyboard|cyber"
    ["PM — WPA Handshake"]="wpa_handshake.html|security-medium|cyber"
    ["PM — Port Scanner"]="port_scanner.html|preferences-system-network|cyber"

    # COMMS
    ["PM — GPS"]="gps_app.html|gps|comms"
    ["PM — WiFi Connect"]="wifi_app.html|network-wireless|comms"
    ["PM — SSH Client"]="ssh_client.html|utilities-terminal|comms"
    ["PM — Voice Terminal"]="voice_terminal.html|audio-input-microphone|comms"
    ["PM — Mesh Messenger"]="mesh_messenger.html|chat|comms"
    ["PM — SOS Beacon"]="sos_beacon.html|emblem-important|comms"
    ["PM — Contacts"]="contacts.html|stock_contact|comms"

    # TOOLS
    ["PM — Notepad"]="notepad.html|accessories-text-editor|tools"
    ["PM — Calculator"]="calculator.html|accessories-calculator|tools"
    ["PM — Clock"]="clock.html|appointment-soon|tools"
    ["PM — Calendar"]="calendar.html|x-office-calendar|tools"
    ["PM — Etch"]="etch.html|applications-graphics|tools"
    ["PM — Filesystem"]="filesystem.html|system-file-manager|tools"
    ["PM — Field Notes"]="field_notes.html|accessories-text-editor|tools"
    ["PM — Flashlight"]="flashlight.html|weather-clear-night|tools"
    ["PM — Compass"]="compass.html|applications-utilities|tools"
    ["PM — Pass Gen"]="passgen.html|dialog-password|tools"
    ["PM — Vault"]="vault.html|security-high|tools"
    ["PM — QR Tool"]="qr_tool.html|view-barcode|tools"
    ["PM — Barcode"]="barcode.html|view-barcode|tools"

    # INTEL
    ["PM — Gemini Terminal"]="gemini_terminal.html|applications-internet|intel"
    ["PM — Gemini Log"]="gemini_log.html|x-office-document|intel"
    ["PM — Baseball"]="baseball.html|applications-games|intel"
    ["PM — Trails"]="trails.html|applications-internet|intel"
    ["PM — Medical Ref"]="medical_ref.html|applications-science|intel"
    ["PM — Survival Ref"]="survival_ref.html|applications-utilities|intel"
    ["PM — Weather"]="weather.html|weather-clear|intel"
    ["PM — Recipes"]="recipes.html|kitchen|intel"
    ["PM — Sun & Moon"]="sun_moon.html|weather-clear-night|intel"
    ["PM — Tides"]="tides.html|weather-storm|intel"
    ["PM — Body Metrics"]="body_metrics.html|user-info|intel"
    ["PM — Habits"]="habits.html|x-office-calendar|intel"

    # NEWS
    ["PM — News (General)"]="news_general.html|applications-internet|news"
    ["PM — News (World)"]="news_world.html|applications-internet|news"
    ["PM — News (Tech)"]="news_tech.html|applications-internet|news"
    ["PM — News (Finance)"]="news_finance.html|applications-internet|news"
    ["PM — News (Local)"]="news_local.html|applications-internet|news"

    # SPORTS
    ["PM — NFL"]="nfl.html|applications-games|sports"
    ["PM — NBA"]="nba.html|applications-games|sports"
    ["PM — NHL"]="nhl.html|applications-games|sports"
    ["PM — MLS"]="mls.html|applications-games|sports"

    # GAMES
    ["PM — SimCity"]="simcity.html|applications-games|games"
    ["PM — Pac-Man"]="pacman.html|applications-games|games"
    ["PM — Galaga"]="galaga.html|applications-games|games"
    ["PM — Chess"]="chess.html|applications-games|games"
    ["PM — Snake"]="snake.html|applications-games|games"
    ["PM — Tetris"]="tetris.html|applications-games|games"
    ["PM — Minesweeper"]="minesweeper.html|applications-games|games"
    ["PM — Breakout"]="breakout.html|applications-games|games"

    # MEDIA
    ["PM — Audio Player"]="audio_player.html|multimedia-audio-player|media"
    ["PM — Audio Recorder"]="audio_recorder.html|audio-input-microphone|media"
    ["PM — Video Player"]="video_player.html|multimedia-video-player|media"

    # MAPS
    ["PM — Offline Maps"]="offline_maps.html|applications-internet|maps"

    # SYSTEM
    ["PM — System Info"]="system_info.html|preferences-system|system"
    ["PM — Ghost Partition"]="ghost_partition.html|drive-harddisk|system"
    ["PM — PIN Screen"]="pin_screen.html|system-lock-screen|system"
    ["PM — About"]="about.html|help-about|system"

    # FLUID FORTUNE
    ["PM — Punky"]="punky.html|applications-internet|fluidfortune"
    ["PM — Little Soul"]="little_soul.html|applications-internet|fluidfortune"
    ["PM — Static"]="static.html|applications-internet|fluidfortune"
    ["PM — Spadra Smelter"]="spadra_smelter.html|applications-internet|fluidfortune"
)

LAUNCHER_COUNT=0
for name in "${!APPS[@]}"; do
    IFS='|' read -r file icon category <<< "${APPS[$name]}"

    if [[ ! -f "/opt/pisces-moon/html/$file" ]]; then
        continue
    fi

    slug="${file%.html}"
    desktop_file="$LAUNCHER_DIR/pm-$slug.desktop"

    cat > "$desktop_file" <<DESKEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$name
Comment=Pisces Moon OS app
Exec=chromium --app=file:///opt/pisces-moon/html/$file --window-size=1280,800
Icon=$icon
Categories=PiscesMoon-${category^};
Terminal=false
StartupNotify=true
StartupWMClass=chromium-browser
DESKEOF

    chmod 644 "$desktop_file"
    LAUNCHER_COUNT=$((LAUNCHER_COUNT + 1))
done

chown -R "$TARGET_USER:$TARGET_USER" "$LAUNCHER_DIR"
ok "Generated $LAUNCHER_COUNT .desktop launchers"

# ── 7. Hardware-specific tweaks ────────────────────────────────────
step "Detecting hardware"

PRODUCT="$(cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || echo 'unknown')"
IS_Q508=false
if [[ "$PRODUCT" == *"Q508"* ]]; then
    IS_Q508=true
    info "Detected Fujitsu Q508 — applying tablet tweaks"
fi

if [[ "$IS_Q508" == "true" ]]; then
    mkdir -p /etc/X11/xorg.conf.d
    cat > /etc/X11/xorg.conf.d/40-libinput-touchscreen.conf <<XORGEOF
Section "InputClass"
    Identifier      "libinput touchscreen catchall"
    MatchIsTouchscreen "on"
    MatchDevicePath "/dev/input/event*"
    Driver          "libinput"
    Option          "Tapping" "on"
    Option          "TappingButtonMap" "lmr"
EndSection
XORGEOF
    ok "Touchscreen calibration written"
fi

# ── 8. Auto-start onboard for tablets ──────────────────────────────
if [[ "$IS_Q508" == "true" ]]; then
    sudo -u "$TARGET_USER" mkdir -p "$TARGET_HOME/.config/autostart"
    cat > "$TARGET_HOME/.config/autostart/onboard.desktop" <<ONBOARDEOF
[Desktop Entry]
Type=Application
Name=Onboard
Exec=onboard
X-GNOME-Autostart-enabled=true
NoDisplay=false
ONBOARDEOF
    chown "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/autostart/onboard.desktop"
    ok "Onboard autostart configured"
fi

# ── 9. edge_bridge systemd user service ────────────────────────────
if [[ -f /opt/pisces-moon/tools/edge_bridge.py ]]; then
    step "Creating edge_bridge systemd user service"

    sudo -u "$TARGET_USER" mkdir -p "$TARGET_HOME/.config/systemd/user"
    cat > "$TARGET_HOME/.config/systemd/user/pisces-moon-bridge.service" <<SVCEOF
[Unit]
Description=Pisces Moon edge bridge (T-Beam serial → WebSocket)
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/pisces-moon/tools/edge_bridge.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SVCEOF
    chown "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/systemd/user/pisces-moon-bridge.service"

    ok "Service file created (not enabled by default)"
    info "Enable: systemctl --user enable --now pisces-moon-bridge"
fi

# ── 10. Final summary ──────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}  PISCES MOON OS v0.5 — INSTALL COMPLETE${NC}"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "  Apps deployed:    $HTML_COUNT"
echo "  Launchers made:   $LAUNCHER_COUNT"
echo "  HTML root:        /opt/pisces-moon/html/"
echo "  Tools:            /opt/pisces-moon/tools/"
echo "  Wallpaper:        $WALLPAPER_DEST"
echo ""
echo "  Next steps:"
echo "    1. Log out and back in (or reboot) to apply XFCE config"
echo "    2. Find apps in the Applications menu under 'PiscesMoon-*' categories"
echo "    3. Or right-click desktop → Applications → PiscesMoon-Cyber etc."
echo ""
echo "  Test directly:"
echo "    chromium --app=file:///opt/pisces-moon/html/about.html"
echo ""
echo "  License:  AGPL-3.0-or-later (see /opt/pisces-moon/LICENSE)"
echo "  Project:  https://fluidfortune.com"
echo ""
echo "  Dedicated to Jennifer Soto and Clark Beddows."
echo "═══════════════════════════════════════════════════════════════════════"
