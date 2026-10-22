#!/bin/bash
# Build kernel for iBall Slide Skye 03 (SC7731E / pike2 / SP7731E-1H10-FP)
set -o pipefail
KROOT=/home/kgvarunkanth/claude/kernel
TC=/home/kgvarunkanth/claude/toolchains/arm-4.9/bin/arm-linux-androideabi-
LOG=/home/kgvarunkanth/claude/build.log
cd "$KROOT"
export ARCH=arm
export CROSS_COMPILE="$TC"
export KBUILD_BUILD_USER=romdev KBUILD_BUILD_HOST=claude
JOBS=$(nproc)
echo "=== toolchain ==="; ${TC}gcc --version | head -1
echo "=== building zImage + DTB (sp7731e-1h10-native-fp) ==="
make -j"$JOBS" zImage sp7731e-1h10-native-fp.dtb 2>&1 | tee "$LOG"
rc=$?
echo "=== build rc=$rc ==="
ls -la arch/arm/boot/zImage arch/arm/boot/dts/sp7731e-1h10-native-fp.dtb 2>&1
exit $rc
