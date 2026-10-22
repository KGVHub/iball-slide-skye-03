#!/bin/bash
# Flash a partition image on the tablet through the Windows PC over Tailscale.
# The image is copied with scp, checked by SHA-256 on Windows, then written
# with the local fastboot.exe there (usbip fastboot is ~260 KB/s).
# The tablet must be plugged into the Windows PC, not attached through usbip.
# usage: remote_flash.sh <partition> <image> [--no-reboot]
set -u
PART=${1:?partition}; IMG=${2:?image}; REBOOT=${3:-}
# Set REMOTE_FLASH_HOST="user@windows-host" and REMOTE_FLASH_KEY=~/.ssh/key
HOST=${REMOTE_FLASH_HOST:?set REMOTE_FLASH_HOST=user@host}
KEY=${REMOTE_FLASH_KEY:-$HOME/.ssh/id_ed25519}
WDIR='C:/kgv-flash'
PT='C:\platform-tools'
[ -f "$IMG" ] || { echo "no such image: $IMG"; exit 1; }
W() { ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "$@"; }

name=$(basename "$IMG")
want=$(sha256sum "$IMG" | cut -c1-64)
echo "== copying $name ($(du -h "$IMG" | cut -f1))"
W "if not exist C:\\kgv-flash mkdir C:\\kgv-flash" >/dev/null || exit 1
scp -q -i "$KEY" -o BatchMode=yes "$IMG" "$HOST:$WDIR/$name" || { echo "scp failed"; exit 1; }
got=$(W "powershell -NoProfile -Command (Get-FileHash '$WDIR/$name').Hash" | tr -d '\r' | tr A-F a-f)
[ "$got" = "$want" ] || { echo "hash mismatch on Windows: $got"; exit 1; }
echo "== sha256 verified on Windows"

if [ -z "$(W "$PT\\fastboot.exe devices" | tr -d '\r')" ]; then
    W "$PT\\adb.exe reboot bootloader" >/dev/null 2>&1
    for i in $(seq 1 40); do
        sleep 2
        [ -n "$(W "$PT\\fastboot.exe devices" | tr -d '\r')" ] && break
    done
fi
[ -n "$(W "$PT\\fastboot.exe devices" | tr -d '\r')" ] || { echo "no fastboot device on Windows"; exit 2; }

out=$(W "$PT\\fastboot.exe -S 128M flash $PART $WDIR/$name" 2>&1 | tr -d '\r')
echo "$out" | tail -4
echo "$out" | grep -q 'FAILED\|error' && { echo "== flash FAILED, not rebooting"; exit 2; }
echo "$out" | grep -q 'Writing.*OKAY' || { echo "== no Writing OKAY, not rebooting"; exit 2; }
echo "== flashed $PART"
[ "$REBOOT" = --no-reboot ] && exit 0
W "$PT\\fastboot.exe reboot" >/dev/null 2>&1
for i in $(seq 1 75); do
    sleep 4
    [ "$(W "$PT\\adb.exe shell getprop sys.boot_completed" 2>/dev/null | tr -d '\r')" = 1 ] && {
        echo "== Android up: $(W "$PT\\adb.exe shell uname -rv" | tr -d '\r')"; exit 0; }
done
echo "Android did not finish booting"; exit 3
