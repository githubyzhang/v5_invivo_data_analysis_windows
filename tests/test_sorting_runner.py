import copy
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shank_input import ROOT,probe
from run_sorting import validate_geometry,read


class RunnerTests(unittest.TestCase):
    def test_reference_and_each_shank_geometry(self):
        for s in range(4):
            path=ROOT/('configs/pilot01/geometry/channel_map.csv' if s==0 else f'data/w14-extra4-inputs01/channel_map_shank{s}.csv')
            mapping=np.genfromtxt(path,delimiter=',',names=True,dtype=int)
            c=dict(binary_channels=512,shank_zero_based=s,excluded_binary_channels=[248] if s==0 else [])
            active=validate_geometry(c,probe(s),mapping)
            np.testing.assert_array_equal(active,np.delete(np.arange(512),c['excluded_binary_channels']))
            broken=copy.deepcopy(probe(s));broken['kcoords']=[s+1]*512
            with self.assertRaises(AssertionError):validate_geometry(c,broken,mapping)
            swapped=mapping.copy();swapped['original_channel_id'][[0,1]]=swapped['original_channel_id'][[1,0]]
            with self.assertRaises(AssertionError):validate_geometry(c,probe(s),swapped)
            c['excluded_binary_channels']=[512]
            with self.assertRaises(ValueError):validate_geometry(c,probe(s),mapping)

    def test_w15a_contract_does_not_inherit_exclusion(self):
        c=read(ROOT/'configs/extra4_shank1_w15a.json');old=read(ROOT/c['settings_reference'])
        self.assertEqual(c['excluded_binary_channels'],[])
        self.assertEqual(c['settings_overrides'],{})
        self.assertEqual(old['settings']['fs'],c['nominal_fs_hz'])
        self.assertEqual(c['shank_zero_based'],1)
        self.assertEqual(c['expected_versions'],old['versions'])


if __name__=='__main__':unittest.main()
