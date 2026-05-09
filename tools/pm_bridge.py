#!/usr/bin/env python3
# ================================================================
# Pisces Moon OS - pm_bridge.py
# Copyright (C) 2026 Eric Becker / Fluid Fortune
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Unified WebSocket bridge for Pisces Moon.
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
#            pm_bridge.pyw  (no console window)
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
log = logging.getLogger('Pisces Moon Bridge')


# ================================================================
# DATA STORAGE - host-side persistence for wardrive sessions
# Every session is one WiGLE 1.4 CSV file owned by the bridge.
# Edge devices (T-Deck, T-Beam Supreme, headless ESP32-S3, native
# scan) are interchangeable - the host is the source of truth.
# ================================================================

def get_data_dir():
    """OS-appropriate user data directory."""
    home = os.path.expanduser('~')
    sysname = platform.system()
    if sysname == 'Darwin':
        path = os.path.join(home, 'Library', 'Application Support', 'PiscesMoon')
    elif sysname == 'Windows':
        path = os.path.join(os.environ.get('APPDATA', home), 'PiscesMoon')
    else:
        xdg = os.environ.get('XDG_DATA_HOME')
        if xdg:
            path = os.path.join(xdg, 'pisces-moon')
        else:
            path = os.path.join(home, '.local', 'share', 'pisces-moon')
    return path

def get_sessions_dir():
    d = os.path.join(get_data_dir(), 'sessions')
    os.makedirs(d, exist_ok=True)
    return d

WIGLE_HEADER_1 = ('WigleWifi-1.4,appRelease=PiscesMoon-Bridge,model=Bridge,'
                  'release=v0.5,device=PMOS,display=PMOS,board=PMOS,brand=FluidFortune,'
                  'star=Sol,body=Earth,subBody=0')
WIGLE_HEADER_2 = ('MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,'
                  'CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type')

class WardriveLog:
    """Thread-safe append-only WiGLE CSV writer."""
    def __init__(self):
        self._lock = threading.Lock()
        self._fh = None
        self._path = None
        self._session_id = None
        self._row_count = 0

    def open_new(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
            stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
            self._session_id = stamp
            self._path = os.path.join(get_sessions_dir(), f'wardrive_{stamp}.csv')
            self._fh = open(self._path, 'w', encoding='utf-8', newline='')
            self._fh.write(WIGLE_HEADER_1 + '\n')
            self._fh.write(WIGLE_HEADER_2 + '\n')
            self._fh.flush()
            self._row_count = 0
            log.info(f"Wardrive session opened: {self._path}")
            return {'session_id': self._session_id, 'path': self._path}

    def append(self, row):
        with self._lock:
            if not self._fh:
                stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
                self._session_id = stamp
                self._path = os.path.join(get_sessions_dir(), f'wardrive_{stamp}.csv')
                self._fh = open(self._path, 'w', encoding='utf-8', newline='')
                self._fh.write(WIGLE_HEADER_1 + '\n')
                self._fh.write(WIGLE_HEADER_2 + '\n')
                log.info(f"Wardrive session auto-opened: {self._path}")

            bssid = row.get('bssid') or row.get('mac') or ''
            ssid  = (row.get('ssid') or '').replace(',', '_').replace('\n', ' ')
            enc   = row.get('enc')
            sec   = row.get('sec') or row.get('security')
            if sec is None:
                sec = ('WPA' if enc else 'OPEN') if enc is not None else 'UNKNOWN'
            ch    = row.get('channel') or row.get('ch') or 0
            rssi  = row.get('rssi') or -100
            lat   = row.get('lat') or 0
            lng   = row.get('lng') or row.get('lon') or 0
            alt   = row.get('alt') or row.get('alt_m') or 0
            ts    = time.strftime('%Y-%m-%d %H:%M:%S')

            try:
                line = f'{bssid},{ssid},[{sec}],{ts},{ch},{rssi},{float(lat):.6f},{float(lng):.6f},{float(alt):.1f},5,WIFI\n'
                self._fh.write(line)
                self._fh.flush()
                self._row_count += 1
                return True
            except Exception as e:
                log.warning(f"Wardrive append failed: {e}")
                return False

    def close(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
                log.info(f"Wardrive session closed: {self._path} ({self._row_count} rows)")
                result = {
                    'session_id': self._session_id,
                    'path': self._path,
                    'rows': self._row_count,
                }
                self._fh = None
                self._session_id = None
                self._path = None
                self._row_count = 0
                return result
            return None

    def status(self):
        with self._lock:
            return {
                'open': self._fh is not None,
                'session_id': self._session_id,
                'path': self._path,
                'rows': self._row_count,
            }

def list_wardrive_sessions():
    sessions = []
    try:
        d = get_sessions_dir()
        for fname in sorted(os.listdir(d), reverse=True):
            if not fname.startswith('wardrive_') or not fname.endswith('.csv'):
                continue
            full = os.path.join(d, fname)
            try:
                stat = os.stat(full)
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                    rows = max(0, sum(1 for _ in f) - 2)
                sessions.append({
                    'name':  fname,
                    'path':  full,
                    'size':  stat.st_size,
                    'mtime': stat.st_mtime,
                    'rows':  rows,
                })
            except Exception:
                continue
    except Exception as e:
        log.warning(f"List sessions failed: {e}")
    return sessions

def read_wardrive_session(name):
    if not name or '/' in name or '\\' in name or '..' in name:
        return None
    path = os.path.join(get_sessions_dir(), name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        log.warning(f"Read session failed: {e}")
        return None

# Module-level wardrive log instance
wardrive_log = WardriveLog()


# ── BLE LOGGING ──────────────────────────────────────────────────
# CSV header for BLE observations
BLE_HEADER_1 = ('PiscesMoonBLE-1.0,appRelease=PiscesMoon-Bridge,model=Bridge,'
                'release=v0.5,device=PMOS,brand=FluidFortune')
BLE_HEADER_2 = ('MAC,Name,RSSI,FirstSeen,LastSeen,Vendor,'
                'CurrentLatitude,CurrentLongitude,AltitudeMeters,'
                'ManufacturerData,ServiceUUIDs,AddrType,Source,Type')

class BleLog:
    """Thread-safe append-only BLE observation CSV writer.
       Mirrors WardriveLog architecture for parallel disk logging."""
    def __init__(self):
        self._lock = threading.Lock()
        self._fh = None
        self._path = None
        self._session_id = None
        self._row_count = 0

    def open_new(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
            stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
            self._session_id = stamp
            self._path = os.path.join(get_sessions_dir(), f'ble_{stamp}.csv')
            self._fh = open(self._path, 'w', encoding='utf-8', newline='')
            self._fh.write(BLE_HEADER_1 + '\n')
            self._fh.write(BLE_HEADER_2 + '\n')
            self._fh.flush()
            self._row_count = 0
            log.info(f"BLE session opened: {self._path}")
            return {'session_id': self._session_id, 'path': self._path}

    def append(self, row):
        with self._lock:
            if not self._fh:
                stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
                self._session_id = stamp
                self._path = os.path.join(get_sessions_dir(), f'ble_{stamp}.csv')
                self._fh = open(self._path, 'w', encoding='utf-8', newline='')
                self._fh.write(BLE_HEADER_1 + '\n')
                self._fh.write(BLE_HEADER_2 + '\n')
                log.info(f"BLE session auto-opened: {self._path}")

            mac    = (row.get('mac') or row.get('bssid') or '').replace(',', '')
            name   = (row.get('name') or '').replace(',', '_').replace('\n', ' ')
            rssi   = row.get('rssi') or -100
            vendor = (row.get('vendor') or '').replace(',', '_')
            lat    = row.get('lat') or 0
            lng    = row.get('lng') or row.get('lon') or 0
            alt    = row.get('alt') or row.get('alt_m') or 0
            mfg    = (row.get('mfg_data') or row.get('manufacturer_data') or '').replace(',', ';')
            uuids  = (row.get('service_uuids') or row.get('uuids') or '').replace(',', ';')
            addr_t = row.get('addr_type') or 'unknown'
            source = row.get('source') or 'native'
            ts     = time.strftime('%Y-%m-%d %H:%M:%S')

            try:
                line = (f'{mac},{name},{rssi},{ts},{ts},{vendor},'
                        f'{float(lat):.6f},{float(lng):.6f},{float(alt):.1f},'
                        f'{mfg},{uuids},{addr_t},{source},BLE\n')
                self._fh.write(line)
                self._fh.flush()
                self._row_count += 1
                return True
            except Exception as e:
                log.warning(f"BLE append failed: {e}")
                return False

    def close(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
                log.info(f"BLE session closed: {self._path} ({self._row_count} rows)")
                result = {
                    'session_id': self._session_id,
                    'path': self._path,
                    'rows': self._row_count,
                }
                self._fh = None
                self._session_id = None
                self._path = None
                self._row_count = 0
                return result
            return None

    def status(self):
        with self._lock:
            return {
                'open': self._fh is not None,
                'session_id': self._session_id,
                'path': self._path,
                'rows': self._row_count,
            }

ble_log = BleLog()


# ── PROBE REQUEST LOGGING ────────────────────────────────────────
PROBE_HEADER_1 = ('PiscesMoonProbe-1.0,appRelease=PiscesMoon-Bridge,model=Bridge,'
                  'release=v0.5,device=PMOS,brand=FluidFortune')
PROBE_HEADER_2 = ('ClientMAC,SSIDRequested,RSSI,FirstSeen,LastSeen,SightingCount,'
                  'Vendor,CurrentLatitude,CurrentLongitude,AltitudeMeters,Source,Type')

class ProbeLog:
    """Thread-safe append-only probe-request CSV writer."""
    def __init__(self):
        self._lock = threading.Lock()
        self._fh = None
        self._path = None
        self._session_id = None
        self._row_count = 0

    def open_new(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
            stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
            self._session_id = stamp
            self._path = os.path.join(get_sessions_dir(), f'probes_{stamp}.csv')
            self._fh = open(self._path, 'w', encoding='utf-8', newline='')
            self._fh.write(PROBE_HEADER_1 + '\n')
            self._fh.write(PROBE_HEADER_2 + '\n')
            self._fh.flush()
            self._row_count = 0
            log.info(f"Probe session opened: {self._path}")
            return {'session_id': self._session_id, 'path': self._path}

    def append(self, row):
        with self._lock:
            if not self._fh:
                stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
                self._session_id = stamp
                self._path = os.path.join(get_sessions_dir(), f'probes_{stamp}.csv')
                self._fh = open(self._path, 'w', encoding='utf-8', newline='')
                self._fh.write(PROBE_HEADER_1 + '\n')
                self._fh.write(PROBE_HEADER_2 + '\n')
                log.info(f"Probe session auto-opened: {self._path}")

            mac    = (row.get('mac') or row.get('client') or '').replace(',', '')
            ssid   = (row.get('ssid') or row.get('ssid_requested') or '').replace(',', '_').replace('\n', ' ')
            rssi   = row.get('rssi') or -100
            count  = row.get('count') or row.get('sightings') or 1
            vendor = (row.get('vendor') or '').replace(',', '_')
            lat    = row.get('lat') or 0
            lng    = row.get('lng') or row.get('lon') or 0
            alt    = row.get('alt') or row.get('alt_m') or 0
            source = row.get('source') or 'tdeck'
            ts     = time.strftime('%Y-%m-%d %H:%M:%S')

            try:
                line = (f'{mac},{ssid},{rssi},{ts},{ts},{count},{vendor},'
                        f'{float(lat):.6f},{float(lng):.6f},{float(alt):.1f},'
                        f'{source},PROBE\n')
                self._fh.write(line)
                self._fh.flush()
                self._row_count += 1
                return True
            except Exception as e:
                log.warning(f"Probe append failed: {e}")
                return False

    def close(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
                log.info(f"Probe session closed: {self._path} ({self._row_count} rows)")
                result = {
                    'session_id': self._session_id,
                    'path': self._path,
                    'rows': self._row_count,
                }
                self._fh = None
                self._session_id = None
                self._path = None
                self._row_count = 0
                return result
            return None

    def status(self):
        with self._lock:
            return {
                'open': self._fh is not None,
                'session_id': self._session_id,
                'path': self._path,
                'rows': self._row_count,
            }

probe_log = ProbeLog()


# ── LORA MESH LOGGING ────────────────────────────────────────────
LORA_HEADER_1 = ('PiscesMoonLoRa-1.0,appRelease=PiscesMoon-Bridge,model=Bridge,'
                 'release=v0.5,device=PMOS,brand=FluidFortune')
LORA_HEADER_2 = ('NodeFrom,NodeTo,RSSI,SNR,Frequency,SF,Bandwidth,'
                 'FirstSeen,LinkQuality,GPSLatFrom,GPSLonFrom,GPSLatTo,GPSLonTo,Type')

class LoraLog:
    """Thread-safe append-only LoRa mesh link CSV writer."""
    def __init__(self):
        self._lock = threading.Lock()
        self._fh = None
        self._path = None
        self._session_id = None
        self._row_count = 0

    def open_new(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
            stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
            self._session_id = stamp
            self._path = os.path.join(get_sessions_dir(), f'lora_{stamp}.csv')
            self._fh = open(self._path, 'w', encoding='utf-8', newline='')
            self._fh.write(LORA_HEADER_1 + '\n')
            self._fh.write(LORA_HEADER_2 + '\n')
            self._fh.flush()
            self._row_count = 0
            log.info(f"LoRa session opened: {self._path}")
            return {'session_id': self._session_id, 'path': self._path}

    def append(self, row):
        with self._lock:
            if not self._fh:
                stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
                self._session_id = stamp
                self._path = os.path.join(get_sessions_dir(), f'lora_{stamp}.csv')
                self._fh = open(self._path, 'w', encoding='utf-8', newline='')
                self._fh.write(LORA_HEADER_1 + '\n')
                self._fh.write(LORA_HEADER_2 + '\n')

            n_from = (row.get('node_from') or row.get('from') or '').replace(',', '')
            n_to   = (row.get('node_to') or row.get('to') or '').replace(',', '')
            rssi   = row.get('rssi') or -100
            snr    = row.get('snr') or 0
            freq   = row.get('freq') or row.get('frequency') or 915.0
            sf     = row.get('sf') or row.get('spreading_factor') or 7
            bw     = row.get('bw') or row.get('bandwidth') or 125
            qual   = row.get('quality') or row.get('link_quality') or 0
            lat_f  = row.get('lat_from') or 0
            lon_f  = row.get('lon_from') or 0
            lat_t  = row.get('lat_to') or 0
            lon_t  = row.get('lon_to') or 0
            ts     = time.strftime('%Y-%m-%d %H:%M:%S')

            try:
                line = (f'{n_from},{n_to},{rssi},{snr},{freq},{sf},{bw},'
                        f'{ts},{qual},{float(lat_f):.6f},{float(lon_f):.6f},'
                        f'{float(lat_t):.6f},{float(lon_t):.6f},LORA\n')
                self._fh.write(line)
                self._fh.flush()
                self._row_count += 1
                return True
            except Exception as e:
                log.warning(f"LoRa append failed: {e}")
                return False

    def close(self):
        with self._lock:
            if self._fh:
                try: self._fh.close()
                except Exception: pass
                log.info(f"LoRa session closed: {self._path} ({self._row_count} rows)")
                result = {
                    'session_id': self._session_id,
                    'path': self._path,
                    'rows': self._row_count,
                }
                self._fh = None
                self._session_id = None
                self._path = None
                self._row_count = 0
                return result
            return None

    def status(self):
        with self._lock:
            return {
                'open': self._fh is not None,
                'session_id': self._session_id,
                'path': self._path,
                'rows': self._row_count,
            }

lora_log = LoraLog()


# ── SESSION BUNDLE EXPORT ────────────────────────────────────────
def export_session_bundle(session_id=None):
    """Bundle all CSVs from a session into a single .pmsession archive (ZIP).
       If session_id is None, bundles the most recent session of each type."""
    import zipfile

    bundle_stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
    bundle_name = f'pmsession_{bundle_stamp}.pmsession'
    bundle_path = os.path.join(get_sessions_dir(), bundle_name)

    # Build manifest
    manifest = {
        'created':    bundle_stamp,
        'creator':    'pm_bridge.py v1.2',
        'session_id': session_id or 'latest',
        'platform':   platform.system(),
        'files':      [],
    }

    sessions_dir = get_sessions_dir()
    files_to_bundle = []

    if session_id:
        # Bundle exact-match session files
        for prefix in ('wardrive_', 'ble_', 'probes_', 'lora_'):
            candidate = os.path.join(sessions_dir, f'{prefix}{session_id}.csv')
            if os.path.exists(candidate):
                files_to_bundle.append((candidate, f'{prefix}{session_id}.csv'))
    else:
        # Bundle the most recent file of each type
        for prefix in ('wardrive_', 'ble_', 'probes_', 'lora_'):
            try:
                matches = sorted([f for f in os.listdir(sessions_dir)
                                 if f.startswith(prefix) and f.endswith('.csv')],
                                reverse=True)
                if matches:
                    full = os.path.join(sessions_dir, matches[0])
                    files_to_bundle.append((full, matches[0]))
            except Exception:
                continue

    if not files_to_bundle:
        return {'error': 'No session files found', 'bundle': None}

    try:
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for src_path, arcname in files_to_bundle:
                zf.write(src_path, arcname)
                manifest['files'].append({
                    'name': arcname,
                    'size': os.path.getsize(src_path),
                })
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))

        log.info(f"Session bundle created: {bundle_path} ({len(files_to_bundle)} files)")
        return {
            'bundle':   bundle_path,
            'name':     bundle_name,
            'files':    [f['name'] for f in manifest['files']],
            'size':     os.path.getsize(bundle_path),
        }
    except Exception as e:
        log.warning(f"Bundle export failed: {e}")
        return {'error': str(e), 'bundle': None}


# ── Config ───────────────────────────────────────────────────────
WS_HOST      = '127.0.0.1'
WS_PORT      = 8080
SCAN_INTERVAL = 30      # seconds between native scans
SERIAL_BAUD  = 921600   # T-Deck Plus / T-Beam S3 Supreme native USB CDC baud
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
    # Espressif (ESP32, ESP8266 - DIY/IoT/hobbyist devices)
    '24:0A:C4': 'Espressif',    '24:62:AB': 'Espressif',    '24:6F:28': 'Espressif',
    '24:DC:C3': 'Espressif',    '24:D7:EB': 'Espressif',    '30:AE:A4': 'Espressif',
    '30:C6:F7': 'Espressif',    '34:85:18': 'Espressif',    '3C:71:BF': 'Espressif',
    '40:91:51': 'Espressif',    '4C:75:25': 'Espressif',    '4C:EB:D6': 'Espressif',
    '54:43:B2': 'Espressif',    '5C:CF:7F': 'Espressif',    '60:01:94': 'Espressif',
    '68:67:25': 'Espressif',    '7C:9E:BD': 'Espressif',    '7C:DF:A1': 'Espressif',
    '80:7D:3A': 'Espressif',    '84:0D:8E': 'Espressif',    '84:CC:A8': 'Espressif',
    '84:F3:EB': 'Espressif',    '8C:AA:B5': 'Espressif',    '94:B5:55': 'Espressif',
    '94:B9:7E': 'Espressif',    '94:E6:86': 'Espressif',    '98:F4:AB': 'Espressif',
    '9C:9C:1F': 'Espressif',    'A0:20:A6': 'Espressif',    'A4:CF:12': 'Espressif',
    'A8:03:2A': 'Espressif',    'AC:67:B2': 'Espressif',    'AC:D0:74': 'Espressif',
    'B4:E6:2D': 'Espressif',    'B8:D6:1A': 'Espressif',    'BC:DD:C2': 'Espressif',
    'BC:FF:4D': 'Espressif',    'C4:4F:33': 'Espressif',    'C4:5B:BE': 'Espressif',
    'C8:2B:96': 'Espressif',    'C8:C9:A3': 'Espressif',    'C8:F0:9E': 'Espressif',
    'CC:50:E3': 'Espressif',    'CC:DB:A7': 'Espressif',    'D8:A0:1D': 'Espressif',
    'D8:BF:C0': 'Espressif',    'DC:54:75': 'Espressif',    'DC:4F:22': 'Espressif',
    'E0:98:06': 'Espressif',    'E8:31:CD': 'Espressif',    'E8:DB:84': 'Espressif',
    'EC:64:C9': 'Espressif',    'EC:FA:BC': 'Espressif',    'F0:08:D1': 'Espressif',
    'F4:CF:A2': 'Espressif',    'F4:12:FA': 'Espressif',    'F8:B7:97': 'Espressif',
    'FC:F5:C4': 'Espressif',    'FC:6F:D7': 'Espressif',
}

def ble_mfg_lookup(hex_code):
    """Bluetooth SIG company identifier lookup for common vendors."""
    if not hex_code:
        return ''
    h = hex_code.upper().replace(' ', '')
    # Common BLE manufacturer codes (subset - covers most consumer devices)
    table = {
        '004C': 'Apple',           '0006': 'Microsoft',
        '0075': 'Samsung',         '00E0': 'Google',
        '0087': 'Garmin',          '00D2': 'Bose',
        '0157': 'Anhui Huami',     '038F': 'Xiaomi',
        '0590': 'Logitech',        '0499': 'Ruuvi',
        '0001': 'Ericsson',        '0002': 'Intel',
        '000F': 'Broadcom',        '0030': 'ST Micro',
        '0059': 'Nordic',          '02E5': 'Espressif',
        '02FF': 'Silicon Labs',    '0156': 'Tile',
        '004A': 'BlackBerry',      '00C4': 'LG',
        '0118': 'Withings',        '0131': 'Cypress',
        '0171': 'Amazon',          '01D7': 'Polar',
        '02E0': 'OPPO',            '02FE': 'Sonos',
    }
    return table.get(h, '')


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

def scan_android():
    """Use termux-wifi-scaninfo to scan on Android (requires Termux:API app)."""
    networks = []
    try:
        import json as _json
        result = subprocess.run(
            ['termux-wifi-scaninfo'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0 or not result.stdout.strip():
            log.warning(f"termux-wifi-scaninfo failed: {result.stderr[:100]}")
            log.warning("Install Termux:API app + pkg install termux-api")
            return networks
        data = _json.loads(result.stdout)
        for ap in data:
            ssid    = ap.get('ssid', '')
            bssid   = ap.get('bssid', '')
            rssi    = ap.get('rssi', ap.get('level', -99))  # termux uses 'rssi'
            freq    = ap.get('frequency_mhz', ap.get('frequency', 2412))
            caps    = ap.get('capabilities', '')
            bw      = ap.get('channel_bandwidth_mhz', '20')
            # Proper 5GHz channel calculation
            if freq >= 5000:
                channel = (freq - 5000) // 5
            else:
                channel = max(1, (freq - 2407) // 5)
            band    = '5G' if freq >= 5000 else '2.4G'
            enc     = 'WPA' if ('WPA' in caps or 'WEP' in caps) else 'OPEN'
            networks.append({
                'ssid': ssid, 'bssid': bssid, 'rssi': rssi,
                'channel': channel, 'enc': enc, 'band': band,
                'bandwidth': bw, 'source': 'android'
            })
        log.info(f"termux-wifi-scaninfo: found {len(networks)} networks")
    except FileNotFoundError:
        log.warning("termux-wifi-scaninfo not found — install: pkg install termux-api")
    except Exception as e:
        log.warning(f"Android scan error: {e}")
    return networks

def scan_android_ble():
    """Use termux-bluetooth-scaninfo for BLE on Android (requires Termux:API)."""
    devices = []
    try:
        import json as _json
        result = subprocess.run(
            ['termux-bluetooth-scaninfo'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0 or not result.stdout.strip():
            return devices
        data = _json.loads(result.stdout)
        for dev in data:
            devices.append({
                'type': 'ble',
                'mac':  dev.get('address', ''),
                'name': dev.get('name', ''),
                'rssi': dev.get('rssi', -99),
                'source': 'android'
            })
        log.info(f"termux-bluetooth-scaninfo: found {len(devices)} devices")
    except FileNotFoundError:
        log.warning("termux-bluetooth-scaninfo not found — install: pkg install termux-api")
    except Exception as e:
        log.warning(f"Android BLE scan error: {e}")
    return devices

def is_android():
    """Detect Android/Termux environment."""
    return os.path.exists('/data/data/com.termux') or 'ANDROID_ROOT' in os.environ

def native_scan():
    """Run the OS-appropriate WiFi scan, return list of network dicts."""
    if is_android():
        return scan_android()
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
            'type':     'wardrive',
            'bssid':    n.get('bssid', ''),
            'ssid':     n.get('ssid', ''),
            'rssi':     n.get('rssi', -80),
            'ch':       n.get('ch', n.get('channel', 0)),  # Android uses 'channel'
            'channel':  n.get('channel', n.get('ch', 0)),
            'enc':      n.get('enc', True),
            'band':     n.get('band', ''),
            'vendor':   n.get('vendor', ''),
            'source':   n.get('source', 'native'),
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
            # ESP32-S3 native USB CDC (T-Deck Plus, T-Beam Supreme)
            glob.glob('/dev/cu.usbmodem*') +
            glob.glob('/dev/tty.usbmodem*') +
            # CP210x / CH340 USB-to-serial (older T-Beam, breakout boards)
            glob.glob('/dev/tty.usbserial*') +
            glob.glob('/dev/tty.SLAB_USBtoUART*') +
            glob.glob('/dev/tty.wchusbserial*') +
            glob.glob('/dev/cu.usbserial*') +
            # Espressif VID catch-all
            glob.glob('/dev/cu.JTAG*')
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
            # Open with explicit DTR/RTS - native USB CDC on ESP32-S3
            # silently drops TX data when DTR is not asserted
            s = serial.Serial()
            s.port     = port
            s.baudrate = SERIAL_BAUD
            s.dtr      = True
            s.rts      = True
            s.timeout  = 2
            s.open()
            # Give OS + ESP32-S3 CDC driver time to register state change
            time.sleep(0.15)
            # Drain any boot/ready garbage so our ping sees a clean response
            s.reset_input_buffer()
            # Now send the ping
            s.write(b'{"cmd":"ping"}\n')
            time.sleep(0.5)
            response = s.read(s.in_waiting or 1)
            if response:
                log.info(f"T-Deck found on {port}")
                # CRITICAL: Do NOT close - keeping DTR high continuously prevents
                # the T-Deck from thinking the host disconnected. Return the
                # live connection object so _run_serial_mode reuses it.
                return (port, s)
            s.close()
        except Exception:
            try: s.close()
            except: pass
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
    Started/stopped by Pisces Moon Bridge on demand.
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
        client.send({'type': 'status', 'bridge': 'Pisces Moon Bridge', 'version': '1.0'})

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

class PiscesMoonBridge:
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
            result = find_tbeam()
            if result:
                port, conn = result
                self.mode        = 'serial'
                self.serial_port = port
                self.serial_conn = conn   # reuse the already-open connection
                log.info(f"Mode: SERIAL RELAY via {port}")
                self._run_serial_mode()
                return
        except ImportError:
            log.info("pyserial not available - skipping T-Beam detection")

        # Fall back to native scan
        self.mode = 'native'
        log.info(f"Mode: NATIVE SCAN ({'Android' if is_android() else platform.system()})")
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

        elif cmd == 'scan_ble':
            # Native BLE scan (or relay to T-Deck if serial mode)
            if self.mode == 'serial' and self.serial_conn:
                # T-Deck wardrive already streams ble_seen events
                # Just turn on streaming if not already on
                self._serial_send({'cmd': 'wardrive_start'})
            else:
                threading.Thread(
                    target=self._do_ble_scan, daemon=True).start()

        elif cmd == 'scan_air':
            # Combined: do everything available - BLE + LAN + (T-Deck wardrive if active)
            threading.Thread(
                target=self._do_device_scan, daemon=True).start()
            if self.mode == 'serial' and self.serial_conn:
                self._serial_send({'cmd': 'wardrive_start'})
            else:
                threading.Thread(
                    target=self._do_ble_scan, daemon=True).start()

        elif cmd == 'packet_start':
            channel = msg.get('channel', None)
            if self.mode == 'serial' and self.serial_conn:
                # T-Deck is the packet source - enable promiscuous wardrive streaming
                self._serial_send({'cmd': 'wardrive_start'})
                self._tdeck_packet_streaming = True
                self.ws_server.broadcast({
                    'type': 'packet_status',
                    'state': 'capturing',
                    'source': 'tdeck',
                    'mode': 'promiscuous',
                    'message': 'T-Deck streaming WiFi + BLE management frames',
                })
                log.info("Packet capture enabled via T-Deck wardrive streaming")
            elif self.packet_capture:
                # Native tcpdump fallback (Linux + monitor-capable hardware)
                threading.Thread(
                    target=self.packet_capture.start,
                    args=(channel,), daemon=True).start()
            else:
                client.send({
                    'type': 'packet_error',
                    'message': 'No packet source available. '
                               'Connect T-Deck or use Linux with monitor-mode hardware.',
                })

        elif cmd == 'packet_stop':
            if self.mode == 'serial' and self.serial_conn:
                self._tdeck_packet_streaming = False
                # Don't stop wardrive entirely if other apps using it - just mark this client done
                self.ws_server.broadcast({
                    'type': 'packet_status',
                    'state': 'stopped',
                    'source': 'tdeck',
                })
            elif self.packet_capture:
                threading.Thread(
                    target=self.packet_capture.stop, daemon=True).start()

        elif cmd == 'packet_status':
            if self.packet_capture:
                client.send(self.packet_capture.status)

        elif cmd == 'wardrive_log_open':
            try:
                result = wardrive_log.open_new()
                client.send({'type': 'wardrive_log_status', **result, 'open': True})
            except Exception as e:
                client.send({'type': 'wardrive_log_error', 'error': str(e)})

        elif cmd == 'wardrive_log_append':
            row = msg.get('row', {})
            ok = wardrive_log.append(row)
            if not ok:
                client.send({'type': 'wardrive_log_error', 'error': 'append failed'})

        elif cmd == 'wardrive_log_close':
            result = wardrive_log.close()
            client.send({'type': 'wardrive_log_status', 'open': False, **(result or {})})

        elif cmd == 'wardrive_log_status':
            client.send({'type': 'wardrive_log_status', **wardrive_log.status()})

        elif cmd == 'wardrive_list_sessions':
            sessions = list_wardrive_sessions()
            client.send({'type': 'wardrive_sessions', 'sessions': sessions})

        elif cmd == 'wardrive_read_session':
            name = msg.get('name', '')
            content = read_wardrive_session(name)
            if content is not None:
                client.send({
                    'type':    'wardrive_session_data',
                    'name':    name,
                    'content': content,
                })
            else:
                client.send({
                    'type':  'wardrive_log_error',
                    'error': 'session not found or unreadable',
                })

        # ── BLE LOG COMMANDS ──────────────────────────────────────
        elif cmd == 'ble_log_open':
            try:
                result = ble_log.open_new()
                client.send({'type': 'ble_log_status', **result, 'open': True})
            except Exception as e:
                client.send({'type': 'ble_log_error', 'error': str(e)})

        elif cmd == 'ble_log_append':
            row = msg.get('row', {})
            ok = ble_log.append(row)
            if not ok:
                client.send({'type': 'ble_log_error', 'error': 'append failed'})

        elif cmd == 'ble_log_close':
            result = ble_log.close()
            client.send({'type': 'ble_log_status', 'open': False, **(result or {})})

        elif cmd == 'ble_log_status':
            client.send({'type': 'ble_log_status', **ble_log.status()})

        # ── PROBE LOG COMMANDS ────────────────────────────────────
        elif cmd == 'probe_log_open':
            try:
                result = probe_log.open_new()
                client.send({'type': 'probe_log_status', **result, 'open': True})
            except Exception as e:
                client.send({'type': 'probe_log_error', 'error': str(e)})

        elif cmd == 'probe_log_append':
            row = msg.get('row', {})
            ok = probe_log.append(row)
            if not ok:
                client.send({'type': 'probe_log_error', 'error': 'append failed'})

        elif cmd == 'probe_log_close':
            result = probe_log.close()
            client.send({'type': 'probe_log_status', 'open': False, **(result or {})})

        elif cmd == 'probe_log_status':
            client.send({'type': 'probe_log_status', **probe_log.status()})

        # ── LORA LOG COMMANDS ─────────────────────────────────────
        elif cmd == 'lora_log_open':
            try:
                result = lora_log.open_new()
                client.send({'type': 'lora_log_status', **result, 'open': True})
            except Exception as e:
                client.send({'type': 'lora_log_error', 'error': str(e)})

        elif cmd == 'lora_log_append':
            row = msg.get('row', {})
            ok = lora_log.append(row)
            if not ok:
                client.send({'type': 'lora_log_error', 'error': 'append failed'})

        elif cmd == 'lora_log_close':
            result = lora_log.close()
            client.send({'type': 'lora_log_status', 'open': False, **(result or {})})

        elif cmd == 'lora_log_status':
            client.send({'type': 'lora_log_status', **lora_log.status()})

        # ── SESSION BUNDLE EXPORT ─────────────────────────────────
        elif cmd == 'session_bundle_export':
            session_id = msg.get('session_id')
            result = export_session_bundle(session_id)
            client.send({'type': 'session_bundle', **result})

        elif cmd == 'host_info':
            # Detailed host info for the About page
            try:
                import platform as plat_mod
                info = {
                    'type':        'host_info',
                    'system':      plat_mod.system(),
                    'release':     plat_mod.release(),
                    'version':     plat_mod.version(),
                    'machine':     plat_mod.machine(),
                    'processor':   plat_mod.processor(),
                    'node':        plat_mod.node(),
                    'python':      plat_mod.python_version(),
                }
                # macOS-specific: get the marketing version (e.g. "26.0" / "Tahoe")
                if plat_mod.system() == 'Darwin':
                    try:
                        sw_vers = subprocess.check_output(
                            ['sw_vers', '-productVersion'],
                            timeout=2, encoding='utf-8'
                        ).strip()
                        info['mac_version'] = sw_vers
                        major = int(sw_vers.split('.')[0])
                        codenames = {
                            26: 'Tahoe', 25: 'Tahoe',
                            15: 'Sequoia', 14: 'Sonoma',
                            13: 'Ventura', 12: 'Monterey',
                            11: 'Big Sur', 10: 'Catalina',
                        }
                        info['mac_name'] = codenames.get(major, '')
                    except Exception:
                        pass
                # Linux-specific: read /etc/os-release
                elif plat_mod.system() == 'Linux':
                    try:
                        with open('/etc/os-release') as f:
                            for line in f:
                                if line.startswith('PRETTY_NAME='):
                                    info['linux_pretty'] = line.split('=',1)[1].strip().strip('"')
                                    break
                    except Exception:
                        pass
                client.send(info)
            except Exception as e:
                client.send({'type': 'host_info', 'error': str(e)})

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
        """Relay JSON lines from T-Deck serial to all WebSocket clients."""
        import serial as pyserial
        buf = ''
        first_iteration = True
        while True:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    log.info(f"Connecting to T-Deck on {self.serial_port}...")
                    self.serial_conn = pyserial.Serial()
                    self.serial_conn.port     = self.serial_port
                    self.serial_conn.baudrate = SERIAL_BAUD
                    self.serial_conn.dtr      = True
                    self.serial_conn.rts      = True
                    self.serial_conn.timeout  = SERIAL_TIMEOUT
                    self.serial_conn.open()
                    # Wait for ESP32-S3 to register DTR state, then drain stale buffer
                    time.sleep(0.2)
                    self.serial_conn.reset_input_buffer()
                    log.info("T-Deck connected")
                
                # On first connection, prod the T-Deck so it sends current status
                # and starts streaming wardrive events immediately. This guarantees
                # we get data even if we missed the initial 'ready' announcement.
                if first_iteration:
                    first_iteration = False
                    log.info("Requesting T-Deck status + wardrive stream...")
                    self._serial_send({'cmd': 'status'})
                    time.sleep(0.1)
                    self._serial_send({'cmd': 'wardrive_start'})
                    self.ws_server.broadcast({
                        'type': 'bridge_status',
                        'mode': 'serial',
                        'serial_port': self.serial_port,
                    })
                    # Start GPS polling
                    self._last_gps_poll = 0

                # Poll GPS every 10 seconds
                now = time.time()
                if not hasattr(self, '_last_gps_poll'):
                    self._last_gps_poll = 0
                if now - self._last_gps_poll > 10:
                    self._last_gps_poll = now
                    try:
                        self._serial_send({'cmd': 'gps'})
                    except Exception:
                        pass

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
                                # Visibility logging - so you can see data flowing
                                mtype = m.get('type', '')
                                if mtype == 'wardrive':
                                    log.info(f"📡 WiFi: {m.get('ssid','(hidden)')} [{m.get('bssid','?')}] {m.get('rssi','?')}dBm ch{m.get('ch','?')}")
                                elif mtype == 'ble':
                                    log.info(f"📶 BLE:  {m.get('name','(unnamed)')} [{m.get('mac','?')}] {m.get('rssi','?')}dBm")
                                elif mtype == 'probe':
                                    log.info(f"🔍 PROBE: {m.get('mac','?')} → '{m.get('ssid','?')}' {m.get('rssi','?')}dBm")
                                elif mtype == 'mesh_link':
                                    log.info(f"📻 LoRa: {m.get('node_from','?')}→{m.get('node_to','?')} {m.get('rssi','?')}dBm SNR={m.get('snr','?')}")
                                elif mtype == 'packet':
                                    log.info(f"📦 PKT:  {m.get('frame_type','?')} src={m.get('src','?')} ch{m.get('channel','?')}")
                                elif mtype == 'GPS_FIX':
                                    log.info(f"🛰  GPS:  {m.get('lat','?'):.6f}, {m.get('lon','?'):.6f} sats={m.get('sats','?')}")
                                elif mtype == 'wardrive_status':
                                    log.info(f"⚡ WD status: active={m.get('active')} count={m.get('count')} ble={m.get('ble',0)}")
                                elif mtype == 'bridge_status':
                                    log.info(f"🔗 Bridge status: {m.get('device_os','')} v{m.get('version','')} uptime={m.get('uptime_s',0)}s")
                                # Cache wardrive networks
                                if mtype == 'wardrive':
                                    bssid = m.get('bssid', '')
                                    self._scan_cache = [
                                        n for n in self._scan_cache
                                        if n.get('bssid') != bssid
                                    ]
                                    self._scan_cache.append(m)
                    except json.JSONDecodeError:
                        log.debug(f"Serial non-JSON: {line[:60]}")

            except Exception as e:
                import traceback
                log.warning(f"Serial error: {e} - reconnecting in 5s")
                log.warning(f"Serial traceback:\n{traceback.format_exc()}")
                if self.serial_conn:
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None
                self.ws_server.broadcast({'type': 'bridge_status', 'mode': 'serial',
                                          'error': 'T-Deck disconnected, reconnecting...'})
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

    def _do_ble_scan(self):
        """
        Native BLE scan using OS Bluetooth radio.
        macOS: Swift CoreBluetooth snippet (same pattern as CoreWLAN)
        Linux: bluetoothctl scan
        Windows: not yet supported
        Each discovered device broadcast as {type:'ble', mac, name, rssi, vendor}
        """
        os_name = platform.system()
        log.info(f"Running native BLE scan on {os_name}...")
        self.ws_server.broadcast({'type': 'scan_start', 'source': 'ble'})

        try:
            if os_name == 'Darwin':
                self._do_ble_scan_macos()
            elif os_name == 'Linux':
                self._do_ble_scan_linux()
            else:
                log.warning(f"BLE scan not supported on {os_name}")
        except Exception as e:
            log.error(f"BLE scan failed: {e}")
        finally:
            self.ws_server.broadcast({'type': 'scan_complete', 'source': 'ble'})

    def _do_ble_scan_macos(self):
        """Use Swift CoreBluetooth to scan BLE devices on macOS."""
        # Swift CBCentralManager runs an event loop, scans for ~8 seconds,
        # prints each discovered peripheral as MAC<TAB>NAME<TAB>RSSI
        swift_script = r"""
import CoreBluetooth
import Foundation

class BleScanner: NSObject, CBCentralManagerDelegate {
    var central: CBCentralManager!
    var seen: Set<String> = []
    func start() {
        central = CBCentralManager(delegate: self, queue: nil)
    }
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn {
            central.scanForPeripherals(withServices: nil,
                options: [CBCentralManagerScanOptionAllowDuplicatesKey: false])
        }
    }
    func centralManager(_ central: CBCentralManager,
                        didDiscover peripheral: CBPeripheral,
                        advertisementData: [String : Any],
                        rssi RSSI: NSNumber) {
        let id = peripheral.identifier.uuidString
        if seen.contains(id) { return }
        seen.insert(id)
        let name = peripheral.name ??
                   (advertisementData[CBAdvertisementDataLocalNameKey] as? String) ?? ""
        let mfg = advertisementData[CBAdvertisementDataManufacturerDataKey] as? Data
        var mfgHex = ""
        if let m = mfg, m.count >= 2 {
            mfgHex = String(format: "%02X%02X", m[1], m[0])
        }
        print("\(id)\t\(name)\t\(RSSI)\t\(mfgHex)")
        fflush(stdout)
    }
}
let s = BleScanner()
s.start()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 8))
"""

        try:
            result = subprocess.run(
                ['/usr/bin/swift', '-'],
                input=swift_script,
                capture_output=True,
                text=True,
                timeout=30
            )
            log.info(f"BLE Swift rc={result.returncode} stderr={repr(result.stderr[:200])}")
            count = 0
            for line in result.stdout.strip().splitlines():
                parts = line.split('	')
                if len(parts) < 3:
                    continue
                try:
                    uuid_str = parts[0]
                    name     = parts[1]
                    rssi     = int(parts[2])
                    mfg_hex  = parts[3] if len(parts) > 3 else ''
                    # Apple devices have manufacturer code 004C (Apple Inc.)
                    vendor = ble_mfg_lookup(mfg_hex) if mfg_hex else ''
                    # Auto-log if BLE log is open
                    if ble_log.status().get('open'):
                        ble_log.append({
                            'mac': uuid_str.upper(), 'name': name,
                            'rssi': rssi, 'vendor': vendor,
                            'mfg_data': mfg_hex, 'source': 'native',
                        })
                    self.ws_server.broadcast({
                        'type':   'ble',
                        'mac':    uuid_str.upper(),
                        'name':   name or '(unnamed)',
                        'rssi':   rssi,
                        'vendor': vendor,
                        'mfg_data': mfg_hex,
                        'source': 'native',
                    })
                    count += 1
                except (ValueError, IndexError):
                    continue
            log.info(f"BLE scan: found {count} devices")
        except subprocess.TimeoutExpired:
            log.warning("BLE Swift scan timed out")
        except Exception as e:
            log.warning(f"BLE Swift scan exception: {e}")

    def _do_ble_scan_linux(self):
        """Use bluetoothctl on Linux."""
        try:
            # Start scan
            subprocess.run(['bluetoothctl', '--timeout', '8', 'scan', 'on'],
                           capture_output=True, timeout=10)
            # Get devices
            result = subprocess.run(['bluetoothctl', 'devices'],
                                    capture_output=True, text=True, timeout=5)
            count = 0
            for line in result.stdout.splitlines():
                # Format: "Device AA:BB:CC:DD:EE:FF DeviceName"
                parts = line.strip().split(' ', 2)
                if len(parts) >= 2 and parts[0] == 'Device':
                    mac  = parts[1]
                    name = parts[2] if len(parts) > 2 else '(unnamed)'
                    self.ws_server.broadcast({
                        'type':   'ble',
                        'mac':    mac,
                        'name':   name,
                        'rssi':   -80,  # bluetoothctl doesn't expose RSSI in this view
                        'vendor': oui_lookup(mac),
                        'source': 'native',
                    })
                    count += 1
            log.info(f"BLE scan (Linux): found {count} devices")
        except subprocess.TimeoutExpired:
            log.warning("bluetoothctl scan timed out")
        except FileNotFoundError:
            log.warning("bluetoothctl not installed")
        except Exception as e:
            log.warning(f"Linux BLE scan failed: {e}")

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
            # Synthetic BSSID when hardware doesn't expose it (Tahoe CoreWLAN)
            if not bssid:
                import hashlib
                bssid = 'SYN:' + hashlib.md5(f'{ssid}{ch}{rssi}'.encode()).hexdigest()[:11].upper()
            # Auto-log if wardrive log is open
            if wardrive_log.status().get('open'):
                wardrive_log.append({
                    'bssid': bssid, 'ssid': ssid, 'sec': enc_s,
                    'ch': ch, 'rssi': rssi, 'lat': lat, 'lng': lng,
                })
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
            # Also emit as packet event for the Packets tab when streaming
            if getattr(self, '_tdeck_packet_streaming', False):
                out.append({
                    'type':       'packet',
                    'frame_type': 'beacon',
                    'src':        bssid,
                    'dst':        'FF:FF:FF:FF:FF:FF',
                    'ssid':       ssid,
                    'channel':    ch,
                    'rssi':       rssi,
                    'vendor':     oui_lookup(bssid),
                    'source':     'tdeck',
                })

        # ── Streaming BLE events ───────────────────────────────────────
        elif event == 'ble_seen':
            mac  = msg.get('mac', '')
            name = msg.get('name', '')
            rssi = msg.get('rssi', -80)
            lat  = msg.get('lat', 0.0)
            lng  = msg.get('lng', 0.0)
            mfg  = msg.get('mfg_data', '') or msg.get('manufacturer_data', '')
            uuids = msg.get('service_uuids', '') or msg.get('uuids', '')
            addr_t = msg.get('addr_type', 'unknown')
            # Auto-log if BLE log is open
            if ble_log.status().get('open'):
                ble_log.append({
                    'mac': mac, 'name': name, 'rssi': rssi,
                    'vendor': oui_lookup(mac),
                    'lat': lat, 'lng': lng,
                    'mfg_data': mfg, 'service_uuids': uuids,
                    'addr_type': addr_t, 'source': 'tdeck',
                })
            out.append({
                'type':   'ble',
                'mac':    mac,
                'name':   name,
                'rssi':   rssi,
                'vendor': oui_lookup(mac),
                'lat':    lat,
                'lng':    lng,
                'mfg_data':      mfg,
                'service_uuids': uuids,
                'addr_type':     addr_t,
                'source': 'tdeck',
            })
            # Also emit as packet event when streaming
            if getattr(self, '_tdeck_packet_streaming', False):
                out.append({
                    'type':       'packet',
                    'frame_type': 'ble_adv',
                    'src':        mac,
                    'dst':        '',
                    'ssid':       name,
                    'channel':    0,
                    'rssi':       rssi,
                    'vendor':     oui_lookup(mac),
                    'source':     'tdeck',
                })

        # ── Streaming probe request events (Probe Intel) ───────────────
        elif event == 'probe_seen':
            client_mac = msg.get('mac', '') or msg.get('client', '')
            ssid_req   = msg.get('ssid', '') or msg.get('ssid_requested', '')
            rssi       = msg.get('rssi', -80)
            count      = msg.get('count', 1) or msg.get('sightings', 1)
            lat        = msg.get('lat', 0.0)
            lng        = msg.get('lng', 0.0)
            # Auto-log if probe log is open
            if probe_log.status().get('open'):
                probe_log.append({
                    'mac': client_mac, 'ssid': ssid_req, 'rssi': rssi,
                    'count': count, 'vendor': oui_lookup(client_mac),
                    'lat': lat, 'lng': lng, 'source': 'tdeck',
                })
            out.append({
                'type':   'probe',
                'mac':    client_mac,
                'ssid':   ssid_req,
                'rssi':   rssi,
                'count':  count,
                'vendor': oui_lookup(client_mac),
                'lat':    lat,
                'lng':    lng,
                'source': 'tdeck',
            })

        # ── Streaming LoRa mesh link events ────────────────────────────
        elif event == 'mesh_link' or event == 'lora_link':
            n_from = msg.get('from', '') or msg.get('node_from', '')
            n_to   = msg.get('to', '') or msg.get('node_to', '')
            rssi   = msg.get('rssi', -100)
            snr    = msg.get('snr', 0)
            freq   = msg.get('freq', 915.0) or msg.get('frequency', 915.0)
            sf     = msg.get('sf', 7) or msg.get('spreading_factor', 7)
            bw     = msg.get('bw', 125) or msg.get('bandwidth', 125)
            qual   = msg.get('quality', 0) or msg.get('link_quality', 0)
            # Auto-log if lora log is open
            if lora_log.status().get('open'):
                lora_log.append({
                    'node_from': n_from, 'node_to': n_to,
                    'rssi': rssi, 'snr': snr, 'freq': freq,
                    'sf': sf, 'bw': bw, 'quality': qual,
                    'lat_from': msg.get('lat_from', 0),
                    'lon_from': msg.get('lon_from', 0),
                    'lat_to':   msg.get('lat_to', 0),
                    'lon_to':   msg.get('lon_to', 0),
                })
            out.append({
                'type':       'mesh_link',
                'node_from':  n_from,
                'node_to':    n_to,
                'rssi':       rssi,
                'snr':        snr,
                'frequency':  freq,
                'sf':         sf,
                'bandwidth':  bw,
                'quality':    qual,
                'source':     'tdeck',
            })

        # ── wifi_scan one-shot response ────────────────────────────────
        elif ok is True and 'data' in msg:
            data = msg['data']
            # wifi_scan returns data.networks[] as a JSON array
            # status returns data.wardrive.networks as an integer count
            # Only iterate if it's actually a list
            if 'networks' in data and isinstance(data['networks'], list):
                networks = data['networks']
                for net in networks:
                    bssid  = net.get('bssid', '')
                    ssid_n = net.get('ssid', '')
                    ch_n   = net.get('channel', 0)
                    rssi_n = net.get('rssi', -80)
                    if not bssid:
                        import hashlib
                        bssid = 'SYN:' + hashlib.md5(f'{ssid_n}{ch_n}{rssi_n}'.encode()).hexdigest()[:11].upper()
                    enc_s  = net.get('enc', 'WPA')
                    out.append({
                        'type':   'wardrive',
                        'ssid':   ssid_n,
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
            # status response (has wardrive/wifi/gps nested objects)
            elif 'wardrive' in data and isinstance(data['wardrive'], dict):
                wd = data['wardrive']
                out.append({
                    'type':   'wardrive_status',
                    'active': wd.get('active', False),
                    'count':  wd.get('networks', 0),
                    'ble':    wd.get('ble', 0),
                    'logfile':wd.get('logfile', ''),
                    'source': 'tdeck',
                })
                # Also surface platform info
                out.append({
                    'type':     'bridge_status',
                    'mode':     'serial',
                    'platform': 'T-Deck',
                    'device_os':data.get('os', 'Pisces Moon'),
                    'version':  data.get('version', ''),
                    'uptime_s': data.get('uptime_s', 0),
                })

            # ping / status responses (top-level pong or os)
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
            # gps command response
            elif 'valid' in data:
                if data.get('valid') and data.get('lat'):
                    out.append({
                        'type':   'GPS_FIX',
                        'lat':    data.get('lat', 0),
                        'lon':    data.get('lng', data.get('lon', 0)),
                        'alt_m':  data.get('alt_m', 0),
                        'alt_ft': data.get('alt_ft', 0),
                        'sats':   data.get('sats', 0),
                        'speed':  data.get('speed_mph', 0),
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
    log.info("Pisces Moon Bridge v1.2")
    log.info("Pisces Moon OS / Fluid Fortune / fluidfortune.com")
    log.info(f"Platform: {platform.system()} {platform.release()}")
    log.info(f"WebSocket: ws://{WS_HOST}:{WS_PORT}")
    log.info("=" * 60)

    bridge = PiscesMoonBridge()
    try:
        bridge.start()  # blocks in native or serial loop
    except KeyboardInterrupt:
        log.info("Bridge stopped.")
