"""Small real-GPU history diagnostic; never added to training/test selection."""
import json
from pathlib import Path
import numpy as np
from flyrendezvous.adapter import FlyvisAdapter
from flyrendezvous.camera import Camera
from flyrendezvous.features import Pooling,History
from flyrendezvous.readout import Readout,ImagePolicy
from flyrendezvous.phase2_runtime import load_config,adapter_config
from flyrendezvous.recording import write_json,sha256
def main():
    out=Path("outputs/phase2");cfg=load_config();camera=Camera(cfg["camera"])
    adapter=FlyvisAdapter(adapter_config());pool=Pooling(adapter.nodes,4);readout=Readout.load(out/"readout.npz")
    policy=ImagePolicy(adapter,pool,readout,cfg["a_max"]);traces={}
    for name,start in [("approaching",18.),("receding",14.)]:
        states=np.column_stack([np.linspace(start,16.,60),np.full(60,.3),np.zeros((60,2))])
        images=np.stack([camera.render(s) for s in states]);policy.reset();activity=[];features=[];raw=[];receptors=[]
        for image in images:
            u,_,d=policy.step(image);raw.append(u);activity.append(d["activity"]);features.append(d["phi"]);receptors.append(d["receptors"])
        traces[name]=dict(images=images,activity=np.array(activity),phi=np.array(features),u_raw=np.array(raw),receptors=np.array(receptors))
    first,second=traces.values()
    np.testing.assert_array_equal(first["images"][-1],second["images"][-1])
    diff=float(np.linalg.norm(first["phi"][-1]-second["phi"][-1]))
    assert diff>1e-6
    path=out/"history_diagnostic.npz"
    np.savez_compressed(path,**{name+"_"+key:value for name,data in traces.items() for key,value in data.items()},
        baseline=policy.baseline)
    adapter.assert_frozen()
    summary=dict(final_images_identical=True,final_feature_l2_difference=diff,
        final_activity_rms_difference=float(np.sqrt(np.mean((first["activity"][-1].astype(float)-second["activity"][-1])**2))),
        final_raw_acceleration_difference=(first["u_raw"][-1]-second["u_raw"][-1]).tolist(),
        receptor_range=[float(min(d["receptors"].min() for d in traces.values())),float(max(d["receptors"].max() for d in traces.values()))],
        record_sha256=sha256(path),readout_sha256=sha256(out/"readout.npz"),
        parameter_sha256_before=adapter.initial_parameter_hash,parameter_sha256_after=adapter.parameter_hash(),
        interpretation="prescribed image-history diagnostic, not HCW trajectory or added training data; response difference alone does not prove linear control")
    write_json(out/"history_diagnostic.json",summary);print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
