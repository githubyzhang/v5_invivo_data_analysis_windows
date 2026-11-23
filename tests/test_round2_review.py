"""Check lag orientation/endpoints and exact-run boundaries on synthetic data."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review_pilot_round2 import cross_lags, constant_runs, features, pca_projection


class Round2Algorithms(unittest.TestCase):
    def test_cross_lags_match_bruteforce_including_coincidence_and_endpoints(self):
        a=np.array([20,0,10]); b=np.array([30,10,11])
        brute=(b[:,None]-a).ravel();brute=brute[abs(brute)<=10]
        np.testing.assert_array_equal(np.sort(cross_lags(a,b,10)),np.sort(brute))
        self.assertEqual(cross_lags(np.array([],dtype=int),b).size,0)

    def test_runs_include_prefix_suffix_and_signed_zero(self):
        values=np.array([-0.,0.,0.,2.,2.,3.,4.,4.,4.])
        start,stop=constant_runs(values,3)
        np.testing.assert_array_equal(start,[0,6]);np.testing.assert_array_equal(stop,[3,9])

    def test_feature_alignment_uses_physical_channels(self):
        pc=np.arange(12).reshape(2,3,2)
        ids,values=features(pc,np.array([[9,4],[4,9]]),np.array([0,1]),0,np.array([4,9]))
        np.testing.assert_array_equal(ids,[0]);np.testing.assert_array_equal(values,[[1,0,3,2,5,4]])

    def test_pca_projection_preserves_full_rank_two_geometry(self):
        a=np.array([[0.,0.],[1.,0.],[0.,1.]]);b=a+5
        projected,center,axes,var=pca_projection([a,b])
        np.testing.assert_allclose(projected[0]@axes+center,a,atol=1e-12)
        self.assertAlmostEqual(float(var.sum()),1.)


if __name__=='__main__':unittest.main()
