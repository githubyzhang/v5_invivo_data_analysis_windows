import unittest
from analysis.validate_frozen_guards import assert_disjoint


class IntervalSelectionTests(unittest.TestCase):
    def test_overlap_in_same_recording_rejected(self):
        old={'x':{'source':'/tmp/a.h5','sample_start':100,'sample_stop':200}}
        with self.assertRaises(ValueError): assert_disjoint([('/tmp/a.h5',150,250)],old)

    def test_touching_intervals_and_different_files_allowed(self):
        old={'x':{'source':'/tmp/a.h5','sample_start':100,'sample_stop':200}}
        assert_disjoint([('/tmp/a.h5',200,300),('/tmp/b.h5',150,250)],old)


if __name__=='__main__': unittest.main()
