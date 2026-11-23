"""Exercise Kilosort's FAISS call, CUDA and optional Qt imports without sorting."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, help='Isolated candidate site-packages')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a fresh validation output')
    if args.candidate:
        sys.path.insert(0, str(args.candidate.resolve()))
    root = Path(__file__).resolve().parents[1]
    os.environ['KILOSORT_LOCAL_DOWNLOADS_PATH'] = str(root / 'viewing/kilosort-cache')
    import faiss
    import kilosort
    import numpy as np
    import torch
    from kilosort.clustering_qr import neigh_mat

    rng = np.random.default_rng(20261122)
    features = rng.normal(size=(128, 12)).astype(np.float32)
    distances = np.sum((features[:, None] - features[None, :]) ** 2, axis=2)
    expected = np.argsort(distances, axis=1)[:, :8]
    index = faiss.IndexFlatL2(features.shape[1])
    index.add(features)
    measured_distances, measured = index.search(features, 8)
    np.testing.assert_array_equal(measured, expected)
    np.testing.assert_allclose(measured_distances, np.take_along_axis(distances, expected, axis=1), atol=1e-5)
    neighbors, graph = neigh_mat(features, n_neigh=8)
    np.testing.assert_array_equal(neighbors, expected)
    assert graph.shape == (128, 128) and np.all(graph.diagonal() == 0)

    tensor = torch.as_tensor(features, device='cuda')
    product = tensor @ tensor.T
    torch.cuda.synchronize()
    torch.testing.assert_close(product.cpu(), torch.from_numpy(features) @ torch.from_numpy(features).T)
    result = dict(python=sys.executable, faiss_version=faiss.__version__,
                  faiss_path=faiss.__file__, kilosort_version=kilosort.__version__,
                  torch_version=torch.__version__, gpu=torch.cuda.get_device_name(),
                  nearest_neighbors_match_numpy=True, kilosort_neighbor_graph_passed=True,
                  cuda_passed=True, sorting_performed=False)
    if args.gui:
        os.environ['QT_API'] = 'pyqt6'
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from qtpy import QtCore, QtWidgets
        from kilosort.gui.launch import launcher
        from kilosort.gui import KilosortGUI
        from launch_kilosort import local_qsettings, configure_settings
        assert callable(launcher)
        result['qt_version'] = QtCore.qVersion()
        result['kilosort_gui_import_passed'] = True
        app = QtWidgets.QApplication([])
        original = QtCore.QSettings
        with local_qsettings(args.output.with_suffix('.ini')) as settings:
            configure_settings(settings)
            settings.sync()
            assert settings.status() == original.Status.NoError
            window = KilosortGUI(app, filename=str(root / 'data/extra4_shank0_float32.bin'), skip_load=True)
            assert Path(window.qt_settings.fileName()) == args.output.with_suffix('.ini').resolve()
            assert window.results_directory.is_relative_to(root / 'viewing/gui_runs')
            app.processEvents()
            window.close()
            app.processEvents()
        assert QtCore.QSettings is original
        result['gui_constructed_offscreen'] = True
        result['project_local_settings_verified'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
