"""Quarried erratics, two Voronoi-fractured ore bodies, talus and a disintegrating moon.

The rock template coordinates are Blender metres around the root. Fracture cell
pivots, volumes and proxies are also exported for the runtime rigid-body solver.
"""
import math
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from lib.ground import G
from lib.kit import Kit, export_glb, material
from lib.layout import CRATERS, PADS, PIT_A, PIT_B, PIT_C, PIT_ROT, ROADS, three


def normalized(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


@lru_cache(maxsize=6)
def geodesic(level):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=level, radius=1.)
    bm.verts.index_update()
    points = np.asarray([v.co[:] for v in bm.verts], dtype=float)
    triangles = np.asarray([[v.index for v in f.verts] for f in bm.faces], dtype=int)
    bm.free()
    return normalized(points), triangles


@lru_cache(maxsize=32)
def noise_table(seed):
    return np.random.default_rng(seed).uniform(-1., 1., (32, 32, 32))


def field(p, frequency, seed):
    """Continuous 3D value noise, coherently shared by adjoining rock faces."""
    table = noise_table(seed)
    u = np.asarray(p) * frequency + [9.31, 17.76, 14.29]
    ix = np.floor(u).astype(int)
    f = u - ix
    f = f * f * (3 - 2 * f)
    v = np.zeros(len(p))
    for i in range(2):
        for j in range(2):
            for k in range(2):
                weight = (f[:, 0] if i else 1-f[:, 0]) * (f[:, 1] if j else 1-f[:, 1]) * (f[:, 2] if k else 1-f[:, 2])
                v += weight * table[(ix[:, 0]+i) % 32, (ix[:, 1]+j) % 32, (ix[:, 2]+k) % 32]
    return v


def hemispherical_ao(points, faces, scale):
    """Cast a short, deterministic fan above each vertex of the actual surface."""
    tri = points[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(points)
    for k in range(3):
        np.add.at(normals, faces[:, k], cross)
    normals = normalized(normals)
    tangent = np.cross(normals, np.array([0., 0., 1.]))
    polar = np.linalg.norm(tangent, axis=1) < .05
    tangent[polar] = np.cross(normals[polar], np.array([0., 1., 0.]))
    tangent = normalized(tangent)
    bitangent = np.cross(normals, tangent)
    tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
    origin = points + normals * (scale * .001)
    ambient = np.ones(len(points))
    for i in range(13):
        z = .075 + .81 * (i + .5) / 13
        az = i * 2.3999632297
        spread = math.sqrt(1-z*z)
        ray = normals*z + tangent*(spread*math.cos(az)) + bitangent*(spread*math.sin(az))
        for j in range(len(points)):
            dist = tree.ray_cast(origin[j], ray[j], scale*.75)[3]
            if dist is not None:
                ambient[j] -= .065 * (1-dist/(scale*.75))
    return np.clip(ambient, .36, 1.)


def mesh_faces(K, vertices, triangles, aos, material_name='rock_dark', fresh=None):
    """Per-corner AO survives glTF vertex duplication at faceted normals."""
    batch = K.groups[K.active]
    for i, q in enumerate(triangles):
        name = 'rock_inner' if fresh is not None and fresh[i] else material_name
        count = len(batch.col)
        K.face(vertices[q], name, color=(1., 1., 1., 1.))
        if len(batch.col) != count:
            batch.col[count:] = [(float(aos[j]),)*3+(1.,) for j in q]


def refine_outcrop(directions, triangles, face_normal, crater_normal):
    """Conforming local subdivision around a worked face and the surviving impact rim."""
    edges, inverse = np.unique(np.sort(triangles[:, [[0, 1], [1, 2], [2, 0]]], axis=2).reshape(-1, 2),
                               axis=0, return_inverse=True)
    mid = normalized(directions[edges].sum(axis=1))
    split = (mid @ face_normal > .52) | (mid @ crater_normal > .84)
    index = np.full(len(edges), -1)
    index[split] = np.arange(split.sum()) + len(directions)
    midpoints = index[inverse].reshape(-1, 3)
    patterns = (
        ((0,1,2),), ((0,3,2),(3,1,2)), ((1,4,0),(4,2,0)),
        ((1,4,3),(0,3,2),(3,4,2)), ((2,5,1),(5,0,1)),
        ((0,3,5),(2,5,1),(5,3,1)), ((2,5,4),(1,4,0),(4,5,0)),
        ((0,3,5),(1,4,3),(2,5,4),(3,4,5)),
    )
    vertices = np.column_stack((triangles, midpoints))
    masks = (midpoints >= 0) @ np.array([1, 2, 4])
    refined = [vertices[masks == n][:, pattern].reshape(-1,3) for n, pattern in enumerate(patterns)]
    return np.vstack((directions, mid[split])), np.vstack(refined)


def battered_body(seed, variant, level, radius, detailed=False):
    """A jointed anisotropic mass, clipped by quarry planes and eroded by impacts."""
    d, triangles = geodesic(level)
    rng = np.random.default_rng(seed)
    # Different shapes have different bedding and dominant quarrystone joint sets.
    shapes = [
        ((1.17,.75,.80), 3.15, ((.55,-.8,.3),(.88,.18,-.40),(-.15,.35,.95))),
        ((.74,.84,1.18), 2.82, ((.77,-.61,.17),(-.76,-.35,.33),(.40,.20,.94))),
        ((1.13,.68,.83), 3.30, ((.3,-.91,-.25),(-.75,.25,.56),(.22,.48,.91))),
        ((1.12,.87,.71), 2.58, ((.4,-.82,.3),(-.7,-.17,-.52),(-.1,.75,.65))),
        ((.93,1.10,.76), 2.92, ((-.25,.91,.27),(.81,-.3,.40),(-.47,-.58,.61))),
    ]
    axes, boxiness, normals = shapes[variant % len(shapes)]
    axes = np.asarray(axes)
    cut_normal = normalized(np.asarray(normals[0], float))
    major_crater = normalized(np.array([(.55,-.23,.76),(-.29,-.75,.56),(.22,-.71,.74)][variant % 3]))
    if detailed:
        d, triangles = refine_outcrop(d, triangles, cut_normal, major_crater)
    rho = np.sum(np.abs(d / axes)**boxiness, axis=1)**(-1/boxiness)
    rho *= 1. + .17*field(d, 1.65, seed) + .065*field(d, 3.8, seed)
    coarse = rho.copy()
    for j, normal in enumerate(normalized(np.array(normals))):
        h = [.68,.79,.73][j] * np.linalg.norm(normal*axes)
        if detailed and not j:
            # A discontinuous depth of cut leaves broad quarry benches.
            bed = d[:, 2] + .24*d[:, 0] - .11*d[:, 1] + .045*field(d, 3.1, seed)
            h = h - .065*(bed > .04) - .095*(bed > .44) - .045*(bed < -.41)
        rho = np.minimum(rho, h / np.maximum(.001, d @ normal))
    cuts = np.clip((coarse-rho)*9., 0., 1.)
    micro = .017*field(d, 9.5, seed) + .009*field(d, 21, seed)
    rho += micro*(1-.73*cuts)
    joints = np.zeros(len(d))
    exposed = np.zeros(len(d))
    if detailed:
        joint_specs = [
            [([.73,.28,.54],-.065,.16,.185,[.12,-.88,.52]),
             ([-.39,.64,.67],.39,.12,.11,[-.62,.75,.17])],
            [([.85,.33,-.18],.18,.17,.20,[.17,-.98,.08]),
             ([.21,.86,.31],.22,.12,.085,[-.63,-.27,.72])],
            [([.05,-.26,.96],.18,.145,.15,[.36,-.72,.61]),
             ([-.57,.35,.68],-.38,.095,.09,[-.75,.33,-.17])]
        ][variant % 3]
        for normal, offset, width, depth, side in joint_specs:
            n = normalized(np.asarray(normal, float))
            trace = d@n - offset + .071*field(d, 3.5, seed+1) + .022*field(d, 9., seed+1)
            # The fractures terminate within the old surface instead of encircling it.
            limit = np.clip((d@normalized(np.asarray(side, float))+.17)*2.3, 0., 1.)
            gorge = np.maximum(0., 1-abs(trace)/width) * limit
            joints += gorge * depth
        rho -= joints
        # Short shelves of harder bedding overhang recesses on the exposed quarry face.
        # The seams taper away before reaching the impact-worn side of the block.
        facing = np.clip((d@cut_normal-.43)*3.9, 0., 1.)
        lateral = d@normalized(np.cross(cut_normal, [0., 0., 1.]))
        dip = d[:,2] + (.16 + .12*variant)*lateral + .077*field(d,2.8,seed+4) + .021*field(d,8.6,seed+7)
        for z, reach, offset in [(-.26,.71,-.23), (.19,.68,.18), (.44,.45,-.07)]:
            extent = facing * np.clip((reach-np.abs(lateral-offset))*5.,0.,1.)
            bed = dip-z
            undercut = np.exp(-((bed+.012)/.041)**2)
            lip = np.exp(-((bed-.060)/.039)**2)
            rho += extent*(.029*lip-.063*undercut)
            exposed = np.maximum(exposed, extent*np.exp(-((bed-.016)/.037)**2))
        for i in range(16):
            orientation = normalized(rng.normal(size=3))
            cr = rng.uniform(.07,.24) if i else .40
            if i == 0:
                orientation = major_crater
            angle = np.linalg.norm(d-orientation, axis=1)/cr
            intact = (1-.69*cuts)
            bowl = np.maximum(0., 1.-angle*angle)**1.45
            berm = np.exp(-((angle-.98)/.155)**2)
            rho += (.048*berm-.248*bowl)*cr*intact
    xyz = d*rho[:, None]
    xyz[:, 0] += (.05 if variant % 2 else -.06)*xyz[:, 2]
    xyz *= radius / np.linalg.norm(xyz, axis=1).max()
    ao = hemispherical_ao(xyz, triangles, radius) if level >= 3 else np.ones(len(d))
    ao *= np.clip(.985 - joints*1.15 + .025*field(d, 3.7, seed+2), .49, 1)
    # Exposed quarry faces admit more ambient light than the oxidised rind.
    # The close rock shader provides strata; avoid an isolated light paint-like patch.
    ao *= .91 + .09*cuts
    fresh = exposed[triangles].mean(axis=1) > .65 if detailed else None
    return xyz, triangles, np.clip(ao, .3, 1), fresh


def forged_link(K):
    """An oblong ship-chain link, 1.24 x 2.68 m, swept from 0.30 m round bar."""
    pts = []
    for a in np.linspace(0, math.pi, 9):
        pts.append([.47*math.cos(a), 0., .72 + .47*math.sin(a)])
    for a in np.linspace(math.pi, 2*math.pi, 9):
        pts.append([.47*math.cos(a), 0., -.72 + .47*math.sin(a)])
    pts = np.asarray(pts)
    rings = []
    for i, p in enumerate(pts):
        d = normalized(pts[(i+1) % len(pts)] - pts[i-1])
        out = np.array([d[2], 0., -d[0]])
        rings.append([p + .15*(out*math.cos(a) + [0., math.sin(a), 0.]) for a in np.arange(7)*math.tau/7])
    K.loft(rings+[rings[0]], 'steel_rust', False, True)


def bench_slab(K):
    """A thin shear wedge. Blender X is its length and Z its bedding normal."""
    outline = np.array([(-.96,-.15),(-.63,-.41),(-.15,-.48),(.44,-.34),(.86,-.26),
                        (1.,-.05),(.75,.35),(.27,.48),(-.31,.43),(-.81,.29)])
    scar = np.array([.09,.06,.03,0.,.12,.17,.09,.03,0.,.04])
    points = []
    ring = len(outline)
    for row, (scale, z) in enumerate(((.81,-.24),(1.,-.095),(.97,.025),(.90,.145),(.58,.208))):
        ledge = scar if row == 2 else 0.
        xy = outline * np.asarray(scale-ledge).reshape(-1,1)
        xy[:,0] += (.025 if row > 2 else -.025)
        heights = z + .067*xy[:,0] - .09*xy[:,1] + .032*np.sin(4*xy[:,0]+3*xy[:,1]+row*.46)
        points.extend(np.column_stack((xy,heights)))
    points.extend([(-.09,.035,-.29),(.05,.055,.25)])
    faces = []
    mats = []
    for i in range(ring):
        j = (i+1)%ring
        faces.extend([(5*ring,j,i),(5*ring+1,4*ring+i,4*ring+j)])
        mats.extend(['rock_inner','rock_dark'])
        for row in range(4):
            lo, hi = row*ring, (row+1)*ring
            faces.extend([(lo+i,lo+j,hi+j),(lo+i,hi+j,hi+i)])
            face_mat = 'rock_inner' if row == 0 or (row < 3 and i in (3,4,5)) else 'rock_dark'
            mats.extend([face_mat,face_mat])
    points = np.asarray(points)
    low, high = points.min(axis=0), points.max(axis=0)
    points = (points-(high+low)*.5) * (np.array([2.,1.,.56])/(high-low))
    with K.into('bench_slab'):
        for f, mat in zip(faces, mats):
            ao = .80 if mat == 'rock_inner' else .91
            K.face(points[list(f)],mat,color=(ao,ao,ao,1.))


def moored_boulder(K, name, variant, r):
    points, faces, ao, fresh = battered_body(431+variant*17, variant, 5, r, True)
    with K.into(name):
        mesh_faces(K, points, faces, ao, fresh=fresh)
        # Grouted twin-flange anchorage. Its hanging eye is the physical tow point.
        bottom = points[np.argmin(points[:, 2])]
        x, y, z = bottom
        with K.into(name+'_shoe', parent=name, loc=(x,y,z)):
            K.part()
            K.box((x,y,z+.42), (3.8,3.1,1.65),'steel_dark',13)
            for side in (-1,1):
                K.box((x,y+side*.92,z-.34),(2.15,.5,2.16),'steel_rust')
            K.pipe((x,y-1.47,z-.99),(x,y+1.47,z-.99),.36,'steel',12)
            for i in (-1,1):
                for j in (-1,1):
                    K.cyl((x+i*1.29,y+j*1.05,z-.40),.23,.26,'steel_rust',6)
        K.marker(name+'_attachment',(x,y,z-.99))
    dims=np.ptp(points,axis=0)/2
    long=int(np.argmax(dims))
    width=min(dims)
    proxy=[]
    for t in (-.34,0.,.34):
        center=np.zeros(3);center[long]=dims[long]*t
        proxy.append({'p':three(center),'r':float(width*(.85 if t else .99))})
    K.data['bodies'][name]={'radius':r,'spheres':proxy}


def tidy_polygon(vertices, epsilon=1e-7):
    if len(vertices)<3:
        return None
    pts=np.asarray(vertices)
    pts=pts[np.linalg.norm(pts-np.roll(pts,1,axis=0),axis=1)>epsilon]
    if len(pts)<3:
        return None
    af=pts-np.roll(pts,1,axis=0);bf=np.roll(pts,-1,axis=0)-pts
    area=np.linalg.norm(np.cross(af,bf),axis=1)
    pts=pts[area>epsilon*np.maximum(1.,np.linalg.norm(af,axis=1)+np.linalg.norm(bf,axis=1))]
    return pts if len(pts)>=3 else None


def clip_solid(faces, n, h, cut_material):
    """Clip all oriented polygons to n.x <= h. The new cap has outward normal n."""
    out, border = [], []
    for poly, mat in faces:
        d = poly@n-h
        if d.max()<=1e-8:
            out.append((poly,mat))
            continue
        if d.min()>1e-8:
            continue
        pts=[]
        for i,a in enumerate(poly):
            j=(i+1)%len(poly)
            ina=d[i]<=1e-8
            if ina:
                pts.append(a)
            if ina != (d[j]<=1e-8):
                mid=a+(poly[j]-a)*(d[i]/(d[i]-d[j]))
                pts.append(mid)
                border.append(mid)
        pts=tidy_polygon(pts)
        if pts is not None:
            out.append((pts,mat))
    if len(border)>=3:
        # An intersection point may be shared by more than two coplanar triangles.
        pts=np.asarray(list({tuple(np.round(v,7)):v for v in border}.values()))
        if len(pts)>=3:
            u=normalized(np.cross(n,[0.,0.,1.] if abs(n[2])<.9 else [0.,1.,0.]))
            v=np.cross(n,u);d=pts-pts.mean(axis=0)
            pts=tidy_polygon(pts[np.argsort(np.arctan2(d@v,d@u))])
            if pts is not None:
                out.append((pts,cut_material))
    return out


def volume_centroid(faces):
    volume=0.; moment=np.zeros(3)
    for p,_ in faces:
        a=p[0];b=p[1:-1];c=p[2:]
        t=np.cross(b-a,c-a)@a / 6.
        volume+=t.sum()
        moment+=(t[:,None]*(a+b+c)*.25).sum(axis=0)
    if volume<1e-10:
        raise ValueError('Unexpected empty or inward fracture cell')
    return volume,moment/volume


def asteroid_hull(rng,rad,variant):
    ds,tri=geodesic(2)
    h=[(4*ds[q], 'rock_dark') for q in tri]
    axes=np.array([1.01,.76,.89]) if not variant else np.array([.82,1.11,.79])
    for i in range(61):
        z=1-2*(i+.5)/61
        a=i*2.3999632297
        m=math.sqrt(1-z*z)
        n=normalized(np.array([m*math.cos(a),m*math.sin(a),z])+rng.normal(0,.06,3))
        support=np.linalg.norm(n*axes)*rng.uniform(.875,1.055)
        h=clip_solid(h,n,support,'rock_dark')
    largest=max(np.linalg.norm(p,axis=1).max() for p,mat in h)
    return [(p*(rad/largest),mat) for p,mat in h]


def seed_cells(rng,n,hull):
    normals=[]; offsets=[]
    for poly,mat in hull:
        outward=normalized(np.cross(poly[1]-poly[0],poly[2]-poly[0]))
        normals.append(outward);offsets.append(np.dot(outward,poly[0]))
    normals=np.asarray(normals);offsets=np.asarray(offsets)
    points=np.concatenate([p for p,_ in hull])
    lo=points.min(axis=0);hi=points.max(axis=0)
    candidates=rng.uniform(lo,hi,(3500,3))
    candidates=candidates[np.all(candidates@normals.T<offsets[None,:]*.94,axis=1)]
    seeds=[candidates[0]]
    for i in range(1,n):
        batch=candidates[rng.integers(0,len(candidates),12)]
        dist=np.linalg.norm(batch[:,None,:]-np.array(seeds)[None,:,:],axis=2).min(axis=1)
        seeds.append(batch[np.argmax(dist)])
    return np.asarray(seeds)


def voronoi(hull,sites,i,mat):
    faces=hull
    order=np.argsort(np.linalg.norm(sites-sites[i],axis=1))
    for j in order[1:]:
        n=normalized(sites[j]-sites[i])
        h=np.dot(n,(sites[i]+sites[j])*.5)
        faces=clip_solid(faces,n,h,mat)
    return faces


def weathered_panel(poly, rad, seed, pits):
    """Relieve an old outer facet. Its edges stay put, so the split still fits."""
    normal=normalized(np.cross(poly[1]-poly[0],poly[2]-poly[0]))
    edges=np.roll(poly,-1,axis=0)-poly
    inward=normalized(np.cross(normal,edges))
    divisions=int(np.clip(np.ceil(np.max(np.linalg.norm(edges,axis=1))/(rad*.13)),1,5))
    if divisions == 1:
        return [(poly,'rock_dark')]
    center=poly.mean(axis=0)
    patches=[]
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        rows=[]
        for i in range(divisions+1):
            tt=np.arange(divisions-i+1)[:,None]/divisions
            uv=center+(i/divisions)*(a-center)+tt*(b-center)
            rows.append(uv)
        for i in range(divisions):
            for j in range(divisions-i):
                patches.append([rows[i][j],rows[i+1][j],rows[i][j+1]])
                if j < divisions-i-1:
                    patches.append([rows[i+1][j],rows[i+1][j+1],rows[i][j+1]])
    pts=np.asarray(patches).reshape(-1,3)
    dist=np.min(np.einsum('ijk,jk->ij',pts[:,None,:]-poly[None,:,:],inward),axis=1)
    w=np.clip(dist/(rad*.068),0,1)
    w=w*w*(3.-2.*w)
    u=normalized(pts)
    # Existing impact bowls and rough oxidised rind survive only on the outer shell.
    erosion=.002+.006*field(u,4.5,seed)+.006*field(u,10.2,seed)
    for direction,width in pits:
        arc=np.linalg.norm(u-direction,axis=1)/width
        erosion+=.085*width*np.maximum(0.,1-arc*arc)**1.6
    pts-=normal*(rad*erosion*w)[:,None]
    return [(q,'rock_dark') for q in pts.reshape(-1,3,3)]


def fracture(K, name, variant, n, radius):
    seed=711+variant
    rng=np.random.default_rng(seed)
    hull=asteroid_hull(rng,radius,variant)
    total,body_com=volume_centroid(hull)
    hull=[(p-body_com,mat) for p,mat in hull]
    sites=seed_cells(rng,n,hull)
    pits=[(normalized(rng.normal(size=3)),rng.uniform(.12,.33)) for _ in range(11)]
    cells=[]; unweathered_volume=0.
    for i in range(n):
        cell=voronoi(hull,sites,i,'rock_inner')
        unweathered_volume+=volume_centroid(cell)[0]
        finish=[]
        for poly,mat in cell:
            if mat=='rock_dark':
                finish.extend(weathered_panel(poly,radius,seed,pits))
            else:
                finish.append((poly,mat))
        volume,center=volume_centroid(finish)
        cells.append((finish,volume,center))
    if abs(unweathered_volume/total-1.)>2e-6:
        raise ValueError(f'{name} Voronoi cells did not conserve the source hull')
    total=sum(v for cell,v,c in cells)
    com=sum(v*c for cell,v,c in cells)/total
    specs=[]
    with K.into(name):
        for i,(cell,vol,raw_center) in enumerate(cells):
            fragname=f'{name}_{i:02d}'
            center=raw_center-com
            with K.into(fragname,parent=name,loc=center):
                for poly,mat in cell:
                    # A uniform shrink reveals a hairline joint; COM stays fixed.
                    shown=center+(poly-raw_center)*.993
                    val=.81 if mat=='rock_inner' else .94
                    K.face(shown,mat,color=(val,val,val,1.))
            extent=max(np.linalg.norm(p-raw_center,axis=1).max() for p,_ in cell)
            effective=(3.*vol/(4.*math.pi))**(1/3)
            specs.append({'name':fragname,'p':three(center),'volume':float(vol*.993**3),'massFraction':float(vol/total),
                          'radius':float(effective*.88),'extent':float(extent*.993)})
    balance=np.linalg.norm(sum(np.asarray(c['p'])*c['massFraction'] for c in specs))
    if balance>2e-5:
        raise ValueError(f'{name} has a nonzero COM: {balance}')
    K.data['fractures'][name]=specs


def lunar_surface(direction, craters):
    """Relief and near-field occlusion on the old crust before it split."""
    coarse = field(direction,2.8,266)
    folded = field(direction,7.1,267)
    angular = field(direction,13.5,268)
    relief = .061*coarse + .037*folded + .017*angular
    # A long crooked scarp leaves a fault valley with only one raised wall.
    fault = direction @ normalized(np.array([.31,.83,.46])) + .14 + .15*coarse + .035*folded
    gorge = np.exp(-(fault/.055)**2)
    relief += .037*np.exp(-((fault-.078)/.049)**2) - .046*gorge
    ao = .91 + .07*coarse - .11*gorge
    for normal, width in craters:
        arc = np.linalg.norm(direction-normal,axis=1)/width
        arc *= 1 + .105*folded + .055*angular
        floor = np.maximum(0.,1.-arc*arc)**1.23
        rim = np.exp(-((arc-.99)/.19)**2)
        relief += width*(.097*rim-.323*floor)
        if width > .235:
            terrace = np.exp(-((arc-.70)/.11)**2)
            relief += width*(.080*np.exp(-(arc/.23)**2)+.043*terrace)
            ao += .035*terrace
        ao += .08*rim-.15*floor
    warp = np.column_stack([field(direction,2.75,seed)+.39*field(direction,8.,seed) for seed in (28,29,30)])
    twisted = normalized(direction+.105*(warp-direction*np.sum(warp*direction,axis=1)[:,None]))
    return twisted*(1+relief)[:,None], np.clip(ao,.52,1.)


def plate_boundary(normal, sites):
    """Unit great-circle intersections of one spherical Voronoi cell in winding order."""
    planes = normal-sites
    planes = planes[np.linalg.norm(planes,axis=1)>.01]
    corners = []
    for i, a in enumerate(planes):
        for b in planes[i+1:]:
            for p in (normalized(np.cross(a,b)),normalized(np.cross(b,a))):
                if np.min(planes@p)>-1e-8:
                    corners.append(p)
    corners = np.unique(np.round(corners,8),axis=0)
    across = normalized(np.cross(normal,[0.,0.,1.]))
    along = np.cross(normal,across)
    order = np.argsort(np.arctan2(corners@along,corners@across))
    return corners[order]


@lru_cache(maxsize=4)
def triangle_samples(divisions):
    weights = []
    indices = {}
    for i in range(divisions+1):
        for j in range(divisions-i+1):
            indices[i,j] = len(weights)
            weights.append(((divisions-i-j)/divisions,i/divisions,j/divisions))
    triangles = []
    for i in range(divisions):
        for j in range(divisions-i):
            triangles.append([indices[i,j],indices[i+1,j],indices[i,j+1]])
            if i+j < divisions-1:
                triangles.append([indices[i+1,j],indices[i+1,j+1],indices[i,j+1]])
    return np.asarray(weights), np.asarray(triangles)


def crust_plate(normal, outline, craters, seed):
    pieces = []
    divisions = 11
    weights, triangles = triangle_samples(divisions)
    boundary = []
    for a,b in zip(outline,np.roll(outline,-1,axis=0)):
        direction = normalized(weights@np.array([normal,a,b]))
        skin, ao = lunar_surface(direction,craters)
        pieces.append((skin,triangles,ao,'rock_moon'))
        t = np.arange(divisions)[:,None]/divisions
        boundary.extend(normalized(a+(b-a)*t))

    boundary = np.asarray(boundary)
    crest, crest_ao = lunar_surface(boundary,craters)
    radial = normalized(crest)
    toward_center = normalized(normal-radial*(radial@normal)[:,None])
    thickness = .46 + .054*field(boundary,3.7,seed)
    teeth = 1 + .50*field(boundary,8.4,seed) + .23*field(boundary,16.5,seed+1)
    radius = np.linalg.norm(crest,axis=1)
    n = len(crest)
    a = np.arange(n); b = np.roll(a,-1)
    side = np.vstack((np.column_stack((n+a,n+b,b)),np.column_stack((n+a,b,a))))
    top = crest
    top_ao = crest_ao
    # Successive harder and softer exposed beds form stepped, undercut rims.
    layers = [( .10, .010,.85,'rock_moon'),(.25,.066,.70,'rock_moon_inner'),
              ( .32, .024,.81,'rock_moon_inner'),(.58,.104,.66,'rock_moon_inner'),
              ( .72, .068,.72,'rock_moon_inner'),(1.,.15,.55,'rock_moon_core')]
    for depth, recess, light, name in layers:
        foot = normalized(radial + toward_center*(recess*teeth)[:,None]) * (radius-depth*thickness)[:,None]
        lower_ao = np.clip(light + .085*field(boundary,8.9,seed+2) + .035*teeth, .42,.95)
        pieces.append((np.vstack((top,foot)),side,np.r_[top_ao,lower_ao],name))
        top,top_ao = foot,lower_ao
    inside = np.vstack((top,normalized(top.mean(axis=0))*.49))
    cap = np.column_stack((np.full(n,n),b,a))
    pieces.append((inside,cap,np.r_[top_ao,.51],'rock_moon_core'))
    return pieces


def fractured_moon(K):
    rng=np.random.default_rng(907)
    seeds=[]
    for i in range(16):
        z=1-2*(i+.5)/16
        a=i*2.3999632297
        r=math.sqrt(1-z*z)
        seeds.append(normalized(np.array([r*math.cos(a),r*math.sin(a),z])+rng.normal(0,.24,3)))
    seeds=np.asarray(seeds)
    craters=[(normalized(rng.normal(size=3)),rng.uniform(.077,.23)) for _ in range(23)]
    # Two near-side basins fit inside surviving plates; older impacts also straddle joints.
    craters.extend([(seeds[5],.258),(seeds[2],.29),
                    (normalized(np.array([.84,-.48,-.22])),.24),(normalized(np.array([-.61,.66,-.22])),.31)])
    tail=normalized(np.array([.62,-.55,-.56]))
    detached=int(np.argmax(seeds@tail))
    plates=[]
    for i, outward in enumerate(seeds):
        cell = crust_plate(outward,plate_boundary(outward,seeds),craters,561+i)
        center = outward*.76
        pull=max(0.,np.dot(outward,tail))
        shift=outward*(rng.uniform(.013,.058)+pull**3*.23) + tail*pull**3*.08
        yaw=rng.uniform(-.065,.065)*(1+pull)
        if i == detached:
            shift+=np.array([.18,.04,-.15])
            yaw-=.33
        axis=normalized(np.cross(outward,[.47,-.82,.3]))
        for points, faces, ao, mat in cell:
            u=(points-center)*(.966-.071*pull)
            rotated=u*math.cos(yaw)+np.cross(axis,u)*math.sin(yaw)+(u@axis)[:,None]*axis*(1-math.cos(yaw))
            plates.append((center+shift+rotated,faces,ao,mat))
    satellites=[]
    for i in range(60):
        # Three ejecta families: a broken lip, a small loose arc and a fall line.
        scatter=normalized(tail+rng.normal(0,.30,3)) if i<40 else normalized(seeds[(i*7)%16]+rng.normal(0,.24,3))
        dist=rng.uniform(1.17,1.46)+(rng.uniform(0,.18) if i<13 else 0)
        size=rng.uniform(.018,.062)*(1.3 if i%7==0 else 1.)
        rock,fac,ao,_=battered_body(908+i%4,i%5,1,size)
        if i%3==0:
            # Detached, angular shingles retain the local bedding of the parent crust.
            tangent = normalized(np.cross(scatter,[0.,0.,1.]))
            along = np.cross(scatter,tangent)
            rock = (rock[:,0,None]*1.37*tangent + rock[:,1,None]*.76*along
                    + (rock[:,2,None]*.27+.11*rock[:,0,None])*scatter)
        satellites.append((rock+scatter*dist,fac,ao))
    largest=max(max(np.linalg.norm(p,axis=1).max() for p,_,_,_ in plates),max(np.linalg.norm(p,axis=1).max() for p,_,_ in satellites))
    with K.into('moon'):
        for points,faces,ao,mat in plates:
            mesh_faces(K,points/largest,faces,ao,mat)
        for pts,fac,ao in satellites:
            mesh_faces(K,pts/largest,fac,ao,'rock_moon')
        core,fac,ao,_=battered_body(94,1,3,.53/largest)
        mesh_faces(K,core,fac,ao,'rock_moon_core')
    K.data['moon']={'plates':16,'ejecta':60,'scaleRadius':1.,'intactRadius':1/largest}


def set_moon_materials():
    for name,rgb,em,power in [('rock_moon',(.072,.065,.083),(0.,0.,0.),0.),
                              ('rock_moon_inner',(.041,.030,.039),(.25,.022,.03),.011),
                              ('rock_moon_core',(.016,.011,.019),(.30,.018,.028),.016)]:
        mat=material(name)
        mat.diffuse_color=(*rgb,1.)
        bsdf=mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(*rgb,1.)
        bsdf.inputs['Emission Color'].default_value=(*em,1.)
        bsdf.inputs['Emission Strength'].default_value=power


def shade_lunar_crust(mesh):
    """Blend normals across the eroded skin, retaining the sharp cut through each plate."""
    loops = np.empty(len(mesh.loops),dtype=np.int32)
    mesh.loops.foreach_get('vertex_index',loops)
    positions = np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',positions)
    points = positions.reshape(-1,3)[loops]
    triangles = points.reshape(-1,3,3)
    area = np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    materials = np.empty(len(mesh.polygons),dtype=np.int32)
    mesh.polygons.foreach_get('material_index',materials)
    skin = materials == mesh.materials.find('rock_moon')
    skin_loops = np.flatnonzero(np.repeat(skin,3))
    face_area = area[skin_loops//3]
    face_normal = normalized(face_area)
    normals = np.zeros_like(points)
    keys = np.rint(points[skin_loops]*500000).astype(np.int32)
    _, group = np.unique(keys,axis=0,return_inverse=True)
    order = np.argsort(group)
    boundaries = np.flatnonzero(np.diff(group[order]))+1
    for adjacent in np.split(order,boundaries):
        disk = face_normal[adjacent]
        # Keep detached chips angular and crests crisp even when sharing an edge.
        compatible = disk@disk.T > .72
        blended = normalized(compatible@face_area[adjacent])
        normals[skin_loops[adjacent]] = normalized(.87*blended+.13*disk)
    mesh.polygons.foreach_set('use_smooth',skin)
    mesh.normals_split_custom_set(normals.tolist())


def segment_distance(x,y,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy),0.,1.)
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)


def free_talus(x,y,clearance):
    for _,width,path in ROADS:
        if any(segment_distance(x,y,a,b)<width*.5+clearance+1.85 for a,b in zip(path,path[1:])):
            return False
    for _,cx,cy,sx,sy,rot,z in PADS:
        a=math.radians(rot);dx=x-cx;dy=y-cy
        if abs(dx*math.cos(a)+dy*math.sin(a))<sx*.5+clearance and abs(-dx*math.sin(a)+dy*math.cos(a))<sy*.5+clearance:
            return False
    co=math.cos(PIT_ROT);si=math.sin(PIT_ROT);dx=x-PIT_C[0];dy=y-PIT_C[1]
    if math.hypot((co*dx+si*dy)/PIT_A,(-si*dx+co*dy)/PIT_B)<1.025:
        return False
    # Reserved spaces for the wreck, quarry gantry, foundry, listening array and relics.
    for cx,cy,rx,ry in [(-36,-184,97,25),(-66,-98,58,17),(-160,-74,28,20),(66,-157,38,28),
                         (122,-116,20,18),(-59,159,22,22),(28,14,11,18),(212,-55,19,22),
                         (-177,-53,20,18),(-156,47,19,19),(239,-88,35,27)]:
        if ((x-cx)/(rx+clearance))**2+((y-cy)/(ry+clearance))**2<1:
            return False
    return all(math.hypot(x-cx,y-cy)>r*.58+clearance for cx,cy,r,_ in CRATERS)


def dressed_talus(K):
    rng=np.random.default_rng(3198)
    prototypes=[battered_body(231+i,i,2,1.)[:3] for i in range(12)]
    # Eroded ridge talus, discard fans and fractured shelf edges form irregular clusters.
    fans=[(-155,98,34,22),(-116,139,37,20),(-51,190,28,13),(-161,-113,37,22),
          (-111,-152,30,16),(-178,-39,28,17),(118,-79,19,19),(204,-137,16,21),(33,171,21,18)]
    placed=[]
    for attempt in range(40000):
        if len(placed)==263:
            break
        if rng.random()<.72:
            cx,cy,sx,sy=fans[rng.integers(len(fans))]
            x=rng.normal(cx,sx);y=rng.normal(cy,sy)
        else:
            x=rng.uniform(-222,282);y=rng.uniform(-216,218)
        r=.83+3.25*rng.random()**2.75
        if rng.random()<.035:
            r+=rng.uniform(1.3,2.8)
        z=G.z(x,y)
        if z< -22. or not free_talus(x,y,r):
            continue
        near=[G.z(x+r,y),G.z(x-r,y),G.z(x,y+r),G.z(x,y-r)]
        if min(near)<-30 or max(near)-min(near)>2.65*r:
            continue
        if any((x-ox)**2+(y-oy)**2<(.90*(r+oldr))**2 for ox,oy,oldr in placed):
            continue
        coords,faces,ao=prototypes[len(placed)%len(prototypes)]
        yaw=rng.uniform(0.,math.tau)
        rotation=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1.]])
        coords=(coords*np.array([1,rng.uniform(.77,1.15),rng.uniform(.58,.98)])*r)@rotation.T
        # Seat each fragment part-way into local regolith, following its average tangent plane.
        dzdx=(near[0]-near[1])/(2*r);dzdy=(near[2]-near[3])/(2*r)
        lows=coords[:,2]-.65*(coords[:,0]*dzdx+coords[:,1]*dzdy)
        center=np.array([x,y,z-lows.min()-r*.30])
        shade=ao*(.56+.44*np.clip((lows-lows.min())/(r*.59),0.,1.))
        mesh_faces(K,coords+center,faces,shade)
        placed.append((x,y,r))
        K.data['scatter'].append({'p':three(center),'r':float(r)})
    if len(placed)!=263:
        raise ValueError('Could not reserve enough clear talus positions')


def build(out,log):
    K=Kit('rocks',98)
    K.data.update(bodies={},fractures={},scatter=[])
    set_moon_materials()
    for i,(name,r) in enumerate(zip(('boulder_a','boulder_b','boulder_c'),(24.,20.,16.))):
        moored_boulder(K,name,i,r)
    fracture(K,'ast_A',0,32,14.5)
    fracture(K,'ast_B',1,33,13.6)
    for i,name in enumerate(('chunk_a','chunk_b','chunk_c','rubble_a','rubble_b')):
        level=1 if i<3 else 2
        p,f,ao,_=battered_body(104+i,i,level,1)
        with K.into(name):
            mesh_faces(K,p,f,ao)
    with K.into('chain_link'):
        forged_link(K)
    bench_slab(K)
    fractured_moon(K)
    dressed_talus(K)
    # The triplanar rock shader reads local positions, normals and corner AO.
    # Keep the metre-scale UVs on steel fittings and omit both unused streams
    # from natural rock. Blender can then also share coplanar face vertices.
    with TemporaryDirectory(dir=out) as staging:
        staging = Path(staging)
        K.finalize(staging,log)
        for mesh in bpy.data.meshes:
            if mesh.name == 'moon_surface':
                shade_lunar_crust(mesh)
            if mesh.materials and all(mat.name.startswith('rock_') for mat in mesh.materials):
                while mesh.uv_layers:
                    mesh.uv_layers.remove(mesh.uv_layers[-1])
        export_glb(staging/'rocks.glb')
        for file in ('rocks.glb','rocks.json'):
            (staging/file).replace(Path(out)/file)
