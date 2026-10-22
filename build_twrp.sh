#!/bin/bash
# Build TWRP 3.7.0_9 for iBall Slide Skye 03 and pack it into the stock SPRD recovery layout.
set -o pipefail
SRC=/home/kgvarunkanth/claude/twrp/src
LOG=/home/kgvarunkanth/claude/twrp/build.log
IMG_OUT=/home/kgvarunkanth/claude/out/twrp-3.7.0_9-KGV-Slide_Skye_03.img
export PATH=/home/kgvarunkanth/claude/tools/buildbin:/home/kgvarunkanth/claude/tools/python2/bin:$PATH
export LC_ALL=C ALLOW_MISSING_DEPENDENCIES=true
cd "$SRC"
source build/envsetup.sh
lunch omni_Slide_Skye_03-eng || exit 1
# Ubuntu 26.04 has only ncurses 6; host tools built against the glibc2.17 sysroot want .so.5
for d in out/soong/host/linux-x86/lib64 out/host/linux-x86/lib64; do
    mkdir -p "$d"
    ln -sf /usr/lib/x86_64-linux-gnu/libncurses.so.6 "$d/libncurses.so.5"
    ln -sf /usr/lib/x86_64-linux-gnu/libtinfo.so.6 "$d/libtinfo.so.5"
done
mka -j${JOBS:-6} recoveryimage 2>&1 | tee "$LOG"
rc=$?
[ $rc -eq 0 ] || { echo "=== build failed rc=$rc ==="; exit $rc; }
python3 /home/kgvarunkanth/claude/tools/scripts/make_twrp_img.py \
    "$SRC/out/target/product/Slide_Skye_03/recovery.img" "$IMG_OUT"
