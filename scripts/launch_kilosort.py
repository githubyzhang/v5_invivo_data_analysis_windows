"""Launch stock Kilosort GUI using local data and fresh exploration outputs.

Adapted from the preserved worker viewing/launch_kilosort.py (2026-11-21).
Importing this module does not open a window; main() does.
"""
from pathlib import Path
import datetime
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    cache = ROOT / 'viewing/kilosort-cache'
    os.environ['KILOSORT_LOCAL_DOWNLOADS_PATH'] = str(cache)
    os.environ['QT_API'] = 'pyqt6'
    from qtpy import QtCore
    from kilosort.io import load_probe
    from kilosort.gui.launch import launcher
    config_root = ROOT / 'configs/pilot01'
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.Format.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.Format.IniFormat,
                            QtCore.QSettings.Scope.UserScope,
                            str(ROOT / 'viewing/qt-config-local'))
    settings = QtCore.QSettings('Janelia', 'Kilosort4')
    if not settings.contains('monday_initialized'):
        config = json.loads((config_root / 'config.json').read_text())
        for key, value in config['settings'].items():
            settings.setValue(key, value)
        settings.setValue('data_dtype', 'float32')
        settings.setValue('probe_layout', load_probe(config_root / 'geometry/probe.json'))
        settings.setValue('probe_name', 'extra4_shank0.json')
        settings.setValue('auto_load', False)
        settings.setValue('monday_initialized', True)
    probe_dir = cache / 'probes'
    probe_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_root / 'geometry/probe.json', probe_dir / 'extra4_shank0.json')
    settings.setValue('results_dir', ROOT / 'viewing/gui_runs' /
                      datetime.datetime.now().strftime('exploration_%Y%m%d_%H%M%S_%f'))
    settings.sync()
    launcher(filename=str(ROOT / 'data/extra4_shank0_float32.bin'), skip_load=True)


if __name__ == '__main__':
    main()
