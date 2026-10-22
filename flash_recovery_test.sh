#!/bin/bash
# Safe recovery-slot test for KGVKernel. Flashes ONLY the recovery partition.
# Normal boot/system are never touched. Stock recovery can be restored anytime.
set -e
IMG=/home/kgvarunkanth/claude/out/recovery-KGV.img
STOCK=/home/kgvarunkanth/claude/firmware/unpacked/recovery.img
FB="fastboot"

echo "== 1. Checking fastboot device =="
$FB devices
N=$($FB devices | grep -c fastboot || true)
[ "$N" -ge 1 ] || { echo "No device in fastboot mode. Enter fastboot first (see steps)."; exit 1; }

echo "== 2. Image to flash =="
ls -la "$IMG"
echo "Kernel inside:"; LC_ALL=C grep -ao 'Linux version 4.4.83-KGVKernel[^)]*)' "$IMG" | head -1

read -p "Flash this to the RECOVERY partition? (normal OS untouched) [y/N] " ans
[ "$ans" = y ] || { echo "Aborted."; exit 0; }

echo "== 3. Flashing recovery =="
$FB flash recovery "$IMG"

echo
echo "== Done. To TEST: boot into recovery =="
echo "   fastboot reboot        # boots normal Android"
echo "   then: adb reboot recovery   (or hold Power+Vol-Up)"
echo
echo "== To RESTORE stock recovery later =="
echo "   fastboot flash recovery $STOCK"
