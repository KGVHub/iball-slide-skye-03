#!/usr/bin/env bash
set -eo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$PROJECT_ROOT/lineage"
cd "$PROJECT_ROOT/lineage"
repo init -u https://github.com/LineageOS/android.git -b lineage-15.1 \
    --depth=1 --no-clone-bundle --platform=linux \
    --groups=default,-darwin,-infra,-tools,path:prebuilts/tools --git-lfs
mkdir -p .repo/local_manifests
cp "$PROJECT_ROOT/lineage-port/space-saving.xml" .repo/local_manifests/kgv-space-saving.xml
repo sync -c --no-tags --no-clone-bundle --optimized-fetch -j"${SYNC_JOBS:-2}" --fail-fast

# repo init --git-lfs does not clear skip filters in an already-created project.
git -C external/chromium-webview/prebuilt/arm config --local --replace-all filter.lfs.smudge 'git-lfs smudge -- %f'
git -C external/chromium-webview/prebuilt/arm config --local --replace-all filter.lfs.process 'git-lfs filter-process'
git -C external/chromium-webview/prebuilt/arm lfs pull
