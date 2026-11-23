"""Launch stock Kilosort GUI using local data and fresh exploration outputs.

Adapted from the preserved worker viewing/launch_kilosort.py (2026-11-21).
Importing this module does not open a window; main() does.
"""
from pathlib import Path
from contextlib import contextmanager
import datetime
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def local_qsettings(settings_file):
    """Scope Kilosort 4.1.7's two-string QSettings call to an explicit INI file.

    On Windows that overload uses NativeFormat even after setDefaultFormat.
    This adapter changes only settings storage, not installed upstream files.
    """
    from qtpy import QtCore
    original = QtCore.QSettings
    settings_file = Path(settings_file).resolve()
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    class ProjectSettings(original):
        def __init__(self, *args, **kwargs):
            if args == ('Janelia', 'Kilosort4') and not kwargs:
                super().__init__(str(settings_file), original.Format.IniFormat)
            else:
                super().__init__(*args, **kwargs)

    QtCore.QSettings = ProjectSettings
    try:
        yield ProjectSettings('Janelia', 'Kilosort4')
    finally:
        QtCore.QSettings = original


def main():
    cache = ROOT / 'viewing/kilosort-cache'
    os.environ['KILOSORT_LOCAL_DOWNLOADS_PATH'] = str(cache)
    os.environ['QT_API'] = 'pyqt6'
    from qtpy import QtCore
    from kilosort.gui.launch import launcher
    with local_qsettings(ROOT / 'viewing/qt-config-local/Kilosort4.ini') as settings:
        configure_settings(settings)
        settings.sync()
        if settings.status() != QtCore.QSettings.Status.NoError:
            raise RuntimeError(f'Cannot save GUI settings: {settings.fileName()}')
        launcher(filename=str(ROOT / 'data/extra4_shank0_float32.bin'), skip_load=True)


def configure_settings(settings):
    from kilosort.io import load_probe
    config_root = ROOT / 'configs/pilot01'
    if not settings.contains('monday_initialized'):
        config = json.loads((config_root / 'config.json').read_text())
        for key, value in config['settings'].items():
            settings.setValue(key, value)
        settings.setValue('data_dtype', 'float32')
        settings.setValue('probe_layout', load_probe(config_root / 'geometry/probe.json'))
        settings.setValue('probe_name', 'extra4_shank0.json')
        settings.setValue('auto_load', False)
        settings.setValue('monday_initialized', True)
    probe_dir = ROOT / 'viewing/kilosort-cache/probes'
    probe_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_root / 'geometry/probe.json', probe_dir / 'extra4_shank0.json')
    settings.setValue('results_dir', ROOT / 'viewing/gui_runs' /
                      datetime.datetime.now().strftime('exploration_%Y%m%d_%H%M%S_%f'))


if __name__ == '__main__':
    main()
