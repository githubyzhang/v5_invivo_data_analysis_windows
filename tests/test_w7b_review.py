import unittest
import numpy as np
from scripts.review_w7b import matched_pairs


class EventMatching(unittest.TestCase):
    def test_endpoints_and_no_reuse(self):
        a=np.array([10,11,20,30]);b=np.array([12,18,33])
        np.testing.assert_array_equal(matched_pairs(a,b),[[0,0],[2,1]])
        self.assertEqual(matched_pairs([],[]).shape,(0,2))

    def test_maximum_count_against_dynamic_program(self):
        rng=np.random.default_rng(57)
        for _ in range(100):
            a=np.sort(rng.integers(0,30,12));b=np.sort(rng.integers(0,30,9))
            dp=np.zeros((len(a)+1,len(b)+1),int)
            for i in range(1,len(a)+1):
                for j in range(1,len(b)+1):
                    dp[i,j]=max(dp[i-1,j],dp[i,j-1],dp[i-1,j-1]+int(abs(a[i-1]-b[j-1])<=2))
            pairs=matched_pairs(a,b)
            self.assertEqual(len(pairs),dp[-1,-1])
            self.assertEqual(len(np.unique(pairs[:,0])),len(pairs))
            self.assertEqual(len(np.unique(pairs[:,1])),len(pairs))
            self.assertTrue(np.all(np.abs(a[pairs[:,0]]-b[pairs[:,1]])<=2))


if __name__=='__main__':
    unittest.main()
