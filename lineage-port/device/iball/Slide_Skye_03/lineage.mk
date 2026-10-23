# Android 8.1 system image for the stock 27.0 Treble vendor interface.
$(call inherit-product, $(SRC_TARGET_DIR)/product/treble_common_32.mk)
$(call inherit-product, vendor/lineage/config/common_mini_phone.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/go_defaults.mk)

PRODUCT_NAME := lineage_Slide_Skye_03
PRODUCT_DEVICE := Slide_Skye_03
PRODUCT_BRAND := iBall
PRODUCT_MANUFACTURER := iBall
PRODUCT_MODEL := Slide Skye 03
PRODUCT_CHARACTERISTICS := tablet
PRODUCT_AAPT_CONFIG := normal large mdpi hdpi
PRODUCT_AAPT_PREF_CONFIG := mdpi
PRODUCT_LOCALES := en_US

# No vendor partition, firmware, kernel, recovery or userdata in this target.
# Keep authenticated ADB rather than the generic GSI's ro.adb.secure=0.

# Proprietary system libraries the stock vendor needs (libefuse, librpmbclient),
# from android_vendor_iball_Slide_Skye_03.
$(call inherit-product, vendor/iball/Slide_Skye_03/Slide_Skye_03-vendor.mk)

DEVICE_PACKAGE_OVERLAYS += device/iball/Slide_Skye_03/overlay

# FM radio with the stock Spreadtrum libfmjni
PRODUCT_PACKAGES += FMRadio
# /dev/fm is owned by the media group (stock platform.xml did the same).
PRODUCT_COPY_FILES += \
    device/iball/Slide_Skye_03/permissions/fmradio-media-gid.xml:system/etc/permissions/fmradio-media-gid.xml

# Avoid visible frame-pacing stalls while the Mali governor climbs from its
# lowest 153.6 MHz step. The demand power policy still gates an idle GPU.
PRODUCT_COPY_FILES += \
    device/iball/Slide_Skye_03/rootdir/etc/init/kgv-perf.rc:system/etc/init/kgv-perf.rc
