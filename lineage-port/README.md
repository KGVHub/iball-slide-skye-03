# LineageOS 15.1 system-only bring-up

Initial target for iBall Slide Skye 03, SC7731E, Android 8.1 vendor.
This is an unvalidated port, not a supported LineageOS device build.

Measured: ARM32 userspace, 32-bit Binder, Treble enabled, vendor SELinux policy
27.0, separate vendor, A-only/non-system-as-root, 1,363,148,800-byte system.
Retain the working KGV-Pro-X boot, stock vendor, known-good TWRP, modem and NV.
Do not flash generic disabled-vbmeta artifacts: this SPRD bootloader requires
its established signed chain. Any ROM flash requires explicit user approval.

The source checkout is ../lineage (excluded from workspace Git). Source history
uses repo --depth=1, current-branch-only sync, no tags/clone bundles, Linux
platform, and two download jobs. The local manifest excludes non-ARM WebViews
and the Android emulator. No ccache is used. Existing TWRP source is retained.

Device files here are copied to lineage/device/iball/Slide_Skye_03 by the build
script. Build only systemimage; this target deliberately does not build boot,
recovery or vendor images. Verify system image size, vendor dependency and
policy compatibility before offering it for a hardware test.

See ../docs/KERNEL_AUDIT.md for remaining kernel issues. Building a ROM does
not resolve the timer/hotplug warning or validate untested hardware functions.

The stock vendor ELF audit found 66 needed libraries outside vendor. Most are
platform/VNDK modules. Two proprietary system dependencies, libefuse.so and
librpmbclient.so, are copied from the existing blobs repository when building.
No stock libc/libutils/framework libraries are substituted over Lineage output.
All other vendor dependencies must be checked against the completed staging
image. Stock combined split SELinux policy compiles with secilc policyvers 30;
repeat that check with the generated Lineage platform policy before flashing.

AVB: physical system is 1,363,148,800 bytes; stock filesystem payload limit is
1,341,554,688 bytes. BoardConfig uses the latter, reserving the observed space
for SHA1 hashtree, two-root FEC and a SHA256_RSA4096 vbmeta/footer. A separate
packaging step must sign the image and update only the system chain key in the
existing v2 DHTB-wrapped vbmeta. Preserve boot/recovery test-key chains and all
stock vendor/modem keys. Do not flash the generic disabled-vbmeta output.

Host preparation used the existing Python 2.7 and downloaded JDK8. Additional
packages installed: git-lfs, gperf, lzop, libxml2-utils, ImageMagick. The tools
group is excluded except for the required prebuilts/tools project, which
supplies Java test-library definitions needed by the graph checks even when
building only systemimage. Missing dependency checks stay enabled. Source
revisions are recorded in manifest-pinned.xml.

Host-only patches are stored under patches/ and applied idempotently by
apply-patches.sh. The pinned manifest records upstream revisions; apply these
patches afterward. The Jack patch handles the first-start state before PEM
certificates exist on recent curl; it does not weaken TLS verification.

check-vendor-symbols.py models vendor-first DT_NEEDED resolution and compares
strong imports with dependency exports (including the ARM linker exports).
The stock baseline for all 380 vendor ELFs has no unresolved strong imports;
its JSON baseline is tracked. Packaging stops on new unresolved imports. This
heuristic does not validate runtime dlopen, symbol versions or namespaces.

## Status 2026-10-22: boots to the setup wizard

LineageOS 15.1 userdebug boots on the tablet (boot_completed=1, setup
wizard, no system_server crashes) with the stock vendor and the
KGV-Pro-X #13 kernel. Four fixes were needed, each found from device logs:

1. SELinux: the stock init runs secilc without -m. Platform statements the
   stock vendor policy also makes are left out
   (BOARD_SEPOLICY_STOCK_VENDOR_CIL, patches/system-sepolicy-stock-vendor-dups.patch).
2. Linker: the stock vendor ships older copies of ~80 VNDK libraries in
   /vendor/lib. Vendor processes search the platform VNDK first
   (device ld.config.txt, TARGET_LD_CONFIG_FILE,
   patches/system-core-device-ld-config.patch). Without it hwcomposer and
   the camera provider fail to link (gServiceSidMap).
3. Boot ramdisk: Lineage's init.environ.rc puts the Lineage framework jars
   on BOOTCLASSPATH/SYSTEMSERVERCLASSPATH. Boot image:
   out/boot-KGV-Pro-X-lineage.img (kernel #13 + daily ramdisk with that
   one file; tools/scripts/swap_boot_ramdisk.py, cpio_replace.py). Use it
   only with the Lineage system; the stock system keeps the daily image.
4. Fingerprint: the stock init drops property values over 91 bytes.
   BUILD_FINGERPRINT (BoardConfig.mk) is the stock vendor fingerprint.
   A changed fingerprint does not regenerate build.prop: delete
   system/build.prop and system/etc/prop.default in out/ before rebuilding.

Install: vbmeta v3 (out/lineage-15.1-Slide_Skye_03/vbmeta.img), system
(same directory, `fastboot -S 128M flash system`), boot-KGV-Pro-X-lineage.img,
then format data in TWRP.

Hardware on Lineage (checked over adb): touch, display/GPU (Mali-T820
r21p0 GLES 3.2, 59 fps), WiFi scan, Bluetooth on, both cameras listed and
rear preview streaming, BMA253 accelerometer and proximity sensors, audio
output thread, battery/charging, modem firmware loaded (no SIM tested).
Not yet tested by hand: WiFi connect, audio playback, FM, GPS, calls/SMS.
Known issue: vendor.sprd.hardware.log@1.0-service restarts on an SELinux
denial registering ILogControl (debug logging only).

Debug loop: read logcat/pstore, rebuild only the failing component, get to
TWRP (adb reboot bootloader; fastboot flash misc <boot-recovery BCB>;
fastboot reboot), mount system rw and push the file, reboot. The bootloader
ignores `adb reboot recovery`.
