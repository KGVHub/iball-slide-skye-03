#!/usr/bin/env python3
"""Compare strong vendor ELF imports with available dependency exports.

Use the stock system as a JSON baseline, then compare the built system with
--baseline. This is a diagnostic approximation, not a linker namespace test.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--system', type=Path, required=True)
p.add_argument('--vendor', type=Path, required=True)
p.add_argument('--json', type=Path, required=True)
p.add_argument('--baseline', type=Path)
a = p.parse_args()
cache = {}

def elf(path):
    if path in cache:
        return cache[path]
    with path.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            cache[path] = None
            return None
    out = subprocess.run(['readelf', '--dyn-syms', '--wide', '-d', str(path)],
                         capture_output=True, text=True, check=True).stdout
    needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', out)
    exports, imports = set(), set()
    for line in out.splitlines():
        c = line.split()
        if len(c) < 8 or not c[0].endswith(':') or not c[0][:-1].isdigit():
            continue
        name = c[7].split('@')[0]
        if c[6] == 'UND' and c[4] == 'GLOBAL':
            imports.add(name)
        elif c[6] != 'UND' and c[4] in {'GLOBAL', 'WEAK'} and c[5] in {'DEFAULT', 'PROTECTED'}:
            exports.add(name)
    cache[path] = needed, exports, imports
    return cache[path]

# Model vendor-first lookup; prefer root lib/ over its subdirectories.
providers = {}
for root in [a.system/'lib', a.vendor/'lib']:
    paths = sorted(root.rglob('*.so'), key=lambda x: (-len(x.parts), str(x)))
    for path in paths:
        if path.is_file():
            providers[path.name] = path
linker = a.system/'bin/linker'
linker_exports = elf(linker)[1] if linker.is_file() else set()
missing = {}
count = 0
for root in [a.vendor/'lib', a.vendor/'bin']:
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        info = elf(path)
        if info is None:
            continue
        count += 1
        exports = set(linker_exports)
        visited = set()
        pending = collections.deque([path])
        while pending:
            item = pending.popleft()
            if item in visited:
                continue
            visited.add(item)
            deps = elf(item)
            if deps is None:
                continue
            exports.update(deps[1])
            pending.extend(providers[n] for n in deps[0] if n in providers)
        absent = sorted(info[2] - exports)
        if absent:
            missing[str(path.relative_to(a.vendor))] = absent
baseline = json.loads(a.baseline.read_text()) if a.baseline else {}
regressions = {name: sorted(set(names)-set(baseline.get(name, [])))
               for name, names in missing.items()}
regressions = {k: v for k, v in regressions.items() if v}
a.json.write_text(json.dumps(missing, indent=2, sort_keys=True)+'\n')
print(f'Checked {count} vendor ELFs. Importers with unresolved strong symbols: {len(missing)}')
print(f'Importers with new unresolved symbols versus baseline: {len(regressions)}')
for name, symbols in sorted(regressions.items()):
    print(name+': '+', '.join(symbols))
print('Diagnostic only: runtime dlopen, versioning, and actual linker namespaces remain untested.')
raise SystemExit(1 if a.baseline and regressions else 0)
