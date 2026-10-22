import struct, sys, os

img, outd = sys.argv[1], sys.argv[2]
os.makedirs(outd, exist_ok=True)
d = open(img, 'rb').read()
assert d[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, ta, ps = struct.unpack_from('<8I', d, 8)
print("kernel_size", ks, "ramdisk_size", rs, "second_size", ss, "page_size", ps)

def rup(n, p):
    return (n + p - 1) // p * p

off = rup(608, ps)  # header is 608 bytes then padded to page
k = d[off:off+ks]
open(os.path.join(outd, 'kernel'), 'wb').write(k)
off += rup(ks, ps)
r = d[off:off+rs]
open(os.path.join(outd, 'ramdisk.cpio.gz'), 'wb').write(r)
off += rup(rs, ps)
if ss:
    open(os.path.join(outd, 'second'), 'wb').write(d[off:off+ss])
print("wrote kernel + ramdisk to", outd)
