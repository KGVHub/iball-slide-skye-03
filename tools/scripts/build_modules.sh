#!/bin/bash
# Build the out-of-tree driver modules against the KGV-Pro-X kernel in
# kernel-blu/out (build the kernel first), strip them and check their CRCs.
# They inherit the kernel's compiler flags (-O2, -mtune=cortex-a7).
# usage: build_modules.sh <out dir>
set -eu
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
OUT=$(realpath -m "${1:?out dir}")
K=$ROOT/kernel-blu
export ARCH=arm CROSS_COMPILE=${CROSS_COMPILE:-$ROOT/toolchains/arm-4.9/bin/arm-linux-androideabi-}
mkdir -p "$OUT"

(cd "$ROOT/gpu/mali-midgard-r21p0-sprd" && make -C "$K" O=out M="$PWD" modules >/dev/null && cp mali.ko "$OUT/")
(cd "$ROOT/wifi/sprdwl-ng" && make -C "$K" O=out M="$PWD" CONFIG_SPRDWL_NG=m modules >/dev/null && cp sprdwl_ng.ko "$OUT/")
cd "$ROOT/btfm/sprd-wcn-sipc"
for d in bluetooth/driver fm/driver; do
    make -C "$K" O=out M="$PWD/$d" BSP_BOARD_UNISOC_WCN_SOCKET=sipc modules >/dev/null
done
cp bluetooth/driver/sprdbt_tty.ko fm/driver/sprd_fm.ko "$OUT/"

"${CROSS_COMPILE}strip" --strip-debug "$OUT"/*.ko
python3 "$ROOT/tools/scripts/check_module_crcs.py" "$K/out/Module.symvers" "$OUT"/*.ko
