import unittest
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_sorting import ROOT,read,validate_geometry
from review_w15c_shared import masks_from_flat


class W15CTests(unittest.TestCase):
    def test_matched_conditions_and_geometry(self):
        a,b=[read(ROOT/f'configs/extra4_shank3_w15c_{name}.json') for name in ['allchannels','exclude259']]
        different={'run_id','output_path','excluded_binary_channels'}
        self.assertEqual({k:v for k,v in a.items() if k not in different},{k:v for k,v in b.items() if k not in different})
        self.assertTrue(a['save_preprocessed_copy']);self.assertEqual(a['excluded_binary_channels'],[])
        m=np.genfromtxt(ROOT/b['mapping_path'],delimiter=',',names=True,dtype=int)
        active=validate_geometry(b,read(ROOT/b['probe_path']),m)
        self.assertEqual(len(active),511);self.assertEqual(m['original_channel_id'][259],2045)

    def test_fixed_threshold_and_clipped_shoulder_union(self):
        flat=np.array([[3,ch,ch,100,200,0] for ch in range(256)]+[[3,ch,ch,900,950,0] for ch in range(255)],float)
        concurrency,zones=masks_from_flat(flat,1000)
        self.assertEqual(zones['core'].sum(),100)
        self.assertEqual(zones['shoulder'].sum(),600)
        self.assertEqual(zones['away'].sum(),300)
        np.testing.assert_array_equal(zones['core']|zones['shoulder']|zones['away'],np.ones(1000,bool))
        self.assertFalse(np.any(zones['core']&zones['shoulder']))
        self.assertEqual(concurrency[900],255)


if __name__=='__main__':unittest.main()
