import unittest
import numpy as np
from analysis.compare_detectors import controlled_scales, match_indices, compare_events, METHODS, FILTERS


class ComparisonTests(unittest.TestCase):
    def test_both_estimators_exclude_same_invalid_values(self):
        x=np.tile([-1.,1.],5000)
        bad=np.zeros(10000,bool); bad[:1000]=True
        x[:1000]=1e8
        scales,common,counts=controlled_scales({f:x for f in FILTERS},bad)
        self.assertTrue(common[0]); self.assertEqual(counts[0],9000)
        for f in FILTERS:
            self.assertAlmostEqual(scales[f+'_rms'][0],1)
            self.assertAlmostEqual(scales[f+'_mad'][0],1/.67448975)

    def test_common_support_drops_all_methods_when_one_is_unusable(self):
        x=np.tile([-1.,1.],5000)
        ys={f:x for f in FILTERS}; ys['hp300']=np.zeros_like(x)
        scales,common,_=controlled_scales(ys,np.zeros(len(x),bool))
        self.assertFalse(common[0])
        self.assertTrue(all(np.isnan(s[0]) for s in scales.values()))

    def test_partial_window_and_exposure_requirement(self):
        x=np.tile([-1.,1.],5200)
        scales,common,counts=controlled_scales({f:x for f in FILTERS},np.zeros(len(x),bool))
        np.testing.assert_array_equal(counts,[10000,400])
        self.assertTrue(common.all())
        bad=np.zeros(len(x),bool); bad[10000:10200]=True
        _,common,counts=controlled_scales({f:x for f in FILTERS},bad)
        self.assertFalse(common[1]) # 200 good samples <250 required

    def test_matching_is_one_to_one_and_tolerance_is_inclusive(self):
        a,b=match_indices(np.array([10,11,30]),np.array([12,33]))
        np.testing.assert_array_equal(a,[0,2]); np.testing.assert_array_equal(b,[0,1])
        self.assertEqual(len(match_indices(np.array([10]),np.array([14]))[0]),0)

    def test_event_matching_never_crosses_channels(self):
        a=np.array([[0,100,1,1],[1,200,1,1]],float)
        b=np.array([[1,100,1,1],[1,203,1,1]],float)
        s=compare_events(a,b)
        self.assertEqual(s['matched_within_0_3ms'],1)
        self.assertEqual(s['a_only'],1)
        self.assertIsNone(compare_events(np.empty((0,4)),np.empty((0,4)))['jaccard'])


if __name__=='__main__': unittest.main()
