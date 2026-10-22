#!/usr/bin/env bash
set -eo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE_DIR="$PROJECT_ROOT/lineage"
DEST_DIR="$PROJECT_ROOT/out/lineage-15.1-Slide_Skye_03"
SYSTEM_DIR="$SOURCE_DIR/out/target/product/Slide_Skye_03/system"
SYSTEM_IMAGE="$SOURCE_DIR/out/target/product/Slide_Skye_03/system.img"
export PATH="$SOURCE_DIR/out/host/linux-x86/bin:$PATH"
command -v fec >/dev/null || { echo 'Build the host fec tool first.' >&2; exit 1; }
"$PROJECT_ROOT/lineage-port/check-system.py" --system "$SYSTEM_DIR" \
 --vendor "$PROJECT_ROOT/blobs/vendor" --image "$SYSTEM_IMAGE" \
 --secilc "$SOURCE_DIR/out/host/linux-x86/bin/secilc"
"$PROJECT_ROOT/lineage-port/check-vendor-symbols.py" --system "$SYSTEM_DIR" \
 --vendor "$PROJECT_ROOT/blobs/vendor" \
 --baseline "$PROJECT_ROOT/lineage-port/vendor-symbols-stock-baseline.json" \
 --json "$PROJECT_ROOT/work/lineage_built_vendor_symbols.json"
mkdir -p "$DEST_DIR"
cp --reflink=auto "$SYSTEM_IMAGE" "$DEST_DIR/system.img"
python3 "$PROJECT_ROOT/tools/avb/avbtool.py" add_hashtree_footer \
 --image "$DEST_DIR/system.img" --partition_name system --partition_size 1363148800 \
 --hash_algorithm sha1 --fec_num_roots 2 --algorithm SHA256_RSA4096 \
 --key "$PROJECT_ROOT/tools/avb/testkey_rsa4096.pem"
python3 "$PROJECT_ROOT/tools/avb/avbtool.py" verify_image \
 --image "$DEST_DIR/system.img" --key "$PROJECT_ROOT/tools/avb/testkey_rsa4096.pem"
"$PROJECT_ROOT/lineage-port/prepare-vbmeta.py"
cp "$PROJECT_ROOT/out/vbmeta-lineage-system-KGV-v3.img" "$DEST_DIR/vbmeta.img"
(cd "$DEST_DIR" && sha256sum system.img vbmeta.img > SHA256SUMS)
echo "Candidate prepared in $DEST_DIR; no flash performed. ABI/namespace and hardware validation remain."
