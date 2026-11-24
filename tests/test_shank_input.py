"""Mapping orientation and binary-layout failure cases for expansion preflight."""
import tempfile
import unittest
from pathlib import Path
import h5py
import numpy as np
from scripts.shank_input import channel_ids, check_binary, probe, ROOT


class ShankInputTests(unittest.TestCase):
    def test_full_mapping_and_pilot_agreement(self):
        ids = channel_ids()
        old = np.genfromtxt(ROOT/'configs/pilot01/geometry/channel_map.csv', delimiter=',', names=True, dtype=int)
        np.testing.assert_array_equal(ids[0], old['original_channel_id'])
        # Independently chosen endpoints straddle the legacy reversal at column 11.
        for gid, shank, pad in [(0,0,0),(4,0,1),(16,1,0),(32,2,0),(44,2,511),(48,3,508),(2047,3,3)]:
            self.assertEqual(ids[shank, pad], gid)
        for s in range(4):
            self.assertEqual(probe(s)['kcoords'], [s]*512)

    def test_exact_cast_channel_order_and_last_chunk(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            with h5py.File(folder/'source.h5', 'w') as f:
                values = (np.arange(2048)[:,None] % 100 + np.arange(7)[None,:]/8).astype('f2')
                ds = f.create_dataset('signals', data=values)
                for ids in channel_ids():
                    binary = folder/'data.bin'
                    values[ids].T.astype('<f4').tofile(binary)
                    self.assertEqual(check_binary(ds, binary, ids, 7, 3), 7*512)
                values[ids[::-1]].T.astype('<f4').tofile(binary)
                with self.assertRaises(AssertionError):
                    check_binary(ds, binary, ids, 7, 3)
                binary.write_bytes(b'bad')
                with self.assertRaises(ValueError):
                    check_binary(ds, binary, ids, 7)


if __name__ == '__main__':
    unittest.main()
