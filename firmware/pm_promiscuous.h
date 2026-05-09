/*
 * Pisces Moon OS - pm_promiscuous.h
 *
 * True 802.11 promiscuous mode capture for ESP32 / ESP32-S3 devices.
 * Add this to the T-Deck, T-Beam, or headless ESP32-S3 wardriver firmware
 * to get continuous packet capture instead of scan-cycle snapshots.
 *
 * Copyright (C) 2026 Eric Becker / Fluid Fortune
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * USAGE in your .ino:
 *
 *   #include "pm_promiscuous.h"
 *
 *   void onPacket(const pm_pkt_info_t* pkt) {
 *       // Stream pkt to bridge as JSON
 *       StaticJsonDocument<512> doc;
 *       doc["event"] = "pkt";
 *       doc["frame_type"] = pkt->subtype_str;
 *       doc["src"]  = pkt->src_mac_str;
 *       doc["dst"]  = pkt->dst_mac_str;
 *       doc["bssid"]= pkt->bssid_str;
 *       doc["ssid"] = pkt->ssid;
 *       doc["channel"] = pkt->channel;
 *       doc["rssi"] = pkt->rssi;
 *       String out;
 *       serializeJson(doc, out);
 *       sendMsg(out);
 *   }
 *
 *   void setup() {
 *       pm_promiscuous_begin(onPacket);
 *   }
 *
 *   void loop() {
 *       pm_promiscuous_tick();  // hops channels every CHANNEL_HOP_MS
 *   }
 *
 * To stop: pm_promiscuous_end();
 *
 * BANDWIDTH NOTE: in busy RF environments this can produce >100 packets/sec.
 * The bridge_app.cpp serial protocol uses 921600 baud which handles ~95kB/s -
 * enough headroom but you may want to filter (e.g. management frames only)
 * to reduce serial saturation.
 */

#pragma once

#include <Arduino.h>
#include <esp_wifi.h>
#include <esp_wifi_types.h>

// ── Configuration ─────────────────────────────────────────────
#define PM_CHANNEL_HOP_MS       250    // ms between channel hops
#define PM_CHANNEL_MIN          1
#define PM_CHANNEL_MAX          13     // 14 in JP, 11 in US (FCC)
#define PM_PKT_QUEUE_SIZE       32     // ring buffer size

// ── Frame subtype identifiers ─────────────────────────────────
typedef enum {
    PM_SUB_BEACON,
    PM_SUB_PROBE_REQ,
    PM_SUB_PROBE_RESP,
    PM_SUB_AUTH,
    PM_SUB_DEAUTH,
    PM_SUB_ASSOC_REQ,
    PM_SUB_ASSOC_RESP,
    PM_SUB_DISASSOC,
    PM_SUB_ACTION,
    PM_SUB_DATA,
    PM_SUB_OTHER,
} pm_subtype_t;

// ── Parsed packet info ────────────────────────────────────────
typedef struct {
    pm_subtype_t subtype;
    const char* subtype_str;
    char src_mac_str[18];
    char dst_mac_str[18];
    char bssid_str[18];
    char ssid[33];
    uint8_t channel;
    int8_t  rssi;
    uint16_t seq_num;
    uint32_t millis_at_capture;
} pm_pkt_info_t;

typedef void (*pm_pkt_callback_t)(const pm_pkt_info_t*);

// ── Internal state ────────────────────────────────────────────
static pm_pkt_callback_t _pm_user_cb = nullptr;
static volatile uint32_t _pm_last_hop = 0;
static volatile uint8_t  _pm_current_channel = 1;
static volatile bool     _pm_active = false;
static volatile uint32_t _pm_pkt_count = 0;
static volatile uint32_t _pm_pkt_dropped = 0;

// Filter mask - only capture management + selected subtypes by default.
// (Capturing all data frames would saturate serial in any active network.)
static uint32_t _pm_subtype_mask = 0xFFFF;  // all management frame subtypes

// ── Helpers ───────────────────────────────────────────────────
static inline void _pm_mac_to_str(const uint8_t* mac, char* out) {
    snprintf(out, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

static const char* _pm_subtype_to_str(uint8_t fctl_subtype, uint8_t fctl_type) {
    if (fctl_type == 0) {  // Management
        switch (fctl_subtype) {
            case 0x0: return "assoc-req";
            case 0x1: return "assoc-resp";
            case 0x2: return "reassoc-req";
            case 0x3: return "reassoc-resp";
            case 0x4: return "probe-req";
            case 0x5: return "probe-resp";
            case 0x8: return "beacon";
            case 0xA: return "disassoc";
            case 0xB: return "auth";
            case 0xC: return "deauth";
            case 0xD: return "action";
            default:  return "mgmt";
        }
    } else if (fctl_type == 1) {
        return "ctrl";
    } else if (fctl_type == 2) {
        return "data";
    }
    return "other";
}

// Extract SSID from beacon/probe-resp tagged parameters
static int _pm_extract_ssid(const uint8_t* payload, size_t payload_len, char* out) {
    // For beacon/probe-resp: first 12 bytes after MAC header are
    // timestamp(8) + beacon_interval(2) + capabilities(2)
    // For probe-req: tagged params start immediately after MAC header
    // Tag 0 = SSID
    size_t i = 0;
    while (i + 2 <= payload_len) {
        uint8_t tag = payload[i];
        uint8_t len = payload[i + 1];
        if (i + 2 + len > payload_len) break;
        if (tag == 0) {  // SSID
            int copy = len < 32 ? len : 32;
            memcpy(out, &payload[i + 2], copy);
            out[copy] = 0;
            return copy;
        }
        i += 2 + len;
    }
    out[0] = 0;
    return 0;
}

// ── Packet sniffer callback (runs in WiFi task context) ──────
static void IRAM_ATTR _pm_promiscuous_cb(void* buf, wifi_promiscuous_pkt_type_t type) {
    if (!_pm_active || !_pm_user_cb) return;
    if (type != WIFI_PKT_MGMT && type != WIFI_PKT_DATA) return;

    const wifi_promiscuous_pkt_t* pkt = (const wifi_promiscuous_pkt_t*)buf;
    const uint8_t* payload = pkt->payload;
    int len = pkt->rx_ctrl.sig_len;
    if (len < 24) return;  // smaller than minimum 802.11 header

    // 802.11 frame control field (bytes 0-1)
    uint8_t fctl0 = payload[0];
    uint8_t fctl_type    = (fctl0 >> 2) & 0x3;
    uint8_t fctl_subtype = (fctl0 >> 4) & 0xF;

    // Only management frames by default
    if (fctl_type != 0) return;

    // Mask filter
    if (!(_pm_subtype_mask & (1 << fctl_subtype))) return;

    pm_pkt_info_t info;
    info.subtype_str = _pm_subtype_to_str(fctl_subtype, fctl_type);
    info.channel = pkt->rx_ctrl.channel;
    info.rssi = pkt->rx_ctrl.rssi;
    info.millis_at_capture = millis();

    // Subtype enum
    switch (fctl_subtype) {
        case 0x4: info.subtype = PM_SUB_PROBE_REQ;  break;
        case 0x5: info.subtype = PM_SUB_PROBE_RESP; break;
        case 0x8: info.subtype = PM_SUB_BEACON;     break;
        case 0xA: info.subtype = PM_SUB_DISASSOC;   break;
        case 0xB: info.subtype = PM_SUB_AUTH;       break;
        case 0xC: info.subtype = PM_SUB_DEAUTH;     break;
        case 0xD: info.subtype = PM_SUB_ACTION;     break;
        default:  info.subtype = PM_SUB_OTHER;      break;
    }

    // 802.11 MAC header layout (mgmt frames):
    // bytes 4-9   = receiver address (dst)
    // bytes 10-15 = transmitter address (src)
    // bytes 16-21 = BSSID
    // bytes 22-23 = sequence control
    _pm_mac_to_str(&payload[4],  info.dst_mac_str);
    _pm_mac_to_str(&payload[10], info.src_mac_str);
    _pm_mac_to_str(&payload[16], info.bssid_str);
    info.seq_num = (payload[22] | (payload[23] << 8)) >> 4;

    // SSID extraction depends on subtype:
    // - probe-req: tagged params start at offset 24
    // - beacon/probe-resp: 12 bytes of fixed fields, then tagged params at 36
    int ssid_offset;
    if (fctl_subtype == 0x4) {           // probe-req
        ssid_offset = 24;
    } else if (fctl_subtype == 0x8 ||    // beacon
               fctl_subtype == 0x5) {    // probe-resp
        ssid_offset = 36;
    } else {
        info.ssid[0] = 0;
        ssid_offset = -1;
    }

    if (ssid_offset > 0 && ssid_offset < len) {
        _pm_extract_ssid(&payload[ssid_offset], len - ssid_offset, info.ssid);
    } else {
        info.ssid[0] = 0;
    }

    _pm_pkt_count++;
    _pm_user_cb(&info);
}

// ── Public API ────────────────────────────────────────────────

/**
 * Begin promiscuous capture.
 * @param cb Callback invoked for each captured packet (runs in WiFi task!)
 * @return true on success
 */
inline bool pm_promiscuous_begin(pm_pkt_callback_t cb) {
    if (_pm_active) return false;
    _pm_user_cb = cb;

    // Tear down any existing WiFi state
    esp_wifi_set_promiscuous(false);
    esp_wifi_disconnect();
    esp_wifi_stop();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_storage(WIFI_STORAGE_RAM);
    esp_wifi_set_mode(WIFI_MODE_NULL);
    esp_wifi_start();

    // Set filter to receive only management frames by default
    wifi_promiscuous_filter_t filter;
    filter.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT;
    esp_wifi_set_promiscuous_filter(&filter);

    esp_wifi_set_promiscuous_rx_cb(&_pm_promiscuous_cb);
    esp_err_t err = esp_wifi_set_promiscuous(true);
    if (err != ESP_OK) {
        Serial.printf("[pm_promiscuous] enable failed: %d\n", err);
        return false;
    }

    _pm_active = true;
    _pm_current_channel = PM_CHANNEL_MIN;
    esp_wifi_set_channel(_pm_current_channel, WIFI_SECOND_CHAN_NONE);
    _pm_last_hop = millis();
    _pm_pkt_count = 0;
    _pm_pkt_dropped = 0;
    Serial.println("[pm_promiscuous] capture started");
    return true;
}

/**
 * Stop promiscuous capture.
 */
inline void pm_promiscuous_end() {
    if (!_pm_active) return;
    esp_wifi_set_promiscuous(false);
    _pm_active = false;
    _pm_user_cb = nullptr;
    Serial.printf("[pm_promiscuous] stopped (%lu pkts captured, %lu dropped)\n",
                  _pm_pkt_count, _pm_pkt_dropped);
}

/**
 * Call from loop() to advance channel hopping.
 * Hops every PM_CHANNEL_HOP_MS through PM_CHANNEL_MIN..PM_CHANNEL_MAX.
 */
inline void pm_promiscuous_tick() {
    if (!_pm_active) return;
    uint32_t now = millis();
    if (now - _pm_last_hop >= PM_CHANNEL_HOP_MS) {
        _pm_current_channel++;
        if (_pm_current_channel > PM_CHANNEL_MAX) _pm_current_channel = PM_CHANNEL_MIN;
        esp_wifi_set_channel(_pm_current_channel, WIFI_SECOND_CHAN_NONE);
        _pm_last_hop = now;
    }
}

/**
 * Lock to a single channel (disable hopping).
 */
inline void pm_promiscuous_lock_channel(uint8_t ch) {
    if (ch >= PM_CHANNEL_MIN && ch <= PM_CHANNEL_MAX) {
        _pm_current_channel = ch;
        esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE);
        _pm_last_hop = 0xFFFFFFFF;  // disable auto-hop
    }
}

/**
 * Resume channel hopping after being locked.
 */
inline void pm_promiscuous_unlock_channel() {
    _pm_last_hop = millis();
}

/**
 * Get capture stats.
 */
inline void pm_promiscuous_stats(uint32_t* captured, uint32_t* dropped, uint8_t* current_ch) {
    if (captured)   *captured = _pm_pkt_count;
    if (dropped)    *dropped  = _pm_pkt_dropped;
    if (current_ch) *current_ch = _pm_current_channel;
}

/**
 * Set subtype filter mask. Bit N = capture management subtype N.
 * Default 0xFFFF captures all management subtypes.
 *
 * Common useful masks:
 *   0x0100 = beacons only        (1<<8)
 *   0x0010 = probe requests only (1<<4)
 *   0x1010 = probe req + deauth  (1<<4 | 1<<12)
 */
inline void pm_promiscuous_set_subtype_mask(uint32_t mask) {
    _pm_subtype_mask = mask;
}

/**
 * Returns true if currently active.
 */
inline bool pm_promiscuous_is_active() { return _pm_active; }
