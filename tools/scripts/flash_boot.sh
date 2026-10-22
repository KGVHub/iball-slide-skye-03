#!/bin/bash
# Flash a boot image to the iBall Slide Skye 03 and wait for Android.
# Tries fastboot first; if the tablet does not reach fastboot (our test
# kernels ignore "reboot bootloader"), falls back to download mode via
# "adb reboot autodloader" + spd_dump.
# The image must be signed for the boot key in the vbmeta on the tablet
# (vbmeta v2 = our test key).
# usage: flash_boot.sh <boot.img> [fastboot wait s]
set -u
IMG=${1:?boot.img}; FB_WAIT=${2:-40}
F=/home/kgvarunkanth/claude/firmware/unpacked
SPD=/home/kgvarunkanth/claude/tools/spd_dump/spd_dump
LOG=/home/kgvarunkanth/claude/work/flash_boot.log
[ -f "$IMG" ] || { echo "no such image: $IMG"; exit 1; }
: > "$LOG"

wait_android() {
    for i in $(seq 1 75); do
        sleep 4
        [ "$(timeout 3 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && {
            echo "== Android up: $(adb shell uname -rv | tr -d '\r')"; return 0; }
    done
    echo "Android did not finish booting"; return 1
}

echo "== trying fastboot"
if [ -z "$(timeout 2 fastboot devices)" ]; then
    adb reboot bootloader 2>>"$LOG"
    for i in $(seq 1 "$FB_WAIT"); do
        sleep 1
        [ -n "$(timeout 2 fastboot devices)" ] && break
    done
fi
if [ -n "$(timeout 2 fastboot devices)" ]; then
    if timeout 120 fastboot flash boot "$IMG" 2>&1 | tee -a "$LOG" | grep -q 'Writing.*OKAY'; then
        echo "== flashed with fastboot"
        fastboot reboot >/dev/null 2>&1
        wait_android; exit $?
    fi
    echo "fastboot flash failed, see $LOG"; exit 2
fi

echo "== no fastboot after ${FB_WAIT}s, using download mode"
"$SPD" --wait 300 fdl $F/fdl1-sign.bin 0x50002E00 fdl $F/fdl2-sign.bin 0x9EFFFE00 exec \
    part_size boot skip_confirm 1 write_part boot "$IMG" reset >>"$LOG" 2>&1 &
spd=$!
for i in $(seq 1 900); do
    [ "$(adb get-state 2>/dev/null)" = device ] && { adb reboot autodloader 2>/dev/null; break; }
    sleep 0.3
done
wait $spd || { echo "spd_dump failed, see $LOG"; exit 2; }
echo "== flashed with spd_dump"
wait_android
