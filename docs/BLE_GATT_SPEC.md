<!--
  Pisces Moon OS — BLE_GATT_SPEC.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON BLE GATT SERVICE SPECIFICATION

**Version:** 1.0
**Date:** April 2026
**Status:** Draft — for T-Beam firmware implementation

---

## OVERVIEW

This document defines the Bluetooth Low Energy GATT service that a T-Beam (or any Pisces Moon edge node) must expose to be compatible with the Pisces Moondroid APK or any Web Bluetooth-enabled Pisces Moon HTML app.

The service is intentionally minimal: one data stream out, one command stream in, one status stream out. All payloads are JSON strings encoded as UTF-8 bytes.

---

## SERVICE UUID

```
8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a
```

This is a custom 128-bit UUID, randomly generated for Pisces Moon. Don't change it — every Pisces Moon HTML app filters for this UUID specifically when scanning for devices.

---

## CHARACTERISTICS

### 1. DATA characteristic (T-Beam → Tablet)

```
UUID:        8b5e0002-7c34-4a91-bd5c-1a2e9d6f8c4a
Properties:  NOTIFY (required), READ (optional)
Format:      UTF-8 encoded JSON
Max size:    512 bytes per notification
```

**Purpose:** Streams data from the T-Beam to the tablet. Wifi scan results, BLE observations, GPS positions, environmental sensor readings, packet metadata — everything that the USB serial protocol currently emits goes through this characteristic instead.

**Format:** Each notification is a single JSON object terminated implicitly by the BLE packet boundary. The tablet receives one complete JSON object per notification.

**Example payloads:**

```json
{"type":"wifi_scan","ssid":"NETGEAR-23","bssid":"a4:2b:b0:cf:d3:9a","rssi":-67,"channel":6,"security":"WPA2","timestamp":1714342890}
```

```json
{"type":"ble_observation","mac":"4c:8d:55:fa:11:23","name":"AirPods","rssi":-45,"manufacturer":"Apple","timestamp":1714342891}
```

```json
{"type":"gps","lat":34.0617,"lon":-118.2380,"alt":89,"hdop":1.2,"sats":11,"timestamp":1714342892}
```

```json
{"type":"env","temp_c":22.4,"humidity_pct":58,"pressure_hpa":1013.2,"timestamp":1714342893}
```

If a payload would exceed 512 bytes, split it across multiple notifications, each carrying a complete JSON object. Don't split JSON across notifications — that creates parsing nightmares on the receiving end.

### 2. COMMAND characteristic (Tablet → T-Beam)

```
UUID:        8b5e0003-7c34-4a91-bd5c-1a2e9d6f8c4a
Properties:  WRITE (required), WRITE_WITHOUT_RESPONSE (optional)
Format:      UTF-8 encoded JSON
Max size:    512 bytes per write
```

**Purpose:** Lets the tablet send commands to the T-Beam. Start/stop scanning, change channels, set GPS reporting interval, request a one-time sensor reading, etc.

**Example commands:**

```json
{"cmd":"wifi_scan","params":{"channels":[1,6,11],"duration_sec":10}}
```

```json
{"cmd":"ble_scan","params":{"active":true,"duration_sec":30}}
```

```json
{"cmd":"set_gps_interval","params":{"seconds":5}}
```

```json
{"cmd":"stop_all"}
```

The T-Beam should respond to commands by emitting a status update on the STATUS characteristic, then continuing to emit data on the DATA characteristic as the command executes.

### 3. STATUS characteristic (T-Beam → Tablet)

```
UUID:        8b5e0004-7c34-4a91-bd5c-1a2e9d6f8c4a
Properties:  NOTIFY (recommended), READ (recommended)
Format:      UTF-8 encoded JSON
Max size:    512 bytes
```

**Purpose:** Provides device-level status separate from streaming data. Battery level, current operation mode, errors, command acknowledgments.

**Example status payloads:**

```json
{"battery_pct":78,"mode":"idle","gps_fix":true,"sat_count":11,"temp_c":34.2}
```

```json
{"mode":"wifi_scan","progress":0.4,"channel":6}
```

```json
{"error":"command_failed","cmd":"wifi_scan","reason":"radio_busy"}
```

```json
{"ack":"wifi_scan","started_at":1714342890}
```

---

## DEVICE NAMING

The T-Beam should advertise itself with a name beginning with one of these prefixes (the Web Bluetooth filter looks for these):

- `PiscesMoon-` (recommended, e.g. `PiscesMoon-A1`)
- `T-Beam-` (acceptable, e.g. `T-Beam-Eric`)

Including a unique suffix (last 4 hex digits of MAC, user-set name, etc.) helps users distinguish multiple T-Beams.

---

## ADVERTISING

The T-Beam should advertise:
- The Pisces Moon service UUID (`8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a`) in the advertising packet so Web Bluetooth filters can find it without a name match
- Its device name (must begin with one of the prefixes above)
- TX power level (helps tablet estimate distance/quality)

Recommended advertising interval: 100-250 ms while idle, 50-100 ms when actively scanning (faster reconnection if connection drops).

---

## CONNECTION PARAMETERS

Recommended values for the T-Beam to request from the tablet after connection:

```
Connection Interval: 15-30 ms     (good throughput, decent battery)
Slave Latency:        0           (no skipping for low latency)
Supervision Timeout:  4000 ms     (4 seconds)
MTU:                  Negotiate to 247 or higher
```

After MTU negotiation, you can send up to (MTU - 3) bytes per notification. With MTU 247 that's 244 bytes per notification, which is enough for most JSON payloads.

For large MTU support, request 512 byte MTU. Modern Android and Chromium support this.

---

## EXAMPLE FIRMWARE STRUCTURE

Pseudocode for the T-Beam side (Arduino-style):

```cpp
// Service UUIDs
#define PM_SERVICE_UUID      "8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a"
#define PM_DATA_CHAR_UUID    "8b5e0002-7c34-4a91-bd5c-1a2e9d6f8c4a"
#define PM_COMMAND_CHAR_UUID "8b5e0003-7c34-4a91-bd5c-1a2e9d6f8c4a"
#define PM_STATUS_CHAR_UUID  "8b5e0004-7c34-4a91-bd5c-1a2e9d6f8c4a"

BLEServer*         pServer;
BLECharacteristic* pDataChar;
BLECharacteristic* pCommandChar;
BLECharacteristic* pStatusChar;

void setup() {
    BLEDevice::init("PiscesMoon-A1");
    pServer = BLEDevice::createServer();

    BLEService* pService = pServer->createService(PM_SERVICE_UUID);

    pDataChar = pService->createCharacteristic(
        PM_DATA_CHAR_UUID,
        BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ
    );
    pDataChar->addDescriptor(new BLE2902());

    pCommandChar = pService->createCharacteristic(
        PM_COMMAND_CHAR_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    pCommandChar->setCallbacks(new CommandCallbacks());

    pStatusChar = pService->createCharacteristic(
        PM_STATUS_CHAR_UUID,
        BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ
    );
    pStatusChar->addDescriptor(new BLE2902());

    pService->start();
    pServer->getAdvertising()->addServiceUUID(PM_SERVICE_UUID);
    pServer->getAdvertising()->start();
}

// To send data to the tablet:
void emitData(const String& jsonPayload) {
    pDataChar->setValue(jsonPayload.c_str());
    pDataChar->notify();
}

// Command handler — called when tablet writes to command char
class CommandCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* c) {
        std::string cmd = c->getValue();
        // Parse JSON, dispatch to handler, send ack via status char
        handleCommand(cmd);
    }
};
```

---

## COMPATIBILITY NOTES

### Web Bluetooth requirements

- Must use HTTPS or be a local file (file:// or app://). Not http:// over network.
- User must explicitly tap a "Connect" button — Web Bluetooth requires a user gesture for the pairing dialog.
- iOS Safari does not support Web Bluetooth. iPad users via Safari cannot use this transport.
- Android Chrome and Chromium-based WebView fully support it.

### Bandwidth realities

Practical sustained throughput over BLE in this configuration is around 10-50 KB/s depending on connection parameters. That's plenty for:
- Wifi scan results (one entry per notification)
- BLE observations
- GPS positions every few seconds
- Environmental sensor readings
- Command/control traffic

It's NOT enough for:
- Raw packet capture streaming
- RF spectrum waterfall display
- Full pcap file transfers

For high-bandwidth use cases, fall back to USB serial via the edge bridge architecture.

### Power considerations

BLE notifications are cheap on the T-Beam side (microwatt-class). The bigger power cost is the radio scanning (wifi/BLE observation modes). Idle BLE connection holding pulls maybe 1-3 mA on the ESP32-S3.

---

## VERSIONING

This spec is version 1.0. Future versions may add:
- Additional characteristics for specific data types (separate channels for wifi/ble/gps)
- A "config" characteristic for persistent device settings
- A "log" characteristic for debug output
- A "fw_update" characteristic for OTA updates

The service UUID stays the same across minor versions. Major version changes (breaking protocol changes) get a new service UUID.

---

## TESTING

To test the spec without writing firmware, you can:

1. **Use nRF Connect on Android** — emulate the GATT server, manually push test JSON payloads, verify the Pisces Moon HTML app receives them correctly
2. **Use a second ESP32** — write a stub firmware that just emits canned wifi_scan payloads on a timer
3. **Use bleak (Python BLE library)** on a Linux laptop — emulate the GATT server in Python for rapid iteration

---

*Pisces Moon BLE Spec v1.0 — Eric Becker / Fluid Fortune / 2026*
*Service UUID: 8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a — registered to FluidFortune*
