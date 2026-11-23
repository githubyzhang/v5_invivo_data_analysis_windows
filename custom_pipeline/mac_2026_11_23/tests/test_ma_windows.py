import unittest
import numpy as np
from analysis.compare_ma_windows import ma_residuals
from analysis.compare_detectors import controlled_scales

class MAWindowTests(unittest.TestCase):
    def test_all_widths_match_explicit_legacy_alignment(self):
        x=np.random.default_rng(7).normal(size=1003)
        for name,y in ma_residuals(x).items():
            k=int(name[2:]);expected=x-np.convolve(np.pad(x,(k//2,k//2-1),mode='edge'),np.ones(k)/k,mode='valid')
            np.testing.assert_allclose(y,expected,atol=1e-14)

    def test_new_filter_participates_in_common_support(self):
        x=np.tile([-1.,1.],5000)
        ys={'ma50':np.zeros_like(x),'ma100':x,'ma200':x}
        scales,common,_=controlled_scales(ys,np.zeros(len(x),bool))
        self.assertEqual(set(scales),{f'ma{k}_{est}' for k in [50,100,200] for est in ['rms','mad']})
        self.assertFalse(common.any());self.assertTrue(all(np.isnan(v).all() for v in scales.values()))

if __name__=='__main__':unittest.main()
