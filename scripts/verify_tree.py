"""Create or verify a SHA-256 inventory without changing the inspected tree."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f'Refusing a linked path: {path}')
        if path.is_file():
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            files[path.relative_to(root).as_posix()] = {
                'bytes': path.stat().st_size, 'sha256': digest}
            if len(files) % 10000 == 0:
                print(f'Hashed {len(files)} files', flush=True)
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['create', 'verify', 'verify-remaining'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    root, manifest = args.root.resolve(), args.manifest.resolve()
    if manifest.is_relative_to(root):
        raise ValueError('Manifest must be outside the inspected tree')
    files = inventory(root)
    if args.mode == 'create':
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open('x', encoding='utf-8') as stream:
            json.dump({'schema': 'preserved-tree-v1', 'source': str(root), 'files': files}, stream, indent=2)
    else:
        expected = json.loads(manifest.read_text(encoding='utf-8'))['files']
        # A partial move can leave a subset at the source, but no changed/new file.
        names = set(files) if args.mode == 'verify-remaining' else set(files) | set(expected)
        changed = [name for name in names if files.get(name) != expected.get(name)]
        if changed:
            raise ValueError(f'{len(changed)} mismatches: {changed[:20]}')
    print(json.dumps({'mode': args.mode, 'files': len(files),
                      'bytes': sum(x['bytes'] for x in files.values()), 'passed': True}))
