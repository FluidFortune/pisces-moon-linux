# Pisces Moon T-Deck Firmware Patch — True Promiscuous Capture

This patch upgrades the T-Deck (or T-Beam, or any ESP32-S3) wardrive
firmware from active scanning to true 802.11 promiscuous monitor mode.

## Files

- `pm_promiscuous.h` — drop-in module providing the capture engine.

## Why

The current firmware uses `WiFi.scanNetworks()`, which sends probe
requests and waits for AP responses. This produces:
- One snapshot per ~4 seconds
- Only beacons/probe-responses (no probe requests, deauth, association)
- No client device visibility (only APs)

True promiscuous mode reveals:
- Every WiFi management frame in the air
- Probe requests from phones/laptops nearby (with the SSIDs they
  remember — leaks travel patterns and visited networks)
- Deauth/disassoc frames (signature of an active attack)
- Association choreography (which device just joined which AP)
- Continuous frame stream (10-100+ frames/sec in busy areas)

## Integration into tbeam_pisces.ino

1. Copy `pm_promiscuous.h` into your sketch folder.

2. At the top of `tbeam_pisces.ino`, after the other includes:
   ```cpp
   #include "pm_promiscuous.h"
   ```

3. Add a packet handler. Right above `setup()`:
   ```cpp
   void onCapturedPacket(const pm_pkt_info_t* pkt) {
       StaticJsonDocument<512> doc;
       doc["event"]      = "pkt";
       doc["frame_type"] = pkt->subtype_str;
       doc["src"]        = pkt->src_mac_str;
       doc["dst"]        = pkt->dst_mac_str;
       doc["bssid"]      = pkt->bssid_str;
       doc["ssid"]       = pkt->ssid;
       doc["channel"]    = pkt->channel;
       doc["rssi"]       = pkt->rssi;
       doc["seq"]        = pkt->seq_num;
       String out;
       serializeJson(doc, out);
       sendMsg(out);
   }
   ```

4. Add new commands to the bridge protocol handler (where you parse
   `wardrive_start` etc.):
   ```cpp
   } else if (cmd == "promiscuous_start") {
       pm_promiscuous_begin(onCapturedPacket);
       sendOk("promiscuous capture started");

   } else if (cmd == "promiscuous_stop") {
       pm_promiscuous_end();
       sendOk("promiscuous capture stopped");

   } else if (cmd == "promiscuous_lock") {
       int ch = doc["channel"] | 1;
       pm_promiscuous_lock_channel(ch);
       sendOk("locked to channel " + String(ch));

   } else if (cmd == "promiscuous_filter") {
       // Subtype mask: which management subtypes to capture
       uint32_t mask = doc["mask"] | 0xFFFF;
       pm_promiscuous_set_subtype_mask(mask);
       sendOk("filter mask updated");
   }
   ```

5. In `loop()`, add the tick:
   ```cpp
   void loop() {
       // existing loop code...
       pm_promiscuous_tick();  // advances channel hop
   }
   ```

## Bridge integration (already done)

The `pm_bridge.py` `_translate_tdeck` already accepts events with type
`packet` / `pkt`. When the firmware emits the new `pkt` events, they
flow through to:
- Silas Creek Parkway → Packets tab (live frame stream)
- Watchtower → tracker/persistence/anomaly classification
- Probe Intel → SSID probing analysis

## Bandwidth considerations

In a busy RF environment (urban / office) you may see 100+ frames/sec.
The serial link runs at 921600 baud (~95 KB/s). Each JSON frame is
~150-300 bytes, so 100 frames/sec = ~30 KB/s — comfortable headroom.

If serial saturates, set a stricter filter mask:
```cpp
// Only deauth, beacons, probe requests
pm_promiscuous_set_subtype_mask((1<<4) | (1<<8) | (1<<12));
```

## What you get

| Use case                | Before (scan)    | After (promisc) |
|-------------------------|------------------|-----------------|
| Find APs                | ✓ every 4s       | ✓ continuous    |
| Find client devices     | ✗                | ✓ via probe-req |
| Detect deauth attacks   | ✗                | ✓ live          |
| See association events  | ✗                | ✓ live          |
| Track probe-requests    | ✗                | ✓ full SSIDs    |
| Build device timelines  | partial          | ✓ continuous    |

## Hardware compatibility

| Device              | Promiscuous support     |
|---------------------|-------------------------|
| T-Deck / T-Deck Plus| ✓ (ESP32-S3)            |
| T-Beam              | ✓ (ESP32 / ESP32-S3)    |
| T-Beam Supreme      | ✓ (ESP32-S3)            |
| M5 Cardputer        | ✓ (ESP32-S3)            |
| ESP32 DevKit        | ✓                       |
| ESP32-C3            | ✓ (limited subtypes)    |
| ESP8266             | ✗ (no callback support) |
