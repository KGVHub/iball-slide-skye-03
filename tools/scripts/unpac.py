import struct, sys, os

pac_path, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

def u16str(b):
    return b.decode('utf-16-le', 'replace').split('\x00', 1)[0]

f = open(pac_path, 'rb')
hdr = f.read(1084)
# PacHeader offsets (little-endian) from pacextractor.c struct
partitionCount, = struct.unpack_from('<i', hdr, 1076)
partitionsListStart, = struct.unpack_from('<i', hdr, 1080)
firmwareName = u16str(hdr[564:564+512])
print("Firmware name:", firmwareName)
print("Partition count:", partitionCount, "list@", partitionsListStart)

parts = []
cur = partitionsListStart
for i in range(partitionCount):
    f.seek(cur)
    length, = struct.unpack('<I', f.read(4))
    f.seek(cur)
    rec = f.read(length)
    cur += length
    partitionName = u16str(rec[4:4+512])
    fileName = u16str(rec[516:516+1024])
    partitionSize, = struct.unpack_from('<I', rec, 1540)
    partitionAddrInPac, = struct.unpack_from('<I', rec, 1552)
    parts.append((partitionName, fileName, partitionSize, partitionAddrInPac))
    print(f"  [{i:2}] {partitionName:16} file={fileName:30} size={partitionSize:>12} off={partitionAddrInPac}")

print("\nExtracting...")
for partitionName, fileName, size, off in parts:
    if size == 0 or not fileName:
        continue
    safe = os.path.basename(fileName) or (partitionName + '.img')
    outp = os.path.join(out_dir, safe)
    f.seek(off)
    left = size
    with open(outp, 'wb') as o:
        while left:
            chunk = f.read(min(left, 8 << 20))
            if not chunk:
                print("  !! short read on", safe); break
            o.write(chunk); left -= len(chunk)
    print(f"  -> {safe} ({size} bytes)")
f.close()
print("Done.")
