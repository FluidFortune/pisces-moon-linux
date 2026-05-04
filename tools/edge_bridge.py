#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# Pisces Moon OS — edge_bridge.py
# Copyright (C) 2026 Eric Becker / Fluid Fortune
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# See LICENSE file for full text. Commercial licenses available.
# Contact Eric Becker / Fluid Fortune (fluidfortune.com).
# ═══════════════════════════════════════════════════════════════════════
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
