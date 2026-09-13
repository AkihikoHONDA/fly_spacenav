import bpy,json
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath=str(Path("assets/fly_pilot/Fly Old.blend").resolve()))
report=[]
for o in bpy.data.objects:
 r=dict(name=o.name,type=o.type,location=list(o.location),rotation=list(o.rotation_euler),scale=list(o.scale),bounds=[list(o.matrix_world@__import__('mathutils').Vector(v)) for v in o.bound_box])
 if o.type=='MESH':
  o.data.calc_loop_triangles()
  r.update(vertices=len(o.data.vertices),triangles=len(o.data.loop_triangles),materials=[m.name for m in o.data.materials])
 report.append(r)
print(json.dumps(report,indent=2))
Path('assets/fly_pilot/blend_inspection.json').write_text(json.dumps(dict(objects=report,images=[dict(name=i.name,path=i.filepath,packed=bool(i.packed_file)) for i in bpy.data.images]),indent=2))
