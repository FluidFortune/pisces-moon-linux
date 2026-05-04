<!--
  Pisces Moon OS — ANDROID_GUIDE.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
  See LICENSE file. Commercial licenses available via fluidfortune.com.
-->

# PISCES MOON OS — ANDROID TROJAN HORSE GUIDE

**Version 0.4 — April 2026**
Eric Becker / Fluid Fortune / fluidfortune.com

---

## WHAT THIS IS

A complete deployment package for running Pisces Moon HTML apps on **any Android tablet or phone**, with full T-Beam USB serial integration. Three components:

1. **APK Wrapper** — Native Android app that loads the HTML in a WebView
2. **Termux Bridge** — Python script that converts USB-serial → WebSocket
3. **USB Serial App** — Third-party Android app for raw USB-OTG access

Together these form the **Localhost Relay** architecture — your HTML apps connect to `ws://127.0.0.1:8080` exactly like they do on Linux. They don't need to know they're running on Android.

---

## THE ARCHITECTURE

```
                    ┌─────────────────────┐
                    │     T-Beam S3       │
                    │  (your hardware)    │
                    └──────────┬──────────┘
                               │ USB-C (OTG cable)
                    ┌──────────▼──────────┐
                    │   Android Tablet    │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ USB Serial    │  │  ← Third-party app
                    │  │ Bridge App    │  │     (handles native USB)
                    │  └───────┬───────┘  │
                    │   exposes TCP :8888 │
                    │          │          │
                    │  ┌───────▼───────┐  │
                    │  │  Termux       │  │  ← Linux-on-Android
                    │  │  Python:      │  │
                    │  │  edge_bridge  │  │
                    │  └───────┬───────┘  │
                    │   serves WS :8080   │
                    │          │          │
                    │  ┌───────▼───────┐  │
                    │  │  Pisces Moon  │  │  ← Your APK
                    │  │  Trojan Horse │  │
                    │  │  (WebView)    │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

Why this works: Android's security model blocks Termux from raw USB access, but it allows any app to listen on a local TCP socket. The USB Serial app does the native Android dance to read your T-Beam, then re-broadcasts the data on `127.0.0.1:8888`. Termux can talk to that. Your HTML apps talk to Termux's WebSocket. Everything stays on the device — no internet required.

---

## INSTALLATION — STEP BY STEP

### Step 1: Install Termux on the tablet

**Termux must come from F-Droid or GitHub, NOT the Play Store** (the Play Store version is outdated and broken).

```
F-Droid app:  https://f-droid.org/en/packages/com.termux/
Direct APK:   https://github.com/termux/termux-app/releases
```

While you're at F-Droid, also install **Termux:Boot** — it autostarts the bridge when the tablet boots:
```
https://f-droid.org/en/packages/com.termux.boot/
```

### Step 2: Run the Termux setup script

Open Termux. You'll see a Linux shell. Type:

```bash
# First time setup — grants storage access
termux-setup-storage
```

Now copy `termux_setup.sh` and `edge_bridge_android.py` to the tablet. Easy methods:

**Method A (USB cable):**
```bash
# From your Mac, with the tablet plugged in
adb push termux_setup.sh /sdcard/Download/
adb push edge_bridge_android.py /sdcard/Download/

# In Termux on the tablet
cp /sdcard/Download/termux_setup.sh ~/
cp /sdcard/Download/edge_bridge_android.py ~/
```

**Method B (download directly in Termux):**
```bash
# If you've put the files on a public URL
curl -O https://your-server.com/termux_setup.sh
curl -O https://your-server.com/edge_bridge_android.py
```

Now run setup:
```bash
chmod +x termux_setup.sh
bash termux_setup.sh
```

Takes about 2 minutes. Installs Python, websockets library, sets up `~/pisces-moon/`, creates aliases.

### Step 3: Install a USB Serial bridge app

Pick ONE from the Play Store:

| App                                 | Cost  | Status      |
|-------------------------------------|-------|-------------|
| **USB Serial** by Kai Morich        | Free  | Recommended |
| Serial USB Terminal by Kai Morich   | Free  | Also good   |
| TCPUART Transparent Bridge          | Free  | Battle-tested |
| Serial USB Console                  | Paid  | More features |

Install. Don't open it yet.

### Step 4: Configure the bridge app

1. Plug the T-Beam into the tablet's USB-C port (use an OTG cable if your port is small)
2. Open the USB Serial app
3. Android shows: *"Allow [app] to access USB device?"* → **OK**
4. ⚠ Tick the **"Use by default for this USB device"** checkbox — saves you from re-permission every reconnect
5. In the app:
   - Set **baud rate**: `115200`
   - Set **data bits**: `8`, **stop bits**: `1`, **parity**: `none`
   - Find a setting like **"TCP Server Mode"** or **"Network Bridge"**
   - Set **port**: `8888`
   - Tap **Start** / **Connect** / **Listen**

The app should now show: *"TCP server listening on 127.0.0.1:8888"* or similar.

**Test it works** — in Termux:
```bash
nc 127.0.0.1 8888
```
You should see raw bytes from the T-Beam streaming in. Press Ctrl-C.

### Step 5: Start the Pisces Moon edge bridge

In Termux:
```bash
pm-bridge
# (alias for: bash ~/pisces-moon/start_bridge.sh)
```

You should see:
```
╔══════════════════════════════════════════════════╗
║   PISCES MOON OS — EDGE BRIDGE (ANDROID)         ║
║   T-Beam USB → WebSocket for HTML apps           ║
╚══════════════════════════════════════════════════╝

[PM-BRIDGE] HH:MM:SS [INFO] WebSocket server starting on ws://127.0.0.1:8080
[PM-BRIDGE] HH:MM:SS [INFO] Reading USB stream from 127.0.0.1:8888
[PM-BRIDGE] HH:MM:SS [OK]   Connected to USB-bridge. T-Beam stream active.
[PM-BRIDGE] HH:MM:SS [RX]   ← {"type":"wifi_scan",...}
```

If you see `[RX]` lines flowing, **you have a working bridge**. Leave Termux running.

### Step 6: Build the Pisces Moon APK

The APK source is in `apk/`. There are two ways to build it:

#### Path A: Android Studio (easier, recommended for first build)

1. Download Android Studio (free): https://developer.android.com/studio
2. Open Android Studio → **File → New → New Project**
3. Pick **Empty Activity**, package name `com.fluidfortune.piscesmoon`
4. Replace the auto-generated files:
   - Replace `app/src/main/java/com/fluidfortune/piscesmoon/MainActivity.java` with our version
   - Replace `app/src/main/AndroidManifest.xml` with our version
   - Replace `app/build.gradle` with our version
   - Create `app/src/main/res/xml/network_security_config.xml` with our version
   - Create folder `app/src/main/assets/html/`
   - Copy ALL Pisces Moon HTML files INTO `app/src/main/assets/html/`
   - Also copy `pm_scraper.js` and `pm_shared.css` into `app/src/main/assets/html/`
5. Replace the launcher icons (or keep defaults for now)
6. **Build → Build APK(s)**
7. APK appears at: `app/build/outputs/apk/debug/app-debug.apk`
8. Transfer to tablet, install. Done.

#### Path B: Gradle CLI (faster for repeat builds)

```bash
# Install Android command-line tools
# https://developer.android.com/studio#command-line-tools-only

# In the project directory
./gradlew assembleDebug

# Output: app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Step 7: Launch and verify

Open the **Pisces Moon** app on the tablet. The default app loads (about.html).

To test the bridge end-to-end, navigate to **wardrive.html** (or any cyber app):
- It should display "Connected" or show live data
- Termux logs will show new WebSocket clients connected

**🎉 You now have a complete Android Pisces Moon node.**

---

## TROUBLESHOOTING

### "Cannot reach USB-bridge app"

The Termux script can't find the TCP socket on port 8888. Either:
- The USB Serial app isn't running → reopen it
- The USB Serial app is using a different port → edit `edge_bridge_android.py` and change `USB_BRIDGE_PORT`
- The T-Beam isn't plugged in or doesn't have data permission → re-plug, re-grant

### Bridge shows no `[RX]` lines

Connection works but T-Beam isn't sending data. Check:
- Wrong baud rate (T-Beam custom firmware usually uses 115200)
- T-Beam needs to be powered on AND running firmware that outputs serial
- Test with the USB Serial app's built-in terminal — if you see no data there, problem is upstream

### HTML apps say "WebSocket disconnected"

The bridge stopped or moved. In Termux:
```bash
pm-status
```
If down, restart with `pm-bridge`.

### APK installs but crashes immediately

Common causes:
- HTML files weren't copied into `app/src/main/assets/html/`
- `network_security_config.xml` missing → Android blocks cleartext WebSocket
- Used wrong package name → check it's `com.fluidfortune.piscesmoon` everywhere

### USB Serial app loses connection randomly

This is the Android USB stack, not us. Workarounds:
- Use a high-quality OTG cable (cheap ones drop)
- Disable battery optimization for the USB Serial app: Settings → Apps → [app] → Battery → Unrestricted
- Keep the screen on while bridging (the APK does this automatically when active)

---

## AUTOSTART — RUN BRIDGE ON BOOT

If you have Termux:Boot installed (Step 1):

```bash
# The setup script already created the autostart shortcut
ls ~/.termux/boot/
# Should show: start-pisces-bridge

# Reboot
# After login, the bridge runs in the background automatically
```

You can also configure the USB Serial app to auto-start when the T-Beam is plugged in:
- Most USB Serial apps offer this in their settings
- Settings → "Start on USB device attach" or similar

---

## OPTIONAL: OPTION B (Native USB without Termux)

The current setup uses **Option A** — the Localhost Relay with Termux. **Option B** would put native Android UsbManager code directly in the APK, eliminating the need for Termux and the third-party USB Serial app.

Option B trade-offs:
- ✅ One app to install, no Termux required
- ✅ No third-party USB app needed
- ❌ Must write Java/Kotlin USB-CDC driver code (~500 lines)
- ❌ APK is fully responsible for USB lifecycle, permission handling, reconnection
- ❌ Harder to debug — logs are buried in Logcat instead of a Termux terminal

For v0.4 we ship **Option A**. If you want Option B later, it slots into the same APK — replace the WebSocket connection in your HTML apps with calls to `PiscesAndroid.readSerial()` (which would expose USB data via the JS bridge already wired in MainActivity.java).

---

## DELIVERABLE INVENTORY

```
pisces-android/
├── termux/
│   ├── edge_bridge_android.py    ← The Termux Python bridge
│   └── termux_setup.sh           ← Bootstrap script for Termux
├── apk/
│   ├── MainActivity.java         ← The WebView wrapper
│   ├── AndroidManifest.xml       ← Permissions and launcher config
│   ├── network_security_config.xml ← Allow ws://localhost
│   └── build.gradle              ← Build config
└── docs/
    └── ANDROID_GUIDE.md          ← This file
```

---

## DEPLOYMENT TO MULTIPLE TABLETS

Once you've built the APK once, deploy to additional tablets:

```bash
# Via ADB (fastest)
adb install -r pisces-moon-trojan-horse-v0.4.apk

# Via sideload
# Copy APK to /sdcard/, open file manager, tap to install
# (User must enable "Install from unknown sources" once)
```

The APK contains all 46 HTML apps as assets. Termux is per-device but the setup script makes it 5 minutes of work.

---

## LICENSE

- **APK source code**: AGPL-3.0
- **HTML apps**: MIT (already)
- **Termux bridge**: AGPL-3.0
- **Build config**: AGPL-3.0

All files have SPDX headers.

---

*Pisces Moon OS — Android Trojan Horse — fluidfortune.com — Eric Becker / 2026*
