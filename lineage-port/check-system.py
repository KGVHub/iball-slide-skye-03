#!/usr/bin/env python3
"""Check image size, vendor DT_NEEDED presence, and split SELinux compilation.

This does not prove symbol ABI, linker namespace, or hardware compatibility.
"""
import argparse
import pathlib
import re
import struct
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--system', type=pathlib.Path, required=True)
p.add_argument('--vendor', type=pathlib.Path, required=True)
p.add_argument('--image', type=pathlib.Path)
p.add_argument('--secilc', type=pathlib.Path, required=True)
p.add_argument('--partition-size', type=int, default=1363148800)
a = p.parse_args()
for d in [a.system, a.vendor]:
    if not d.is_dir():
        p.error(f'not a directory: {d}')
failed = False
with (a.system/'bin/linker').open('rb') as f:
    header = f.read(20)
arm32 = (len(header) == 20 and header[:6] == b'\x7fELF\x01\x01'
         and struct.unpack_from('<H', header, 18)[0] == 40)
print(f'System linker is little-endian ARM32: {"PASS" if arm32 else "FAIL"}')
failed |= not arm32
if a.image:
    with a.image.open('rb') as f:
        h = f.read(28)
    if len(h) >= 28 and struct.unpack_from('<I', h)[0] == 0xed26ff3a:
        size = struct.unpack_from('<I', h, 12)[0] * struct.unpack_from('<I', h, 16)[0]
    else:
        size = a.image.stat().st_size
    print(f'Expanded image: {size} bytes; partition: {a.partition_size} bytes')
    if size > a.partition_size:
        failed = True

apks = list(a.system.rglob('*.apk'))
invalid_apks = []
for apk in apks:
    with apk.open('rb') as f:
        if f.read(4) != b'PK\x03\x04':
            invalid_apks.append(str(apk.relative_to(a.system)))
print(f'Installed APK payloads: {len(apks)}; invalid ZIP headers: {len(invalid_apks)}')
for apk in invalid_apks:
    print('  Invalid APK payload:', apk)
failed |= bool(invalid_apks) or not apks

available = {x.name for root in [a.system, a.vendor] for x in root.rglob('*.so') if x.is_file()}
missing = {}
count = 0
for base in [a.vendor / 'bin', a.vendor / 'lib']:
    for f in base.rglob('*'):
        if not f.is_file() or f.is_symlink():
            continue
        with f.open('rb') as src:
            if src.read(4) != b'\x7fELF':
                continue
        count += 1
        r = subprocess.run(['readelf', '-d', str(f)], check=True, capture_output=True, text=True)
        for dep in re.findall(r'\(NEEDED\).*?\[(.*?)\]', r.stdout):
            if dep not in available:
                missing.setdefault(dep, []).append(str(f.relative_to(a.vendor)))
print(f'Checked {count} vendor ELF files; missing library names: {len(missing)}')
for dep, users in sorted(missing.items()):
    print(f'  {dep}: {", ".join(users)}')
failed |= bool(missing)

# The stock 8.1 init drops any property value over 91 bytes (PROP_VALUE_MAX).
long_props = []
for prop_file in ('build.prop', 'etc/prop.default'):
    path = a.system / prop_file
    if path.is_file():
        for line in path.read_text(errors='replace').splitlines():
            key, sep, value = line.partition('=')
            if sep and not key.startswith('#') and len(value.encode()) > 91:
                long_props.append(f'{prop_file}: {key} ({len(value.encode())})')
print(f'Properties over 91 bytes: {len(long_props)}')
for item in long_props:
    print(f'  {item}')
failed |= bool(long_props)

policy = [a.system / 'etc/selinux/plat_sepolicy.cil',
          a.system / 'etc/selinux/mapping/27.0.cil',
          a.vendor / 'etc/selinux/nonplat_sepolicy.cil']
# The stock (iBall) init runs secilc without -m: duplicate statements fail.
secilc = [str(a.secilc.resolve()), '-M', 'true', '-G']
policy_args = ['-c', '30', *(str(x) for x in policy), '-f', '/dev/null']
with tempfile.TemporaryDirectory(prefix='kgv-policy-') as d:
    # init compiles with -N (no neverallow checks); that decides whether we boot.
    r = subprocess.run(secilc + ['-N'] + policy_args + ['-o', str(pathlib.Path(d)/'policy')])
    print(f'Split policy compilation as init does it (-N): {"PASS" if r.returncode == 0 else "FAIL"}')
    failed |= r.returncode != 0
    r = subprocess.run(secilc + policy_args + ['-o', str(pathlib.Path(d)/'strict')],
                       capture_output=True, text=True)
    n = r.stderr.count('neverallow check failed')
    print(f'Vendor neverallow conflicts (not enforced at boot): {n}' if r.returncode
          else 'Vendor neverallow conflicts: 0')
print('Presence/policy checks only: symbol ABI, namespaces, boot and hardware still require validation.')
raise SystemExit(1 if failed else 0)
