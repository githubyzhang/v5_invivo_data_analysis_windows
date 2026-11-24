import tempfile
import sys
from pathlib import Path
import unittest
import h5py
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_w14_inputs import export
from shank_input import sha,channel_ids


class ExportTests(unittest.TestCase):
    def test_all_shanks_exact_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=d/'source.h5'
            values=(np.arange(2048)[:,None]+np.arange(23)[None,:]/32).astype('f2')
            with h5py.File(source,'w') as f:f['signals']=values
            digest=sha(source);dest=d/'export'
            result=export(source,digest,dest,(0,1,2,3),23,7)
            for s,ids in enumerate(channel_ids()):
                raw=np.fromfile(dest/result[str(s)]['binary'],dtype='<f4').reshape(23,512)
                np.testing.assert_array_equal(raw,values[ids].T)
            self.assertEqual(sha(source),digest)
            with self.assertRaises(ValueError):export(source,digest,dest,(1,),23)
            with self.assertRaises(ValueError):export(source,'bad',d/'bad',(1,),23)
            self.assertFalse((d/'bad').exists())


if __name__=='__main__':unittest.main()
