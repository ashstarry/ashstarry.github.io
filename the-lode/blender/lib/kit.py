"""Batched hard-surface kit. All inputs use absolute Blender metres, angles in degrees."""
import math, random, json, hashlib
from contextlib import contextmanager
from pathlib import Path
import bpy, numpy as np
from mathutils import Vector, Euler, Quaternion
from .layout import three

MATS={
'metal_yellow':((.42,.27,.05),.6,0),'metal_orange':((.40,.13,.035),.6,0),'metal_red':((.26,.05,.035),.6,0),'metal_white':((.42,.41,.38),.55,0),'metal_grey':((.16,.165,.17),.6,0),'metal_dark':((.045,.047,.05),.55,0),'metal_green':((.10,.13,.09),.6,0),'metal_blue':((.07,.11,.16),.6,0),'metal_teal':((.06,.13,.13),.6,0),'metal_hazard':((.45,.30,.04),.6,0),
'steel':((.19,.185,.18),.45,.85),'steel_dark':((.06,.06,.062),.5,.8),'steel_rust':((.16,.075,.04),.8,.3),'hull_grey':((.20,.205,.21),.5,.2),'hull_dark':((.06,.062,.068),.5,.2),'hull_rust':((.22,.10,.05),.6,.1),'hull_white':((.36,.35,.33),.5,.1),
'conc':((.23,.225,.21),.9,0),'conc_dark':((.10,.10,.098),.9,0),'conc_warm':((.25,.21,.17),.9,0),'rubber':((.015,.015,.016),.9,0),'glass':((.02,.03,.04),.1,0),'glass_warm':((.20,.14,.07),.15,0),'solar':((.012,.016,.035),.25,.5),'tarp':((.16,.10,.06),.95,0),'rock_dark':((.09,.085,.08),.95,0),
'emit_warm':((1.,.62,.28),.5,0),'emit_sodium':((1.,.45,.10),.5,0),'emit_cool':((.62,.8,1),.5,0),'emit_white':((1.,.95,.85),.5,0),'emit_red':((1.,.07,.03),.5,0),'emit_green':((.25,1.,.45),.5,0),'emit_amber':((1.,.55,.05),.5,0),'emit_blue':((.2,.45,1.),.5,0),'emit_molten':((1.,.30,.05),.6,0),'relic':((.004,.004,.005),.25,0),'lode':((.0025,.0027,.003),.22,0),'ground':((.16,.14,.12),.92,0),'rock_inner':((.22,.17,.15),.9,0)}
def material(name):
    existing=bpy.data.materials.get(name)
    if existing:return existing
    c,r,m=MATS.get(name,((.17,.15,.13),.85,0))
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*c,1.);mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1.);p.inputs['Roughness'].default_value=r;p.inputs['Metallic'].default_value=m
    if name.startswith('emit_'):
        p.inputs['Emission Color'].default_value=(*c,1);p.inputs['Emission Strength'].default_value=.65
    return mat
def V(p):return Vector(p)
Z=V((0,0,1))
def rotmat(rot):
    if isinstance(rot,(float,int)):rot=(0,0,rot)
    return Euler(tuple(math.radians(a) for a in rot)).to_matrix()
def circle(cx,cy,z,rx,ry,n=16,angle=0):
    return [(cx+rx*math.cos(math.tau*i/n+angle),cy+ry*math.sin(math.tau*i/n+angle),z) for i in range(n)]
def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,export_materials='EXPORT',export_texcoords=True,export_normals=True,export_vertex_color='ACTIVE',export_all_vertex_colors=True,export_animations=False)

class Batch:
    def __init__(self,loc,parent):
        self.loc=V(loc);self.parent=parent;self.v=[];self.faces=[];self.uv=[];self.half=[];self.col=[];self.names=[];self.midx=[]
class Kit:
    def __init__(self,name,seed=None):
        self.name=name;self.rng=random.Random(seed if seed is not None else int.from_bytes(hashlib.md5(name.encode()).digest()[:4],'little'))
        self.groups={'static':Batch((0,0,0),None)};self.active='static';self.partR=.5;self.user=0.;self.data={'markers':{},'lights':[],'colliders':[],'paths':{},'units':'metres, three.js axes'}
        self.part()
    def part(self,user=0):
        self.partR=self.rng.uniform(.08,.94);self.user=user
    @contextmanager
    def into(self,name,parent=None,loc=(0,0,0)):
        old=self.active
        if name not in self.groups:self.groups[name]=Batch(loc,parent or (old if old!='static' else None))
        self.active=name
        try:yield self
        finally:self.active=old
    def face(self,pts,mat='steel',curve=False,color=None):
        if len(pts)<3:return
        g=self.groups[self.active];ps=[V(p) for p in pts];a=ps[0];normal=(ps[1]-a).cross(ps[2]-a)
        if normal.length_squared<1e-10:return
        normal.normalize();u=Z.cross(normal)
        if u.length_squared<1e-7:u=V((1,0,0))
        u.normalize();v=normal.cross(u).normalized()
        uv=[((p-a).dot(u),(p-a).dot(v)) for p in ps];mx=max(t[0] for t in uv);mi=min(t[0] for t in uv);my=max(t[1] for t in uv);mj=min(t[1] for t in uv)
        if mat not in g.names:g.names.append(mat)
        g.midx.append(g.names.index(mat));start=len(g.v);g.v.extend(tuple(p-g.loc) for p in ps);g.faces.append(tuple(range(start,start+len(ps))))
        g.uv.extend((x-(mx+mi)*.5,y-(my+mj)*.5) for x,y in uv);g.half.extend([(99. if curve else max(.001,(mx-mi)*.5),max(.001,(my-mj)*.5))]*len(ps))
        c=tuple(color) if color is not None else (self.partR,self.rng.random(),self.user,1.);g.col.extend([c]*len(ps))
    def box(self,center,size,mat='metal_grey',rot=0):
        c=V(center);a,b,h=[s*.5 for s in size];r=rotmat(rot) if rot else None
        ps=[V(t) for t in [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
        ps=[c+(r@p if r else p) for p in ps]
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face([ps[i] for i in f],mat)
    def loft(self,rings,mat='metal_grey',caps=True,curve=False):
        for lo,hi in zip(rings,rings[1:]):
            for i in range(len(lo)):
                j=(i+1)%len(lo);self.face([lo[i],lo[j],hi[j],hi[i]],mat,curve)
        if caps:self.face(list(reversed(rings[0])),mat);self.face(rings[-1],mat)
    def prism(self,points,z0,z1,mat='conc'):
        self.loft([[(x,y,z) for x,y in points] for z in [z0,z1]],mat)
    def lathe(self,center,profile,mat='metal_grey',n=16):
        x,y,z=center;self.loft([circle(x,y,z+h,r,r,n) for h,r in profile],mat,True,True)
    def cyl(self,center,r,h,mat='steel',n=12):
        self.lathe(center,[(-h/2,r),(h/2,r)],mat,n)
    def pipe(self,a,b,r,mat='steel',n=8):
        p,q=V(a),V(b);d=(q-p)
        if d.length_squared<1e-8:return
        d.normalize();u=d.cross(Z if abs(d.z)<.92 else V((0,1,0))).normalized();v=d.cross(u)
        ring=[r*(u*math.cos(math.tau*i/n)+v*math.sin(math.tau*i/n)) for i in range(n)]
        self.loft([[a0+t for t in ring] for a0 in (p,q)],mat,True,True)
    def tube(self,points,r,mat='steel',n=8):
        for p,q in zip(points,points[1:]):self.pipe(p,q,r,mat,n)
    def beam(self,a,b,w,h=None,mat='steel_dark'):
        if isinstance(h,str):mat,h=h,None
        h=w if h is None else h;p,q=V(a),V(b);d=q-p
        if d.length_squared<1e-8:return
        d.normalize();u=d.cross(Z if abs(d.z)<.97 else V((0,1,0))).normalized()*w*.5;v=d.cross(u.normalized())*h*.5
        self.loft([[c-u-v,c+u-v,c+u+v,c-u+v] for c in (p,q)],mat)
    def truss(self,a,b,w=3,h=3,mat='steel_rust',bays=None,member=.42):
        a,b=V(a),V(b);d=(b-a).normalized();s=Z.cross(d)
        if s.length_squared<.01:s=V((1,0,0))
        s.normalize();up=d.cross(s).normalized()
        corners=[s*x*w*.5+up*y*h*.5 for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        for v in corners:self.beam(a+v,b+v,member,member,mat)
        bays=bays or max(1,round((b-a).length/max(3.5,w*1.7)))
        for i in range(bays):
            p=a.lerp(b,i/bays);q=a.lerp(b,(i+1)/bays)
            for j,k in [(0,3),(1,2),(0,1)]:
                self.beam(p+corners[j],p+corners[k],member*.69,mat)
                self.beam(p+corners[j if i%2 else k],q+corners[k if i%2 else j],member*.65,mat)
    def tower(self,center,z0,z1,base=9,top=5,mat='steel_rust',bays=5,member=.65):
        x,y=center
        def ring(z,w):return [V((x+i*w/2,y+j*w/2,z)) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        low=ring(z0,base);high=ring(z1,top)
        for a,b in zip(low,high):self.beam(a,b,member*1.3,mat)
        for i in range(bays):
            p=[a.lerp(b,i/bays) for a,b in zip(low,high)];q=[a.lerp(b,(i+1)/bays) for a,b in zip(low,high)]
            for k in range(4):
                j=(k+1)%4;self.beam(q[k],q[j],member,mat);self.beam(p[k if i%2 else j],q[j if i%2 else k],member*.73,mat)
    def torus(self,center,major,minor,mat='steel',n=28,m=6,normal=(0,0,1)):
        c=V(center);d=V(normal).normalized();a=d.cross(V((0,1,0)) if abs(d.y)<.94 else Z).normalized();b=d.cross(a);rings=[]
        for i in range(n):
            u=a*math.cos(math.tau*i/n)+b*math.sin(math.tau*i/n)
            rings.append([c+u*(major+minor*math.cos(math.tau*j/m))+d*minor*math.sin(math.tau*j/m) for j in range(m)])
        for i in range(n):
            lo,hi=rings[i],rings[(i+1)%n]
            for j in range(m):
                k=(j+1)%m;self.face((lo[j],hi[j],hi[k],lo[k]),mat,True)
    def sphere(self,center,radii,mat='metal_grey',n=16,m=10):
        if isinstance(radii,(float,int)):radii=(radii,)*3
        x,y,z=center;rx,ry,rz=radii;rings=[]
        for i in range(1,m):
            a=-math.pi*.5+math.pi*i/m;rings.append(circle(x,y,z+rz*math.sin(a),rx*math.cos(a),ry*math.cos(a),n))
        self.loft(rings,mat,False,True)
        for j in range(n):
            k=(j+1)%n;self.face([(x,y,z-rz),rings[0][k],rings[0][j]],mat);self.face([rings[-1][j],rings[-1][k],(x,y,z+rz)],mat)
    def cable(self,a,b,sag=.7,r=.1,mat='steel_dark',n=9):
        a,b=V(a),V(b);p=[a.lerp(b,i/n)-Z*(4*sag*i/n*(1-i/n)) for i in range(n+1)]
        self.tube(p,r,mat,5)
    def railing(self,a,b,mat='metal_yellow',height=1.15):
        a,b=V(a),V(b);n=max(1,round((b-a).length/3.4))
        for i in range(n+1):
            p=a.lerp(b,i/n);self.beam(p,p+Z*height,.10,mat)
        for h in (.5,height):self.beam(a+Z*h,b+Z*h,.105,mat)
    def catwalk(self,a,b,width=1.8,mat='steel_dark'):
        a,b=V(a),V(b);s=Z.cross(b-a).normalized()*width*.47;self.beam(a,b,width,.25,mat)
        for side in [-1,1]:self.railing(a+s*side+Z*.12,b+s*side+Z*.12)
    def ladder(self,a,b,width=.7,mat='steel'):
        a,b=V(a),V(b);side=V((width/2,0,0))
        for s in [-1,1]:self.beam(a+side*s,b+side*s,.09,mat)
        n=max(1,int((b-a).length/.64))
        for i in range(n):
            p=a.lerp(b,(i+.45)/n);self.beam(p-side,p+side,.1,mat)
    def stairs(self,a,b,width=2.4,mat='steel_dark'):
        a,b=V(a),V(b);s=Z.cross(b-a).normalized()*width*.5
        n=max(2,int(abs(b.z-a.z)/.32))
        for i in range(n):
            p=a.lerp(b,(i+.5)/n);self.beam(p-s,p+s,(V((b.x-a.x,b.y-a.y,0)).length/n)+.04,.16,mat)
        for j in [-1,1]:self.beam(a+j*s,b+j*s,.18,mat);self.railing(a+j*s,b+j*s)
    def tank(self,x,y,z,r,h,mat='metal_grey'):
        self.part();self.cyl((x,y,z+.45),r+1,.9,'conc_dark');self.lathe((x,y,z),[(.9,r*.93),(1.7,r),(h,r),(h+1.2,r*.8),(h+1.6,r*.18)],mat,20)
        for hh in (1.8,h*.58,h):self.cyl((x,y,z+hh),r+.11,.25,'steel_dark',20)
        self.ladder((x,y-r-.23,z+1),(x,y-r-.23,z+h));self.pipe((x+r,y,z+2.4),(x+r+2,y,z+2.4),.45,'steel_rust')
    def lamp(self,pos,h=5.,kind='flood',col=(.62,.8,1.),r=16.,power=1.1):
        p=V(pos);q=p+Z*h;self.beam(p,q,.18,'steel_dark');end=q+V((0,-.85,0));self.beam(q,end,.17,'steel_dark');self.box(end,(1.0,.72,.46),'metal_dark')
        self.box(end+V((0,-.17,-.25)),(.78,.46,.10),'emit_red' if kind=='beacon' else 'emit_cool' if col[2]>.65 else 'emit_sodium');self.light(end,col,r,power,kind)
    def light(self,pos,color=(.62,.8,1.),radius=16,power=1.,kind='lamp',obj=None):
        group=obj or self.active;origin=self.groups[group].loc if group in self.groups else V((0,0,0))
        self.data['lights'].append(dict(p=three(V(pos)-origin),c=list(color),r=radius,i=power,k=kind,obj=group))
    def marker(self,name,pos,axis=(1,0,0),up=(0,0,1)):
        self.data['markers'][name]={'p':three(pos),'axis':three(axis),'up':three(up),'obj':self.active}
    def collider(self,size,loc,rot=0,tag='solid',friction=.75):
        r=rotmat(rot).to_quaternion() if rot else Quaternion((1,0,0,0))
        self.data['colliders'].append(dict(p=three(loc),h=[size[0]/2,size[2]/2,size[1]/2],q=[r.x,r.z,-r.y,r.w],tag=tag,mu=friction,obj=self.active))
    def path(self,name,points):self.data['paths'][name]=points
    def finalize(self,out,log=print):
        obs={};tris=0
        for name,g in self.groups.items():
            ob=bpy.data.objects.new(name if name!='static' else self.name+'_static',None);bpy.context.collection.objects.link(ob);obs[name]=ob
            if g.parent and g.parent in obs:ob.parent=obs[g.parent];ob.location=g.loc-self.groups[g.parent].loc
            else:ob.location=g.loc
            if not g.faces:continue
            mesh=bpy.data.meshes.new(name+'_surface');mesh.from_pydata(g.v,[],g.faces);mesh.update()
            for nm in g.names:mesh.materials.append(material(nm))
            mesh.polygons.foreach_set('material_index',np.array(g.midx,dtype='int32'))
            for nm,vals in [('UVMap',g.uv),('MetricHalf',g.half)]:
                layer=mesh.uv_layers.new(name=nm);layer.data.foreach_set('uv',np.asarray(vals,'float32').ravel())
            ca=mesh.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER');ca.data.foreach_set('color',np.asarray(g.col,'float32').ravel());mesh.color_attributes.active_color=ca
            mob=bpy.data.objects.new((self.name if name=='static' else name)+'_geo',mesh);bpy.context.collection.objects.link(mob);mob.parent=ob;tris+=sum(len(f)-2 for f in g.faces)
        out=Path(out);out.mkdir(parents=True,exist_ok=True);self.data['triangles']=tris;self.data['objects']=list(self.groups)[1:]
        export_glb(out/(self.name+'.glb'));(out/(self.name+'.json')).write_text(json.dumps(self.data,separators=(',',':')))
        log(f'{self.name}: {tris} triangles, {len(self.data["lights"])} lights, {len(self.data["colliders"])} colliders')
