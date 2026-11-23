import unittest
import numpy as np
from analysis.shared_artifacts import consensus,build_mask,intervals


class SharedFlagTests(unittest.TestCase):
    def test_same_sign_quorum_and_minimum_support(self):
        p=np.array([500,512,700,400]); n=np.array([500,0,0,700]); e=np.array([2048,1024,900,2048])
        np.testing.assert_array_equal(consensus(p,n,e,.5),[False,True,False,False])

    def test_half_open_intervals(self):
        self.assertEqual(intervals(np.array([1,1,0,1,0,1],bool)),[(0,2),(3,4),(5,6)])
        self.assertEqual(intervals(np.zeros(10,bool)),[])

    def test_baseline_covers_both_bins_and_guard(self):
        bp=np.array([0,0,1500,0,0]); zeros=np.zeros(5,int); be=np.full(5,2048)
        hp=np.zeros(50,int); he=np.full(50,2048)
        b,h=build_mask(bp,zeros,be,hp,hp,he,.5,5,500)
        self.assertEqual(intervals(b),[(50,350)])
        self.assertFalse(h.any())

    def test_broadband_guard_clips_edges_and_union_overlaps(self):
        hp=np.zeros(50,int); hp[[0,4,49]]=1500; he=np.full(50,2048)
        b,h=build_mask(np.zeros(5,int),np.zeros(5,int),np.full(5,2048),hp,np.zeros(50,int),he,.5,5,500)
        self.assertFalse(b.any())
        self.assertEqual(intervals(h),[(0,100),(440,500)])

    def test_more_stringent_quorum_and_larger_guard_are_monotonic(self):
        rng=np.random.default_rng(9); hp=rng.integers(0,2049,500); hn=np.zeros(500,int); he=np.full(500,2048)
        bp=rng.integers(0,2049,50); bn=np.zeros(50,int); be=np.full(50,2048)
        masks=[]
        for fraction in [.25,.5,.75]:
            b,h=build_mask(bp,bn,be,hp,hn,he,fraction,5,5000); masks.append(b|h)
        self.assertFalse((masks[2]&~masks[1]).any()); self.assertFalse((masks[1]&~masks[0]).any())
        b,h=build_mask(bp,bn,be,hp,hn,he,.5,20,5000)
        self.assertFalse((masks[1]&~(b|h)).any())


if __name__=='__main__': unittest.main()
