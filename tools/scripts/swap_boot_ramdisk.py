# Replace the ramdisk in a SPRD v0 boot image (header, kernel, DT kept).
import struct, sys, hashlib
src, rd, outp = sys.argv[1:4]
d = open(src, 'rb').read()
(ks, ka, rs, ra, ss, sa, ta, ps) = struct.unpack_from('<8I', d, 8)
dts = struct.unpack_from('<I', d, 40)[0]
rup = lambda n: (n + ps - 1) // ps * ps
off = rup(608); k = d[off:off+ks]; off += rup(ks); off += rup(rs); off += rup(ss)
dt = d[off:off+dts]
nr = open(rd, 'rb').read()
h = hashlib.sha1()
for blob in (k, nr, b''):
    h.update(blob); h.update(struct.pack('<I', len(blob)))
h.update(dt); h.update(struct.pack('<I', len(dt)))
hdr = bytearray(d[:608]); struct.pack_into('<I', hdr, 16, len(nr)); hdr[576:596] = h.digest()
pad = lambda b: b + b'\0' * (rup(len(b)) - len(b))
open(outp, 'wb').write(pad(bytes(hdr)) + pad(k) + pad(nr) + pad(dt))
print('ramdisk', rs, '->', len(nr))
