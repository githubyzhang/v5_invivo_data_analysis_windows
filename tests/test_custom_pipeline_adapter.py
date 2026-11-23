import unittest
import numpy as np
from scripts.annotate_kilosort_from_custom import membership
from scripts.run_custom_pipeline import checked_output, ROOT


class AdapterTests(unittest.TestCase):
    def test_half_open_mapping_does_not_assume_candidate_event_order(self):
        times=np.array([20,10,9,15,14,19,0,25])
        np.testing.assert_array_equal(membership(times,[[10,15],[20,25]]),[True,True,False,False,True,False,False,False])

    def test_empty_unavailable_and_overlapping_intervals(self):
        self.assertFalse(membership(np.array([1,2]),[]).any())
        with self.assertRaises(ValueError):membership(np.array([1]),[[0,3],[2,5]])

    def test_output_cannot_target_source_archive_or_existing_result(self):
        for name in ['worker_returns/new','results','data/new','custom_pipeline/new','results/custom_detector']:
            with self.assertRaises(ValueError):checked_output(ROOT/name,ROOT/'README.md')


if __name__=='__main__':unittest.main()
