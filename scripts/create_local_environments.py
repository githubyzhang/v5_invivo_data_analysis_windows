"""Rebuild Windows venv launchers around preserved installed packages, offline.

The source worker is read only. All destination environments must be new.
Package distributions are copied, not re-resolved from a package index.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


REBUILD_ENTRY_POINTS = r'''
import importlib.metadata
import json
from pathlib import Path
import sys
from pip._vendor.distlib.scripts import ScriptMaker
site = Path(sys.prefix) / 'Lib/site-packages'
maker = ScriptMaker(None, str(Path(sys.prefix) / 'Scripts'))
maker.executable = sys.executable
maker.clobber = True
maker.variants = {''}
count = 0
for dist in importlib.metadata.distributions(path=[str(site)]):
    for entry in dist.entry_points:
        if entry.group in ('console_scripts', 'gui_scripts'):
            maker.make(f'{entry.name} = {entry.value}', options={'gui': entry.group == 'gui_scripts'})
            count += 1
maker.make(f'pip{sys.version_info.major}.{sys.version_info.minor} = pip._internal.cli.main:main')
print(json.dumps({'environment': sys.prefix, 'entry_points_rebuilt': count}))
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path, required=True)
    args = parser.parse_args()
    worker = args.worker.resolve()
    root = Path(__file__).resolve().parents[1]
    names = ['.python', '.venv', '.venv-gui', '.venv-phy']
    locks = {'.venv': worker / 'environment-lock.txt',
             '.venv-gui': worker / 'viewing/setup/kilosort-gui-lock.txt',
             '.venv-phy': worker / 'viewing/setup/phy-lock.txt'}
    if any((root / name).exists() for name in names):
        raise ValueError('Destination runtime/environments must not exist')
    if not all((worker / name).is_dir() for name in names):
        raise ValueError('Missing source runtime/environment')
    if not all(path.is_file() for path in locks.values()):
        raise ValueError('Missing frozen source dependency locks')
    shutil.copytree(worker / '.python', root / '.python')
    base = root / '.python/python.exe'
    subprocess.run([str(base), '-B', '-c', REBUILD_ENTRY_POINTS], check=True)
    for name in names[1:]:
        target = root / name
        subprocess.run([str(base), '-B', '-m', 'venv', '--without-pip', str(target)], check=True)
        shutil.copytree(worker / name / 'Lib/site-packages', target / 'Lib/site-packages', dirs_exist_ok=True)
        if name == '.venv-gui':
            # Preserve the original split Qt6/pilot dependency design, now entirely local.
            (target / 'Lib/site-packages/pilot_dependencies.pth').write_text(
                str(root / '.venv/Lib/site-packages') + '\n', encoding='utf-8')
        python = target / 'Scripts/python.exe'
        subprocess.run([str(python), '-B', '-c', REBUILD_ENTRY_POINTS], check=True)
        subprocess.run([str(python), '-B', '-m', 'pip', 'check'], check=True)
        # Archived source environments retain historical paths and must not be run.
        before = locks[name].read_text(encoding='utf-8-sig')
        after = subprocess.check_output([str(python), '-B', '-m', 'pip', 'freeze'], text=True)
        if sorted(before.splitlines()) != sorted(after.splitlines()):
            raise ValueError(f'Installed dependency list changed for {name}')
        print(json.dumps({'environment': name, 'dependency_lock_unchanged': True}), flush=True)
