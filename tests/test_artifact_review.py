"""Guard boundaries must remain sample-exact without creating exclusions."""
import unittest
import numpy as np
from scripts.review_pilot_artifacts import flat_intervals, expand_union
from analysis.pilot import flat_mask, dilate


class GuardBoundaries(unittest.TestCase):
    def test_run_threshold_and_recording_edges(self):
        values = np.r_[np.zeros(10), np.arange(1, 20), np.full(9, 30), np.full(10, 40)]
        np.testing.assert_array_equal(flat_intervals(values), [[0, 10], [38, 48]])
        np.testing.assert_array_equal(expand_union(flat_intervals(values), len(values), 2), [[0, 12], [36, 48]])

    def test_touching_guards_merge(self):
        np.testing.assert_array_equal(expand_union(np.array([[3, 5], [9, 11]]), 15, 2), [[1, 13]])
        self.assertEqual(expand_union(np.empty((0, 2), int), 15).shape, (0, 2))

    def test_matches_legacy_mask_on_quantized_random_traces(self):
        rng = np.random.default_rng(17)
        for _ in range(30):
            values = rng.integers(-3, 1, 400).astype(float)
            for start in rng.integers(0, 380, 10):
                values[start:start+int(rng.integers(1, 20))] = 0
            expected = dilate(flat_mask(values, min_run=10), 7)
            actual = np.zeros(len(values), bool)
            for a, b in expand_union(flat_intervals(values), len(values), 7):
                actual[a:b] = True
            np.testing.assert_array_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
