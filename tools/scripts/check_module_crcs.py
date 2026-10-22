#!/usr/bin/env python3
"""Compare the symbol CRCs a prebuilt .ko expects (__versions) with a kernel's Module.symvers.
usage: check_module_crcs.py <Module.symvers> <module.ko>...
"""
import struct, sys

def versions(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'\x7fELF' and d[4] == 1, 'expect 32-bit ELF'
    shoff, = struct.unpack_from('<I', d, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x2e)
    secs = [struct.unpack_from('<IIIIIIIIII', d, shoff + i * shentsize) for i in range(shnum)]
    stroff = secs[shstrndx][4]
    for s in secs:
        name = d[stroff + s[0]:d.index(b'\0', stroff + s[0])].decode()
        if name == '__versions':
            off, size = s[4], s[5]
            for i in range(off, off + size, 64):
                crc, = struct.unpack_from('<I', d, i)
                sym = d[i + 4:i + 64].split(b'\0')[0].decode()
                yield sym, crc

symvers = {}
for line in open(sys.argv[1]):
    crc, sym = line.split()[:2]
    symvers[sym] = int(crc, 16)

bad = 0
for ko in sys.argv[2:]:
    syms = list(versions(ko))
    miss = [s for s, c in syms if s not in symvers and s != 'module_layout']
    diff = [s for s, c in syms if s in symvers and symvers[s] != c]
    bad += len(miss) + len(diff)
    print('%-14s %3d symbols  %3d CRC mismatch  %3d missing' % (ko.split('/')[-1], len(syms), len(diff), len(miss)))
    for s in diff[:15]: print('    crc  ', s)
    for s in miss[:15]: print('    miss ', s)
sys.exit(1 if bad else 0)
