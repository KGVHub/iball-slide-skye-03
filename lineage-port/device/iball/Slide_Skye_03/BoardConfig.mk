# System-only port: retain the validated KGV-Pro-X boot and stock vendor.
include build/make/target/board/treble_common_32.mk

TARGET_ARCH := arm
TARGET_ARCH_VARIANT := armv7-a-neon
TARGET_CPU_VARIANT := cortex-a7
TARGET_CPU_ABI := armeabi-v7a
TARGET_CPU_ABI2 := armeabi
# CONFIG_ANDROID_BINDER_IPC_32BIT=y in the validated kernel.
TARGET_USES_64_BIT_BINDER := false

TARGET_BOARD_PLATFORM := sp7731e
TARGET_BOOTLOADER_BOARD_NAME := sp7731e_1h10
TARGET_NO_BOOTLOADER := true
TARGET_NO_KERNEL := true
TARGET_NO_RECOVERY := true
TARGET_SYSTEM_PROP := device/iball/Slide_Skye_03/system.prop

# Physical system partition: 1363148800 bytes. Match the stock filesystem
# payload limit, leaving space for SHA1 verity + 2-root FEC + signed footer.
# Signing is a separate packaging step; generic Treble rejects BOARD_AVB_ENABLE.
BOARD_SYSTEMIMAGE_PARTITION_SIZE := 1341554688
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BUILD_SYSTEM_ROOT_IMAGE := false
BOARD_USES_GENERIC_AUDIO := false
TARGET_USES_HWC2 := true
TARGET_SCREEN_WIDTH := 600
TARGET_SCREEN_HEIGHT := 1024

# Stock vendor policy, compiled by an init without secilc -m (see
# lineage-port/patches/system-sepolicy-stock-vendor-dups.patch).
BOARD_SEPOLICY_STOCK_VENDOR_CIL := device/iball/Slide_Skye_03/sepolicy/stock_nonplat_sepolicy.cil

# The stock vendor ships its own older copies of most VNDK libraries in
# /vendor/lib. Search the platform VNDK first for vendor processes, or
# mixed versions fail to link (e.g. missing gServiceSidMap in hwcomposer).
TARGET_LD_CONFIG_FILE := device/iball/Slide_Skye_03/ld.config.txt

# Use the stock vendor's fingerprint. Lineage's own is 94 characters, over
# the 91 the stock init accepts, so ro.build.fingerprint stayed empty and
# ActivityManager crashed formatting the fingerprint-mismatch warning.
BUILD_FINGERPRINT := iBall/Slide_Skye_03/Slide_Skye_03:8.1.0/OPM2.171019.012/32419:user/release-keys
