#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  Pisces Moon OS — install.sh (top-level wrapper)
#  Copyright (C) 2026 Eric Becker / Fluid Fortune
#  SPDX-License-Identifier: AGPL-3.0-or-later
#
#  Convenience wrapper. Just calls scripts/install.sh.
#
#  Usage:
#    sudo ./install.sh
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo:  sudo ./install.sh"
    exit 1
fi

if [[ ! -x "$SCRIPT_DIR/scripts/install.sh" ]]; then
    chmod +x "$SCRIPT_DIR/scripts/install.sh"
fi

exec "$SCRIPT_DIR/scripts/install.sh" "$@"
