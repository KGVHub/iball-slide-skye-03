import struct, sys, hashlib, os

stock = "/home/kgvarunkanth/claude/firmware/unpacked/recovery.img"
zimg  = "/home/kgvarunkanth/claude/kernel/arch/arm/boot/Image"
outp  = "/home/kgvarunkanth/claude/out/recovery-KGV.img"
os.makedirs(os.path.dirname(outp), exist_ok=True)

d = open(stock, "rb").read()
assert d[:8] == b"ANDROID!"
(ks, ka, rs, ra, ss, sa, ta, ps) = struct.unpack_from("<8I", d, 8)
dt_size = struct.unpack_from("<I", d, 40)[0]   # SPRD appended-DT size (page-padded)
os_ver  = struct.unpack_from("<I", d, 44)[0]
name    = d[48:48+16]
cmdline = d[64:64+512]
extra   = d[576+32:608]  # trailing header bytes after id (extra_cmdline area start)

def rup(n, p): return (n + p - 1) // p * p

hdr_pages = rup(608, ps)
off = hdr_pages
stock_kernel  = d[off:off+ks];            off += rup(ks, ps)
stock_ramdisk = d[off:off+rs];            off += rup(rs, ps)
off += rup(ss, ps)                        # second (0)
stock_dt      = d[off:off+dt_size]        # SPRD DT image region

new_kernel = open(zimg, "rb").read()
print("stock kernel", ks, "-> new", len(new_kernel))
print("ramdisk", rs, "dt", dt_size, "(reused)")

nks = len(new_kernel)
# recompute id (SHA1 over sections+sizes, AOSP scheme incl. dt as the 4th section)
sha = hashlib.sha1()
for blob, sz in ((new_kernel, nks), (stock_ramdisk, rs), (b"", ss), (stock_dt, dt_size)):
    sha.update(blob); sha.update(struct.pack("<I", sz))
img_id = sha.digest() + b"\x00"*(32-20)

hdr = bytearray(ps)
hdr[0:8] = b"ANDROID!"
struct.pack_into("<8I", hdr, 8, nks, ka, rs, ra, ss, sa, ta, ps)
struct.pack_into("<I", hdr, 40, dt_size)
struct.pack_into("<I", hdr, 44, os_ver)
hdr[48:48+16]   = name
hdr[64:64+512]  = cmdline
hdr[576:576+32] = img_id

with open(outp, "wb") as o:
    o.write(hdr)
    o.write(new_kernel + b"\x00"*(rup(nks, ps)-nks))
    o.write(stock_ramdisk + b"\x00"*(rup(rs, ps)-rs))
    o.write(stock_dt)      # already page-padded
print("wrote", outp, os.path.getsize(outp), "bytes")
