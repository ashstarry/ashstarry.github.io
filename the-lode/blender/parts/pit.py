"""Excavation infrastructure. The wall deck carries its own local vertical."""

import math

from mathutils import Matrix, Vector

from lib.ground import G
from lib.kit import Kit, V, Z
from lib.layout import PIT_A, PIT_B, PIT_C, PIT_ROT, WALL_TH, three, wall_path


TEAL = (.57, .82, .83)
AMBER = (1., .51, .17)
RED = (.99, .064, .021)
# The road's lateral direction is constant through both ninety-degree transitions.
ACROSS = V((math.sin(WALL_TH), -math.cos(WALL_TH), 0))
OUTWARD = V((math.cos(WALL_TH), math.sin(WALL_TH), 0))


def from_three(v):
    return V((v[0], -v[2], v[1]))


def local_box(K, c, axes, sizes, material, collider=None):
    """A plate or housing whose 'up' can be horizontal, e.g. on a gravity wall."""
    x, y, z = (v.normalized() for v in axes)
    ax, ay, az = (v * s * .5 for v, s in zip((x, y, z), sizes))
    c = V(c)
    lo = [c - ax - ay - az, c + ax - ay - az, c + ax + ay - az, c - ax + ay - az]
    K.loft([lo, [p + 2 * az for p in lo]], material)
    if collider:
        e = Matrix((x, y, z)).transposed().to_euler()
        K.collider(sizes, c, tuple(math.degrees(a) for a in e), collider)


def rect(cx, cy, z, sx, sy, chamfer=0):
    x = sx / 2
    y = sy / 2
    k = min(chamfer, x * .48, y * .48)
    if k:
        ring = [(-x + k, -y), (x-k, -y), (x, -y+k), (x, y-k),
                (x-k, y), (-x+k, y), (-x, y-k), (-x, -y+k)]
    else:
        ring = [(-x, -y), (x, -y), (x, y), (-x, y)]
    return [V((cx+i, cy+j, z)) for i, j in ring]


def lamp_box(K, at, normal, colour=TEAL, radius=14, power=1.0, warning=False):
    """Protected work light on a real plinth; the lens faces the working surface."""
    c = V(at)
    n = V(normal).normalized()
    right = Z.cross(n)
    if right.length_squared < .01:
        right = V((1, 0, 0))
    right.normalize()
    up = n.cross(right)
    frame = (right, up, n)
    K.part(K.rng.random())
    local_box(K, c, frame, (1.15, .86, .66), 'metal_dark')
    mat = 'emit_red' if warning else ('emit_cool' if colour == TEAL else 'emit_sodium')
    local_box(K, c + n*.36, frame, (.84, .54, .105), mat)
    K.light(c + n*.51, colour, radius, power, 'beacon' if warning else 'flood')


def build_wall(K):
    path = wall_path()
    points = [from_three(entry['p']) for entry in path]
    ups = [from_three(entry['up']).normalized() for entry in path]
    distance = [0.]
    for a, b in zip(points, points[1:]):
        distance.append(distance[-1]+(a-b).length)
    for i, entry in enumerate(path):
        entry['s'] = round(distance[i], 4)
        entry['kind'] = 'rim' if i < 9 else ('rollover' if i < 26 else
                        ('wall' if i < 45 else ('runout' if i < 63 else 'floor')))
    K.path('wall', path)
    K.marker('wall_rim', points[8], -OUTWARD, ups[8])
    K.marker('wall_mid', points[36], (0, 0, -1), ups[36])
    K.marker('wall_foot', points[62], -OUTWARD, ups[62])
    # Anchor the load marker to the centre of the clear deck near y=60.
    t = (points[66].y - 60) / (points[66].y-points[67].y)
    load = points[66].lerp(points[67], t)
    K.marker('wall_load', load, OUTWARD)
    K.marker('wall_turn', points[-1], -OUTWARD)

    def ribbon(left, right, level, mat):
        for i in range(len(points)-1):
            a = points[i] + ups[i]*level
            b = points[i+1] + ups[i+1]*level
            K.face([a+left*ACROSS, b+left*ACROSS, b+right*ACROSS, a+right*ACROSS], mat)

    # Three narrow continuous wearing courses sit on top of an unbroken girder deck.
    # Their ends meet on the same cross-section at every sample of the curvature.
    half_width = 8.9
    for i, (a, b) in enumerate(zip(points, points[1:])):
        u, v = ups[i:i+2]
        K.part()
        for lo, hi, mat in [(-half_width,-.81,'hull_dark'),(-.81,.81,'metal_grey'),(.81,half_width,'hull_dark')]:
            K.face([a+lo*ACROSS,b+lo*ACROSS,b+hi*ACROSS,a+hi*ACROSS],mat)
        K.face([a-half_width*ACROSS-u*.58,a+half_width*ACROSS-u*.58,
                b+half_width*ACROSS-v*.58,b-half_width*ACROSS-v*.58], 'metal_dark')
        for s in (-1,1):
            here = a+s*half_width*ACROSS
            following = b+s*half_width*ACROSS
            K.beam(here-u*.61, following-v*.61,.58,1.17,'hull_rust')
            K.beam(here+u*.51, following+v*.51,.21,.22,'metal_grey')
            K.beam(here+u*1.16, following+v*1.16,.19,.19,'metal_yellow')
            if i % 2 == 0:
                K.beam(here-u*.24,here+u*1.20,.22,.26,'steel')
        # A quaternion is derived from the cross-deck basis, so horizontal and
        # vertical road panels have consistent collision normals through the bend.
        d = (b-a).normalized()
        face_up = ACROSS.cross(-d).normalized()
        e = Matrix((ACROSS,-d,face_up)).transposed().to_euler()
        K.collider((half_width*2, (b-a).length+.035, .58), (a+b)*.5-face_up*.29,
                   tuple(math.degrees(val) for val in e), 'wall_deck', .78)

    # Wheel-polish on two lanes. The wear tracks are interrupted by replacing panels.
    for width in (-6.3,-2.65,2.65,6.3):
        ribbon(width-.19,width+.19,.018,'steel_dark')

    for i in [3,7,14,23,29,32,35,39,43,50,58,65,69]:
        p, up = points[i], ups[i]
        d = (points[i+1]-points[i-1]).normalized()
        frame = (ACROSS, -d, up)
        local_box(K,p-up*1.06,frame,(18.9,.68,1.48),'steel_dark')
        if 26 <= i <= 44:
            # Long shear keys pass four metres behind the vertical road into the rock.
            for side in (-1,1):
                here = p+side*7.5*ACROSS
                embed = here-up*5.5
                local_box(K,embed,frame,(2.7,3.7,.75),'conc_warm')
                K.beam(embed,here-up*.62,.85,.9,'steel_dark')
                K.beam(embed+d*2.4,here+side*.76*ACROSS-up*.5,.56,.68,'steel_rust')
                K.pipe(here-up*.35,here+up*.52,.29,'steel',8)
        elif i in (3,7,65,69):
            for side in (-1,1):
                top = p+side*7.3*ACROSS-up*.89
                z = min(top.z-.8, G.z(top.x,top.y)-.7)
                K.box((top.x,top.y,(z+top.z)/2),(1.5,1.5,top.z-z),'conc_dark')

    # Hand-painted lane guidance, confined to the landing and the straight face.
    # Six broad, weathered arrows read as road markings when the surface turns vertical.
    for idx in [4,34,40,65]:
        c = points[idx]; up = ups[idx]
        tangent = (points[idx+1]-points[idx-1]).normalized()
        for lane in (-1,1):
            along=tangent*(1 if lane<0 else -1)
            across=along.cross(up).normalized()
            anchor=c+ACROSS*(lane*4.50)+up*.055
            # Polygon order is checked against up before adding each paint patch.
            polys=[((-0.29,-2.0),(.29,-2.0),(.29,.34),(-.29,.34)),
                   ((-1.05,.20),(1.05,.20),(0,1.94))]
            for poly in polys:
                vertices=[anchor+across*u+along*v for u,v in poly]
                if (vertices[1]-vertices[0]).cross(vertices[2]-vertices[0]).dot(up)<0:
                    vertices.reverse()
                K.face(vertices,'metal_yellow' if idx in (4,65) else 'metal_white')

    # The gravity plating has service bays outside the road: open armoured doors,
    # pressure accumulators and a short escape duct. The carriageway stays clear.
    for idx,side in [(30,-1),(38,1),(43,-1)]:
        p=points[idx];normal=ups[idx];travel=(points[idx+1]-points[idx-1]).normalized()
        frame=(ACROSS,-travel,normal)
        bay=p+ACROSS*side*11.0
        K.part()
        local_box(K,bay-normal*.54,frame,(3.7,5.35,1.72),'hull_grey')
        local_box(K,bay+normal*.41,frame,(2.62,3.68,.40),'metal_dark')
        hatch=bay+normal*.91+travel*.22
        K.pipe(hatch-normal*.34,hatch,.91,'steel_rust',12)
        K.pipe(hatch,hatch+normal*.09,.65,'metal_teal',12)
        for dy in (-1.73,1.64):
            K.pipe(bay+travel*dy-ACROSS*.94+normal*.74,
                   bay+travel*dy+ACROSS*.85+normal*.74,.21,'steel',7)
        K.tube([bay+travel*2.2, bay+travel*2.6+ACROSS*side*.7,
                bay+travel*4.0+ACROSS*side*.7, p+ACROSS*9.38*side+travel*5.2],.23,'steel_rust',7)
        lamp_box(K,bay-travel*2.62+normal*1.05,-ACROSS*side-normal*.24,AMBER,18,1.25)

    # Direction-change stations: work lights face the deck along its local normal.
    # Each bank is separately mounted, with very few lamps opposite one another.
    for i, side in [(3,1),(8,-1),(14,1),(22,-1),(27,1),(30,-1),(35,1),
                    (39,-1),(43,1),(54,-1),(60,1),(66,-1),(71,1)]:
        p, up = points[i], ups[i]
        edge = p+side*9.05*ACROSS
        bracket = edge + up*2.65 + side*.46*ACROSS
        K.beam(edge,bracket,.33,.29,'steel_dark')
        face = -side*ACROSS*.8-up*.46
        lamp_box(K,bracket,face, AMBER if i in (8,30,43,66) else TEAL,14,.84)
    for side in (-1,1):
        for i,j in [(8,25),(27,42),(46,61)]:
            pts = [points[k]+ACROSS*(side*9.32)-ups[k]*.45 for k in range(i,j+1,2)]
            K.tube(pts,.25,'steel_rust',6)

    # Control hut at the outer end of the paved apron, outside the traffic envelope.
    apron=points[8]
    centre=apron+ACROSS*15.7-OUTWARD*.8
    floor=max(G.z(centre.x,centre.y),1.)
    K.loft([rect(centre.x,centre.y,floor-.45,9.3,6.2,.65),
            rect(centre.x,centre.y,floor+1.05,8.4,5.6,.45)],'conc_warm')
    K.box((centre.x,centre.y,floor+3.15),(7.7,5.2,4.4),'metal_teal')
    K.box((centre.x+.3,centre.y-2.6,floor+3.5),(6.15,.42,1.75),'metal_dark')
    for j in range(3):
        K.part(K.rng.random())
        K.box((centre.x-1.65+j*2,centre.y-2.83,floor+3.62),(1.64,.09,1.20),
              'glass_warm' if j!=1 else 'emit_warm')
    K.box((centre.x,centre.y-.32,floor+5.57),(8.7,6.3,.72),'hull_dark')
    K.pipe((centre.x-2.8,centre.y,floor+5.87),(centre.x-2.8,centre.y,floor+9.1),.15,'steel')
    lamp_box(K,(centre.x-3.85,centre.y-1.8,floor+4.38),(-1,-.2,-.25),AMBER,13,.66)
    K.light((centre.x,centre.y-3.15,floor+3.65),(1,.55,.23),12,.72,'window')

    # A low, widened loading apron with swing clearance for a fifteen metre truck.
    # Broad posts and the material bunker sit to its west, outside both wall lanes.
    apron = load-ACROSS*14.5
    pad = rect(apron.x,apron.y,load.z-.10,11,22,1.4)
    K.loft([[V((v.x,v.y,min(G.z(v.x,v.y)-.3,load.z-1.1))) for v in pad],pad], 'conc_dark')
    K.collider((11,22,.8),(apron.x,apron.y,load.z-.50),0,'floor_apron')
    K.marker('loader_dock',apron+Z*.11, ACROSS)
    west = apron-ACROSS*4.3
    for d in [-8.0,7.4]:
        p=west+OUTWARD*d
        K.box((p.x,p.y,load.z+1.55),(1.7,3.7,3.1),'conc')
        lamp_box(K,(p.x,p.y,load.z+3.55),(.75,.1,-.35),AMBER,17,.9)
    shed=west-ACROSS*2.5+OUTWARD*4.2
    K.box((shed.x,shed.y,load.z+1.7),(3.9,5.0,3.4),'hull_rust')
    K.box((shed.x,shed.y,load.z+3.54),(4.5,5.66,.44),'hull_dark')
    K.light((shed.x+2.0,shed.y,load.z+2.42),TEAL,10,.55)
    return points


def mast_strut(K,a,b,stations,web='hull_rust',edge='metal_grey'):
    """Tapered welded box girder. Broad webs and folded flanges have separate skins."""
    a,b=V(a),V(b);d=(b-a).normalized()
    wide=V((1,0,0))-d*d.x
    if wide.length_squared<.17:
        wide=V((0,1,0))-d*d.y
    wide.normalize();deep=d.cross(wide)
    rings=[]
    for t,width,depth in stations:
        c=a.lerp(b,t);w=width*.5;h=depth*.5;c0=min(w,h)*.27
        profile=[(-w+c0,-h),(w-c0,-h),(w,-h+c0),(w,h-c0),(w-c0,h),
                 (-w+c0,h),(-w,h-c0),(-w,-h+c0)]
        rings.append([c+wide*i+deep*j for i,j in profile])
    K.face(list(reversed(rings[0])),edge);K.face(rings[-1],edge)
    for lo,hi in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8
            K.face([lo[i],lo[j],hi[j],hi[i]],web if i in (0,4,6) else edge)
    for k in [2,7]:
        for lo,hi in zip(rings,rings[1:]):
            K.beam(lo[k],hi[k],.29,.35,edge)


def mast_cheek(K,x,y,z,thickness,outline,colour):
    """Plate profile in the vertical YZ plane, with the two cut edges modelled."""
    if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(outline,outline[1:]+outline[:1]))<0:
        outline=list(reversed(outline))
    rings=[[V((x+u,y+i,z+j)) for i,j in outline] for u in [-thickness*.5,thickness*.5]]
    K.loft(rings,colour)


def mast_sheave(K,c,r,thickness,axis):
    """Hollow flanged head sheave with a grooved tread and six cast spokes."""
    c=V(c);axis=V(axis).normalized();u=Z.cross(axis).normalized();v=axis.cross(u)
    profile=[(-.5,.78),(-.5,1),(-.32,1),(-.24,.88),(.24,.88),(.32,1),
             (.5,1),(.5,.78),(-.5,.78)]
    rings=[[c+axis*(a*thickness)+(u*math.cos(math.tau*j/24)+v*math.sin(math.tau*j/24))*b*r
            for j in range(24)] for a,b in profile]
    for s,(lo,hi) in enumerate(zip(rings,rings[1:])):
        for j in range(24):
            n=(j+1)%24;K.face([lo[j],lo[n],hi[n],hi[j]],'steel' if s in (1,5) else 'steel_dark',True)
    K.pipe(c-axis*(thickness*.6),c+axis*(thickness*.6),r*.28,'steel_rust',16)
    for j in range(6):
        t=math.tau*j/6+.12
        n=u*math.cos(t)+v*math.sin(t);s=-u*math.sin(t)+v*math.cos(t)
        K.beam(c+n*r*.25,c+n*r*.84+s*r*.11,thickness*.55,r*.175,'hull_grey')


def mast_headworks(K,point):
    """Raking headframe and counterjib. The fixed breaker works north of this structure."""
    X=V((1,0,0));Y=V((0,1,0))
    pin=V((15,-35,113))
    west=V((2.9,-7.2,53.85));east=V((36.0,-6.3,52.3))
    toes=[west,east];peaks=[pin-X*4.10,pin+X*4.10]
    lower=[V((10.9,12.65,17.1)),V((34.3,7.0,20.2))]
    # The west caisson is keyed into the inclined pit lip. Its cap is deliberately
    # level; the vertical liners and two exposed anchors show the buried depth.
    gx,gy=lower[0].x,lower[0].y
    h=G.z(gx,gy)
    K.part()
    K.loft([rect(gx,gy,h-2.4,9.3,8.6,.83),rect(gx,gy,h+2.4,9.3,8.6,.83),
            rect(gx+.35,gy+.28,h+7.4,7.7,6.35,.78),rect(gx,gy,16.7,5.65,5.,.69)],'conc_dark')
    K.collider((5.4,4.9,17.4-h),(gx,gy,(17.4+h)*.5),0,'mast_pintle')
    for x in [-1.62,1.62]:
        K.pipe((gx+x,gy-2.35,8.4),(gx+x,gy-2.35,16.63),.29,'steel_rust',8)
        K.cyl((gx+x,gy-2.35,16.98),.58,.8,'steel',6)
    for i,(a,b,tip) in enumerate(zip(lower,toes,peaks)):
        K.part()
        mast_strut(K,a,b,[(0,4.75,4.5),(.22,4.1,4.7),(.75,3.20,3.2),(1,3.55,3.72)],
                   'hull_dark','metal_grey')
        K.pipe(b-X*3.18,b+X*3.18,2.43,'metal_red',20)
        K.pipe(b-X*3.50,b+X*3.50,1.38,'steel',16)
        # In profile the two legs run toward one enormous cast pin; the left
        # has a wide welded web, the right exposes two separate compression booms.
        mast_strut(K,b,tip,[(0,4.05,3.45),(.10,4.7,4.35),(.42,3.75,3.84),
                            (.80,2.62,2.87),(1,2.95,3.20)],
                   'hull_rust' if i==0 else 'metal_grey','metal_grey' if i==0 else 'steel_dark')
        shoulder=b.lerp(tip,.24);knee=b.lerp(tip,.67)
        for p0,size in [(shoulder,2.0),(knee,1.38)]:
            K.pipe(p0-X*size,p0+X*size,size*.59,'steel_dark',14)
            K.pipe(p0-X*(size+.18),p0+X*(size+.18),size*.34,'steel',12)
    K.part()
    # Back of the fixed discharge station carries the transverse foot table.
    mast_strut(K,west,east,[(0,2.52,2.8),(.14,3.35,3.2),(.72,2.4,2.62),(1,2.95,3.25)],
               'metal_grey','hull_dark')
    K.beam((10.35,12.65,17.),(24.2,8.2,48.9),1.35,1.75,'hull_rust')
    K.beam((32.8,8.4,34.1),east,1.60,1.95,'metal_grey')
    # Single deep box collar and knee at the lower third of the clear triangular
    # opening. The remainder stays open against the pit behind it.
    c=west.lerp(peaks[0],.34);d=east.lerp(peaks[1],.34)
    mast_strut(K,c,d,[(0,2.7,2.65),(.13,2.1,2.15),(.84,1.82,2.12),(1,2.56,2.55)],
               'metal_grey','hull_dark')
    K.beam(c.lerp(d,.20),west.lerp(peaks[0],.47),.90,1.22,'hull_rust')
    K.beam(c.lerp(d,.88),east.lerp(peaks[1],.43),.76,.98,'metal_grey')

    # Lobed pierced-looking cast cheeks, a common shaft, flanged rope sheaves and
    # a removable end cap. All fixed equipment is on the south of the moving hammer.
    outline=[(-4.05,-4.05),(-1.77,-5.86),(1.78,-5.82),(4.38,-2.51),
             (4.13,1.64),(2.25,4.26),(-.91,4.58),(-3.24,2.85)]
    for offset,colour in [(-4.10,'metal_red'),(4.10,'hull_rust')]:
        K.part()
        mast_cheek(K,pin.x+offset,pin.y,pin.z,1.72,outline,colour)
        outer=1 if offset>0 else -1
        K.pipe(pin+X*(offset+outer*.73),pin+X*(offset+outer*1.36),2.32,'steel_dark',24)
        K.pipe(pin+X*(offset+outer*1.25),pin+X*(offset+outer*1.51),1.53,'steel',20)
        for j in range(6):
            t=math.tau*j/6+.26
            n=(Y*math.cos(t)+Z*math.sin(t))*1.90+pin+X*(offset+outer*1.34)
            K.pipe(n,n+X*(.24*outer),.188,'steel',6)
    K.pipe(pin-X*5.73,pin+X*5.73,1.08,'steel_dark',20)
    for dx,r in [(-2.03,3.58),(1.25,3.38)]:
        mast_sheave(K,pin+X*dx,r,1.20,X)
    K.marker('mast_head_pin',pin,(1,0,0))

    # A short heel stay balances two asymmetric outriggers. The torn asteroid
    # and its tug brake north of the long pennants, leaving the trolley line clear.
    for dx,t,off,r,sag in [(-2.13,.175,-4.30,.34,.35),(1.12,.705,16.45,.38,.55),
                            (-1.71,.918,8.04,.41,.63)]:
        high=10.15-4.55*t+1.05*math.sin(math.pi*t)
        anchor=point(t,off,high)
        if off>0:
            w=4.58-1.83*t
            K.beam(point(t,-w,high),anchor,.71,.90,'hull_rust')
            K.beam(point(t-.047,w,high-.62),anchor,.51,.65,'metal_grey')
            K.beam(point(t,w,.0),anchor,.61,.80,'steel_dark')
        eye=pin+X*dx+Y*2.94+Z*1.82
        toward=(eye-anchor).normalized()
        K.cable(anchor,eye,sag,r,'steel_dark' if off<0 else 'steel',13)
        K.pipe(anchor-toward*.34,anchor+toward*3.85,r*1.76,'hull_grey',12)
        K.pipe(anchor+toward*2.78,anchor+toward*3.43,r*1.98,'hull_rust',12)
        K.beam(anchor-Z*1.86,anchor+Z*.34,1.37,1.61,'metal_grey')

    # Offset machine deck, two separate sheave cheek walls and a genuinely
    # deep counterweight pocket outside the working apron, well above the Mitt.
    winch=V((35.8,-41.5,64.8))
    boom_root=V((33.3,7.9,48.8))
    for sign in [-1,1]:
        k=sign*2.74;a=boom_root+X*k;b=winch+X*k-Z*5.05
        K.part()
        mast_strut(K,a,b,[(0,1.82,2.58),(.11,2.38,3.12),(.78,1.32,1.73),(1,1.23,1.37)],
                   'metal_grey','hull_rust')
        K.beam(a-Z*4.32,b-Z*.36,1.04,1.32,'hull_dark')
        for t in [.13,.47,.78]:
            q=a.lerp(b,t);K.beam(q,q.lerp(b,.15)-Z*(3.5*(1-t)),.55,.69,'steel_dark')
        link=winch+X*k+Y*.74+Z*.45;head=pin+X*(3.75*sign)-Y*2.87
        K.cable(link,head,.44,.45 if sign>0 else .34,'steel_dark',12)
        K.pipe(link,link.lerp(head,.16),.82,'metal_grey',12)
        K.pipe(link.lerp(head,.11),link.lerp(head,.17),.98,'hull_rust',14)
    K.box(winch-Z*3.49,(11.7,8.4,2.35),'hull_dark',-8)
    for dx,w,depth,h0 in [(-2.82,5.07,6.84,7.55),(2.42,4.91,6.10,6.52)]:
        K.part();q=winch+X*dx-Y*1.04
        K.loft([rect(q.x,q.y,q.z-11.2,w*.77,depth*.72,.64),
                rect(q.x,q.y,q.z-9.95,w,depth,.62),rect(q.x,q.y,q.z-11.2+h0,w,depth,.66)],
               'conc_dark' if dx<0 else 'conc_warm')
        for sign in [-1,1]:
            K.beam(q+X*(w*.36*sign)-Y*(depth*.5+.11)-Z*9.8,
                   q+X*(w*.36*sign)-Y*(depth*.5+.11)-Z*4.,.38,.37,'hull_rust')
    for dx in [-3.42,3.42]:
        mast_cheek(K,winch.x+dx,winch.y,winch.z,.89,
             [(-3.23,-2.86),(2.65,-2.86),(2.45,-.72),(1.21,1.95),(-1.35,2.03),(-2.76,.05)],'metal_green')
    K.pipe(winch-X*3.95,winch+X*3.95,.77,'steel',16)
    K.pipe(winch-X*2.64,winch+X*2.44,1.44,'metal_grey',24)
    for dx in [-2.56,2.29]:
        K.pipe(winch+X*dx,winch+X*(dx+.23),2.10,'steel_rust',24)
    for dx in [-1.92,-1.39,-.86,-.33,.20,.73,1.26,1.79]:
        K.torus(winch+X*dx,1.45,.14,'steel_dark',18,5,X)
    K.box(winch+X*3.89+Y*.29,(2.75,3.9,2.71),'metal_grey')
    K.marker('mast_winch',winch,(1,0,0))

    # The watchmen work outside the machine with no obstructions at head or
    # foot level. The 1.10 m top rail and 2.9 m aisle are deliberately human scale.
    watch_z=68.25;edge_y=-21.9
    K.part()
    K.box((12.00,edge_y,watch_z-.22),(19.8,3.22,.44),'hull_grey')
    for y0 in [-23.35,-20.45]:
        K.beam((2.15,y0,watch_z-.50),(21.86,y0,watch_z-.50),.35,.67,'steel_dark')
    for a,b in [((2.28,-23.35),(21.71,-23.35)),((2.28,-20.45),(5.52,-20.45)),
                ((8.20,-20.45),(21.71,-20.45)),((2.28,-23.35),(2.28,-20.45)),
                ((21.71,-23.35),(21.71,-20.45))]:
        K.railing((*a,watch_z),(*b,watch_z),'steel_dark',height=1.10)
    for x0,b0 in [(4.55,west.lerp(peaks[0],.22)),(20.74,east.lerp(peaks[1],.22))]:
        K.beam(b0,V((x0,-20.5,watch_z-.55)),.62,1.00,'steel_dark')
        K.beam(b0-Z*3.88,V((x0,-23.3,watch_z-.57)),.54,.76,'hull_rust')
    landing=V((7.02,-15.30,64.99))
    K.beam((7.02,-14.0,64.77),landing-Z*.21,1.77,.42,'hull_grey')
    K.stairs(landing,(7.02,-20.55,watch_z),1.41,'metal_grey')
    K.catwalk((12.88,-9.41,64.91),landing,1.63,'hull_grey')
    K.beam((13.35,-6.61,53.92),(13.35,-9.61,53.92),1.65,.34,'hull_grey')
    K.ladder((13.35,-9.61,54.03),(13.35,-9.61,64.97),.82)
    for name,x0 in [('watch_mast_a',4.8),('watch_mast_b',20.1)]:
        K.marker(name,(x0,edge_y,watch_z),(1,0,0))
    K.marker('mast_watch_lamp',(3.3,-23.2,69.5),(-.18,.8,-.28))
    lamp_box(K,(3.3,-23.2,69.5),(.8,.22,-.36),AMBER,14,.74)
    lamp_box(K,winch+X*4.51+Z*1.15,(-.40,-.78,-.51),TEAL,18,.88)
    K.marker('gantry_search',pin+X*4.07-Y*.55+Z*4.87,(-.7,.1,-.65))
    lamp_box(K,pin+X*4.07-Y*.55+Z*4.87,(-.75,.02,-.65),TEAL,24,1.15)
    lamp_box(K,pin-X*3.78+Y*.95+Z*4.31,(.14,-.85,.17),RED,13,.61,True)


def build_mast(K):
    x,y=27.,13.
    # Four independent caissons with shear keys. A raked inner portal frames the
    # falling stream under the upper machinery floor.
    legs=[((18.8,6.5),(21.8,8.2)),((34.3,7.0),(32.2,8.2)),
          ((34.1,20.),(32.4,17.9)),((18.2,20.4),(21.7,18.2))]
    for i,(bot,top) in enumerate(legs):
        bx,by=bot;tx,ty=top
        ground=G.z(bx,by)
        K.part()
        K.loft([rect(bx,by,ground-1.3,6.3,6.6,.82),
                rect(bx,by,ground+3.1,6.3,6.6,.82),
                rect(bx+(tx-bx)*.2,by+(ty-by)*.2,ground+10.2,4.45,4.25,.55),
                rect(bx+(tx-bx)*.4,by+(ty-by)*.4,21.0,3.82,3.66,.40)],'conc_warm')
        K.collider((5.12,5.3,max(2,20-ground)),(bx,by,ground+(20-ground)*.5),0,'mast_foot')
        for sign in [-1,1]:
            fx=bx+sign*1.17;fy=by-2.07 if i in (0,1) else by+2.07
            K.beam((fx,fy,ground+.15),(fx,fy,ground+5.62),.5,.69,'steel_rust')
        K.beam((bx+(tx-bx)*.4,by+(ty-by)*.4,19.9),(tx,ty,57.1),
               1.5,2.05,'hull_dark' if i in (0,2) else 'metal_grey')
        K.box((tx,ty,56.95),(3.4,3.3,2.03),'steel_rust')
    for z,m in [(20.6,'steel_dark'),(36.5,'hull_rust'),(50.2,'steel_dark')]:
        v=(z-19.9)/(57.1-19.9)
        corners=[V((bx+(tx-bx)*(.4+.6*v),by+(ty-by)*(.4+.6*v),z))
                 for (bx,by),(tx,ty) in legs]
        for i in range(4):
            K.beam(corners[i],corners[(i+1)%4],.95,1.72,m)
        if z<45:
            for i in (1,2,3):
                a=corners[i];b=corners[(i+1)%4]
                K.beam(a,b+Z*14.2,.80,.84,'metal_grey')
                if i==2:K.beam(b,a+Z*14.2,.65,.8,'steel_dark')
    # The upper floor is a ring of plates; the aperture is actually open.
    for zz in (37.1,50.8):
        for ox,oy,sx,sy in [(-6.8,0,2.4,14.6),(6.8,0,2.45,14.6),(0,-6.45,11.6,1.8),(0,6.45,11.6,1.8)]:
            K.box((x+ox,y+oy,zz),(sx,sy,.76),'hull_grey')
        K.railing((x-7.75,y-7.15,zz+.43),(x+7.7,y-7.15,zz+.43),'metal_yellow')
        K.railing((x+8,y-6.5,zz+.43),(x+8,y+7.2,zz+.43),'metal_grey')
    # Oversize discharge chute and an access cabinet express the path into the plant.
    K.loft([rect(32.1,14,23.1,4.4,4.65,.5),rect(x,y,54.8,7.6,6.15,1.0)],'hull_rust',False)
    K.tube([(32.6,14.,23.1),(33,14.,18.5),(34.,11.,14.)],1.48,'metal_dark',8)
    for a in [(21.45,5.33),(32.55,19.45)]:
        K.tube([(a[0],a[1],3.6),(a[0],a[1],28),(a[0]+.4,a[1]+.45,31.7),
                (a[0]+.4,a[1]+.45,47.6)],.46,'steel_rust',9)
        for zz in (7.3,18.2,29.3,36.8,45.5):
            K.cyl((a[0]+(.4 if zz>31 else 0),a[1]+(.45 if zz>31 else 0),zz),.56,.45,'steel',10)
    K.ladder((34.4,7.7,1.0),(34.4,7.7,19.8),.96)
    K.ladder((34.35,8.25,21.),(34.35,8.25,36.7),.94)
    K.ladder((33.6,7.15,37.5),(33.6,7.15,50.7),.90)
    K.box((x+4.9,y-5.1,42.8),(4.3,5.7,9.1),'metal_teal')
    for zz in [40.6,44.9]:
        K.box((x+5.0,y-8.02,zz),(3.38,.24,1.35),'metal_dark')
        K.box((x+5.0,y-8.18,zz+.07),(2.9,.1,.95),'glass_warm')
    K.box((x+4.9,y-5.4,47.8),(5.35,6.6,.7),'hull_dark')
    K.light((x+4.6,y-8.3,45.),(1,.47,.22),12,.7,'window')

    # An octagonal flared feed mouth, inner cast liners and sacrificial lip blocks.
    # Shell winding faces out. The inner rings face into the hollow throat.
    rings=[rect(x,y,54.5,10.8,9.2,1.30),rect(x,y,58.5,13.4,11.3,1.65),
           rect(x,y,64.1,19.4,16.4,2.5),rect(x,y,66.,19.7,16.8,2.50)]
    inner=[rect(x,y,55.2,9.65,8.15,1.1),rect(x,y,59.3,12.1,10.1,1.4),
           rect(x,y,65.95,17.7,14.8,2.32)]
    K.part();K.loft(rings,'metal_orange',False)
    K.loft([list(reversed(r)) for r in inner],'hull_dark',False)
    for i in range(8):
        j=(i+1)%8
        K.face([rings[-1][i],rings[-1][j],inner[-1][j],inner[-1][i]],'steel')
        K.beam(rings[1][i],rings[2][i],.65,.82,'steel_rust')
        K.beam(rings[-1][i]+Z*.15,rings[-1][j]+Z*.15,.53,.55,'metal_hazard' if i in (3,6) else 'hull_grey')
        K.beam(inner[1][i],inner[2][i],.26,.37,'steel')
    K.marker('maw',(x,y,66.),(0,0,-1),(0,1,0))
    K.marker('maw_exit',(34,11,14),(1,0,-.5))
    # Drum axes point north (three.js -Z). Chevron teeth on the two drums
    # interleave, and both shafts extend beyond their replaceable journal bearings.
    for i, suffix in enumerate(('a','b')):
        cx=x-2.65 if i==0 else x+2.65
        z=60.;cy=y
        with K.into('maw_roller_'+suffix,loc=(cx,cy,z)):
            K.pipe((cx,cy-6.38,z),(cx,cy+6.38,z),.72,'steel',12)
            K.pipe((cx,cy-4.95,z),(cx,cy+4.95,z),2.28,'steel_dark',16)
            for row in range(8):
                y0=cy-4.8+row*1.2
                for tooth in range(7):
                    ang=math.tau*tooth/7.+(.26*min(row,7-row)+i*.43)
                    off=V((math.cos(ang),0,math.sin(ang)))
                    t=V((off.z,0,-off.x))
                    local_box(K,V((cx,y0+.57,z))+off*2.51,(t,V((0,1,0)),off),
                              (1.05,.94,.80),'steel_rust' if (row+tooth)%4==0 else 'metal_grey')
        for sign in [-1,1]:
            K.box((cx,cy+sign*6.03,z),(2.75,1.13,2.9),'hull_grey')
            K.pipe((cx,cy+sign*6.13,z),(cx,cy+sign*6.65,z),1.2,'steel',12)
        K.box((cx,cy-7.0,z-.1),(3.24,1.58,3.3),'metal_teal')
    for pos,normal,col in [((19,8,58),(-.35,-1,-.25),TEAL),((34.6,6.3,59.),(.2,-1,-.2),AMBER),
                           ((33,20.1,64.),(0,1,.1),RED),((20.2,18.3,65.),(-.8,.2,-.4),TEAL)]:
        lamp_box(K,pos,normal,col,22,1.10,col==RED)

    # Deeper open Warren truss at the root; a slender fork carries the induction head.
    root=V((18,18,48));tip=V((-58,60,48));axis=(tip-root).normalized();side=Z.cross(axis).normalized()
    node_t=[0,.075,.175,.31,.445,.58,.705,.82,.918,1.]
    def point(t,s=0,h=0):
        return root.lerp(tip,t)+side*s+Z*h
    for i,(a,b) in enumerate(zip(node_t,node_t[1:])):
        wa,wb=4.58-1.83*a,4.58-1.83*b
        ha=10.15-4.55*a+1.05*math.sin(math.pi*a)
        hb=10.15-4.55*b+1.05*math.sin(math.pi*b)
        K.part()
        for sign in (-1,1):
            la=point(a,sign*wa,-.22);lb=point(b,sign*wb,-.22)
            ua=point(a,sign*wa,ha);ub=point(b,sign*wb,hb)
            K.beam(la,lb,1.12-.39*a,1.47-.52*a,'metal_grey')
            K.beam(ua,ub,1.09-.36*a,1.35-.47*a,'hull_rust')
            K.beam(la,ua,.80-.23*a,.84-.23*a,'metal_dark')
            K.beam(la if i%2==0 else ua,ub if i%2==0 else lb,.89-.29*a,.93-.32*a,
                   'metal_yellow' if i in (0,3,5,8) else 'metal_grey')
            if i in (0,2):
                K.beam(ua,lb,.35,.51,'steel_dark')
            if i in (0,4,7):
                K.pipe(ua-side*sign*.86,ua+side*sign*.86,1.24-.27*a,'steel_rust',16)
                K.pipe(ua+side*sign*.78,ua+side*sign*1.03,.72-.19*a,'metal_grey',12)
        K.beam(point(a,-wa,ha),point(a,wa,ha),.49,.57,'steel_dark')
        K.beam(point(a,-wa,-.24),point(a,wa,-.24),.55,.67,'hull_dark')
        K.beam(point(a,-wa,ha),point(b,wb,hb),.32,.42,'steel_dark')
    # Cantilevered winchman’s cab and cable drums hang beside, not below, the
    # guide rails. The warm slot in its brow makes the scale of this truss legible.
    cab=point(.126,5.2,-1.35)
    cab_frame=(axis,side,Z)
    local_box(K,cab,cab_frame,(4.8,3.25,3.78),'metal_yellow')
    local_box(K,cab+Z*.39+side*1.65,cab_frame,(4.05,.18,1.38),'metal_dark')
    for dx in (-1.14,.29,1.35):
        cp=cab+axis*dx+side*1.76+Z*.45
        local_box(K,cp,cab_frame,(.84,.08,.99),'glass_warm' if dx<1 else 'emit_warm')
    local_box(K,cab+Z*2.02,cab_frame,(5.34,3.97,.55),'hull_dark')
    for dx in (-1.75,1.75):
        K.beam(cab+axis*dx-side*.8+Z*2.22,point(.126,2.7,3.48)+axis*dx,.48,.56,'steel_rust')
    K.light(cab+side*1.89+Z*.42,(1,.50,.24),14,.73,'window')
    for t in (.32,.63):
        stand=point(t,3.75,1.38)
        K.beam(stand-Z*1.50,stand+side*.67,.25,.30,'steel_dark')
        lamp_box(K,stand+side*.67,-axis*.58-side*.62+Z*.35,AMBER if t<.4 else TEAL,22,1.36)

    # A service walk follows the northeast face. Slung guide rails leave a gap
    # along their underside for material to travel back to the tower.
    K.catwalk(point(0,-4.16,.43),point(.59,-3.47,.43),1.30)
    K.catwalk(point(.59,-3.47,.43),point(.99,-2.86,.43),1.30)
    for sign in [-1,1]:
        K.beam(point(0.,sign*1.18,-1.22),point(1.,sign*1.18,-1.22),.31,.45,'steel_dark')
        K.tube([point(t,sign*(3.82-1.4*t),.8) for t in (0,.32,.7,1.)],
               .24,'steel_rust' if sign<0 else 'steel',8)
    # Gantry forks and head. A broad gap in its plates exposes the bore.
    head=V((-62.,62.,46.))
    for sign in [-1,1]:
        K.truss(point(.955,sign*1.89,2.1),head+side*3.5+Z*.8 if sign==1 else head-side*3.5+Z*.8,
                1.,1.45,'hull_grey',2,.29)
    for i in range(8):
        a0=math.tau*i/8
        radial=V((math.cos(a0),math.sin(a0),0));tangent=Z.cross(radial)
        p=head+radial*4.5
        K.part()
        local_box(K,p,(tangent,-radial,Z),(3.22,2.10,2.05),'metal_dark' if i%3 else 'metal_yellow')
        if i in (0,2,5,7):
            K.beam(p+radial*.5,p+radial*1.12-Z*2.0,.82,1.15,'hull_rust')
            lamp_box(K,p-Z*1.10,-Z,TEAL,12,.57)
    K.torus(head+Z*.37,4.28,.46,'steel',22,7)
    K.marker('tractor_head',head,(0,0,-1),(0,1,0))
    K.marker('tractor_foot',(-62,62,-74))
    K.marker('boom_feed_start',(-58,60,45.5),-axis)
    K.marker('boom_feed_end',(18,18,45.5),-axis)
    # A short incline at the root hands the ore into the open Maw; it stays above
    # the tower on the pit side where transported stones can be seen in profile.
    transfer=[point(.018,0,-1.7),V((19.1,17.5,48.8)),V((19.7,17.2,57.0)),V((21.0,16.1,63.1))]
    for sign in (-1,1):
        K.tube([v+side*2.00*sign for v in transfer],.31,'steel_rust',8)
    K.marker('maw_lift',(21.2,16.1,63.2),(1,-.3,.5))
    mast_headworks(K,point)
    for t in [.03,.21,.49,.72,.965]:
        p=point(t,-(4.08-1.3*t),1.75)
        K.beam(p-Z*1.17,p,.18,.2,'steel')
        lamp_box(K,p,(-side*.75-Z*.48), AMBER if t<.3 else TEAL,14,.82)
    for p in [(21.1,7.2,4.1),(33.3,7.5,4.1),(32.5,19.4,16.7),(34.0,8.,21.8),
              (21.0,7.4,38.0),(33.5,7.4,38.0),(21.1,7.6,51.7),(33.4,18.5,52.)]:
        lamp_box(K,p,(.45,-.5,-.8),AMBER if p[2] in (4.1,38.0) else TEAL,15,.89)
    lamp_box(K,(23.25,8.43,63.6),(0,-1,.1),RED,20,1.01,True)
    K.marker('mast_base',(x,y,G.z(x,y)))


def warden(K,angle,radius,height,style):
    """A tripod bolted separately into uneven inner benches, all heads turned inward."""
    a=math.radians(angle)
    x=PIT_C[0]+radius*math.cos(a);y=PIT_C[1]+radius*math.sin(a)
    floor=G.z(x,y)
    up=Z;inward=V((-math.cos(a),-math.sin(a),0));right=inward.cross(Z)
    c=V((x,y,floor));joint=c+up*height
    K.part()
    base_points=[c+right*(-2.8)-inward*1.5,c+right*2.1-inward*1.3,c+inward*3.4]
    for i,p in enumerate(base_points):
        gz=G.z(p.x,p.y);foot=V((p.x,p.y,gz))
        K.loft([rect(p.x,p.y,gz-1.1,2.45,2.45,.35),rect(p.x,p.y,gz+.8,2.08,2.05,.21)],'conc_dark')
        K.beam(foot+up*.68,joint+right*(.58 if i==1 else -.42)-up*1.26,
               .69 if style else .59,.97,'hull_rust' if i==0 else 'steel_dark')
    middle=c+up*(height*.66)
    local_box(K,middle,(right,inward,Z),(3.10,2.75,1.31),'metal_grey')
    K.beam(middle,joint,.91,1.03,'metal_grey')
    K.pipe(joint-right*2.1,joint+right*1.7,.49,'steel',10)
    cap=joint+inward*.58+up*.35;tilt=(inward-.22*up).normalized()
    top=right.cross(tilt)
    if top.z<0:top=-top
    frame=(right,tilt,top)
    if style==0:
        local_box(K,cap,frame,(3.30,3.80,2.35),'hull_grey')
        lip=cap+tilt*1.96
        local_box(K,lip,frame,(2.25,.24,1.34),'hull_dark')
        K.pipe(lip+tilt*.13,lip+tilt*.40,.51,'steel',10)
        K.pipe(lip+tilt*.38,lip+tilt*.46,.38,'glass',10)
    elif style==1:
        for j in [-1,1]:
            p=cap+right*j*1.05
            K.pipe(p-tilt*.98,p+tilt*1.85,.79,'hull_grey',10)
            K.pipe(p+tilt*1.85,p+tilt*2.04,.74,'metal_dark',10)
            K.pipe(p+tilt*2.04,p+tilt*2.14,.49,'glass',10)
        local_box(K,cap+Z*.7,frame,(3.,1.67,.48),'metal_green')
    else:
        K.cyl(joint+Z*.25,1.45,.85,'steel_dark',12)
        local_box(K,cap,frame,(2.65,2.7,1.84),'metal_teal')
        for j in [-1,1]:
            K.beam(joint+right*j*.92,joint+right*j*1.55+inward*1.2+Z*3.15,.29,'steel_rust')
        K.beam(joint-right*1.55+inward*1.2+Z*3.15,
               joint+right*1.55+inward*1.2+Z*3.15,.38,.49,'hull_grey')
    cabinet=c+right*2.94-inward*.08
    gz=G.z(cabinet.x,cabinet.y)
    local_box(K,(cabinet.x,cabinet.y,gz+1.43),(right,inward,Z),(1.35,1.65,2.86),'metal_teal')
    K.cable((cabinet.x,cabinet.y,gz+2.2),middle-right*.85,.65,.14,'steel_rust',6)
    lamp_box(K,joint+right*1.54+up*.14,tuple(-right*.35+inward*.55-Z*.25),RED if style==2 else AMBER,12,.64,style==2)
    return c


def drill(K,x,y,heading,mast_height):
    """Bench crawler: oil cooler, hollow mast, top drive and a dropped drill string."""
    a=math.radians(heading)
    fwd=V((math.cos(a),math.sin(a),0));left=Z.cross(fwd);frame=(fwd,left,Z)
    center=V((x,y,G.z(x,y)+1.20))
    K.part()
    for s in (-1,1):
        c=center+left*1.63*s
        local_box(K,c,frame,(5.85,1.12,1.38),'rubber')
        local_box(K,c-Z*.05+left*.56*s,frame,(4.96,.14,.78),'hull_dark')
        for l in (-2.,0.,1.94):
            p=c+fwd*l+left*.54*s
            K.pipe(p,p+left*.15*s,.47,'steel_dark',8)
    local_box(K,center+Z*1.31,frame,(6.2,3.85,1.43),'metal_yellow')
    local_box(K,center-fwd*1.31+Z*2.79,frame,(3.32,2.03,1.77),'metal_grey')
    seat=center-left*.99+Z*2.94
    local_box(K,seat,frame,(2.06,1.37,2.07),'metal_orange')
    local_box(K,seat+fwd*1.05+Z*.18,frame,(.09,1.16,.94),'glass_warm')
    base=center+fwd*2.8+left*.53+Z*1.1;d=V((fwd.x*.075,fwd.y*.075,1)).normalized()
    end=base+d*mast_height
    K.truss(base,end,1.14,1.56,'metal_yellow',max(3,round(mast_height/2.1)),.19)
    K.pipe(base+fwd*.82+Z*.55,end+fwd*.82,.21,'steel_dark',8)
    K.pipe(base+fwd*.82-Z*1.6,base+fwd*.82+Z*.65,.17,'steel',8)
    local_box(K,base+d*(mast_height*.64)+fwd*.65,frame,(1.25,1.46,1.65),'hull_rust')
    K.beam(center+left*.8-fwd*.65+Z*2.6,base+d*(mast_height*.50),.32,.42,'steel')
    K.cable(center-fwd*.75+left*.62+Z*3.4,end,.92,.115,'rubber',8)
    lamp_box(K,seat+Z*1.18,fwd-left*.16-Z*.15,TEAL,12,.76)
    K.light(end+Z*.2,RED,7,.47,'beacon')


def build_benches(K):
    for az,rad,h,style in [(188,43,10,0),(225,38,8.3,1),(253,48,7.4,1),(284,44,12.3,2),
                           (317,50,15.1,0),(348,45,8.3,1),(23,43,12.1,0),(139,49,11.5,2),(164,59,6.7,1)]:
        p=warden(K,az,rad,h,style)
        if az==317:K.marker('warden',p+Z*h,V((PIT_C[0]-p.x,PIT_C[1]-p.y,0)).normalized())
    for i,(x,y,heading,h) in enumerate([(-149,9,118,10.2),(-131,-30,25,8.4),(-103,-46,68,11.1),
                                        (-56,-46,151,8.8),(-10,37,202,9.4),(-129,68,293,11.8)]):
        drill(K,x,y,heading,h)
        if i==4:K.marker('rim_drill',(x,y,G.z(x,y)+h*.65))
    # A thin, partially decommissioned rim defence. Break it at the working face,
    # around each haul entrance, and along the plunging south-west scree slope.
    co=math.cos(PIT_ROT);si=math.sin(PIT_ROT)
    def perimeter(deg):
        a=math.radians(deg);px=(PIT_A+3.6)*math.cos(a);py=(PIT_B+3.7)*math.sin(a)
        x=PIT_C[0]+px*co-py*si; y=PIT_C[1]+px*si+py*co
        return V((x,y,G.z(x,y)))
    for start,stop in [(8,24),(36,53),(115,123),(157,173),(182,194),(232,247),(255,273),(284,304),(312,320)]:
        arc=[]
        for t in range(start,stop+1,3):
            arc.append(perimeter(t))
        for i,(a,b) in enumerate(zip(arc,arc[1:])):
            if abs(a.z-b.z)>3.3:continue
            d=b-a;d.z=0;d.normalize();n=Z.cross(d).normalized()
            aa=a+d*.14;bb=b-d*.14;z0=max(a.z,b.z)+.2
            lower=[aa-n*.85,bb-n*.85,bb+n*.85,aa+n*.85]
            upper=[V((aa.x,aa.y,z0+1.02))-n*.36,V((bb.x,bb.y,z0+1.02))-n*.36,
                   V((bb.x,bb.y,z0+1.02))+n*.36,V((aa.x,aa.y,z0+1.02))+n*.36]
            K.part();K.loft([[p-Z*.48 for p in lower],upper], 'conc_dark' if i%5 else 'conc_warm')
        if len(arc)>3:
            p=arc[len(arc)//2]
            K.lamp(p,3.8, 'flood', AMBER if start in (36,157,255) else TEAL,14,.83)

    # Shot-hole collars, lead cables and a firing shelter. Leave the centre empty
    # so the material throwing and sorting systems have a distinct silhouette.
    for x,y in [(-108.,-44.),(-137.,-20.),(-21.,33.)]:
        z=G.z(x,y)
        K.part();K.box((x,y,z+.81),(2.75,1.8,1.64),'metal_red')
        K.box((x,y,z+1.71),(3.10,2.07,.27),'hull_dark')
        previous=V((x,y,z+1.0))
        for j in range(3):
            px=x-2.9-j*2.8;py=y+1.6+math.sin(j+1)*1.42
            floor=G.z(px,py);end=V((px,py,floor+.28))
            K.cyl(end,.47,.51,'steel_dark',9)
            mid=(previous+end)*.5;mid.z=max(G.z(mid.x,mid.y)+.18,(previous.z+end.z)*.5-.25)
            K.tube([previous,mid,end],.085,'rubber',5);previous=end
            K.pipe(end,end+Z*.71,.115,'metal_orange',7)
        K.light((x,y-.96,z+1.22),AMBER,9,.45)


def build(out,log):
    K=Kit('pit',1081)
    build_wall(K)
    build_mast(K)
    build_benches(K)
    K.finalize(out,log)
