import numpy as np
import pytest
from flyrendezvous.recording import save_episode

def data():
    # Explicit unit-test fixture only, never used by run.py or the viewer.
    return dict(images=np.zeros((2,4,4)), receptor_input=np.zeros((2,3)),
                input_time=np.array([0.,.01]), response_time=np.array([.01,.02]),
                activity=np.array([[1.,2.],[3.,4.]]), baseline=np.zeros(2),
                cell_index=np.arange(2), cell_type=np.array(["A","B"]),
                u=np.array([0,1]),v=np.array([0,0]),
                receptor_u=np.array([0,1,2]),receptor_v=np.zeros(3,dtype=int),
                wall_seconds=np.array([.1,.2]))

def test_roundtrip_without_pickle(tmp_path):
    path=tmp_path/"record.npz"
    d=data()
    save_episode(path, **d)
    with np.load(path,allow_pickle=False) as loaded:
        for key in d:
            np.testing.assert_array_equal(loaded[key],d[key])

def test_nonfinite_rejected(tmp_path):
    d=data(); d["activity"][0,0]=np.nan
    with pytest.raises(ValueError,match="Nonfinite"):
        save_episode(tmp_path/"bad.npz",**d)

def test_cell_alignment_rejected(tmp_path):
    d=data(); d["cell_index"]=np.array([1,0])
    with pytest.raises(ValueError,match="indices"):
        save_episode(tmp_path/"bad.npz",**d)
