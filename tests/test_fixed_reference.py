import unittest
import numpy as np
from analysis.fixed_reference_thresholds import calibrate

class FixedReferenceTests(unittest.TestCase):
    def test_stability_uses_unfloored_scales_and_requires_two_segments(self):
        x=np.ones((3,3,4,5));ok=np.ones((3,4,5),bool)
        x[2,:,1]=2;ok[1:,2]=False;x[:,:,3]=0
        _,_,_,count,stable,thr=calibrate(x,ok)
        np.testing.assert_array_equal(stable,[1,0,0,0])
        self.assertEqual(count[2],1)
        np.testing.assert_array_equal(thr[:,0],[5,5,5]);self.assertTrue(np.isnan(thr[:,1:]).all())

    def test_rejected_reference_values_do_not_change_calibration(self):
        x=np.ones((3,3,2,5));ok=np.ones((3,2,5),bool);ok[0,:,0]=False
        x[0,:,:,0]=1e8
        _,est,_,_,stable,thr=calibrate(x,ok)
        self.assertTrue(stable.all());np.testing.assert_array_equal(est,np.ones((3,2)))
        np.testing.assert_array_equal(thr,np.full((3,2),5))

    def test_empty_reference_is_unavailable_not_zero_threshold(self):
        x=np.ones((3,3,2,5));ok=np.zeros((3,2,5),bool)
        *_,stable,thr=calibrate(x,ok)
        self.assertFalse(stable.any());self.assertTrue(np.isnan(thr).all())

if __name__=='__main__':unittest.main()
