import unittest
import numpy as np
from analysis.focused_ma50_review import select_events

class ReviewSelectionTests(unittest.TestCase):
    def test_strata_and_no_duplicate_events(self):
        a=np.array([[0,100,6,5,0],[1,200,5.1,5,0],[2,300,20,5,0]],float)
        b=np.array([[0,102,6,5,0],[3,400,5.2,5,0],[4,500,30,5,0]],float)
        rows=select_events(a,b)
        self.assertEqual(len(rows),5)
        self.assertEqual(len({(r[2][0],r[2][1]) for r in rows}),5)
        self.assertEqual([(r[0],r[1]) for r in rows[:2]],[('fixed-only','near-threshold'),('fixed-only','large-amplitude')])
        self.assertEqual(rows[0][2][0],3);self.assertEqual(rows[1][2][0],4)
        self.assertEqual(sum(r[0]=='shared' for r in rows),1)

    def test_empty_groups(self):
        self.assertEqual(select_events(np.empty((0,5)),np.empty((0,5))),[])

if __name__=='__main__':unittest.main()
