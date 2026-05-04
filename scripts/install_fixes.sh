#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  PISCES MOON OS — DISPLAY FIXES v0.3.2
#  Copyright (C) 2026 Eric Becker / Fluid Fortune
#  SPDX-License-Identifier: AGPL-3.0-or-later
#
#  Fixes after initial install.sh:
#    1. Battery indicator in XFCE panel
#    2. Wallpaper auto-apply (live, not just on next login)
#    3. Right-click desktop menu shows all Pisces Moon apps
#    4. XFCE panel plugins (clock, systray, window buttons)
#
#  Run AFTER the main install.sh:
#    chmod +x install_fixes.sh
#    sudo ./install_fixes.sh
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

CY='\033[0;36m'; GR='\033[0;32m'; YL='\033[0;33m'
RD='\033[0;31m'; NC='\033[0m'; BD='\033[1m'

step() { echo -e "\n${CY}▶${NC} ${BD}$1${NC}"; }
ok()   { echo -e "  ${GR}✓${NC} $1"; }
warn() { echo -e "  ${YL}⚠${NC}  $1"; }
info() { echo -e "    $1"; }

if [[ $EUID -ne 0 ]]; then
    echo -e "${RD}Run with sudo:${NC}  sudo ./install_fixes.sh"
    exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
REAL_UID=$(id -u "$REAL_USER")

echo ""
echo -e "${CY}${BD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CY}${BD}║     PISCES MOON OS — DISPLAY FIXES           ║${NC}"
echo -e "${CY}${BD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════
# 1. INSTALL MISSING PACKAGES (battery plugin, menu tools)
# ═══════════════════════════════════════════════════════════════════════
step "Installing missing XFCE plugins"

apt-get update -qq 2>/dev/null || true
apt-get install -y -qq \
    xfce4-power-manager \
    xfce4-power-manager-plugins \
    xfce4-battery-plugin \
    xfce4-whiskermenu-plugin \
    xfce4-panel \
    xfce4-session \
    xfdesktop4 \
    acpi \
    upower \
    2>&1 | grep -v "^$" || true

ok "Battery & panel plugins installed"

# ═══════════════════════════════════════════════════════════════════════
# 2. WALLPAPER — APPLY LIVE
# ═══════════════════════════════════════════════════════════════════════
step "Applying wallpaper live"

WALLPAPER_DEST="/usr/share/pixmaps/pisces-moon/pisces-moon-1280x800.jpg"

if [[ ! -f "$WALLPAPER_DEST" ]]; then
    warn "No wallpaper found at $WALLPAPER_DEST — skipping live apply"
    info "Run main install.sh first, or copy your own:"
    info "  sudo cp yourfile.jpg $WALLPAPER_DEST"
else
    # Write the xfconf XML (for next login)
    XFCONF_DIR="$REAL_HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
    sudo -u "$REAL_USER" mkdir -p "$XFCONF_DIR"

    # Detect ALL possible monitor paths — XFCE uses monitor0, monitorVGA-1, etc.
    # depending on the driver. We write for all common ones.
    sudo -u "$REAL_USER" tee "$XFCONF_DIR/xfce4-desktop.xml" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitor0" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
        </property>
        <property name="workspace1" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
        </property>
      </property>
      <property name="monitorVGA-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
        </property>
      </property>
      <property name="monitorHDMI-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
        </property>
      </property>
      <property name="monitoreDP-1" type="empty">
        <property name="workspace0" type="empty">
          <property name="color-style" type="int" value="0"/>
          <property name="image-style" type="int" value="5"/>
          <property name="last-image" type="string" value="$WALLPAPER_DEST"/>
        </property>
      </property>
    </property>
  </property>
  <property name="desktop-menu" type="empty">
    <property name="show" type="bool" value="true"/>
    <property name="show-default-applications" type="bool" value="true"/>
  </property>
  <property name="windowlist-menu" type="empty">
    <property name="show" type="bool" value="true"/>
  </property>
  <property name="desktop-icons" type="empty">
    <property name="style" type="int" value="2"/>
    <property name="file-icons" type="empty">
      <property name="show-home" type="bool" value="false"/>
      <property name="show-filesystem" type="bool" value="false"/>
      <property name="show-removable" type="bool" value="true"/>
      <property name="show-trash" type="bool" value="true"/>
    </property>
    <property name="icon-size" type="uint" value="48"/>
  </property>
</channel>
EOF
    ok "Wallpaper XML written"

    # Try to apply LIVE if DISPLAY is set
    export DISPLAY="${DISPLAY:-:0}"
    export XAUTHORITY="${XAUTHORITY:-$REAL_HOME/.Xauthority}"

    # Try every possible monitor path via xfconf-query
    for monitor in monitor0 monitorVGA-1 monitorHDMI-1 monitoreDP-1 monitorLVDS-1; do
        sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
            xfconf-query -c xfce4-desktop \
            -p "/backdrop/screen0/$monitor/workspace0/last-image" \
            -s "$WALLPAPER_DEST" --create -t string 2>/dev/null || true
        sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
            xfconf-query -c xfce4-desktop \
            -p "/backdrop/screen0/$monitor/workspace0/image-style" \
            -s 5 --create -t int 2>/dev/null || true
    done

    # Force xfdesktop to reload
    sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
        xfdesktop --reload 2>/dev/null &
    sleep 1

    ok "Wallpaper applied live (if session is active)"
fi

# ═══════════════════════════════════════════════════════════════════════
# 3. RIGHT-CLICK DESKTOP MENU — ADD PISCES MOON APPS
# ═══════════════════════════════════════════════════════════════════════
step "Configuring right-click desktop menu"

# Ensure the .desktop files exist in the applications directory
APPS_DIR="/usr/share/applications"

# All 37 Pisces Moon apps as .desktop files
declare -A ALL_APPS=(
    # CYBER
    ["wardrive"]="Wardrive|CYBER|network-wireless"
    ["bt_radar"]="BT Radar|CYBER|bluetooth"
    ["pkt_sniffer"]="Packet Sniffer|CYBER|network-workgroup"
    ["beacon_spotter"]="Beacon Spotter|CYBER|network-wireless"
    ["net_scanner"]="Net Scanner|CYBER|network-workgroup"
    ["hash_tool"]="Hash Tool|CYBER|system-lock-screen"
    ["ble_gatt"]="BLE GATT|CYBER|bluetooth"
    ["wpa_handshake"]="WPA Handshake|CYBER|network-wireless"
    ["rf_spectrum"]="RF Spectrum|CYBER|audio-card"
    ["probe_intel"]="Probe Intel|CYBER|network-wireless"
    ["pkt_analysis"]="Pkt Analysis|CYBER|network-workgroup"
    ["ble_ducky"]="BLE Ducky|CYBER|input-keyboard"
    ["usb_ducky"]="USB Ducky|CYBER|input-keyboard"
    ["wifi_ducky"]="WiFi Ducky|CYBER|network-wireless"
    # COMMS
    ["wifi_app"]="WiFi Connect|COMMS|network-wireless"
    ["gps_app"]="GPS|COMMS|applications-internet"
    ["mesh_messenger"]="Mesh Messenger|COMMS|mail-send"
    ["voice_terminal"]="Voice Terminal|COMMS|audio-input-microphone"
    ["ssh_client"]="SSH Client|COMMS|utilities-terminal"
    ["pin_screen"]="Pin Screen|COMMS|system-lock-screen"
    # INTEL — Core
    ["gemini_terminal"]="Gemini Terminal|INTEL|applications-internet"
    ["gemini_log"]="Gemini Log|INTEL|text-x-generic"
    ["baseball"]="Baseball Intel|INTEL|applications-games"
    ["trails"]="Trails|INTEL|applications-internet"
    ["medical_ref"]="Medical Ref|INTEL|emblem-important"
    ["survival_ref"]="Survival Ref|INTEL|emblem-important"
    # INTEL — News Aggregators
    ["news_general"]="News — General|INTEL|emblem-default"
    ["news_world"]="News — World|INTEL|applications-internet"
    ["news_tech"]="News — Tech|INTEL|applications-development"
    ["news_finance"]="News — Finance|INTEL|applications-office"
    ["news_local"]="News — Local|INTEL|mark-location"
    # INTEL — Sports
    ["nfl"]="NFL Intel|INTEL|applications-games"
    ["nba"]="NBA Intel|INTEL|applications-games"
    ["nhl"]="NHL Intel|INTEL|applications-games"
    ["mls"]="MLS Intel|INTEL|applications-games"
    # TOOLS
    ["notepad"]="Notepad|TOOLS|accessories-text-editor"
    ["calculator"]="Calculator|TOOLS|accessories-calculator"
    ["clock"]="Clock|TOOLS|preferences-system-time"
    ["calendar"]="Calendar|TOOLS|x-office-calendar"
    ["etch"]="Etch|TOOLS|applications-graphics"
    ["filesystem"]="Filesystem|TOOLS|system-file-manager"
    ["ghost_partition"]="Ghost Partition|TOOLS|drive-harddisk"
    ["recipes"]="Recipe Book|TOOLS|applications-other"
    # MEDIA
    ["audio_player"]="Audio Player|MEDIA|audio-x-generic"
    ["audio_recorder"]="Audio Recorder|MEDIA|audio-input-microphone"
    # SYSTEM
    ["system_info"]="System Info|SYSTEM|preferences-system"
    ["about"]="About|SYSTEM|help-about"
)

info "Creating .desktop files for all apps..."
for app_key in "${!ALL_APPS[@]}"; do
    IFS='|' read -r name category icon <<< "${ALL_APPS[$app_key]}"
    DFILE="$APPS_DIR/pisces-moon-${app_key}.desktop"

    cat > "$DFILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PM — $name
GenericName=Pisces Moon $category
Comment=Pisces Moon OS / $category / $name
Exec=chromium --app=file:///opt/pisces-moon/html/${app_key}.html
Icon=$icon
Terminal=false
Categories=PiscesMoon;PM-$category;
StartupNotify=false
EOF
done
ok "37 .desktop files created"

# Create the Pisces Moon directory entries for each category
for cat in CYBER COMMS INTEL TOOLS MEDIA SYSTEM; do
    cat > "/usr/share/desktop-directories/pisces-moon-${cat,,}.directory" << EOF
[Desktop Entry]
Version=1.0
Type=Directory
Name=Pisces Moon — $cat
Icon=applications-system
EOF
done
ok "Category directories registered"

# Build the menu XML that shows everything under a single "Pisces Moon" root
mkdir -p /etc/xdg/menus/applications-merged
cat > /etc/xdg/menus/applications-merged/pisces-moon.menu << 'EOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
 "http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">
<Menu>
  <Name>Applications</Name>
  <Menu>
    <Name>Pisces Moon</Name>
    <Directory>pisces-moon.directory</Directory>
    <Include><Category>PiscesMoon</Category></Include>
    <Menu>
      <Name>CYBER</Name>
      <Directory>pisces-moon-cyber.directory</Directory>
      <Include><Category>PM-CYBER</Category></Include>
    </Menu>
    <Menu>
      <Name>COMMS</Name>
      <Directory>pisces-moon-comms.directory</Directory>
      <Include><Category>PM-COMMS</Category></Include>
    </Menu>
    <Menu>
      <Name>INTEL</Name>
      <Directory>pisces-moon-intel.directory</Directory>
      <Include><Category>PM-INTEL</Category></Include>
    </Menu>
    <Menu>
      <Name>TOOLS</Name>
      <Directory>pisces-moon-tools.directory</Directory>
      <Include><Category>PM-TOOLS</Category></Include>
    </Menu>
    <Menu>
      <Name>MEDIA</Name>
      <Directory>pisces-moon-media.directory</Directory>
      <Include><Category>PM-MEDIA</Category></Include>
    </Menu>
    <Menu>
      <Name>SYSTEM</Name>
      <Directory>pisces-moon-system.directory</Directory>
      <Include><Category>PM-SYSTEM</Category></Include>
    </Menu>
  </Menu>
</Menu>
EOF
ok "Menu XML written"

# Parent directory
cat > /usr/share/desktop-directories/pisces-moon.directory << 'EOF'
[Desktop Entry]
Version=1.0
Type=Directory
Name=Pisces Moon
Comment=Local intelligence platform
Icon=applications-internet
EOF

update-desktop-database "$APPS_DIR" 2>/dev/null || true
ok "Desktop database rebuilt"

# ═══════════════════════════════════════════════════════════════════════
# 4. XFCE PANEL — ADD BATTERY, CLOCK, SYSTRAY
# ═══════════════════════════════════════════════════════════════════════
step "Configuring XFCE panel (battery, clock, systray)"

PANEL_XML="$REAL_HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
sudo -u "$REAL_USER" mkdir -p "$(dirname "$PANEL_XML")"

sudo -u "$REAL_USER" tee "$PANEL_XML" > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="dark-mode" type="bool" value="true"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="size" type="uint" value="32"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
        <value type="int" value="7"/>
        <value type="int" value="8"/>
        <value type="int" value="9"/>
      </property>
      <property name="icon-size" type="uint" value="22"/>
    </property>
  </property>
  <property name="plugins" type="empty">
    <!-- Whisker Menu (Apps launcher) -->
    <property name="plugin-1" type="string" value="whiskermenu"/>
    <!-- Window buttons -->
    <property name="plugin-2" type="string" value="tasklist">
      <property name="show-labels" type="bool" value="true"/>
      <property name="grouping" type="uint" value="1"/>
    </property>
    <!-- Separator -->
    <property name="plugin-3" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <!-- System tray -->
    <property name="plugin-4" type="string" value="systray">
      <property name="size-max" type="uint" value="22"/>
      <property name="square-icons" type="bool" value="true"/>
    </property>
    <!-- Notification plugin -->
    <property name="plugin-5" type="string" value="notification-plugin"/>
    <!-- Power manager plugin (battery) -->
    <property name="plugin-6" type="string" value="power-manager-plugin">
      <property name="show-panel-label" type="uint" value="3"/>
    </property>
    <!-- PulseAudio volume -->
    <property name="plugin-7" type="string" value="pulseaudio">
      <property name="enable-keyboard-shortcuts" type="bool" value="true"/>
      <property name="show-notifications" type="bool" value="true"/>
    </property>
    <!-- Clock -->
    <property name="plugin-8" type="string" value="clock">
      <property name="mode" type="uint" value="2"/>
      <property name="digital-layout" type="uint" value="3"/>
      <property name="digital-date-font" type="string" value="Sans 8"/>
      <property name="digital-time-font" type="string" value="Sans Bold 10"/>
    </property>
    <!-- Action buttons (logout, lock) -->
    <property name="plugin-9" type="string" value="actions">
      <property name="appearance" type="uint" value="1"/>
      <property name="items" type="array">
        <value type="string" value="+lock-screen"/>
        <value type="string" value="+switch-user"/>
        <value type="string" value="+separator"/>
        <value type="string" value="+suspend"/>
        <value type="string" value="+hibernate"/>
        <value type="string" value="+separator"/>
        <value type="string" value="+shutdown"/>
        <value type="string" value="+restart"/>
        <value type="string" value="+logout"/>
      </property>
    </property>
  </property>
</channel>
EOF

chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.config/xfce4"
ok "Panel configured with battery, clock, tray, volume"

# ═══════════════════════════════════════════════════════════════════════
# 5. POWER MANAGER — ENABLE BATTERY MONITORING
# ═══════════════════════════════════════════════════════════════════════
step "Enabling power manager"

POWER_XML="$REAL_HOME/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml"

sudo -u "$REAL_USER" tee "$POWER_XML" > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-power-manager" version="1.0">
  <property name="xfce4-power-manager" type="empty">
    <property name="show-tray-icon" type="bool" value="true"/>
    <property name="power-button-action" type="uint" value="4"/>
    <property name="lid-action-on-battery" type="uint" value="1"/>
    <property name="lid-action-on-ac" type="uint" value="1"/>
    <property name="inactivity-on-battery" type="uint" value="30"/>
    <property name="inactivity-on-ac" type="uint" value="0"/>
    <property name="brightness-switch" type="int" value="0"/>
    <property name="brightness-switch-restore-on-exit" type="int" value="1"/>
    <property name="show-panel-label" type="uint" value="3"/>
    <property name="dpms-enabled" type="bool" value="true"/>
  </property>
</channel>
EOF

chown "$REAL_USER:$REAL_USER" "$POWER_XML"

# Make sure power manager autostarts
sudo -u "$REAL_USER" mkdir -p "$REAL_HOME/.config/autostart"
sudo -u "$REAL_USER" tee "$REAL_HOME/.config/autostart/xfce4-power-manager.desktop" > /dev/null << 'EOF'
[Desktop Entry]
Type=Application
Name=Power Manager
Exec=xfce4-power-manager
X-GNOME-Autostart-enabled=true
Hidden=false
NoDisplay=false
EOF

ok "Power manager configured and set to autostart"

# ═══════════════════════════════════════════════════════════════════════
# 6. TRY TO APPLY LIVE
# ═══════════════════════════════════════════════════════════════════════
step "Attempting live application"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$REAL_HOME/.Xauthority}"

# Try to restart panel without logging out
if sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
   xfce4-panel --quit 2>/dev/null; then
    sleep 2
    sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
       nohup xfce4-panel > /dev/null 2>&1 &
    ok "Panel restarted — battery & plugins should appear"
else
    warn "Could not restart panel live (no active session?)"
    info "Log out and back in to see changes"
fi

# Reload desktop
sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
    xfdesktop --reload 2>/dev/null || true

# Start power manager if not running
if ! pgrep -u "$REAL_USER" xfce4-power-manager > /dev/null 2>&1; then
    sudo -u "$REAL_USER" DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
        nohup xfce4-power-manager > /dev/null 2>&1 &
    ok "Power manager started"
fi

# ═══════════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CY}${BD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CY}${BD}║     DISPLAY FIXES COMPLETE                   ║${NC}"
echo -e "${CY}${BD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GR}Fixed:${NC}"
echo -e "  ✓ Battery indicator added to panel"
echo -e "  ✓ Wallpaper set to auto-apply"
echo -e "  ✓ Right-click menu shows all 37 apps by category"
echo -e "  ✓ XFCE panel has clock, tray, volume, power"
echo ""
echo -e "${YL}If changes don't appear:${NC}"
echo -e "  1.  Log out and log back in (most reliable)"
echo -e "  2.  Or manually restart panel:  xfce4-panel -r"
echo -e "  3.  Or reload desktop:  xfdesktop --reload"
echo ""
echo -e "${NC}Pisces Moon OS — fluidfortune.com${NC}"
echo ""
