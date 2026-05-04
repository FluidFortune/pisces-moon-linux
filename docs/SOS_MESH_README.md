<!--
  Pisces Moon OS — SOS_MESH_README.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON — MESH SOS SYSTEM
## Emergency Communication for the World Beyond Cell Service
### Version 1.0 — May 2026
**Eric Becker / Fluid Fortune / fluidfortune.com**
*The Clark Beddows Protocol — Local Intelligence. No Gatekeepers. Your Machine, Your Rules.*

---

> "The moment you need emergency communication is the exact moment
> cell infrastructure fails you. Mountains block signals. Canyons
> swallow them. Disasters knock out towers. The only system that
> works when everything else fails is the one that doesn't depend
> on anything else."

---

## WHAT THIS IS

The Pisces Moon Mesh SOS System is an emergency communication network built on LoRa radio mesh technology. It enables anyone carrying a compatible device — a $50 T-Beam, a T-Deck, a tablet with an edge node, a laptop — to send an SOS message with GPS coordinates that routes through a mesh of relay nodes to a gateway, which forwards it as an SMS to any phone number on Earth.

No cell service required at the sender's location.
No satellite subscription required.
No monthly fee beyond a $1/month Twilio number.
No proprietary hardware lock-in.
No single point of failure.

The total hardware cost for a complete park-wide deployment: under $1,000.
The monthly operational cost: $1.

---

## HOW IT WORKS

### The Message Path

```
HIKER IN DISTRESS
(no cell service)
        ↓
   T-Beam / T-Deck / Tablet + Edge Node
   Tap SOS button
   GPS coordinates auto-populated
   Message broadcast on ALL LoRa channels
        ↓ LoRa radio (915MHz, 10-15km line of sight)
   RELAY NODE 1
   (solar-powered, fixed installation)
   Receives message, rebroadcasts
        ↓ LoRa hop
   RELAY NODE 2
   (trailhead, ranger station, ridge mount)
        ↓ LoRa hop
   GATEWAY NODE
   (cellular or WiFi connected)
   Receives SOS, formats message, sends SMS
        ↓ Twilio SMS API / Native Android SMS
   SAR COORDINATOR / 911 / EMERGENCY CONTACT
   Receives formatted SMS with GPS coordinates
   and Google Maps link
        ↓ SMS reply
   BACK THROUGH THE MESH
   Hiker receives confirmation:
   "Help is coming. ETA 2 hours. Stay put."
```

### The SOS Message Format

When a hiker activates SOS, the following SMS is sent to all configured contacts:

```
[PM-SOS] EMERGENCY

Person: Jane Smith
Situation: Broken ankle, cannot walk, solo hiker

GPS: 36.57854, -118.29231
Alt: 3,847m
Accuracy: GOOD

MAP: https://maps.google.com/?q=36.57854,-118.29231

Node: pisces-7a3b
Broadcast #3
Time: 2026-05-03T19:42:17Z

Reply to this number to send message back to the device.
Pisces Moon OS — mesh.fluidfortune.com
```

The SAR coordinator receives an immediately actionable message. No decoding required. No app required on the receiving end. A standard SMS with a Google Maps link.

### Two-Way Communication

Unlike most emergency beacons, this system is **fully bidirectional**. The SAR coordinator can reply:

```
SMS: "Jane, your location is confirmed. 
Mountain Rescue helicopter ETA 90 minutes. 
Stay where you are, conserve heat, 
flash your light every 10 minutes."
```

That reply routes back through the mesh to the hiker's device. They know help is coming. The psychological impact of confirmation cannot be overstated — a hiker who knows their signal was received behaves very differently from one who pressed a button and heard nothing.

---

## THE HARDWARE

### Sender Devices (field-deployable)

Any of the following work as SOS senders:

| Device | Cost | Battery Life | Notes |
|--------|------|-------------|-------|
| LilyGo T-Beam S3 Supreme | $50 | 12-20 hrs | GPS built-in, ideal |
| LilyGo T-Deck Plus | $50 | 8-12 hrs | Keyboard, runs full Pisces Moon OS |
| ESP32 + SX1262 + battery | $15-25 | Variable | Bare minimum DIY build |
| Android tablet + T-Beam OTG | $70-150 | 8-12 hrs | Full Pisces Moon suite |
| Laptop + T-Beam USB | Any | Variable | Full capability |

### Relay Nodes (fixed deployment)

Fixed relay nodes are T-Beams in weatherproof enclosures with solar panels.

**Component cost per node:**
- LilyGo T-Beam S3: $50
- Weatherproof ABS enclosure: $8
- 5W solar panel: $12
- SLA or LiPo battery pack: $15
- LoRa antenna (fiberglass, 3dBi): $10
- Mounting hardware: $5
- **Total per node: ~$100**

### Gateway Nodes

The gateway needs internet connectivity. Options:

| Gateway Type | Cost | Monthly | Notes |
|-------------|------|---------|-------|
| Android phone (existing) | $0 extra | $1 (Twilio) | Uses phone's cellular data |
| LilyGo T-SIM7080G | $25 | $5-10 (SIM) | Dedicated, no phone needed |
| T-Beam + WiFi location | $50 | $1 (Twilio) | Requires WiFi at gateway loc |
| Raspberry Pi + LTE hat | $60 | $5-10 (SIM) | Fixed installation, robust |

### Complete Park Deployment Example

**Moderate-sized trail system (50 sq km coverage):**

| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| Relay nodes (solar) | 8 | $100 | $800 |
| Gateway node (cellular SIM) | 1 | $35 | $35 |
| Twilio number | 1 | $1/mo | $1/mo |
| **Total** | | | **$835 + $1/mo** |

That covers a 50 square kilometer trail system with emergency communication capability. Forever. For the cost of less than three months of a single Garmin inReach subscription.

---

## HONEST COMPARISON WITH SATELLITE DEVICES

### Why Satellite Isn't Always Better

| Factor | Satellite (Garmin inReach) | Pisces Moon Mesh |
|--------|--------------------------|-----------------|
| Hardware cost | $350 | $50 |
| Monthly cost | $15-50 | $1 |
| Works anywhere on Earth | ✓ Yes | ✗ Requires mesh coverage |
| Two-way messaging | ✓ Yes | ✓ Yes |
| GPS coordinates | ✓ Yes | ✓ Yes |
| Battery life | 100+ hours (tracking off) | 12-20 hours (active) |
| Requires subscription | ✓ Always | ✗ One-time hardware |
| Requires proprietary service | ✓ Garmin network | ✗ Open LoRa standard |
| Community deployable | ✗ No | ✓ Yes |
| Works if company goes bankrupt | ✗ No | ✓ Yes |
| Works when satellites are jammed | ✗ No | ✓ Yes |

### Where Mesh Wins

**1. Price.** The satellite device costs 7x more. The subscription costs 15-50x more per month. For the cost of one year of a Garmin inReach subscription ($180-600), you can deploy six relay nodes covering an entire trail system.

**2. Community infrastructure.** Satellite devices are individual tools. The Pisces Moon mesh is community infrastructure. A trail running club, SAR team, or park conservancy deploys the nodes once. Every hiker with any compatible device — including people who didn't specifically plan for emergencies — benefits automatically.

**3. No subscription failure.** Satellite devices stop working if you forget to pay, if the company changes its terms, if the service is discontinued. A deployed mesh network continues operating indefinitely with no ongoing dependency on any vendor.

**4. Resilience to infrastructure attacks.** GPS satellite signals can theoretically be jammed. LoRa operates on unlicensed spectrum at frequencies that are extremely difficult to selectively jam without affecting a wide area. In a scenario where GPS jamming is occurring (military conflict, HEMP event), LoRa mesh may continue functioning where satellite devices fail.

**5. No single point of failure.** The mesh has no central server, no cloud infrastructure, no single company whose operational status determines whether it works. Each node is independent. Nodes that go offline are routed around automatically. The network degrades gracefully rather than failing catastrophically.

**6. Extensibility.** Satellite devices do one thing. The T-Beam running Pisces Moon OS simultaneously collects WiFi intelligence, scans BLE devices, monitors the RF spectrum, and records GPS tracks — while being an SOS beacon. One device, many functions.

### Where Satellite Wins

**1. Coverage.** Satellite works anywhere on Earth with clear sky view. The mesh requires nodes within LoRa range. In truly remote wilderness with no deployed infrastructure, satellite is the only option.

**2. Per-device independence.** Each satellite device works independently. The mesh requires network coverage — a single hiker in a completely un-meshed area cannot get a message out regardless of their device.

**3. Battery life.** Garmin inReach in tracking mode lasts weeks. T-Beam in active mode lasts 12-20 hours. In low-power SOS-only mode (broadcast every 60 seconds, sleep otherwise) the T-Beam can last 3-7 days on a single 18650 cell plus a small power bank.

### The Honest Bottom Line

**For individual hikers in remote wilderness: bring a satellite device.** The coverage guarantee is worth the price for solo backcountry travel.

**For organized activities in defined areas: deploy mesh.** A trail running race, a scout troop, a search and rescue team operating in a known geographic area — mesh infrastructure serves the entire group for less than the cost of devices for each individual.

**The ideal combination:** A mesh network deployed in high-use wilderness areas as community infrastructure, with satellite devices as individual backups for those venturing beyond mesh coverage.

---

## DEPLOYMENT GUIDE — NATIONAL PARKS AND WILDERNESS AREAS

### Phase 1: Assessment

Map the area and identify:
- **High-traffic entry points** — trailheads, visitor centers, parking areas. These are guaranteed gateway locations with existing infrastructure.
- **Natural relay points** — ridges, peaks, saddles, firetowers, existing communication infrastructure. These give maximum LoRa range.
- **High-risk zones** — popular technical routes, cliffs, river crossings, areas with historical incident concentration.

Draw circles of 5km radius (conservative urban) or 10km radius (line-of-sight open terrain) around each planned node location. Identify gaps and add relay nodes to fill them.

### Phase 2: Gateway Installation

The gateway is the only node that requires ongoing connectivity. Install at the park entrance, visitor center, or ranger station where:
- Cellular signal is reliable
- Electrical power is available for charging backup battery
- Physical security is adequate (theft prevention)

The gateway node runs continuously. Configure the Twilio webhook to forward incoming SOS messages to:
- Park SAR coordinator phone
- Local 911 dispatch (where legally appropriate — confirm with local authorities)
- A designated emergency contact list

### Phase 3: Relay Node Deployment

Each solar relay node:

1. **Enclosure** — IP66 or better waterproof ABS or polycarbonate box. Mount the LoRa antenna externally for maximum range. The antenna connector passes through a weatherproof gland.

2. **Power** — 5W solar panel mounted on the enclosure or on a separate bracket. The AXP2101 PMU on the T-Beam handles solar charging natively. Add a 3.7V LiPo or 18650 pack sized for 5+ days of cloudy weather.

3. **Mounting** — Trail signs, existing fence posts, tree mounting straps, small post-mount. Keep antenna vertical and elevated above surrounding vegetation.

4. **Firmware** — Relay nodes run a minimal firmware: receive LoRa, rebroadcast on same frequency, report own battery and GPS to mesh. No display required. No keyboard. Just radio.

5. **Maintenance** — Annual inspection. Check solar panel orientation, clean panels, verify battery health. The T-Beam hardware is rated for -40°C to +85°C operating temperature.

### Phase 4: Community Integration

**Signage.** Post at trailheads: "This trail is covered by Pisces Moon Emergency Mesh Network. In emergency, activate SOS on your Pisces Moon device or compatible LoRa device."

**QR codes.** Link to the Pisces Moon app download. A hiker who downloads the app before their trip has SOS capability on their existing phone (via Bluetooth to a T-Beam, or via direct T-Beam device).

**SAR training.** Work with local SAR teams to integrate mesh SOS messages into their dispatch procedures. The SMS format is standardized and immediately actionable.

**Partnership opportunities:**
- Trail running clubs (members carry T-Beams during events)
- Wilderness first aid organizations
- Scout organizations
- College outdoor programs
- State and national park foundations
- Search and rescue volunteer organizations

---

## SOS BEACON APP — USER GUIDE

### Before You Go

1. **Set your profile.** Name, emergency contact number, SAR contact number, default situation description ("Hiking alone, Mt Whitney main trail, expected return 6pm").

2. **Test the gateway.** Use the Send Test SMS button to verify your gateway contact receives a test message. Do this before entering the field.

3. **Verify GPS.** The SOS beacon shows GPS quality bars. Ensure you have a fix before departing. The T-Beam typically acquires fix within 30-90 seconds with clear sky.

4. **Know the mesh coverage.** Download the mesh coverage map for your area (if one exists). Know where the relay nodes are. Plan your route to stay within coverage where possible.

### In the Field

The SOS beacon app runs in the background while you use other Pisces Moon apps. GPS is continuously updated from the T-Beam.

**To activate SOS:**
1. Open the SOS Beacon app
2. Tap the large red SOS button once (confirmation required)
3. Tap again within 3 seconds to confirm
4. The app broadcasts immediately and every 60 seconds thereafter
5. Watch the hop display to see your message routing through the mesh

**What the device does automatically:**
- Broadcasts GPS coordinates every 60 seconds on all channels simultaneously
- Requests screen wake lock (screen stays on)
- Displays inbound replies prominently
- Vibrates on reply received
- Switches to 5-minute heartbeat when acknowledged (to conserve battery)

**Battery management during SOS:**
- The broadcast cycle (200ms transmit every 60 seconds) uses approximately 5mA average current
- A 3500mAh 18650 cell lasts approximately 700 hours (29 days) at this duty cycle
- In practice, GPS continuous operation dominates current draw — realistic SOS mode battery life is 48-96 hours on a full 18650

### For SAR Coordinators

**Receiving an SOS:**

The SMS arrives formatted with all relevant information. The Google Maps link opens directly to the coordinates. No app required on the receiving end.

**Sending a reply:**

Reply to the SMS from the Twilio number. Your reply routes back through the mesh to the hiker's device. Keep replies short (SMS length limits) and direct:

Good reply examples:
- "Help confirmed. Helicopter ETA 2 hours. Stay put, conserve heat."
- "Mountain rescue en route. ETA 3 hours. Flash light every 10 min."
- "Received. SAR team deploying. Estimated arrival 90 min."
- "Confirm: are you injured? Reply Y/N."

**If no reply arrives at the hiker:**

The mesh may be overloaded or the hiker may have moved out of coverage. The hiker's device continues broadcasting every 60 seconds — as long as messages arrive at the gateway, SAR is being updated with the current GPS position even if replies don't reach the hiker.

---

## LOW POWER SOS FIRMWARE

For maximum battery life in emergency scenarios, the T-Beam can run a dedicated low-power SOS firmware:

```
Power cycle:
  55.8 seconds: deep sleep (~0.01mA)
  200ms: wake, transmit SOS packet (~100mA)
  500ms: listen for ACK (~12mA)
  500ms: process, update GPS (~80mA)

Average current: ~2mA
18650 3500mAh battery life: ~1750 hours = 72 days
```

This firmware sacrifices real-time GPS updates (position updates every 60 seconds instead of continuously) in exchange for weeks of battery life. For a hiker who has activated SOS and needs to wait for rescue, 72 days of battery life is effectively infinite.

The GPS position in the SOS message updates every cycle. SAR coordinators see a new position every 60 seconds, which is more than sufficient for helicopter location.

---

## THE BIGGER PICTURE

### What This Changes

There are approximately 300,000 search and rescue operations per year in the United States. Roughly 60% occur in wilderness areas. Cell service is unavailable at the point of emergency in an estimated 40% of backcountry incidents.

Garmin inReach and similar satellite devices have saved lives. But at $350 plus $15-50/month, they are economically accessible to a subset of hikers. The people most likely to be underprepared for wilderness emergencies — less experienced hikers, families on day trips, people who spontaneously decide to extend a hike — are the people least likely to own a $350 emergency beacon.

A $50 T-Beam running Pisces Moon OS changes this calculus. A trail club deploying a mesh network in a popular recreation area creates emergency communication infrastructure that benefits anyone who enters the coverage area — including people who have never heard of Pisces Moon, who carry only a phone and a water bottle, who didn't plan for emergencies.

The mesh is community infrastructure. Like a trailhead register. Like a wilderness first aid station. Like the painted blazes on a trail. It benefits everyone who passes through, regardless of their preparation level.

### The CERT and SAR Integration

Community Emergency Response Teams and Search and Rescue organizations are the natural deployment partners for this system. They already:
- Operate in the areas where mesh coverage is most needed
- Have the technical sophistication to deploy and maintain nodes
- Have the SAR coordinator infrastructure to receive and act on SOS messages
- Have organizational continuity to maintain the network long-term

A proposal to a regional SAR organization: provide the hardware designs, firmware, and gateway software. They provide the deployment labor, local knowledge, and operational integration. The hardware cost per node is less than a tank of gas.

### The Clark Beddows Protocol Applied

The Clark Beddows Protocol says: local first, no gatekeepers, you own everything.

Applied to emergency communication:
- **Local first** — the mesh operates without any central server, cloud service, or vendor dependency
- **No gatekeepers** — any device that speaks the protocol can participate. No subscription, no registration, no approval process.
- **You own everything** — the nodes you deploy, the frequencies you use (unlicensed), the firmware running on your hardware, the data flowing through your network

A Garmin inReach operates on Garmin's satellite network, using Garmin's infrastructure, under Garmin's terms of service, for Garmin's subscription fee. If Garmin discontinues the service, the device becomes a GPS-only unit. The network you deployed cannot be taken away.

---

## TECHNICAL APPENDIX

### LoRa Parameters for Emergency Use

For maximum range and reliability in emergency scenarios:

```
Frequency:        915MHz (US) / 868MHz (EU) / 433MHz (global)
Spreading Factor: SF12 (maximum range, minimum data rate)
Bandwidth:        125kHz
Coding Rate:      4/8
TX Power:         20dBm (maximum legal)
```

At SF12, 125kHz bandwidth, 20dBm TX power with a 3dBi antenna:
- Urban/suburban: 3-5km
- Rural open terrain: 8-12km
- Mountain line of sight: 15-25km
- Theoretical maximum: 40km+ (antenna height and terrain dependent)

Trade-off: SF12 limits data rate to ~293 bps. An SOS message of 500 characters takes approximately 14 seconds to transmit. This is fine for emergency use — the 60-second broadcast interval provides adequate throughput.

### Message Format

```json
{
  "type":      "SOS",
  "version":   "1.0",
  "node_id":   "pisces-7a3b",
  "name":      "Jane Smith",
  "contact":   "+15551234567",
  "sar":       "+15559876543",
  "situation": "Broken ankle, cannot walk, solo hiker",
  "gps": {
    "lat":     36.57854,
    "lon":     -118.29231,
    "alt_m":   3847,
    "hdop":    1.2,
    "sats":    11,
    "quality": "EXCELLENT"
  },
  "maps_url":  "https://maps.google.com/?q=36.57854,-118.29231",
  "timestamp": "2026-05-03T19:42:17Z",
  "broadcast": 3,
  "platform":  "Pisces Moon OS"
}
```

### Gateway SMS Template

```
[PM-SOS] EMERGENCY

Person: {name}
Situation: {situation}

GPS: {lat}, {lon}
Alt: {alt}m
Accuracy: {quality}

MAP: https://maps.google.com/?q={lat},{lon}

Node: {node_id}
Broadcast #{n}
Time: {timestamp}

Reply to this number to contact the device.
Pisces Moon OS — mesh.fluidfortune.com
```

### Twilio Configuration

1. Create a Twilio account at twilio.com
2. Purchase a phone number ($1/month)
3. Configure the SMS webhook URL to point to your Phantom server or gateway endpoint
4. Add the Twilio account SID, auth token, and phone number to your gateway configuration

For organizations without a server: the Android phone acting as gateway does not require a Twilio webhook — it uses native Android SMS send/receive directly.

---

## LICENSE

This system is released under MIT license.
The hardware designs are open.
The firmware is open.
The protocol is open.
The SMS format is documented.

Anyone can deploy this. Any SAR organization, any trail club, any park conservancy, any individual. No license fee. No vendor lock-in. No permission required.

The only thing we ask: if you deploy this and it saves a life, let us know.

forge@fluidfortune.com

---

*Pisces Moon OS — Fluid Fortune — May 2026*
*Dedicated to Jennifer Soto and Clark Beddows*
*The Clark Beddows Protocol — Local Intelligence — Your machine, your rules*

*"The moment you need emergency communication is the exact moment cell infrastructure fails you. We built the alternative."*
