#!/bin/bash
# Raw-image backup of every eMMC partition of the iBall Slide Skye 03 from TWRP over adb.
# Each image is checked with sha256 on the tablet and on the PC.
# usage: backup_partitions.sh <out dir> [extra partitions, e.g. userdata]
set -u
OUTDIR=${1:?usage: backup_partitions.sh <out dir> [extra partitions]}
shift
BYNAME=/dev/block/platform/soc/soc:ap-ahb/20600000.sdio/by-name
SKIP=" userdata "
EXTRA=" $* "
mkdir -p "$OUTDIR"

adb get-state 2>/dev/null | grep -q recovery || { echo "tablet is not in TWRP (adb recovery)"; exit 1; }

parts=$(adb shell "ls $BYNAME" | tr -d '\r')
parts="$parts mmcblk0boot0 mmcblk0boot1"

fail=0
for p in $parts; do
    if [[ "$SKIP" == *" $p "* && "$EXTRA" != *" $p "* ]]; then continue; fi
    case $p in mmcblk0boot*) dev=/dev/block/$p ;; *) dev=$BYNAME/$p ;; esac
    printf '%-14s ' "$p"
    adb exec-out "dd if=$dev bs=1048576 2>/dev/null" > "$OUTDIR/$p.img"
    dev_sum=$(adb shell "sha256sum $dev" | tr -d '\r' | cut -d' ' -f1)
    pc_sum=$(sha256sum "$OUTDIR/$p.img" | cut -d' ' -f1)
    size=$(stat -c %s "$OUTDIR/$p.img")
    if [ "$dev_sum" = "$pc_sum" ]; then
        echo "OK   $size bytes"
        echo "$pc_sum  $p.img" >> "$OUTDIR/SHA256SUMS"
    else
        echo "MISMATCH (tablet $dev_sum, pc $pc_sum)"
        fail=1
    fi
done
exit $fail
