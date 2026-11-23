import unittest
import numpy as np
from analysis.local_artifact_review import sustained, channel_flags

class LocalWarningTests(unittest.TestCase):
    def test_sustained_keeps_runs_not_isolated_bins(self):
        np.testing.assert_array_equal(sustained(np.array([1,0,1,1,0,1],bool)),[0,0,1,1,0,0])

    def test_fast_requires_duration_and_eligible_bins(self):
        scale=np.array([1,8,8,1,9,1.]); valid=np.ones(6,bool)
        flags=channel_flags(scale,np.zeros(6),valid,1,1)
        self.assertEqual(np.flatnonzero(flags['fast']).tolist(),list(range(400)))
        valid[2]=False
        self.assertFalse(channel_flags(scale,np.zeros(6),valid,1,1)['fast'].any())

    def test_step_covers_both_bins_with_guard_without_other_channels(self):
        f=channel_flags(np.ones(8),np.array([0,0,0,10,10,10,10,10]),np.ones(8,bool),1,1)
        self.assertEqual(np.flatnonzero(f['step']).tolist(),list(range(100,500)))
        clean=channel_flags(np.ones(8),np.zeros(8),np.ones(8,bool),1,1)
        self.assertFalse(any(m.any() for m in clean.values()))

    def test_unavailable_reference_cannot_flag_and_collapse_is_separate(self):
        f=channel_flags(np.zeros(5),np.arange(5)*100,np.ones(5,bool),np.nan,np.nan)
        self.assertFalse(any(m.any() for m in f.values()))
        f=channel_flags(np.zeros(5),np.zeros(5),np.ones(5,bool),1,1)
        self.assertTrue(f['low_variability'].all())
        self.assertFalse(f['fast'].any())

if __name__=='__main__': unittest.main()
