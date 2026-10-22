# LineageOS 15.1 device tree: iBall Slide Skye 03

| | |
|---|---|
| SoC | Unisoc SC7731E (pike2), board `sp7731e_1h10`, ARM32 |
| Stock | Android 8.1 Go, Treble, vendor interface 27.0 |
| Build | `lineage_Slide_Skye_03-userdebug`, **system image only** |

This port runs a LineageOS system on the **unmodified stock vendor
partition**. Boot (kernel + ramdisk), recovery and vbmeta come from
[iball-slide-skye-03](https://github.com/KGVHub/iball-slide-skye-03).

## Build

```bash
repo init -u https://github.com/LineageOS/android.git -b lineage-15.1
mkdir -p .repo/local_manifests
curl -o .repo/local_manifests/iball_Slide_Skye_03.xml \
  https://raw.githubusercontent.com/KGVHub/iball-slide-skye-03/main/lineage-port/local_manifests/iball_Slide_Skye_03.xml
repo sync -c
source build/envsetup.sh
lunch lineage_Slide_Skye_03-userdebug
make systemimage
```

## What makes it boot on the stock vendor

- `BOARD_SEPOLICY_STOCK_VENDOR_CIL`: the stock init runs `secilc` without
  `-m`, so platform policy statements the vendor also makes are dropped
  (needs the KGVHub `android_system_sepolicy` fork).
- `TARGET_LD_CONFIG_FILE`: vendor processes search the platform VNDK before
  `/vendor/lib`, which holds older VNDK copies (needs the KGVHub
  `android_system_core` fork).
- `BUILD_FINGERPRINT` is the stock one: the stock init drops property
  values over 91 bytes.
- The boot ramdisk must carry Lineage's `init.environ.rc` (see the main repo).
