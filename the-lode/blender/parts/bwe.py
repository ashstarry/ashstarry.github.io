"""BWE-14. Three twin crawlers carry a luffing, fourteen-cell overburden wheel.

All centreline samples are top contact points in the authored rest pose. Only the
short boom-load belt and its guards need to follow the boom in the simulation.
"""
import math

from mathutils import Matrix, Vector

from lib.ground import G
from lib.kit import Kit
from lib.layout import BWE_POS, three


UP = Vector((0, 0, 1))
AZ = 52.4
A = math.radians(AZ)
FORE = Vector((math.cos(A), math.sin(A), 0))
PORT = UP.cross(FORE)
PITCH = math.radians(14)
ARM = FORE * math.cos(PITCH) - UP * math.sin(PITCH)
ARM_UP = ARM.cross(PORT)
TEAL = (.62, .84, .91)
SODIUM = (1, .47, .17)
RED = (1, .075, .035)


def box_between(K, a, b, width, height, mat, tag=None, mu=.75, speed=0):
    """Oriented box with local X along the conveyor. Supports/guards share its basis."""
    a, b = Vector(a), Vector(b)
    direction = (b-a).normalized()
    side = UP.cross(direction).normalized()
    normal = direction.cross(side)
    rotation = Matrix((direction, side, normal)).transposed().to_euler('XYZ')
    rot = tuple(math.degrees(t) for t in rotation)
    center = (a+b)*.5
    size = ((b-a).length, width, height)
    K.box(center, size, mat, rot)
    if tag:
        K.collider(size, center, rot=rot, tag=tag, friction=mu)
        item = K.data['colliders'][-1]
        if speed:
            item['surfaceVelocity'] = three(direction * speed)
    return direction, side, normal


def panel(K, points, mat, thickness=.16):
    """Closed plate. Its interior is visible on open hoppers, scoops and guides."""
    pts = [Vector(p) for p in points]
    n = (pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized() * (thickness*.5)
    K.loft([[p-n for p in pts], [p+n for p in pts]], mat)


def cheek(K, frame, profile, lo, hi, mat):
    """Extrude an X/Z profile between two lateral offsets (profile has CCW winding)."""
    left = [frame(x, lo, z) for x, z in profile]
    right = [frame(x, hi, z) for x, z in profile]
    K.face(left, mat)
    K.face(list(reversed(right)), mat)
    for i in range(len(left)):
        j = (i+1) % len(left)
        K.face([left[j], left[i], right[i], right[j]], mat)


def oriented_frame(origin, forward):
    forward = Vector(forward).normalized()
    side = UP.cross(forward).normalized()
    origin = Vector(origin)

    def point(x, y, z):
        return origin + forward*x + side*y + UP*z
    return point


def roof_hatch(K, frame, x, y, z, yaw, width, depth, mat):
    p = frame(x,y,z)
    K.box(p, (width,depth,.26), 'steel_dark', yaw)
    K.box(p+UP*.19, (width-.25,depth-.25,.20), mat, yaw)
    for t in (-width*.30, width*.30):
        K.pipe(frame(x+t,y-.20,z+.31), frame(x+t,y+.20,z+.31), .095, 'steel', 6)


def crawler(K, center, yaw, length=12.6, width=2.45, height=3.65):
    """Continuous ring with separate grouser shoes, geared idlers and bogie arms."""
    K.part()
    a = math.radians(yaw)
    u = Vector((math.cos(a),math.sin(a),0))
    v = UP.cross(u)
    F = oriented_frame(center, u)
    radius = height*.48
    offset = length*.5-radius
    profile = []
    # One path goes right along the bottom, up at the nose and back along the top.
    for c, begin in ((offset,-math.pi/2),(-offset,math.pi/2)):
        for j in range(7):
            t = begin+j*math.pi/6
            profile.append((c+radius*math.cos(t), radius+.10+radius*math.sin(t),
                            math.cos(t), math.sin(t)))
    outer = [[F(s,side*width/2,z) for s,z,_,_ in profile] for side in (-1,1)]
    inner = [[F(s-.27*nx,side*width/2,z-.27*nz) for s,z,nx,nz in profile] for side in (-1,1)]
    for i in range(len(profile)):
        j = (i+1)%len(profile)
        K.face((outer[0][i],outer[1][i],outer[1][j],outer[0][j]),'rubber')
        K.face((inner[0][j],inner[1][j],inner[1][i],inner[0][i]),'rubber')
        for k in (0,1):
            q = [outer[k][i],outer[k][j],inner[k][j],inner[k][i]]
            K.face(q if k==0 else list(reversed(q)), 'steel_dark')
    # Link pitch follows the actual perimeter, including both rounded ends.
    straight = offset*2
    arc = math.pi*radius
    perim = 2*(straight+arc)
    count = round(perim/.87)
    for i in range(count):
        s0 = (i+.24)*perim/count
        if s0<straight:
            x,z,ang = -offset+s0,.12,0.
        elif s0<straight+arc:
            ang = (s0-straight)/radius
            x,z = offset+math.sin(ang)*radius,radius+.12-math.cos(ang)*radius
        elif s0<2*straight+arc:
            ang = math.pi
            x,z = offset-(s0-straight-arc),height*.96+.12
        else:
            ang = math.pi+(s0-2*straight-arc)/radius
            x,z = -offset+math.sin(ang)*radius,radius+.12-math.cos(ang)*radius
        outward = u*math.sin(ang)-UP*math.cos(ang)
        K.box(F(x,0,z)+outward*.06,(perim/count*.72,width+.14,.15),
              'steel_rust' if i%9==1 else 'steel_dark',(0,-math.degrees(ang),yaw))
    # Armoured gear case, with a visible line of separate, inset rollers.
    cheek(K,F,[(-offset-1,.95),(-offset-.4,.57),(offset,.62),(offset+1.1,1.6),
               (offset-.65,height-.37),(-offset+.5,height-.4),(-offset-1,2.4)],
          -width*.40,width*.40,'metal_dark')
    for i in range(5):
        x = (i-2)*offset*.48
        z = radius if i in (0,4) else radius*.82
        rr = radius*(.78 if i in (0,4) else .64)
        K.pipe(F(x,-width*.44,z),F(x,width*.44,z),rr,'metal_grey',10)
        for side in (-1,1):
            y1 = side*width*.44
            K.pipe(F(x,y1,z), F(x,y1+side*.16,z), rr*.42,'steel_rust',8)
            if i%2==0:
                K.beam(F(x,y1+side*.19,z),F(x+.62,y1+side*.19,z+rr*.88),
                       .25,.30,'metal_dark')
    K.beam(F(-offset*.94,0,height+.15),F(offset*.94,0,height+.15),width*.64,.59,'metal_dark')


def belt(K, start, end, width, owner, tag, path_name, speed, segments=9):
    """Surface position and its orientation are shared by the mesh and the particle model."""
    a,b = Vector(start),Vector(end)
    d = (b-a).normalized()
    side = UP.cross(d).normalized()
    normal = d.cross(side)
    K.path(path_name,[dict(p=three(a.lerp(b,i/segments)),up=three(normal),obj=owner)
                      for i in range(segments+1)])
    for i in range(segments):
        p = a.lerp(b,i/segments)
        q = a.lerp(b,(i+1)/segments)
        box_between(K,p-normal*.175-d*.018,q-normal*.175+d*.018,
                    width,.35,'rubber',tag+'_belt',1.1,speed)
        for sign in (-1,1):
            v = side*sign*(width*.5+.08)+normal*.43
            box_between(K,p+v-d*.01,q+v+d*.01,.24,.99,'metal_grey',tag+'_guard')
        # Idler bracket and a visible return belt below. No periodic lamps on this run.
        K.pipe(p-side*(width*.5+.29)-normal*.40,p+side*(width*.5+.29)-normal*.40,.28,'steel_dark',10)
        for sign in (-1,1):
            K.beam(p+side*(sign*width*.53)-normal*.44,
                   p+side*(sign*width*.34)-normal*1.26,.22,'metal_grey')
    K.beam(a-normal*1.32,b-normal*1.32,width*.88,.16,'rubber')
    for p in (a,b):
        K.pipe(p-side*(width*.5+.45)-normal*.56,p+side*(width*.5+.45)-normal*.56,.67,'metal_dark',12)
        K.pipe(p+side*(width*.5+.37)-normal*.56,p+side*(width*.5+1.)-normal*.56,.34,'steel',10)


def chute(K, upper, lower, mat='metal_yellow', rim=True, tag=None):
    """A hollow transition box. No cap is placed across the throat."""
    for i in range(len(upper)):
        j=(i+1)%len(upper)
        panel(K,[upper[i],lower[i],lower[j],upper[j]],mat,.24)
        if rim:
            K.beam(upper[i],upper[j],.28,.38,'steel_dark')
        K.beam(lower[i],upper[i],.30,'steel_rust')
        if tag:
            # A sloped OBB keeps the longitudinal opening clear right down to the throat.
            along = (upper[j]-upper[i]).normalized()
            drop = (lower[i]+lower[j]-upper[i]-upper[j])*.5
            across = (drop-along*drop.dot(along)).normalized()
            normal = along.cross(across)
            rotation = Matrix((along,across,normal)).transposed().to_euler('XYZ')
            extent = max((upper[j]-upper[i]).length,(lower[j]-lower[i]).length)
            centre = (upper[i]+upper[j]+lower[i]+lower[j])*.25
            K.collider((extent,abs(across.dot(drop)),.24),centre,
                       rot=tuple(math.degrees(t) for t in rotation),tag=tag,friction=.42)


def ring(K, center, rad_in, rad_out, left, right, mat, segments=42):
    def P(radius,lateral,i):
        theta=math.tau*i/segments
        return center + (FORE*math.cos(theta)+UP*math.sin(theta))*radius + lateral*PORT
    for i in range(segments):
        j=(i+1)%segments
        inside0,inside1=P(rad_in,left,i),P(rad_in,right,i)
        out0,out1=P(rad_out,left,i),P(rad_out,right,i)
        p0,p1=P(rad_in,left,j),P(rad_in,right,j)
        q0,q1=P(rad_out,left,j),P(rad_out,right,j)
        K.face((out0,out1,q1,q0),mat)
        K.face((p0,p1,inside1,inside0),mat)
        K.face((inside0,out0,q0,p0),mat)
        K.face((inside1,p1,q1,out1),mat)


def wheel(K, center):
    # theta increases from the face toward the zenith. Positive rotation axis = -PORT.
    K.marker('bwe_wheel_axis',center,axis=-PORT)
    K.pipe(center-PORT*2.55,center+PORT*3.45,2.38,'metal_dark',20)
    for side in (-1,1):
        y=side*1.62
        K.part()
        K.pipe(center+PORT*(y-.2),center+PORT*(y+.2),2.6,'metal_orange',20)
        ring(K,center,7.12,8.03,y-.27,y+.27,'metal_yellow')
        ring(K,center,7.12,7.34,y-.39,y+.39,'steel_dark')
        for i in range(7):
            theta=math.tau*(i+.21*side)/7
            radial=FORE*math.cos(theta)+UP*math.sin(theta)
            tangent=-FORE*math.sin(theta)+UP*math.cos(theta)
            p=center+PORT*y
            # Tapered web/flange spokes and a diagonal between the two rims.
            panel(K,(p+radial*1.34-tangent*.58,p+radial*7.45-tangent*.44,
                     p+radial*7.53+tangent*.28,p+radial*1.69+tangent*1.18),'metal_orange',.28)
            K.beam(p+radial*1.9,p+radial*7.42,.38,.40,'steel_rust')
            K.beam(p+radial*4.1,p+radial*7.35-PORT*(y*2)+tangent*.57,.26,'steel_dark')
    for i in range(14):
        theta=math.tau*(i+.125)/14
        radial=FORE*math.cos(theta)+UP*math.sin(theta)
        tangent=-FORE*math.sin(theta)+UP*math.cos(theta)

        def point(t,y,r):
            return center+tangent*t+PORT*y+radial*r

        # Rolled bucket back, floor and tapered cheeks. Leave the two front lips open.
        cross=[(1.88,10.55),(.18,10.36),(-1.41,9.65),(-1.73,8.66),
               (-1.14,7.92),(-.24,7.86),(1.47,8.58)]
        w=3.65
        K.part(i/14)
        for j in range(len(cross)-1):
            t0,r0=cross[j];t1,r1=cross[j+1]
            panel(K,(point(t0,-w/2,r0),point(t1,-w/2,r1),
                     point(t1,w/2,r1),point(t0,w/2,r0)),
                  'steel_rust' if j in (1,2,3) else 'steel_dark',.15)
        for sign in (-1,1):
            y=sign*w/2
            pts=[point(t,y,r) for t,r in cross]
            panel(K,pts,'metal_orange' if i in (2,9,12) else 'steel_rust',.17)
            K.beam(point(-1.43,y+sign*.14,8.8),point(.26,y+sign*.14,9.64),.19,'steel')
            K.pipe(point(-.82,y,8.25),point(-.82,y+sign*.27,8.25),.28,'metal_dark',8)
        K.beam(point(1.84,-w*.52,10.55),point(1.84,w*.52,10.55),.34,.32,'steel')
        K.beam(point(1.47,-w*.51,8.56),point(1.47,w*.51,8.56),.22,.22,'steel_dark')
        for j in (-1.27,-.42,.42,1.27):
            # Each forged tooth narrows in both lateral width and height at the tip.
            heel=[point(1.62,j-.22,10.37),point(1.62,j+.22,10.37),
                  point(1.62,j+.22,10.67),point(1.62,j-.22,10.67)]
            tip=[point(2.40,j-.16,10.70),point(2.40,j+.16,10.70),
                 point(2.40,j+.12,10.77),point(2.40,j-.12,10.77)]
            # In the basis {tangent,PORT,radial}, PORT × radial points against tangent.
            K.loft([list(reversed(heel)),list(reversed(tip))],'steel')
    # Axle end and inspection cover are distinct from the stationary drive gearbox.
    K.pipe(center-PORT*2.3,center-PORT*2.8,1.63,'metal_grey',18)
    for i in range(8):
        th=math.tau*i/8
        p=center+(FORE*math.cos(th)+UP*math.sin(th))*1.27
        K.pipe(p-PORT*2.81,p-PORT*2.98,.16,'steel',6)


def build(out,log):
    K=Kit('bwe',73)
    bx,by=BWE_POS
    zground=G.z(bx,by)
    base=Vector((bx,by,0))
    # The six tracked pontoons are independent undercarriages below a stationary ring.
    F=oriented_frame(base,FORE)
    for group,(s,t,yaw) in enumerate([(-10.1,.25,AZ-9),(6.6,-7.1,AZ+6),(7.5,6.8,AZ-3)]):
        station=F(s,t,zground)
        bot=oriented_frame(station,(math.cos(math.radians(yaw)),math.sin(math.radians(yaw)),0))
        for sign in (-1,1):
            crawler(K,bot(0,sign*1.74,0),yaw,length=13.2 if group==0 else 12.2)
        K.part()
        K.box(bot(.2,0,4.0),(5.66,6.02,1.25),'metal_dark',yaw)
        K.cyl(bot(0,0,4.99),2.05,1.06,'steel_rust',14)
        K.beam(bot(-2.26,-2.9,5.07),bot(-2.26,2.9,5.07),.54,.62,'metal_grey')
        K.beam(bot(0,0,5.32),F(0,0,zground+6.22),3.2,2.0,'metal_dark')
        for side in (-1,1):
            p=bot(-.5,side*3.24,3.7)
            K.light(p,TEAL,8.,.44,'lamp')
    for z,r,h,m in [(zground+5.79,8.0,1.7,'steel_dark'),(zground+6.91,9.1,.96,'metal_dark'),
                      (zground+7.58,9.64,.48,'steel'),(zground+7.94,8.9,.42,'steel_rust')]:
        K.cyl((bx,by,z),r,h,m,36)
    K.torus((bx,by,zground+7.3),9.15,.22,'steel_rust',36)
    # Round crosswalk with two discontinuities for the transfer and stair landings.
    for start,end in [(15,119),(154,238),(266,334)]:
        steps=math.ceil((end-start)/16)
        old=None
        for i in range(steps+1):
            t=math.radians(start+(end-start)*i/steps)
            p=base+Vector((math.cos(t)*9.7,math.sin(t)*9.7,zground+7.53))
            if old is not None:
                K.beam(old,p,1.48,.22,'steel_dark')
                q0=old+Vector((old.x-bx,old.y-by,0)).normalized()*.61
                q1=p+Vector((p.x-bx,p.y-by,0)).normalized()*.61
                K.railing(q0,q1)
            old=p
    # No stairs or footings in the west haul lane.
    K.stairs(F(-9.4,-6.5,zground+.24),F(-1.0,-9.05,zground+7.53),1.72)
    K.lamp(F(4,-9.8,zground+7.6),2.7,col=SODIUM,r=13,power=.86)
    K.marker('bwe_slew_axis',(bx,by,zground+8.27),axis=UP)

    # Six metres of forward offset aligns the wheel with the carved working face.
    pivot=F(6,0,16.0)
    def arm(s,t,h=0):
        return pivot+ARM*s+PORT*t+ARM_UP*h
    hub=arm(56,0)
    arm_start=arm(51.8,3.16,2.8)
    arm_end=arm(-4.65,3.16,2.8)
    dstart=Vector((-193.95,3.2,14.7))
    dend=Vector((-186,-50,19.))
    with K.into('bwe_super',loc=(bx,by,zground+8.27)):
        def rect(cx,cy,z,dx,dy):
            return [F(cx+u*dx/2,cy+v*dy/2,z) for u,v in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        K.part()
        K.loft([rect(-.6,0,zground+8.12,21,14),
                rect(-.6,0,zground+10.16,24,16.7)],'metal_grey')
        K.box(F(-.6,-6.45,zground+10.53),(22.4,1.58,.80),'metal_orange',AZ)
        K.box(F(-.2,6.2,zground+10.54),(22.3,2.1,.73),'metal_grey',AZ)
        K.catwalk(F(-11.3,-8.65,zground+10.91),F(10.4,-8.65,zground+10.91),1.85)
        K.catwalk(F(-11.1,8.27,zground+10.91),F(6.62,8.27,zground+10.91),1.68)
        # Boom hinge saddles have their own pin and elastic service hoses.
        for sign in (-1,1):
            p=F(6,sign*2.92,16)
            K.box(p-UP*.94,(4.3,.89,2.1),'metal_grey',AZ)
            K.pipe(p-PORT*.70,p+PORT*.70,1.38,'metal_orange',16)
        K.pipe(F(6,-3.72,16),F(6,3.72,16),.88,'steel',16)
        # The main electro-mechanical house is deliberately offset; the central chute stays clear.
        cheek(K,F,[(-12.7,13),(-3.6,13),(-2.9,14.1),(-2.9,19.8),(-4.2,21.2),
                   (-11.3,21.2),(-12.7,19.55)],-7.3,-2.3,'metal_green')
        K.box(F(-7.68,-4.89,21.39),(8.87,5.34,.56),'hull_grey',AZ)
        K.box(F(-7.58,-7.39,16.3),(5.32,.26,2.54),'metal_dark',AZ)
        for s in [-9.75,-8.70,-7.65,-6.60,-5.55]:
            K.box(F(s,-7.59,16.36),(.39,.34,2.22),'metal_grey',(0,12,AZ))
        roof_hatch(K,F,-8.2,-5.6,21.84,AZ,4.1,2.35,'metal_green')
        K.pipe(F(-10.7,-3.1,20.8),F(-10.7,-3.1,24.1),.47,'steel_rust',10)
        K.pipe(F(-10.7,-3.1,24.1),F(-11.58,-3.1,24.25),.44,'metal_dark',10)
        K.tube([F(-11.9,-7.68,14.4),F(-9.7,-7.68,14.4),F(-8.8,-7.68,13.5),
                F(-3.75,-7.68,13.5),F(-1.7,-6.45,13.5)],.23,'steel_rust')
        # Ballast tray on two independent trusses. Concrete cases have gaps and lifting lugs.
        for sign in (-1,1):
            K.truss(F(-2.8,sign*4.85,17.35),F(-21.2,sign*4.85,24.2),
                    2.07,2.6,'steel_dark',5,.47)
            K.beam(F(-11.1,sign*5.1,13.35),F(-21.4,sign*4.85,24.35),.78,'metal_grey')
        K.box(F(-20.0,0,24.53),(5.8,13.8,1.55),'metal_orange',AZ)
        for j in range(5):
            t=(j-2)*2.46
            K.part()
            K.box(F(-20.25,t,26.37),(4.98,2.23,2.25),'conc_warm',AZ)
            K.box(F(-20.25,t,28.52),(4.68,2.13,1.77),'conc' if j in (0,2,3) else 'conc_dark',AZ)
            K.pipe(F(-20.6,t,29.46),F(-20.03,t,29.46),.18,'steel_rust',8)
        for t in (-6.25,6.25):
            K.beam(F(-22.3,t,23.8),F(-22.3,t,29.56),.47,'steel_rust')
            K.beam(F(-22.5,t,28.8),F(-17.6,t,28.8),.42,'steel_dark')
        # Walking portal with a paired A-frame head. Forward legs leave sight of the ribbon.
        masthead=F(-3.5,0,42.0)
        for sign in (-1,1):
            K.truss(F(-11.9,sign*6.55,14.1),F(-3.5,sign*2.8,41.5),2.15,2.12,'metal_grey',6,.43)
            K.truss(F(4.2,sign*5.95,14.4),F(-3.3,sign*2.8,41.3),1.58,2.21,'metal_yellow',6,.38)
            K.beam(F(-7.5,sign*4.2,28.4),F(.52,sign*4.38,27.7),.45,'steel_rust')
            K.cable(F(-3.5,sign*2.85,41.8),F(-20.35,sign*4.83,28.9),.31,.16,'steel_dark',9)
            K.cable(F(-3.1,sign*2.76,41.55),arm(37.6,3.16+sign*2.52,2.32),.34,.19,'steel',11)
            K.cable(F(-3.2,sign*2.63,41.4),arm(49.7,3.16+sign*1.79,2.03),.54,.135,'steel_dark',12)
        K.beam(F(-3.5,-3.88,41.6),F(-3.5,3.88,41.6),2.10,1.18,'metal_orange')
        K.catwalk(F(-3.55,-4.2,42.42),F(-3.55,4.2,42.42),1.48)
        for t in (-3.1,-2.47,2.47,3.1):
            K.pipe(F(-3.45,t-.23,41.95),F(-3.45,t+.23,41.95),1.30,'metal_dark',16)
            K.pipe(F(-3.45,t-.25,41.95),F(-3.45,t+.25,41.95),.47,'steel_rust',12)
        K.marker('bwe_search',masthead+UP*1.65)
        K.lamp(F(-3.7,-3.1,42.35),1.95,'beacon',RED,23,.87)
        K.lamp(F(-3.6,2.84,42.17),1.46,col=TEAL,r=26,power=.85)
        # Operator's pulpit is isolated from the slewing deck on a short lattice arm.
        K.truss(F(1.2,-4.8,17.9),F(4.1,-11.15,19.52),1.78,1.91,'steel_rust',3,.29)
        K.beam(F(0,-6.8,13.65),F(4.31,-10.4,19.18),.52,'metal_dark')
        K.catwalk(F(.66,-4.55,20.0),F(4.2,-10.1,20.16),1.45)
        cheek(K,F,[(2.2,19.2),(7.8,19.2),(8.4,20.0),(8.45,22.26),(7.3,23.55),(2.2,23.55)],
              -12.94,-9.30,'hull_white')
        K.box(F(5.05,-11.15,23.65),(5.93,4.12,.55),'metal_dark',AZ)
        for s,w in [(3.1,1.07),(4.57,1.4),(6.37,1.54)]:
            K.part(K.rng.random())
            K.box(F(s,-13.02,21.93),(w,.19,1.87),'glass_warm',AZ)
            K.box(F(s,-13.135,21.40),(w*.79,.052,.22),'emit_warm',AZ)
        K.box(F(8.26,-11.17,21.88),(.24,2.9,1.51),'glass_warm',AZ)
        K.light(F(6.5,-13.12,21.3),(1,.60,.29),13,.61,'window')
        K.lamp(F(5.82,-13.86,19.75),2.3,col=TEAL,r=20,power=1.06)
        K.lamp(F(-11.3,-8.55,13.5),3.1,col=SODIUM,r=17,power=.78)
        # Main winch drum and flange difference make the rope path legible at close range.
        K.pipe(F(-7.2,1.4,18.25),F(-7.2,5.95,18.25),1.63,'steel_dark',18)
        for t in (1.45,3.14,5.82):
            K.pipe(F(-7.2,t-.15,18.25),F(-7.2,t+.15,18.25),1.89,'metal_orange',16)
        for t in (1.2,3.1,5.65):
            K.cable(F(-7.1,t,19.8),F(-3.53,2.5+.09*t,41.2),.20,.11,'steel',8)
        K.beam(F(-10.1,.35,15.9),F(-4.4,.35,15.9),1.38,'metal_grey')
        K.box(F(-7.17,3.5,16.08),(4.92,6.76,1.25),'metal_grey',AZ)
        K.box(F(-6.95,6.47,18.25),(3.25,1.28,2.01),'metal_green',AZ)

        for s,t,z,h in [(7.5,-6.5,13.58,2.1),(-7.7,7.8,13.68,1.9),(-16.1,-4.2,23.0,1.2),
                        (-20.2,6.1,28.92,1.1),(-.8,4.8,26.5,1.05)]:
            K.lamp(F(s,t,z),h,col=SODIUM if s<0 else TEAL,r=10.8,power=.47)
        with K.into('bwe_boom',parent='bwe_super',loc=pivot):
            K.marker('bwe_boom_axis',pivot,-PORT)
            # Two lower chords and an overhead offset lattice; the carrying belt runs in the trough.
            for sign in (-1,1):
                K.truss(arm(-2.7,3.16+sign*2.62,-.8),arm(51.9,3.16+sign*2.25,-.65),
                        .95,2.90,'metal_yellow' if sign<0 else 'metal_grey',11,.34)
                K.beam(arm(-2.15,3.16+sign*2.91,1.16),arm(50.7,3.16+sign*2.48,1.02),
                       .29,.47,'steel_rust')
            for s in (-1.3,3.8,11.9,18.4,26.3,33.24,41.0,49.2):
                K.beam(arm(s,.57,-1.62),arm(s,5.71,-1.62),.55,.62,'metal_grey')
                K.beam(arm(s,.81,-1.2),arm(s+3.,5.28,-1.23),.29,'steel_dark')
            belt(K,arm_start,arm_end,3.36,'bwe_boom','bwe_arm','bwe_belt',4.2)
            K.marker('bwe_belt_start',arm_start,-ARM,ARM_UP)
            K.marker('bwe_belt_end',arm_end,-ARM,ARM_UP)
            K.marker('bwe_drop',arm_start+ARM_UP*1.7,-ARM,ARM_UP)
            K.catwalk(arm(-2.3,6.77,.70),arm(49.1,6.77,.70),1.6)
            K.tube([arm(-1.2,7.17,.16),arm(24.1,7.17,.16),arm(25.,7.45,.34),
                    arm(46.3,7.45,.34)],.29,'steel_rust')
            K.lamp(arm(4.8,6.75,.8),2.23,col=SODIUM,r=15,power=.66)
            K.lamp(arm(25.6,6.85,.8),1.92,col=TEAL,r=14,power=.64)
            K.lamp(arm(46.7,6.81,.8),2.48,col=SODIUM,r=19,power=.8)
            # Discharge channel captures the top of each bucket and crosses behind the wheel.
            wrim=[arm(48.1,.69,4.45),arm(54.80,.69,4.45),
                  arm(54.80,4.94,4.45),arm(48.1,4.94,4.45)]
            low=[arm(49.0,2.26,3.08),arm(52.0,2.26,3.08),
                 arm(52.0,4.06,3.08),arm(49.0,4.06,3.08)]
            chute(K,wrim,low,'metal_orange',tag='bwe_collector_wall')
            # The leading rim of the stationary receiving spoon sits behind the wheel
            # just below its upper arc. Ore tips from the crown into this lined trough.
            pour_upper = [hub+FORE*x+PORT*y+UP*z for x,y,z in
                          [(-4.7,.25,9.2),(-1.75,.25,9.8),(-1.75,1.62,9.6),(-4.7,1.62,9.0)]]
            pour_lower = [arm(50.7,2.2,4.32),arm(53.05,2.2,4.32),
                          arm(53.05,2.95,4.32),arm(50.7,2.95,4.32)]
            # A three-sided open slide sends the material across the wheel's front plane.
            for j in (0,1,3):
                k=(j+1)%4
                panel(K,[pour_upper[j],pour_lower[j],pour_lower[k],pour_upper[k]],'steel_dark',.2)
            K.beam(pour_upper[0],pour_upper[1],.34,.31,'steel')
            K.beam(arm(48.25,5.02,3.15),pour_upper[3],.36,.54,'metal_grey')
            K.marker('bwe_bucket_tip', (pour_upper[0]+pour_upper[1])*.5,axis=-PORT)
            for j in (0,1):
                K.beam(arm(45.7,2+3*j,-1.35),hub+PORT*(1.8+3*j),1.21,1.39,'metal_grey')
            K.pipe(hub+PORT*1.72,hub+PORT*5.93,1.66,'steel_dark',18)
            K.pipe(hub+PORT*2.39,hub+PORT*2.84,2.77,'metal_yellow',20)
            K.box(hub+PORT*5.46+UP*.54,(4.85,2.39,3.48),'metal_grey',AZ)
            K.pipe(arm(50.65,6.07,.64),arm(54.65,6.07,.64),.79,'metal_green',12)
            K.light(hub-PORT*2.9+UP*2.1,TEAL,21,1.08,'flood')
            with K.into('bwe_wheel',parent='bwe_boom',loc=hub):
                wheel(K,hub)
    # Swing chute feeds a second conveyor. It passes above the access road on its own support.
    uf=FORE;vs=PORT
    chute(K,[arm_end-ARM*.68+uf*s+vs*t-UP*1.12 for s,t in [(-2.15,-2.7),(2.15,-2.7),(2.15,2.7),(-2.15,2.7)]],
          [dstart+uf*s+vs*t+UP*1.07 for s,t in [(-1.1,-1.18),(1.1,-1.18),(1.1,1.18),(-1.1,1.18)]],
          'metal_dark',tag='bwe_transfer_wall')
    discharge_dir=(dend-dstart).normalized()
    ds=UP.cross(discharge_dir).normalized()
    dn=discharge_dir.cross(ds)
    K.truss(dstart-dn*2.48,dend-dn*2.48,4.98,2.46,'metal_grey',10,.41)
    belt(K,dstart,dend,3.18,'static','bwe_discharge','discharge_belt',4.)
    K.marker('discharge_start',dstart,discharge_dir,dn)
    K.marker('discharge_end',dend,discharge_dir,dn)
    K.catwalk(dstart-ds*3.24-dn*.54,dend-ds*3.24-dn*.54,1.48)
    for t in (.08,.32,.68,.93):
        K.lamp(dstart.lerp(dend,t)-ds*3.28-dn*.42,1.76,col=TEAL if t<.5 else SODIUM,r=12,power=.69)
    # Counterbalanced transfer crawler, west of the swept haul-road envelope.
    sx,sy=-194.2,-40.4
    sf=Vector((math.cos(math.radians(-78)),math.sin(math.radians(-78)),0))
    S=oriented_frame(Vector((sx,sy,G.z(sx,sy))),sf)
    for sign in (-1,1):
        crawler(K,S(.2,sign*2.32,0),-78,length=9.58,width=1.72,height=2.57)
    K.cyl(S(0,0,3.12),3.54,1.14,'metal_dark',18)
    K.box(S(-.1,0,4.35),(8.4,6.75,1.38),'metal_orange',-78)
    sp=S(-.56,-1.1,23)
    for sign in (-1,1):
        K.truss(S(-3.15,sign*2.82,4.76),sp+Vector((sign*.9,0,0)),
                1.42,1.27,'metal_grey',4,.31)
        K.beam(S(3.28,sign*2.8,4.76),sp+Vector((sign*.9,0,0)),.57,.68,'metal_yellow')
        K.beam(S(2.21,sign*2.54,4.98),dstart.lerp(dend,.79)+ds*(sign*1.89)-dn*3.65,.64,'metal_grey')
    K.beam(sp+ds*-1.42,sp+ds*1.68,1.04,'metal_dark')
    for t in (.62,.92):
        K.cable(sp,dstart.lerp(dend,t)-dn*2.+ds*1.93,.25,.12,'steel',6)
    K.lamp(S(-2.28,-2.55,4.95),2.10,col=SODIUM,r=15,power=.67)
    K.lamp(sp,.95,'beacon',RED,18,.65)

    # Sling receiving hopper; four walls stay open around the outlet.
    hc=Vector((-186,-50,0))
    def rect_at(c,z,rx,ry):
        return [c+Vector((x*rx,y*ry,z)) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    hopper_top=rect_at(hc,17.6,4.7,4.0)
    hopper_bottom=rect_at(hc,10.75,1.4,1.30)
    chute(K,hopper_top,hopper_bottom,'metal_orange',tag='sling_hopper_wall')
    for i in range(4):
        p=hopper_top[i]
        z=G.z(p.x,p.y)
        q=Vector((p.x,p.y,z+.62))
        K.box(q,(2.05,1.85,1.1),'conc')
        K.beam(q,p,.67,.79,'steel_dark')
        next_p=hopper_top[(i+1)%4]
        if i!=0:
            K.beam(q.lerp(p,.28),next_p-UP*2.31,.38,'steel_rust')
    K.catwalk(hopper_top[0]-UP*.28,hopper_top[3]-UP*.28,1.66)
    K.ladder((hc.x-5.18,hc.y-.01,G.z(hc.x-5.18,hc.y)),(hc.x-5.18,hc.y-.01,17.59),.9,'steel_dark')
    K.marker('sling_hopper',(hc.x,hc.y,17.6))
    K.lamp(hopper_top[0],2.0,col=SODIUM,r=17,power=.9)
    K.lamp(hopper_top[2],1.2,col=TEAL,r=15,power=.6)
    # A pair of flywheels straddles a worn open throwing channel on a cantilever.
    heading=math.radians(8)
    fs=Vector((math.cos(heading),math.sin(heading),0))
    ss=UP.cross(fs)
    elev=math.radians(42)
    guide=fs*math.cos(elev)+UP*math.sin(elev)
    gn=guide.cross(ss)
    mouth=Vector((-167.,-60.,27.))
    breech=mouth-guide*25.6
    def barrel(s,t=0,h=0):return breech+guide*s+ss*t+gn*h
    top=barrel(0,0,.46)
    feed_start=Vector((-186,-49.89,9.4));feed_end=top+UP*.64
    K.truss(feed_start-UP*1.01,feed_end-UP*1.02,2.78,1.42,'steel_dark',4,.25)
    fdir=(feed_end-feed_start).normalized()
    fside=UP.cross(fdir).normalized()
    box_between(K,feed_start,feed_end,2.1,.25,'rubber','sling_feeder_belt',1.1,3.8)
    K.path('sling_feeder',[dict(p=three(p),up=three(fdir.cross(fside)),obj='static')
                           for p in (feed_start,feed_end)])
    for sign in (-1,1):
        K.beam(feed_start+fside*sign*1.11+UP*.21,
               feed_end+fside*sign*1.11+UP*.21,.19,.55,'metal_grey')
    K.marker('sling_breech',breech,guide,gn)
    K.marker('sling_mouth',mouth,guide,gn)
    K.part()
    for sign in (-1,1):
        K.truss(barrel(-.75,sign*2.0,-1.3),barrel(25.6,sign*1.75,-1.1),
                .74,1.98,'metal_yellow' if sign<0 else 'steel_dark',6,.30)
        K.beam(barrel(-1.0,sign*1.63,.63),barrel(25.6,sign*1.63,.45),.39,.95,'metal_grey')
        K.beam(barrel(18.5,sign*1.75,.51),barrel(25.55,sign*1.75,.51),.12,.30,'steel')
    K.beam(barrel(-1.0,0,-.14),mouth-gn*.14,3.08,.31,'steel_dark')
    for s in (1.4,7.2,13.5,20.4,24.9):
        K.beam(barrel(s,-2,-1.64),barrel(s,2,-1.64),.37,.48,'metal_orange')
    for sign in (-1,1):
        p=barrel(3.9,sign*2.05,.35)
        K.pipe(p-ss*.57,p+ss*.57,2.36,'metal_dark',18)
        K.pipe(p-ss*.62,p+ss*.62,1.85,'metal_orange',18)
        K.pipe(p-ss*.70,p+ss*.70,.92,'steel',12)
        K.pipe(barrel(.85,sign*3.0,-.72),barrel(4.6,sign*3.0,-.72),.78,'metal_green',12)
        foot=barrel(2.45,sign*2.04,-.5)
        ground=Vector((foot.x,foot.y,G.z(foot.x,foot.y)))
        K.box(ground+UP*.42,(2.25,2.25,.86),'conc')
        K.beam(ground+UP*.72,foot,.71,'steel_dark')
        foot2=barrel(11.55,sign*2.05,-1.39)
        anchor=ground+fs*6.45
        anchor.z=G.z(anchor.x,anchor.y)
        K.box(anchor+UP*.51,(2.85,2.4,1.1),'conc_dark')
        K.beam(anchor+UP*.7,foot2,.94,'metal_grey')
        K.beam(ground+UP*3.2,foot2,.51,'steel_rust')
        K.beam(anchor+UP*.7,barrel(2.14,sign*2.01,-1.40),.37,'metal_grey')
    K.catwalk(barrel(-.98,-3.15,-1.28),barrel(13.75,-3.15,-1.28),1.36)
    K.lamp(barrel(.75,-3.4,-1.12),1.80,col=SODIUM,r=13,power=.81)
    K.lamp(barrel(12.25,-3.15,-1.18),1.45,col=TEAL,r=13,power=.67)
    K.lamp(barrel(21.15,1.96,-1.03),.95,'beacon',RED,14,.65)
    # Technicians' shelter and low-voltage switch cabinet stay on the hopper side.
    shelter=Vector((-192.3,-52.4,G.z(-192.3,-52.4)))
    K.box(shelter+UP*.40,(5.2,3.5,.8),'conc_dark',-7)
    K.box(shelter+UP*2.19,(4.48,3.16,2.94),'metal_teal',-7)
    K.box(shelter+UP*3.86,(5.13,3.63,.41),'hull_grey',-7)
    K.box(shelter+Vector((.12,-1.56,2.49)),(2.55,.21,.81),'glass_warm',-7)
    K.pipe(shelter+Vector((-2.43,.82,.54)),shelter+Vector((-2.43,.82,4.61)),.24,'steel_rust')
    K.lamp(shelter+Vector((2.57,-1.75,.73)),2.72,col=SODIUM,r=12,power=.73)
    # Local illumination comes from the work faces, service landings and inspection hatches.
    # These low-output sources have no separate visible lamp array across the boom.
    for s,t,z,c,r,power in [
        (-9.4,-6.5,5.0,TEAL,8,.36),(-5.3,6.8,5.2,SODIUM,8,.38),(6.6,-5.7,6.2,TEAL,10,.42),
        (4.5,9.2,4.1,SODIUM,7,.47),(-15.8,1.4,4.5,TEAL,7,.33),(-.6,-9.1,9.9,TEAL,10,.42)]:
        K.light(F(s,t,zground+z),c,r,power)
    with K.into('bwe_super'):
        for s,t,z,c,r,power in [
            (-12.5,-6.5,15.3,SODIUM,9,.40),(-10,-3.8,19.8,TEAL,9,.32),(-5.5,-7.46,17.95,SODIUM,9,.36),
            (-2.5,6.81,18.1,TEAL,11,.4),(-5.1,4.6,20.34,SODIUM,11,.43),(.7,-4.4,20.23,TEAL,10,.36),
            (-17.3,3.5,25.1,TEAL,12,.32),(-18.3,-4.3,26.7,SODIUM,11,.31),(-3.35,-2.45,39.66,TEAL,14,.34),
            (2.,-10.4,19.6,SODIUM,9,.38),(7.75,-12.85,22.43,TEAL,10,.34),(3.25,5.22,15.3,TEAL,12,.48),
            (1.6,-5.43,15.75,SODIUM,10,.39),(-3.3,2.4,27.35,TEAL,11,.32)]:
            K.light(F(s,t,z),c,r,power)
    with K.into('bwe_boom'):
        for s,t,h,c,r in [(1.4,5.27,-.66,TEAL,11),(7.7,.56,1.,SODIUM,9),(17.9,6.1,.1,TEAL,9),
                           (30.9,4.86,-.2,SODIUM,12),(39.7,1.02,1.15,TEAL,12),
                           (47.0,4.8,3.55,SODIUM,13),(53.7,3.5,2.2,TEAL,13)]:
            K.light(arm(s,t,h),c,r,.42)
    for p,c,r in [(dstart+ds*2.1+UP,TEAL,12),(dend-ds*2.15+UP,SODIUM,12),
                  (dstart.lerp(dend,.42)+ds*2.4,TEAL,12),(sp-UP*3.,SODIUM,13),
                  (S(1.2,2.46,5.2),TEAL,10),(hopper_top[3]-UP*2.,TEAL,9),
                  (hopper_bottom[0]-UP*.3,SODIUM,10),(feed_start+UP*1.6,SODIUM,9),
                  (barrel(3.3,-3.3,.85),TEAL,11),(barrel(20.0,1.77,-.68),SODIUM,10),
                  (shelter+Vector((-.8,-1.7,2.63)),SODIUM,8)]:
        K.light(p,c,r,.40)
    K.finalize(out,log)
