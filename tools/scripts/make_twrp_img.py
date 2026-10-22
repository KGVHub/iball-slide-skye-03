#!/usr/bin/env python3
"""Pack a ramdisk into the stock SPRD boot/recovery layout for iBall Slide Skye 03.

STOCK is the template image (header, kernel, DT); PART_NAME is the AVB
partition name (recovery or boot).

Layout (matches stock recovery.img): Android boot header v0 with the SPRD
dt_size field at offset 40, kernel, ramdisk, SPRD appended DT, then an AVB
hash footer padding the image to the full recovery partition size.

usage: make_twrp_img.py <ramdisk.cpio.gz|recovery.img> <out.img> [kernel]
"""
import hashlib, os, struct, subprocess, sys

STOCK = os.environ.get("STOCK", "/home/kgvarunkanth/claude/firmware/unpacked/recovery.img")
AVBTOOL = os.environ.get("AVBTOOL", "/home/kgvarunkanth/claude/tools/avb/avbtool.py")
AVBKEY = os.environ.get("AVBKEY", "/home/kgvarunkanth/claude/tools/avb/testkey_rsa4096.pem")
PART_SIZE = 36700160
PART_NAME = os.environ.get("PART_NAME", "recovery")


def rup(n, p):
    return (n + p - 1) // p * p


def split_bootimg(d):
    assert d[:8] == b"ANDROID!", "not an Android boot image"
    ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from("<8I", d, 8)
    dt_size = struct.unpack_from("<I", d, 40)[0]
    off = rup(608, ps)
    kernel = d[off:off + ks]; off += rup(ks, ps)
    ramdisk = d[off:off + rs]; off += rup(rs, ps)
    off += rup(ss, ps)
    dt = d[off:off + dt_size]
    return dict(ks=ks, ka=ka, rs=rs, ra=ra, ss=ss, sa=sa, ta=ta, ps=ps,
                kernel=kernel, ramdisk=ramdisk, dt=dt, dt_size=dt_size,
                os_ver=struct.unpack_from("<I", d, 44)[0], cmdline=d[64:576])


def main():
    src, outp = sys.argv[1], sys.argv[2]
    stock = split_bootimg(open(STOCK, "rb").read())

    blob = open(src, "rb").read()
    if blob[:8] == b"ANDROID!":
        # TWRP's own recovery.img: take its ramdisk (and cmdline)
        built = split_bootimg(blob)
        ramdisk, cmdline = built["ramdisk"], built["cmdline"]
        # Android 9 mkbootimg puts header_version (0) at offset 40, so no DT there
    else:
        ramdisk, cmdline = blob, stock["cmdline"]
    kernel = open(sys.argv[3], "rb").read() if len(sys.argv) > 3 else stock["kernel"]
    dt, dt_size, ps = stock["dt"], stock["dt_size"], stock["ps"]

    sha = hashlib.sha1()
    for b in (kernel, ramdisk, b"", dt):
        sha.update(b); sha.update(struct.pack("<I", len(b)))

    hdr = bytearray(ps)
    hdr[0:8] = b"ANDROID!"
    struct.pack_into("<8I", hdr, 8, len(kernel), stock["ka"], len(ramdisk),
                     stock["ra"], 0, stock["sa"], stock["ta"], ps)
    struct.pack_into("<I", hdr, 40, dt_size)
    struct.pack_into("<I", hdr, 44, stock["os_ver"])
    hdr[64:576] = cmdline
    hdr[576:576 + 20] = sha.digest()

    with open(outp, "wb") as o:
        o.write(hdr)
        o.write(kernel + b"\0" * (rup(len(kernel), ps) - len(kernel)))
        o.write(ramdisk + b"\0" * (rup(len(ramdisk), ps) - len(ramdisk)))
        o.write(dt)
    raw = os.path.getsize(outp)
    assert raw < PART_SIZE - 128 * 1024, "image too large for recovery partition"

    subprocess.check_call([sys.executable, AVBTOOL, "add_hash_footer", "--image", outp,
                           "--partition_size", str(PART_SIZE), "--partition_name", PART_NAME,
                           "--algorithm", "SHA256_RSA4096", "--key", AVBKEY])
    print("wrote %s: %d bytes (payload %d, kernel %d, ramdisk %d, dt %d)"
          % (outp, os.path.getsize(outp), raw, len(kernel), len(ramdisk), dt_size))


if __name__ == "__main__":
    main()
