import contextlib
import io
import tempfile
import unittest
from pathlib import Path
import h5py
import numpy as np
from scipy.signal import find_peaks
from analysis.detect_recordings import detect,validate,window_scale,merge_intervals,main,run_pipeline
from analysis.pilot import flat_mask,dilate,spaced_peaks

class RecordingPipelineTests(unittest.TestCase):
    def test_explicit_filename_cli_and_fixed_source_provenance(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'arbitrary recording name.h5'
            x=np.random.default_rng(92).normal(size=(2,12000));x[:,3000]=-20
            with h5py.File(source,'w') as f:f['signals']=x
            with contextlib.redirect_stdout(io.StringIO()):
                main(['--input',str(source),'--output',str(root/'adaptive'),'--coincidence-min-channels','2'])
            self.assertTrue(validate(root/'adaptive/spikes.h5'))
            with h5py.File(root/'adaptive/spikes.h5','r') as f:
                self.assertIn(3000,f['spikes/sample_index'][:])
                self.assertFalse(f['spikes/shared_warning_available'][:].any())
            with h5py.File(root/'adaptive/coincidence/annotations.h5','r') as a,h5py.File(root/'adaptive/spikes.h5','r') as f:
                self.assertEqual(a.attrs['default_warning'],'broad')
                np.testing.assert_array_equal(a['events/sample_index'][:],f['spikes/sample_index'][:])
                self.assertTrue(a['warnings/broad/event_warning'][:].any())
            self.assertEqual(json.loads((root/'adaptive/pipeline_progress.json').read_text())['stage'],'complete')
            refs=root/'references';refs.mkdir();cal=refs/'any_calibration.npz'
            np.savez(cal,eligible=np.ones(2,bool),thresholds=np.full((3,2),7.))
            st=source.stat();protocol={'threshold_multiplier':5,'source_metadata':{'arbitrary':{
                'path':str(source),'size':st.st_size,'mtime_ns':st.st_mtime_ns}}}
            (root/'protocol.json').write_text(json.dumps(protocol))
            with contextlib.redirect_stdout(io.StringIO()):
                main(['--input',str(source),'--output',str(root/'fixed'),'--mode','fixed','--calibration',str(cal),'--coincidence-min-channels','2','--coincidence-warning','tight'])
            self.assertTrue(validate(root/'fixed/spikes.h5'))
            with h5py.File(root/'fixed/coincidence/annotations.h5','r') as f:self.assertEqual(f.attrs['default_warning'],'tight')
            protocol['source_metadata']['arbitrary']['mtime_ns']-=1
            (root/'protocol.json').write_text(json.dumps(protocol))
            with self.assertRaisesRegex(ValueError,'different or modified source'):
                main(['--input',str(source),'--output',str(root/'rejected'),'--mode','fixed','--calibration',str(cal),'--coincidence-min-channels','2','--coincidence-warning','tight'])
            self.assertFalse((root/'rejected').exists())

    def test_pipeline_annotation_failure_and_explicit_disable(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input.h5'
            with h5py.File(source,'w') as f:f['signals']=np.random.default_rng(9).normal(size=(2,1000))
            with self.assertRaises(ValueError):run_pipeline(source,root/'bad')
            self.assertFalse((root/'bad').exists())
            with patch('analysis.candidate_coincidence.run',side_effect=RuntimeError('simulated failure')):
                with self.assertRaises(RuntimeError):run_pipeline(source,root/'failed',coincidence_min_channels=2)
            self.assertTrue(validate(root/'failed/spikes.h5'))
            self.assertEqual(json.loads((root/'failed/pipeline_progress.json').read_text())['stage'],'annotation_failed')
            run_pipeline(source,root/'off',coincidence_warning='none')
            self.assertFalse((root/'off/coincidence').exists())
            self.assertEqual(json.loads((root/'off/pipeline_progress.json').read_text())['annotation'],'disabled')

    def test_cli_requires_explicit_source_and_calibration(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for argv in [[],['--output','unused'],['--input','x.h5','--output','unused','--mode','fixed'],
                         ['--input','x.h5','--recordings','4','--output','unused']]:
                with self.assertRaises(SystemExit):main(argv)

    def test_full_series_oracle_chunk_boundaries_and_partial_tail(self):
        rng=np.random.default_rng(81);x=rng.normal(0,1,(3,61537))
        x[0,9997]=-14;x[0,10007]=-22;x[0,61500]=-17
        x[1,8000:10500]=0;x[2,30000:30100]=0
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.h5'
            with h5py.File(source,'w') as f:f['signals']=x
            with contextlib.redirect_stdout(io.StringIO()):
                s=detect(source,root/'a',batch_channels=1,chunk_seconds=1,annotate_shared=False)
                detect(source,root/'b',batch_channels=2,chunk_seconds=5,annotate_shared=False)
            sigma=np.full((3,7),np.nan);bad=np.zeros_like(x,dtype=bool);ys=[]
            for ch in range(3):
                y=x[ch]-np.convolve(np.pad(x[ch],(25,24),mode='edge'),np.ones(50)/50,mode='valid');ys.append(y)
                bad[ch]=dilate(flat_mask(x[ch]),500);bad[ch,:25]=True;bad[ch,-24:]=True
                for w,a in enumerate(range(0,x.shape[1],10000)):
                    v=y[a:a+10000][~bad[ch,a:a+10000]]
                    if len(v)>=max(250,(len(y[a:a+10000])+1)//2):sigma[ch,w]=np.median(np.abs(v-np.median(v)))/.67448975
            floor=np.nanmedian(sigma,axis=0)
            with h5py.File(root/'a/spikes.h5','r') as a,h5py.File(root/'b/spikes.h5','r') as b:
                np.testing.assert_array_equal(a['spikes/sample_index'][:],b['spikes/sample_index'][:])
                np.testing.assert_array_equal(a['spikes/channel_id'][:],b['spikes/channel_id'][:])
                np.testing.assert_allclose(a['noise/mad'][:],sigma,atol=1e-12)
                for ch,y in enumerate(ys):
                    p=find_peaks(-y)[0];p=p[~bad[ch,p]]
                    th=5*np.maximum(sigma[ch,p//10000],floor[p//10000]);p=p[-y[p]>=th]
                    p=p[spaced_peaks(p,-y[p],50)]
                    rows=a['spikes/channel_id'][:]==ch
                    np.testing.assert_array_equal(a['spikes/sample_index'][:][rows],p)
                p=a['spikes/sample_index'][:][a['spikes/channel_id'][:]==0]
                self.assertIn(10007,p);self.assertNotIn(9997,p);self.assertIn(61500,p)
                self.assertEqual(a['quality/valid_noise_window'].shape,(3,7))
                self.assertFalse(a['spikes/shared_warning_available'][:].any())
            self.assertTrue(validate(root/'a/spikes.h5'));self.assertEqual(s['samples_per_channel'],61537)

    def test_fixed_mode_uses_constant_threshold_and_unavailable_channels(self):
        rng=np.random.default_rng(18);x=rng.normal(0,1,(2,20500));x[:,[100,10100,20200]]=-12
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with h5py.File(root/'source.h5','w') as f:f['signals']=x
            np.savez(root/'cal.npz',eligible=np.array([True,False]),thresholds=np.array([[7,np.nan],[8,np.nan],[9,np.nan]]))
            with contextlib.redirect_stdout(io.StringIO()):detect(root/'source.h5',root/'out',mode='fixed',calibration=root/'cal.npz',annotate_shared=False)
            with h5py.File(root/'out/spikes.h5','r') as f:
                self.assertTrue((f['spikes/channel_id'][:]==0).all());self.assertTrue((f['spikes/threshold'][:]==7).all())
                self.assertFalse(f['quality/valid_noise_window'][1].any());self.assertEqual(f['spikes/counts_per_channel'][1],0)
                self.assertIn(20200,f['spikes/sample_index'][:])

    def test_insufficient_tail_and_interval_merging(self):
        self.assertTrue(np.isnan(window_scale(np.arange(200.),np.zeros(200,bool))[0]))
        np.testing.assert_array_equal(merge_intervals([(10,20),(0,10),(30,35),(34,40)]),[[0,20],[30,40]])


class FlatRunEquivalenceTests(unittest.TestCase):
    def test_all_run_lengths_and_boundaries(self):
        lengths=np.array([1,9,10,11,2,35,8,10])
        x=np.repeat(np.arange(len(lengths),dtype=float),lengths)
        for minimum in [1,10,20,100]:
            np.testing.assert_array_equal(flat_mask(x,minimum),np.repeat(lengths>=minimum,lengths))
        self.assertEqual(len(flat_mask(np.array([]))),0)

if __name__=='__main__':unittest.main()
