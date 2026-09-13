"""Deterministic format/placement conversion of the credited Sketchfab fly; no rigging."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path.cwd();OUT=ROOT/'assets/fly_pilot'
import sys
sys.path.append(str(ROOT/'.venv/lib/python3.12/site-packages'))
source=OUT/'Fly Old.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
mesh_objects=[o for o in bpy.data.objects if o.type=='MESH']
assert len(mesh_objects)==1
obj=mesh_objects[0];obj.data.calc_loop_triangles()
assert len(obj.data.loop_triangles)==1736
armatures=sum(o.type=='ARMATURE' for o in bpy.data.objects)
assert armatures==0
original_vertices=len(obj.data.vertices)
# Preserve original world shape, then apply a documented illustrative placement.
transform=Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Rotation(math.radians(-25),4,'X')@Matrix.Scale(140,4)
obj.data.transform(transform@obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
lowest=min(v.co.z for v in obj.data.vertices)
shift=Vector((-.75,.25,.04-lowest))
for v in obj.data.vertices:v.co+=shift
obj.animation_data_clear()
# Relink only the provided original base-color texture; stable simple rough material.
mat=bpy.data.materials.new('Fly_original_base_color');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear()
output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
texture=nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(OUT/'Fly_01_DefaultMaterial_BaseColor.png'))
mat.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value=.7;bsdf.inputs['Metallic'].default_value=0
mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
obj.data.materials.clear();obj.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
destination=OUT/'fly_pilot.glb'
bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_yup=False,export_animations=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
commit='c6f45eaee28e6ab5e41e5df8f49fd83d7e3ffc9d'
from urllib.parse import quote
sources=[]
for filename,repo in [('Fly Old.blend','Assets/Models/Fly Old.blend'),('Fly_01_DefaultMaterial_BaseColor.png','Assets/Models/fly textures/Fly_01_DefaultMaterial_BaseColor.png'),('Fly_01_DefaultMaterial_Normal.png','Assets/Models/fly textures/Fly_01_DefaultMaterial_Normal.png'),('Fly_01_DefaultMaterial_Roughness.png','Assets/Models/fly textures/Fly_01_DefaultMaterial_Roughness.png')]:
 p=OUT/filename;sources.append(dict(path=p.relative_to(ROOT).as_posix(),original_filename=filename,sha256=sha(p),bytes=p.stat().st_size,url='https://raw.githubusercontent.com/adenprince/cs428-project-2/'+commit+'/'+quote(repo)))
m=dict(model='Low Poly House Fly (Diptera)',model_uid='2baa84955f704a4091a274ef4acec24a',author='Glowbox 3D',license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',
 original_model_url='https://sketchfab.com/3d-models/low-poly-house-fly-diptera-2baa84955f704a4091a274ef4acec24a',
 redistribution_credit='https://sites.google.com/uic.edu/cs428-adenprince/project-2',repository_commit=commit,
 acquisition='Public credited redistribution of the SAME specified Sketchfab model. Direct Sketchfab download API returned 401; no authenticated access bypassed.',
 identity_evidence='Redistributor credits exact model URL; 1736 triangles match. Blender has 924 vertices vs published 908; file identity against official ZIP cannot be established.',
 source_files=sources,converted_path=destination.relative_to(ROOT).as_posix(),converted_sha256=sha(destination),converted_bytes=destination.stat().st_size,
 vertices=original_vertices,triangles=1736,armature_count=armatures,animation='fixed pose; no foreleg tracking',
 conversion=dict(blender=bpy.app.version_string,script='scripts/convert_fly_phase4a.py',script_sha256=sha(ROOT/'scripts/convert_fly_phase4a.py'),
 scale=140,rotations_degrees={'X':-25,'Z':90},translation=list(shift),axis='Z-up; export_yup=False',
 materials='Original base-color texture relinked; opaque, roughness 0.7, metallic 0; normal/roughness maps retained as source only',
 changes='Format conversion, uniform display scaling, rigid tilt/rotation/placement and material relinking. No mesh deformation, rig, animation or control changes.'),
 restrictions='Source page carries NoAI notice. Deterministic presentation only; no generative-AI training or asset generation.',
 cadnav_attempt=dict(url='https://www.cadnav.com/3d-models/model-45541.html',format='Maya .mb',license='Non-commercial',download='HTTP 403',importer='Maya unavailable; Blender does not import Maya binary',selected=False))
(OUT/'manifest.json').write_text(json.dumps(m,indent=2))
print(json.dumps({'asset':str(destination),'vertices':original_vertices,'triangles':1736,'bytes':destination.stat().st_size,'sha256':sha(destination)},indent=2))
