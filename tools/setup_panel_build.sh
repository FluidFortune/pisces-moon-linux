#!/usr/bin/env bash
# Pisces Moon OS — setup_panel_build.sh
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
# ═══════════════════════════════════════════════════════════════════════
#  PISCES MOON OS — PANEL BUILD ENVIRONMENT SETUP
#  Target: Luckfox Pico 86 Panel (RV1106 / Buildroot / LVGL)
#  Host:   Ubuntu 24.04 x86-64
#
#  Run this once on your build machine.
#  It will:
#    1. Install Docker
#    2. Pull the Luckfox SDK Docker image
#    3. Clone the Luckfox SDK
#    4. Clone the 86Panel UI demo (LVGL reference)
#    5. Create the Pisces Moon Panel project structure
#    6. Drop you into the build container ready to compile
#
#  Usage:
#    chmod +x setup_panel_build.sh
#    ./setup_panel_build.sh
#
#  After first run, re-enter the build environment with:
#    sudo docker start -ai luckfox
#
#  Author: Eric Becker / Fluid Fortune / Pisces Moon OS / 2026
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────
CY='\033[0;36m'; GR='\033[0;32m'; YL='\033[0;33m'
RD='\033[0;31m'; NC='\033[0m'; BD='\033[1m'

step() { echo -e "\n${CY}▶${NC} ${BD}$1${NC}"; }
ok()   { echo -e "  ${GR}✓${NC} $1"; }
warn() { echo -e "  ${YL}⚠${NC}  $1"; }
info() { echo -e "    $1"; }
die()  { echo -e "\n${RD}✗ ERROR:${NC} $1"; exit 1; }

# ── Sanity checks ────────────────────────────────────────────────────────
step "Checking build environment"

# Must be x86-64
ARCH=$(uname -m)
[[ "$ARCH" == "x86_64" ]] || die "Requires x86-64 host. Got: $ARCH
ARM machines (Apple Silicon, Raspberry Pi) cannot run the Rockchip cross-compiler."
ok "Architecture: $ARCH"

# Must NOT be root (Docker install needs sudo, not root login)
[[ $EUID -ne 0 ]] || die "Run as a normal user with sudo access, not as root."
ok "User: $USER"

# Ubuntu version — warn if not 22/24
if [ -f /etc/os-release ]; then
    . /etc/os-release
    ok "OS: $NAME $VERSION_ID"
    if [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
        warn "Tested on Ubuntu 22.04 and 24.04. Your version ($VERSION_ID) may work but is untested."
    fi
fi

# ── Workspace ────────────────────────────────────────────────────────────
step "Setting up workspace"

WORKSPACE="$HOME/pisces-moon-panel"
SDK_DIR="$WORKSPACE/luckfox-pico"
PANEL_DEMO_DIR="$WORKSPACE/luckfox-panel-ui-demo"
PM_DIR="$WORKSPACE/pisces-moon-panel-src"

mkdir -p "$WORKSPACE"
ok "Workspace: $WORKSPACE"

# ── Install Docker ───────────────────────────────────────────────────────
step "Installing Docker"

if command -v docker &>/dev/null; then
    ok "Docker already installed: $(docker --version)"
else
    info "Installing Docker via official script..."
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Docker official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    # Docker repo — use jammy (22.04) repo even on 24.04, it works
    CODENAME=$(lsb_release -cs)
    # If noble (24.04), fall back to jammy for Docker repo
    [[ "$CODENAME" == "noble" ]] && CODENAME="jammy"

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $CODENAME stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group so we don't need sudo every time
    sudo usermod -aG docker "$USER"
    ok "Docker installed"
    warn "You've been added to the 'docker' group."
    warn "This script will use 'sudo docker' for this session."
    warn "After rebooting, you can use 'docker' without sudo."
fi

DOCKER_CMD="docker"
# If user isn't in docker group yet in this session, use sudo
if ! groups | grep -q docker; then
    DOCKER_CMD="sudo docker"
fi

# ── Clone Luckfox SDK ────────────────────────────────────────────────────
step "Cloning Luckfox Pico SDK"

if [ -d "$SDK_DIR/.git" ]; then
    ok "SDK already cloned at $SDK_DIR"
    info "Pulling latest..."
    cd "$SDK_DIR" && git pull --quiet && cd -
else
    info "Cloning from GitHub (this is a large repo ~2GB, may take a few minutes)..."
    git clone https://github.com/LuckfoxTECH/luckfox-pico.git "$SDK_DIR"
    ok "SDK cloned to $SDK_DIR"
fi

# ── Clone 86Panel UI Demo ─────────────────────────────────────────────────
step "Cloning Luckfox 86Panel LVGL UI Demo"

if [ -d "$PANEL_DEMO_DIR/.git" ]; then
    ok "Panel UI demo already cloned"
else
    if git clone https://github.com/LuckfoxTECH/luckfox_pico_86panel_ui_demo.git "$PANEL_DEMO_DIR" 2>/dev/null; then
        ok "86Panel UI demo cloned — LVGL reference implementation"
    else
        warn "Could not clone panel UI demo (repo may have moved)"
        warn "Check: https://github.com/LuckfoxTECH"
        mkdir -p "$PANEL_DEMO_DIR"
    fi
fi

# ── Create Pisces Moon Panel project structure ─────────────────────────────
step "Creating Pisces Moon Panel project structure"

mkdir -p "$PM_DIR"/{src,include,assets,scripts,protocol}

# ── Serial protocol definition ─────────────────────────────────────────────
cat > "$PM_DIR/protocol/pm_protocol.h" << 'EOF'
// ═══════════════════════════════════════════════════════════════════════
//  PISCES MOON OS — PANEL SERIAL PROTOCOL v1.0
//  JSON-over-UART between Luckfox Panel (host) and ESP32 nodes
//
//  Format: single-line JSON, newline terminated, max 512 bytes per line
//  Baud:   115200 (USB serial default)
//  Port:   /dev/ttyUSB0 (T-Beam S3)
//          /dev/ttyUSB1 (future: second node)
//
//  Message types (ESP32 → Panel):
//    wardrive  — WiFi AP scan result
//    ble       — BLE device scan result
//    gps       — GPS fix data
//    lora      — Received LoRa packet
//    probe     — WiFi probe request
//    status    — Node health/telemetry
//    beacon    — Beacon spotter result
//
//  Command types (Panel → ESP32):
//    cmd_scan_start   — Begin wardrive scan
//    cmd_scan_stop    — Pause wardrive scan
//    cmd_channel      — Set WiFi channel
//    cmd_lora_send    — Send LoRa message
//    cmd_reboot       — Reboot the node
//
//  Author: Eric Becker / Fluid Fortune / Pisces Moon OS / 2026
// ═══════════════════════════════════════════════════════════════════════

#pragma once

// ── Inbound message types (ESP32 → Panel) ─────────────────────────────

// WiFi AP discovered
// {"type":"wardrive","bssid":"AA:BB:CC:DD:EE:FF","ssid":"HomeNet",
//  "rssi":-67,"ch":6,"enc":true,"vendor":"Apple"}
#define PM_MSG_WARDRIVE    "wardrive"

// BLE device discovered
// {"type":"ble","mac":"AA:BB:CC:DD:EE:FF","name":"AirPods",
//  "rssi":-54,"adtype":"LE"}
#define PM_MSG_BLE         "ble"

// GPS fix
// {"type":"gps","lat":34.0522,"lon":-118.2437,"alt":71.0,
//  "sats":8,"fix":true,"speed":0.0,"heading":0.0}
#define PM_MSG_GPS         "gps"

// LoRa packet received
// {"type":"lora","msg":"Hello from node 2","rssi":-89,
//  "snr":7.2,"freq":915.0,"from":"NODE2"}
#define PM_MSG_LORA        "lora"

// WiFi probe request
// {"type":"probe","mac":"AA:BB:CC:DD:EE:FF","ssid":"CorpVPN",
//  "rssi":-71,"vendor":"Samsung"}
#define PM_MSG_PROBE       "probe"

// Beacon spotter
// {"type":"beacon","bssid":"AA:BB:CC:DD:EE:FF","ssid":"HiddenNet",
//  "rssi":-80,"ch":11,"hidden":true,"beacons":1200}
#define PM_MSG_BEACON      "beacon"

// Node status/telemetry (sent every 30 seconds)
// {"type":"status","node":"TBEAM_S3","bat":87,"uptime":3600,
//  "temp":24.1,"pressure":1013.2,"gps_fix":true,
//  "wifi_scans":142,"ble_seen":38,"lora_rx":5,"lora_tx":2}
#define PM_MSG_STATUS      "status"

// ── Outbound command types (Panel → ESP32) ────────────────────────────

// {"cmd":"scan_start"}
// {"cmd":"scan_stop"}
// {"cmd":"channel","ch":6}
// {"cmd":"lora_send","msg":"Hello from Panel","dest":"ALL"}
// {"cmd":"reboot"}

#define PM_CMD_SCAN_START  "scan_start"
#define PM_CMD_SCAN_STOP   "scan_stop"
#define PM_CMD_CHANNEL     "channel"
#define PM_CMD_LORA_SEND   "lora_send"
#define PM_CMD_REBOOT      "reboot"

// ── Protocol constants ────────────────────────────────────────────────
#define PM_SERIAL_BAUD     115200
#define PM_MSG_MAX_LEN     512
#define PM_MSG_TERMINATOR  '\n'
EOF

ok "Protocol header: $PM_DIR/protocol/pm_protocol.h"

# ── Serial bridge daemon (Panel side, C) ──────────────────────────────────
cat > "$PM_DIR/src/serial_bridge.c" << 'EOF'
// ═══════════════════════════════════════════════════════════════════════
//  PISCES MOON OS — SERIAL BRIDGE DAEMON
//  Runs on Luckfox Panel (Linux/Buildroot)
//  Opens /dev/ttyUSB0, reads JSON lines from T-Beam,
//  routes parsed messages to the LVGL UI via a named pipe or callback.
//
//  Compile (cross):
//    arm-rockchip830-linux-uclibcgnueabihf-gcc \
//      serial_bridge.c -o serial_bridge -lm
//
//  Usage:
//    ./serial_bridge /dev/ttyUSB0 &
//
//  Author: Eric Becker / Fluid Fortune / Pisces Moon OS / 2026
// ═══════════════════════════════════════════════════════════════════════

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>
#include <signal.h>
#include <time.h>

#define BAUD_RATE    B115200
#define MAX_LINE     512
#define PIPE_PATH    "/tmp/pm_serial_in"   // Named pipe → LVGL app reads this
#define LOG_PATH     "/data/logs/serial_bridge.log"

static volatile int running = 1;
static FILE *logfile = NULL;

void sig_handler(int sig) { running = 0; }

void log_msg(const char *level, const char *msg) {
    time_t now = time(NULL);
    char ts[32];
    strftime(ts, sizeof(ts), "%H:%M:%S", localtime(&now));
    if (logfile) fprintf(logfile, "[%s] [%s] %s\n", ts, level, msg);
    fprintf(stderr, "[%s] [%s] %s\n", ts, level, msg);
    if (logfile) fflush(logfile);
}

int open_serial(const char *port) {
    int fd = open(port, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) return -1;

    struct termios tty;
    memset(&tty, 0, sizeof(tty));
    if (tcgetattr(fd, &tty) != 0) { close(fd); return -1; }

    cfsetispeed(&tty, BAUD_RATE);
    cfsetospeed(&tty, BAUD_RATE);

    tty.c_cflag |= (CLOCAL | CREAD);   // Enable receiver
    tty.c_cflag &= ~PARENB;            // No parity
    tty.c_cflag &= ~CSTOPB;            // 1 stop bit
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;                // 8 data bits
    tty.c_cflag &= ~CRTSCTS;           // No hardware flow control
    tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);  // Raw mode
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);          // No software flow control
    tty.c_oflag &= ~OPOST;             // Raw output

    tty.c_cc[VMIN]  = 0;
    tty.c_cc[VTIME] = 1;   // 100ms read timeout

    if (tcsetattr(fd, TCSANOW, &tty) != 0) { close(fd); return -1; }
    return fd;
}

int open_pipe(const char *path) {
    // Create named pipe if it doesn't exist
    if (access(path, F_OK) != 0) {
        if (mkfifo(path, 0666) != 0 && errno != EEXIST) return -1;
    }
    // Open non-blocking so we don't hang if no reader yet
    int fd = open(path, O_WRONLY | O_NONBLOCK);
    return fd;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s /dev/ttyUSB0\n", argv[0]);
        return 1;
    }

    signal(SIGINT,  sig_handler);
    signal(SIGTERM, sig_handler);

    // Open log
    logfile = fopen(LOG_PATH, "a");

    char logbuf[128];
    snprintf(logbuf, sizeof(logbuf), "Serial bridge starting on %s", argv[1]);
    log_msg("INFO", logbuf);

    int serial_fd = -1;
    int pipe_fd   = -1;
    char line_buf[MAX_LINE];
    int  line_len = 0;

    while (running) {
        // (Re)connect serial if needed
        if (serial_fd < 0) {
            serial_fd = open_serial(argv[1]);
            if (serial_fd < 0) {
                log_msg("WARN", "Serial port not available, retrying in 2s...");
                sleep(2);
                continue;
            }
            snprintf(logbuf, sizeof(logbuf), "Serial connected: %s", argv[1]);
            log_msg("INFO", logbuf);
        }

        // (Re)open pipe if needed
        if (pipe_fd < 0) {
            pipe_fd = open_pipe(PIPE_PATH);
            // Pipe may not have a reader yet — that's fine
        }

        // Read bytes from serial
        char byte;
        int n = read(serial_fd, &byte, 1);

        if (n < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(1000);   // Nothing available, yield
                continue;
            }
            // Real error — device disconnected
            log_msg("WARN", "Serial read error, reconnecting...");
            close(serial_fd);
            serial_fd = -1;
            line_len  = 0;
            sleep(1);
            continue;
        }

        if (n == 0) { usleep(5000); continue; }

        // Accumulate into line buffer
        if (byte == '\n' || byte == '\r') {
            if (line_len > 0) {
                line_buf[line_len] = '\0';

                // Write to named pipe (LVGL app reads this)
                if (pipe_fd >= 0) {
                    int written = write(pipe_fd, line_buf, line_len);
                    write(pipe_fd, "\n", 1);
                    if (written < 0) {
                        // Reader gone, re-open pipe next loop
                        close(pipe_fd);
                        pipe_fd = -1;
                    }
                }

                // Log raw message (debug)
                if (logfile) fprintf(logfile, "[MSG] %s\n", line_buf);

                line_len = 0;
            }
        } else if (line_len < MAX_LINE - 1) {
            line_buf[line_len++] = byte;
        } else {
            // Line overflow — discard and reset
            log_msg("WARN", "Line overflow, discarding buffer");
            line_len = 0;
        }
    }

    log_msg("INFO", "Serial bridge shutting down");
    if (serial_fd >= 0) close(serial_fd);
    if (pipe_fd   >= 0) close(pipe_fd);
    if (logfile)        fclose(logfile);
    return 0;
}
EOF

ok "Serial bridge: $PM_DIR/src/serial_bridge.c"

# ── T-Beam firmware serial reporter ──────────────────────────────────────
cat > "$PM_DIR/src/tbeam_reporter.cpp" << 'EOF'
// ═══════════════════════════════════════════════════════════════════════
//  PISCES MOON OS — T-BEAM S3 SERIAL REPORTER
//  Runs on T-Beam S3 Supreme (ESP32-S3 / Arduino / PlatformIO)
//
//  Add this to your T-Beam PlatformIO project.
//  Call pm_report_*() functions from wardrive.cpp, gps task, etc.
//  instead of (or in addition to) drawing to the OLED.
//
//  The Panel receives these as JSON lines on /dev/ttyUSB0.
//
//  Add to platformio.ini:
//    [env:tbeam_s3]
//    platform = espressif32
//    board = esp32s3box
//    framework = arduino
//    build_flags = -DTBEAM_S3_SUPREME
//    monitor_speed = 115200
//    upload_speed = 921600
//
//  Author: Eric Becker / Fluid Fortune / Pisces Moon OS / 2026
// ═══════════════════════════════════════════════════════════════════════

#pragma once
#include <Arduino.h>

// ── Serial port for Panel comms ──────────────────────────────────────────
// T-Beam S3: USB-C is Serial (UART0 over USB CDC)
// Panel reads this as /dev/ttyUSB0
#define PM_SERIAL Serial
#define PM_BAUD   115200

namespace PiscesReporter {

void begin() {
    PM_SERIAL.begin(PM_BAUD);
    // Brief delay to let Panel's serial bridge detect the device
    delay(500);
}

// ── Wardrive: WiFi AP discovered ─────────────────────────────────────────
void report_wardrive(const char* bssid, const char* ssid,
                     int rssi, int channel, bool encrypted,
                     const char* vendor = "") {
    // Escape SSID for JSON — replace " with '
    String safe_ssid = String(ssid);
    safe_ssid.replace("\"", "'");
    String safe_vendor = String(vendor);
    safe_vendor.replace("\"", "'");

    PM_SERIAL.printf(
        "{\"type\":\"wardrive\","
        "\"bssid\":\"%s\","
        "\"ssid\":\"%s\","
        "\"rssi\":%d,"
        "\"ch\":%d,"
        "\"enc\":%s,"
        "\"vendor\":\"%s\"}\n",
        bssid, safe_ssid.c_str(), rssi, channel,
        encrypted ? "true" : "false", safe_vendor.c_str()
    );
}

// ── BLE: Device discovered ───────────────────────────────────────────────
void report_ble(const char* mac, const char* name, int rssi) {
    String safe_name = String(name);
    safe_name.replace("\"", "'");

    PM_SERIAL.printf(
        "{\"type\":\"ble\","
        "\"mac\":\"%s\","
        "\"name\":\"%s\","
        "\"rssi\":%d}\n",
        mac, safe_name.c_str(), rssi
    );
}

// ── GPS: Fix data ────────────────────────────────────────────────────────
void report_gps(double lat, double lon, double alt,
                int sats, bool fix,
                float speed_kmh = 0.0f, float heading = 0.0f) {
    PM_SERIAL.printf(
        "{\"type\":\"gps\","
        "\"lat\":%.6f,"
        "\"lon\":%.6f,"
        "\"alt\":%.1f,"
        "\"sats\":%d,"
        "\"fix\":%s,"
        "\"speed\":%.1f,"
        "\"heading\":%.1f}\n",
        lat, lon, alt, sats,
        fix ? "true" : "false",
        speed_kmh, heading
    );
}

// ── LoRa: Packet received ────────────────────────────────────────────────
void report_lora_rx(const char* msg, int rssi, float snr,
                    float freq_mhz = 915.0f) {
    String safe_msg = String(msg);
    safe_msg.replace("\"", "'");

    PM_SERIAL.printf(
        "{\"type\":\"lora\","
        "\"msg\":\"%s\","
        "\"rssi\":%d,"
        "\"snr\":%.1f,"
        "\"freq\":%.1f}\n",
        safe_msg.c_str(), rssi, snr, freq_mhz
    );
}

// ── Probe request captured ───────────────────────────────────────────────
void report_probe(const char* mac, const char* ssid, int rssi,
                  const char* vendor = "") {
    String safe_ssid = String(ssid);
    safe_ssid.replace("\"", "'");

    PM_SERIAL.printf(
        "{\"type\":\"probe\","
        "\"mac\":\"%s\","
        "\"ssid\":\"%s\","
        "\"rssi\":%d,"
        "\"vendor\":\"%s\"}\n",
        mac, safe_ssid.c_str(), rssi, vendor
    );
}

// ── Status telemetry (call every 30s) ────────────────────────────────────
void report_status(int bat_pct, unsigned long uptime_s,
                   float temp_c, float pressure_hpa,
                   bool gps_fix,
                   int wifi_scans, int ble_seen,
                   int lora_rx, int lora_tx) {
    PM_SERIAL.printf(
        "{\"type\":\"status\","
        "\"node\":\"TBEAM_S3\","
        "\"bat\":%d,"
        "\"uptime\":%lu,"
        "\"temp\":%.1f,"
        "\"pressure\":%.1f,"
        "\"gps_fix\":%s,"
        "\"wifi_scans\":%d,"
        "\"ble_seen\":%d,"
        "\"lora_rx\":%d,"
        "\"lora_tx\":%d}\n",
        bat_pct, uptime_s, temp_c, pressure_hpa,
        gps_fix ? "true" : "false",
        wifi_scans, ble_seen, lora_rx, lora_tx
    );
}

// ── Command receiver (call in loop()) ────────────────────────────────────
// Returns the command string if one was received, "" otherwise.
// Panel sends: {"cmd":"scan_start"} etc.
String check_commands() {
    if (!PM_SERIAL.available()) return "";
    String line = PM_SERIAL.readStringUntil('\n');
    line.trim();
    return line;
}

} // namespace PiscesReporter
EOF

ok "T-Beam reporter: $PM_DIR/src/tbeam_reporter.cpp"

# ── Main build script (runs inside Docker) ─────────────────────────────────
cat > "$WORKSPACE/build_inside_docker.sh" << 'DOCKER_SCRIPT'
#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  Run this script INSIDE the Luckfox Docker container.
#  It configures and builds the Buildroot image for the 86Panel.
#
#  Usage (from inside container):
#    cd /home && ./build_inside_docker.sh
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

CY='\033[0;36m'; GR='\033[0;32m'; YL='\033[0;33m'; NC='\033[0m'; BD='\033[1m'
step() { echo -e "\n${CY}▶${NC} ${BD}$1${NC}"; }
ok()   { echo -e "  ${GR}✓${NC} $1"; }
warn() { echo -e "  ${YL}⚠${NC}  $1"; }

step "Installing SDK dependencies"
apt-get update -qq
apt-get install -y -qq \
    git ssh make gcc gcc-multilib g++-multilib \
    module-assistant expect g++ gawk texinfo libssl-dev \
    bison flex fakeroot cmake unzip gperf autoconf \
    device-tree-compiler libncurses5-dev pkg-config bc \
    python-is-python3 passwd openssl openssh-server \
    openssh-client vim file cpio rsync \
    2>/dev/null && ok "Dependencies installed" || warn "Some packages may have failed"

step "Setting up cross-compilation toolchain"
cd /home/luckfox-pico/tools/linux/toolchain/arm-rockchip830-linux-uclibcgnueabihf/
source env_install_toolchain.sh
ok "Toolchain ready"

step "Configuring for RV1106 Luckfox Pico 86Panel"
cd /home/luckfox-pico

# Run build.sh lunch non-interactively
# Option 11 = RV1106_Luckfox_Pico_86Panel, then EMMC, then Buildroot
echo -e "11\n0\n0" | ./build.sh lunch
ok "Board configured: RV1106_Luckfox_Pico_86Panel / EMMC / Buildroot"

step "Building SDK (this takes 30-60 minutes on first run)"
warn "Go make coffee. Seriously."
./build.sh

ok "Build complete!"
echo ""
echo -e "${GR}${BD}Output image:${NC} /home/luckfox-pico/output/image/"
echo ""
echo "Flash with SocToolKit (Windows) or upgrade_tool (Linux):"
echo "  sudo ./rkflash.sh update"
echo ""
echo "Or copy output/image/ to your host machine and use SocToolKit."
DOCKER_SCRIPT

chmod +x "$WORKSPACE/build_inside_docker.sh"
ok "Docker build script: $WORKSPACE/build_inside_docker.sh"

# ── Pull Luckfox Docker image ─────────────────────────────────────────────
step "Pulling Luckfox Docker image"

if $DOCKER_CMD images | grep -q "luckfox_pico"; then
    ok "Luckfox Docker image already present"
else
    info "Pulling luckfoxtech/luckfox_pico:1.0 ..."
    $DOCKER_CMD pull luckfoxtech/luckfox_pico:1.0
    ok "Docker image pulled"
fi

# ── Create and start Docker container ─────────────────────────────────────
step "Creating Luckfox build container"

CONTAINER_NAME="luckfox_pm_panel"

if $DOCKER_CMD ps -a | grep -q "$CONTAINER_NAME"; then
    ok "Container '$CONTAINER_NAME' already exists"
    info "To re-enter: sudo docker start -ai $CONTAINER_NAME"
else
    $DOCKER_CMD create \
        --name "$CONTAINER_NAME" \
        --privileged \
        -v "$WORKSPACE:/home" \
        -w /home \
        luckfoxtech/luckfox_pico:1.0 \
        /bin/bash
    ok "Container created: $CONTAINER_NAME"
fi

# ── Print README ──────────────────────────────────────────────────────────
cat > "$WORKSPACE/README.md" << 'README'
# Pisces Moon Panel — Build Environment

## Directory Structure
```
pisces-moon-panel/
├── luckfox-pico/              ← Luckfox SDK (Buildroot, kernel, U-Boot)
├── luckfox-panel-ui-demo/     ← Official LVGL 86Panel UI demo (reference)
├── pisces-moon-panel-src/     ← Our Pisces Moon Panel application
│   ├── protocol/
│   │   └── pm_protocol.h     ← Serial protocol definitions
│   ├── src/
│   │   ├── serial_bridge.c   ← Panel serial daemon (reads T-Beam)
│   │   └── tbeam_reporter.cpp ← T-Beam firmware reporter
│   ├── include/              ← Panel app headers (LVGL screens)
│   ├── assets/               ← Icons, fonts, images
│   └── scripts/              ← Build and flash helpers
├── build_inside_docker.sh    ← Run this inside the Docker container
└── README.md                 ← This file
```

## Build Steps

### First time — build the base image
```bash
# Enter the Docker container
sudo docker start -ai luckfox_pm_panel

# Inside the container:
cd /home
./build_inside_docker.sh
```
This takes 30-60 minutes. It builds U-Boot, the Linux kernel, and
the Buildroot rootfs for the RV1106 86Panel.

### Flash to the Panel
Connect Panel via USB-C while holding the BOOT button.

**Linux:**
```bash
cd luckfox-pico
sudo ./rkflash.sh update
```

**Windows:**
Use SocToolKit — point it at `output/image/update.img`

### Re-enter Docker for subsequent builds
```bash
sudo docker start -ai luckfox_pm_panel
cd /home/luckfox-pico
./build.sh          # Full rebuild
./build.sh app      # App only (faster)
```

## Next Steps (Phase 1)
1. Get base image booting on Panel ← YOU ARE HERE
2. Add LVGL boot screen with Pisces Moon branding
3. Add serial bridge daemon to rootfs
4. Connect T-Beam, verify JSON messages arrive
5. Build wardrive display screen

## T-Beam Integration
The T-Beam S3 Supreme connects via USB-C → Panel USB-C (OTG hub).
It appears as /dev/ttyUSB0 on the Panel.

Add `#include "tbeam_reporter.cpp"` to your T-Beam PlatformIO project
and call the report_*() functions from wardrive.cpp, GPS task, etc.

See: pisces-moon-panel-src/src/tbeam_reporter.cpp
See: pisces-moon-panel-src/protocol/pm_protocol.h

## Author
Eric Becker / Fluid Fortune / fluidfortune.com / 2026
The Clark Beddows Protocol. Your machine, your rules.
README

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${CY}${BD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CY}${BD}║       PISCES MOON PANEL — BUILD ENV READY            ║${NC}"
echo -e "${CY}${BD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GR}Workspace:${NC}  $WORKSPACE"
echo -e "${GR}SDK:${NC}        $SDK_DIR"
echo -e "${GR}Project:${NC}    $PM_DIR"
echo -e "${GR}Container:${NC}  $CONTAINER_NAME"
echo ""
echo -e "${YL}NEXT STEPS:${NC}"
echo ""
echo -e "  1. Enter the build container:"
echo -e "     ${CY}sudo docker start -ai $CONTAINER_NAME${NC}"
echo ""
echo -e "  2. Inside the container, run the build script:"
echo -e "     ${CY}cd /home && ./build_inside_docker.sh${NC}"
echo ""
echo -e "  3. Go make coffee — first build takes 30-60 minutes."
echo ""
echo -e "  4. Flash the image to the Panel:"
echo -e "     ${CY}cd /home/luckfox-pico && sudo ./rkflash.sh update${NC}"
echo ""
echo -e "${GR}To re-enter Docker later:${NC}"
echo -e "  ${CY}sudo docker start -ai $CONTAINER_NAME${NC}"
echo ""
echo -e "Pisces Moon OS — Fluid Fortune — fluidfortune.com"
echo -e "The Clark Beddows Protocol. Your machine, your rules."
echo ""
