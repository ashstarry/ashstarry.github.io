"""Workers' hill, its rotating pressure hull, and the reclaimed-water loop."""
import math

from mathutils import Vector

from lib.ground import G
from lib.kit import Kit
from lib.layout import TOWER_POS


Z = Vector((0, 0, 1))
WARM = (1.0, .53, .26)
COOL = (.62, .80, 1.)


def chamfer_ring(x, y, z, width, depth, cut):
    a, b = width / 2, depth / 2
    c = min(cut, a * .7, b * .7)
    return [(x + dx, y + dy, z) for dx, dy in [
        (-a+c, -b), (a-c, -b), (a, -b+c), (a, b-c),
        (a-c, b), (-a+c, b), (-a, b-c), (-a, -b+c)]]


def casing(k, x, y, tiers, mat):
    k.loft([chamfer_ring(x, y, z, w, d, cut) for z, w, d, cut in tiers], mat)


def cowl(k, x, y, z, radius):
    k.part()
    k.lathe((x, y, z), [(0, radius*.96), (.4, radius), (.72, radius*.95)], 'hull_grey', 18)
    k.cyl((x, y, z+.74), radius*.87, .12, 'metal_dark', 18)
    for a in (18, 90, 162, 234, 306):
        angle = math.radians(a)
        k.box((x+radius*.42*math.cos(angle), y+radius*.42*math.sin(angle), z+.87),
              (.85*radius, radius*.23, .13), 'steel_dark', a+16)
    k.cyl((x, y, z+.96), radius*.18, .3, 'steel', 10)


def gallery_block(k, cx, cy, z, sx, sy, rooms, style):
    """A setback core behind concrete floor trays. The glazing occupies the reveal."""
    finish = ('conc_warm', 'conc', 'hull_grey')[style]
    level = 3.18
    lobby = z+2.8
    front, right = cy-sy*.5, cx+sx*.5
    roof = lobby+rooms*level
    k.part()
    casing(k, cx, cy, [(z-.28, sx+1.5, sy+1.2, 1.8), (z+.66, sx+1.5, sy+1.2, 1.8),
                       (z+1.4, sx-.2, sy-.3, 1.5)], 'conc_dark')
    casing(k, cx-.65, cy+.65,
           [(z+.75,sx-2.9,sy-2.4,1.4),(lobby,sx-1.8,sy-2.05,1.45),
            (roof+.15,sx-1.8,sy-2.05,1.55)], finish)
    k.part()
    # Cast-in stair core, slightly offset from the roof and occupied gallery floors.
    core_x, core_y = cx-sx*.31, cy+sy*.24
    casing(k, core_x, core_y, [(z+.8, 5.3, sy*.61, .75),
                               (roof+1.9, 4.5, sy*.57, .82),
                               (roof+3.05, 3.4, sy*.43, .78)], 'conc_warm')
    for dx in (-.39, .18, .40):
        xx = cx+sx*dx
        k.beam((xx, front+1.1, z+.85), (xx, front+.22, lobby+.5), .92, 1.25, 'conc_dark')
    k.box((cx+.10*sx, front+1.43, z+1.8), (3.4,.18,2.05), 'metal_dark')
    k.box((cx+.10*sx+.45, front+1.32, z+1.75), (1.72,.14,1.77), 'metal_green')
    k.box((cx+.10*sx, front+.12, lobby+.24), (5.15,2.75,.37), 'steel_dark')

    for lev in range(rooms):
        fz = lobby+lev*level
        setback = .78 if lev == rooms-1 and rooms >= 4 else 0
        width = sx-2*setback
        # A narrow exposed front soffit reveals the thickness of each cast floor.
        k.part()
        lip = 1.05 if (lev+style)%3 == 0 else .50
        casing(k, cx, cy+.06+setback*.35,
               [(fz-.18, width+.2, sy+lip-.75*setback,.95),
                (fz+.22, width+.2, sy+lip-.75*setback,.95),
                (fz+.34, width-.24, sy+lip-.42-.75*setback,.91)], 'conc_dark' if lev%3==0 else finish)
        intervals = ((-.45,-.12),(-.085,.10),(.15,.43))
        for j,(start,end) in enumerate(intervals):
            a, b = cx+width*start, cx+width*end
            px, pw = .5*(a+b), b-a
            depth = .49+.20*((style+j)%2)
            wy = front+1.30+setback*.23
            k.box((px,wy,fz+1.68), (pw,.32,2.01), 'metal_dark')
            # Some suites have one double pane, others a dark vent next to lit glass.
            panes = 2 if pw>4 else 1
            for m in range(panes):
                k.part(k.rng.random())
                span = (pw-.67)/panes
                pane_x = a+.335+span*(m+.5)
                pane_mat = 'emit_warm' if (lev*7+j*3+m+style)%9 in (0,1,3,4,6) else 'glass'
                k.box((pane_x,wy-.175,fz+1.70), (span-.20,.10,1.15), pane_mat)
            # Projecting mineral-concrete jambs sit outside the glazing.
            k.box((a-.17, wy-depth/2-.12, fz+1.60), (.45,depth+.85,2.74), finish)
            if (lev+j+style)%3 == 0:
                k.beam((px-pw*.40,wy-.23,fz+.86),
                       (px+pw*.40,wy-.23,fz+.86),.15,.22,'steel_rust')
        for j,off in enumerate((-.24,.16)):
            yy = cy+sy*off
            k.part(k.rng.random())
            k.box((right-1.43,yy,fz+1.70), (.26,sy*.27,1.88),'metal_dark')
            k.box((right-1.26,yy+.11,fz+1.75),(.10,sy*.22,1.05),
                  'emit_warm' if (lev+j+style)%4!=1 else 'glass')
            k.box((right-1.10,yy+sy*.153,fz+1.66),(.90,.54,2.87),finish)
    k.part()
    casing(k,cx,cy+.20,[(roof-.18,sx+.1,sy+.25,.97),(roof+.52,sx+.15,sy+.27,1.04),
                         (roof+.71,sx-.53,sy-.46,.96)],finish)
    # Raised sills on three sides leave an open service landing at the fourth corner.
    k.beam((cx-sx*.38,front+.42,roof+.95),(cx+sx*.40,front+.42,roof+.95),.36,.53,finish)
    k.beam((right-.43,front+1.3,roof+.95),(right-.43,cy+sy*.35,roof+.95),.37,.53,finish)
    k.beam((cx-sx*.36,cy+sy*.43,roof+.95),(cx+sx*.34,cy+sy*.43,roof+.95),.41,.52,finish)
    casing(k,cx+sx*.12,cy+sy*.05,
           [(roof+.61,6.15,4.7,.66),(roof+2.22,6.15,4.7,.66),
            (roof+2.83,5.15,3.7,.58)],'metal_teal' if style!=2 else 'hull_rust')
    cowl(k,cx+sx*.12,cy+sy*.05,roof+2.82,1.22)
    pipex, pipey = cx-sx*.42, cy-sy*.12
    k.pipe((pipex,pipey,z+2), (pipex,pipey,roof+1.64), .37, 'steel_rust', 9)
    k.pipe((pipex,pipey,roof+1.64),(core_x,core_y,roof+1.64),.37,'steel_rust',9)
    k.light((cx+.10*sx,front-.32,lobby+.05),WARM,14,.68,'window')
    k.light((right-.3,cy,roof-level*1.1),WARM,16,.54,'window')
    k.light((cx-sx*.20,front-.35,lobby+rooms*level*.58),WARM,15,.59,'window')


def slab_block(k, cx, cy, z, sx, sy, h, paint, levels):
    r = k.rng
    k.part()
    k.box((cx,cy,z+.65),(sx+2.5,sy+2.8,1.3),'conc_dark')
    casing(k,cx,cy,[(z+.9,sx-.8,sy-.6,1.15),(z+2.1,sx,sy,1.2),
                      (z+h+.8,sx,sy,1.18)],paint)
    casing(k,cx,cy,[(z+h+.42,sx+.55,sy+.55,1.20),(z+h+1.10,sx+.88,sy+.95,1.24),
                      (z+h+1.35,sx+.36,sy+.33,1.10)],'conc')
    front = cy-sy/2
    for i in (-.43,.04,.43):
        k.box((cx+sx*i,front-.42,z+h*.54),(1.45,1.6,h*.98),'conc_warm')
    for l in range(levels):
        zz=z+3+l*3.15
        cols=max(2,int(sx/3.7))
        for i in range(cols):
            if (i==cols//2 and l==0) or r.random()<.12:
                continue
            xx=cx+(i+.5-cols/2)*sx/(cols+.4)
            k.part(r.random())
            k.box((xx,front-.08,zz),(2.15,.24,1.35),'metal_dark')
            k.box((xx+.1,front-.222,zz+.08),(1.73,.07,.82),'emit_warm' if r.random()>.18 else 'glass')
        if l%2==0:
            k.box((cx-.6,front-.85,zz-.83),(sx-1,1.8,.45),'conc_dark')
        for j in range(max(2,int(sy/4.3))):
            k.part(r.random())
            k.box((cx+sx/2+.07,cy-sy*.36+j*3.55,zz),(.15,1.7,.84),'emit_warm' if r.random()>.34 else 'glass')
    k.part()
    casing(k,cx-sx*.11,cy+sy*.12,[(z+h+1.30,6.0,4.55,.62),(z+h+2.35,6.0,4.55,.62),
                                     (z+h+2.90,5.25,3.73,.60)],'metal_teal')
    cowl(k,cx+sx*.24,cy-sy*.1,z+h+1.34,1.15)
    k.pipe((cx-sx*.36,front-.95,z+1.6),(cx-sx*.36,front-.95,z+h+1.45),.32,'steel_rust')
    k.box((cx+sx*.18,front-1.1,z+3.9),(5.4,3.1,.55),'metal_green')
    k.lamp((cx+sx*.18-2,front-2,z+1),3,r=14,col=WARM)
    for p in range(max(1,int(sx/9))):
        k.light((cx-sx*.35+p*8,front-1,z+h*.55),WARM,14,.54,'window')


def ring_point(angle, radius, z):
    return Vector((TOWER_POS[0]+radius*math.cos(angle),TOWER_POS[1]+radius*math.sin(angle),z))


def sweep(k, start, end, profile, faces, end_mat, spans):
    """Sweep a radial-height section in plan; its forward perimeter bounds the start cap."""
    rings = [[ring_point(start+(end-start)*i/spans,r,z) for r,z in profile] for i in range(spans+1)]
    for near,far in zip(rings,rings[1:]):
        for j,finish in enumerate(faces):
            jj = (j+1)%len(profile)
            k.face([near[j],far[j],far[jj],near[jj]],finish)
    k.face(rings[0],end_mat)
    k.face(rings[-1][::-1],end_mat)


def ring_barracks(k):
    x,y = TOWER_POS
    # Fixed service race and circulating pressure collar are different radial envelopes.
    k.lathe((x,y,0),[(49.5,8.0),(50.8,9.1),(52.6,9.1),(53.2,8.65)],'steel_dark',32)
    k.torus((x,y,52.4),8.95,.40,'steel_rust',40,6)
    k.lathe((x,y,0),[(59.0,8.4),(60.0,9.45),(61.4,9.45),(62.1,8.65)],'metal_grey',32)
    with k.into('hab_ring',loc=(x,y,56)):
        k.lathe((x,y,0),[(53.6,9.05),(54.4,10.4),(57.2,10.4),(58.55,9.1)],'metal_dark',32)
        for z,major,minor,mat in [(53.55,33.1,.65,'steel_rust'),(54.04,36.25,.32,'steel_dark'),
                                  (54.1,10.13,.31,'steel'),(58.0,9.6,.25,'steel_rust')]:
            k.torus((x,y,z),major,minor,mat,64 if major>20 else 40,6)
        span = math.tau/12
        casing_colours = ('hull_grey','metal_green','hull_white','hull_grey','hull_grey','hull_rust',
                          'hull_white','hull_grey','metal_green','hull_grey','hull_grey','hull_white')
        for i,paint in enumerate(casing_colours):
            k.part()
            a=i*span+.07
            # Top and bottom shoulders overhang the inset side windows.
            profile=[(33.3,53.65),(35.7,53.65),(37.57,54.72),(37.57,55.09),
                     (36.86,55.29),(36.86,57.05),(37.55,57.23),(37.51,57.60),
                     (36.37,58.62),(33.45,58.62),(32.58,57.54),(32.55,55.27)]
            skins=('steel_dark','hull_dark',paint,'steel_dark','metal_dark','steel_dark',
                   'hull_dark',paint,paint,paint,'hull_dark','hull_dark')
            sweep(k,a+.012,a+span-.013,profile,skins,'steel_dark',4)
            # Expansion joint between cabins. Its recess reads as a soft shadow from afar.
            joint=[(33.5,53.91),(35.8,53.91),(37.04,55.06),(36.67,56.88),
                   (37.05,57.37),(36.15,58.24),(33.62,58.24),(32.83,57.24)]
            sweep(k,a-.016,a+.014,joint,['rubber']*8,'hull_dark',1)
            portholes = (4,3,4,2)[i%4]
            for j in range(portholes):
                k.part(k.rng.random())
                centre = a+span*((j+1)/(portholes+1))
                half = .030 if portholes>2 else .039
                # Faces are parallel to the faceted hull. The sills bridge the reveal.
                aperture=[(36.91,55.53),(37.12,55.63),(37.12,56.78),(36.91,56.87)]
                sweep(k,centre-half,centre+half,aperture,
                      ['metal_dark','emit_warm' if (2*i+j)%7 not in (1,5) else 'glass',
                       'metal_dark','hull_dark'],'metal_dark',1)
            if i in (0,3,7,10):
                short=a+.21
                k.part()
                top=ring_point(short,34.85,58.82)
                k.box(top,(4.1,2.05,.40),'hull_rust' if i==3 else 'hull_dark',math.degrees(short)+90)
                k.cyl((top.x,top.y,59.14),.68,.30,'metal_grey',12)
                k.light(ring_point(a+.14,37.4,56.6),WARM,13,.63,'window')
            if i in (1,6,9):
                inner=ring_point(a+.26,32.7,56.07)
                k.box(inner,(4.2,1.45,2.45),'metal_green',math.degrees(a+.26)+90)
                k.lamp(inner+Vector((0,0,.15)),1.54,col=WARM,r=10,power=.4)

        # Two pressure transfer corridors carry crew. A triangulated pair carries torque.
        for i in range(4):
            a=.07+(i+.5)*math.pi/2
            end=ring_point(a,33.6,55.02)
            start=ring_point(a,9.4,56.65)
            side=Vector((-math.sin(a),math.cos(a),0))
            if i%2==0:
                k.part()
                k.beam(start,end,2.9,2.1,'hull_grey')
                k.beam(start+Z*1.00,end+Z*1.0,2.52,.24,'metal_green')
                for along in (.12,.55,.91):
                    p=start.lerp(end,along)
                    k.box(p,(1.0,3.28,2.49),'metal_dark',math.degrees(a))
                for sign in (-1,1):
                    k.beam(start+side*1.2-Z*1.02, end+side*1.2-Z*1.02,.32,.38,'steel_rust')
            else:
                k.part()
                k.truss(start,end,2.35,2.20,'steel_dark',4,.39)
                for sign in (-1,1):
                    k.beam(ring_point(a,9.4,54.15)+side*2.15*sign,
                           ring_point(a,18.4,55.57)+side*.85*sign,.53,.59,'hull_grey')
            for sign in (-1,1):
                k.beam(ring_point(a,27.8,54.95)+side*.85*sign,
                       ring_point(a+sign*.095,34.3,54.28),.58,.59,'steel_rust')


def covered_link(k, a, b, width):
    a,b=Vector(a),Vector(b)
    direction=(b-a).normalized()
    side=Z.cross(direction).normalized()
    up=direction.cross(side).normalized()
    def section(p):
        return [p+side*s+up*h for s,h in [
            (-width*.5,0),(width*.5,0),(width*.5,1.92),(width*.35,2.86),
            (-width*.35,2.86),(-width*.5,1.92)]]
    # Actual right/left glazed reveals are built above a deep sill.
    k.beam(a+up*.10,b+up*.10,width+.18,.45,'hull_dark')
    for s in (-1,1):
        aa=a+side*(s*(width*.5-.11));bb=b+side*(s*(width*.5-.11))
        k.beam(aa+up*.60,bb+up*.60,.26,.86,'metal_green')
        k.beam(aa+up*1.39,bb+up*1.39,.12,.83,'glass_warm')
        k.beam(aa+up*1.91,bb+up*1.91,.30,.31,'hull_grey')
    p,q=section(a),section(b)
    for i in (2,3,4):
        k.face([p[i],p[i+1],q[i+1],q[i]],'hull_grey' if i!=3 else 'metal_grey')
    for t in (.08,.51,.91):
        r=section(a.lerp(b,t))
        for j in range(1,6):
            k.beam(r[j],r[(j+1)%6],.27,.29,'steel_dark')
    for t in (.17,.83):
        k.light(a.lerp(b,t)+up*1.62,WARM,8.5,.40,'window')
    mid=a.lerp(b,.5)
    if (b-a).length>12:
        for s in (-1,1):
            p=mid+side*s*(width*.50-.15)
            foot=G.z(p.x,p.y)
            k.cyl((p.x,p.y,foot+.27),.77,.73,'conc_dark',8)
            k.beam((p.x,p.y,foot+.5),p,.47,.53,'steel_dark')


# Plan axes of the damper frame. Its open side faces the southeast overview.
TOWER_ANGLE = 18.0
TOWER_COS = math.cos(math.radians(TOWER_ANGLE))
TOWER_SIN = math.sin(math.radians(TOWER_ANGLE))


def tower_point(u, v, z):
    x, y = TOWER_POS
    return Vector((x + TOWER_COS*u - TOWER_SIN*v, y + TOWER_SIN*u + TOWER_COS*v, z))


def tower_shell(k, levels, finish):
    """Tapered eight-sided casting in the local axes of the tower."""
    rings = []
    for z, u, v, width, depth, cut in levels:
        rings.append([tower_point(px, py, pz) for px, py, pz in chamfer_ring(u, v, z, width, depth, cut)])
    k.loft(rings, finish)


def tower_box(k, u, v, z, size, finish):
    k.box(tower_point(u, v, z), size, finish, TOWER_ANGLE)


def tower_skirt(k):
    x, y = TOWER_POS
    k.part()
    tower_shell(k, [(9.8,0,0,36.2,31.8,5.5), (11.8,0,0,36.2,31.8,5.5),
                    (13.3,0,0,33.2,28.8,4.9)], 'conc_dark')
    tower_shell(k, [(12.3,0,.7,26.8,23.5,4.8), (21.8,0,.75,26.1,22.4,4.6),
                    (32.0,0,1,20.4,18.2,4.3), (48.4,0,.25,14.7,13.9,3.6),
                    (52.4,0,0,14.1,13.6,3.6)], 'conc')
    k.lathe((x,y,0), [(48.2,7.75),(51.2,8.09),(53.3,7.76),(60.6,7.73),(64.3,7.20)],'conc_dark',24)
    # Each pair of battered feet fans out onto a separate cast-in bearing. The tips
    # stop below the 52.8–59.3 m swept volume of the moving hub and spokes.
    for side in (-1,1):
        for end in (-1,1):
            k.part()
            levels=[(11.6,side*12.3,end*9.3,7.2,6.0,1.0),
                    (15.1,side*12.5,end*9.47,7.2,6.0,.8),
                    (26.4,side*10.5,end*8.3,5.8,5.0,.76),
                    (39.6,side*7.7,end*6.2,4.8,4.4,.62),
                    (50.5,side*5.95,end*4.9,3.6,3.5,.57)]
            tower_shell(k,levels,'conc_warm' if side==end else 'conc')
            if side!=end:
                k.tube([tower_point(side*14.1,end*11.65,14),tower_point(side*13.8,end*11.5,18),
                        tower_point(side*9.35,end*7.95,37.3),tower_point(side*7.28,end*6.27,48.7)],.41,'steel_rust',10)
    # A personnel connection enters the southeast footing from the covered residential corridor.
    tower_box(k,8.3,-6.9,20.70,(4.1,3.6,3.46),'hull_dark')
    # Removable access doors in the slab between the two front buttresses.
    tower_box(k,-.36,-10.83,19.27,(6.93,.51,5.93),'metal_dark')
    for u,width in ((-1.86,2.75),(1.11,2.64)):
        tower_box(k,u,-11.18,18.79,(width,.31,4.39),'metal_green')
        tower_box(k,u+.72,-11.43,18.51,(.18,.23,1.28),'steel')
    tower_box(k,-.37,-11.32,22.58,(8.05,2.15,.71),'conc_warm')
    ring_barracks(k)


def damper_bay(k, suffix, u, rest_z, paint):
    """One suspended weight, two guide shoes and a single-acting accumulator ram."""
    v = -8.25
    top_z = rest_z + 28.0
    radius = 2.02
    name = 'tuner_' + suffix
    k.part()
    # The steel cheek webs lie to the rear; the block remains exposed on the front.
    for du in (-4.77,4.77):
        rail = u+du
        tower_box(k,rail,v+.74,rest_z+1.1,(.64,1.48,42.7),'steel_dark')
        tower_box(k,rail,v-.09,rest_z+1.15,(.76,.33,40.6),'steel')
        for z in (rest_z-19.15, rest_z+19.50):
            tower_box(k,rail,v+1.58,z,(1.53,3.65,1.29),'hull_rust')
        k.beam(tower_point(rail,v+3.35,rest_z-18.9),tower_point(rail,v+3.86,top_z-.63),1.08,1.55,'hull_dark')
        k.beam(tower_point(rail,v+3.44,rest_z-18.65),tower_point(rail*.85,1.8,90.50),1.05,1.66,'hull_dark')
    k.beam(tower_point(u,v+3.44,top_z-.65),tower_point(.70*u,2.3,top_z-1.63),2.27,2.42,'hull_dark')
    k.beam(tower_point(u-5.15,v+3.50,top_z-.65),tower_point(u+5.15,v+3.50,top_z-.65),2.31,2.85,'hull_grey')
    for du in (-2.55,2.55):
        k.beam(tower_point(u+du*1.6,v+3.32,rest_z-17.5),
               tower_point(u-du*1.62,v+3.38,rest_z+1.75),.58,.73,'steel_rust')
    # This fixed accumulator receives the polished rod on the travelling mass.
    k.lathe(tower_point(u,v-.11,rest_z),[(-47.4,1.76),(-46.4,2.24),(-43.5,2.13),
            (-41.6,1.64),(-22.0,1.64),(-21.5,1.92),(-20.15,1.92),(-19.65,1.34)],'metal_green',16)
    for z in (rest_z-44.2,rest_z-21.05):
        k.cyl(tower_point(u,v-.11,z),1.97,.55,'hull_grey',16)
    k.tube([tower_point(u+1.65,v,rest_z-42.4),tower_point(u+2.92,v+.45,rest_z-42.4),
            tower_point(u+2.92,v+2.4,rest_z-42.4),tower_point(u+2.92,v+2.4,rest_z-37.0)],.29,'steel_rust',10)
    tower_shell(k,[(rest_z-46.5,u,v+.35,5.25,6.90,.76),
                   (rest_z-43.8,u,v+.35,5.25,6.90,.76)],'conc_dark')
    k.beam(tower_point(u,v+2.1,rest_z-45.4),tower_point(.46*u,1.1,rest_z-46.4),2.1,2.35,'hull_dark')
    # A four-spoke differential sheave. One rope leg goes down to the weight, the
    # return enters the accumulator drum through the brake housing on the backplate.
    axis = Vector((-TOWER_SIN,TOWER_COS,0))
    sheave = tower_point(u,v,top_z)
    with k.into(name+'_sheave',loc=sheave):
        k.torus(sheave,radius-.16,.28,paint,28,7,axis)
        k.torus(sheave+axis*.30,radius-.17,.23,'steel_dark',28,6,axis)
        k.pipe(sheave-axis*.81,sheave+axis*1.62,.56,'hull_grey',14)
        for theta in (12,102,192,282):
            a=math.radians(theta)
            tip=tower_point(u+(radius-.27)*math.cos(a),v,top_z+(radius-.27)*math.sin(a))
            k.beam(sheave,tip,.39,.32,'metal_grey')
    k.pipe(sheave+axis*.70,sheave+axis*3.22,.72,'steel_dark',12)
    k.tube([tower_point(u+radius*math.cos(i*math.pi/12),v+.09,
                        top_z+radius*math.sin(i*math.pi/12)) for i in range(13)],.15,'steel',7)
    k.pipe(tower_point(u-radius,v+.09,top_z),tower_point(u-radius,v+.09,top_z-5.7),.15,'steel',8)
    tower_box(k,u-radius,v+.5,top_z-5.93,(1.77,1.77,2.40),'metal_green')
    k.beam(tower_point(u-radius,v+.95,top_z-6.2),tower_point(u-4.5,v+3.4,top_z-7.4),1.03,1.40,'hull_dark')
    outer = -1 if u<0 else 1
    # A bracket outside the swept block carries a low work flood pointing into the bay.
    k.beam(tower_point(u+outer*4.81,v+.83,rest_z+8.37),
           tower_point(u+outer*5.32,v-2.11,rest_z+7.54),.33,.42,'steel_dark')
    tower_box(k,u+outer*5.32,v-2.18,rest_z+7.54,(1.14,1.12,.56),'hull_dark')
    tower_box(k,u+outer*5.31,v-2.18,rest_z+7.22,(.85,.68,.10),'emit_cool')
    k.light(tower_point(u+outer*3.95,v-3.20,rest_z+6.65),COOL,20,.86,'window')
    eye = tower_point(u+radius,v+.09,rest_z+6.34)
    tangent = tower_point(u+radius,v+.09,top_z)
    k.marker(name+'_head',tangent,axis)
    with k.into(name+'_pendant',loc=tangent):
        k.pipe(tangent,eye,.16,'steel',9)
    k.marker(name+'_eye',eye)
    k.marker(name+'_low',tower_point(u,v,rest_z-12.0),(0,0,1))
    k.marker(name+'_high',tower_point(u,v,rest_z+12.0),(0,0,1))
    with k.into(name+'_mass',loc=tower_point(u,v,rest_z)):
        k.part()
        tower_shell(k,[(rest_z-6.03,u,v,6.55,4.75,.82), (rest_z-4.59,u,v,8.47,6.62,.91),
                       (rest_z+1.8,u,v,8.47,6.62,.91), (rest_z+4.79,u,v,7.71,5.91,.76),
                       (rest_z+5.77,u,v,6.48,4.77,.74)],'conc_warm')
        # Sacrificial wear plate wraps the leading face. Its dark skirt and two
        # shouldered cast slabs remain legible from the overview.
        tower_shell(k,[(rest_z-4.72,u,v-.10,8.52,6.72,.83),(rest_z-3.48,u,v-.10,8.85,6.9,.88),
                       (rest_z-2.69,u,v-.10,8.66,6.8,.89)],'metal_dark')
        tower_shell(k,[(rest_z+.44,u,v-.13,8.6,6.84,.86),(rest_z+3.52,u,v-.13,8.38,6.66,.81),
                       (rest_z+4.55,u,v-.13,7.81,6.25,.76)],paint)
        for du in (-3.05,3.02):
            tower_box(k,u+du,v-3.34,rest_z-.92,(.48,.38,6.48),'steel_rust')
        tower_box(k,u+1.20,v-3.50,rest_z+1.7,(2.9,.18,.52),'hull_white')
        # The tapered central shoe carries load straight into the ram rather than
        # through the thinner jacket. Large recessed pin bosses tie both cheeks together.
        tower_shell(k,[(rest_z-6.45,u,v-.18,3.22,3.70,.62),(rest_z-5.54,u,v-.20,4.42,4.12,.71),
                       (rest_z-4.25,u,v-.23,5.32,4.82,.84)],'hull_dark')
        for du in (-2.84,2.79):
            boss=tower_point(u+du,v-3.24,rest_z-1.32)
            k.pipe(boss,boss-axis*.38,.88,'hull_grey',14)
            k.pipe(boss-axis*.40,boss-axis*.49,.55,'steel_dark',14)
        for du in (-4.24,4.24):
            for dz in (-3.72,3.17):
                tower_box(k,u+du,v+.26,rest_z+dz,(1.02,2.18,1.85),'hull_grey')
        k.pipe(tower_point(u,v-.11,rest_z-34.2),tower_point(u,v-.11,rest_z-5.2),.82,'steel',14)
        tower_box(k,u+radius,v,rest_z+5.83,(1.36,1.46,1.03),'hull_dark')
        k.torus(eye,.42,.18,'steel_rust',14,6,axis)


def watch_gallery(k):
    # The clear 16.8 m walking line sits within a 3.80 m wide, cantilevered inspection deck.
    level = 148.0
    front, back = -14.72, -10.92
    middle = (front+back)/2
    k.part()
    tower_box(k,.25,middle,level-.38,(24.0,back-front,.76),'hull_grey')
    for v in (front+.19,back-.19):
        k.beam(tower_point(-11.74,v,level-.67),tower_point(12.24,v,level-.67),.47,.9,'steel_dark')
    for u in (-9.6,-.65,9.55):
        k.beam(tower_point(u,front+.55,level-.67),tower_point(u,back+4,level-3.35),.58,.75,'steel_dark')
    k.railing(tower_point(-11.69,front+.13,level),tower_point(12.19,front+.13,level),'metal_grey',1.10)
    for u in (-11.57,12.12):
        k.railing(tower_point(u,front+.12,level),tower_point(u,back-.1,level),'metal_grey',1.10)
    for lo,hi in ((-11.60,-2.6),(1.25,12.10)):
        k.railing(tower_point(lo,back-.12,level),tower_point(hi,back-.12,level),'metal_grey',1.10)
    tower_box(k,-.70,-8.96,level-.27,(3.78,4.52,.54),'hull_grey')
    for u in (-2.45,1.03):
        k.railing(tower_point(u,back,level),tower_point(u,-7.17,level),'metal_grey',1.10)
    tower_box(k,-.71,-7.03,level+1.68,(2.73,.35,3.2),'metal_dark')
    k.light(tower_point(-.65,-7.19,level+2.6),WARM,13,.52,'window')
    for suffix,u in [('a',-8.4),('b',8.4)]:
        k.marker('watch_hab_'+suffix,tower_point(u,middle,level+.05),(TOWER_COS,TOWER_SIN,0))


def spire(k):
    x,y=TOWER_POS
    tower_skirt(k)
    # A narrow drum crosses the moving ring. Above it the core changes section into
    # two splayed cast walls carrying the guide bed and the overhead transfer girder.
    k.part()
    tower_shell(k,[(61.6,0,.1,12.1,12.0,2.72),(68.3,0,.35,14.25,13.65,2.75),
                   (80.5,0,1.22,18.30,15.95,3.15),(92.7,0,1.77,20.8,18.25,3.25),
                   (111.5,-.44,1.89,19.3,17.80,3.05),(134.4,-1.58,2.42,17.87,16.90,2.65),
                   (147.6,-1.39,2.23,17.35,16.62,2.48)],'conc')
    for side in (-1,1):
        k.part()
        tower_shell(k,[(63.8,side*6.3,1.15,3.36,6.28,.65),(72.0,side*10.1,1.48,4.84,6.68,.83),
                       (81.4,side*16.8,1.82,5.19,7.37,.83),(87.3,side*18.60,1.89,5.85,7.65,.91),
                       (90.2,side*18.87,1.89,5.85,7.65,.91)],'conc_warm')
        k.beam(tower_point(side*5.9,6.39,65.6),tower_point(side*17.5,6.63,88),1.81,3.40,'hull_dark')
    tower_shell(k,[(87.2,0,2.15,41.8,12.1,2.25),(89.8,0,2.15,44.05,13.05,2.45),
                   (92.1,0,2.15,44.05,13.05,2.45),(93.2,0,2.15,42.1,11.4,1.93)],'hull_grey')
    for side in (-1,1):
        # Back piers stay clear of both moving envelopes, leaving sky through the guide frame.
        k.part()
        tower_shell(k,[(91.7,side*19.6,4.77,4.3,5.8,.70),(100.5,side*19.35,4.77,3.65,4.8,.56),
                       (130.7,side*16.73,3.25,3.22,4.18,.56),(141.9,side*14.15,2.2,3.70,4.90,.64)],
                    'metal_green' if side>0 else 'hull_rust')
        k.beam(tower_point(side*8,3.35,126.1),tower_point(side*17.8,3.70,105.6),1.29,1.61,'steel_dark')
        k.beam(tower_point(side*8.1,2.40,130.1),tower_point(side*16.05,2.28,139.6),1.45,1.85,'conc_warm')
    # A recessed lift spine and its two service lines run up the shaft between the weights.
    tower_box(k,2.4,-6.65,118.65,(3.52,1.57,47.3),'metal_dark')
    for u in (.40,4.45):
        k.pipe(tower_point(u,-7.52,97),tower_point(u,-7.52,138.4),.37,'steel_rust',10)
    for zz in (104.4,121.1,137.4):
        tower_box(k,2.4,-7.52,zz,(4.92,1.05,1.03),'hull_grey')
    damper_bay(k,'a',-16.85,111.6,'metal_yellow')
    damper_bay(k,'b',16.85,116.8,'metal_orange')
    # Raised asymmetrical operations shoulder with a real recessed front: windows,
    # entrance and the south-facing crew gallery are on the line of sight from home.
    k.part()
    tower_shell(k,[(136.2,-.89,2.30,23.72,17.1,2.56),(140.0,-.20,2.60,33.31,20.2,3.43),
                   (143.0,.65,2.42,34.30,20.9,3.46),(144.3,.65,2.42,33.1,19.6,3.24)],'conc_warm')
    tower_shell(k,[(143.9,-1.55,2.08,25.20,17.10,2.65),(151.43,-1.65,2.06,23.78,16.66,2.91),
                   (152.9,-1.9,2.6,22.32,15.18,2.75)],'metal_grey')
    tower_box(k,-1.15,-6.28,148.21,(18.5,1.3,5.05),'hull_dark')
    for idx,(u,w) in enumerate(((-8.1,2.8),(-4.81,2.55),(2.7,1.93),(5.67,2.62))):
        tower_box(k,u,-6.97,149.41,(w,.15,1.16),'glass' if idx==1 else 'emit_warm')
        tower_box(k,u,-7.04,150.32,(w+.42,1.15,.34),'hull_grey')
    watch_gallery(k)
    # The crown carries the signalling works; nearly all of the enlarged height is occupied structure.
    k.part()
    tower_shell(k,[(151.2,-1.7,2.52,22.74,17.76,3.25),(153.4,-2.15,2.37,22.40,17.10,3.15),
                   (158.4,-4.15,2.55,16.95,13.66,2.85),(166.6,-5.32,2.10,15.37,12.24,2.54),
                   (169.4,-5.37,1.9,12.54,10.06,2.12)],'hull_grey')
    tower_shell(k,[(169.05,-6.3,2.18,10.00,8.65,1.89),(171.64,-6.39,2.18,9.71,8.20,1.70),
                   (174.4,-7.60,2.62,5.80,5.29,1.15)],'metal_dark')
    tower_box(k,-7.3,-3.91,162.60,(7.28,1.08,3.57),'metal_dark')
    tower_box(k,-7.40,-4.70,163.06,(6.16,.53,.85),'glass_warm')
    tower_box(k,-7.32,-4.66,164.66,(8.32,1.51,.51),'conc_dark')
    # The upper plant is reached from an old side-door on its own bracketed landing.
    tower_box(k,-13.21,1.17,157.15,(3.86,8.15,.60),'hull_rust')
    for v in (-1.94,4.25):
        k.beam(tower_point(-14.92,v,156.85),tower_point(-11.45,v,153.4),.48,.56,'hull_dark')
    k.railing(tower_point(-14.97,-2.80,157.45),tower_point(-14.97,5.10,157.45),'metal_grey',1.10)
    tower_box(k,-12.56,1.28,159.02,(.63,2.48,2.98),'metal_dark')
    k.tube([tower_point(6.24,-.91,153.10),tower_point(6.24,-1.20,158.97),
            tower_point(2.18,-3.28,163.35),tower_point(2.18,-3.28,166.66)],.56,'hull_rust',12)
    k.cyl(tower_point(6.24,-1.20,156.20),.73,.35,'steel_dark',12)
    k.cyl(tower_point(2.18,-3.28,166.83),.72,.33,'hull_grey',12)
    for u,v,zz,h in [(5.86,5.64,151.85,13.4),(2.45,8.18,151.87,10.21)]:
        pos=tower_point(u,v,zz)
        k.lathe(pos,[(0,2.54),(.8,2.86),(1.74,2.46),(h-.7,2.18),(h,2.38),(h+.65,2.38)],'hull_rust',16)
        k.cyl(pos+Z*(h+.69),1.82,.14,'metal_dark',16)
    mast=tower_point(-7.55,2.59,174.17)
    k.lathe(mast,[(0,1.35),(.83,1.37),(1.70,.72),(3.18,.65),(3.48,.39)],'steel',12)
    k.lamp(mast+Z*3.32,2.10,'beacon',(1,.07,.03),19,.86)
    spotlight=tower_point(8.62,-6.94,153.53)
    k.beam(tower_point(6.35,-4,151.9),spotlight-Z*.60,.69,.89,'steel_dark')
    tower_box(k,8.62,-6.94,153.33,(2.29,1.64,1.3),'metal_dark')
    tower_box(k,8.62,-7.78,153.53,(1.50,.12,.77),'emit_cool')
    k.marker('spire_axis',(x,y,56),(0,0,1))
    k.marker('spire_search',tower_point(8.62,-7.94,153.53))


def water_loop(k):
    """A low horizontal pressure vessel, exchanger and pumps between the two benches."""
    x,y=120,65.8
    foot=8.05
    floor=foot+.68
    outline=[(-15,-5),(-11,-8),(9.3,-8),(16,-3.9),(16,5.1),(12.3,8),(-12.6,8),(-15,5.2)]
    for dx,dy in [(-12,-4),(8.5,-5),(13,3.8),(-11,5.3)]:
        t=G.z(x+dx,y+dy)
        k.box((x+dx,y+dy,(foot+t)/2),(2.4,2.1,max(.3,foot-t+.3)),'conc_dark')
    k.prism([(x+dx,y+dy) for dx,dy in outline],foot-.32,floor,'conc_warm')
    # Axis of the main potable-water separator. The endcaps are spun, not flat discs.
    k.part()
    ax,ay,az=x-4,y+2.5,floor+4.05
    profile=[(-9.2,.32),(-8.87,1.29),(-8.10,2.29),(-6.91,2.89),(-5.87,3.08),
             (5.52,3.08),(6.55,2.92),(7.85,2.32),(8.62,1.24),(8.88,.34)]
    rings=[]
    for dx,r in profile:
        rings.append([(ax+dx,ay+r*math.cos(t*math.tau/24),az+r*math.sin(t*math.tau/24)) for t in range(24)])
    k.loft(rings,'hull_grey',True,True)
    for dx in (-4.5,4.43):
        saddle=ax+dx
        k.box((saddle,ay,floor+.82),(1.7,4.6,1.64),'conc_dark')
        k.box((saddle,ay,floor+1.75),(1.52,3.21,.85),'steel_rust')
        k.torus((saddle,ay,az),3.07,.15,'steel_dark',24,5,(1,0,0))
    k.cyl((ax+1.3,ay,az+3.42),.87,.79,'steel_rust',16)
    k.cyl((ax+1.3,ay,az+3.90),1.04,.21,'hull_rust',16)
    for a in (0,90,180,270):
        co,si=math.cos(math.radians(a)),math.sin(math.radians(a))
        k.cyl((ax+1.3+co*.82,ay+si*.82,az+4.04),.125,.14,'steel',6)
    k.catwalk((ax-5.9,ay-3.48,az+.60),(ax+5.69,ay-3.48,az+.60),1.18)
    k.stairs((ax-8.9,ay-5.20,floor+.19),(ax-5.89,ay-3.48,az+.61),1.44)
    # Individual exchanger cartridges, sloped for withdrawal from the service aisle.
    k.part()
    ex,ey=x+8.45,y+2.2
    k.box((ex,ey,floor+.85),(6.6,7.47,1.7),'conc_dark')
    k.box((ex,ey+.25,floor+2.20),(5.85,6.8,1.12),'metal_teal')
    for offset in (-1.56,1.48):
        xx=ex+offset
        casing(k,xx,ey,[(floor+2.56,2.67,6.60,.34),(floor+5.00,2.67,6.25,.43),
                        (floor+5.50,2.33,5.45,.42)],'metal_green')
        for j in (-1.58,.06,1.67):
            k.box((xx,ey+j,floor+5.55),(1.80,1.30,.13),'metal_dark')
        k.pipe((xx,ey-2.98,floor+3.65),(xx,ey-4.15,floor+3.65),.51,'steel_rust',12)
    k.box((ex,ey+2.63,floor+5.62),(6.45,.62,.40),'hull_grey')
    # Return manifold and insulated pipe supports along the east side of the domes.
    k.tube([(ax+8.58,ay,az),(ax+9.48,ay-.12,az),(ax+9.98,ay-.12,az-.55),
            (ax+9.98,y-2.65,az-.55),(ex+2.0,y-2.65,az-.55)],.50,'steel_rust',12)
    pumpx,pumpy=x+.5,y-4.75
    k.box((pumpx,pumpy,floor+.23),(8.75,2.8,.46),'conc_dark')
    for dx in (-2.4,1.6):
        k.part()
        k.pipe((pumpx+dx-1.13,pumpy,floor+1.24),(pumpx+dx+.80,pumpy,floor+1.24),.72,'metal_green',14)
        k.pipe((pumpx+dx+.64,pumpy,floor+1.24),(pumpx+dx+1.22,pumpy,floor+1.24),.91,'hull_grey',14)
        k.pipe((pumpx+dx+1.05,pumpy,floor+1.58),(pumpx+dx+1.05,pumpy,floor+2.41),.30,'steel_rust',10)
    k.pipe((pumpx-1.36,pumpy,floor+2.38),(pumpx+3.85,pumpy,floor+2.38),.32,'steel_rust',10)
    route=[(ex+2.3,ey+1.8,floor+3.0),(x+13.8,y+4.45,floor+3.0),
           (140.45,76.2,11.75),(141.65,89.1,11.75),(142.65,105.8,11.75),(145.0,108.2,10.6)]
    k.tube(route,.51,'steel_rust',10)
    for pt in route[2:5]:
        px,py,hh=pt
        gz=G.z(px,py)
        k.box((px,py,gz+.43),(1.9,1.65,.86),'conc_dark')
        k.beam((px,py,gz+.70),(px,py,hh-.45),.43,.51,'steel_dark')
        k.box((px,py,hh-.45),(1.64,.65,.29),'metal_grey')
    k.collider((15.7,5.6,5.45),(ax,ay,az),tag='hab_water_vessel')
    k.collider((6.40,6.94,5.13),(ex,ey,floor+2.65),tag='hab_exchanger')
    k.lamp((x+11.7,y-5.4,floor),4.0,col=COOL,r=16,power=.69)
    k.light((ax-4,ay-3,az+.9),WARM,12,.45,'window')
    k.light((ex,ey-3.4,floor+2.75),COOL,9,.32,'window')
    k.marker('hab_reclaim',(ax,ay,az))


def build(out,log):
    k=Kit('habitat',34)
    spire(k)
    for spec in [(61,137,10,21,13,21,'conc',6),(61,160,10,26,14,15,'conc_warm',4),
                 (136,129,10,15,17,13,'hull_grey',3),(51,98,5,22,12,11,'conc_warm',3),
                 (130,101,5,12,15,10,'conc',2),(93,173,10,17,10,9,'metal_green',2)]:
        slab_block(k,*spec)
    for spec in [(76,105.6,5,19.4,10.8,5,0),(110,104,5,24,12.8,3,2),
                 (123,153,10,26.5,17.3,7,1)]:
        gallery_block(k,*spec)
    covered_link(k,(59.65,142.35,20.3),(59.65,153.65,20.30),2.65)
    covered_link(k,(113.3,145.8,20.20),(103.2,140.4,20.20),2.80)
    # High enough for the dam-like central approach and the adjoining pedestrian route.
    covered_link(k,(84.8,106.10,15.00),(98.85,106.10,15.00),2.65)
    for cx,cy in [(42,115),(50,119)]:
        k.part()
        k.lathe((cx,cy,5),[(0,4.8),(2,5.4),(9,3),(13,3.7),(15.2,4.45)],'conc_warm',24)
        k.cyl((cx,cy,20.3),3.9,.24,'metal_dark',24)
        k.torus((cx,cy,20.4),4.1,.35,'steel_rust',24)
    for cx,cy,rr in [(145,113,7.2),(50.2,79.5,6.2)]:
        k.lathe((cx,cy,5),[(0,rr),(2.9,rr),(3.7,rr*.97),(6.9,rr*.67),(8,rr*.18)],'hull_grey',20)
    # Kiosks leave the diagonal haul approach and the shared 87 m footpath clear.
    for cx,cy,width,angle in [(87.8,83.2,4.2,3),(93.15,84.2,5.1,3),(99.1,84.1,3.8,-3),
                              (110.0,89.0,5.8,-7),(117.1,88.6,4.6,-7),(125.9,86.8,4.8,4)]:
        k.part()
        k.box((cx,cy,6.37),(width,3.1,2.7),'metal_teal' if cx<101 else 'metal_red',angle)
        k.box((cx,cy-.79,8),(width+.88,4.77,.33),'tarp',(-7,0,angle))
        k.box((cx+.22,cy-1.62,6.61),(width*.62,.16,.84),'metal_dark',angle)
        if width>4.7:
            k.lamp((cx+width*.38,cy-2.25,5),2.65,col=WARM,r=10,power=.7)
    k.tube([(43,119,8),(44,108,8),(50,108,8),(50,84,8),(59,84,8)],.71,'steel_rust')
    water_loop(k)
    for xx,yy,h in [(40.6,89.0,3.7),(52.4,88.75,4.5),(64.35,99.8,4.0),(69.6,113.1,4.6),
                     (78.3,115.2,3.4),(85.0,116.4,4.2),(99.1,91.3,3.6),(114.5,113.6,4.7),
                     (122.3,116.8,4.0),(137,116.2,4.6),(104.6,124.3,3.8),(137.0,146,4.6)]:
        k.lamp((xx,yy,G.z(xx,yy)),h,col=WARM if h<4.6 else COOL,r=12+h*.7,power=.65)
    k.marker('hab_dome',(*TOWER_POS,10))
    k.finalize(out,log)
