# iBall Slide Skye 03: KGV-Pro-X kernel, TWRP and LineageOS 15.1

Revive the **iBall Slide Skye 03** (S706, Unisoc/Spreadtrum **SC7731E**,
board `sp7731e_1h10`, Android 8.1 Go) with a custom kernel, a working TWRP
and a LineageOS 15.1 system that runs on the stock vendor partition.

| | Status |
|---|---|
| **KGV-Pro-X kernel** (4.4.83) | Daily use on stock Android: GPU, touch, WiFi, BT, FM, accelerometer, cameras |
| **TWRP 3.7.0_9** | Works (touch, adb, data, flashing) |
| **LineageOS 15.1** | Boots to the setup wizard. Checked: touch, display/GPU, WiFi scan, Bluetooth, both cameras, sensors, audio output, charging. Not yet tested: WiFi connect, audio playback, FM, GPS, calls/SMS |

Downloads are on the [Releases](../../releases) page. **Read all of this
before flashing.** You flash at your own risk.

## Repositories

| Repo | Contents |
|---|---|
| [iball-slide-skye-03](https://github.com/KGVHub/iball-slide-skye-03) (this) | Guide, flash/rescue tools, LineageOS build scripts and patches, local manifest |
| [android_kernel_blu_pike2](https://github.com/KGVHub/android_kernel_blu_pike2) branch `kgv/pro-x` | KGV-Pro-X kernel source |
| [mali_midgard_r21p0_sprd](https://github.com/KGVHub/mali_midgard_r21p0_sprd) | Mali GPU driver r21p0 + pike2 devfreq (module) |
| [sprdwl_ng](https://github.com/KGVHub/sprdwl_ng) | WiFi driver (module) |
| [sprd_wcn_sipc](https://github.com/KGVHub/sprd_wcn_sipc) | Bluetooth + FM drivers (modules) |
| [android_device_iball_Slide_Skye_03-twrp](https://github.com/KGVHub/android_device_iball_Slide_Skye_03-twrp) branch `twrp-9.0` | TWRP device tree |
| [android_device_iball_Slide_Skye_03](https://github.com/KGVHub/android_device_iball_Slide_Skye_03) branch `lineage-15.1` | LineageOS device tree |
| [android_vendor_iball_Slide_Skye_03](https://github.com/KGVHub/android_vendor_iball_Slide_Skye_03) branch `lineage-15.1` | The 2 proprietary libraries the system needs |
| [android_system_sepolicy](https://github.com/KGVHub/android_system_sepolicy), [android_system_core](https://github.com/KGVHub/android_system_core) branch `lineage-15.1` | LineageOS forks with the 2 platform fixes |

## Things to know first

- **Verified boot stays on.** The bootloader checks boot, recovery and vbmeta
  against keys in `vbmeta`, even when unlocked, and hangs if they do not
  match. That is why every image here comes with a matching `vbmeta`:
  - `vbmeta-v2`: boot + recovery trust our key. Use with **stock Android**.
  - `vbmeta-v3`: boot + recovery + system trust our key. Use with **LineageOS**.
- **The bootloader must be unlocked** (`fastboot getvar unlocked` or
  `getprop ro.boot.flash.locked` = `0`). On this family that is normally
  Developer options → OEM unlocking, then `fastboot flashing unlock`
  (wipes data). The author's tablet was already unlocked, so this step is
  not verified here.
- **`fastboot boot` does not exist** on this bootloader, and it **ignores
  `adb reboot recovery`**. See "Getting into TWRP" below.
- **Volume keys don't reach recovery or fastboot.** `adb reboot bootloader`
  works from a running Android.
- **Keep a backup.** Get the stock firmware (`.pac`, e.g.
  `iBall_Slide_Skye_03_S706_SC7731E_2.0_180710_SPD`) before you start.

## Hidden reset button (rescue)

If the tablet hangs with a black screen (often stuck in download mode,
showing on the PC as "USB device not recognized"), long-pressing the keys
**will not** reset it. Inside the side edge, under the volume/power
buttons, there is a **4th tactile switch with no button over it**. Pry the
edge open slightly and hold **Power + that hidden switch** with a plastic
tool: the tablet resets. The small hole on the edge is the **microphone**,
not a reset hole. Don't push a pin into it.

## Install: KGV-Pro-X kernel + TWRP (stock Android)

From a booted Android with USB debugging on:

```bash
adb reboot bootloader
fastboot flash vbmeta vbmeta-v2.img
fastboot flash recovery twrp-3.7.0_9-KGV-Slide_Skye_03.img
fastboot flash boot boot-KGV-Pro-X-daily.img
fastboot reboot
```

## Install: LineageOS 15.1

Back up your data first (TWRP, or `adb`); this wipes it.

```bash
adb reboot bootloader
fastboot flash vbmeta vbmeta-v3.img
fastboot -S 128M flash system lineage-15.1-Slide_Skye_03-system.img
fastboot flash boot boot-KGV-Pro-X-lineage.img
```

Then get into TWRP (below) and run **Wipe → Format Data**, then reboot.
The first boot takes several minutes. A "vendor image mismatch" box may
appear: tap OK (known, harmless).

To go back to stock: flash `vbmeta-v2.img`, `boot-KGV-Pro-X-daily.img` and
the stock `system.img` from the firmware `.pac`, then format data.

## Getting into TWRP

The bootloader ignores `adb reboot recovery`. Write a recovery boot command
into `misc` instead:

```bash
adb reboot bootloader
fastboot flash misc tools/misc-boot-recovery.img
fastboot reboot          # comes up in TWRP
```

If Android doesn't boot at all, write the same file from download mode
with [spd_dump](https://github.com/CE1CECL/spd_dump). Hold Volume Down
while plugging in USB, and see `tools/scripts/` (`spd_misc_win.py` does
the same on Windows over the SPRD U2S COM port):

```bash
spd_dump --wait 300 fdl fdl1-sign.bin 0x50002E00 fdl fdl2-sign.bin 0x9EFFFE00 \
  exec skip_confirm 1 write_part misc misc-boot-recovery.img reset
```

`fdl1-sign.bin` and `fdl2-sign.bin` come from the stock `.pac`
(`tools/scripts/unpac.py` extracts it). Run spd_dump on a PC with the
tablet plugged in **directly**. Download mode is too timing-sensitive for
USB-over-network.

## How LineageOS was made to boot

The stock vendor is from an early 8.1 release, and the stock boot ramdisk's
`init` is iBall's. Four problems, each found from the device's own logs
(`lineage-port/README.md` has the details):

1. **SELinux**: the stock init compiles policy without `secilc -m`, so any
   statement both the platform and vendor policy make is fatal. The build
   drops what the stock vendor already declares.
2. **Linker**: the stock vendor ships older copies of ~80 VNDK libraries in
   `/vendor/lib`; vendor processes now search the platform VNDK first.
3. **Boot ramdisk**: needs Lineage's `init.environ.rc` (Lineage framework
   jars on the class paths).
4. **Fingerprint**: Lineage's 94-byte fingerprint is over the stock init's
   91-byte property limit. The build uses the stock fingerprint.

Debug loop that worked: read `logcat` (or `/sys/fs/pstore` from TWRP after
a crash), rebuild only the failing part, push it into `/system` from TWRP,
reboot.

## Building

### Host requirements (measured on the build machine used for this port)

| | Minimum that worked | Comfortable |
|---|---|---|
| RAM | **8 GB + 4 GB swap**, build with `-j2` and Jack heap `-Xmx2G` | 16 GB, `-j8` |
| Disk | ~85 GB (repo 10 GB + source 25 GB + `out/` 47 GB) | 120 GB free (SSD) |
| CPU / time | 8 threads at `-j2`: first full build ran overnight; incremental builds 10–20 min | more cores, more `-j` |
| OS | Ubuntu 22.04+ x86_64 | |
| Tools | OpenJDK 8, Python 2.7, git-lfs, gperf, lzop, libxml2-utils, ImageMagick, ncurses5 compat libs | |

On low-RAM machines the Jack Java compiler is the usual crash: keep
`ANDROID_JACK_VM_ARGS="-Dfile.encoding=UTF-8 -XX:+TieredCompilation -Xmx2G"`
and lower `-j`. If the Jack server fails to start on a modern host, apply
`lineage-port/patches/prebuilts-sdk-jack-curl-bootstrap.patch` to
`prebuilts/sdk`.

### Sync the source

```bash
mkdir lineage-15.1 && cd lineage-15.1
repo init -u https://github.com/LineageOS/android.git -b lineage-15.1 --depth=1
mkdir -p .repo/local_manifests
curl -o .repo/local_manifests/iball_Slide_Skye_03.xml \
  https://raw.githubusercontent.com/KGVHub/iball-slide-skye-03/main/lineage-port/local_manifests/iball_Slide_Skye_03.xml
repo sync -c -j4 --no-tags --no-clone-bundle
```

The local manifest swaps in the KGVHub `system/core` and `system/sepolicy`
forks and adds the device and vendor trees.

### Lunch and build

```bash
source build/envsetup.sh
export ANDROID_JACK_VM_ARGS="-Dfile.encoding=UTF-8 -XX:+TieredCompilation -Xmx2G"
lunch lineage_Slide_Skye_03-userdebug
make -j2 systemimage
```

This target builds **only `system.img`**: the stock vendor partition is
used unchanged, and boot/recovery/vbmeta come from this repo's releases.
Output: `out/target/product/Slide_Skye_03/system.img` (sparse).

If you change `BUILD_FINGERPRINT` or other build properties, delete
`out/target/product/Slide_Skye_03/system/build.prop` and
`system/etc/prop.default` first: they are not regenerated otherwise.

### Release builds

- `userdebug` (what the published images are) keeps adb root for
  debugging. For a daily-driver build use `lunch lineage_Slide_Skye_03-user`.
- Both are signed with the AOSP **test keys**. That is fine for personal
  use; for a public release, generate your own keys and sign the target
  files (`make target-files-package` + `sign_target_files_apks`).
- Before flashing or publishing, run the checks and sign the image for
  this bootloader (AVB hashtree footer + vbmeta-v3), in this repo:

  ```bash
  lineage-port/package-system.sh   # preflight + signed system.img + vbmeta.img + SHA256SUMS
  ```

  The preflight compiles SELinux exactly as the stock init does, checks
  vendor library symbols and property lengths, and fails the build if
  anything would stop the tablet booting.
- A release should contain `system.img`, `vbmeta.img`,
  `boot-KGV-Pro-X-lineage.img` and `SHA256SUMS`.

### Kernel, modules, boot images, TWRP

- **Kernel**: `android_kernel_blu_pike2`, branch `kgv/pro-x`, defconfig
  `sp7731e_1h10_kgv_pro_x_defconfig`, GCC arm-linux-androideabi-4.9:
  `make O=out ARCH=arm CROSS_COMPILE=arm-linux-androideabi- Image`.
- **Modules** (Mali, WiFi, BT, FM): build each module repo against that
  kernel (`make -C <kernel>/out M=$PWD`). Check the symbol CRCs with
  `tools/scripts/check_module_crcs.py out/Module.symvers *.ko`.
- **Boot images**: `tools/scripts/swap_boot_ramdisk.py` and
  `tools/scripts/cpio_replace.py` build the ramdisks, signed with
  `avbtool add_hash_footer --partition_size 36700160 --partition_name boot`
  and the AOSP test key. The LineageOS boot image differs from the stock
  one only in `init.environ.rc`.
- **TWRP**: minimal-manifest-twrp `twrp-9.0` + the TWRP device tree
  (`lunch omni_Slide_Skye_03-eng && mka recoveryimage`), then pack and
  sign with its `tools/make_twrp_img.py`.

## Known issues

- LineageOS: "vendor image mismatch" box at boot (VINTF check, harmless).
- LineageOS: `vendor.sprd.hardware.log@1.0-service` restarts on an SELinux
  denial (Spreadtrum debug logging only).
- LineageOS untested: WiFi connect, audio playback, FM, GPS, calls/SMS.

## Credits

Kernel base: [Qiangong2/android_kernel_blu_pike2](https://github.com/Qiangong2/android_kernel_blu_pike2).
Download tool: [spd_dump](https://github.com/CE1CECL/spd_dump) (ilyakurdyukov, TomKing062, CE1CECL).
LineageOS, TWRP, ARM (Mali), Unisoc/Spreadtrum (WCN drivers).
Bring-up by kgvarunkanth, with Claude Code and Codex.
