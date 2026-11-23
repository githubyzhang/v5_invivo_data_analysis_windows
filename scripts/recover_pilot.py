"""Verify the frozen Windows return, then recover it without modifying the worker."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

ARCHIVE_SHA = '087ba85cb9c195a9e1b401b8dc0f46d1969537e0f728addde33a72cc0f4df73d'
BINARY_SHA = '11cd033eb0bda858f7598123a795f198078cc227d98d92543e8ea88f9e12eff0'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def recover(worker, destination):
    worker, destination = worker.resolve(), destination.resolve()
    if destination == worker or worker in destination.parents or destination.exists():
        raise ValueError('Choose a new destination outside the preserved worker.')
    archive = worker / 'extra4_shank0_pilot01_return.zip'
    binary = worker / 'data/extra4_shank0_float32.bin'
    if digest(archive) != ARCHIVE_SHA:
        raise ValueError('Return archive checksum mismatch')
    if binary.stat().st_size != 6144000000 or digest(binary) != BINARY_SHA:
        raise ValueError('Input binary identity mismatch')
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('return-manifest.json'))
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        files = {n for n in names if not n.endswith('/')}
        if files != set(manifest['files']) | {'return-manifest.json'}:
            raise ValueError('Archive membership differs from manifest')
        for name, entry in manifest['files'].items():
            target = (destination / 'received' / name).resolve()
            if not target.is_relative_to(destination / 'received'):
                raise ValueError('Unsafe archive path')
            payload = z.read(name)
            if len(payload) != entry['bytes'] or hashlib.sha256(payload).hexdigest() != entry['sha256']:
                raise ValueError(f'Payload mismatch: {name}')
        destination.mkdir(parents=True)
        z.extractall(destination / 'received')
    shutil.copy2(archive, destination / archive.name)
    report = dict(schema='windows-pilot-recovery-v1', worker=str(worker),
                  archive_sha256=ARCHIVE_SHA, binary_path=str(binary), binary_sha256=BINARY_SHA,
                  binary_bytes=binary.stat().st_size, verified_payload_files=len(manifest['files']),
                  recovered_to=str(destination / 'received'), python=sys.executable,
                  python_version=platform.python_version(), original_worker_modified=False)
    (destination / 'recovery.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    recover(args.worker, args.destination)
