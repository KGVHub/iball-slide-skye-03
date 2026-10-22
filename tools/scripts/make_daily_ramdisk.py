#!/usr/bin/env python3
"""Restore normal init events for KGV-Pro-X GPU and BT/FM module loading.

Uses cpio_replace.py to preserve ramdisk ownership/modes. Does not flash.
Usage: make_daily_ramdisk.py test-ramdisk.cpio.gz output-ramdisk.cpio.gz
"""
import gzip
from pathlib import Path
import subprocess
import sys
import tempfile

from cpio_replace import entries

src, dst = map(Path, sys.argv[1:])
files = {n: b for n, _, _, b, _ in entries(gzip.decompress(src.read_bytes()))
         if n in {'init.common.rc', 'init.sp7731e_1h10.rc'}}
assert len(files) == 2
replacements = {}
for name, body in files.items():
    text = body.decode('utf-8')
    if name == 'init.common.rc':
        tail = ('# KGV test build: load the rebuilt GPU driver only after adbd is up, so a\n'
                '# driver problem cannot take adb (and the autodloader rescue) down with it.\n'
                'on property:init.svc.adbd=running\n'
                '    insmod /lib/modules/mali.ko\n')
        placeholder = '    # KGV test build: mali.ko is loaded once adbd runs (see below)'
        normal = ('    # KGV: load the validated GPU module independently of adbd.\n'
                  '    insmod /lib/modules/mali.ko')
    else:
        modules = ('    insmod /lib/modules/sprdbt_tty.ko\n'
                   '    insmod /lib/modules/sprd_fm.ko\n'
                   '    chmod 660 /sys/class/rfkill/rfkill0/state\n'
                   '    chmod 660 /sys/class/rfkill/rfkill0/type\n'
                   '    chown bluetooth net_bt_admin /sys/class/rfkill/rfkill0/state\n'
                   '    chown bluetooth net_bt_admin /sys/class/rfkill/rfkill0/type\n')
        tail = ('# KGV test build: load the rebuilt BT/FM drivers only after adbd is up, so a\n'
                '# driver problem cannot take adb (and the autodloader rescue) down with it.\n'
                'on property:init.svc.adbd=running\n' + modules)
        placeholder = '    # KGV test build: BT/FM modules and rfkill permissions moved below'
        normal = '    # KGV: restore validated modules to the original boot event.\n' + modules.rstrip('\n')
    assert text.count(tail) == 1, name
    assert text.count(placeholder) == 1, name
    text = text.replace(tail, '').replace(placeholder, normal)
    assert 'on property:init.svc.adbd=running' not in text
    replacements[name] = text.encode()
with tempfile.TemporaryDirectory(prefix='kgv-daily-ramdisk-') as temp:
    args = []
    for name, body in replacements.items():
        f = Path(temp)/name
        f.write_bytes(body)
        args.append(f'{name}={f}')
    subprocess.run([sys.executable, str(Path(__file__).with_name('cpio_replace.py')),
                    str(src), str(dst), *args], check=True)
old = {n: (h, b, f) for n, h, _, b, f in entries(gzip.decompress(src.read_bytes())) if n}
new = {n: (h, b, f) for n, h, _, b, f in entries(gzip.decompress(dst.read_bytes())) if n}
assert old.keys() == new.keys()
changed = []
for n, (h, b, f) in old.items():
    nh, nb, nf = new[n]
    # Only the newc filesize field may differ in entry metadata.
    assert h[:54] == nh[:54] and h[62:] == nh[62:], n
    if b != nb:
        changed.append(n)
assert set(changed) == set(replacements), changed
print('Verified: only the two init scripts changed; entry metadata and module bytes preserved.')
