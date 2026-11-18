"""Headless CPU studio photograph of one generated part. -- part [out.png]."""
import sys,bpy,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'blender'));args=sys.argv[sys.argv.index('--')+1:];name=args[0]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(root/'web/assets'/(name+'.glb')))
# Vertex colors encode weathering seeds. Preview the real base paint, rather than multiplying by those seeds.
from lib.kit import MATS
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    name0=mat.name.split('.')[0]
    if bs and name0 in MATS:
        sock=bs.inputs['Base Color']
        for link in list(sock.links):mat.node_tree.links.remove(link)
        sock.default_value=(*MATS[name0][0],1.)
if name in ('fleet','rocks'):
    roots=[o for o in bpy.context.scene.objects if not o.parent and o.children and 'static' not in o.name]
    for i,o in enumerate(roots):o.location.x+=(i%4)*95;o.location.y+=(i//4)*85
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(p) for o in bpy.context.scene.objects if o.type=='MESH' for p in o.bound_box]
if not points:raise ValueError('no geometry')
mn=Vector([min(p[i] for p in points) for i in range(3)]);mx=Vector([max(p[i] for p in points) for i in range(3)]);c=(mn+mx)/2
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=False;world=bpy.data.worlds.new('studio');world.color=(.20,.22,.25);scene.world=world
def aim(obj,target):obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
for vec,energy,col in [((2,-3,4),3.2,(.8,.93,1)),((-3,2,1),2.2,(1,.36,.25))]:
    bpy.ops.object.light_add(type='SUN',location=c+Vector(vec)*200);o=bpy.context.object;o.data.energy=energy;o.data.color=col;o.data.angle=.12;aim(o,c)
bpy.ops.object.camera_add(location=c+Vector((.95,-1.55,1.03))*max(80,(mx-mn).length));cam=bpy.context.object;aim(cam,c);cam.data.type='ORTHO';scene.camera=cam;cam.data.clip_end=9000
inv=cam.rotation_euler.to_matrix().transposed();q=[inv@(p-c) for p in points]
cam.data.ortho_scale=max(max(p.x for p in q)-min(p.x for p in q),(max(p.y for p in q)-min(p.y for p in q))*1.5)*1.12
scene.render.resolution_x=720;scene.render.resolution_y=480;scene.render.resolution_percentage=100;scene.render.threads_mode='FIXED';scene.render.threads=3
scene.render.filepath=str(Path(args[1]).resolve() if len(args)>1 else root/'qa'/(name+'.png'));bpy.ops.render.render(write_still=True)
