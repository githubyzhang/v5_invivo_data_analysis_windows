import unittest
import tempfile,json
from pathlib import Path
import h5py
import numpy as np
from analysis.candidate_coincidence import sliding_counts, expand_windows, run, sha256
from analysis.detect_recordings import runs

class CoincidenceTests(unittest.TestCase):
    def test_matches_bruteforce_with_missing_support_and_duplicates(self):
        rng=np.random.default_rng(42)
        for width in (1,2,5,11):
            n=27;support=rng.random((6,n))>.15
            events=[rng.integers(0,n,15) for _ in range(6)]
            active,eligible=sliding_counts(events,[runs(x) for x in support],n,width)
            expected=[]
            for a in range(n-width+1):
                ok=support[:,a:a+width].all(axis=1)
                hit=np.array([np.any((t>=a)&(t<a+width)) for t in events])
                expected.append([(ok&hit).sum(),ok.sum()])
            np.testing.assert_array_equal(active,np.array(expected)[:,0])
            np.testing.assert_array_equal(eligible,np.array(expected)[:,1])
    def test_crosses_bin_boundary_and_counts_channel_once(self):
        # Events straddling a hypothetical 5-sample bin boundary are coincident.
        active,eligible=sliding_counts([[4,5],[6]],[[[0,12]],[[0,12]]],12,3)
        self.assertEqual(active[4],2)
        self.assertEqual(active[3],1)
        self.assertTrue(np.all(eligible==2))
    def test_partial_channel_not_counted_in_either_side(self):
        active,eligible=sliding_counts([[4],[4]],[[[0,10]],[[4,10]]],10,3)
        self.assertEqual((active[3],eligible[3]),(1,1))
        self.assertEqual((active[4],eligible[4]),(2,2))
    def test_half_open_edges_and_last_window(self):
        a,e=sliding_counts([[0,3,6]],[[[0,7]]],7,3)
        np.testing.assert_array_equal(a,[1,1,1,1,1])
        mask=expand_windows(np.array([False,True,False,False,True]),3,7)
        np.testing.assert_array_equal(mask,[False,True,True,True,True,True,True])
    def test_no_events_no_support(self):
        a,e=sliding_counts([[]],[[]],8,2)
        self.assertFalse(a.any());self.assertFalse(e.any())
        self.assertFalse(expand_windows(a>0,2,8).any())
    def test_reject_invalid_ranges(self):
        with self.assertRaises(ValueError):sliding_counts([[3]],[[[0,5],[4,7]]],8,2)
        with self.assertRaises(ValueError):sliding_counts([[8]],[[[0,8]]],8,2)
        with self.assertRaises(ValueError):sliding_counts([[]],[[]],8,9)

    def test_sidecar_roundtrip_preserves_input_and_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'events.h5';out=Path(tmp)/'annotations'
            n=1000;support=np.ones((3,n),bool)
            support[:,:2]=False;support[:,-1:]=False
            support[2,200:300]=False;support[0,500:510]=False
            valid=np.ones((3,10),bool);valid[2,2]=False
            cfg={'shape':[3,n],'noise_window_samples':100,'nominal_fs_hz':1000,
                 'physical_fs_hz':1008,'physical_edge_exclusion_samples':[2,1]}
            with h5py.File(path,'w') as f:
                f.attrs['complete']=True;f.attrs['config_json']=json.dumps(cfg)
                f.create_dataset('spikes/channel_id',data=[0,0,1])
                f.create_dataset('spikes/sample_index',data=[200,250,202])
                f.create_dataset('spikes/channel_offsets',data=[0,2,3,3])
                f.create_dataset('quality/valid_noise_window',data=valid)
                f.create_dataset('quality/reference_eligible',data=[True]*3)
                f.create_dataset('quality/flat_guard_intervals',data=[[0,500,510]])
                f.create_dataset('quality/usable_samples_per_channel_window',data=support.reshape(3,10,100).sum(axis=2))
                f.create_dataset('quality/shared_available_intervals',data=[[0,100]])
                f.create_dataset('quality/shared20_intervals',data=np.empty((0,2),int))
            before=sha256(path);summary=run(path,out,min_channels=2)
            self.assertEqual(before,sha256(path))
            self.assertEqual(summary['default_warning'],'broad')
            self.assertEqual(summary['primary'],'w5ms_q5')
            self.assertEqual(set(summary['variants']),{'w1ms_q5','w5ms_q5'})
            self.assertEqual(summary['variants']['w5ms_q5']['flagged_candidates'],3)
            with h5py.File(out/'annotations.h5','r') as f:
                self.assertTrue(f.attrs['complete'])
                self.assertEqual(f['warnings/default'].id,f['warnings/broad'].id)
                self.assertEqual(f['warnings/tight/event_available'].id,f['tracks/w1ms/event_available'].id)
                self.assertEqual(f['warnings/broad/event_warning'].id,f['variants/w5ms_q5/event_warning'].id)
                self.assertEqual(f['tracks/w5ms/active_channels'][200],2)
                self.assertEqual(f['tracks/w5ms/eligible_channels'][200],2)
                np.testing.assert_array_equal(f['events/sample_index'][:],[200,250,202])
            with self.assertRaises(FileExistsError):run(path,out,min_channels=2)
            tight=Path(tmp)/'tight'
            ts=run(path,tight,min_channels=2,profile='tight')
            self.assertEqual(ts['primary'],'w1ms_q5')
            with h5py.File(tight/'annotations.h5','r') as f,h5py.File(out/'annotations.h5','r') as g:
                self.assertEqual(f['warnings/default'].id,f['warnings/tight'].id)
                for key in ('w1ms_q5','w5ms_q5'):
                    np.testing.assert_array_equal(f[f'variants/{key}/event_warning'][:],g[f'variants/{key}/event_warning'][:])
            with self.assertRaises(ValueError):run(path,Path(tmp)/'conflict',profile='broad',widths_ms=(3,),fractions=(.05,))
            custom=Path(tmp)/'custom'
            result=run(path,custom,min_channels=2,widths_ms=(3,),fractions=(.25,.5))
            self.assertEqual(set(result['variants']),{'w3ms_q25','w3ms_q50'})
            self.assertIsNone(json.loads((custom/'protocol.json').read_text())['primary'])
            with h5py.File(custom/'annotations.h5','r') as f:
                self.assertEqual(f['tracks/w3ms'].attrs['width_samples'],3)
                self.assertEqual(f['tracks/w3ms/active_channels'][200],2)
            with self.assertRaises(ValueError):run(path,Path(tmp)/'bad',min_channels=2,widths_ms=())

if __name__=='__main__':unittest.main()
