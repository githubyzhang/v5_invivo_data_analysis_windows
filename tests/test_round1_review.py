"""Small algorithm checks; raw-data integration is a separate explicit audit."""
import unittest
import numpy as np
from scripts.review_pilot_round1 import acg_samples, selection


class Round1Algorithms(unittest.TestCase):
    def test_acg_is_symmetric_excludes_self_and_keeps_radius_endpoint(self):
        actual=np.sort(acg_samples(np.array([20,0,10]),radius=10))
        np.testing.assert_array_equal(actual,[-10,-10,10,10])

    def test_acg_does_not_invent_pairs_for_single_event(self):
        self.assertEqual(acg_samples(np.array([2])).size,0)

    def test_selection_preserves_endpoints_order_and_small_populations(self):
        events=np.arange(9)*7
        np.testing.assert_array_equal(selection(events,3),[0,28,56])
        np.testing.assert_array_equal(selection(events,20),events)
        self.assertEqual(selection(np.array([],dtype=int),20).size,0)


if __name__=='__main__':
    unittest.main()
