import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from analysis.pilot import moving_average, flat_mask, dilate, spaced_peaks, candidate_peaks, noise_scales


class PilotTests(unittest.TestCase):
    def test_moving_average_matches_legacy_even_and_odd(self):
        x = np.random.default_rng(4).normal(size=1500)
        for size in [1, 7, 200]:
            padded = np.pad(x,(size//2,size-1-size//2),mode='edge')
            ref = np.convolve(padded,np.ones(size)/size,mode='valid')
            np.testing.assert_allclose(moving_average(x,size),ref,atol=1e-14)

    def test_context_removes_artificial_window_boundary(self):
        x = np.arange(22000,dtype=float)
        ref = x-moving_average(x)
        # Adjacent processing blocks with adequate real context reproduce the whole.
        parts=[]
        for a,b in [(200,10000),(10000,21000)]:
            parts.append(x[a:b]-moving_average(x[a-100:b+100])[100:-100])
        np.testing.assert_allclose(np.concatenate(parts),ref[200:21000],atol=1e-10)

    def test_flat_runs_and_guard(self):
        x=np.r_[np.arange(20),np.full(10,50),np.arange(20)]
        mask=flat_mask(x)
        self.assertEqual(mask.sum(),10)
        expanded=dilate(mask,5)
        self.assertTrue(expanded[15:35].all())
        self.assertEqual(expanded.sum(),20)
        self.assertTrue(flat_mask(np.ones(100)).all())
        self.assertFalse(flat_mask(np.arange(100)).any())

    def test_global_spacing_across_windows_and_tail(self):
        y=np.zeros(10500)
        y[[9990,10010,10480]]=[-6,-8,-7]
        peaks,amp=candidate_peaks(y,np.ones(2))
        np.testing.assert_array_equal(peaks,[9990,10010,10480])
        keep=spaced_peaks(peaks,amp,50)
        np.testing.assert_array_equal(peaks[keep],[10010,10480])
        legacy,_=candidate_peaks(y,np.ones(2),windowed=True)
        np.testing.assert_array_equal(legacy,[9990])

    def test_mask_before_spacing_and_no_noise_estimate(self):
        y=np.zeros(10000)
        y[[100,120]]=[-100,-6]
        invalid=np.zeros(10000,dtype=bool)
        invalid[100]=True
        peaks,amp=candidate_peaks(y,np.ones(1),invalid)
        np.testing.assert_array_equal(peaks[spaced_peaks(peaks,amp,50)],[120])
        _,mad,good=noise_scales(y,np.ones(10000,dtype=bool),len(y))
        self.assertTrue(np.isnan(mad[0]))
        self.assertEqual(good[0],0)
        self.assertEqual(len(candidate_peaks(y,mad)[0]),0)


if __name__=='__main__':
    unittest.main()
