#!/bin/bash
# Performance benchmark for the tablet, following docs/PERFORMANCE.md "Method".
# Needs adb (root not required). Run at least two minutes after boot, screen on,
# unlocked, launcher in front. Prints one summary line plus raw values.
# usage: perf_bench.sh [label]
set -u
LABEL=${1:-run}
A() { adb shell "$@" | tr -d '\r'; }

A input keyevent 224; A wm dismiss-keyguard >/dev/null 2>&1; A input keyevent 3; sleep 2

launch() {   # pkg/component -> median TotalTime of 3 force-stopped runs
    local comp=$1 pkg=${1%%/*} t=()
    for i in 1 2 3; do
        A am force-stop "$pkg"; A input keyevent 3; sleep 2
        t+=("$(A am start -W -n "$comp" | awk '/TotalTime/{print $2}')")
        sleep 2
    done
    A input keyevent 3
    printf '%s\n' "${t[@]}" | sort -n | sed -n 2p
}

declare -A L
for c in com.android.settings/.Settings \
         com.android.camera2/com.android.camera.CameraLauncher \
         com.android.fmradio/.FmMainActivity \
         com.android.gallery3d/.app.GalleryActivity; do
    L[$c]=$(launch "$c")
done
for p in com.android.settings com.android.camera2 com.android.fmradio com.android.gallery3d; do A am force-stop $p; done

# Launcher: 10 left/right swipe pairs at 250 ms per swipe on the home screen.
A input keyevent 3; sleep 2
A dumpsys gfxinfo org.lineageos.trebuchet reset >/dev/null
for i in $(seq 1 10); do
    A input swipe 520 500 80 500 250; A input swipe 80 500 520 500 250
done
sleep 2
G=$(A dumpsys gfxinfo org.lineageos.trebuchet)
frames=$(echo "$G" | awk -F': ' '/Total frames rendered/{print $2; exit}')
janky=$(echo "$G" | awk '/Janky frames:/{print $3, $4; exit}')
pct=$(echo "$G" | awk '/50th percentile|90th percentile|95th percentile|99th percentile/{printf "%s ", $3}' | head -c 60)

free_idle=$(A dumpsys meminfo | awk '/Free RAM:/{gsub(",","",$3); print $3; exit}')
echo "== $LABEL"
echo "Settings ${L[com.android.settings/.Settings]} ms | Camera ${L[com.android.camera2/com.android.camera.CameraLauncher]} ms | FM ${L[com.android.fmradio/.FmMainActivity]} ms | Gallery ${L[com.android.gallery3d/.app.GalleryActivity]} ms"
echo "Launcher: $frames frames, janky $janky, p50/p90/p95/p99 $pct"
echo "Free RAM: $free_idle"
