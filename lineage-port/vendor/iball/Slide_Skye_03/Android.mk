LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),Slide_Skye_03)

# Spreadtrum FM JNI library from the stock ROM; it drives /dev/fm and reads
# /system/app/DreamFMRadio/fm.conf. Used by FMRadio (BOARD_FMRADIO_PREBUILT_JNI).
include $(CLEAR_VARS)
LOCAL_MODULE := libfmjni
LOCAL_SRC_FILES := proprietary/lib/libfmjni.so
LOCAL_MODULE_CLASS := SHARED_LIBRARIES
LOCAL_MODULE_SUFFIX := .so
LOCAL_MODULE_TAGS := optional
LOCAL_MULTILIB := 32
LOCAL_STRIP_MODULE := false
LOCAL_SHARED_LIBRARIES := libcutils libmedia liblog libnativehelper libc++
include $(BUILD_PREBUILT)

endif
