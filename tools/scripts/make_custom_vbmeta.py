#!/usr/bin/env python3
"""Build a custom vbmeta for iBall Slide Skye 03 that trusts our key for chosen partitions.

Every chain descriptor of the stock vbmeta (boot, system, vendor, modem...) is
copied verbatim, keeping its original public key and rollback location, so the
stock OS verifies exactly as before. Only the chain keys of OUR_PARTS (comma
list, default 'recovery') are replaced with the public half of AVBKEY. The
result is wrapped in the same SPRD DHTB header as stock (magic, version,
sha256(payload), payload size) and padded to the stock file size.

usage: make_custom_vbmeta.py <stock vbmeta-sign.img> <out.img>
"""
import hashlib, os, struct, subprocess, sys, tempfile

AVBTOOL = os.environ.get("AVBTOOL", "/home/kgvarunkanth/claude/tools/avb/avbtool.py")
sys.path.insert(0, os.path.dirname(AVBTOOL))
import avbtool  # noqa: E402

AVBKEY = os.environ.get("AVBKEY", "/home/kgvarunkanth/claude/tools/avb/testkey_rsa4096.pem")
DHTB_SIZE = 0x200
# chain partitions whose key is replaced with AVBKEY
OUR_PARTS = os.environ.get("OUR_PARTS", "recovery").split(",")


def main():
    stock_path, outp = sys.argv[1], sys.argv[2]
    stock = open(stock_path, "rb").read()
    assert stock[:4] == b"DHTB", "stock vbmeta has no DHTB header"
    payload_size = struct.unpack_from("<I", stock, 0x30)[0]
    payload = stock[DHTB_SIZE:DHTB_SIZE + payload_size]
    assert hashlib.sha256(payload).digest() == stock[8:40], "stock DHTB hash mismatch"

    hdr = avbtool.AvbVBMetaHeader(payload[:avbtool.AvbVBMetaHeader.SIZE])
    aux = payload[avbtool.AvbVBMetaHeader.SIZE + hdr.authentication_data_block_size:]
    descs = avbtool.parse_descriptors(aux[hdr.descriptors_offset:
                                          hdr.descriptors_offset + hdr.descriptors_size])

    tmp = tempfile.mkdtemp()
    our_pub = os.path.join(tmp, "recovery_pub.bin")
    subprocess.check_call([sys.executable, AVBTOOL, "extract_public_key",
                           "--key", AVBKEY, "--output", our_pub])

    args = [sys.executable, AVBTOOL, "make_vbmeta_image", "--key", AVBKEY,
            "--algorithm", "SHA256_RSA4096", "--rollback_index", str(hdr.rollback_index),
            "--padding_size", str(payload_size), "--output", os.path.join(tmp, "vbmeta.img")]
    for d in descs:
        assert isinstance(d, avbtool.AvbChainPartitionDescriptor), "unexpected descriptor %r" % d
        if d.partition_name in OUR_PARTS:
            key = our_pub
        else:
            key = os.path.join(tmp, d.partition_name + "_pub.bin")
            open(key, "wb").write(d.public_key)
        args += ["--chain_partition", "%s:%d:%s" % (d.partition_name, d.rollback_index_location, key)]
        print("chain %-9s loc %d  %s" % (d.partition_name, d.rollback_index_location,
                                         "OUR KEY" if key == our_pub else "stock key"))
    subprocess.check_call(args)

    new_payload = open(os.path.join(tmp, "vbmeta.img"), "rb").read()
    assert len(new_payload) == payload_size, "payload size %d != stock %d" % (len(new_payload), payload_size)

    dhtb = bytearray(stock[:DHTB_SIZE])
    dhtb[8:40] = hashlib.sha256(new_payload).digest()
    out = bytes(dhtb) + new_payload
    out += b"\0" * (len(stock) - len(out))
    open(outp, "wb").write(out)
    print("wrote %s (%d bytes, same size as stock)" % (outp, len(out)))


if __name__ == "__main__":
    main()
