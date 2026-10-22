#!/usr/bin/env bash
set -eo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE_DIR="$PROJECT_ROOT/lineage"
apply_patch_file() {
 local project=$1 patch_file=$2
 if git -C "$SOURCE_DIR/$project" apply --reverse --check "$patch_file" >/dev/null 2>&1; then
  return 0
 fi
 git -C "$SOURCE_DIR/$project" apply --check "$patch_file"
 git -C "$SOURCE_DIR/$project" apply "$patch_file"
}
apply_patch_file prebuilts/sdk "$PROJECT_ROOT/lineage-port/patches/prebuilts-sdk-jack-curl-bootstrap.patch"
apply_patch_file system/sepolicy "$PROJECT_ROOT/lineage-port/patches/system-sepolicy-stock-vendor-dups.patch"
apply_patch_file system/core "$PROJECT_ROOT/lineage-port/patches/system-core-device-ld-config.patch"
apply_patch_file build/make "$PROJECT_ROOT/lineage-port/patches/build-make-device-vintf.patch"
