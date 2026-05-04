<!--
  Pisces Moon OS — UNIFIED_ARCHITECTURE.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON OS — UNIFIED SOURCE TREE

**Version 0.5 — April 2026**
Eric Becker / Fluid Fortune / fluidfortune.com

---

## THE ARCHITECTURE

One source tree. Two deployments. Same HTML apps in both.

```
pisces-moon/
├── apps/                          ← THE SOURCE OF TRUTH
│   ├── shared/
│   │   ├── pm_scraper.js          ← News/feed scraping library
│   │   ├── pm_shared.css          ← Visual design system
│   │   └── pm_transport.js        ← Hardware connection abstraction
│   ├── cyber/                     ← Apps that talk to T-Beam
│   │   └── (wardrive.html, bt_radar.html, etc.)
│   └── intel/                     ← Apps with no hardware needs
│       └── (news_general.html, recipes.html, baseball.html, etc.)
│
├── deploy-linux/                  ← x86 / XFCE deployment
│   ├── install.sh
│   ├── install_fixes.sh
│   └── tools/
│       └── edge_bridge.py         ← USB serial → WebSocket bridge
│
├── deploy-android/                ← Android APK deployment
│   ├── apk/                       ← Java/Kotlin WebView wrapper source
│   ├── termux/                    ← Optional fallback bridge
│   └── docs/
│       └── ANDROID_GUIDE.md
│
├── firmware/                      ← T-Beam firmware reference
│   └── ble_gatt_service.md        ← BLE service spec for cyber apps
│
├── licenses/
│   ├── LICENSE-AGPL.txt
│   └── LICENSE-MIT.txt
│
└── build.sh                       ← Materializes both deployments
```

## WHY ONE SOURCE TREE

The HTML apps don't care what platform they run on. They're written in standards-compliant HTML/JS/CSS that works in any modern Chromium.

What changes between Linux and Android is only:
- The **shell** (XFCE menu vs. APK launcher)
- The **transport** for hardware-using apps (WebSocket vs. Web Bluetooth)
- The **install/distribution mechanism** (Debian package vs. APK sideload)

So we keep one copy of the apps and let each deployment wrap them differently.

## THE TRANSPORT ABSTRACTION

The cleverness lives in `apps/shared/pm_transport.js`. Every cyber app uses it like this:

```javascript
const beam = new PMTransport({
    onMessage: msg => handleData(msg),
    onStatus:  s   => updateUI(s),
});

await beam.connect();         // auto-detects WebSocket OR Bluetooth
beam.send({cmd: "wifi_scan"});
```

The same HTML app, with no code changes, works in both deployments:
- **On Linux:** transport.connect() finds the WebSocket from edge_bridge.py
- **On Android:** transport.connect() opens a BLE pairing dialog and uses Web Bluetooth

The app developer doesn't need to know or care which one is in use. The transport layer handles everything.

## THE TWO TRANSPORTS

### Transport A: WebSocket (Linux primary)

```
T-Beam (USB-C) → edge_bridge.py (Python) → WebSocket :8080 → HTML app
```

- High bandwidth (1+ MB/s)
- Requires Python and a running daemon
- Good for x86 desktops/tablets where running services is normal

### Transport B: Web Bluetooth (Android primary)

```
T-Beam (BLE GATT) → Pisces Moon APK WebView → HTML app
```

- Low bandwidth (10-50 KB/s practical)
- Zero infrastructure — no Python, no daemon, no Termux
- Good for tablets/phones where users won't run services
- Requires firmware support on the T-Beam (see firmware/ble_gatt_service.md)

### When does each get used?

`pm_transport.js` auto-detects:

```
On Linux desktop Chromium:
  → Try WebSocket first (probes ws://127.0.0.1:8080)
  → If unavailable, fall back to Web Bluetooth

On Android Pisces Moon APK:
  → Try Web Bluetooth first (no daemon dependency)
  → If T-Beam not paired or BLE unavailable, fall back to Termux WebSocket

The user can also manually override:
  new PMTransport({mode: "bluetooth"})
  new PMTransport({mode: "websocket"})
```

## THE FIRMWARE CONTRACT

For the Android Web Bluetooth path to work, the T-Beam firmware must expose its data as a BLE GATT service. The spec is in `firmware/ble_gatt_service.md`.

Briefly:
- Service UUID: `8b5e0001-7c34-4a91-bd5c-1a2e9d6f8c4a`
- One characteristic for data (T-Beam → tablet, NOTIFY)
- One characteristic for commands (tablet → T-Beam, WRITE)
- One characteristic for status (T-Beam → tablet, NOTIFY)
- All payloads are JSON strings encoded as UTF-8

The same firmware can keep its existing USB serial output for the Linux path. Just emit on both transports — anyone listening gets the data.

## BUILD

```bash
./build.sh both        # Build both deployments (default)
./build.sh linux       # Linux only
./build.sh android     # Android only
```

Outputs land in `build-out/`:
- `pisces-moon-linux-v0.5.zip` — Drop on a Debian system, run install.sh
- `pisces-moon-android-v0.5.zip` — Contains APK source + assets + bridge

## DEVELOPMENT WORKFLOW

When you fix a bug or add a feature to an HTML app:

1. Edit the HTML file in `apps/cyber/` or `apps/intel/`
2. Test it directly: `chromium --app=file://$PWD/apps/intel/news_general.html`
3. Run `./build.sh` to produce updated deployment packages
4. Both Linux and Android get the change — no double maintenance

When you fix something Linux-specific (install script, edge bridge):

1. Edit the file in `deploy-linux/`
2. Android side is unaffected
3. Run `./build.sh linux`

When you fix something Android-specific (APK, Termux bridge):

1. Edit the file in `deploy-android/`
2. Linux side is unaffected
3. Run `./build.sh android`

## VERSIONING

Both deployments share a single version number. v0.5 Linux and v0.5 Android contain the same HTML apps from the same git commit. This avoids the divergent-fork trap — there's no "v0.5.2 Linux but v0.4.3 Android" confusion.

The only place version numbers diverge is the APK's `versionCode` (Android requires monotonically increasing integers) which is computed from the semver: `0.5 → 50`, `0.5.1 → 51`, etc.

## LICENSING

| Component | License | Files |
|-----------|---------|-------|
| Platform infrastructure | AGPL-3.0 | install.sh, install_fixes.sh, edge_bridge.py, build.sh, APK source |
| HTML applications | MIT | apps/intel/*.html, apps/cyber/*.html |
| Shared libraries | MIT | apps/shared/*.js, apps/shared/*.css |
| Firmware spec | MIT | firmware/*.md |

All files have SPDX headers.

## NEXT STEPS

To complete the unified source tree:

1. **Move existing v0.4 HTML apps** into `apps/cyber/` and `apps/intel/`
2. **Update cyber apps** to use `pm_transport.js` instead of hardcoded WebSocket
3. **Implement BLE GATT firmware** on the T-Beam following `firmware/ble_gatt_service.md`
4. **Run `./build.sh`** to produce v0.5 deployment packages
5. **Test on both platforms** — Q508 for Linux, Crelander or Lenovo for Android

Once cyber apps speak the transport abstraction, Pisces Moon becomes truly platform-portable. One codebase, multiple deployments, unified maintenance.

---

*Pisces Moon OS — Unified Source — fluidfortune.com — Eric Becker — 2026*
*A resource. Not a dependency.*
