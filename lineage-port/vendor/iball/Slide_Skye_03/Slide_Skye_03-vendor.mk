# Proprietary files from the stock iBall Slide Skye 03 ROM
# (iBall/Slide_Skye_03/Slide_Skye_03:8.1.0/OPM2.171019.012/32419:user/release-keys).
# The stock vendor partition is used as-is; only these system-side libraries,
# which stock vendor binaries link against, are needed in the system image.

PRODUCT_COPY_FILES += \
    vendor/iball/Slide_Skye_03/proprietary/lib/libefuse.so:system/lib/libefuse.so \
    vendor/iball/Slide_Skye_03/proprietary/lib/librpmbclient.so:system/lib/librpmbclient.so

# FM radio: the stock config at the path the stock libfmjni reads.
PRODUCT_COPY_FILES += \
    vendor/iball/Slide_Skye_03/proprietary/etc/fm.conf:system/app/DreamFMRadio/fm.conf
