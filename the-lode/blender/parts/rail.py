"""The Whip: a surveyed closed railway and its enclosed winding headframe.

The samples are the running surface at wheel contact. The same frames form the
railheads, which avoids fitting a second spline to a vertically inverted train.
"""
import bisect
import math
from mathutils import Vector
from lib.kit import Kit,V,Z
from lib.layout import three,BRIDGE_W,BRIDGE_E,ANCHORS
from lib.ground import G

E=V((*BRIDGE_E,0))
W=V((*BRIDGE_W,0))
SPAN=(E-W).length
F=(E-W).normalized()
N=Z.cross(F)
AZ=math.degrees(math.atan2(F.y,F.x))
LANE=2.85
RAILHEAD=.26
COLD=(.62,.80,1.)
SODIUM=(1.,.52,.20)
RED=(1.,.065,.035)

def local(u,v,z):
    return E+F*u+N*v+Z*z

def blk(k,u,v,z,size,mat):
    k.box(local(u,v,z),size,mat,AZ)

def ring(u,v,z,du,dv):
    return [local(u+i*du/2,v+j*dv/2,z) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]

def signal(k,p,color=COLD,r=15,power=.6,face=(0,-1,-.22),kind='flood'):
    p=V(p);d=V(face).normalized()
    k.part()
    k.beam(p-d*.25,p+d*.22,.70,.46,'metal_dark')
    paint='emit_red' if kind=='beacon' else ('emit_cool' if color[2]>.65 else 'emit_sodium')
    k.beam(p+d*.22,p+d*.28,.56,.30,paint)
    k.light(p+d*.38,color,r,power,kind)

def smooth(t):
    return t*t*(3-2*t)

class Survey:
    def __init__(self):
        self.points=[]
        self.marks={}

    def section(self,kind,fun,n):
        for j in range(n+1):
            p,t,h=fun(j/n);t=V(t).normalized();p=V(p);h=(V(h)-t*t.dot(V(h))).normalized()
            sd=h.cross(t).normalized()
            if j==0 and self.points:
                prev=self.points[-1]
                if (prev['p']-p).length>.022:
                    raise ValueError(f"Rail survey gap at {kind}: {prev['p']}, {p}")
                prev.update(t=t,up=h,side=sd,kind=kind)
                continue
            prev=self.points[-1] if self.points else None
            s=prev['s']+(prev['p']-p).length if prev else 0.
            self.points.append(dict(p=p,t=t,up=h,side=sd,kind=kind,s=s))

    def line(self,kind,a,b,up=Z):
        a,b=V(a),V(b)
        self.section(kind,lambda t:(a.lerp(b,t),b-a,up),max(1,math.ceil((b-a).length/2.9)))

    def cubic(self,kind,a,b,c,d):
        a,b,c,d=map(V,(a,b,c,d))
        def pt(t):
            u=1-t
            return (a*(u*u*u)+b*(3*t*u*u)+c*(3*t*t*u)+d*(t*t*t),
                    (b-a)*(3*u*u)+(c-b)*(6*u*t)+(d-c)*(3*t*t),Z)
        self.section(kind,pt,max(5,math.ceil(((b-a).length+(c-b).length+(d-c).length)/2.45)))

    def mark(self,name):
        self.marks[name]=self.points[-1]['s'] if self.points else 0.

    def sample(self,s):
        i=max(0,min(len(self.points)-2,bisect.bisect_right(self.lengths,s)-1))
        a,b=self.points[i:i+2]
        t=(s-a['s'])/max(.001,b['s']-a['s'])
        return dict(p=a['p'].lerp(b['p'],t),t=a['t'].lerp(b['t'],t).normalized(),
                    up=a['up'].lerp(b['up'],t).normalized(),side=a['side'].lerp(b['side'],t).normalized(),
                    kind=a['kind'])

def make_survey():
    q=Survey();q.mark('load');q.line('main',(114,8,8),(114,29,8))
    def loop(t):
        a=math.pi*t
        return (V((121-7*math.cos(a),29+7*math.sin(a),8)),
                V((math.sin(a),math.cos(a),0)),Z)
    q.section('north_loop',loop,18)
    q.cubic('main',(128,29,8),(128,20,8),(128,6,6.8),(128,-4,5.5))
    q.cubic('main',(128,-4,5.5),(128,-14,4.2),(128,-20,3.9),(128,-28,3.25))
    q.mark('signal');q.mark('runup')
    north=W+N*LANE+Z*(-1+RAILHEAD)
    alpha=math.atan2(F.x,-F.y)
    radius=12.
    outer=V((north.x-radius*(1-math.cos(alpha)),north.y+radius*math.sin(alpha),.83))
    q.cubic('runup',(128,-28,3.25),(128,-35,2.72),outer+V((0,5.5,.53)),outer)
    def arc_onto_bridge(t):
        a=alpha*t
        ht=outer.z+(north.z-outer.z)*t
        return (V((outer.x+radius*(1-math.cos(a)),outer.y-radius*math.sin(a),ht)),
                V((radius*alpha*math.sin(a),-radius*alpha*math.cos(a),north.z-outer.z)),Z)
    q.section('runup',arc_onto_bridge,12)
    q.mark('bridgeOutStart')
    q.line('bridge_out',north,local(0,LANE,-8+RAILHEAD));q.mark('bridgeOutEnd')
    q.line('runup',local(0,LANE,-8+RAILHEAD),local(6,LANE,-8+RAILHEAD))
    # The east abutment is pitched down from the west. The short shard approach
    # returns to level before the large vertical transition starts.
    zlow=-8+RAILHEAD;spring=zlow+20
    def bottom_out(t):
        a=math.pi*.5*t
        return (local(6+20*math.sin(a),LANE,spring-20*math.cos(a)),
                F*math.cos(a)+Z*math.sin(a), -F*math.sin(a)+Z*math.cos(a))
    q.section('climb',bottom_out,20)
    q.line('climb',local(26,LANE,spring),local(26,LANE,92),-F);q.mark('release')
    def head(t):
        a=math.pi*t
        p=local(35-9*math.cos(a),LANE*(1-2*smooth(t)),92+9*math.sin(a))
        tangent=F*(9*math.pi*math.sin(a))+N*(-12*LANE*t*(1-t))+Z*(9*math.pi*math.cos(a))
        up=-F*math.cos(a)+Z*math.sin(a)
        return p,tangent,up
    q.section('crest',lambda t:head(t*.5),15);q.mark('crest')
    q.section('crest',lambda t:head((1+t)*.5),15)
    q.line('descent',local(44,-LANE,92),local(44,-LANE,74),F)
    def wrap(t):
        a=math.pi*smooth(t);da=6*math.pi*t*(1-t)
        p=local(35+9*math.cos(a),-LANE-12*math.sin(a),74-44*t)
        dt=F*(-9*math.sin(a)*da)+N*(-12*math.cos(a)*da)-Z*44
        return p,dt,F*math.cos(a)-N*math.sin(a)
    q.section('spiral',wrap,34)
    q.line('descent',local(26,-LANE,30),local(26,-LANE,spring),-F)
    def bottom_back(t):
        a=math.pi*.5*t
        return (local(6+20*math.cos(a),-LANE,spring-20*math.sin(a)),
                -F*math.sin(a)-Z*math.cos(a),-F*math.cos(a)+Z*math.sin(a))
    q.section('descent',bottom_back,20);q.line('return',local(6,-LANE,zlow),local(0,-LANE,zlow))
    q.mark('bridgeInStart');south=W-N*LANE+Z*(-1+RAILHEAD);q.line('bridge_in',local(0,-LANE,zlow),south);q.mark('bridgeInEnd')
    # Establish the westward tangent before the incoming line turns north to x=110.5.
    radius=13.4;clear=(south.x-radius*(1+F.y)-110.5)/F.x
    lead=south-F*clear;lead.z=-.36
    q.line('return',south,lead)
    centre=lead+N*radius
    def back(t):
        # Center minus the bridge-lane normal is the start radius. Rotate clockwise to west.
        a=math.atan2(-N.y,-N.x)-alpha*t
        p=V((centre.x+radius*math.cos(a),centre.y+radius*math.sin(a),lead.z+2.62*t))
        dt=V((radius*alpha*math.sin(a),-radius*alpha*math.cos(a),2.62))
        return p,dt,Z
    q.section('return',back,14)
    p=q.points[-1]['p']
    q.cubic('return',p,p+V((0,6,.74)),(110.5,-26,4.05),(110.5,-20,4.68))
    q.cubic('return',(110.5,-20,4.68),(110.5,-10,5.73),(114,-2,8),(114,8,8))
    q.mark('length');q.lengths=[p['s'] for p in q.points]
    return q

def section_profile(k,path,cross,mat):
    """Continuous rail extrusion in the surveyed frame. u is left; v is up."""
    if len(path)<2:return
    rings=[[pt['p']+pt['side']*u+pt['up']*v for u,v in cross] for pt in path]
    # side × up = tangent; the profile is CCW in side/up and extrudes forward.
    k.loft(rings,mat)

def rail_geometry(k,q):
    # Pairs of dark steel stringers and polished railheads, on all fixed sections.
    spans=[];current=[]
    for i,point in enumerate(q.points[:-1]):
        active=not point['kind'].startswith('bridge_')
        if active:
            if not current:current=[point]
            current.append(q.points[i+1])
        elif current:spans.append(current);current=[]
    if current:spans.append(current)
    for pts in spans:
        for side in (-1,1):
            k.part()
            def rect(c,v,w,h):
                return [(c-w/2,v-h/2),(c+w/2,v-h/2),(c+w/2,v+h/2),(c-w/2,v+h/2)]
            section_profile(k,pts,rect(side*1.05,-.12,.24,.24),'steel')
            section_profile(k,pts,rect(side*1.05,-.49,.15,.54),'steel_dark')
            section_profile(k,pts,rect(side*1.05,-.82,.45,.16),'steel_rust')
        k.part()
        section_profile(k,pts,[(-.33,-1.86),(.33,-1.86),(.48,-.85),(-.48,-.85)],'metal_dark')
    # Ordinary insulated ties at wide intervals, with a heavier crosshead at turnout structures.
    s=.45;step=0
    while s<q.marks['length']-.5:
        f=q.sample(s);tag=f['kind'];p=f['p'];up=f['up'];side=f['side']
        if not tag.startswith('bridge_'):
            k.part()
            run=1.72 if tag in ('climb','crest','spiral','descent') else 1.58
            k.beam(p-side*run-up*.57,p+side*run-up*.57,.27,.41,'hull_rust' if step%11==5 else 'steel_dark')
            if step%4==0 and tag in ('climb','descent','crest','spiral'):
                k.beam(p-up*.72,p-up*2.07,.65,.72,'metal_grey')
        step+=1;s+=(2.72,3.22,2.98,3.35,2.84)[step%5]
    # Concrete trestles, expansion caps and piled footings sampled along main-island line.
    ranges=[(.85,q.marks['bridgeOutStart']-5.9),(q.marks['bridgeInEnd']+4.4,q.marks['length']-5.)]
    for start,end in ranges:
        s=start;i=0
        while s<end:
            fr=q.sample(s);p=fr['p'];side=fr['side'];t=fr['t'];z0=G.z(p.x,p.y)
            if z0>-9000 and p.z-z0>1.5:
                k.part()
                ht=p.z-z0;foot=V((p.x,p.y,z0));az=math.degrees(math.atan2(t.y,t.x))
                k.box(foot+Z*.17,(2.4,3.5,.70),'conc_dark',az)
                width=.92 if ht>3.5 else 1.2
                k.box(foot+Z*(ht*.5-.40),(1.3,width,ht-.56),'conc_warm',az)
                rr=p-Z*1.16;k.beam(rr-side*1.72,rr+side*1.72,.86,.53,'conc')
                if ht>4:
                    for dd in (-1,1):k.beam(foot+Z*(ht*.35),rr+side*dd*1.44,.56,.93,'conc')
                if i%3==1:
                    l=rr+side*1.44;signal(k,l+Z*.37,SODIUM,10,.43,tuple(side*.9-Z*.35))
                    k.box(l-Z*.24,(.55,.52,.64),'metal_green',az)
            i+=1;s+=(10.3,12.3,9.75,13.4,11.6)[i%5]
    # Inspector's refuges, a wayside signal and the bin weighing station share the rail gauge.
    for s,l in [(10.7,5.2),(32.,4.6),(q.marks['signal'],6.1),(q.marks['length']-37,4.2)]:
        f=q.sample(s);p=f['p'];t=f['t'];side=f['side'];ref=p+side*3.1-Z*.35
        k.part();k.beam(ref-t*l/2,ref+t*l/2,1.55,.30,'metal_dark')
        k.railing(ref+side*.69-t*l/2,ref+side*.69+t*l/2,'steel_rust')
        for offset in (-l*.34,l*.34):k.beam(p-Z*1.38+t*offset,ref+side*.58+t*offset,.28,.42,'steel_rust')
        head=ref+side*.48+Z*(2.88 if s==q.marks['signal'] else 2.01)
        k.beam(ref+side*.48,head,.19,'metal_dark');signal(k,head,RED if s==q.marks['signal'] else COLD,15,.68,tuple(-t),'beacon' if s==q.marks['signal'] else 'flood')
    # Yard switch and switch house at the north end, inside the compact radius.
    k.part();k.box((121.6,23.3,1.72),(3.9,7.6,3.45),'conc_warm')
    k.box((121.6,23.16,3.58),(4.49,8.1,.56),'hull_grey')
    k.box((121.6,19.44,1.70),(2.86,.19,1.05),'glass_warm')
    k.pipe((123.01,25.4,2.2),(123.01,25.4,5.74),.34,'steel_rust')
    signal(k,(122.5,19.30,2.94),SODIUM,13,.67)

def frame_tower(k):
    # Four battered piers form a compact quadrilateral core. The west face
    # carries the rising track; the full south-west envelope belongs to the descent.
    for u in (31.25,39.15):
        for v in (-6.15,5.95):
            k.part()
            toe=local(u,v,-8);ground=G.z(toe.x,toe.y)
            if ground<-9000:raise ValueError('Whip footing outside port shard')
            k.loft([ring(u,v,ground-.85,4.9,4.7),ring(u,v,ground+.62,4.9,4.7),
                    ring(u,v,ground+2.15,3.65,3.61),ring(u,v,ground+3.10,3.63,3.60)],'conc_dark')
            k.loft([ring(u,v,ground+2.95,3.5,3.46),ring(u,v,3.2,3.03,2.83),
                    ring(u+(35.-u)*.11,v*.95,13.5,2.07,2.20)],'conc_warm')
            for du in (-1.23,1.23):
                for dv in (-1.24,1.24):
                    k.cyl(local(u+du,v+dv,ground+3.16),.22,.29,'steel',6)
            signal(k,local(u,v+(-1.58 if v<0 else 1.58),1.45),COLD,16,.67,tuple(N*(-1 if v<0 else 1)-Z*.35))
    # Cross sections deliberately change in broad, unequal stages to leave the spiral legible.
    levels=[(9.3,8.5,12.0),(20.5,8.5,11.8),(30.3,8.15,11.45),(43.4,7.85,10.6),
            (58.3,7.52,10.20),(70.2,7.18,9.65),(82.8,6.83,9.18),(91.6,6.52,8.75)]
    def corners(lev):
        z,du,dv=lev
        return [local(35.1+a*du/2,.05+b*dv/2,z) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    for idx,(low,high) in enumerate(zip(levels,levels[1:])):
        lo=corners(low);hi=corners(high)
        for j in range(4):
            jj=(j+1)%4;k.part()
            k.beam(lo[j],hi[j],1.00 if idx<3 else .88,.86,'hull_grey')
            k.beam(hi[j],hi[jj],.77,1.03,'metal_dark')
            k.beam(lo[j],hi[jj],.57,.64,'steel_rust' if j<2 else 'steel_dark')
            if idx in (0,3,5) and j%2==0:
                k.beam(lo[jj],hi[j],.48,.52,'steel_dark')
            # Gusset plates terminate every primary diagonal at the cap steel.
            k.box(hi[j],(1.27,1.27,1.34),'hull_rust' if idx%3==0 else 'hull_dark',AZ)
        if idx in (0,2,4,6):
            z=high[0]+.12
            for j in (0,2):k.beam(lo[j],hi[(j+2)%4],.36,.46,'steel_dark')
            blk(k,35.2,.05,z,(6.35,9.14,.34),'metal_grey')
            # Low-watt task lamps inside the frame, not a long string of beacons.
            signal(k,local(38.05,-3.62,z+1.1),COLD,15,.70,tuple(F-N-Z*.22))
            signal(k,local(32.35,3.85,z+1.3),SODIUM,12,.59,tuple(-F+N-Z*.25))
    # Track bracketry on the open western and eastern faces. At the handover,
    # only the rear of the rail is supported. The ascending payload flies free.
    for v,us,zlevels,dir_ in [
            (LANE,26,(16.8,29.2,42.9,57.5,72.,85.8),1),
            (-LANE,26,(15.5,24.8),1),
            (-LANE,44,(78.5,85.9),-1)]:
        for z in zlevels:
            for s in (-1,1):
                k.part()
                a=local(31.5 if dir_==1 else 38.65,v+s*1.16,z-2.25)
                b=local(us+dir_*1.60,v+s*1.16,z)
                c=local(31.5 if dir_==1 else 38.65,v+s*1.16,z+.22)
                k.beam(a,b,.42,.65,'steel_rust')
                k.beam(b,c,.47,.58,'metal_dark')
            signal(k,local(us+dir_*1.92,v+(1.62 if dir_==1 else -1.62),z+.68),SODIUM,11,.48,tuple(N-Z*.3))
    # Spiral supports run from the core onto the back of the corkscrew, keeping the
    # open hopper on the outside. Their intersections follow the actual pitched helix.
    for t in (.15,.32,.52,.69,.85):
        angle=math.pi*smooth(t);r=F*math.cos(angle)-N*math.sin(angle);z=74-44*t
        rim=local(35+9*math.cos(angle),-LANE-12*math.sin(angle),z)-r*1.7
        foot=local(35+3.5*math.cos(angle),-2.9-2.5*math.sin(angle),z-4.1)
        other=foot+Z*5.45
        k.part();k.beam(foot,rim,.67,.77,'hull_rust');k.beam(other,rim,.58,.71,'metal_dark')
        if t==.52 or t==.85:signal(k,rim-Z*.62,COLD,13,.63,tuple(-r-Z*.4))
    # The brake accumulator hangs off the southern frame on a pair of corbels.
    # It breaks up the open lattice below the empty-car descending flight.
    k.part()
    blk(k,35.65,-6.61,22.85,(7.86,4.49,1.12),'metal_dark')
    for u in (32.5,38.85):
        k.beam(local(u,-4.60,17.45),local(u,-8.3,22.2),.69,.82,'hull_rust')
        k.beam(local(u,-4.85,22.33),local(u,-8.74,22.33),.55,.73,'steel_dark')
    k.loft([ring(35.6,-6.8,23.42,7.56,3.78),ring(35.6,-6.8,28.72,7.56,3.78),
            ring(35.25,-6.68,29.8,5.34,3.34)],'hull_rust')
    for u,sz in ((33.2,1.32),(35.8,2.84),(38.17,1.03)):
        blk(k,u,-8.76,25.91,(sz,.12,3.19),'hull_dark')
        blk(k,u,-8.85,26.96,(sz*.84,.11,.77),'metal_teal')
    k.pipe(local(33.1,-7.04,29.15),local(33.1,-7.04,32.08),.59,'steel_dark',10)
    blk(k,35.35,-8.78,23.85,(7.6,1.65,.29),'steel_rust')
    k.railing(local(31.62,-9.46,24.02),local(39.04,-9.46,24.02),'metal_yellow')
    for u in (36.7,37.93):
        k.tube([local(u,-7.7,23.01),local(u,-7.7,19.28),local(u,-4.15,19.28),
                local(u,-4.15,14.22)],.27,'steel_rust',8)
    for u in (32.72,37.78):
        signal(k,local(u,-8.89,27.9),SODIUM,12,.69,tuple(-N-Z*.29))
    # The recovery block occupies the inside of the top loop. No cap spans the
    # inverted track or the release column; the wheel and two disc brakes are accessible.
    k.part()
    blk(k,35.4,1.5,89.0,(6.85,6.3,4.55),'hull_rust')
    k.pipe(local(35.2,-3.9,92),local(35.2,5.55,92),.74,'steel',14)
    for v in (-2.4,2.4):
        c=local(35.2,v,92.);k.torus(c,4.85,.49,'metal_grey',32,7,N)
        k.torus(c,1.42,.45,'hull_rust',20,6,N)
        for j in range(7):
            angle=math.tau*j/7+.18
            v0=F*math.cos(angle)+Z*math.sin(angle)
            k.beam(c+v0*1.13,c+v0*4.76,.51,.56,'steel_dark')
        k.pipe(c-N*.31,c+N*.31,1.01,'steel_dark',12)
    for uu in (31.85,38.5):
        blk(k,uu,3.16,91.62,(2.25,1.34,2.82),'metal_yellow')
        k.pipe(local(uu,2.80,90.90),local(uu,5,90.90),.42,'steel',12)
    # Compact hoist manway and cable ducts climb the north-east corner.
    for u,v in [(38.2,4.8),(39.18,4.56)]:
        k.pipe(local(u,v,5.8),local(u-.78,v-.67,81.5),.33,'steel_rust',8)
    for i,(z1,z2) in enumerate([(2.,17.),(17.,31.),(31.,45.3),(45.3,59.),(59.,73.4),(73.4,84.)]):
        v=6.69 if i%2 else 5.98
        at=local(35.55,v,z1)
        k.ladder(at,local(35.55,v,z2),.86,'steel')
        blk(k,35.62,6.24,z2,(4.15,2.55,.38),'metal_grey')
        k.railing(local(33.76,7.35,z2+.23),local(37.47,7.35,z2+.23),'metal_yellow')
        if i in (0,2,4):signal(k,local(37.3,7.31,z2+1.4),SODIUM,14,.78,tuple(N-Z*.3))
    k.ladder(local(35.55,6.69,84.15),local(35.55,6.69,91.15),.85,'steel')
    blk(k,35.65,6.18,91.15,(6.85,2.83,.49),'metal_grey')
    k.railing(local(32.33,7.45,91.43),local(38.98,7.45,91.43),'metal_yellow')
    blk(k,36.4,5.51,92.68,(4.06,2.18,2.67),'metal_green')
    k.pipe(local(35.25,3.16,92.07),local(35.25,6.04,92.07),.73,'hull_dark',14)
    signal(k,local(37.44,6.68,93.27),SODIUM,15,.69,tuple(N-Z*.25))
    # Lower machinery room and pressure accumulator sit to the east, below the descending track.
    k.part()
    for z,mat,dx,dy,h in [(-6.95,'conc_dark',10.8,9.2,2.),(-3.15,'metal_dark',9.7,8.15,6.1),(.35,'hull_grey',10.4,8.85,1.3)]:
        blk(k,46.7,1.9,z,(dx,dy,h),mat)
    for uu in (43.9,46.5,49.2):
        blk(k,uu,-2.24,-3.35,(2.01,.19,3.05),'metal_green')
        blk(k,uu,-2.36,-2.56,(1.22,.13,.65),'glass_warm')
    for vv in (.35,3.55):
        k.cyl(local(46.6,vv,1.9),1.27,2.72,'hull_grey',12)
        k.pipe(local(46.63,vv,3.20),local(46.63,vv,4.66),.46,'steel_rust',8)
    for vv in (-1.35,4.25):
        k.tube([local(42.0,vv,-4),local(40.25,vv,-4),local(40.25,vv,4.4),local(39.0,vv,4.4)],.37,'steel_rust',8)
    # Operator's cabin views the inverted cars through a hooded corner window.
    k.part()
    blk(k,40.75,5.35,68.95,(4.05,4.22,4.5),'metal_green')
    blk(k,40.77,5.31,71.36,(4.83,4.62,.37),'hull_white')
    blk(k,42.81,5.36,69.72,(.16,3.26,1.03),'glass_warm')
    blk(k,41.12,3.22,69.72,(2.98,.16,1.03),'glass')
    k.beam(local(38.9,3.3,64.55),local(42.32,3.52,66.71),.62,.76,'steel_dark')
    k.beam(local(38.9,6.0,64.55),local(42.32,6.96,66.71),.62,.76,'steel_dark')
    signal(k,local(42.99,5.49,68.95),SODIUM,15,.83,tuple(F-Z*.28))
    signal(k,local(38.9,4.28,94.5),RED,24,.90,tuple(F),'beacon')
    signal(k,local(33.3,-4.36,84.2),COLD,20,.70,tuple(-N-Z))
    # Low bearing blocks follow the two 20 m transition curves on the shard.
    for vv in (LANE,-LANE):
        for ang in (.18,.49,.76,1.03):
            u=6+20*math.sin(ang);z=12+RAILHEAD-20*math.cos(ang)
            base=local(u,vv,-8)
            terrain=G.z(base.x,base.y)
            if terrain<-9000:continue
            k.part()
            target=local(u,vv,z)+F*(math.sin(ang)*1.5)-Z*(math.cos(ang)*1.5)
            depth=target.z-terrain
            if depth<.4:continue
            k.box(V((target.x,target.y,terrain+.10)),(2.15,3.12,.69),'conc_dark',AZ)
            k.beam(V((target.x,target.y,terrain+.29)),target,1.38,1.66,'conc_warm')
    for u,v,z in [(43.7,-2.58,-1.),(49.1,-1.99,-1.4),(36.9,5.4,6.4),(32.95,-5.87,13.2),(38.13,-5.13,30.8),
                  (37.65,-4.67,43.9),(35.03,-4.48,60.),(32.67,-3.35,71.),(35.24,3.68,88.8)]:
        signal(k,local(u,v,z),COLD if v<0 else SODIUM,16,.66,tuple(-N-Z*.18))

def anchors(k):
    # Offset chain windlasses allow personnel to reach the underside of each pin.
    for i,(cx,cy) in enumerate(ANCHORS):
        z=G.z(cx,cy)
        if z<-9000:raise ValueError('Tether footing outside rock')
        d=V((-78-cx,12-cy,0)).normalized();v=Z.cross(d);az=math.degrees(math.atan2(d.y,d.x))
        def pp(u,s,h):return V((cx,cy,z))+d*u+v*s+Z*h
        def corners(u,h,x,y):return [pp(u+a*x/2,b*y/2,h) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        k.part()
        k.loft([corners(-.55,-.93,11.3,9.1),corners(-.55,.86,11.3,9.1),
                corners(-.33,2.25,7.9,6.45)],'conc_warm')
        k.box(pp(-.3,0,2.31),(7.55,5.95,.40),'steel_dark',az)
        for side in (-1,1):
            k.box(pp(0,side*1.38,3.35),(3.68,.59,2.23),'hull_rust',az)
            for x in (-1.61,1.58):k.cyl(pp(x,side*2.4,2.62),.32,.38,'steel',6)
        k.pipe(pp(0,-1.9,4.07),pp(0,1.9,4.07),.65,'steel',14)
        k.torus(pp(0,0,4.08),1.18,.24,'steel_dark',20,6,v)
        wh=pp(-3.28,0,3.33);k.pipe(wh-v*2.0,wh+v*2.0,.91,'hull_grey',12)
        for vv in (-1.88,1.88):k.pipe(wh+v*(vv-.13),wh+v*(vv+.13),1.08,'steel_dark',12)
        k.marker('anchor_'+chr(97+i),pp(0,0,4.56),tuple(d),tuple(Z))
        signal(k,pp(-2.58,-2.74,3.01),SODIUM,14,.59,tuple(-v))
        k.lamp(pp(-3.15,2.38,2.33),2.65,'beacon',RED,15,.53)
        k.collider((8.25,6.68,2.2),pp(-.32,0,1.05),az,'mooring_anchor')

def build(out,log):
    k=Kit('rail',157)
    q=make_survey()
    records=[dict(p=three(f['p']),up=three(f['up']),tangent=three(f['t']),kind=f['kind'],s=f['s']) for f in q.points]
    k.path('rail',records);k.data['railMarks']=q.marks
    for name in ('load','signal','runup','release','crest'):
        idx=min(range(len(q.points)),key=lambda i:abs(q.points[i]['s']-q.marks[name]))
        pt=q.points[idx]
        k.marker({'load':'rail_load','signal':'rail_signal','runup':'rail_runup','release':'whip_release','crest':'whip_crest'}[name],
                 pt['p'],pt['t'],pt['up'])
    k.marker('freighter_berth',(228,-92,150),tuple(F))
    k.data['release']={'p':k.data['markers']['whip_release']['p'],'tangent':k.data['markers']['whip_release']['axis']}
    rail_geometry(k,q);frame_tower(k);anchors(k);k.finalize(out,log)
