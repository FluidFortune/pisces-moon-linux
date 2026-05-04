#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Pisces Moon OS — debloat_crelander.sh
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
# Pisces Moon — Crelander Debloat Script
# Run from Mac: bash debloat_crelander.sh

echo "Debloating Crelander..."

PKGS=(
    # Unisoc/Spreadtrum manufacturer junk
    com.sprd.logmanager
    com.sprd.engineermode
    com.sprd.validationtools
    com.sprd.cameracalibration
    com.sprd.camta
    com.sprd.omacp
    com.sprd.uasetting
    com.incar.agingmode
    com.incar.update
    com.guanhong.guanhongpcb
    com.unisoc.silent.reboot
    com.tencent.soter.soterserver

    # Google bloat
    com.google.android.apps.tachyon
    com.google.android.apps.youtube.music
    com.google.android.youtube
    com.google.android.videos
    com.google.android.play.games
    com.google.android.keep
    com.google.android.gm
    com.google.android.calendar
    com.google.android.apps.maps
    com.google.android.apps.photos
    com.google.android.apps.wellbeing
    com.google.android.apps.turbo
    com.google.android.deskclock
    com.google.android.tag
    com.google.android.printservice.recommendation
    com.google.android.federatedcompute
    com.google.android.ondevicepersonalization.services
    com.google.android.gms.location.history
    com.google.mainline.telemetry
    com.google.android.adservices.api
    com.google.mainline.adservices

    # Wallpaper
    com.android.wallpaper.livepicker
    com.android.dreams.phototable

    # FM Radio
    com.android.fmradio
)

for pkg in "${PKGS[@]}"; do
    echo -n "Disabling $pkg... "
    adb shell pm disable-user --user 0 "$pkg" 2>&1 | grep -v "^$"
done

echo ""
echo "Done. Reboot the tablet."
echo "To verify: adb shell pm list packages -d"
