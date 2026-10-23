#!/usr/bin/env bash
set -eo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE_DIR="$PROJECT_ROOT/lineage"
[ -f "$SOURCE_DIR/build/envsetup.sh" ] || { echo 'Finish repo sync first.' >&2; exit 1; }
[ "$(df --output=avail -k "$SOURCE_DIR" | tail -1)" -ge 41943040 ] || { echo 'Need at least 40 GiB free before starting a build.' >&2; exit 1; }
python3 - "$SOURCE_DIR/external/chromium-webview/prebuilt/arm/webview.apk" <<'PYWEBVIEW'
import sys
with open(sys.argv[1], 'rb') as f:
    if f.read(4) != b'PK\x03\x04':
        raise SystemExit('ARM WebView LFS payload missing; run lineage-port/sync.sh first.')
PYWEBVIEW
"$PROJECT_ROOT/lineage-port/apply-patches.sh"
mkdir -p "$SOURCE_DIR/device/iball/Slide_Skye_03"
cp -a "$PROJECT_ROOT/lineage-port/device/iball/Slide_Skye_03/." "$SOURCE_DIR/device/iball/Slide_Skye_03/"
mkdir -p "$SOURCE_DIR/vendor/iball/Slide_Skye_03"
cp -a "$PROJECT_ROOT/lineage-port/vendor/iball/Slide_Skye_03/." "$SOURCE_DIR/vendor/iball/Slide_Skye_03/"
mkdir -p "$SOURCE_DIR/vendor/iball/Slide_Skye_03/proprietary/lib"
for lib in libefuse.so librpmbclient.so libfmjni.so; do
 cp -p "$PROJECT_ROOT/blobs/system/lib/$lib" "$SOURCE_DIR/vendor/iball/Slide_Skye_03/proprietary/lib/$lib"
done
mkdir -p "$SOURCE_DIR/vendor/iball/Slide_Skye_03/proprietary/etc"
cp -p "$PROJECT_ROOT/blobs/system/app/DreamFMRadio/fm.conf" "$SOURCE_DIR/vendor/iball/Slide_Skye_03/proprietary/etc/fm.conf"
rm -rf "$SOURCE_DIR/device/iball/Slide_Skye_03/proprietary"
# Android 8.1 clang needs ncurses5 sonames; this host provides ncurses6.
# Keep the compatibility links in generated output, not in source checkouts.
for libdir in "$SOURCE_DIR/out/host-compat" "$SOURCE_DIR/out/host/linux-x86/lib64" "$SOURCE_DIR/out/soong/host/linux-x86/lib64"; do
 mkdir -p "$libdir"
 ln -sfn /usr/lib/x86_64-linux-gnu/libncurses.so.6 "$libdir/libncurses.so.5"
 ln -sfn /usr/lib/x86_64-linux-gnu/libtinfo.so.6 "$libdir/libtinfo.so.5"
done
export LD_LIBRARY_PATH="$SOURCE_DIR/out/host-compat${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LC_ALL=C
export USE_CCACHE=false
export CCACHE_DISABLE=1
# Precompile the framework and apps (Go defaults); WITH_DEXPREOPT=false for
# quick debug builds.
export WITH_DEXPREOPT=${WITH_DEXPREOPT:-true}
# userdebug otherwise preopts only the boot image and system server.
export WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY=${WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY:-false}
export ANDROID_JACK_VM_ARGS='-Dfile.encoding=UTF-8 -XX:+TieredCompilation -Xmx2G'
export JACK_SERVER_VM_ARGUMENTS="$ANDROID_JACK_VM_ARGS"
export JACK_HOME="$SOURCE_DIR/out/jack-server"
export JACK_CLIENT_SETTING="$SOURCE_DIR/out/jack-settings"
# 8 GB hosts: one Jack compilation at a time (each can take most of the
# 2 GB heap), and make this build, not the desktop or shell, the first
# process the OOM killer picks if memory still runs out.
if [ -f "$JACK_HOME/config.properties" ]; then
 sed -i 's/^jack.server.max-service=.*/jack.server.max-service=1/' "$JACK_HOME/config.properties"
fi
echo 500 > /proc/self/oom_score_adj
export PATH="$PROJECT_ROOT/tools/buildbin:$PROJECT_ROOT/tools/python2/bin:$PATH"
if [ -x "$SOURCE_DIR/prebuilts/jdk/jdk8/linux-x86/bin/java" ]; then
 export JAVA_HOME="$SOURCE_DIR/prebuilts/jdk/jdk8/linux-x86"
else
 export JAVA_HOME="$PROJECT_ROOT/twrp/src/prebuilts/jdk/jdk8/linux-x86"
fi
export ANDROID_JAVA_HOME="$JAVA_HOME"
export PATH="$JAVA_HOME/bin:$PATH"
cd "$SOURCE_DIR"
source build/envsetup.sh
lunch lineage_Slide_Skye_03-userdebug
make -j"${JOBS:-1}" systemimage fec 2>&1 | tee "$PROJECT_ROOT/work/lineage_build.log"
