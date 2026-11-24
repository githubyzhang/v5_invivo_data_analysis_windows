import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_sorting_runs import matches
from run_sorting import ROOT,read,validate_geometry


class ComparisonTests(unittest.TestCase):
    def test_matching_against_dynamic_programming(self):
        rng=np.random.default_rng(19)
        for _ in range(100):
            a=np.sort(rng.integers(0,30,size=rng.integers(0,15)))
            b=np.sort(rng.integers(0,30,size=rng.integers(0,15)))
            dp=np.zeros((len(a)+1,len(b)+1),int)
            for i,x in enumerate(a):
                for j,y in enumerate(b):
                    dp[i+1,j+1]=max(dp[i,j+1],dp[i+1,j],dp[i,j]+int(abs(x-y)<=2))
            pairs=matches(a,b)
            self.assertEqual(len(pairs),dp[-1,-1])
            self.assertEqual(len(np.unique(pairs[:,0])),len(pairs))
            self.assertEqual(len(np.unique(pairs[:,1])),len(pairs))
            self.assertTrue(np.all(np.abs(a[pairs[:,0]]-b[pairs[:,1]])<=2))

    def test_w15b_conditions(self):
        a,b=[read(ROOT/f'configs/extra4_shank2_w15b_{name}.json') for name in ['allchannels','exclude54-148']]
        allowed={'run_id','output_path','excluded_binary_channels'}
        self.assertEqual({k:v for k,v in a.items() if k not in allowed},{k:v for k,v in b.items() if k not in allowed})
        mapping=np.genfromtxt(ROOT/b['mapping_path'],delimiter=',',names=True,dtype=int)
        active=validate_geometry(b,read(ROOT/b['probe_path']),mapping)
        self.assertEqual(len(active),510)
        self.assertEqual(mapping['original_channel_id'][b['excluded_binary_channels']].tolist(),[872,353])


if __name__=='__main__':unittest.main()
