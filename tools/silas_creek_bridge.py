#!/usr/bin/env python3
# ================================================================
# Pisces Moon OS - silas_creek_bridge.py
# Copyright (C) 2026 Eric Becker / Fluid Fortune
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Unified WebSocket bridge for Silas Creek Parkway.
# Zero external dependencies - pure Python stdlib only.
#
# AUTO-DETECTION ORDER:
#   1. T-Beam S3 connected via serial/USB -> relay mode
#      Reads JSON lines from T-Beam, broadcasts to WebSocket clients
#   2. No T-Beam -> native mode
#      Shells out to OS WiFi CLI, formats results as matching JSON
#      Windows:  netsh wlan show networks mode=bssid
#      macOS:    /System/Library/PrivateFrameworks/Apple80211.framework/
#                Versions/Current/Resources/airport -s
#      Linux:    iwlist scan or nmcli dev wifi list
#
# WEBSOCKET ENDPOINT: ws://127.0.0.1:8080
# Same as edge_bridge.py - drop-in compatible with pm_transport.js
#
# AUTO-START:
#   Linux:   systemd user service (created by install.sh)
#   macOS:   ~/Library/LaunchAgents/com.fluidfortune.piscesmoon.plist
#   Windows: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
#            silas_creek_bridge.pyw  (no console window)
# ================================================================

import asyncio
import json
import logging
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('silas_creek_bridge')

# ── Config ───────────────────────────────────────────────────────
WS_HOST      = '127.0.0.1'
WS_PORT      = 8080
SCAN_INTERVAL = 30      # seconds between native scans
SERIAL_BAUD  = 115200
SERIAL_TIMEOUT = 1

# ── OUI vendor lookup (top vendors likely in hospital environments) ──
OUI_TABLE = {
    '00:17:F2': 'Apple',        'AC:BC:32': 'Apple',
    'F4:F1:5A': 'Apple',        '3C:22:FB': 'Apple',
    '00:1A:11': 'Google',       'F4:F5:D8': 'Google',
    '00:23:14': 'Cisco',        '00:25:84': 'Cisco',
    'F8:72:EA': 'Cisco',        'CC:46:D6': 'Cisco',
    '00:1C:0E': 'Cisco',        '00:26:99': 'Cisco',
    '00:0C:E7': 'Ubiquiti',     'FC:EC:DA': 'Ubiquiti',
    '24:A4:3C': 'Ubiquiti',     '74:83:C2': 'Ubiquiti',
    '00:50:F1': 'Ubiquiti',     'DC:9F:DB': 'Ubiquiti',
    '00:1B:63': 'Apple',        '00:17:AB': 'Intel',
    '8C:8D:28': 'Intel',        'AC:FD:CE': 'Intel',
    '00:21:6B': 'Juniper',      '00:12:80': 'Ruckus',
    'D4:68:BA': 'Ruckus',       '00:25:C4': 'Ruckus',
    '00:0B:86': 'Aruba/HP',     '00:1A:1E': 'Aruba/HP',
    '94:B4:0F': 'Aruba/HP',     'D8:C7:C8': 'Aruba/HP',
    '00:11:20': 'Netgear',      'A0:21:B7': 'Netgear',
    '10:0C:6B': 'TP-Link',      '50:C7:BF': 'TP-Link',
    'B0:BE:76': 'Samsung',      '8C:77:12': 'Samsung',
    'B8:27:EB': 'Raspberry Pi', 'DC:A6:32': 'Raspberry Pi',
    'E4:5F:01': 'Raspberry Pi',
}

def oui_lookup(bssid):
    """Return vendor name from BSSID OUI prefix."""
    if not bssid:
        return ''
    prefix = bssid.upper()[:8]
    return OUI_TABLE.get(prefix, '')

def rssi_to_quality(rssi):
    """Convert dBm to percentage quality."""
    if rssi >= -50:  return 100
    if rssi <= -100: return 0
    return int(2 * (rssi + 100))

# ================================================================
# NATIVE WIFI SCANNER
# ================================================================

def scan_windows():
    """Parse netsh wlan show networks mode=bssid output."""
    networks = []
    try:
        out = subprocess.check_output(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            stderr=subprocess.DEVNULL,
            timeout=15,
            encoding='utf-8',
            errors='replace'
        )
        # Parse blocks separated by blank lines
        current = {}
        bssid_count = 0
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('SSID') and ':' in line and 'BSSID' not in line:
                if current:
                    networks.append(current)
                ssid = line.split(':', 1)[1].strip()
                current = {'ssid': ssid, 'bssid': '', 'rssi': -80,
                           'ch': 0, 'enc': True, 'vendor': ''}
                bssid_count = 0
            elif 'BSSID' in line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    bssid = parts[1].strip()
                    # Only use the first BSSID per network block
                    if bssid_count == 0:
                        current['bssid'] = bssid.upper()
                        current['vendor'] = oui_lookup(bssid)
                    bssid_count += 1
            elif 'Signal' in line and ':' in line:
                pct_str = line.split(':', 1)[1].strip().replace('%', '')
                try:
                    pct = int(pct_str)
                    # Convert percentage back to approximate dBm
                    current['rssi'] = int((pct / 2) - 100)
                except ValueError:
                    pass
            elif 'Channel' in line and ':' in line:
                try:
                    current['ch'] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif 'Authentication' in line and ':' in line:
                auth = line.split(':', 1)[1].strip().lower()
                current['enc'] = 'open' not in auth
        if current:
            networks.append(current)
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError) as e:
        log.warning(f"Windows scan failed: {e}")
    return networks

def scan_macos():
    """
    Scan WiFi on macOS using CoreWLAN via Swift one-liner.
    Works on macOS 13+ including Tahoe (macOS 26) where airport is gone.
    Falls back to wdutil info (current network only) if Swift fails.
    Fully compatible with T-Beam bridge output format.
    """
    networks = []

    # ── Primary: CoreWLAN via Swift ───────────────────────────────
    # Swift ships with Xcode CLT on every modern Mac.
    # No pip install, no PyObjC needed. Calls the same API as the
    # macOS WiFi menu bar.
    # Confirmed working on macOS Tahoe (Darwin 25.x)
    # interfaceName and securityMode are properties (not methods) on Tahoe
    swift_script = (
        'import CoreWLAN\n'
        'let client = CWWiFiClient.shared()\n'
        'guard let iface = client.interface() else { exit(1) }\n'
        'guard let nets = try? iface.scanForNetworks(withName: nil) else { exit(1) }\n'
        'for n in nets {\n'
        '    let ssid  = n.ssid ?? ""\n'
        '    let bssid = n.bssid ?? ""\n'
        '    let rssi  = n.rssiValue\n'
        '    let ch    = n.wlanChannel?.channelNumber ?? 0\n'
        '    print("\\(ssid)\\t\\(bssid)\\t\\(rssi)\\t\\(ch)")\n'
        '}\n'
    )

    try:
        result = subprocess.run(
            ['/usr/bin/swift', '-'],
            input=swift_script,
            capture_output=True,
            text=True,
            timeout=60   # Swift JIT compile takes ~15-30s on first run
        )
        log.info(f"Swift rc={result.returncode} stdout={repr(result.stdout[:200])} stderr={repr(result.stderr[:200])}")

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                parts = line.split('\t')
                if len(parts) < 3:
                    continue
                try:
                    ssid  = parts[0]
                    bssid = parts[1].upper() if len(parts) > 1 and parts[1] else ''
                    rssi  = int(parts[2])
                    ch    = int(parts[3]) if len(parts) > 3 else 0
                    # Tahoe removed security property from CWNetwork
                    # Default enc=True (conservative - open networks are rare)
                    enc   = True
                    networks.append({
                        'ssid':   ssid,
                        'bssid':  bssid,
                        'rssi':   rssi,
                        'ch':     ch,
                        'enc':    enc,
                        'vendor': oui_lookup(bssid),
                    })
                except (ValueError, IndexError):
                    continue

            if networks:
                log.info(f"CoreWLAN/Swift: found {len(networks)} networks")
                return networks
        else:
            log.warning(f"Swift returned no usable output")

    except FileNotFoundError:
        log.warning("swift not found at /usr/bin/swift")
    except subprocess.TimeoutExpired:
        log.warning("CoreWLAN/Swift timed out after 60s")
    except Exception as e:
        log.warning(f"CoreWLAN/Swift exception: {type(e).__name__}: {e}")

    # ── Fallback: wdutil info (current network only) ──────────────
    # wdutil needs sudo but gives us at least the connected AP.
    # If we got here without sudo, it will fail gracefully.
    try:
        result = subprocess.run(
            ['wdutil', 'info'],
            capture_output=True, text=True, timeout=10
        )
        out = result.stdout + result.stderr
        # Parse current connection from wdutil info output
        ssid  = re.search(r'SSID\s*:\s*(.+)', out)
        bssid = re.search(r'BSSID\s*:\s*([0-9a-fA-F:]{17})', out)
        rssi  = re.search(r'RSSI\s*:\s*(-\d+)', out)
        ch    = re.search(r'Channel\s*:\s*\w+(\d+)', out)
        sec   = re.search(r'Security\s*:\s*(.+)', out)

        if ssid and rssi:
            bssid_val = bssid.group(1).upper() if bssid else ''
            ch_val    = int(ch.group(1)) if ch else 0
            enc       = bool(sec) and 'none' not in sec.group(1).lower()
            networks.append({
                'ssid':   ssid.group(1).strip(),
                'bssid':  bssid_val,
                'rssi':   int(rssi.group(1)),
                'ch':     ch_val,
                'enc':    enc,
                'vendor': oui_lookup(bssid_val),
            })
            log.info(f"wdutil: found current network (1 result - scan cache unavailable)")
            return networks

    except Exception as e:
        log.warning(f"wdutil fallback failed: {e}")

    log.warning("macOS: all scan methods failed")
    return networks


def scan_linux():
    """Parse nmcli or iwlist output on Linux."""
    networks = []
    # Try nmcli first (available on most modern Linux)
    try:
        out = subprocess.check_output(
            ['nmcli', '-t', '-f', 'SSID,BSSID,SIGNAL,CHAN,SECURITY',
             'dev', 'wifi', 'list', '--rescan', 'yes'],
            stderr=subprocess.DEVNULL,
            timeout=20,
            encoding='utf-8',
            errors='replace'
        )
        for line in out.splitlines():
            if not line.strip():
                continue
            # nmcli -t uses : as separator, but BSSID has colons too
            # Format: SSID:BSSID:SIGNAL:CHAN:SECURITY
            # BSSID is always 17 chars (xx\\:xx\\:xx\\:xx\\:xx\\:xx with escaped colons)
            parts = line.split(':')
            if len(parts) < 8:
                continue
            try:
                ssid  = parts[0].replace('\\:', ':')
                # BSSID is parts 1-6 (each octet separated by escaped colons)
                bssid_parts = [parts[i].replace('\\', '') for i in range(1, 7)]
                bssid = ':'.join(bssid_parts).upper()
                signal = int(parts[7]) if len(parts) > 7 else 50
                rssi   = int((signal / 2) - 100)
                ch     = int(parts[8]) if len(parts) > 8 else 0
                security = ':'.join(parts[9:]) if len(parts) > 9 else ''
                enc    = '--' not in security and security.strip() != ''
                networks.append({
                    'ssid': ssid, 'bssid': bssid, 'rssi': rssi,
                    'ch': ch, 'enc': enc, 'vendor': oui_lookup(bssid)
                })
            except (ValueError, IndexError):
                continue
        if networks:
            return networks
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Fallback: iwlist
    try:
        iface = 'wlan0'
        # Try to find the actual WiFi interface
        try:
            ip_out = subprocess.check_output(['ip', 'link'], encoding='utf-8', timeout=5)
            for line in ip_out.splitlines():
                if 'wl' in line:
                    m = re.search(r'\d+: (wl\S+):', line)
                    if m:
                        iface = m.group(1)
                        break
        except Exception:
            pass

        out = subprocess.check_output(
            ['iwlist', iface, 'scan'],
            stderr=subprocess.DEVNULL,
            timeout=20,
            encoding='utf-8',
            errors='replace'
        )
        current = {}
        for line in out.splitlines():
            line = line.strip()
            if 'Cell' in line and 'Address:' in line:
                if current:
                    networks.append(current)
                bssid = line.split('Address:')[1].strip().upper()
                current = {'ssid': '', 'bssid': bssid, 'rssi': -80,
                           'ch': 0, 'enc': True, 'vendor': oui_lookup(bssid)}
            elif 'ESSID:' in line:
                current['ssid'] = line.split('ESSID:')[1].strip().strip('"')
            elif 'Signal level=' in line:
                m = re.search(r'Signal level=(-?\d+)', line)
                if m:
                    current['rssi'] = int(m.group(1))
            elif 'Channel:' in line:
                m = re.search(r'Channel:(\d+)', line)
                if m:
                    current['ch'] = int(m.group(1))
            elif 'Encryption key:' in line:
                current['enc'] = 'on' in line.lower()
        if current:
            networks.append(current)
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError) as e:
        log.warning(f"Linux scan failed: {e}")
    return networks

def native_scan():
    """Run the OS-appropriate WiFi scan, return list of network dicts."""
    os_name = platform.system()
    if os_name == 'Windows':
        return scan_windows()
    elif os_name == 'Darwin':
        return scan_macos()
    else:
        return scan_linux()

def networks_to_messages(networks):
    """Convert scan results to pm_transport-compatible JSON messages."""
    messages = []
    for n in networks:
        msg = {
            'type': 'wardrive',
            'bssid':  n.get('bssid', ''),
            'ssid':   n.get('ssid', ''),
            'rssi':   n.get('rssi', -80),
            'ch':     n.get('ch', 0),
            'enc':    n.get('enc', True),
            'vendor': n.get('vendor', ''),
            'source': 'native',
        }
        messages.append(msg)
    return messages

# ================================================================
# SERIAL DETECTION
# ================================================================

def find_tbeam():
    """Return serial port path for T-Beam S3 if connected, else None."""
    candidates = []

    os_name = platform.system()
    if os_name == 'Windows':
        # Check COM ports - T-Beam shows as CP210x or CH340
        for i in range(1, 20):
            candidates.append(f'COM{i}')
    elif os_name == 'Darwin':
        import glob
        candidates = (
            glob.glob('/dev/tty.usbserial*') +
            glob.glob('/dev/tty.SLAB_USBtoUART*') +
            glob.glob('/dev/tty.wchusbserial*') +
            glob.glob('/dev/cu.usbserial*')
        )
    else:
        import glob
        candidates = (
            glob.glob('/dev/ttyUSB*') +
            glob.glob('/dev/ttyACM*')
        )

    for port in candidates:
        try:
            import serial
            s = serial.Serial(port, SERIAL_BAUD, timeout=2)
            # Send a ping and wait for any response
            s.write(b'{"cmd":"ping"}\n')
            time.sleep(0.5)
            response = s.read(s.in_waiting or 1)
            s.close()
            if response:
                log.info(f"T-Beam found on {port}")
                return port
        except Exception:
            continue
    return None

# ================================================================
# NATIVE LAN DEVICE SCANNER
# Discovers devices on the current subnet via ping sweep + ARP
# ================================================================

def get_local_subnet():
    """Return the local subnet base e.g. '192.168.1' """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return '.'.join(ip.split('.')[:3])
    except Exception:
        return '192.168.1'

def ping_host(ip, timeout=0.5):
    """Return True if host responds to ping."""
    os_name = platform.system()
    try:
        if os_name == 'Windows':
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(int(timeout*1000)), ip],
                capture_output=True, timeout=timeout+1
            )
        else:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(int(timeout)), ip],
                capture_output=True, timeout=timeout+1
            )
        return result.returncode == 0
    except Exception:
        return False

def get_arp_table():
    """Return dict of ip -> mac from OS ARP table."""
    arp = {}
    os_name = platform.system()
    try:
        if os_name == 'Windows':
            out = subprocess.check_output(['arp', '-a'], timeout=5,
                encoding='utf-8', errors='replace', stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                m = re.match(r'\s+([\d.]+)\s+([\da-f-]+)\s+\w+', line, re.I)
                if m:
                    ip  = m.group(1)
                    mac = m.group(2).replace('-', ':').upper()
                    arp[ip] = mac
        elif os_name == 'Darwin':
            out = subprocess.check_output(['arp', '-a'], timeout=5,
                encoding='utf-8', errors='replace', stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                m = re.search(r'\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]+)', line, re.I)
                if m:
                    arp[m.group(1)] = m.group(2).upper()
        else:
            # Try /proc/net/arp first (no sudo needed)
            try:
                with open('/proc/net/arp') as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if len(parts) >= 4 and parts[2] != '0x0':
                            arp[parts[0]] = parts[3].upper()
            except Exception:
                out = subprocess.check_output(['arp', '-a'], timeout=5,
                    encoding='utf-8', errors='replace', stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    m = re.search(r'\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]+)', line, re.I)
                    if m:
                        arp[m.group(1)] = m.group(2).upper()
    except Exception as e:
        log.warning(f"ARP table read failed: {e}")
    return arp

def resolve_hostname(ip):
    """Reverse DNS lookup with short timeout."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ''

def scan_lan_devices(subnet=None, host_range=range(1, 31)):
    """
    Ping sweep the subnet and return device list.
    Fast: pings .1-.30 concurrently, then reads ARP table.
    """
    if subnet is None:
        subnet = get_local_subnet()

    log.info(f"Scanning LAN subnet {subnet}.0/24 hosts {host_range.start}-{host_range.stop-1}")

    # Concurrent ping sweep to populate ARP cache
    threads = []
    for i in host_range:
        ip = f"{subnet}.{i}"
        t = threading.Thread(target=ping_host, args=(ip, 0.3), daemon=True)
        threads.append(t)
        t.start()

    # Wait for pings with overall timeout
    deadline = time.time() + 5
    for t in threads:
        remaining = max(0, deadline - time.time())
        t.join(timeout=remaining)

    # Read ARP table (populated by pings)
    arp = get_arp_table()

    devices = []
    for ip, mac in arp.items():
        if not ip.startswith(subnet):
            continue
        if mac in ('FF:FF:FF:FF:FF:FF', '00:00:00:00:00:00'):
            continue
        vendor   = oui_lookup(mac)
        hostname = resolve_hostname(ip)
        # Quick ping to confirm alive and get latency
        t0 = time.time()
        alive = ping_host(ip, 0.3)
        latency = round((time.time() - t0) * 1000) if alive else None

        devices.append({
            'type':     'lan',
            'ip':       ip,
            'mac':      mac,
            'hostname': hostname,
            'vendor':   vendor,
            'ping':     latency,
            'status':   'online' if alive else 'offline',
        })

    devices.sort(key=lambda d: [int(x) for x in d['ip'].split('.')])
    log.info(f"LAN scan complete: {len(devices)} devices found")
    return devices


# ================================================================
# PACKET CAPTURE ENGINE
# Streams 802.11 management frames as JSON over WebSocket
# macOS:  sudo tcpdump -I -i en0 (monitor mode, management frames)
# Linux:  creates mon0 virtual interface, tcpdump on it
# T-Beam: firmware already streams frame data via serial
# Windows: not supported (adapter-dependent, Npcap required)
# ================================================================

# Management frame type names
MGMT_SUBTYPES = {
    0:  'assoc-req',      1:  'assoc-resp',
    2:  'reassoc-req',    3:  'reassoc-resp',
    4:  'probe-req',      5:  'probe-resp',
    8:  'beacon',         9:  'atim',
    10: 'disassoc',       11: 'auth',
    12: 'deauth',         13: 'action',
}

# Known attack patterns
DEAUTH_THRESHOLD  = 10   # deauths/second = likely flood
PROBE_STORM_THRESHOLD = 20  # probe-reqs/second = storm

def get_wifi_interface_linux():
    """Return the primary wireless interface name on Linux."""
    try:
        out = subprocess.check_output(['ip', 'link'], encoding='utf-8', timeout=5)
        for line in out.splitlines():
            if 'wl' in line:
                m = re.search(r'\d+: (wl\S+):', line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return 'wlan0'

def get_wifi_interface_macos():
    """Return the primary wireless interface name on macOS."""
    try:
        out = subprocess.check_output(
            ['networksetup', '-listallhardwareports'],
            encoding='utf-8', timeout=5, stderr=subprocess.DEVNULL
        )
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if 'Wi-Fi' in line or 'AirPort' in line:
                for j in range(i, min(i+4, len(lines))):
                    m = re.search(r'Device: (en\d+)', lines[j])
                    if m:
                        return m.group(1)
    except Exception:
        pass
    return 'en0'

def setup_monitor_interface_linux(wifi_iface):
    """
    Create a virtual monitor interface mon0 alongside the managed interface.
    This lets us capture without dropping the WiFi connection.
    Returns the monitor interface name or None on failure.
    """
    mon_iface = 'mon0'
    try:
        # Check if already exists
        result = subprocess.run(['ip', 'link', 'show', mon_iface],
                                capture_output=True, timeout=3)
        if result.returncode != 0:
            # Get the phy device for this interface
            phy_out = subprocess.check_output(
                ['iw', 'dev', wifi_iface, 'info'],
                encoding='utf-8', timeout=5, stderr=subprocess.DEVNULL
            )
            phy = None
            for line in phy_out.splitlines():
                m = re.search(r'wiphy (\d+)', line)
                if m:
                    phy = f"phy{m.group(1)}"
                    break
            if not phy:
                log.warning("Cannot determine phy device")
                return None

            subprocess.run(
                ['sudo', 'iw', 'phy', phy, 'interface', 'add',
                 mon_iface, 'type', 'monitor'],
                check=True, timeout=10, capture_output=True
            )
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', mon_iface, 'up'],
                check=True, timeout=5, capture_output=True
            )
            log.info(f"Created monitor interface {mon_iface} on {phy}")

        return mon_iface
    except subprocess.CalledProcessError as e:
        log.warning(f"Could not create monitor interface: {e}")
        return None
    except Exception as e:
        log.warning(f"Monitor interface setup failed: {e}")
        return None

def teardown_monitor_interface_linux():
    """Remove the virtual monitor interface."""
    try:
        subprocess.run(['sudo', 'iw', 'dev', 'mon0', 'del'],
                       capture_output=True, timeout=5)
        log.info("Removed monitor interface mon0")
    except Exception:
        pass

def parse_tcpdump_line(line):
    """
    Parse a tcpdump management frame line into a dict.
    tcpdump -e output format (with -l for line buffered):
    HH:MM:SS.usec BSSID (OUI) > DEST (OUI), ... Probe Request (SSID) [...]
    Example:
    14:23:45.123456 aa:bb:cc:dd:ee:ff (oui Unknown) > Broadcast, ...
       Probe Request (HomeNetwork) [1.0 2.0 5.5 11.0 Mbit]
    """
    if not line.strip():
        return None

    frame = {
        'type':    'packet',
        'subtype': 'unknown',
        'src':     '',
        'dst':     '',
        'ssid':    '',
        'rssi':    None,
        'ts':      '',
        'raw':     line.strip()[:120],
    }

    try:
        # Timestamp
        ts_m = re.match(r'^(\d{2}:\d{2}:\d{2}\.\d+)', line)
        if ts_m:
            frame['ts'] = ts_m.group(1)

        # MAC addresses
        macs = re.findall(r'([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}'
                          r':[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})', line, re.I)
        if macs:
            frame['src'] = macs[0].upper()
        if len(macs) > 1:
            frame['dst'] = macs[1].upper()

        # Frame subtype from content
        line_lower = line.lower()
        if 'probe request' in line_lower:
            frame['subtype'] = 'probe-req'
            m = re.search(r'Probe Request \(([^)]+)\)', line)
            if m:
                frame['ssid'] = m.group(1)
        elif 'probe response' in line_lower:
            frame['subtype'] = 'probe-resp'
            m = re.search(r'Probe Response \(([^)]+)\)', line)
            if m:
                frame['ssid'] = m.group(1)
        elif 'beacon' in line_lower:
            frame['subtype'] = 'beacon'
            m = re.search(r'Beacon \(([^)]+)\)', line)
            if m:
                frame['ssid'] = m.group(1)
        elif 'deauthentication' in line_lower or 'deauth' in line_lower:
            frame['subtype'] = 'deauth'
        elif 'disassociation' in line_lower or 'disassoc' in line_lower:
            frame['subtype'] = 'disassoc'
        elif 'authentication' in line_lower:
            frame['subtype'] = 'auth'
        elif 'association request' in line_lower:
            frame['subtype'] = 'assoc-req'
        elif 'association response' in line_lower:
            frame['subtype'] = 'assoc-resp'
        elif 'action' in line_lower:
            frame['subtype'] = 'action'

        # Vendor from src MAC
        if frame['src']:
            frame['vendor'] = oui_lookup(frame['src'])

        return frame

    except Exception:
        return None

def check_threats(frame, deauth_window, probe_window):
    """
    Analyze frame for threat indicators.
    Returns list of threat dicts (may be empty).
    """
    threats = []
    subtype = frame.get('subtype', '')
    src     = frame.get('src', '')
    now     = time.time()

    if subtype in ('deauth', 'disassoc'):
        deauth_window.append((now, src))
        # Purge entries older than 1 second
        deauth_window[:] = [(t, s) for t, s in deauth_window if now - t < 1.0]
        if len(deauth_window) >= DEAUTH_THRESHOLD:
            threats.append({
                'type':     'threat',
                'severity': 'critical',
                'name':     'DEAUTH FLOOD',
                'detail':   f"{len(deauth_window)} deauth frames/sec from {src}",
                'src':      src,
                'ts':       frame.get('ts', ''),
            })

    elif subtype == 'probe-req':
        probe_window.append((now, src))
        probe_window[:] = [(t, s) for t, s in probe_window if now - t < 1.0]
        if len(probe_window) >= PROBE_STORM_THRESHOLD:
            threats.append({
                'type':     'threat',
                'severity': 'warning',
                'name':     'PROBE STORM',
                'detail':   f"{len(probe_window)} probe requests/sec",
                'src':      src,
                'ts':       frame.get('ts', ''),
            })

    return threats


class PacketCapture:
    """
    Manages packet capture lifecycle.
    Started/stopped by SilasCreekBridge on demand.
    """
    def __init__(self, broadcast_fn):
        self.broadcast  = broadcast_fn
        self.proc       = None
        self.running    = False
        self._thread    = None
        self._mon_iface = None
        self._deauth_window = []
        self._probe_window  = []
        self.frame_count    = 0
        self.threat_count   = 0

    def start(self, channel=None):
        if self.running:
            return
        os_name = platform.system()

        if os_name == 'Darwin':
            self._start_macos(channel)
        elif os_name == 'Linux':
            self._start_linux(channel)
        else:
            self.broadcast({
                'type': 'packet_error',
                'message': f'Packet capture not supported on {os_name}',
            })
            return

    def _start_macos(self, channel=None):
        iface = get_wifi_interface_macos()
        # tcpdump -I = monitor mode, -e = print link-level headers (MACs),
        # -l = line buffered, -n = no DNS, type mgt = management frames only
        cmd = ['sudo', 'tcpdump', '-I', '-i', iface,
               '-l', '-e', '-n', 'type', 'mgt']
        log.info(f"Starting packet capture: {' '.join(cmd)}")
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            self.running = True
            self.broadcast({'type': 'packet_status', 'state': 'capturing',
                            'iface': iface, 'mode': 'monitor'})
            self._thread = threading.Thread(
                target=self._read_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            log.error(f"tcpdump start failed: {e}")
            self.broadcast({'type': 'packet_error', 'message': str(e)})

    def _start_linux(self, channel=None):
        wifi_iface = get_wifi_interface_linux()
        mon_iface  = setup_monitor_interface_linux(wifi_iface)

        if not mon_iface:
            # Fall back: try putting main interface in monitor mode
            # (will drop WiFi connection but better than nothing)
            log.warning("Could not create mon0 — falling back to wlan0 monitor mode")
            mon_iface = wifi_iface
            try:
                subprocess.run(['sudo', 'ip', 'link', 'set', wifi_iface, 'down'],
                               check=True, capture_output=True, timeout=5)
                subprocess.run(['sudo', 'iw', 'dev', wifi_iface, 'set',
                               'type', 'monitor'],
                               check=True, capture_output=True, timeout=5)
                subprocess.run(['sudo', 'ip', 'link', 'set', wifi_iface, 'up'],
                               check=True, capture_output=True, timeout=5)
            except Exception as e:
                self.broadcast({'type': 'packet_error',
                                'message': f'Monitor mode setup failed: {e}'})
                return
        else:
            self._mon_iface = mon_iface

        # Set channel if specified
        if channel:
            try:
                subprocess.run(['sudo', 'iw', 'dev', mon_iface,
                               'set', 'channel', str(channel)],
                               capture_output=True, timeout=5)
            except Exception:
                pass

        cmd = ['sudo', 'tcpdump', '-i', mon_iface,
               '-l', '-e', '-n', 'type', 'mgt']
        log.info(f"Starting packet capture: {' '.join(cmd)}")
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            self.running = True
            self.broadcast({'type': 'packet_status', 'state': 'capturing',
                            'iface': mon_iface, 'mode': 'monitor'})
            self._thread = threading.Thread(
                target=self._read_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            log.error(f"tcpdump start failed: {e}")
            self.broadcast({'type': 'packet_error', 'message': str(e)})

    def _read_loop(self):
        """Read tcpdump output and broadcast parsed frames."""
        pending = ''
        try:
            for line in self.proc.stdout:
                if not self.running:
                    break
                # tcpdump sometimes splits a frame across two lines
                # Lines starting with whitespace are continuations
                if line.startswith('\t') or line.startswith('  '):
                    pending += ' ' + line.strip()
                    continue
                else:
                    if pending:
                        self._process_line(pending)
                    pending = line.strip()

            if pending:
                self._process_line(pending)
        except Exception as e:
            log.warning(f"Packet read loop error: {e}")
        finally:
            self.running = False
            self.broadcast({'type': 'packet_status', 'state': 'stopped'})

    def _process_line(self, line):
        if not line:
            return
        frame = parse_tcpdump_line(line)
        if not frame:
            return

        # Skip beacon spam by default (too noisy) — client can request them
        if frame['subtype'] == 'beacon':
            return

        self.frame_count += 1
        frame['count'] = self.frame_count
        self.broadcast(frame)

        # Threat detection
        threats = check_threats(
            frame, self._deauth_window, self._probe_window)
        for threat in threats:
            self.threat_count += 1
            self.broadcast(threat)

    def stop(self):
        self.running = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        if self._mon_iface:
            teardown_monitor_interface_linux()
            self._mon_iface = None
        self.broadcast({'type': 'packet_status', 'state': 'stopped',
                        'frames_captured': self.frame_count,
                        'threats_detected': self.threat_count})
        log.info(f"Packet capture stopped. Frames: {self.frame_count}, Threats: {self.threat_count}")

    @property
    def status(self):
        return {
            'type':             'packet_status',
            'state':            'capturing' if self.running else 'stopped',
            'frames_captured':  self.frame_count,
            'threats_detected': self.threat_count,
        }


# ================================================================
# SIMPLE WEBSOCKET SERVER (pure stdlib, no external packages)
# ================================================================
# Implements RFC 6455 WebSocket handshake and framing

import base64
import hashlib
import struct

WS_MAGIC = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

class WSClient:
    def __init__(self, conn, addr):
        self.conn  = conn
        self.addr  = addr
        self.alive = True

    def send(self, data):
        """Send a text frame."""
        if not self.alive:
            return
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            payload = data.encode('utf-8')
            length  = len(payload)
            if length <= 125:
                header = struct.pack('!BB', 0x81, length)
            elif length <= 65535:
                header = struct.pack('!BBH', 0x81, 126, length)
            else:
                header = struct.pack('!BBQ', 0x81, 127, length)
            self.conn.sendall(header + payload)
        except Exception:
            self.alive = False

    def recv_frame(self):
        """Read one WebSocket frame, return text payload or None."""
        try:
            header = self._recv_exactly(2)
            if not header:
                return None
            b1, b2 = header
            # opcode = b1 & 0x0F  (1=text, 8=close)
            opcode = b1 & 0x0F
            if opcode == 8:
                return None  # close frame
            masked  = bool(b2 & 0x80)
            length  = b2 & 0x7F
            if length == 126:
                length = struct.unpack('!H', self._recv_exactly(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self._recv_exactly(8))[0]
            mask_key = self._recv_exactly(4) if masked else b''
            payload  = bytearray(self._recv_exactly(length))
            if masked:
                for i in range(len(payload)):
                    payload[i] ^= mask_key[i % 4]
            return payload.decode('utf-8', errors='replace')
        except Exception:
            return None

    def _recv_exactly(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('disconnected')
            buf += chunk
        return buf

    def close(self):
        self.alive = False
        try:
            self.conn.close()
        except Exception:
            pass


class WSServer:
    def __init__(self, host, port):
        self.host    = host
        self.port    = port
        self.clients = []
        self._lock   = threading.Lock()
        self._sock   = None

    def broadcast(self, msg):
        """Send message to all connected clients."""
        if isinstance(msg, dict):
            msg = json.dumps(msg)
        dead = []
        with self._lock:
            for client in self.clients:
                client.send(msg)
                if not client.alive:
                    dead.append(client)
            for d in dead:
                self.clients.remove(d)

    def send_to(self, client, msg):
        client.send(msg)

    def _do_handshake(self, conn):
        """Perform HTTP→WebSocket upgrade."""
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(1024)
            if not chunk:
                return False
            data += chunk

        lines = data.decode('utf-8', errors='replace').splitlines()
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()

        key = headers.get('sec-websocket-key', '')
        if not key:
            return False

        accept = base64.b64encode(
            hashlib.sha1((key + WS_MAGIC).encode()).digest()
        ).decode()

        response = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n'
            'Access-Control-Allow-Origin: *\r\n'
            '\r\n'
        )
        conn.sendall(response.encode())
        return True

    def _handle_client(self, conn, addr, on_message):
        if not self._do_handshake(conn):
            conn.close()
            return

        client = WSClient(conn, addr)
        with self._lock:
            self.clients.append(client)

        log.info(f"WebSocket client connected: {addr}")
        # Send current status
        client.send({'type': 'status', 'bridge': 'silas_creek_bridge', 'version': '1.0'})

        try:
            while client.alive:
                frame = client.recv_frame()
                if frame is None:
                    break
                try:
                    msg = json.loads(frame)
                    on_message(client, msg)
                except json.JSONDecodeError:
                    pass
        finally:
            client.close()
            with self._lock:
                if client in self.clients:
                    self.clients.remove(client)
            log.info(f"WebSocket client disconnected: {addr}")

    def start(self, on_message):
        """Start accepting connections in a background thread."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        log.info(f"WebSocket server listening on ws://{self.host}:{self.port}")

        def accept_loop():
            while True:
                try:
                    conn, addr = self._sock.accept()
                    t = threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr, on_message),
                        daemon=True
                    )
                    t.start()
                except Exception as e:
                    log.error(f"Accept error: {e}")
                    break

        t = threading.Thread(target=accept_loop, daemon=True)
        t.start()

# ================================================================
# BRIDGE MODES
# ================================================================

class SilasCreekBridge:
    def __init__(self):
        self.ws_server   = WSServer(WS_HOST, WS_PORT)
        self.mode        = None  # 'serial' or 'native'
        self.serial_port = None
        self.serial_conn    = None
        self._scan_cache    = []
        self.packet_capture = None

    def start(self):
        """Auto-detect mode and start bridge."""
        self.ws_server.start(self._on_client_message)
        self.packet_capture = PacketCapture(self.ws_server.broadcast)

        # Try to find a T-Beam
        try:
            import serial as pyserial
            port = find_tbeam()
            if port:
                self.mode        = 'serial'
                self.serial_port = port
                log.info(f"Mode: SERIAL RELAY via {port}")
                self._run_serial_mode()
                return
        except ImportError:
            log.info("pyserial not available - skipping T-Beam detection")

        # Fall back to native scan
        self.mode = 'native'
        log.info(f"Mode: NATIVE SCAN ({platform.system()})")
        self._run_native_mode()

    def _on_client_message(self, client, msg):
        """Handle commands from the HTML app."""
        cmd = msg.get('cmd', '')
        log.info(f"Command from client: {cmd}")

        if cmd == 'scan_start':
            if self.mode == 'serial' and self.serial_conn:
                # bridge_app.cpp protocol: wardrive_start triggers streaming
                self._serial_send({'cmd': 'wardrive_start'})
                # Also do a one-shot wifi_scan for immediate results
                self._serial_send({'cmd': 'wifi_scan'})
                self.ws_server.broadcast({'type': 'scan_start', 'source': 'tdeck'})
            else:
                threading.Thread(target=self._do_native_scan, daemon=True).start()

        elif cmd == 'scan_stop':
            if self.mode == 'serial' and self.serial_conn:
                self._serial_send({'cmd': 'wardrive_stop'})

        elif cmd == 'ping':
            client.send({'type': 'pong', 'bridge_mode': self.mode,
                         'platform': platform.system()})

        elif cmd == 'scan_devices':
            threading.Thread(
                target=self._do_device_scan, daemon=True).start()

        elif cmd == 'packet_start':
            channel = msg.get('channel', None)
            if self.packet_capture:
                threading.Thread(
                    target=self.packet_capture.start,
                    args=(channel,), daemon=True).start()
            else:
                client.send({'type': 'packet_error',
                             'message': 'Packet capture not initialized'})

        elif cmd == 'packet_stop':
            if self.packet_capture:
                threading.Thread(
                    target=self.packet_capture.stop, daemon=True).start()

        elif cmd == 'packet_status':
            if self.packet_capture:
                client.send(self.packet_capture.status)

        elif cmd == 'status':
            client.send({
                'type': 'bridge_status',
                'mode': self.mode,
                'platform': platform.system(),
                'serial_port': self.serial_port,
                'cached_networks': len(self._scan_cache),
            })
            # Also send cached scan results immediately to new client
            for net in self._scan_cache:
                client.send(net)

    def _run_serial_mode(self):
        """Relay JSON lines from T-Beam serial to all WebSocket clients."""
        import serial as pyserial
        buf = ''
        while True:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    log.info(f"Connecting to T-Beam on {self.serial_port}...")
                    self.serial_conn = pyserial.Serial(
                        self.serial_port, SERIAL_BAUD,
                        timeout=SERIAL_TIMEOUT
                    )
                    log.info("T-Beam connected")
                    self.ws_server.broadcast({
                        'type': 'bridge_status',
                        'mode': 'serial',
                        'serial_port': self.serial_port,
                    })

                chunk = self.serial_conn.read(256).decode('utf-8', errors='replace')
                if not chunk:
                    continue
                buf += chunk
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        translated = self._translate_tdeck(msg)
                        if translated:
                            for m in translated:
                                self.ws_server.broadcast(m)
                                # Cache wardrive networks
                                if m.get('type') == 'wardrive':
                                    bssid = m.get('bssid', '')
                                    self._scan_cache = [
                                        n for n in self._scan_cache
                                        if n.get('bssid') != bssid
                                    ]
                                    self._scan_cache.append(m)
                    except json.JSONDecodeError:
                        log.debug(f"Serial non-JSON: {line[:60]}")

            except Exception as e:
                log.warning(f"Serial error: {e} - reconnecting in 5s")
                if self.serial_conn:
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None
                self.ws_server.broadcast({'type': 'bridge_status', 'mode': 'serial',
                                          'error': 'T-Beam disconnected, reconnecting...'})
                time.sleep(5)

    def _run_native_mode(self):
        """Periodically scan WiFi and broadcast results."""
        # Announce mode to any early-connecting clients
        self.ws_server.broadcast({
            'type': 'bridge_status',
            'mode': 'native',
            'platform': platform.system(),
            'scan_interval': SCAN_INTERVAL,
        })
        while True:
            self._do_native_scan()
            time.sleep(SCAN_INTERVAL)

    def _do_native_scan(self):
        log.info("Running native WiFi scan...")
        networks = native_scan()
        log.info(f"Found {len(networks)} networks")

        self.ws_server.broadcast({'type': 'scan_start', 'source': 'native'})
        self._scan_cache = []
        for msg in networks_to_messages(networks):
            self._scan_cache.append(msg)
            self.ws_server.broadcast(msg)
        self.ws_server.broadcast({
            'type': 'scan_complete',
            'source': 'native',
            'count': len(networks),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        })

    def _do_device_scan(self):
        """Scan LAN for connected devices and broadcast results."""
        log.info("Running LAN device scan...")
        self.ws_server.broadcast({'type': 'scan_start', 'source': 'device_scan'})
        try:
            devices = scan_lan_devices()
            for d in devices:
                self.ws_server.broadcast({
                    'type':     'arp',
                    'ip':       d['ip'],
                    'mac':      d['mac'],
                    'hostname': d['hostname'],
                    'vendor':   d['vendor'],
                    'ping':     d['ping'],
                    'status':   d['status'],
                    'source':   'native',
                })
            self.ws_server.broadcast({
                'type':      'scan_complete',
                'source':    'device_scan',
                'count':     len(devices),
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            })
            log.info(f"Device scan broadcast complete: {len(devices)} devices")
        except Exception as e:
            log.error(f"Device scan failed: {e}")
            self.ws_server.broadcast({'type': 'error', 'message': str(e)})

    def _translate_tdeck(self, msg):
        """
        Translate bridge_app.cpp / wardrive.cpp protocol into
        the Pisces Moon WebSocket protocol the HTML apps expect.

        bridge_app.cpp emits:
          {"ok":true, "data":{...}}              -- command response
          {"event":"wifi_seen", ...}             -- wardrive streaming
          {"event":"ble_seen", ...}              -- BLE streaming
          {"event":"ready"/"disconnect"/"timeout"} -- lifecycle

        wardrive.cpp streams (when wardrive_bridge_streaming=true):
          {"event":"wifi_seen","mac","ssid","rssi","ch","enc","lat","lng"}
          {"event":"ble_seen","mac","name","rssi","lat","lng"}

        wifi_scan response:
          {"ok":true,"data":{"count":N,"networks":[{"ssid","bssid","rssi","channel","enc"}]}}

        Target WebSocket format for HTML apps:
          {"type":"wardrive","ssid","bssid","rssi","ch","enc":bool,"vendor","lat","lng"}
          {"type":"ble","mac","name","rssi","vendor"}
          {"type":"bridge_status","mode","platform"}
          {"type":"scan_complete","count","source"}
        """
        event = msg.get('event', '')
        ok    = msg.get('ok', None)

        out = []

        # ── Streaming wardrive events ──────────────────────────────────
        if event == 'wifi_seen':
            bssid  = msg.get('mac', '')
            ssid   = msg.get('ssid', '')
            rssi   = msg.get('rssi', -80)
            ch     = msg.get('ch', 0)
            enc_s  = msg.get('enc', 'WPA')
            lat    = msg.get('lat', 0.0)
            lng    = msg.get('lng', 0.0)
            out.append({
                'type':   'wardrive',
                'ssid':   ssid,
                'bssid':  bssid,
                'rssi':   rssi,
                'ch':     ch,
                'enc':    enc_s != 'OPEN',
                'vendor': oui_lookup(bssid),
                'lat':    lat,
                'lng':    lng,
                'source': 'tdeck',
            })

        # ── Streaming BLE events ───────────────────────────────────────
        elif event == 'ble_seen':
            mac  = msg.get('mac', '')
            name = msg.get('name', '')
            rssi = msg.get('rssi', -80)
            out.append({
                'type':   'ble',
                'mac':    mac,
                'name':   name,
                'rssi':   rssi,
                'vendor': oui_lookup(mac),
                'source': 'tdeck',
            })

        # ── wifi_scan one-shot response ────────────────────────────────
        elif ok is True and 'data' in msg:
            data = msg['data']
            # wifi_scan returns data.networks[]
            if 'networks' in data:
                networks = data['networks']
                for net in networks:
                    bssid  = net.get('bssid', '')
                    enc_s  = net.get('enc', 'WPA')
                    out.append({
                        'type':   'wardrive',
                        'ssid':   net.get('ssid', ''),
                        'bssid':  bssid,
                        'rssi':   net.get('rssi', -80),
                        'ch':     net.get('channel', 0),
                        'enc':    enc_s != 'OPEN',
                        'vendor': oui_lookup(bssid),
                        'source': 'tdeck',
                    })
                out.append({
                    'type':   'scan_complete',
                    'count':  len(networks),
                    'source': 'tdeck',
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
                })
            # ping / status responses
            elif 'pong' in data or 'os' in data:
                out.append({
                    'type':        'bridge_status',
                    'mode':        'serial',
                    'platform':    'T-Deck',
                    'device_os':   data.get('os', 'Pisces Moon'),
                    'version':     data.get('version', ''),
                    'uptime_s':    data.get('uptime_s', 0),
                })
            # wardrive_status response
            elif 'active' in data:
                out.append({
                    'type':   'wardrive_status',
                    'active': data.get('active', False),
                    'count':  data.get('networks', 0),
                    'source': 'tdeck',
                })

        # ── Lifecycle events ───────────────────────────────────────────
        elif event == 'ready':
            log.info(f"T-Deck ready: {msg.get('os','')} {msg.get('version','')}")
            # Announce to clients
            out.append({
                'type':    'bridge_status',
                'mode':    'serial',
                'platform':'T-Deck',
                'version': msg.get('version', ''),
                'source':  'tdeck',
            })
        elif event == 'disconnect':
            log.info(f"T-Deck disconnected: {msg.get('reason','')}")
        elif event == 'timeout':
            log.warning("T-Deck reported host timeout")
        elif event == 'thinking':
            log.debug("T-Deck Gemini is thinking...")
        else:
            # Unknown - log it but don't forward garbage to clients
            log.debug(f"T-Deck unhandled msg: {str(msg)[:80]}")

        return out

    def _serial_send(self, msg):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                line = json.dumps(msg) + '\n'
                self.serial_conn.write(line.encode())
            except Exception as e:
                log.warning(f"Serial send error: {e}")


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == '__main__':
    log.info("=" * 60)
    log.info("Silas Creek Parkway - Edge Bridge v1.0")
    log.info("Pisces Moon OS / Fluid Fortune / fluidfortune.com")
    log.info(f"Platform: {platform.system()} {platform.release()}")
    log.info(f"WebSocket: ws://{WS_HOST}:{WS_PORT}")
    log.info("=" * 60)

    bridge = SilasCreekBridge()
    try:
        bridge.start()  # blocks in native or serial loop
    except KeyboardInterrupt:
        log.info("Bridge stopped.")
