#!/bin/bash
# Chunked, self-verifying raw backup of one partition (for flaky long reads).
# Each chunk is accepted only when the copy pulled to the PC matches a
# sha256 computed by an independent read on the tablet; otherwise retried.
# usage: backup_chunked.sh <partition name> <out.img> [chunk MiB]
set -u
PART=${1:?partition}; OUT=${2:?out.img}; CH=${3:-16}
DEV=/dev/block/platform/soc/soc:ap-ahb/20600000.sdio/by-name/$PART
blk=$(adb shell "readlink -f $DEV" | tr -d '\r'); blk=${blk##*/}
bytes=$(( $(adb shell "cat /sys/class/block/$blk/size" | tr -d '\r') * 512 ))
n=$(( (bytes + CH*1048576 - 1) / (CH*1048576) ))
tmp=$(mktemp)
: > "$OUT"
for ((i = 0; i < n; i++)); do
    for try in 1 2 3 4 5 6 7 8; do
        adb exec-out "dd if=$DEV bs=1048576 skip=$((i*CH)) count=$CH 2>/dev/null" > "$tmp"
        want=$(adb shell "dd if=$DEV bs=1048576 skip=$((i*CH)) count=$CH 2>/dev/null | sha256sum" | cut -c1-64)
        got=$(sha256sum "$tmp" | cut -c1-64)
        # TWRP's dd fails to seek to some offsets past 2 GiB; both reads are
        # then empty and their hashes match, so also require the full length.
        len=$(( bytes - i*CH*1048576 < CH*1048576 ? bytes - i*CH*1048576 : CH*1048576 ))
        [ "$want" = "$got" ] && [ "$(stat -c %s "$tmp")" -eq "$len" ] && break
        echo "  chunk $i: mismatch, retry $try"
    done
    [ "$want" = "$got" ] || { echo "chunk $i failed after 8 tries"; rm -f "$tmp"; exit 1; }
    cat "$tmp" >> "$OUT"
    printf '\r%s: %d/%d chunks' "$PART" $((i+1)) "$n"
done
rm -f "$tmp"
echo
[ "$(stat -c %s "$OUT")" -eq "$bytes" ] || { echo "size mismatch"; exit 1; }
echo "OK $OUT $bytes bytes"
