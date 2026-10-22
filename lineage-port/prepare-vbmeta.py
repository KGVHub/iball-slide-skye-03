#!/usr/bin/env python3
"""Prepare and verify a local DHTB-wrapped vbmeta trusting our system key."""
from pathlib import Path
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root/'tools/avb'))
import avbtool

def descriptors(path):
    data = path.read_bytes()
    assert data[:4] == b'DHTB'
    size = struct.unpack_from('<I', data, 48)[0]
    payload = data[512:512+size]
    assert hashlib.sha256(payload).digest() == data[8:40]
    h = avbtool.AvbVBMetaHeader(payload[:256])
    aux = payload[256+h.authentication_data_block_size:]
    d = avbtool.parse_descriptors(aux[h.descriptors_offset:h.descriptors_offset+h.descriptors_size])
    assert all(isinstance(x, avbtool.AvbChainPartitionDescriptor) for x in d)
    return {x.partition_name: x for x in d}, payload

src = root/'out/vbmeta-custom-KGV-v2.img'
dst = root/'out/vbmeta-lineage-system-KGV-v3.img'
tool = root/'tools/avb/avbtool.py'
key = root/'tools/avb/testkey_rsa4096.pem'
env = os.environ.copy()
env['OUR_PARTS'] = 'system'
subprocess.run([sys.executable, str(root/'tools/scripts/make_custom_vbmeta.py'), str(src), str(dst)], env=env, check=True)
old, _ = descriptors(src)
new, payload = descriptors(dst)
assert old.keys() == new.keys()
for name, d in old.items():
    assert d.rollback_index_location == new[name].rollback_index_location
    if name != 'system':
        assert d.public_key == new[name].public_key
with tempfile.TemporaryDirectory(prefix='kgv-vbmeta-') as tmp:
    tmp = Path(tmp)
    pub = tmp/'ours.avbpubkey'
    subprocess.run([sys.executable, str(tool), 'extract_public_key', '--key', str(key), '--output', str(pub)], check=True)
    assert new['system'].public_key == pub.read_bytes()
    assert new['boot'].public_key == pub.read_bytes()
    assert new['recovery'].public_key == pub.read_bytes()
    image = tmp/'vbmeta.img'
    image.write_bytes(payload)
    cmd = [sys.executable, str(tool), 'verify_image', '--image', str(image), '--key', str(key)]
    for name, d in new.items():
        f = tmp/(name+'.avbpubkey')
        f.write_bytes(d.public_key)
        cmd += ['--expected_chain_partition', f'{name}:{d.rollback_index_location}:{f}']
    subprocess.run(cmd, check=True)
print('Verified DHTB digest, root signature and all chains; only system trust changed.')
print('Prepared locally, not flashed:', dst)
