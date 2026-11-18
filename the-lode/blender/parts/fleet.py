"""Working fleet. Ship roots face east, with the freighter's hatch at the origin.

The open holds and the rear-dumping bed have separate inner and outer plates.
Every movable node is drawn in its rest pose around its physical pivot.
"""
import math
import numpy as np
from lib.kit import Kit, V


def hull_section(x, cy, width, bottom, top):
    """Eight creases around a transverse ship frame, CCW in the YZ plane."""
    r = width / 2
    height = top - bottom
    return [(x, cy + u*r, bottom + t*height) for u, t in (
        (-.60, 0), (.60, 0), (1, .26), (1, .76), (.77, 1),
        (-.77, 1), (-1, .76), (-1, .26))]


def shell(k, stations, material, sides=None):
    rings = [hull_section(*p) for p in stations]
    k.part()
    for a, b in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            k.face([a[i], a[j], b[j], b[i]], sides.get(i, material) if sides else material)
    k.face(rings[0][::-1], material)
    k.face(rings[-1], material)


def ring_x(x, y, z, radius, n=16):
    return [(x, y+radius*math.cos(i*math.tau/n), z+radius*math.sin(i*math.tau/n))
            for i in range(n)]


def axial(k, y, z, profile, mat, n=16):
    k.part()
    k.loft([ring_x(x,y,z,r,n) for x,r in profile], mat, curve=True)


def zloft(k, tiers, material):
    """Chamfered plan boxes for cabs, turrets and removable engine covers."""
    k.part()
    rings=[]
    for z,cx,cy,length,width,bevel in tiers:
        l=length*.5
        w=width*.5
        d=min(bevel,w*.83,l*.83)
        rings.append([(cx+x,cy+y,z) for x,y in (
            (-l+d,-w), (l-d,-w), (l,-w+d), (l,w-d),
            (l-d,w), (-l+d,w), (-l,w-d), (-l,-w+d))])
    k.loft(rings,material)


def hatch(k, x, y, z, width, length, mat='metal_grey'):
    k.part()
    k.box((x,y,z), (length,width,.28), 'steel_dark')
    k.box((x,y,z+.17), (length-.23,width-.24,.14), mat)
    k.pipe((x-.25,y-width*.34,z+.31),(x+.36,y-width*.34,z+.31),.065,'steel')


def lamp(k, p, size=.5, color='cool', power=.72, radius=10):
    mats={
        'red': ('emit_red',(1,.07,.035),'beacon'),
        'amber': ('emit_amber',(1,.57,.13),'beacon'),
        'warm': ('emit_warm',(1,.56,.24),'window'),
        'cool': ('emit_cool',(.56,.86,.81),'flood')}
    mat,c,kind=mats[color]
    k.part(k.rng.random())
    x,y,z=p
    k.box((x,y,z-.075*size),(size*1.22,size*.95,size*.44),'metal_dark')
    k.box((x,y,z+.19*size),(size,size*.72,size*.24),mat)
    k.light((x,y,z+.3*size), c, radius, power, kind)


def thruster(k,x,y,z,r):
    """Inset exhaust throat. Mouth is in the lower-X plane, looking aft."""
    if r>=3:
        n=32
        def ring(dx, radius):
            return ring_x(x+dx*r,y,z,.01+r*radius,n)
        k.part()
        k.loft([ring(0,.98),ring(.1,1.04),ring(.36,.97),ring(1.25,.72),
                ring(1.83,.79),ring(2.42,.71)],'steel_dark',False,True)
        k.loft([ring(0,.88),ring(0,.98)],'steel',False,True)
        k.loft([ring(1.61,.32),ring(1.2,.42),ring(.83,.51),ring(.45,.72),
                ring(.12,.79),ring(0,.88)],'steel_rust',False,True)
        k.face(ring(1.63,.34)[::-1],'metal_dark')
        k.face(ring(1.59,.18)[::-1],'emit_cool')
        k.torus((x+.40*r,y,z),r*.965,r*.068,'steel',32,6,(1,0,0))
        for i in range(7):
            a=i*math.tau/7+.17
            dy,dz=math.cos(a),math.sin(a)
            k.beam((x+.14*r,y+dy*r,z+dz*r),
                   (x+1.84*r,y+dy*.82*r,z+dz*.82*r),r*.16,r*.22,'hull_grey')
        return
    k.part()
    lip=ring_x(x,y,z,r)
    mid=ring_x(x+1.15*r,y,z,r*.62)
    neck=ring_x(x+1.3*r,y,z,r*.84)
    trunk=ring_x(x+2.6*r,y,z,r*.78)
    k.loft([lip,neck,trunk],'steel_dark',False,True)
    # Inward-facing cone and a recessed baffle behind its mouth.
    k.loft([mid,lip],'steel',False,True)
    k.face(mid[::-1],'metal_dark')
    core=ring_x(x+1.14*r,y,z,r*.39)
    k.face(core[::-1],'emit_blue')
    k.torus((x,y,z),r,.13*r,'steel_rust',16,5,(1,0,0))
    for i in (0,1,2,3,4,5):
        q=i*math.tau/6+.18
        dy,dz=math.cos(q),math.sin(q)
        k.beam((x+.23*r,y+dy*r*.99,z+dz*r*.99),
               (x+1.85*r,y+dy*r*.81,z+dz*r*.81),r*.16,r*.18,'hull_grey')


def forebody(k):
    """Raised bow shoulders, a recessed longitudinal rubbing strake, and a raked stem."""
    stations=[
        (20,0,12.0,2.0,16.7),(28,.1,16.5,-.1,18.8),(36,-.1,17.25,0,19.6),
        (47,-.35,16.3,.9,21.0),(55,-.55,14.1,2.4,20.8),
        (62,-.8,11.6,3.9,21.0),(68,-.92,8.8,6.2,21.8),
        (72,-.92,5.9,8.5,22.5),(74.8,-.92,2.6,11.5,21.9)]
    section=[(-.37,0),(.37,0),(.74,.105),(.91,.255),(1,.34),(1,.44),
             (.873,.52),(.873,.65),(.995,.705),(.965,.817),(.90,.92),
             (.70,1),(-.70,1),(-.90,.92),(-.965,.817),(-.995,.705),
             (-.873,.65),(-.873,.52),(-1,.44),(-1,.34),(-.91,.255),(-.74,.105)]
    rings=[[(x, cy+u*r, z0+v*(z1-z0)) for u,v in section] for x,cy,r,z0,z1 in stations]
    for i,(a,b) in enumerate(zip(rings,rings[1:])):
        k.part()
        for j in range(len(section)):
            jj=(j+1)%len(section)
            if i==4 and j in (13,14):
                continue  # opening for the port bow's recessed mooring fairlead
            if j in (5,6,7,15,16,17): mat='steel_dark'
            elif j in (1,2,19,20): mat='hull_rust'
            elif j in (0,4,18): mat='hull_dark'
            elif j in (10,11,12): mat='hull_grey' if i!=1 else 'metal_grey'
            else: mat='hull_white' if i in (3,5,6) else 'hull_grey'
            k.face([a[j],a[jj],b[jj],b[j]],mat)
    k.face(rings[0][::-1],'hull_dark')
    k.face(rings[-1],'hull_dark')

    # Rebuild the two shoulder plates around a through-opening. The back of the
    # cast lip and a chain roller remain visible when looking down into the hawse.
    a,b=rings[4],rings[5]
    def skin(u,v):
        j=15 if v<=.5 else 14
        t=v*2 if v<=.5 else v*2-1
        return V(a[j]).lerp(V(a[j-1]),t).lerp(V(b[j]).lerp(V(b[j-1]),t),u)
    outboard=(skin(1,.5)-skin(0,.5)).cross(skin(.5,1)-skin(.5,0)).normalized()
    frame=[[] for _ in range(5)]
    for i in range(16):
        angle=math.tau*(i/16-.375)
        dx,dz=math.cos(angle),math.sin(angle)
        extent=max(abs(dx),abs(dz))
        frame[0].append(skin(.5+.5*dx/extent,.5+.5*dz/extent))
        for layer,(sx,sz,projection) in enumerate(((.389,.39,0),(.359,.36,.35),
                (.317,.283,.37),(.277,.223,-1.05)),1):
            frame[layer].append(skin(.51+sx*dx,.48+sz*dz)+outboard*projection)
    for outer,inner,mat in zip(frame,frame[1:],('hull_grey','hull_dark','steel','steel_rust')):
        k.part()
        for i in range(16):
            j=(i+1)%16
            k.face([outer[i],outer[j],inner[j],inner[i]],mat)
    k.face(frame[-1],'metal_dark')
    k.pipe(skin(.51,.295)-outboard*.30,skin(.51,.698)-outboard*.30,.29,'steel',12)

    # Wet-dock fairleads flank a recessed forepeak traction winch. A clear slot runs
    # between the cheeks; the drum, brake plate and its shaft can all be seen from above.
    for s in (-1,1):
        s0=s*5.5-.86
        shell(k,[(51,s*8.2-.45,2.8,18.4,20.3),(54,s*8.5-.52,3.4,19.1,22.1),
                 (62,s*7.4-.79,3.4,20.1,24.8),(67,s*5.96-.92,3,20.6,25.6),
                 (71,s0,2.3,20.8,25.0),(72.7,s*3.9-.92,1.45,21.2,23.6)],
                'hull_grey',{4:'steel',0:'hull_dark',1:'hull_rust'})
        k.beam((55.1,-.54+s*8.5,22.2),(66.8,-.92+s*5.96,25.74),.36,.29,'hull_dark')
        for px,py,z,h in [(52,-.42+s*9.2,20.2,2.1),(66.5,-.92+s*6.45,24.52,1.15)]:
            k.cyl((px,py,z),.81,.32,'steel_rust',14)
            k.cyl((px,py,z+h*.50),.49,h,'steel_dark',14)
            k.cyl((px,py,z+h),.74,.2,'steel',14)
        k.beam((53,s*10.95-.5,17.6),(62.2,s*7.73-.8,20.91),.48,.49,'steel')
    k.box((61.3,-.74,21.2),(6.9,6.1,.40),'steel_dark')
    k.pipe((60.7,-3.35,22.3),(60.7,1.87,22.3),1.05,'steel_rust',18)
    for yy in (-3.1,1.65):
        k.pipe((60.7,yy-.15,22.3),(60.7,yy+.15,22.3),1.45,'steel',22)
    k.box((57.7,1.16,21.86),(2.8,1.61,1.25),'metal_teal')
    k.tube([(60.6,-.4,23.38),(65.6,-.62,22.85),(70.4,-.83,23.05)],
           .14,'steel_dark',8)
    k.pipe((70.4,-2.32,23.0),(70.4,.72,23.0),.48,'steel_dark',16)


def service_gallery(k, s):
    """Deep frames in front of the sponson leave two worked-on bays open."""
    shell(k,[(-35,s*16.0,1,5.8,7.2),(-29,s*18.05,2.0,4.6,7.1),
             (-15,s*19.2,1.8,4.8,6.7),(9,s*19.55,1.9,5.1,7.05),
             (21,s*18.75,1.6,5.5,7.5),(29,s*16.5,1.1,6.4,7.9)],
          'hull_dark',{4:'steel_rust'})
    k.catwalk((-28.2,s*18.05,15.35),(21,s*18.05,15.35),1.83,mat='steel_dark')
    k.beam((-30,s*18.54,14.35),(23,s*18.54,14.35),.65,1.18,'hull_grey')
    for x,shift in [(-28.4,1.25),(-16.7,-1.3),(1.8,-1.7),(18.0,.6),(25.6,-1.1)]:
        y=19.37 if -20<x<19 else 18.76
        k.beam((x,s*y,6.0),(x+shift,s*18.6,15.75),1.0,1.27,'hull_grey')
        k.beam((x-1.5,s*(y-.42),6.15),(x+shift,s*18.66,12.4),.42,.66,'steel_dark')
        k.pipe((x,s*(y-.68),6.33),(x,s*(y+.55),6.33),.72,'steel_rust',14)
        k.box((x+shift,s*18.62,15.4),(2.05,.72,.73),'metal_dark')
    # Replaceable armoured covers at two unequal end bays. Centre stays open down to
    # the dark pressure hull and the separate accumulator, clamps and service lines.
    for left,right,base,mat in [(-29.4,-18.6,7.4,'hull_rust'),(3.9,16.4,9.1,'hull_grey')]:
        y=s*19.42
        points=[(left,y,base+1.45),(left+.86,y,base),(right-1.3,y,base+.22),
                (right,y,base+1.60),(right-.55,y,13.93),(left+1.32,y,14.10)]
        plate(k,points,.65,mat)
        k.beam((left+1.24,y+s*.39,base+1.28),(right-1.25,y+s*.39,base+1.37),.43,.35,'steel_dark')
    y=s*18.36
    for z,r,mat in [(8.25,.72,'steel_rust'),(10.06,1.24,'metal_teal')]:
        axial(k,y,z,[(-15.7,r*.46),(-14.8,r*.9),(-13.8,r),(-6.7,r),
                     (-5.8,r*.90),(-5.0,r*.47)],mat,14)
        for x in (-13.55,-7.3):
            k.torus((x,y,z),r+.06,.13,'steel_dark',16,5,(1,0,0))
        k.pipe((-5.2,y,z),(-2.1,y,z),r*.28,'steel',10)
    k.tube([(-3.2,y,11.4),(-1.4,y,11.4),(.2,y,12.58),(3.6,y,12.58)],
           .30,'steel_rust',8)
    k.pipe((-.4,y,12.22),(-.4,y+s*1.05,12.22),.24,'steel',10)
    k.torus((-.4,y+s*1.04,12.22),.75,.12,'metal_red',16,5,(0,1,0))
    k.beam((19.8,s*18.7,6.8),(25.6,s*18.34,12.8),.58,.8,'hull_grey')
    lamp(k,(-13.4,s*18.92,13.97),.71,'cool',.45,9)


def engine_services(k):
    # Two open heat rejection plenums. Tapered trunk, dark return duct and a split
    # extraction hood make a distinctive, asymmetrical silhouette behind the holds.
    for x,y,l,w,top in [(-54,-5.5,9.0,6.6,30.8),(-45.5,4.45,7.9,6.2,28.8)]:
        zloft(k,[(20.8,x+1,y,l+4,w+2,1.5),(24.6,x+.1,y,l+2.1,w+1.2,1.5),
                 (top-1.1,x-.8,y,l,w,1.2)],'hull_dark')
        zloft(k,[(top-1.2,x-.8,y,l+1.25,w+1.12,1.35),
                 (top-.65,x-.8,y,l+.7,w+.69,1.14)],'hull_grey')
        k.box((x-.81,y,top-.57),(l-1,w-1.1,.19),'metal_dark')
        for dx in (-.30,.08,.32):
            k.box((x-.8+l*dx,y,top-.16),(.60,w-.5,.42),'steel',(-12,0,0))
        k.beam((x-3.35,y-w*.57,23.7),(x-3.65,y-w*.59,top-.81),.62,.52,'hull_rust')
        k.tube([(x+4.7,y+w*.57,22.45),(x+4.1,y+w*.63,25.5),
                (x+2.9,y+w*.62,top-.8)],.34,'steel_rust',9)
    k.catwalk((-61,-11.3,20.3),(-37.2,-13.9,20),1.65)
    for x,y in [(-59,-11.8),(-45,-13.2),(-37.8,-13.45)]:
        k.beam((x,y+1.65,16.2),(x,y,20.1),.59,.52,'hull_dark')


def wheelhouse(k):
    """Cantilevered watch floor with a laterally offset docking wing and deep frames."""
    zloft(k,[(18.1,40,-3.2,22.0,18.8,3.1),(21.7,40.6,-3.4,18.9,16.2,2.7),
             (26.8,42.9,-3.78,14.1,11.9,2.0)],'hull_grey')
    zloft(k,[(25.6,42.4,-4.4,15.8,14.1,2.7),(27.2,43.6,-4.75,19.8,16.8,3.3),
             (27.68,43.6,-4.75,19.8,16.8,3.3)],'steel_dark')
    # Plan in CCW order: splayed corner windows have a different angle to the
    # frontal glazing; segment boundaries are individual structural mullions.
    plan=[(-8,-6),(-4,-8.5),(4.8,-8.5),(10,-4.6),(10,2.8),(6.9,5.8),
          (-5.9,5.8),(-8.9,3.1),(-8.9,-3.6)]
    cx,cy=43.0,-3.64
    def ring(z,scale,dx=0):
        return [V((cx+dx+scale*x,cy+scale*y,z)) for x,y in plan]
    lo,hi=ring(27.70,.940),ring(30.85,1.048,.25)
    k.loft([ring(27.12,.951),lo],'hull_dark')
    k.part()
    for i,(cuts,glass) in enumerate([(2,'glass_warm'),(3,'glass'),(2,'glass_warm'),
            (2,'glass_warm'),(1,'glass'),(3,'glass'),(1,'glass_warm'),(1,'hull_grey'),(1,'hull_grey')]):
        j=(i+1)%len(lo)
        a,b=lo[i],lo[j]
        A,B=hi[i],hi[j]
        k.face([a,b,B,A],'steel_dark')
        if glass=='hull_grey':continue
        normal=(b-a).cross(A-a).normalized()
        for p in range(cuts):
            t0,t1=(p+.065)/cuts,(p+.935)/cuts
            c,d=a.lerp(b,t0),a.lerp(b,t1)
            C,D=A.lerp(B,t0),A.lerp(B,t1)
            k.part(k.rng.random())
            actual='emit_warm' if (i,p) in [(0,1),(1,0),(1,2),(3,0),(5,2)] else glass
            k.face([c.lerp(C,.16)+normal*.065,d.lerp(D,.16)+normal*.065,
                    d.lerp(D,.86)+normal*.065,c.lerp(C,.86)+normal*.065],actual)
    k.loft([ring(30.82,1.07,.26),ring(31.37,1.075,.2),ring(31.92,.97,-.2)],'hull_grey')
    k.light((45,-12.67,29.32),(1,.55,.25),13,.67,'window')
    k.light((52.7,-4.3,29.2),(1,.55,.25),11,.46,'window')
    k.catwalk((32,-11.4,23.35),(49,-11.4,23.35),2.0)
    k.stairs((25,-9.9,19.1),(32,-11.4,23.35),1.9)
    for x in (34.7,46.6):
        k.beam((x,-9.0,20.7),(x+1.0,-12.36,23.26),.61,.75,'hull_dark')
    k.ladder((47.7,-11.5,23.6),(47.7,-11.5,26.4))
    zloft(k,[(31.77,40.7,-2.8,5.4,3.7,1.0),(32.9,40.2,-2.8,4.2,3.2,.7)],'hull_dark')
    k.tower((39,-1),31.7,37.9,3.4,1.55,'steel_dark',2,.38)
    k.pipe((39,-1,37.7),(39,-1,43.25),.23,'steel',10)
    k.beam((36.45,-1,37.9),(41.35,-1,37.9),.30,.52,'steel')
    lamp(k,(39,-1,43.2),.48,'red',1.0,23)
    k.pipe((48.4,-4.0,31.55),(48.4,-4,37.2),.21,'steel',9)
    k.cable((39,-1,41.7),(48.4,-4,37.2),.42,.07,'steel_dark',6)


def freighter(k):
    with k.into('freighter'):
        # Forward ballast wedge and aft machinery bloc bound a genuine receiving well.
        shell(k,[(-66,0,18,3,17),(-61,0,29,1,20),(-48,0,33,-.2,20),
                 (-33,0,30,1.1,18.5),(-26,0,22,4.1,15.5)],
              'hull_dark',{3:'hull_grey',4:'hull_grey',5:'hull_grey'})
        forebody(k)
        # Two hard-chined sponsons leave a clear 14.6 m opening below the hold.
        for side in (-1,1):
            s=side
            shell(k,[(-37,s*10.9,8.9,2,15),(-29,s*12.2,10.0,-.1,17.8),
                     (-14,s*12.6,10.6,-.35,18.2),(17,s*12.7,10.8,-.35,18),
                     (31,s*11.3,8.8,2.1,16)],'hull_dark',{4:'hull_grey'})
            k.beam((-32,s*7.8,.6),(24,s*7.8,.6),.75,.95,'steel')
            service_gallery(k,s)
            # Removable feed pipes curve around the machinery casing.
            for j in range(2):
                z=7.3+1.4*j
                k.tube([(-60,s*12.7,z),(-55,s*16,z),(-48,s*17.4,z+1),
                        (-38,s*16.9,z+1),(-33,s*15.7,z+1)],.47+.12*j,'steel_rust',9)
            for i in (-.8,12.3):
                k.beam((i,s*7.6,1),(i,s*6.7,13.5),.45,'steel')
            # Hinges run fore and aft. Doors hang clear under the sponsons when open.
            door='fr_door_l' if s==1 else 'fr_door_r'
            with k.into(door,loc=(0,s*7.3,0)):
                k.box((-1.0,s*3.7,-.16),(31.0,7.03,.75),'hull_grey')
                for xx in (-13.6,-4.7,5.2,11.5):
                    k.beam((xx,s*.48,-.62),(xx+.65,s*6.9,-.62),.4,.32,'steel_dark')
                k.box((-1.2,s*.5,-.55),(29.2,.38,.46),'metal_hazard')
            for xx in (-14,-5.5,7.3,13.1):
                k.pipe((xx-1.15,s*7.3,0),(xx+1.15,s*7.3,0),.64,'steel',10)
        # Coffer ceilings over the receiving bay. Three removable transverse lids
        # have deep, curved lower girders and longitudinal cleats.
        k.box((-1,0,14.1),(56,17,.9),'hull_dark')
        for i,(cx,length,paint) in enumerate(((-20,14.4,'hull_rust'),(-3.3,15.4,'hull_grey'),
                                               (14.0,15.5,'hull_rust'))):
            zloft(k,[(16,cx,0,length+1.5,29,.9),(17.3,cx,0,length+1.6,30,1.5),
                     (19.1+i*.25,cx,0,length-1.2,25.0,2)],paint)
            # The lids lift in two halves. The central combing and two massive ties
            # give each hold a readable ridge, even viewed at the scale of the dock.
            for side in (-1,1):
                zloft(k,[(19.02+i*.25,cx,side*6.5,length-1.3,11.1,1.28),
                         (20.8+i*.25,cx+.2,side*5.8,length-3.6,8.7,1.6)],
                      'hull_grey' if i!=1 or side<0 else 'hull_rust')
            k.beam((cx-length*.39,0,20.1+i*.25),(cx+length*.40,0,20.1+i*.25),
                   1.35,2.24,'hull_dark')
            for s in (-1,1):
                k.beam((cx-length*.39,s*12.3,19.8),(cx+length*.39,s*12.3,19.8),
                       .42,.48,'steel')
                k.box((cx+1,s*14.5,17.85),(3.9,1.75,1.3),'metal_dark')
                for dx in (-length*.28,length*.28):
                    k.beam((cx+dx,s*11.77,19.22+i*.25),(cx+dx,s*8.65,20.99+i*.25),
                           .75,.48,'steel_dark')
        for cx in (-29.1,-11.5,5.55,23.3):
            k.truss((cx,-14.55,16.15),(cx,14.55,16.15),1.65,2.05,'steel_rust',5,.34)
        # Vital lines skirt the removable lids; clearance below allows a fitter to
        # reach the gate hinges while the pressure main stays connected.
        for cx in (-25,-11.2,5.7,20.9):
            k.beam((cx,13.5,17.6),(cx+.65,14.5,22.9),.70,.83,'steel_rust')
            k.beam((cx+.65,14.5,22.9),(cx+2.2,15.1,17.5),.42,.54,'steel_dark')
        k.truss((-27,14.5,22.4),(23,14.5,22.4),1.55,1.82,'hull_dark',7,.31)
        k.tube([(-35,11.6,20.1),(-30,14.0,23.9),(18,14.0,23.9),
                (23,13.1,23.4),(28,9.7,21.2)],.66,'metal_teal',9)
        hatch(k,-2.4,-4.6,21.21,3.1,5.6,'hull_white')
        k.box((12.0,5.7,21.58),(5.0,4.1,.70),'metal_dark')
        for i in range(3):
            k.box((10.4+i*1.45,5.7,22.04),(.75,3.35,.4),'steel')
        k.catwalk((-26,-17.95,6.15),(-10,-17.95,6.15),1.35)
        k.tube([(-10,-18.35,5.95),(-7,-18.55,7.95),(4,-18.55,7.95),
                (6.6,-18.38,6.42),(16.1,-18.38,6.42)],.46,'steel_rust',9)
        for x in (-5.5,3.0,11.0):
            k.box((x,-18.26,7.6 if x<4 else 6.42),(.49,1.65,1.72),'steel_dark')
        # Hull-back engine spine. Four main drives terminate in bell-shaped nozzles.
        shell(k,[(-63,0,16,16,19),(-56,0,22,16,23.8),(-36,0,23,16.5,23),
                 (-29,0,16,16.5,20)],'hull_rust',{4:'metal_grey'})
        for i,(yy,zz) in enumerate(((-9,6.3),(9,6.3),(-8.2,14),(8.2,14))):
            xx=-75 if i<2 else -73.5
            rr=3.65 if i<2 else 3.2
            thruster(k,xx,yy,zz,rr)
            axial(k,yy,zz,[(xx+7,rr*.87),(-64,rr*1.06),(-61,rr*1.14),(-57,rr)],'hull_grey')
            k.marker('fr_engine_'+str(i),(xx,yy,zz),(-1,0,0))
            k.light((xx-.5,yy,zz),(.27,.69,.68),13,.46,'flood')
        for x0,w,offset in ((-59,8,-2),(-48,10,1.2),(-37,7.5,-.6)):
            k.part()
            zloft(k,[(21.4,x0,offset,w,12,1.5),(24.6,x0,offset,w-1.5,10.9,1.2)],
                  'hull_grey')
            for j in range(4):
                k.box((x0-w*.30+j*w*.20,offset,24.76),(.45,7.2,.33),'steel_dark')
        engine_services(k)
        # Raised bridge to port; the starboard side carries a low auxiliary pump room.
        wheelhouse(k)
        for j in range(2):
            y=7.6+j*3.4
            axial(k,y,21.1,[(27,1.0),(29.4,1.7),(42,1.7),(44,1.35),(44.9,.65)],'metal_teal')
        for x in (30.6,39.5):
            k.box((x,9.3,19.4),(1.2,8,1.3),'steel_dark')
        k.tube([(48,8.8,20.9),(53,8.8,21.1),(56.6,6.5,21.1),(61,5.2,19.8)],.62,'steel_rust',9)
        hatch(k,55.1,-4.2,21.0,2.8,3.6)
        # Asymmetric service gantry: landing skids, mooring hooks and RCS stations.
        k.truss((-53,12.5,20.8),(-36,16.2,25.2),1.8,2.3,'metal_yellow',4,.31)
        k.pipe((-36,16.2,25.2),(-36,16.2,18.5),.18,'steel_dark',8)
        k.torus((-36,16.2,18.2),.56,.15,'metal_yellow',12,5,(0,1,0))
        for x,y,z in ((-53,-14,9),(-45,14,12),(52,-12.8,10.8),(56,11,13.2)):
            side=1 if y>0 else -1
            k.box((x,y,z),(6.3,2.9,3.7),'metal_dark')
            for dx in (-1.3,1.35):
                k.pipe((x+dx,y,z),(x+dx,y+2*side,z),.72,'steel',10)
                k.pipe((x+dx,y+1.95*side,z),(x+dx,y+2.17*side,z),.54,'metal_dark',10)
        for side in (-1,1):
            k.tube([(30,15.7*side,8.85),(36,16.8*side,9.15),(46,15.9*side,9.9),
                    (53,13.5*side,11.5),(58.2,12.35*side,11.8)],.52,'hull_rust',10)
            k.beam((35,16.2*side,6.1),(36.6,16.7*side,12.5),.76,1.40,'hull_dark')
            k.beam((45.5,15.55*side,6.9),(47.2,16.1*side,13.3),.77,1.42,'hull_dark')
        for x,y in ((-49,-12),(-45,12),(32,-13),(45,12.1)):
            k.box((x,y,1.05),(7.4,2.5,2),'hull_dark')
            k.beam((x-3,y,-.1),(x+3.4,y,-.1),1.2,.55,'steel_rust')
        for px,py,pz,mode in ((-57,-15.3,14,'amber'),(-48,15.7,17,'red'),
             (-35,-16.8,16.3,'warm'),(-27,15.4,16.8,'cool'),(-15,-7.1,.1,'amber'),
             (12,7.1,.1,'cool'),(15,-7.1,.1,'cool'),(27,-15,16.4,'warm'),
             (57,10.9,18.1,'red'),(66,-8,17.4,'cool'),(49,-10.8,23.7,'warm')):
            lamp(k,(px,py,pz),.7,mode,.68,13)
        k.marker('fr_hatch',(0,0,0),(0,0,1),(1,0,0))
        k.marker('fr_stow',(0,0,12.3))
        k.collider((48,15,1),(0,0,13.5),tag='fr_hold_ceiling')


def breaker(k):
    with k.into('breaker'):
        # The working line is open along X. The pressure vessel and recoil structure
        # sit mostly behind the hammer; fragments leave freely below the clamp.
        shell(k,[(-62,0,10,-6,6),(-58,0,14,-7.5,7),(-48,0,12,-6.7,6.7),
                 (-43,0,9.5,-5,5.5)],'hull_dark',{4:'hull_rust'})
        for side in (-1,1):
            y=side*5.8
            k.truss((-60,y,1),(-12.8,y,1),2.65,5.4,'metal_grey',6,.69)
            k.beam((-61,y,-3.1),(-12.9,y,-3.1),1.22,1.16,'steel')
            k.beam((-58,y,4.3),(-13.3,y,4.3),.95,.57,'metal_yellow')
            k.beam((-17,y,-1),(-8.2,side*18,-.6),2.5,3.5,'steel_rust')
            k.beam((-23,y,2.2),(-8.2,side*18,3.5),1.6,2.3,'steel_dark')
            k.beam((-8.8,side*18,1.5),(7.9,side*19,2.3),3.2,4.6,'metal_grey')
            k.box((2.9,side*18,1.9),(8.2,6.7,6.5),'metal_dark')
            k.pipe((2.8,side*21,2.5),(2.8,side*15.6,2.5),1.63,'steel',12)
            k.box((1.7,side*20.2,5.9),(5.9,3.9,1.35),'metal_yellow')
        for x in (-57,-43,-27,-16):
            k.beam((x,-5.7,-3.5),(x,5.7,-3.5),1.25,1.05,'steel_dark')
        k.catwalk((-55,-8.2,3.9),(-21,-8.2,3.9),1.75)
        k.ladder((-54,-8.5,-4.8),(-54,-8.5,4.2))
        shell(k,[(-41,-9,7,-3.5,5.4),(-38,-10.5,9,-4.2,8),(-30,-10.8,8,-4,7.3),
                 (-27,-9.9,4,-1,4)],'metal_red',{4:'hull_dark'})
        for x in (-36,-33.7):
            k.box((x,-14.91,4.75),(1.61,.31,1.83),'glass_warm')
        k.tube([(-57,7,3),(-53,9,3),(-39,9,4.6),(-23,7.7,4.6),(-15,10.5,2.9)],.49,'steel_rust',9)
        k.pipe((-37,-10,7.7),(-37,-10,13),.28,'steel',8)
        lamp(k,(-37,-10,13),.48,'red',.7,15)
        for x,y,z in ((-58,-5,-4),(-53,5.1,-4.8),(-5,-18,0),(5,18.8,.3)):
            k.pipe((x,y,z),(x,y,z-2.4),1.34,'steel_dark',12)
            k.cyl((x,y,z-2.38),.73,.17,'emit_blue',12)
        for side,name in ((1,'br_jaw_a'),(-1,'br_jaw_b')):
            # At full stroke these inserts move 5 m towards the centreline.
            y=side*18.1
            with k.into(name,loc=(2,y,1.3)):
                k.part()
                k.box((2.1,side*17.7,1.3),(6.1,4.7,5.3),'metal_yellow')
                for z in (-3.3,4.9):
                    k.beam((4,side*18,1.3),(3.8,side*15.5,z),1.65,2.2,'metal_yellow')
                    k.beam((3.8,side*15.5,z),(.7,side*13.6,z*.83),1.39,1.65,'steel')
                    k.box((.9,side*13.6,z*.83),(3.1,.87,1.05),'steel_dark')
                k.pipe((2.8,side*17.2,2.5),(2.8,side*22.2,2.5),.91,'steel',12)
        with k.into('br_ram',loc=(-57,0,0)):
            axial(k,0,0,[(-60.3,2.5),(-58,3.6),(-56.2,4.0),(-54.6,4.0),
                         (-54.1,2.7),(-54,1.85)],'steel',12)
            k.box((-57,0,0),(4.4,9.5,3.45),'metal_hazard')
            for yy in (-4.8,4.8):k.box((-57,yy,-.4),(4.9,1.12,1.65),'steel_dark')
        k.marker('br_grip',(0,0,0))
        k.marker('br_hammer_rest',(-54,0,0))
        for p,c in (((-55,-7.2,5),'amber'),((-28,-8.2,4.4),'cool'),
                    ((1.7,-18.5,6.8),'cool'),((4.5,19,6.8),'red')):
            lamp(k,p,.62,c,.72,12)


def tug(k):
    with k.into('tug'):
        shell(k,[(-6.7,0,4.4,-1.8,1.7),(-4.5,0,5.7,-2.2,2.5),
                 (4.5,-.3,5.9,-1.9,2.9),(7.5,-.2,4.1,-.9,2.5),
                 (8.9,0,2.4,-.25,1.7)],'metal_yellow',{0:'hull_dark',4:'metal_grey'})
        for s in (-1,1):
            yy=3.3*s
            k.beam((-3.1,0,.2),(-5,yy,.2),1.16,1.5,'hull_dark')
            axial(k,yy,.1,[(-7.5,1.4),(-6.8,1.55),(-3.1,1.55),(-1.4,1.04)],'metal_red',12)
            thruster(k,-9.1,yy,.1,1.18)
            k.tube([(-4,yy,1.49),(-3.1,yy,1.85),(-1.4,yy*.70,1.85)],.20,'steel')
            k.box((1.7,yy*.8,-1.42),(4.1,1.6,1),'metal_dark')
            k.pipe((1.8,yy*.8,-1.71),(1.8,yy*.8,-2.38),.54,'steel',10)
        zloft(k,[(2.15,3.0,-.3,4.9,3.8,.49),(3.75,3.52,-.42,3.5,3.1,.39)],
              'metal_yellow')
        zloft(k,[(3.34,3.4,-.4,3.8,3.52,.46),(4.7,3.3,-.4,3.32,3.4,.4)],
              'glass_warm')
        k.box((3.24,-.4,4.72),(3.85,3.65,.27),'hull_dark')
        k.box((3.0,-2.15,4.04),(.19,.15,1.3),'metal_yellow')
        k.light((4.7,-.6,4.04),(1,.58,.28),7,.46,'window')
        # A broad fairlead and two return cylinders carry the tow load to the keel.
        for s in (-1,1):
            k.beam((-3.9,s*1.46,-1.21),(-7.4,s*1.32,-.3),.63,.74,'metal_grey')
        k.pipe((-6.62,-1.26,-.2),(-6.62,1.26,-.2),.70,'steel_rust',12)
        for yy in (-1.03,1.03):
            k.pipe((-6.62,yy-.10,-.2),(-6.62,yy+.10,-.2),.89,'metal_yellow',12)
        k.torus((-8.05,0,-.37),.7,.20,'steel',12,5,(0,1,0))
        k.marker('tug_tow',(-8.66,0,-.37),(-1,0,0))
        k.marker('tug_engine_l',(-9.1,3.3,.1),(-1,0,0))
        k.marker('tug_engine_r',(-9.1,-3.3,.1),(-1,0,0))
        for xx,yy in ((-.6,-2.5),(-2.1,2.7)):
            k.box((xx,yy,2.35),(2.5,.86,1.1),'steel_dark')
        k.pipe((2.2,.64,4.87),(2.2,.64,6.6),.1,'steel',6)
        lamp(k,(2.2,.64,6.6),.35,'red',.6,12)
        lamp(k,(6.6,-1.65,2.4),.48,'cool',.79,13)


def shuttle(k):
    with k.into('shuttle'):
        # A blunt survey ferry with a pressure cabin, folding steps and three feet.
        shell(k,[(-8,0,3.9,1.2,3.3),(-5.8,0,5.1,1.05,4.7),
                 (1.7,0,5.5,1.05,5.2),(5.8,0,4.4,1.3,4.75),
                 (8.3,0,2.55,1.7,3.26)],'hull_white',
              {0:'hull_dark',1:'hull_rust',7:'hull_rust',4:'metal_grey'})
        for s in (-1,1):
            k.beam((-5.0,s*1.7,2.25),(-5.8,s*4.1,2.25),.87,.83,'steel_dark')
            shell(k,[(-7.1,s*3.9,1.45,1,2.7),(-5.4,s*3.9,2.05,.86,3.42),
                     (-2.3,s*3.5,1.9,1.2,3.2),(-.3,s*3.0,1.2,1.61,2.8)],'metal_red')
            thruster(k,-8.15,s*3.9,1.82,.70)
            for xx in (-3.7,-1.7,.42):
                k.box((xx,s*2.72,3.47),(1.14,.22,1.15),'glass_warm')
            k.beam((-4.65,s*2.8,1.5),(-4.8,s*3.8,.33),.34,.38,'steel')
            k.box((-4.83,s*3.85,.15),(1.4,1.19,.26),'metal_dark')
            # Flat mineral glass in the faceted cockpit.
            k.face([(4.4,s*2.32,3.17),(6.66,s*1.65,2.97),(6.2,s*1.64,3.96),
                    (3.83,s*2.35,4.19)][::s*-1], 'glass')
        k.beam((6.15,.25,1.75),(6.57,.26,.26),.39,.45,'steel')
        k.box((6.5,.26,.14),(1.30,1.1,.24),'metal_dark')
        k.box((.6,-2.79,2.8),(1.6,.17,2.55),'metal_grey')
        k.box((.6,-2.91,3.36),(1.0,.06,.53),'glass_warm')
        for i in range(3):k.box((.6,-3.03-.23*i,1.47-.35*i),(1.6,.52,.14),'steel')
        hatch(k,-3.65,0,4.98,2.4,2.1,'hull_dark')
        lamp(k,(5.7,-1.1,4.53),.41,'cool',.61,9)
        lamp(k,(-4.9,1.35,4.62),.33,'amber',.50,9)


def drone(k):
    with k.into('drone'):
        shell(k,[(-1.55,0,1.55,-.54,.52),(-.66,0,2.1,-.72,.86),
                 (.74,-.1,1.8,-.76,.62),(1.65,-.1,1.15,-.36,.42)],
              'metal_orange',{0:'metal_dark'})
        for x,y in ((-1.18,-1.25),(-1.18,1.25),(1.05,-1.1),(1.05,1.1)):
            k.beam((x*.65,y*.48,0),(x,y,.12),.28,.32,'steel_dark')
            k.lathe((x,y,0),[(-.48,.39),(-.29,.30),(.20,.34),(.38,.23)],'metal_grey',8)
        k.box((1.4,-.15,-.29),(.65,.89,.73),'metal_dark')
        k.pipe((1.67,-.15,-.28),(1.95,-.15,-.28),.2,'glass',10)
        k.pipe((-.66,.2,.8),(-.66,.2,1.55),.064,'steel',6)
        lamp(k,(-.66,.2,1.55),.25,'red',.62,10)


def tire_ring(cx, y, cz, r, n):
    return [(cx+r*math.cos(math.tau*i/n),y,cz-r*math.sin(math.tau*i/n))
            for i in range(n)]


def tire(k, center, radius, width, n=18, lugged=False):
    x,y,z=center
    s=1 if y>=0 else -1
    k.part()
    section=[(-.5,.80),(-.43,.925),(-.28,.99),(.28,.99),(.43,.925),(.5,.80)]
    k.loft([tire_ring(x,y+a*width,z,b*radius,n) for a,b in section],'rubber',True,True)
    # Recessed flange, exposed planetary hub, rim bolts and a position mark.
    for d,depth,r,m in ((.49,.08,.61,'steel_dark'),(.55,.075,.47,'metal_yellow'),
                        (.60,.10,.27,'steel_dark'),(.66,.045,.18,'steel')):
        k.pipe((x,y+s*(d-depth*.5)*width,z),(x,y+s*(d+depth*.5)*width,z),
               r*radius,m,n)
    if lugged:
        for i in range(7):
            a=i*math.tau/7
            px=x+.36*radius*math.cos(a);pz=z+.36*radius*math.sin(a)
            k.pipe((px,y+s*.56*width,pz),(px,y+s*.6*width,pz),.044*radius,'steel_dark',6)
        # Alternating tread landings remain inside the nominal diameter.
        for i in range(n):
            a=i*math.tau/n
            xx=math.cos(a);zz=math.sin(a);dy=width*.095*(1 if i%2 else -1)
            k.beam((x+radius*.972*xx+.10*zz,y-width*.36+dy,z+radius*.972*zz-.10*xx),
                   (x+radius*.972*xx-.10*zz,y+width*.36+dy,z+radius*.972*zz+.10*xx),
                   .13*radius,.078*radius,'rubber')


def plate(k, points, thickness, material):
    """A plate has actual thickness, including the edges that face the payload."""
    pts=[V(p) for p in points]
    normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()*thickness*.5
    k.part()
    k.loft([[p-normal for p in pts],[p+normal for p in pts]],material)


def truck(k):
    with k.into('truck'):
        for y in (-1.02,1.02):
            k.box((-.1,y,2.02),(11.8,.62,.86),'steel_dark')
            k.box((-.1,y,2.47),(11.9,.89,.22),'metal_dark')
        for x in (-4.8,-1.6,2.8,5.2):
            k.beam((x,-1.4,1.95),(x,1.4,1.95),.59,.60,'steel_dark')
        for x in (-4.25,4.65):
            k.pipe((x,-2.68,1.9),(x,2.68,1.9),.34,'steel_dark',10)
            for s in (-1,1):
                k.beam((x-.85,s*1.20,2.3),(x,s*2.45,1.65),.41,.36,'metal_grey')
        for name,x,y in (('truck_wheel_fl',4.65,2.60),('truck_wheel_fr',4.65,-2.60),
                         ('truck_wheel_rl',-4.25,2.69),('truck_wheel_rr',-4.25,-2.69)):
            with k.into(name,loc=(x,y,1.9)):
                tire(k,(x,y,1.9),1.9,1.26,20,True)
        # Modular power pack and offset driver's cabin, protected by an overhead cap.
        zloft(k,[(2.25,4.75,.12,4.85,4.5,.44),(3.12,4.72,.12,5.12,5.43,.45),
                 (4.75,4.69,.28,4.65,5.04,.49)],'metal_yellow')
        k.box((7.05,.10,3.58),(.44,4.66,1.46),'metal_dark')
        for y in (-1.35,-.44,.47,1.39):
            k.box((7.32,y,3.55),(.11,.14,1.31),'metal_grey')
        k.box((7.20,.08,2.49),(.57,6.02,.42),'steel_dark')
        k.box((4.3,-2.27,4.53),(4.89,1.97,.36),'metal_yellow')
        zloft(k,[(4.65,4.44,-1.96,3.07,2.21,.24),(5.28,4.51,-1.96,2.9,2.13,.22)],
              'metal_grey')
        zloft(k,[(5.20,4.52,-1.95,2.99,2.15,.20),(6.38,4.39,-1.94,2.73,2.19,.25)],
              'glass_warm')
        k.box((4.4,-1.95,6.52),(3.3,2.50,.29),'metal_yellow')
        for xx in (3.25,4.08,5.65):k.box((xx,-3.035,5.83),(.13,.13,1.16),'steel_dark')
        k.box((3.82,-3.04,5.5),(.23,.11,.15),'emit_warm')
        k.light((4.3,-3.1,5.78),(1,.5,.20),6,.36,'window')
        for y in (.57,1.49):
            k.box((4.81,y,4.87),(2.68,.36,.18),'steel_dark')
        k.pipe((3.36,1.65,4.57),(3.36,1.65,6.38),.23,'steel_rust',10)
        k.pipe((3.36,1.65,6.38),(3.07,1.65,6.62),.24,'steel_dark',10)
        for s in (-1,1):
            k.box((4.6,s*2.97,4.12),(4.4,1.37,.36),'metal_yellow')
            k.beam((6.64,s*2.92,2.74),(6.2,s*2.92,4.05),.16,'steel')
            k.box((6.66,s*2.68,3.57),(.48,.75,.57),'metal_dark')
            k.box((6.91,s*2.68,3.58),(.07,.55,.38),'emit_cool')
            k.light((7.03,s*2.68,3.58),(.58,.86,.82),9,.72,'flood')
        k.stairs((7.10,-2.62,1.52),(4.9,-3.15,4.32),.83)
        # Rear tipping pin. The open tail has no invisible transverse wall.
        pivot=(-5.15,0,3.1)
        k.pipe((-5.15,-2.71,3.1),(-5.15,2.71,3.1),.37,'steel',12)
        for s in (-1,1):
            k.pipe((.6,s*1.12,1.98),(-.4,s*1.12,3.12),.25,'metal_yellow',10)
            k.pipe((-.4,s*1.12,3.12),(-1.09,s*1.12,3.74),.16,'steel',10)
        with k.into('truck_bed',loc=pivot):
            # The inner bed is 5.5 m wide and almost 8.7 m long below its rim.
            k.box((-2.36,0,3.43),(9.05,5.46,.35),'steel_dark')
            plate(k,[(-7.28,-2.95,3.68),(-6.65,-2.72,3.42),(-6.65,2.72,3.42),
                     (-7.28,2.95,3.68)],.27,'steel')
            for s in (-1,1):
                inside=[(-6.83,s*2.70,3.45),(1.92,s*2.70,3.45),(3.04,s*3.55,6.58),
                        (-4.9,s*3.55,6.05),(-7.36,s*3.15,4.35)]
                plate(k,inside,.20,'metal_yellow')
                k.beam((-4.91,s*3.61,6.07),(3.0,s*3.61,6.59),.23,.24,'metal_yellow')
                for i,xx in enumerate((-4.68,-2.12,.36,2.22)):
                    tx=xx+.33
                    tz=6.05+(tx+4.9)*.066
                    k.beam((xx-.38,s*2.85,3.54),(tx,s*3.66,tz),.28,.24,'metal_orange')
                k.box((-6.86,s*2.77,3.49),(.5,.35,.62),'steel_rust')
            plate(k,[(1.96,-2.73,3.43),(1.96,2.73,3.43),(3.05,3.55,6.58),
                     (3.05,-3.55,6.58)],.21,'metal_yellow')
            # Stone guard cantilevers forward above the engine. Cabin roof remains visible.
            plate(k,[(3.05,-3.55,6.61),(3.05,3.55,6.61),(5.34,3.26,6.85),
                     (4.77,-.55,6.91),(3.62,-3.55,6.82)],.21,'metal_yellow')
            # Moving box metadata is expressed in the mesh-local three axes.
            k.collider((9.05,5.46,.35),(-2.36,0,3.43),tag='truck_bed_floor',friction=.36)
            for s in (-1,1):
                k.collider((8.42,.26,2.86),(-1.54,s*3.13,4.86),rot=(-s*16,0,0),
                           tag='truck_bed_side',friction=.36)
            k.marker('truck_bed_pivot',pivot,axis=(0,-1,0))
            k.marker('truck_bed_load',(-1.70,0,4.02))
            k.marker('truck_tail',(-7.26,0,3.68),(-1,0,0))
        lamp(k,(4.22,-2.73,6.73),.31,'amber',.5,8)


def railwheel(k,x,y,z):
    side=1 if y>0 else -1
    k.pipe((x,y-.17,z),(x,y+.17,z),.52,'steel_dark',12)
    k.pipe((x,y-side*.17,z),(x,y-side*.244,z),.57,'steel',12)
    k.pipe((x,y+.14*side,z),(x,y+.26*side,z),.24,'steel_rust',10)


def wagon(k):
    with k.into('wagon'):
        k.box((0,0,1.03),(9.28,3.22,.5),'steel_dark')
        half_gauge=1.05
        axle_z=.52
        axle_end=half_gauge+.31
        for x in (-3.06,3.06):
            k.pipe((x,-axle_end,axle_z),(x,axle_end,axle_z),.14,'steel',9)
            for side in (-1,1):
                y=side*half_gauge
                railwheel(k,x,y,axle_z)
                k.box((x,y+side*.27,.81),(1.35,.30,.46),'hull_dark')
        k.box((0,0,1.51),(6.75,2.78,.28),'steel_dark')
        # A three-metre-deep flaring bin. Grain release is vertically unobstructed.
        bottom=[(-3.34,-1.35,1.58),(3.34,-1.35,1.58),(3.34,1.35,1.58),(-3.34,1.35,1.58)]
        top=[(-4.42,-2.02,4.12),(4.42,-2.02,4.12),(4.42,2.02,4.12),(-4.42,2.02,4.12)]
        for i in range(4):
            j=(i+1)%4
            plate(k,[bottom[i],bottom[j],top[j],top[i]],.18,'hull_rust')
            k.beam(top[i],top[j],.21,.25,'metal_yellow')
        for s in (-1,1):
            for x in (-2.89,-.3,2.52):
                k.beam((x*.86,s*1.50,1.60),(x,s*2.15,4.01),.22,.28,'steel_dark')
            k.box((.4,s*1.85,2.95),(1.51,.22,.48),'hull_white')
        for s in (-1,1):
            k.box((s*4.98,0,1.18),(.64,.58,.43),'steel')
        k.collider((6.75,2.78,.28),(0,0,1.51),tag='wagon_floor')
        k.marker('wagon_load',(0,0,2.34),(0,0,1),(1,0,0))


def loader(k):
    with k.into('loader'):
        zloft(k,[(1.05,-1.42,0,5.45,2.75,.46),(1.82,-1.65,0,5.85,3.66,.60),
                 (2.71,-1.65,0,5.75,3.65,.60)],'metal_yellow')
        k.box((-3.47,.1,2.91),(2.2,2.95,.68),'metal_dark')
        for yy in (-.99,-.37,.22,.82):
            k.box((-3.45,yy,3.29),(1.78,.16,.12),'steel')
        k.pipe((-3.58,1.13,3.16),(-3.58,1.13,4.54),.19,'steel_dark',8)
        k.pipe((-3.58,1.13,4.48),(-3.72,1.13,4.69),.20,'steel_rust',8)
        k.cyl((.74,0,1.85),.92,1.32,'steel_dark',12)
        k.box((1.98,0,1.72),(3.34,2.71,1.07),'metal_yellow')
        for x in (-2.85,2.65):
            for y in (-1.75,1.75):
                tire(k,(x,y,1.30),1.30,.86,14)
                k.box((x,y,2.69),(2.1,1.08,.17),'metal_yellow')
        zloft(k,[(2.61,-.89,0,2.46,2.3,.21),(3.24,-.81,0,2.50,2.51,.24)],
              'metal_yellow')
        zloft(k,[(3.15,-.81,0,2.48,2.50,.24),(4.87,-1.04,0,2.09,2.39,.20)],
              'glass_warm')
        for s in (-1,1):
            k.beam((.21,s*1.06,3.20),(-.07,s*1.05,4.96),.15,.15,'metal_yellow')
            k.beam((-1.8,s*1.06,3.2),(-2.00,s*1.06,4.89),.15,.15,'metal_yellow')
        k.box((-1.02,0,4.98),(2.73,2.77,.27),'metal_dark')
        k.light((-.26,-1.31,4.06),(1,.52,.22),6,.35,'window')
        k.ladder((-1.04,-2.19,1.25),(-1.04,-2.19,3.19),.62,'steel')
        k.box((.10,-2.13,2.89),(2.08,.61,.19),'metal_yellow')
        k.pipe((.38,-1.46,3.15),(.38,1.46,3.15),.33,'steel',10)
        with k.into('loader_arm',loc=(.38,0,3.15)):
            for s in (-1,1):
                k.beam((.38,s*1.22,3.15),(2.38,s*1.39,3.63),.55,.57,'metal_yellow')
                k.beam((2.38,s*1.39,3.63),(5.12,s*1.44,1.2),.48,.60,'metal_yellow')
                k.pipe((1.17,s*1.21,1.73),(2.25,s*1.31,2.75),.27,'metal_dark',10)
                k.pipe((2.22,s*1.30,2.71),(2.94,s*1.36,3.35),.149,'steel',8)
            k.pipe((2.37,-1.5,3.60),(2.37,1.50,3.60),.29,'metal_yellow',10)
            k.beam((2.17,0,3.38),(3.74,0,2.13),.39,.36,'steel_dark')
            k.beam((3.74,0,2.13),(4.94,0,2.62),.32,.32,'steel')
            with k.into('loader_bucket',loc=(5.12,0,1.2)):
                by=1.83
                side=[(4.75,1.87),(4.93,.64),(5.57,.28),(7.12,.22),
                      (6.84,.58),(5.71,1.54),(5.19,2.17)]
                for s in (-1,1):
                    plate(k,[(x,s*by,z) for x,z in side],.18,'metal_yellow')
                for a,b in ((side[0],side[1]),(side[1],side[2]),(side[2],side[3])):
                    plate(k,[(a[0],-by,a[1]),(a[0],by,a[1]),
                             (b[0],by,b[1]),(b[0],-by,b[1])],.17,'steel_dark')
                k.beam((7.02,-1.91,.22),(7.02,1.91,.22),.32,.18,'steel')
                for yy in (-1.5,-.75,0,.75,1.5):
                    k.beam((6.84,yy,.25),(7.33,yy,.16),.21,.13,'steel')
                k.marker('loader_scoop',(5.97,0,.77))
        lamp(k,(-.11,-1.01,5.13),.31,'cool',.6,9)
        lamp(k,(-1.8,.87,5.14),.27,'amber',.46,8)


def pod(k):
    with k.into('pod'):
        # Cable-suspended inspection capsule with a tapered ballast keel.
        zloft(k,[(-1.65,0,0,2.0,1.54,.38),(-.96,0,0,3.08,2.22,.42),
                 (.90,0,0,2.97,2.17,.42),(1.25,0,0,2.48,1.89,.38)],'metal_green')
        k.box((.24,-1.12,.08),(1.93,.12,1.43),'metal_dark')
        k.box((.27,-1.22,.30),(1.51,.07,.63),'glass_warm')
        k.pipe((0,0,1.2),(0,0,1.66),.31,'steel_dark',10)
        k.torus((0,0,1.84),.33,.12,'steel',12,5,(0,1,0))
        k.marker('pod_lift',(0,0,2.16),(0,0,1))
        for y in (-.99,.99):
            k.beam((-1.07,y,-1.32),(1.13,y,-1.32),.22,.27,'steel_dark')
        lamp(k,(1.15,-.64,.99),.27,'cool',.41,7)


def rover(k):
    with k.into('rover'):
        zloft(k,[(.58,0,0,5.7,2.24,.51),(1.26,0,0,5.73,2.60,.48),
                 (1.74,.1,0,5.53,2.57,.41)],'metal_orange')
        for xx in (-1.93,1.82):
            for yy in (-1.33,1.33):tire(k,(xx,yy,.76),.76,.49,12)
        zloft(k,[(1.69,.44,0,3.54,2.32,.31),(2.67,.16,0,2.68,2.04,.26)],
              'glass_warm')
        k.box((.17,0,2.77),(2.99,2.32,.18),'metal_grey')
        for s in (-1,1):
            k.beam((1.96,s*1.02,1.69),(1.41,s*.96,2.73),.13,.13,'metal_orange')
            k.box((.1,s*1.11,2.17),(.15,.18,.86),'steel_dark')
            k.box((2.80,s*.81,1.36),(.17,.45,.25),'emit_cool')
        k.box((-2.05,0,1.85),(1.10,1.93,.54),'metal_green')
        k.pipe((-.75,.55,2.82),(-.84,.55,3.81),.06,'steel',6)
        lamp(k,(.1,-.30,2.94),.27,'amber',.46,7)


def container(k, variant):
    # Root is the container's centre of mass. ISO corner castings define the envelope.
    paint=('metal_red','metal_teal','hull_white')[variant]
    with k.into(('container_a','container_b','container_c')[variant]):
        for s in (-1,1):
            for y in (-1.16,1.16):
                k.box((0,y,s*1.31),(11.94,.24,.22),'steel_dark')
            for x in (-5.91,5.91):
                k.box((x,0,s*1.3),(.26,2.46,.24),paint)
        for x in (-5.89,5.89):
            for y in (-1.13,1.13):
                k.box((x,y,0),(.30,.29,2.58),paint)
                for z in (-1.28,1.28):
                    k.box((x,y,z),(.42,.34,.34),'steel_dark')
        if variant==1:
            # Pressure flask inside an ISO tank frame.
            axial(k,0,-.03,[(-5.56,.30),(-5.38,.77),(-4.92,1.06),(-4.24,1.20),
                            (4.27,1.20),(4.95,1.05),(5.28,.77),(5.5,.34)],paint,16)
            for x in (-3.89,3.88):
                k.torus((x,0,-.03),1.19,.07,'steel',16,5,(1,0,0))
                for s in (-1,1):
                    k.beam((x,s*.54,-1.10),(x,s*1.13,-1.24),.26,.21,'steel_rust')
            for s in (-1,1):
                k.beam((-5.79,s*1.16,-1.20),(-4.05,s*1.16,1.21),.12,.14,'steel')
                k.beam((5.79,s*1.16,-1.20),(4.05,s*1.16,1.21),.12,.14,'steel')
            k.cyl((-.91,0,1.19),.39,.22,'steel_dark',12)
            k.box((.80,0,1.33),(4.06,.53,.11),'steel')
        else:
            k.box((0,0,-.01),(11.55,2.23,2.56),paint)
            for s in (-1,1):
                for x in (-4.82,-3.50,-1.96,1.99,3.52,4.82):
                    k.box((x,s*1.16,0),(.12,.14,2.38),paint)
                k.box((-.09,s*1.177,.03),(2.95,.12,1.79),
                      paint if variant==0 else 'metal_grey')
                k.box((-.81,s*1.266,.55),(.94,.045,.29),'metal_white' if variant==0 else 'metal_red')
            if variant==2:
                for zz in (-.52,-.08,.36):
                    k.box((-5.87,0,zz),(.19,1.61,.20),'metal_dark')
                for x in (-2.4,.75,3.76):
                    k.box((x,0,1.34),(2.41,1.71,.16),'tarp')
            else:
                for yy in (-.56,.56):
                    k.box((5.82,yy,0),(.21,1.06,2.2),'metal_red')
                    k.pipe((5.97,yy,-.93),(5.97,yy,.94),.054,'steel',6)
        k.collider((12.2,2.6,2.9),(0,0,0),tag='container_shell')
        k.marker(('container_a_lift','container_b_lift','container_c_lift')[variant],
                 (.37,-.18,1.45),(0,0,1))


def person(k, heavy):
    name='person_b' if heavy else 'person_a'
    with k.into(name):
        coat='metal_orange'
        k.part(.23 if heavy else .72)
        k.box((0,0,1.03),(.35,.39,.26),'rubber')
        for s in (-1,1):
            offset=.065*s if heavy else -.055*s
            k.beam((offset,s*.12,.93),(offset+.05,s*.12,.53),.16,.18,coat)
            k.beam((offset+.05,s*.12,.53),(offset-.02,s*.12,.16),.15,.17,'rubber')
            k.box((offset+.035,s*.13,.10),(.32,.21,.19),'rubber')
        zloft(k,[(1.10,0,0,.39,.40,.075),(1.46,0,0,.48,.58,.09),
                 (1.58,.025,0,.40,.51,.08)],coat)
        k.box((-.25,0,1.32),(.24,.34,.45),'rubber')
        k.sphere((.035,0,1.77),(.244,.226,.23),'metal_grey',8,5)
        k.box((.224,0,1.77),(.095,.337,.184),'glass')
        for s in (-1,1):
            x=.10 if (s==1)==heavy else 0
            k.beam((-.005,s*.27,1.49),(x-.02,s*.35,1.28),.14,.16,coat)
            k.beam((x-.02,s*.35,1.28),(x+.13,s*.35,1.10),.13,.14,'rubber')
        k.box((.211,-.20,1.51),(.09,.105,.111),'emit_cool')
        k.light((.25,-.19,1.53),(.56,.87,.81),3.5,.34,'lamp')


def salvage_yoke(k):
    """A cutter's T-spreader. Its steel assembly is free to tumble about its mass centre."""
    with k.into('salvage_yoke'):
        for side in (-1,1):
            k.part()
            k.truss((side*1.60,0,0),(side*13.1,0,-.10),2.5,2.45,'steel_rust',3,.44)
            for yy in (-1.35,1.35):
                k.beam((side*2.0,yy,-1.50),(side*14.1,yy,-1.30),.34,.64,'hull_dark')
                k.beam((side*1.30,yy,1.41),(side*13.0,yy,1.11),.46,.53,'metal_grey')
                plate(k,[(side*2.25,yy,.84),(side*2.25,yy,-1.16),
                         (side*5.38,yy,-1.05),(side*4.36,yy,.54)],.29,'hull_rust')
            # End forks: leave daylight between the two thick cheek plates behind a forged pin.
            for yy in (-1.36,1.36):
                plate(k,[(side*12.35,yy,-1.14),(side*14.14,yy,-1.77),
                         (side*15.9,yy,-1.12),(side*15.9,yy,.36),
                         (side*14.54,yy,1.58),(side*12.1,yy,1.2)],.51,'hull_grey')
            k.pipe((side*14.63,-1.94,-.13),(side*14.63,1.94,-.13),.59,'steel',18)
            k.pipe((side*14.63,-2.0,-.13),(side*14.63,-1.75,-.13),.79,'steel_dark',18)

        zloft(k,[(-1.68,.0,.17,5.3,4.9,.71),(-1.22,0,.20,6.35,5.5,1.04),
                 (.87,0,.34,6.12,5.0,1.12),(1.52,0,.38,5.1,4.4,.76)],'steel_dark')
        for side in (-1,1):
            for z in (-1.18,1.18):
                k.beam((side*1.58,1.31,z),(side*.83,15.92,.67*z),.52,.49,'metal_grey')
            for i,(y1,y2) in enumerate([(2.16,5.85),(5.85,9.78),(9.78,13.15),(13.15,15.96)]):
                a=1.60-.05*(y1-1.3)
                b=1.60-.05*(y2-1.3)
                z1=1.13 if i%2 else -1.13
                k.beam((side*a,y1,z1),(side*b,y2,-z1*.85),.36,.49,'steel_rust')
            k.beam((side*5.6,.85,-.52),(side*1.42,6.35,-.52),.54,.73,'hull_rust')
        for y in (4.05,8.90,13.65):
            k.beam((-1.31+.027*y,y,-.88),(1.31-.027*y,y,-.88),.41,.43,'steel_dark')
        # One old inspection cover on the top of the free end makes its half-turn legible.
        zloft(k,[(-.94,0,16.28,2.45,3.0,.48),(-.61,0,16.35,2.95,3.74,.69),
                 (.73,0,16.35,2.93,3.74,.67),(1.01,0,16.32,2.58,3.27,.48)],'hull_dark')
        zloft(k,[(1.025,.05,15.97,2.06,3.39,.3),(1.14,.05,15.97,1.99,3.32,.3)],'metal_yellow')
        k.pipe((-.83,17.1,0),(-.83,18.2,0),.42,'steel_rust',12)
        k.pipe((.83,17.1,0),(.83,18.2,0),.42,'steel_rust',12)
        k.pipe((-.87,18.14,-.02),(.87,18.14,-.02),.33,'steel',14)
        for xx in (-.75,1.12):
            k.box((xx,2.30,1.10),(.31,1.68,1.13),'steel_rust')
        k.pipe((-.98,2.32,1.63),(1.38,2.32,1.63),.34,'steel',16)
        k.torus((.18,2.32,2.00),.81,.31,'hull_grey',24,7,(1,0,0))
        k.box((1.87,.19,1.42),(1.4,2.23,.26),'metal_yellow')

        # Integrate each closed steel piece as signed tetrahedra. Welded overlaps
        # count as the fitted pieces' nominal masses. The eigenbasis lets the viewer
        # conserve angular momentum with exactly diagonal, object-local inertia.
        mesh=k.groups['salvage_yoke']
        points=np.asarray(mesh.v,dtype=np.float64)
        faces=[(face[0],face[j],face[j+1]) for face in mesh.faces for j in range(1,len(face)-1)]
        a,b,c=np.moveaxis(points[np.asarray(faces)],1,0)
        volume=np.einsum('ij,ij->i',a,np.cross(b,c))/6.0
        total=volume.sum()
        corner_sum=a+b+c
        center=(volume @ corner_sum)/(4*total)
        second=sum((v.T*volume)@v for v in (a,b,c,corner_sum))/(20*total)
        covariance=second-np.outer(center,center)
        inertia=np.trace(covariance)*np.eye(3)-covariance
        moments,axes=np.linalg.eigh(inertia)
        # X along the broad crosshead, Y towards the single stem, Z through its plates.
        if axes[0,0]<0:axes[:,0]*=-1
        if axes[1,1]<0:axes[:,1]*=-1
        axes[:,2]=np.cross(axes[:,0],axes[:,1])
        mesh.v=((points-center)@axes).tolist()
        eye=(np.array([.18,2.32,2.0])-center)@axes
        grip=(np.array([.0,15.8,.0])-center)@axes
        k.marker('salvage_eye',eye)
        k.marker('salvage_grip',grip)
        k.data['rigids']={'salvage_yoke':{
            'inertiaPerMass':[float(moments[0]),float(moments[2]),float(moments[1])],
            'com':[0,0,0]}}


def harbor_boat(k):
    """Twin-ended cable lighter. The open slot between its skegs leaves room for a reel."""
    with k.into('harbor_lighter'):
        for s in (-1,1):
            side=s*5.55
            shell(k,[(-20.5,side*.90,1.9,-1.55,1.6),(-17.8,side,4.7,-3.0,3.1),
                     (-11,side,5.9,-4.05,3.1),(5,side,6.1,-3.9,3.0),
                     (13.5,side,5.3,-3.0,3.6),(19.9,side*.92,2.6,-1.75,3.0)],
                  'hull_rust',{0:'hull_dark',1:'hull_dark',3:'metal_orange',
                               4:'hull_grey',5:'hull_white',7:'hull_dark'})
            for side_x in (-1,1):
                cx=side_x*15.8
                # The reversers have independent fore and aft mouths on both sides.
                xx=side_x*20.35
                def ring(dx,r):
                    return ring_x(xx-side_x*dx,side*1.12,-.10,r,18)
                outside=[ring(0,1.79),ring(.52,1.98),ring(1.65,1.83),ring(4,1.51)]
                inside=[ring(2.14,.52),ring(1.01,1.02),ring(.10,1.53),ring(0,1.79)]
                if side_x==1:
                    outside.reverse();inside.reverse()
                k.part()
                k.loft(outside,'hull_dark',False,True);k.loft(inside,'steel_rust',False,True)
                core=ring(2.05,.48)
                k.face(core if side_x==1 else core[::-1],'emit_cool')
                k.torus((xx-side_x*.38,side*1.12,-.10),1.91,.17,'steel',18,6,(1,0,0))
                k.beam((cx-1.4,side-s*.25,3.2),(cx+1.25,side+s*.48,3.31),.76,.56,'metal_dark')
                k.marker('lighter_jet_'+('fore' if side_x==1 else 'aft')+('_p' if s<0 else '_s'),
                         (xx+side_x*.14,side*1.12,-.10),(side_x,0,0))
            k.beam((-12.8,side*1.48,1.23),(13.8,side*1.42,1.40),.48,.93,'steel_dark')
            for x in (-12.6,-5.6,4.8,12.0):
                k.beam((x,side*1.36,-2.6),(x+.88,side*1.49,1.72),.52,.69,'hull_grey')
            k.tube([(-16,side*1.31,2.4),(-10,side*1.47,2.68),(6.1,side*1.41,2.68),
                    (10,side*1.32,2.25)],.26,'steel_rust',8)
            # Open outboard service bay, beyond the shell's full beam. The long
            # dark recess, circuit isolator and pale sacrificial cheeks read broadside.
            y=s*8.66
            k.box((-2.52,y,-.10),(12.5,.38,3.18),'hull_dark')
            k.beam((-8.82,s*9.05,1.38),(3.65,s*9.13,1.41),.77,.65,'hull_white')
            k.beam((-8.68,s*9.21,-1.58),(3.69,s*9.17,-1.56),.73,.57,'steel_rust')
            for x,angle in ((-8.4,.85),(-2.72,-.49),(3.22,-.65)):
                k.beam((x,s*9.27,-1.57),(x+angle,s*9.11,1.43),.64,.67,'hull_grey')
            k.pipe((-6.86,s*8.88,.02),(-3.70,s*8.88,.02),.52,'metal_teal',12)
            k.box((.25,s*8.91,.01),(3.23,.58,1.29),'metal_yellow')
        # The two saddles split the load between the hulls through box webs and knee braces.
        for x in (-5.4,6.15):
            k.beam((x,-6.2,-.78),(x,6.2,-.78),1.72,1.95,'hull_dark')
            for side in (-1,1):
                k.beam((x,side*3.8,2.74),(x,side*1.33,-1.22),.74,.85,'steel_rust')
            k.box((x,0,-1.90),(2.35,2.45,.74),'metal_yellow')
            k.pipe((x,-.83,-2.16),(x,.83,-2.16),.49,'steel',14)
            k.marker('lighter_fair_'+('fore' if x>0 else 'aft'),(x,0,-2.42),(0,0,-1))
        # Machinery deck with an exposed winch and a tall asymmetric line-handling gallows.
        zloft(k,[(1.45,-10.0,.55,13.7,11.6,1.4),(3.26,-10.0,.55,14.1,12.2,1.4),
                 (3.66,-10,.55,13.8,11.9,1.4)],'hull_grey')
        k.pipe((-9.2,-2.8,5.20),(-9.2,2.1,5.20),1.40,'steel_dark',20)
        for y in (-2.8,1.9):
            k.pipe((-9.2,y-.22,5.20),(-9.2,y+.22,5.20),1.76,'metal_orange',20)
            k.beam((-10.8,y,3.65),(-9.2,y,5.15),.61,.69,'steel')
        for y in (-4.98,4.92):
            k.beam((-13.2,y,3.4),(-9.4,y*.81,9.65),.78,.99,'metal_yellow')
            k.beam((-5.85,y,3.5),(-9.4,y*.81,9.65),.62,.88,'hull_white')
        k.beam((-9.4,-4.34,9.65),(-9.4,4.24,9.65),.82,.86,'metal_yellow')
        k.cable((-9.4,-3.6,9.2),(-13.9,-3.3,4.05),.17,.10,'steel',6)
        # Offset wheelhouse and splayed front glazing; only two panes hold warm watches.
        zloft(k,[(2.04,9.2,-.80,14.4,11.95,2.05),(3.5,9.5,-.88,14.5,11.85,1.8),
                 (6.23,10.2,-1.65,9.9,9.0,1.55)],'hull_rust')
        zloft(k,[(5.88,9.85,-1.7,11.6,10.35,1.8),(6.42,9.95,-1.75,12.1,10.6,2.0)],
              'steel_dark')
        zloft(k,[(6.37,10,-1.69,10.25,8.86,1.60),(8.78,10.3,-1.74,11.10,9.52,1.72)],
              'hull_dark')
        zloft(k,[(8.74,10.34,-1.88,12.15,10.93,1.94),(9.23,10.2,-1.88,12.22,10.92,1.94),
                 (9.65,9.93,-1.8,11.51,10.06,1.82)],'hull_grey')
        for n,(xx,w) in enumerate(((6.95,1.85),(9.4,2.10),(12.01,2.07))):
            k.face([(xx-w/2,-6.37,6.72),(xx+w/2,-6.37,6.72),
                    (xx+w/2+.14,-6.62,8.39),(xx-w/2+.14,-6.62,8.39)],
                   'glass' if n==1 else 'glass_warm')
        for n,yy in enumerate((-3.68,-.12)):
            k.face([(15.44,yy-1.21,6.81),(15.44,yy+1.21,6.81),
                    (16.02,yy+1.21,8.50),(16.02,yy-1.21,8.50)],
                   'glass_warm' if n==0 else 'glass')
        k.box((7.4,-.25,9.98),(3.61,2.75,.80),'metal_grey')
        k.pipe((6.94,-.43,10.25),(6.72,-.43,13.62),.18,'steel_dark',9)
        k.beam((5.25,-.43,12.69),(7.98,-.43,12.69),.18,.22,'steel')
        k.catwalk((4.7,4.6,4.21),(15.25,4.6,4.21),1.50)
        k.ladder((7.42,4.95,3.92),(7.42,4.95,7.36))
        lamp(k,(-11.92,-4.61,4.28),.55,'amber',.46,8)
        lamp(k,(7.20,-6.18,6.0),.53,'warm',.52,10)
        lamp(k,(6.72,-.43,13.65),.42,'red',.55,11)


def harbor_reel(k):
    """Transfer stillage with an actual open-spoked cable reel and two independent sling eyes."""
    with k.into('harbor_reel'):
        for s in (-1,1):
            y=s*3.25
            for z,length in ((-3.65,13.4),(.25,10.8)):
                k.beam((-length*.5,y,z),(length*.5,y,z),.62,.69,'hull_dark')
            for x in (-5.48,5.48):
                k.beam((x,y,-3.7),(x*.60,y,.56),.55,.67,'hull_rust')
            k.pipe((0,y-.26,.34),(0,y+.26,.34),.94,'steel_dark',14)
        with k.into('reel_spool',loc=(0,0,.32)):
            for s in (-1,1):
                y=s*2.535
                k.torus((0,y,.32),3.88,.43,'metal_orange' if s>0 else 'metal_yellow',30,7,(0,1,0))
                for i in range(6):
                    a=i*math.tau/6
                    k.beam((math.cos(a)*.77,y,.32+math.sin(a)*.77),
                           (math.cos(a)*3.76,y,.32+math.sin(a)*3.76),.41,.44,'hull_rust')
            k.pipe((0,-2.21,.32),(0,2.21,.32),2.61,'steel_dark',24)
            for y in (-1.74,-1.02,-.30,.42,1.14,1.86):
                k.torus((0,y,.32),2.62,.22,'steel',24,5,(0,1,0))
        for x in (-5.48,5.48):
            k.beam((x,-3.25,-3.64),(x,3.25,-3.64),.64,.72,'hull_dark')
            for s in (-1,1):
                k.beam((x,s*3.25,-3.60),(x*.81,s*1.39,2.19),.50,.58,'metal_grey')
            k.pipe((x*.81,-1.46,2.22),(x*.81,1.46,2.22),.46,'steel')
            k.marker('reel_eye_'+('fore' if x>0 else 'aft'),(x*.81,0,2.22),(0,0,1))


def harbor_cradle(k):
    """Cantilever receiver; origin is the outboard exchange point, +X points out to space."""
    with k.into('harbor_cradle'):
        for side in (-1,1):
            y=side*4.52
            k.truss((-19.8,y,-1.25),(7.1,y,-1.25),1.05,2.20,'hull_rust',5,.33)
            k.beam((-17.8,y,-7.5),(.5,y,-2),.80,1.14,'steel_dark')
            k.box((-17.3,y,-4.23),(5.8,3.4,11.8),'conc_dark')
            k.beam((-4.9,y,.2),(5.5,y,.2),1.16,.91,'hull_grey')
            for x in (-4.8,4.8):
                k.beam((x,y,.27),(x+.25,y+side*.52,1.65),.52,.58,'metal_yellow')
        for x in (-17.6,-11.7,-5.4,1.4,6.5):
            k.beam((x,-4.7,-.90),(x,4.7,-.90),.69,.64,'steel_dark')
        k.catwalk((-18.3,-5.96,.0),(6.4,-5.96,0),1.3)
        zloft(k,[(.02,-13.44,-.45,6.42,5.85,.78),(3.02,-13.72,-.45,6.09,5.28,.75),
                 (3.6,-14.05,-.48,5.62,5.14,.69)],'metal_grey')
        k.tube([(-10.66,-2.4,.94),(-7.5,-2.4,.94),(-6.8,-3.1,.65),
                (-4.7,-3.1,.65)],.24,'steel_rust',8)
        lamp(k,(-11.65,-2.66,3.22),.52,'amber',.6,8)

def build(out, log):
    k=Kit('fleet',307)
    for asset in (freighter,breaker,tug,shuttle,drone,truck,wagon,loader,pod,rover):
        asset(k)
    for variant in range(3):
        container(k,variant)
    person(k,False)
    person(k,True)
    salvage_yoke(k)
    harbor_boat(k)
    harbor_reel(k)
    harbor_cradle(k)
    # Kit.collider positions use the authored absolute frame. Convert only moving
    # template colliders to their owning node's rest-local frame for cloning.
    for collider in k.data['colliders']:
        loc=k.groups[collider['obj']].loc
        collider['p']=[collider['p'][0]-loc.x,collider['p'][1]-loc.z,collider['p'][2]+loc.y]
        collider['local']=True
    k.finalize(out,log)
