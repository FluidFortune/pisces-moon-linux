<!--
  Pisces Moon OS — CONTRIBUTING.md
  Copyright (C) 2026 Eric Becker / Fluid Fortune
  SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Contributing to Pisces Moon OS

Thanks for considering a contribution. Pisces Moon is built around the **Clark Beddows Protocol** — local-first, no gatekeepers, user owns everything — and contributions should reinforce that ethos.

---

## Before you contribute

### 1. Read the CLA

All contributions are accepted under the [Contributor License Agreement (CLA.md)](CLA.md). The CLA grants the project the right to dual-license your contribution (AGPL-3.0-or-later open source + commercial licenses for organizations that need them). You retain copyright in your work.

By opening a PR, you confirm acceptance of the CLA. Each PR includes a checkbox for this.

### 2. Open an issue first (for non-trivial work)

For new apps or larger refactors, open an issue first to discuss scope. Avoids two of us building the same thing in parallel, or you spending a weekend on something that doesn't fit the roadmap.

For typo fixes, small bug fixes, and obvious improvements, just open the PR.

### 3. Read [PM_PROTOCOL.md](docs/PM_PROTOCOL.md)

The Clark Beddows Protocol is the philosophical center of the project. Contributions that violate it (forced cloud accounts, telemetry, user-data exfiltration, non-removable third-party dependencies) will not be merged.

---

## Style & conventions

### HTML apps

Each app is a single self-contained HTML file. Conventions:

- **Place in** `html/` at the root of the repo
- **Single file** — inline `<style>` and `<script>` (no separate CSS/JS files per app)
- **External libs** go in `html/lib/` and are loaded via relative path: `<script src="lib/leaflet.min.js"></script>`
- **Fonts** are loaded via `<link rel="stylesheet" href="pm_fonts.css">` (always include this)
- **Design system** uses the standard CSS vars: `--bg:#050a0e`, `--accent:#00d4ff`, `--accent3:#00ff88`, `--accent4:#ff3366`, `--gold:#f4a820`, `--text:#7ab8d4`, etc. Match existing apps.
- **Fonts:** `'Share Tech Mono', monospace` for body, `'Orbitron', monospace` for headers/UI labels
- **localStorage keys** must be namespaced `pm_*` (e.g., `pm_contacts`, `pm_vault_store`)
- **No external CDN refs** — everything bundled locally
- **No telemetry, analytics, tracking, or "phone-home" code**
- **License header** at the top of every file:
  ```html
  <!DOCTYPE html>
  <!--
    Pisces Moon OS — your_app.html v1
    Copyright (C) 2026 Eric Becker / Fluid Fortune
    SPDX-License-Identifier: AGPL-3.0-or-later
  -->
  ```

### Three-column layout for "intel" apps

Apps that filter / display / analyze data follow a consistent three-column pattern:

```
┌─────────────┬──────────────────┬──────────────┐
│   Filter    │      Grid        │   AI Analyst │
│   panel     │   (results)      │   panel      │
└─────────────┴──────────────────┴──────────────┘
```

Look at `wardrive.html`, `baseball.html`, or `recipes.html` for reference.

### Bash scripts

- Bash, not sh. Use `#!/usr/bin/env bash` and `set -euo pipefail`.
- Color helpers: copy the `step()`, `ok()`, `warn()`, `fail()`, `info()` pattern from `scripts/install.sh`.
- License header at the top — see `scripts/install_fixes.sh` for the canonical format.

### Python tools

- Python 3.11+
- Standard library only where possible. Approved external deps: `websockets`, `pyserial`.
- Type hints encouraged.
- License header at the top.

### Firmware (Arduino / C)

- Match existing style in `firmware/tbeam_pisces.ino` and `firmware/pm_serial_daemon.c`
- Keep memory footprint in mind — these are embedded devices
- License header

---

## Pull request workflow

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-app-name`
3. Make your changes
4. Test:
   - For HTML apps: open in Chromium and verify all functionality
   - For scripts: `bash -n script.sh` minimum, ideally run on a clean Debian 13 VM
5. Commit with a descriptive message
6. Push and open a PR
7. Fill in the PR template, including the CLA acceptance line
8. Wait for review

---

## Adding a new app

If you want to add a new HTML app:

1. Copy an existing app as your starting point (e.g., `flashlight.html` for a simple app or `recipes.html` for a three-column layout)
2. Update the title, copyright, SPDX header
3. Replace the body with your app
4. Add to the launcher catalog in `scripts/install.sh` (the `APPS` associative array)
5. Add to `html/about.html` so it appears in the in-OS launcher
6. Update the README app count

---

## Reporting security issues

**Do not file public GitHub issues for security vulnerabilities.** Email eric@fluidfortune.com with details. We aim to respond within 72 hours.

The security suite (cyber apps, mesh, vault) is designed to be audited. If you find a real flaw, we want to know.

---

## Code of conduct

Be excellent to each other. Don't be a jerk. We're a small project run by humans who have day jobs and families.

---

## Questions?

- General: open a GitHub issue
- Sensitive: eric@fluidfortune.com

— Eric Becker / Fluid Fortune
