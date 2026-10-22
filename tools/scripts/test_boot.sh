#!/bin/bash
# Safe boot test for iBall Slide Skye 03: flash a boot image, watch it boot,
# grab logs from any adb window, and restore the stock boot if Android does
# not finish booting.
# Restore path: adb reboot autodloader + spd_dump (backup boot/vbmeta).
# usage: test_boot.sh <boot.img> <vbmeta for it> <log dir> [timeout s]
set -u
IMG=${1:?boot.img}; VBMETA=${2:?vbmeta}; LOG=${3:?log dir}; TMO=${4:-180}
STOCK_BOOT=/home/kgvarunkanth/claude/backup/raw-20261021/boot.img
STOCK_VBMETA=/home/kgvarunkanth/claude/out/vbmeta-custom-KGV.img
mkdir -p "$LOG"

to_fastboot() {   # reboot to fastboot from Android/recovery, catching short adb windows
    for i in $(seq 1 900); do
        [ -n "$(timeout 1 fastboot devices 2>/dev/null)" ] && return 0
        st=$(adb get-state 2>/dev/null)
        if [ "$st" = device ] || [ "$st" = recovery ]; then adb reboot bootloader 2>/dev/null; fi
        sleep 0.3
    done
    return 1
}
flash() {         # flash <part> <img>, fail if not OKAY
    timeout 120 fastboot flash "$1" "$2" 2>&1 | tee -a "$LOG/flash.txt" | grep -q 'Writing.*OKAY'
}

echo "== to fastboot"; to_fastboot || { echo "could not reach fastboot"; exit 1; }
flash vbmeta "$VBMETA" && flash boot "$IMG" || { echo "flash failed"; exit 1; }
fastboot reboot >/dev/null 2>&1

echo "== watching boot for ${TMO}s"
t0=$(date +%s); ok=0; n=0
while [ $(( $(date +%s) - t0 )) -lt "$TMO" ]; do
    if [ "$(adb get-state 2>/dev/null)" = device ]; then
        n=$((n + 1))
        timeout 8 adb shell 'uname -r; cat /proc/version' >> "$LOG/version.txt" 2>&1
        timeout 8 adb shell dmesg > "$LOG/dmesg.$n.txt" 2>&1
        timeout 8 adb logcat -d -b all > "$LOG/logcat.$n.txt" 2>&1
        [ "$(timeout 4 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { ok=1; break; }
    fi
    sleep 0.5
done
echo "adb windows captured: $n"

if [ $ok = 1 ]; then
    echo "== BOOT COMPLETED in $(( $(date +%s) - t0 ))s"
    exit 0
fi

echo "== did not finish booting -> restoring stock boot via download mode"
# Our test kernels ignore "reboot bootloader", but "reboot autodloader" makes
# u-boot enter download mode, where spd_dump rewrites the partitions.
F=/home/kgvarunkanth/claude/firmware/unpacked
B=/home/kgvarunkanth/claude/backup/raw-20261021
/home/kgvarunkanth/claude/tools/spd_dump/spd_dump --wait 600 \
    fdl $F/fdl1-sign.bin 0x50002E00 fdl $F/fdl2-sign.bin 0x9EFFFE00 exec \
    part_size boot skip_confirm 1 \
    write_part vbmeta $B/vbmeta.img write_part vbmeta_bak $B/vbmeta_bak.img \
    write_part boot $B/boot.img reset > "$LOG/spd_restore.txt" 2>&1 &
spd=$!
for i in $(seq 1 1800); do
    [ "$(adb get-state 2>/dev/null)" = device ] && { adb reboot autodloader 2>/dev/null; break; }
    sleep 0.3
done
wait $spd || { echo "spd_dump restore failed - see $LOG/spd_restore.txt"; exit 2; }
for i in $(seq 1 60); do
    sleep 4
    [ "$(timeout 3 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { echo "== stock restored, Android booted"; exit 3; }
done
echo "stock written but boot not confirmed yet"; exit 3
