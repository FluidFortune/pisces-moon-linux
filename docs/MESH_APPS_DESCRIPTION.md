<!--
  Pisces Moon OS — MESH_APPS_DESCRIPTION.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON OS — MESH & COMMUNICATIONS SUITE
## Complete Application Descriptions
### Version 2.0 — May 2026

**Eric Becker / Fluid Fortune / fluidfortune.com**
*The Clark Beddows Protocol — Local Intelligence. No Gatekeepers. Your Machine, Your Rules.*

---

## OVERVIEW

The Pisces Moon Mesh and Communications Suite is a collection of six applications that together form a complete off-grid communications platform. Five are upgrades of existing v0.3/v0.4 applications. One — the SOS Beacon — is entirely new.

All six use `pm_transport.js` for hardware abstraction. They work identically on Linux, Android, Windows, and macOS. They share the `pm_viz.js` visualization library and `pm_utils.js` utility layer.

The suite is designed around a single principle: **communications that work when infrastructure doesn't.** No cell towers. No internet at the sender's end. No subscription that can be cancelled. No vendor whose continued operation determines whether you can reach the outside world.

---

## APP 1: MESH MESSENGER
**File:** `mesh_messenger.html`
**Version:** 2.0 (complete rewrite from v0.3)

### What It Is

A full-featured encrypted communications client for LoRa mesh networks. The T-Beam's SX1262 radio transmits and receives on 915MHz (US), propagating messages through a network of relay nodes without any cell or internet infrastructure. Messages hop automatically from node to node until they reach their destination or are broadcast to all nodes on the network.

This is the command and control surface for the mesh. Everything the mesh is doing — who's online, where they are, what the signal quality looks like between nodes, how messages are routing — is visible here in real time.

### Three-Tab Interface

**CHAT tab:**
The primary communications view. Identical in feel to any modern messaging app except the transport is LoRa radio rather than the internet. Messages are displayed in a bubble conversation layout: your outgoing messages on the right in gold, incoming messages on the left in cyan. Relayed messages (those that traveled through intermediate nodes) are displayed with dashed borders and a hop count indicator.

Each message shows: sender node ID, message text, timestamp, hop count, signal strength at final reception, and an encryption indicator. All messages are AES-256 encrypted in transit — the lock icon confirms this on every message.

The input area is a resizable textarea with Enter-to-send (Shift+Enter for newlines). The Send button is always visible and large enough for field use.

Five channel selectors at the bottom of the left panel: PM-DEFAULT, PM-ALPHA, PM-BETA, PM-SECURE, and BROADCAST. Each channel is logically isolated — messages on PM-SECURE are not visible to nodes monitoring PM-DEFAULT. All nodes monitor BROADCAST by default.

Direct messaging: click any node in the node list, then click "Direct Message" in the node detail panel. The chat view switches to a private conversation with that node. Direct messages still travel through the mesh (LoRa has no concept of private transmission) but are addressed to a specific node ID.

**TOPOLOGY tab:**
The mesh network visualized as an animated force-directed graph. Every node is a floating bubble. Edges between nodes represent LoRa links — the thickness of the edge reflects signal strength (thick green line = strong signal, thin red line = marginal), and the edge is dashed when the link is a multi-hop relay rather than direct.

Signal strength labels appear on every edge: the dBm value and hop count. Click any node to select it — the selected node glows and its detail panel updates on the right. Your own node is marked with a gold star. Relay nodes (those forwarding traffic they didn't originate) are marked with a hexagon symbol.

The topology updates in real time as nodes appear, disappear, or change signal quality. Nodes that haven't been heard from in 120 seconds fade and are marked offline.

Node detail shown on click: name/ID, status, signal strength, hop count, battery percentage, GPS coordinates (if GPS-equipped), environmental readings (temperature, humidity — from BME280 if present), message count, and last seen timestamp. A Direct Message button in the detail panel opens a private conversation with that node.

**ROUTING tab:**
A chronological log of every message routing event observed by the network. Each entry shows: originating node, destination, number of hops, the specific path through intermediate nodes (e.g., "pisces-1 → relay-4 → relay-7 → gateway-1"), final signal quality, and timestamp.

This is the diagnostic view — if messages aren't getting through, the routing log shows exactly where they're stopping. Useful for understanding mesh topology problems and identifying weak links that need a relay node added.

### Node List (left panel)

Every node currently on the mesh, sorted by signal strength. Each entry shows:
- Status indicator dot: green pulsing (online), yellow (relay only), grey (offline/stale)
- Node name/ID
- Signal strength in dBm, color-coded by quality
- Hop count to reach this node
- Battery percentage if reported
- Message count with this node

Clicking a node selects it and populates the detail panel. Nodes older than 2 minutes with no new traffic are marked stale.

### Channel Selector

Five channel buttons at the bottom of the left panel. The active channel is highlighted. Switching channels changes which messages are displayed in the chat view and which channel outgoing messages are sent on. The mesh messenger monitors all channels simultaneously — new messages on any channel appear with a notification indicator on the channel button.

### Session Persistence

Message history is saved to localStorage between sessions. Your node ID is persistent across sessions. The mesh network state rebuilds automatically from incoming traffic when you reconnect.

Session save (💾 button): exports nodes, recent messages, and routing log as JSON to `/sdcard/PiscesMoon/mesh_session_TIMESTAMP.json` on Android or a browser download on desktop.

### Heartbeat

The app announces your node to the mesh every 60 seconds while connected. Other nodes see you as active. The heartbeat payload includes your node ID and channel — no GPS or personal data is transmitted in heartbeats unless you explicitly configure it.

### Transport

Uses `pm_transport.js` auto-detection:
- Android APK: native USB bridge to T-Beam, then LoRa → mesh
- Linux: WebSocket edge bridge
- Web Bluetooth: direct BLE GATT to T-Beam (for Android without APK)

Hardware requirement: T-Beam with LoRa in mesh relay mode.

---

## APP 2: GPS NAVIGATOR
**File:** `gps_app.html`
**Version:** 2.0 (complete rewrite from v0.3)

### What It Is

A full field navigation application. GPS data streams from the T-Beam's MAX-M10S or L76K receiver. The app records tracks, manages waypoints, calculates distances and bearings, exports in standard GPX format, and displays position in multiple coordinate formats. Falls back to browser Geolocation API when no T-Beam is connected.

### Live Map

Leaflet.js map centered on your current position. A glowing green marker shows your current location, updating continuously as the T-Beam sends GPS fixes. When track recording is active, a green polyline draws behind you showing the path traveled. Waypoints appear as gold dot markers with popup labels.

Follow GPS mode (default on): the map recenters on your position with each GPS update. Toggle off to freely browse the map without it jumping back. The Follow toggle and a Center Map button are in the map controls overlay.

Click anywhere on the map to add a waypoint at that location — a confirmation prompt appears with the coordinates pre-filled, and you can name the waypoint before saving.

### Stats Bar

Six real-time fields spanning the full width above the map:
- **Latitude** — decimal degrees to 5 decimal places (~1.1 meter precision)
- **Longitude** — same
- **Altitude** — meters above sea level
- **Speed** — km/h, updated every GPS fix
- **Satellites** — count of satellites used in fix, color-coded (green ≥6, yellow ≥4, red <4)
- **HDOP** — horizontal dilution of precision, the GPS accuracy metric (lower = better)

### Coordinate Formats (right panel)

Your current position displayed in three formats simultaneously:
- **Decimal** — 36.57854, -118.29231 (standard, Google Maps compatible)
- **DMS** — 36°34'42.7"N 118°17'32.3"W (degrees/minutes/seconds, traditional navigation)
- **MGRS** — approximate Military Grid Reference System zone (full implementation requires a library, current version gives zone designation)

Current heading in degrees with compass point name (NNE, SW, etc.).

### Animated Compass

A 200×200 pixel canvas compass rose with a two-color heading needle. North is marked in red. Cardinal and ordinal points labeled. The needle points in the direction of current travel heading from the GPS. Heading degree value displayed numerically in the center. Updates on every GPS fix.

### Track Recording

Start/Stop toggle button. When recording, every GPS fix is appended to the track array with lat, lon, altitude, speed, heading, and timestamp. The polyline on the map extends in real time. Track point count displayed.

Track data persists to localStorage between sessions — if you close the app and reopen it, the existing track is still there and the polyline redraws on the map.

**GPX Export:** Generates a valid GPX 1.1 file with a track segment containing all recorded points. GPX is the standard format accepted by Garmin devices, Strava, Komoot, AllTrails, Google Maps, and essentially every mapping application. The export includes elevation, timestamp, and speed data per point.

### Waypoint Management

Add waypoints from current GPS position (button in left panel) or by clicking the map. Each waypoint stores name, coordinates, altitude, and timestamp. Waypoints persist to localStorage.

The waypoint list shows distance from current position to each waypoint, updated in real time as you move. Clicking a waypoint in the list centers the map on it and shows the distance and bearing from your current position.

Delete individual waypoints with the × button. Clear all waypoints with confirmation prompt.

### Distance Calculations

The distance panel (bottom of left column) shows:
- **Track distance** — total distance traveled since track started, calculated using the Haversine formula between consecutive track points
- **Distance to selected waypoint** — straight-line distance from current position to the selected waypoint, plus bearing in degrees and compass direction

### Visualization Charts (right panel)

- **Altitude profile sparkline** — 60-point history of altitude readings, showing elevation change over time
- **Speed history sparkline** — 60-point history of speed readings, showing pace changes
- **Satellite count bar chart** — visual representation of GPS satellite signal strength (mock visualization — real per-satellite SNR data requires NMEA GSV parsing)
- **HDOP gauge arc** — signal quality arc showing current HDOP value

### Fallback Mode

When no T-Beam is connected, the app attempts to use the browser's Geolocation API (`navigator.geolocation.watchPosition`). This provides position from the device's built-in GPS or network location. Accuracy varies by device. Track recording, waypoints, GPX export, and all visualizations work identically in fallback mode.

Hardware requirement: T-Beam GPS (preferred) or any GPS-equipped device via browser geolocation.

---

## APP 3: VOICE TERMINAL
**File:** `voice_terminal.html`
**Version:** 2.0 (complete rewrite from v0.3)

### What It Is

Half-duplex push-to-talk radio over LoRa mesh. The T-Beam encodes microphone audio using Codec2 (optimized for low-bandwidth links) and transmits it as LoRa packets. Receiving nodes decode and play back the audio. Range is identical to text mesh range — the audio transport uses the same LoRa radio as all other mesh traffic.

This is the equivalent of a handheld radio, but running over the same mesh infrastructure as all your other communications, without requiring dedicated radio hardware beyond the T-Beam you already have.

### The PTT Button

A large 160×160 pixel circular push-to-talk button dominates the center panel. Works with mouse click-and-hold or touch press-and-hold — designed for one-hand field operation.

**Press and hold:** Microphone activates, audio is captured and encoded, packets are transmitted to the mesh. The button glows red with a pulsing animation during transmission.

**Release:** Transmission stops, the mesh channel opens for incoming audio.

Two-second audio delay at the receiver end — LoRa transmission takes time. This is a feature, not a bug: it means transmissions don't collide with each other (only one node should transmit at a time on a given channel, enforced by protocol).

### Live Audio Waveform

A 300×80 canvas above the PTT button shows the audio waveform in real time during transmission. The time-domain signal drawn as a continuous line — you can see your voice being captured. When not transmitting, the canvas shows "Hold PTT to transmit" as a center label.

### VU Meter

A horizontal level bar below the PTT button shows microphone input level using the Web Audio API analyser. This lets you verify your microphone is active and your voice level is appropriate before transmitting.

### Channel Selector

Five channels: 1, 2, 3, 4, 5, SEC-A, SEC-B. Each channel is independent — teams operating in the same area can use different channels without hearing each other. Switching channels takes effect immediately.

### Codec Selector

Four options in a dropdown:
- **Codec2 2400bps** — optimal for LoRa, lowest bandwidth, most range. Codec2 was specifically designed for HF radio at very low bitrates. Audio quality is voice-intelligible but not music-quality. Recommended for LoRa mesh.
- **Codec2 3200bps** — slightly better quality, slightly more bandwidth
- **Opus 8kbps** — higher quality, requires better link quality
- **GSM 13kbps** — legacy codec, higher bandwidth requirement

Codec2 at 2400bps is the default and the right choice for LoRa mesh. At this bitrate, a one-second voice transmission is approximately 300 bytes — well within LoRa packet limits.

### Squelch Control

A range slider adjusting squelch threshold from -120dBm to -40dBm. Nodes below the squelch threshold are muted — background noise from distant weak nodes doesn't open the audio. Adjust based on your environment. Default -80dBm works for most deployments.

### Active Node List (left panel)

Mesh nodes currently online, with signal strength. Shows who's available for voice communication.

### Transmission Log (right panel)

Every transmission logged with: direction (TX/RX), from node, channel, duration in seconds, signal quality, codec used, and timestamp. Persistent for the session.

### Signal Quality Chart

A gauge arc showing received signal quality for the most recent transmission.

Hardware requirement: T-Beam with microphone (built-in or connected) for TX. Any T-Beam for RX. Codec2 encoding/decoding happens in T-Beam firmware — the HTML app handles the UI and control channel.

---

## APP 4: WIFI MANAGER
**File:** `wifi_app.html`
**Version:** 2.0 (complete rewrite from v0.3)

### What It Is

Network management for the T-Beam's WiFi radio. Scan nearby networks, connect to them, manage credentials, and monitor current connection quality.

### Network List (left panel)

Every detected WiFi network with a visual signal strength indicator — four-bar display identical to a phone's WiFi indicator, plus the exact dBm value color-coded by signal quality. Networks sorted by signal strength descending.

Each entry shows:
- Signal bars and dBm value
- SSID (network name), with "CONNECTED" indicator if currently connected
- Security type badge: OPEN (red), WEP (red), WPA (yellow), WPA2 (green), WPA3 (blue)
- Channel number
- Observation count (how many times seen in scans)

### Connection Management

Selecting an open network and clicking CONNECT sends the connection command to the T-Beam directly. For secured networks, enter the password in the right panel's password field before clicking CONNECT.

DISCONNECT: sends disconnection command to current network.

FORGET: removes saved credentials for the selected network from the T-Beam's flash storage.

RESCAN: triggers a new WiFi scan, updating the network list.

### Current Connection Detail

When connected, the top of the center panel shows a detailed status block:
- SSID of connected network
- Assigned IP address
- Gateway address
- DNS server address
- Current signal strength in dBm
- Channel number

This updates via WIFI_STATUS messages from the T-Beam.

### Signal History Sparkline

60-point history of signal strength on the currently selected network. Shows whether signal quality is stable, improving, or degrading. Useful for positioning decisions — move the device until the sparkline trends upward.

### Channel Utilization Chart

14-bar vertical chart showing how many networks are active on each of the 14 WiFi channels. Immediately shows channel congestion — if channels 1, 6, and 11 are crowded, you know which channels to avoid or which to connect to for best throughput.

### Security Distribution Donut

Proportion of nearby networks by security type: OPEN / WEP / WPA / WPA2 / WPA3. A snapshot of the security posture of the wireless environment. High OPEN or WEP counts are situational awareness data.

### Saved Networks (right panel)

List of networks with saved credentials stored on the T-Beam. One-click connect to any saved network.

Hardware requirement: T-Beam WiFi radio.

---

## APP 5: SSH CLIENT
**File:** `ssh_client.html`
**Version:** 2.0 (complete rewrite from v0.3)

### What It Is

A terminal emulator that provides SSH access to remote Linux systems through the edge bridge. Use it to SSH into Linux servers, mesh nodes, or any device on your network — no separate SSH app required.

### Terminal Display

A full-height dark terminal window with monospace font, proper line wrapping, and auto-scroll. Output text is color-coded:
- **White** — normal command output
- **Red** — stderr / error messages
- **Dim** — system messages from the bridge
- **Green** — command prompts (when the SSH server sends a prompt string)

The terminal is click-to-focus on desktop, always focused on mobile.

### Command Input Bar

At the bottom: a prompt label (shows `username@hostname $` when connected, `$` when not) and a text input field. Enter to send. Shift+Enter for literal newline.

**Arrow key history navigation:** Up arrow cycles through command history (last 100 commands, persisted to localStorage). Down arrow moves forward through history. The history is shared across sessions — commands from previous SSH sessions are accessible.

**Ctrl+C:** Sends SIGINT to the remote process. Works for interrupting long-running commands.

**Autocomplete:** Not yet implemented — future version.

### Saved Hosts (left panel)

Pre-configured connection shortcuts. Clicking any saved host auto-populates the connection form and triggers connection. Delete saved hosts with the × button.

**Pre-loaded entries:**
- Mesh Node (192.168.1.100, root, port 22)
- Router (192.168.1.1, root, port 22)

Add your own saved hosts using the New Connection form and clicking SAVE HOST.

### New Connection Form

- **Hostname or IP** — the target host
- **Username** — defaults to "root" (appropriate for embedded Linux targets)
- **Port** — defaults to 22
- **Password** — optional; key-based auth is handled by the bridge's SSH client

CONNECT: initiates the SSH connection through the bridge. The bridge's SSH client handles the actual SSH protocol — the HTML app sends the connection parameters and then streams stdin/stdout through the bridge.

### Session Tab Bar

Multiple SSH sessions shown as tabs at the top of the terminal area. Click + NEW to open a parallel session. Session switching is immediate — each tab maintains its own terminal history. Currently limited to the active session's output; background session output buffers but doesn't display until that tab is selected.

### How It Actually Works

The SSH client sends `CMD_SSH_CONNECT` to the bridge, which opens an SSH connection to the target using the system's ssh binary or paramiko (Python). All terminal I/O flows as `SSH_OUTPUT` / `SSH_STDERR` messages through the WebSocket or USB bridge. The HTML app is a terminal UI — it doesn't implement the SSH protocol itself.

This means key-based authentication, host key verification, and all other SSH security features work exactly as they would in a normal terminal — they're handled by the bridge's SSH implementation, not by the web app.

Hardware requirement: Edge bridge (edge_bridge.py) running on Linux, or Android native bridge. The T-Beam is the USB connection point but the SSH session itself goes over whatever network the bridge host is connected to.

---

## APP 6 (NEW): SOS BEACON
**File:** `sos_beacon.html`
**Version:** 1.0 (new application)

### What It Is

A dedicated emergency broadcast system. One large button activates an SOS that broadcasts GPS coordinates through the LoRa mesh network to a gateway node, which forwards the message as an SMS to SAR coordinators and emergency contacts. The system is bidirectional — replies from SAR coordinators route back through the mesh to the device.

No cell service required at the sender's location. No satellite subscription. No monthly fee. Works as long as at least one mesh node within LoRa range can reach an internet-connected gateway.

### Design Philosophy

This app was designed for use in worst-case conditions. The UI reflects this:

- **Large touch targets** — all interactive elements are oversized for use with cold, shaking, or injured hands
- **High contrast** — pure white text on near-black background, no subtle gradients
- **No small text** — minimum readable font sizes throughout
- **Double-tap confirmation** — prevents accidental SOS activation
- **Screen wake lock** — the display stays on during active SOS without user intervention
- **Persistent operation** — continues broadcasting if the user sets the device down and walks away

### The SOS Button

A 200×200 pixel circular button dominates the left panel. Red border, red text, red glow.

**First tap:** The button changes to yellow and shows "TAP AGAIN TO CONFIRM." A 3-second timer starts. If the second tap doesn't come within 3 seconds, the button resets. This prevents accidental activation from a device being jostled in a pack.

**Second tap within 3 seconds:** SOS activates. The button turns deep red with a pulsing glow animation. A ring animation expands outward from the button continuously while SOS is active. The button text changes to "SOS ACTIVE — BROADCASTING."

**On acknowledgment:** When a gateway confirms delivery, the button changes to green and shows "✓ RECEIVED — HELP IS COMING." The pulsing animation stops. The heartbeat continues but slows to every 5 minutes to conserve battery.

### Broadcast Behavior

- **Immediate:** First broadcast fires the moment SOS is activated
- **Interval:** Every 60 seconds thereafter
- **Channels:** Broadcasts on ALL five mesh channels simultaneously (PM-DEFAULT, PM-ALPHA, PM-BETA, PM-SECURE, BROADCAST)
- **Priority:** Messages are tagged EMERGENCY priority — gateway nodes process SOS messages before all other traffic
- **On ACK:** Interval slows to 5 minutes (conserves battery while still providing position updates to SAR)

### Countdown Display

Between the button and the status display: a countdown showing "NEXT BROADCAST IN Xs" that counts down from 60 (or 300 after acknowledgment). This lets the user know the system is working and when the next transmission will occur.

### GPS Display

Five GPS signal quality bars (like a phone's signal indicator) plus text showing fix quality: EXCELLENT, GOOD, FAIR, WEAK, or NO FIX with satellite count.

When fix is acquired:
- Coordinates displayed to 5 decimal places
- Altitude in meters
- HDOP value with quality label (IDEAL / EXCELLENT / GOOD / MODERATE / POOR)

The SOS message always includes the most recent GPS fix, even if the fix quality is poor. A weak GPS position is better than no position.

### Hop Path Visualization

Five circles in a row representing the message's journey:

```
YOU  →  RELAY1  →  RELAY2  →  GATEWAY  →  SMS
```

Each circle starts grey (unknown). As the mesh reports routing information:
- Your origin node is always green
- Relay nodes light up green as they're confirmed in the routing path
- The GATEWAY circle turns gold when a gateway is detected on the mesh
- The SMS circle shows ✓ when delivery to SMS is confirmed

This gives the user real-time feedback on whether their message is getting through and how many hops it's traveling.

### Status Panel

Six status rows below the GPS display:
- **GPS** — fix quality with signal bars
- **Coordinates** — lat/lon to 5 decimal places
- **Altitude** — meters
- **Accuracy** — HDOP value and quality label
- **Mesh** — ONLINE (green) or OFFLINE (red)
- **Gateway** — node ID and signal strength if gateway detected, "NOT FOUND" if not
- **Broadcasts** — count of broadcasts sent this session
- **Delivered** — delivery confirmation status

### Profile Setup (right panel, top)

Four fields the user fills in before deploying to the field:
- **Name** — their name, included in every SOS message
- **Emergency contact** — phone number to receive SMS alerts
- **SAR contact** — dedicated SAR/911 gateway number
- **Default situation** — pre-written description of their planned activity ("Hiking alone, Mt Whitney main trail, expected return 6pm")

The default situation description is included in every SOS message. It provides critical context even if the user cannot type a custom message during the emergency. Profile is saved to localStorage and persists between sessions.

### Inbound Replies (right panel, middle)

A dedicated section for messages coming back from SAR coordinators. Each reply shows:
- Sender (SAR coordinator, phone number, or node ID)
- Message text (large, readable font)
- Timestamp
- Hop count and signal strength if available

When a reply arrives, the device vibrates (if supported) and the reply section scrolls into view. The user does not need to navigate away from the main SOS screen to see replies — they appear in the same interface.

### Broadcast Log (right panel, bottom)

Timestamped log of every broadcast event:
- SOS ACTIVATED
- Broadcast #N sent on X channels
- SOS ACKNOWLEDGED by [node]
- REPLY RECEIVED from [sender]
- SOS CANCELLED by user

Color coded: green for successful events, yellow for warnings, red for errors.

### Last SOS Message (right panel, bottom)

The complete JSON of the most recent SOS broadcast, formatted for readability. Shows exactly what data was sent, including GPS coordinates, situation description, timestamp, and broadcast number. Useful for verifying the message content is correct before and during an emergency.

### Cancel

A "■ CANCEL SOS" button appears below the countdown when SOS is active. Requires a browser confirmation dialog before cancelling — not accidental. Sends a CANCEL message to the mesh so gateway nodes know the emergency is resolved. The button is visible but not prominent — the interface is designed to make cancellation deliberate.

### The SOS Message Sent to SAR

```
[PM-SOS] EMERGENCY

Person: Jane Smith
Situation: Broken ankle, cannot walk, solo hiker

GPS: 36.57854, -118.29231
Alt: 3847m
Accuracy: EXCELLENT

MAP: https://maps.google.com/?q=36.57854,-118.29231

Node: pisces-7a3b
Broadcast #3
Time: 2026-05-03T19:42:17Z

Reply to this number to contact the device.
Pisces Moon OS — mesh.fluidfortune.com
```

The MAP link opens directly to the coordinates in Google Maps on any smartphone. No app required on the SAR side. A standard SMS with everything needed to dispatch a rescue.

### Battery Behavior

In active SOS mode, the broadcast cycle consumes approximately 5mA average current (200ms transmit at ~100mA, sleep remainder of 60 seconds). A 3500mAh 18650 cell provides approximately 700 hours (29 days) at this duty cycle in theory. In practice, GPS continuous operation dominates — realistic battery life in SOS-only mode is 48-96 hours on a full cell.

After acknowledgment, the 5-minute heartbeat interval extends this further. A hiker who activates SOS and then focuses on survival does not need to worry about their device dying before rescue arrives.

---

## THE SMS GATEWAY

**File:** `SmsGateway.java`
**Platform:** Android APK

### What It Is

A Java service that runs inside the Pisces Moon Android APK alongside `MainActivity.java`. It acts as the bridge between the LoRa mesh and the SMS network. Any Android phone running the Pisces Moon APK and connected to a T-Beam (via USB-C OTG or Bluetooth) becomes a mesh-to-SMS gateway.

### What It Does

**Outbound (mesh → SMS):**
1. The SOS Beacon or Mesh Messenger sends a mesh message addressed to a phone number or tagged as SOS
2. The gateway intercepts this via the `PiscesSMS` JavaScript bridge
3. Formats the SOS message into the standardized SMS template
4. Sends to all configured SAR contacts via Android's `SmsManager`
5. Sends a mesh ACK back to the originating node confirming delivery

**Inbound (SMS → mesh):**
1. A `BroadcastReceiver` monitors incoming SMS
2. When an SMS arrives, it's formatted as a `SOS_REPLY` mesh message
3. Injected into the WebView via `PiscesAndroid._onData()`
4. Routed through the mesh back to the originating node
5. Appears in the SOS Beacon's reply panel

### JavaScript Bridge (`PiscesSMS`)

Exposed to all HTML apps in the WebView:

- `PiscesSMS.sendSOS(sosJson)` — sends SOS to all configured contacts
- `PiscesSMS.sendToPhone(number, from, text)` — sends a mesh message as SMS
- `PiscesSMS.setContacts(csv)` — configure SAR contact numbers
- `PiscesSMS.getContacts()` — retrieve configured contacts
- `PiscesSMS.setEnabled(bool)` — enable/disable gateway
- `PiscesSMS.sendTestSms(number)` — send a test message to verify gateway works
- `PiscesSMS.isAvailable()` — check if gateway service is running

### Permissions Required

Added to `AndroidManifest.xml`:
- `android.permission.SEND_SMS`
- `android.permission.RECEIVE_SMS`
- `android.permission.READ_SMS`

These are standard Android permissions. The user is prompted to grant them on first launch. The app explains why they're needed.

### No Twilio Required

The gateway uses the phone's native SMS capability — the same mechanism as the built-in Messages app. No Twilio account, no API key, no cloud dependency. If you have cell service on your phone, the gateway works.

For deployments where the gateway needs to receive SMS replies and forward them into the mesh, Twilio is useful because it provides a stable, publicly reachable webhook URL. But for basic SOS-out functionality, native Android SMS is all that's needed.

---

## DEPLOYMENT SCENARIOS

### Scenario 1: Day Hiker Personal Setup

Equipment:
- T-Beam S3 Supreme in pocket: $50
- Android phone (existing) with Pisces Moon APK
- T-Beam connected via USB-C OTG

Operation:
- Phone has cell service at trailhead, loses it on trail
- SOS Beacon app running in background
- If emergency occurs: tap SOS button twice
- Message routes through any mesh nodes in range OR
- If no mesh nodes: stores message and retransmits when in range of any node
- The phone itself becomes the gateway the moment it regains cell service

Total additional cost: $50 for T-Beam

### Scenario 2: Trail Running Event

Equipment:
- 1 gateway node at race start/finish: T-Beam + phone with APK
- Every runner carries a T-Beam
- Mesh coverage along course from relay nodes at aid stations

Operation:
- Downed runner activates SOS
- Message hops through aid station nodes to start/finish gateway
- Race director receives SMS with GPS coordinates
- Sends reply: "Medic en route, ETA 12 min"
- Runner receives confirmation

Total infrastructure cost: ~$300 for relay nodes at 3 aid stations

### Scenario 3: National Park Permanent Installation

Equipment:
- 8-12 solar relay nodes along high-traffic corridors
- 1 gateway node at visitor center (Ethernet + cellular backup)
- Twilio number routing to park SAR coordinator

Operation:
- Any hiker with a T-Beam, T-Deck, or compatible device is covered
- Coverage map posted at trailheads
- SAR coordinator receives SMS from any node in the park
- Bidirectional communication with hiker via SMS reply

Total infrastructure cost: ~$1,000. Monthly cost: $1.

### Scenario 4: Wilderness First Responder Team

Equipment:
- Each team member carries T-Beam
- Team leader's phone is gateway
- Mesh messenger for team coordination
- SOS beacon on all devices as backup

Operation:
- Team coordinates via mesh messenger (no cell required in field)
- Any team member can SOS if injured or separated
- Voice terminal for quick communication
- GPS navigator shows team member positions on topology map

Total additional cost per team member: $50

---

## PLATFORM SUPPORT

All six apps run identically on:

| Platform | Method | Hardware Bridge | Notes |
|----------|--------|----------------|-------|
| Android (APK) | Pisces Moon APK | Native USB via SmsGateway.java | Full SMS gateway capability |
| Linux/XFCE | Chromium --app= | edge_bridge.py | SMS via phone gateway on mesh |
| macOS | Chrome/Brave | edge_bridge.py | SMS via phone gateway on mesh |
| Windows | Edge/Chrome | edge_bridge.py | SMS via phone gateway on mesh |
| iOS | Safari PWA | Web Bluetooth | No SMS gateway (iOS restrictions) |

The SOS Beacon's GPS fallback to browser Geolocation works on all platforms including iOS, so position reporting functions even without T-Beam hardware.

---

## SHARED DEPENDENCIES

All six apps require these shared files in the same directory:

- `pm_shared.css` — design system (Pisces Moon color palette, common UI components)
- `pm_transport.js` — hardware transport abstraction (USB bridge / WebSocket / BLE)
- `pm_viz.js` — visualization library (charts, maps, sparklines)
- `pm_utils.js` — utility functions (HTML escaping, localStorage, format helpers)
- Leaflet.js — loaded from CDN for GPS and mesh topology maps (gps_app, mesh_messenger)

---

*Pisces Moon OS — Mesh & Communications Suite v2.0*
*Fluid Fortune — May 2026*
*Dedicated to Jennifer Soto and Clark Beddows*
*The Clark Beddows Protocol — Local Intelligence — Your machine, your rules*
