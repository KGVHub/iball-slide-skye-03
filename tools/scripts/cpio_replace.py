#!/usr/bin/env python3
"""Replace files inside a gzip'd newc cpio ramdisk, keeping every other entry
(and the replaced entries' mode/owner/mtime) byte-for-byte.

usage: cpio_replace.py <in.cpio.gz> <out.cpio.gz> <path-in-archive>=<local file> ...
"""
import gzip, sys


def entries(data):
    off = 0
    while True:
        assert data[off:off + 6] == b"070701", "not a newc cpio at %d" % off
        hdr = data[off:off + 110]
        f = [int(hdr[6 + 8 * i:14 + 8 * i], 16) for i in range(13)]
        namesize, filesize = f[11], f[6]
        name = data[off + 110:off + 110 + namesize - 1].decode()
        dstart = (off + 110 + namesize + 3) & ~3
        dend = (dstart + filesize + 3) & ~3
        yield name, hdr, data[off + 110:dstart], data[dstart:dstart + filesize], f
        off = dend
        if name == "TRAILER!!!":
            # keep the block padding that follows the trailer
            yield None, data[off:], b"", b"", None
            return


def main():
    src, dst = sys.argv[1], sys.argv[2]
    repl = dict(a.split("=", 1) for a in sys.argv[3:])
    data = gzip.open(src).read()
    out, done = bytearray(), set()
    for name, hdr, namepad, body, f in entries(data):
        if name is None:
            out += hdr
            continue
        if name in repl:
            body = open(repl[name], "rb").read()
            hdr = hdr[:54] + b"%08X" % len(body) + hdr[62:]
            done.add(name)
        out += hdr + namepad
        out += body + b"\0" * (-len(body) % 4)
    missing = set(repl) - done
    assert not missing, "not found in archive: %s" % missing
    with gzip.open(dst, "wb", compresslevel=9) as o:
        o.write(out)
    print("replaced:", ", ".join(sorted(done)))


if __name__ == "__main__":
    main()
