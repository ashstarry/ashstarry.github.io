import math,json
import numpy as np, bpy
from .layout import *
from .nz import noise,smooth
from .kit import material,export_glb
from .images import png
def outline(x,y,part):
    lx=x-(SHARD_OFF[0] if part else 0);ly=y-(SHARD_OFF[1] if part else 0)
    th=np.arctan2(ly,lx);r=np.hypot(lx,ly)
    outer=220+4*np.sin(3*th+.4)+3*np.cos(7*th-1)+2.2*np.sin(13*th)+1.4*np.cos(23*th)-r
    fiss= bite_xc(ly)+2.5*np.sin(ly*.095)+1.8*np.cos(ly*.037)-lx
    return np.minimum(outer,-fiss if part else fiss)
def boxdist(x,y,cx,cy,sx,sy,angle):
    a=math.radians(angle);u=(x-cx)*math.cos(a)+(y-cy)*math.sin(a);v=-(x-cx)*math.sin(a)+(y-cy)*math.cos(a)
    return np.maximum(abs(u)-sx/2,abs(v)-sy/2)
def blur(a,r):
    def axis(v,axis):
        pad=[(0,0)]*2;pad[axis]=(r,r);d=np.pad(v,pad,mode='edge');p=[(0,0)]*2;p[axis]=(1,0)
        c=np.pad(d,p).cumsum(axis=axis,dtype='float64');n=2*r+1
        return ((c[n:]-c[:-n]) if axis==0 else (c[:,n:]-c[:,:-n]))/n
    return axis(axis(a,0),1).astype('float32')
def mesh_slab(name,part,xv,yv,height,dist):
    # Select occupied cells, then project the boundary back onto the analytic fracture.
    step=4;xx=xv[::step];yy=yv[::step];dx=xx[1]-xx[0];h=height[::step,::step]
    xc,yc=np.meshgrid((xx[1:]+xx[:-1])*.5,(yy[1:]+yy[:-1])*.5)
    inside=outline(xc,yc,part)>0; iy,ix=np.where(inside);ww=len(xx)
    quads=np.stack((iy*ww+ix,iy*ww+ix+1,(iy+1)*ww+ix+1,(iy+1)*ww+ix),axis=1)
    used,flat=np.unique(quads,return_inverse=True);quads=flat.reshape(-1,4);jy,jx=np.divmod(used,ww)
    vx=xx[jx].copy();vy=yy[jy].copy();vz=h[jy,jx].copy()
    # Winding is anticlockwise when viewed from above.
    perimeter=[]
    pad=np.pad(inside,1)
    for edge,neighbour in enumerate([pad[:-2,1:-1],pad[1:-1,2:],pad[2:,1:-1],pad[1:-1,:-2]]):
        eid=np.where(~neighbour[iy,ix])[0]
        perimeter.extend(zip(quads[eid,edge].tolist(),quads[eid,(edge+1)%4].tolist()))
    ids=np.unique(np.asarray(perimeter));bx=vx[ids];by=vy[ids];dd=outline(bx,by,part)
    gx=(outline(bx+.4,by,part)-outline(bx-.4,by,part))/.8;gy=(outline(bx,by+.4,part)-outline(bx,by-.4,part))/.8
    ll=np.maximum(.25,gx*gx+gy*gy);vx[ids]-=dd*gx/ll;vy[ids]-=dd*gy/ll
    verts=np.stack((vx,vy,vz),axis=1).tolist();faces=quads.tolist()
    boundary={a:b for a,b in perimeter}
    rings=[]
    while boundary:
        first=next(iter(boundary));loop=[first];p=boundary.pop(first)
        while p!=first and p in boundary:loop.append(p);p=boundary.pop(p)
        if len(loop)>8:rings.append(loop)
    for loop in rings:
        lo=loop;px=vx[loop];py=vy[loop];pz=vz[loop];n=len(loop)
        cx,cy=((244.,-63.) if part else (-13.,2.));rng1=noise(px,py,24,11);rng2=noise(px,py,6.5,19)
        edgethick=(13 if part else 24)+(11 if part else 22)*rng1+6*rng2
        dx_=np.roll(px,-1)-np.roll(px,1);dy_=np.roll(py,-1)-np.roll(py,1);length=np.maximum(.01,np.hypot(dx_,dy_));nx=dy_/length;ny=-dx_/length
        for level in (0.07,.17,.31,.36,.58,.78,1.):
            relief=(1.5*np.sin(px*.095+py*.14+level*10)+2.8*(noise(px+level*18,py,10,6)-.5)-3*level)
            if level==.36:relief-=1.9
            nv=np.stack((px+nx*relief,py+ny*relief,pz-edgethick*level),-1);new=list(range(len(verts),len(verts)+n));verts.extend(nv.tolist())
            faces.extend((lo[(i+1)%n],lo[i],new[i],new[(i+1)%n]) for i in range(n));lo=new
        # The underside breaks into irregular keels. Downsample each inner ring progressively.
        prev_indices=np.arange(n);prev=lo
        for j,f in enumerate((.10,.23,.37,.52,.67,.81,.92)):
            ixr=np.arange(0,n,min(2**(j+1),24));rx=px[ixr]*(1-f)+cx*f;ry=py[ixr]*(1-f)+cy*f
            d=np.maximum(outline(rx,ry,part),0)
            base=(15+52*(1-np.exp(-d/26))) if part else (22+112*(1-np.exp(-d/62)))
            ridges=(1-abs(noise(rx,ry,26,22)*2-1))**6
            height_=-base-(6 if part else 34)*ridges-15*noise(rx,ry,10,27)-9
            new=list(range(len(verts),len(verts)+len(ixr)));verts.extend(np.stack((rx,ry,height_),axis=-1).tolist())
            for i in range(len(prev)):
                k=(i+1)%len(prev);t=int(np.searchsorted(ixr,prev_indices[i],side='right')-1);u=int(np.searchsorted(ixr,prev_indices[k],side='right')-1)
                faces.append((prev[k],prev[i],new[t]))
                if t!=u:faces.append((prev[k],new[t],new[u]))
            prev_indices,prev=ixr,new
        faces.append(tuple(reversed(prev)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    mesh.materials.append(material('ground'));ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    # Smooth topography, keep weathered bedrock and the fractured underside faceted.
    mesh.polygons.foreach_set('use_smooth',np.arange(len(faces))<len(quads))
    return sum(len(f)-2 for f in faces)
def build(out,log):
    xv=np.linspace(WX0,WX1,NFINE,dtype='float32');yv=np.linspace(WY0,WY1,NFINE,dtype='float32')
    X=xv[None,:];Y=yv[:,None];dm=outline(X,Y,0);ds=outline(X,Y,1);sh=ds>dm;d=np.maximum(dm,ds)
    lx=X-np.where(sh,70.,0.).astype('float32');ly=Y+np.where(sh,20.,0.).astype('float32')
    n=noise(lx,ly,74,7);med=noise(lx,ly,17,23);fine=noise(lx,ly,4.5,12)
    h=.05*ly+10*(n-.5)+2.6*(med-.5)+1.2*(1-abs(fine*2-1))+(SHARD_DROP*sh)
    h-= (3.+4*med)*(1-smooth(d/15))
    r=np.hypot(lx,ly);theta=np.mod(np.arctan2(ly,lx)*180/np.pi,360)
    ridge=smooth((r-118)/16)*smooth((168-r)/18)*smooth((theta-100)/16)*smooth((205-theta)/16)
    h+=ridge*(9+19*noise(lx,ly,22,31))*(.75+.25*med)
    for x,y,a,b,z in [(-158,-92,36,21,11),(-98,-152,27,18,8),(-176,-40,22,15,7)]:
        rr=np.hypot((X-x)/a,(Y-y)/b);h+=np.maximum(1-rr,0)*z*(.86+.24*np.cos(np.arctan2(Y-y,X-x)*14+med*4))
    for x,y,cr,depth in CRATERS:
        rr=np.hypot(X-x,Y-y)/cr;h+=depth*(.36*np.exp(-((rr-1)/.12)**2)-np.maximum(1-rr*rr,0))
    dx=X-PIT_C[0];dy=Y-PIT_C[1];co=math.cos(PIT_ROT);si=math.sin(PIT_ROT);u=(dx*co+dy*si)/PIT_A;v=(-dx*si+dy*co)/PIT_B
    pd=np.hypot(u,v);a=np.mod(np.degrees(np.arctan2(dy,dx)),360)
    pde=pd+(.012*(med-.5)+.005*np.sin(a*.24+med*3))*smooth(pd/.4)
    profile=np.interp(pde,[0,.30,.33,.42,.45,.55,.58,.685,.72,.82,.86,.95,1],[ -76,-74.5,-65,-64,-53,-52,-39.5,-38.5,-25.5,-24.5,-12.5,-11.5,0]).astype('float32')
    slide=smooth((33-np.abs(a-222))/12);profile=profile*(1-slide)+(-76*(1-np.clip(pd,0,1)**1.25))*slide
    pa=np.mod(a+25,360);route=.975-.34*pa/190;rw=smooth((.043-abs(pd-route))/.012)*smooth((192-pa)/6);profile=profile*(1-rw)+(-39*pa/190)*rw
    hp=profile+PIT_ZREF+1.1*(med-.5)+.45*(fine-.5)
    rc=np.hypot(dx,dy);hp-=1.8*np.exp(-((rc-27.5)/1.25)**2);hp+=.38*np.cos(np.arctan2(dy,dx)*59+rc*.04)*(1-smooth((rc-32)/14))
    pm=1-smooth((pd-.97)/.045);h=h*(1-pm)+hp*pm;h+=1.3*np.exp(-((pd-1.014)/.017)**2)
    # A retired southern access cut opens a sightline from the apron to the crown.
    # Its narrow benches retain the full 76 m profile on either side.
    along=dx*.519-dy*.855
    across=dx*.855+dy*.519
    cut=smooth((along-35)/18)*smooth((147-along)/21)*(1-smooth((abs(across+1.8*(med-.5))-15)/17))
    grade=-73+.51*along
    bench=.44*grade+.56*(np.floor(grade/5)*5)+.9*(med-.5)
    h=h+(np.minimum(h,bench)-h)*cut
    wn=(math.cos(WALL_TH),math.sin(WALL_TH));s=dx*wn[0]+dy*wn[1]-WALL_DIST;t=-dx*wn[1]+dy*wn[0]
    swall=s.copy();twall=t.copy()
    wm=smooth((WALL_HALF-abs(t))/7)*smooth((s+39)/10)*smooth((19-s)/8)
    wall=np.where(s>=0,WALL_ZTOP-.9+med,-75.2+.55*fine);h=h*(1-wm)+wall*wm
    notch=1-smooth((boxdist(X,Y,-157.2,49.8,34,26,52.4)+1)/4);h=h*(1-notch)+np.minimum(h,-9.5+fine*.4)*notch
    valid=(d>=0).astype('float32');road=np.zeros_like(h);pad=road.copy()
    for _,width,pts in ROADS:
        for (ax,ay),(bx,by) in zip(pts,pts[1:]):
            vx=bx-ax;vy=by-ay;t=np.clip(((X-ax)*vx+(Y-ay)*vy)/(vx*vx+vy*vy),0,1)
            dist=np.hypot(X-ax-t*vx,Y-ay-t*vy)
            np.maximum(road,1-smooth((dist-width*.36)/(width*.3)),out=road)
    sm=blur(h*valid,18)/np.maximum(.00001,blur(valid,18));h=h*(1-road)+(sm-.12)*road
    for _,cx,cy,sx,sy,ang,z0 in PADS:
        bd=boxdist(X,Y,cx,cy,sx,sy,ang);f=1-smooth(bd/5);mask=(bd<0)&(d>=0)
        z=z0 if z0 is not None else float(h[mask].mean()) if mask.any() else 0.;h=h*(1-f)+z*f;pad=np.maximum(pad,f)
    # Cut both approaches to the surveyed deck after terrain grading.
    shoulder=1-smooth((abs(twall)-9.0)/5.5)
    upper=shoulder*smooth((swall-1)/5)*smooth((39-swall)/6)
    lower=shoulder*smooth((-swall-11)/5)*smooth((55+swall)/6)
    h=h*(1-upper)+np.minimum(h,.78)*upper
    h=h*(1-lower)+np.minimum(h,-75.1)*lower
    tex=out/'tex';tex.mkdir(parents=True,exist_ok=True)
    ao=np.ones_like(h)
    for nscale,gain in [(5,.3),(22,.13),(72,.075)]:
        bl=blur(h*valid,nscale)/np.maximum(.0001,blur(valid,nscale));ao*=np.clip(1-np.maximum(bl-h,0)*gain,.48,1)
    crack0=noise(lx,ly,16,43)+.36*noise(lx,ly,4,44);crack=(1-smooth(abs(crack0-.63)/.022))*(1-smooth(abs(bite_xc(ly)-lx)/70))*(.45+.55*med)
    png(tex/'terrain_mask.png',np.stack((ao,road,pad),axis=-1)[::2,::2]);png(tex/'terrain_mask2.png',np.stack((crack,pm,pm*0),axis=-1)[::2,::2])
    ii=np.rint(np.linspace(0,NFINE-1,1024)).astype(int);grid=np.where(d[np.ix_(ii,ii)]>=0,h[np.ix_(ii,ii)],-9999).astype('<f4');grid.tofile(out/'height.bin')
    tri=mesh_slab('main_disc',0,xv,yv,h,dm)+mesh_slab('port_shard',1,xv,yv,h,ds)
    # Store sphere in world geometry so radial weathering is centred on the Lode.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=72,ring_count=36,radius=34,location=(-78,12,-96));ob=bpy.context.object;ob.name='the_lode';bpy.ops.object.transform_apply(location=True,rotation=False,scale=False)
    ob.data.materials.append(material('lode'));[setattr(p,'use_smooth',True) for p in ob.data.polygons]
    export_glb(out/'terrain.glb')
    (out/'terrain.json').write_text(json.dumps(dict(rect=[WX0,WY0,WX1-WX0],resolution=1024,lode=[-78,-96,-12,34],triangles=tri,markers={},lights=[],colliders=[],paths={})))
    log(f'Terrain {tri:,} triangles. Height valid {int((grid>-9000).sum()):,} texels.')
