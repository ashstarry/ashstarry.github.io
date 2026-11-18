"""Ore preparation on the east apron. Coordinates are Blender metres.

The top skin of each transport collider is the specified running surface.
Every gate and chute remains open at its throat. Carrier speeds are exported
along the local belt tangent in the three.js world frame.
"""
import math

from mathutils import Matrix, Vector

from lib.ground import G
from lib.kit import Kit
from lib.layout import three

Z = Vector((0, 0, 1))
TEAL = (.50, .84, .80)
SODIUM = (1., .48, .17)
WINDOW = (1., .63, .30)
RED = (1., .075, .042)
FADED_BLUE = 'metal_teal'
PLATE = 'hull_rust'
DARK = 'steel_dark'
CV1 = [(48, -8, 5), (64, -22, 11)]
CV2 = [(84, -27, 2), (91.5, -26, 2.3), (96, -15.5, 3.2), (98, -4, 3.7), (98, 4, 4)]
CV3 = [(70, -18, 4), (103, -18, 13), (134, -33, 13), (146, -34, 12)]


def vec(p):
    return Vector(p)


def ground(x, y):
    value = G.z(x, y)
    return value if value > -9000 else None


def rect(x, y, z, width, depth):
    return [vec((x + i*width/2, y + j*depth/2, z))
            for i, j in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]


def rotation(side, along, normal):
    basis = Matrix((side, along, normal)).transposed()
    return tuple(math.degrees(a) for a in basis.to_euler())


def belt_frame(p, q):
    along = (vec(q) - vec(p)).normalized()
    side = vec((along.y, -along.x, 0)).normalized()
    return side, along, side.cross(along).normalized()


def slab(k, points, normal, thickness, face_mat, back_mat):
    """A thick tapered sheet, with a correctly wound industrial liner."""
    points = [vec(p) for p in points]
    normal = vec(normal).normalized()
    if (points[1]-points[0]).cross(points[2]-points[0]).dot(normal) < 0:
        points.reverse()
    back = [p-normal*thickness for p in points]
    k.face(points, face_mat)
    k.face(list(reversed(back)), back_mat)
    for i in range(len(points)):
        j = (i+1) % len(points)
        k.face([points[i], back[i], back[j], points[j]], back_mat)


def lamp_head(k, p, target, color=TEAL, radius=15, power=.77, kind='flood'):
    p = vec(p)
    aim = (vec(target)-p).normalized()
    side = aim.cross(Z)
    if side.length_squared < .02:
        side = vec((1, 0, 0))
    side.normalize()
    along = aim.cross(side).normalized()
    rot = rotation(side, along, aim)
    k.part()
    k.box(p, (1.08, .60, .46), 'metal_dark', rot)
    k.box(p+aim*.26, (.85, .43, .10),
          'emit_red' if color == RED else 'emit_cool' if color == TEAL else 'emit_sodium', rot)
    k.light(p+aim*.4, color, radius, power, kind)


def pedestal(k, p, size, stem, mat='conc'):
    x, y, z = p
    k.part()
    k.box((x, y, z+.24), (size[0], size[1], .48), 'conc_dark')
    k.box((x, y, z+.48+stem/2), (size[0]-.42, size[1]-.42, stem), mat)
    k.box((x, y, z+.55+stem), (size[0]-.63, size[1]-.63, .13), DARK)


def valve(k, p, axis, radius=.52):
    p = vec(p)
    axis = vec(axis).normalized()
    end = p+axis*(radius+.34)
    k.pipe(p, end, max(.09, radius*.20), 'steel', 8)
    k.torus(end, radius, max(.065, radius*.14), 'metal_red', 12, 5, axis)
    s = axis.cross(Z if abs(axis.z)<.8 else vec((0, 1, 0))).normalized()
    t = axis.cross(s)
    for a in (0, math.pi/3, 2*math.pi/3):
        outward = (s*math.cos(a)+t*math.sin(a))*radius
        k.beam(end-outward, end+outward, .09, 'metal_red')


def drive(k, p, axis=(0, 1, 0), size=1.0):
    """Motor, clutch and shaft pedestal beneath bulk handling drives."""
    p = vec(p)
    d = vec(axis).normalized()
    s = d.cross(Z).normalized()
    k.part()
    k.pipe(p-d*.32*size, p+d*.45*size, .70*size, 'metal_yellow', 14)
    k.pipe(p+d*.24*size, p+d*1.92*size, .51*size, FADED_BLUE, 12)
    for end in (.41, 1.58):
        k.pipe(p+d*end*size, p+d*(end+.16)*size, .6*size, DARK, 12)
    for j in (-1, 1):
        k.beam(p+s*j*.36*size-Z*.50*size, p+s*j*.36*size+d*1.4*size-Z*.50*size,
               size*.22, size*.23, 'steel_rust')
    k.box(p+d*.81*size+Z*.53*size, (size*.49, size*.57, size*.37), 'metal_grey')


def working_hopper(k, center, z0, z1, throat, mouth, prefix, paint):
    """Four tapering wear-lined sheets. Overlapping OBB courses tile the liner."""
    x, y = center
    bottom, top = rect(x, y, z0, *throat), rect(x, y, z1, *mouth)
    dz = z1-z0
    for i, (nx, ny) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
        j=(i+1)%4
        outward=vec((nx,ny,0))
        lo=(bottom[i]+bottom[j])*.5
        hi=(top[i]+top[j])*.5
        slide=(hi-lo).normalized()
        side=vec((ny,-nx,0))
        inward=side.cross(slide).normalized()
        k.part()
        slab(k, [bottom[i], bottom[j], top[j], top[i]], inward, .48,
             'steel_dark' if i%2 else 'hull_dark', paint)
        ncourse=7 if prefix=='mitt' else 8
        rot=rotation(side,slide,inward)
        for t in range(ncourse):
            t0=t/ncourse
            t1=(t+1)/ncourse
            centerline=lo.lerp(hi,(t0+t1)/2)
            # The wider edge of each course closes the diagonal mitre.
            width=(bottom[j]-bottom[i]).length*(1-t1)+(top[j]-top[i]).length*t1
            k.collider((width+.07,(hi-lo).length/ncourse+.055,.46),
                       centerline-inward*.23,rot,tag=prefix+'_wall',friction=.44)
        k.beam(top[i],top[j],.76,.74,'metal_grey')
        k.beam(bottom[i],bottom[j],.55,.57,'steel')
        for t in (.17,.62,.85):
            aa=bottom[i].lerp(bottom[j],t)-inward*.72
            bb=top[i].lerp(top[j],t)-inward*.77
            k.beam(aa,bb,.44,.55,'steel_rust' if t==.62 else 'metal_grey')
        for t in (.32,.72):
            aa=bottom[i].lerp(top[i],t)-inward*.55
            bb=bottom[j].lerp(top[j],t)-inward*.55
            k.beam(aa,bb,.23,.39,'hull_dark')
        for t in (.28,.72):
            p=top[i].lerp(top[j],t)
            k.box(p+Z*.14, (2.3,.94,.33) if nx==0 else (.94,2.3,.33),'hull_white')
        if prefix=='mitt' or i!=2:
            p=(top[i]+top[j])*.5+outward*.34+Z*.72
            lamp_head(k,p,lo+Z*2,TEAL,15,.66)
    return bottom,top


def mitt(k):
    x,y=40,-8
    k.marker('mitt_mouth',(x,y,26),(0,0,-1))
    k.marker('mitt_throat',(x,y,10),(0,0,-1))
    k.marker('crusher_in',(x,y,8.9))
    k.marker('crusher_out',CV1[0])
    bottom,top=working_hopper(k,(x,y),10,26,(6,6),(24,24),'mitt',PLATE)
    # Splayed abutments and the crusher undercroft are open on the rail side.
    for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
        foot=vec((x+sx*8.85,y+sy*8.6,0))
        knee=vec((x+sx*8.8,y+sy*8.5,12.1))
        cap=vec((x+sx*11.8,y+sy*11.8,25.8))
        pedestal(k,foot,(3.6,3.15),.92)
        lower=rect(foot.x,foot.y,1.4,2.7,2.5)
        upper=rect(knee.x,knee.y,knee.z,1.86,2.1)
        k.loft([lower,upper],'conc_warm')
        k.beam(knee,cap,1.18,1.45,'metal_grey')
        k.beam(knee-Z*.9,cap+vec((-sx*2.15,0,-3)),.50,.62,'steel_rust')
        k.box(knee,(2.6,2.45,.64),DARK)
    for sy in (-1,1):
        k.beam((31.2,y+sy*8.6,10.9),(48.9,y+sy*8.6,10.9),.78,.89,DARK)
        k.beam((31.9,y+sy*8.6,2.3),(42.3,y+sy*8.6,10.6),.36,.50,'steel_rust')
    # Impact wall: three armour cassettes, bolted to a bridge of backwards-raking ribs.
    for cy, length, h in [(-15.3,6.9,12.7),(-8.0,7.4,16.0),(-.6,7.2,14.4)]:
        xbase=52.26
        a=vec((xbase,cy,26));b=vec((xbase+1.22,cy,26+h))
        side,along,norm=belt_frame(a,b)
        rot=rotation(side,along,norm)
        k.part()
        k.box((a+b)*.5,(length-.08,(b-a).length,.66),'hull_grey',rot)
        k.collider((length,(b-a).length,.68),(a+b)*.5,rot,'mitt_backstop',.48)
        for t in (-.36,.35):
            q=a+vec((.65,t*length,0))
            k.beam(q,b+vec((.65,t*length,0)),.41,.60,'steel_rust')
            k.beam(q+vec((3.1,0,-2.5)),q+vec((.68,0,h*.61)),.59,.69,'metal_grey')
        k.box(b+Z*.1,(1.00,length+.2,.36),'metal_yellow')
    k.catwalk((54.8,-19.4,25.3),(54.8,2.0,25.3),1.78)
    k.catwalk((46.3,-20.7,25.35),(54.8,-20.7,25.35),1.55)
    k.ladder((55.8,-16,10.2),(55.8,-16,25.4))
    k.ladder((49.1,-17.4,1.0),(49.1,-17.4,10.2))
    k.catwalk((48.1,-17.1,10.1),(55.8,-17.1,10.1),1.64)
    lamp_head(k,(54,-14,32),(47,-13,18),SODIUM,19,1.16)
    lamp_head(k,(54,1,33),(51,-2,21),TEAL,16,.84)
    k.lamp((52.85,-7.7,40.7),1.55,'beacon',RED,17,.92)
    # Jaw housing, eccentric, exposed flywheel rim and an accessible gearbox.
    k.part()
    k.box((40.8,-8,1.01),(11.4,8.9,2.02),'conc_dark')
    k.loft([rect(40.5,-8,2.0,10.6,8.2),rect(40.4,-8,8.9,7.2,6.7)],'metal_green')
    k.box((40,-8,9.55),(6.6,6.6,.68),'steel_rust')
    for yy in (-12.35,-4):
        k.pipe((39.4,yy-.28,5.1),(39.4,yy+.28,5.1),2.45,'hull_dark',18)
        k.torus((39.4,yy-.36,5.1),1.92,.36,'metal_red',22,6,(0,1,0))
        k.pipe((39.4,yy-.58,5.1),(39.4,yy+.48,5.1),.54,'steel',14)
    drive(k,(44.6,-12.2,3.2),(0,-1,0),1.07)
    k.beam((42,-8,7.4),(47.9,-8,5.4),3.35,.32,'metal_dark')
    for yy in (-9.77,-6.23):
        k.beam((42,yy,7.8),(48,yy,5.85),.24,.98,PLATE)
    lamp_head(k,(32.7,-14.6,10.3),(40,-8,3.4),SODIUM,13,.9)
    lamp_head(k,(48.8,-13.8,10.5),(46,-11,4.2),TEAL,13,.94)
    lamp_head(k,(31.5,-.2,11),(36,-8,2.4),TEAL,13,.72)


def grizzly(k):
    x,y=40,24
    k.marker('truck_grizzly',(x,y,.38),(0,-1,0))
    k.marker('truck_dump',(x,y+2.4,1.45),(0,-1,0))
    k.part()
    k.box((x,y,.12),(14,11.2,.24),'rubber')
    for sx in (-1,1):
        k.box((x+sx*7.75,y,.41),(1.38,13.9,.82),'conc')
        k.box((x+sx*7.75,y+.2,.87),(1.07,12.0,.15),DARK)
    k.box((x,y-6.2,.56),(16.8,1.12,1.12),'conc_dark')
    for i in range(12):
        xx=x+(i-5.5)*1.07
        k.beam((xx,y-5.3,.38),(xx,y+5.2,.40),.34,.35,'steel_rust' if i%4==0 else DARK)
    k.box((x,y+5.85,.18),(15.2,1.35,.36),'metal_hazard')
    for sx,mat in [(-1,FADED_BLUE),(1,'metal_red')]:
        xx=x+sx*8.0
        k.box((xx,y-3.4,1.85),(1.37,2.75,2.64),mat)
        lamp_head(k,(xx,y-3.3,3.55),(x,y-.8,.75),TEAL if sx<0 else SODIUM,12,.81)
    k.tube([(47.8,20.0,1.8),(48.9,20,1.8),(48.9,11.4,1.8),(47.8,11.4,1.8)],.24,'steel')
    k.lamp((31.4,18.2,.2),4.8,col=SODIUM,r=13,power=.72)


def belt_colliders(k,name,start,end,width,speed,guard=True):
    p,q=vec(start),vec(end)
    side,direction,up=belt_frame(p,q)
    rot=rotation(side,direction,up)
    length=(q-p).length
    count=max(1,math.ceil(length/4.6))
    velocity=three(direction*speed)
    for i in range(count):
        c=p.lerp(q,(i+.5)/count)
        k.collider((width,length/count+.04,.29),c-up*.145,rot,name,1.15)
        item=k.data['colliders'][-1]
        item['surfaceVelocity']=velocity
        if guard:
            for s in (-1,1):
                k.collider((.19,length/count+.04,.86),c+side*s*(width/2+.095)+up*.22,
                           rot,'belt_guard',.49)


def conveyor(k,name,pts,width,speed):
    material={'cv1':'metal_yellow','cv2':'metal_green','cv3':'hull_rust'}[name]
    ps=[vec(p) for p in pts]
    k.marker(name+'_start',ps[0],(ps[1]-ps[0]).normalized())
    k.marker(name+'_end',ps[-1],(ps[-1]-ps[-2]).normalized())
    k.path(name,[{'p':three(p),'up':three(belt_frame(p,ps[min(i+1,len(ps)-1)] if i<len(ps)-1 else p+(p-ps[i-1]))[2])} for i,p in enumerate(ps)])
    for leg,(p,q) in enumerate(zip(ps,ps[1:])):
        side,d,up=belt_frame(p,q)
        length=(q-p).length
        k.part()
        k.beam(p-up*.145,q-up*.145,width,.29,'rubber')
        belt_colliders(k,name,p,q,width,speed)
        for sign in (-1,1):
            lo=p+side*sign*(width/2+.10)
            hi=q+side*sign*(width/2+.10)
            k.beam(lo+up*.27,hi+up*.27,.20,.88,material)
            k.beam(lo+up*.68,hi+up*.68,.26,.12,'steel')
        bridge=(name=='cv3' and leg in (1,2))
        bottom=1.72 if not bridge else .89
        k.truss(p-up*bottom,q-up*bottom,width+.7, min(1.55,bottom),DARK,
                max(1,round(length/6.2)),.25 if width<4 else .31)
        k.catwalk(p+side*(width/2+1.28)-up*.21, q+side*(width/2+1.28)-up*.21,1.65)
        stations=max(1,int(length/3.6))
        for j in range(stations):
            c=p.lerp(q,(j+.45)/stations)-up*.41
            k.pipe(c-side*(width/2+.22),c+side*(width/2+.22),.18,'steel_rust',7)
        nleg=max(1,round(length/13))
        if name=='cv3' and leg==2:
            nleg=0
        for j in range(nleg):
            c=p.lerp(q,(j+.35)/nleg)
            # The waste conveyor spans both rail viaducts. Piers stand outside their loading gauge.
            if (name=='cv3' and (106<c.x<133)) or (name=='cv2' and c.y>-1):
                continue
            feet=[]
            for ss in (-1,1):
                pp=c+side*(width/2+.8)*ss
                z=ground(pp.x,pp.y)
                if z is None:continue
                if c.z-z<2.0:continue
                foot=vec((pp.x,pp.y,z))
                feet.append(foot)
                pedestal(k,foot,(1.8,1.8),.22)
                k.beam(foot+Z*.74,pp-Z*.72,.45,.56,'metal_grey')
            if len(feet)==2 and c.z-max(f.z for f in feet)>3.3:
                k.beam(feet[0]+Z*.82,c+side*(width/2+.75)-Z*.85,.31,.38,material)
        if leg==0 or leg==len(ps)-2:
            t=.22 if leg==0 else .75
            c=p.lerp(q,t)+side*(width/2+1.9)-up*.11
            k.lamp(c,2.75,col=SODIUM if name=='cv3' else TEAL,r=11,power=.67)
    for index in (0,len(ps)-1):
        p=ps[index]
        a,b=(ps[0],ps[1]) if index==0 else (ps[-2],ps[-1])
        side,d,up=belt_frame(a,b)
        k.pipe(p-side*(width/2+.48)-up*.37,p+side*(width/2+.52)-up*.37,.42,'steel_dark',12)
        drive(k,p+side*(width/2+.70)-up*.38,tuple(side),.85 if name=='cv2' else 1.2)
    if name=='cv3':
        # Triangular cantilever carrying the final discharge out over the new fracture.
        p=ps[-2];q=ps[-1]
        side,d,up=belt_frame(p,q)
        # A short concrete portal is founded on the last intact rock west of the break.
        # Both legs stand east of x=131; the loaded train can pass underneath the approach span.
        abutment=p-d*1.0
        foot_height=ground(abutment.x,abutment.y)
        if foot_height is not None:
            for sign in (-1,1):
                foot=abutment+side*sign*2.88
                foot.z=ground(foot.x,foot.y) or foot_height
                crown=p+side*sign*2.16-Z*1.05
                pedestal(k,foot,(2.46,2.74),.74)
                k.beam(foot+Z*1.30,crown,1.11,1.35,'conc_warm')
                k.beam(foot+Z*3.52,q+side*sign*1.84-Z*1.18,.47,.54,'hull_rust')
            k.beam(p-side*2.30-Z*1.21,p+side*2.30-Z*1.21,.93,1.05,DARK)
        for sign in (-1,1):
            k.truss(p+side*sign*(width*.5+.25)-Z*3.65,
                    q+side*sign*(width*.5+.25)-Z*1.2,
                    .72,1.10,'hull_rust',3,.28)
        lamp_head(k,q+side*2.6+Z*1.6,q-Z*4,SODIUM,17,.94)
        k.marker('waste_out',q,d)

def jig(k):
    x,y=74,-26
    floor=2.2
    top=9.2
    k.marker('jig',(x,y,3))
    k.marker('jig_ore_exit',(83.45,-27,2.25))
    k.marker('jig_overflow',(70,-20.6,5.1),(0,1,0))
    k.marker('jig_gate_axis',(83.25,-27,2.2),(0,0,1))
    k.marker('jig_feed_land',(65.75,-22.9,7.7))
    k.part()
    k.box((x,y,floor-.37),(19.35,11.3,.74),'metal_grey')
    k.collider((18.3,10.3,.55),(x,y,floor-.275),tag='jig_floor',friction=.68)
    # The corners of the sieve move on paired spring blocks. Its plenum lies below the pan.
    for sx in (-1,1):
        for sy in (-1,1):
            xx=x+sx*7.7
            yy=y+sy*4.5
            pedestal(k,(xx,yy,0),(2.55,1.91),.22)
            spiral=[(xx+.40*math.cos(t*math.tau*2.55/20),
                     yy+.40*math.sin(t*math.tau*2.55/20),.75+1.03*t/20) for t in range(21)]
            k.tube(spiral,.15,'steel_dark',5)
            k.cyl((xx,yy,1.34),.25,.94,'steel',8)
    k.box((x+1.4,y,1.08),(12.9,6.5,1.52),'metal_teal')
    def wall(p,size,paint='hull_grey',tag='jig_wall'):
        k.part()
        k.box(p,size,paint)
        k.collider(size,p,tag=tag,friction=.61)
    wall((64.63,y,(top+floor)*.5),(.74,11.45,top-floor),PLATE)
    wall((x,-31.36,(top+floor)*.5),(18.43,.72,top-floor),'hull_grey')
    # East discharge throat and separate north weir.
    for sy,ey in [(-31,-29.25),(-24.75,-21)]:
        wall((83.37,(sy+ey)/2,(floor+top)/2),(.74,ey-sy,top-floor),PLATE)
    wall((83.37,-27,8.5),(.74,4.5,1.4),'metal_yellow')
    for sx,ex in [(65,67.65),(72.35,83)]:
        wall(((sx+ex)/2,-20.64,(floor+top)/2),(ex-sx,.72,top-floor))
    wall((70,-20.64,(floor+5.1)/2),(4.71,.72,5.1-floor),PLATE)
    for a,b in [((64.54,-31.43,9.31),(83.7,-31.43,9.31)),
                ((64.53,-31.4,9.31),(64.53,-20.52,9.31)),
                ((72.32,-20.57,9.31),(83.75,-20.57,9.31))]:
        k.beam(a,b,.79,.34,DARK)
    for xx in [66.6,70.8,77.2,81.45]:
        k.beam((xx,-32.37,2.04),(xx,-31.75,9.2),.56,.59,'metal_grey')
        k.box((xx,-32,2.25),(1.15,.98,.46),'steel_rust')
    for yy in (-29.44,-24.55):
        k.box((83.91,yy,7.6),(.67,.42,10.25),DARK)
    k.box((83.92,-27,12.8),(.90,5.55,.48),'metal_yellow')
    k.pipe((83.94,-27,8.7),(83.94,-27,12.6),.32,'steel',12)
    with k.into('jig_gate_door',loc=(83.32,-27,2.2)):
        c=(83.32,-27,4.98)
        wall(c,(.42,4.45,5.56),'metal_orange','jig_gate')
        k.box((83.60,-27,5.12),(.16,4.0,.65),'metal_hazard')
        for yy in (-28.45,-25.55):
            k.box((83.61,yy,5.0),(.23,.31,4.93),DARK)
    # The two moving steel plates entrain settled ore and the skimmed waste independently.
    feeder_a,feeder_b=(77,-27,2.3),(83.05,-27,2.24)
    belt_colliders(k,'jig_feeder',feeder_a,feeder_b,3.62,2.8,False)
    k.beam(vec(feeder_a)-Z*.08,vec(feeder_b)-Z*.08,3.65,.16,'steel_rust')
    for i in range(7):
        k.box((77.2+i*.81,-27,2.31),(.14,3.53,.083),'steel_dark')
    waste_a,waste_b=(70,-20.19,4.87),(70,-17.95,4.18)
    belt_colliders(k,'waste_feeder',waste_a,waste_b,3.8,2.65,False)
    k.beam(vec(waste_a)-Z*.12,vec(waste_b)-Z*.12,3.8,.24,'metal_orange')
    for xx in (67.92,72.08):
        k.beam((xx,-20.30,5.48),(xx,-17.7,4.60),.27,.8,'hull_grey')
    # The oscillating air reservoirs have flanged couplings and inspection wheels.
    for xx,yy in [(67.2,-34.9),(80.0,-34.1)]:
        k.pipe((xx-1.3,yy,1.59),(xx+1.28,yy,1.59),.91,'metal_teal',14)
        k.pipe((xx-.88,yy,1.59),(xx-.67,yy,1.59),.99,DARK,12)
        k.tube([(xx,yy,2.45),(xx,yy,3.45),(xx,-31.7,3.45)],.36,'steel_rust')
        valve(k,(xx,yy-.78,1.58),(0,-1,0),.37)
    k.catwalk((65,-32.97,7.0),(81.8,-32.97,7.),1.58)
    k.stairs((63.2,-37.8,.3),(65,-33.3,7.),1.42)
    for p,aim,col in [((66,-33.1,8.4),(68,-28,4.6),SODIUM),((79,-32.3,8.4),(78,-28,4.1),TEAL),
                      ((65.1,-20.4,9.6),(69,-22,5),TEAL),((83.8,-25.1,10.1),(84,-27,2.4),SODIUM)]:
        lamp_head(k,p,aim,col,13,.76)


def updraft(k):
    x,y=98,8
    k.marker('updraft_base',(x,y,3),(0,0,1))
    k.marker('updraft_top',(x,y,62),(1,0,0))
    k.marker('updraft_elbow',(109.55,y,60.3),(1,0,-.23))
    # Four corners are separated by broad open lift bays, with the heavy bracing on the far side.
    for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
        xx=x+sx*4.97
        yy=y+sy*4.99
        pedestal(k,(xx,yy,0),(3.42,3.25),1.16)
        k.loft([rect(xx,yy,1.65,2.48,2.4),rect(xx,yy,12.65,1.54,1.5)],'conc_warm')
        k.beam((xx,yy,12.6),(xx,yy,61.9),1.3,1.49,'hull_grey')
        k.beam((xx+sx*.71,yy+sy*.28,7.9),(xx+sx*.71,yy+sy*.28,61.8),.30,.51,'steel_rust')
    # Thin sidewall OBBs are shorter than the broad-phase cell budget.
    for nx,ny in [(0,1),(-1,0),(1,0),(0,-1)]:
        first=11.0 if ny<0 else 3.
        for i in range(math.ceil((62-first)/6.8)):
            low=first+i*6.8
            high=min(62,low+6.8)
            c=(x+nx*4.13,y+ny*4.13,(low+high)/2)
            k.collider((8.4,.26,high-low) if ny else (.26,8.4,high-low),c,tag='updraft_wall',friction=.21)
    for z in [12.5,26.2,43.2,58.7]:
        for xx in (92.95,103.04):
            k.beam((xx,3.05,z),(xx,12.95,z),.59,.81,'metal_grey')
        for yy in (3.04,12.96):
            k.beam((92.95,yy,z),(103.04,yy,z),.68,.88,'metal_grey')
    bands=[(3.3,13.2),(13.2,26.1),(26.1,43.1),(43.1,58.65)]
    for i,(low,high) in enumerate(bands):
        k.part()
        # Central back wall and a narrow cutaway beside it allow the ascending rock stream to silhouette.
        k.box((98.1,12.73,(low+high)/2),(7.35,.55,high-low-.24),
              'metal_green' if i==1 else 'hull_grey')
        k.beam((93.4,13.25,low),(102.8,13.25,high),.44,.55,DARK)
        k.beam((92.8,3.6,low),(92.8,12.65,high),.53,.69,'steel_rust')
        k.box((92.93,9.70,(low+high)/2),(.50,3.65,high-low-.69),'metal_teal')
        if i in (1,3):
            k.beam((103.05,3.65,low),(103.05,12.65,high),.43,.55,'metal_grey')
    # Riser services and expansion unions up the west side.
    for i,yy in enumerate((5.25,7.2,11.3)):
        xx=91.88-i*.26
        k.pipe((xx,yy,2.5),(xx,yy,61.7),.38 if i!=1 else .59,'steel_rust' if i==1 else 'steel')
        for z in (10.35+i*1.35,29.8+i*.70,53+i*.72):
            k.cyl((xx,yy,z),.65 if i!=1 else .85,.44,DARK,12)
    for z in (13.2,27.,44.,60.):
        k.catwalk((92.0,13.8,z),(104.1,13.8,z),1.6)
        k.catwalk((92,7.6,z),(92,13.8,z),1.55)
        k.beam((93.1,12.4,z-2.65),(92.25,14.4,z),.35,.41,'steel_rust')
        k.box((93.5,14.8,z+1),(1.38,.81,1.9),'metal_grey')
        lamp_head(k,(92.3,13.43,z+1.76),(95,9,z-3),SODIUM if z==27 else TEAL,12,.91)
    k.ladder((91.7,14.0,2),(91.7,14.0,60.2),.69)
    # The east-facing elbow is open at its exit. A crescent of armoured sheathing
    # and a goose-neck service rail describe the bend, without covering the mouth.
    roof=[(93.5,59.3),(93.5,63.2),(94.35,66),(96.4,67.6),(99.6,68.25),(103.75,67.55),(107.35,66.1),(111.2,64.2)]
    lower=[(102.1,59.3),(102.3,60.9),(103.1,61.2),(104.65,60.95),(107.45,60.05),(111.15,58.6)]
    for yy,normal in [(4,-1),(12,1)]:
        contour=[(xx,yy,zz) for xx,zz in roof]+[(xx,yy,zz) for xx,zz in reversed(lower)]
        slab(k,contour,(0,normal,0),.40,'metal_grey','hull_dark')
        for (xx,zz),(ex,ez) in zip(roof,roof[1:]):
            k.beam((xx,yy+.08*normal,zz),(ex,yy+.08*normal,ez),.39,.44,'steel_rust')
    for shape,paint in [(roof,'metal_teal'),(lower,'hull_dark')]:
        for (xx,zz),(ex,ez) in zip(shape,shape[1:]):
            k.part()
            face=[(xx,4,zz),(ex,4,ez),(ex,12,ez),(xx,12,zz)]
            n=vec((ex-xx,0,ez-zz)).cross(vec((0,1,0))).normalized()
            slab(k,face,n,.37,paint,'steel_rust')
    for yy in (3.70,12.3):
        k.beam((93.6,yy,59.4),(101.05,yy,67.6),.47,.53,'metal_grey')
        k.beam((101.05,yy,67.6),(109.65,yy,61.6),.43,.45,'metal_grey')
        k.box((110.95,yy,61.4),(.69,.98,5.6),'metal_yellow',(0,5,0))
    k.pipe((92.02,7.2,60.2),(94.12,7.2,63.0),.58,'steel_rust')
    k.lamp((94.37,12.4,65.4),2.7,'beacon',RED,21,.95)
    lamp_head(k,(102.5,12.45,61.5),(111,8,40),TEAL,24,1.20)
    lamp_head(k,(98.7,3.6,58.45),(98,8,47),TEAL,16,.86)
    lamp_head(k,(103.2,12.3,25.7),(99,8,19),SODIUM,15,.81)
    lamp_head(k,(94.16,4.85,11.6),(98,6,4.6),TEAL,17,1.06)
    k.catwalk((89.6,3.2,4.4),(93,3.2,4.4),1.25)
    valve(k,(91.5,7.1,4.0),(-1,0,0),.80)


def buffer(k):
    x,y=114,8
    k.marker('bin_out',(x,y,17),(0,0,-1))
    k.marker('bin_mouth',(x,y,38),(0,0,-1))
    k.marker('bin_gate_axis',(x,y,16.78),(1,0,0))
    bottom,top=working_hopper(k,(x,y),17,38,(4,4),(14,12),'bin','hull_grey')
    k.part()
    # Raked portal legs straddle both rails and leave the load aperture free.
    for xx in (104.8,123.25):
        for sy in (-1,1):
            yy=y+sy*7.9
            z=ground(xx,yy)
            z=0 if z is None else z
            pos=vec((xx,yy,z))
            high=vec((xx+(.86 if xx<114 else -.85),y+sy*6.85,37.75))
            pedestal(k,pos,(2.7,3.25),.91)
            k.beam(pos+Z*1.46,high,1.19,1.53,'metal_grey')
            k.beam(pos+Z*5.9,high+vec((0,-sy*2.48,-17.4)),.48,.58,'steel_rust')
            k.box((xx,yy,15.44),(1.50,1.55,.58),'steel_rust')
    for yy in (.9,15.1):
        k.truss((105.3,yy,22.8),(122.6,yy,22.8),1.55,2.26,DARK,4,.39)
        k.beam((105.37,yy,23.9),(110.2,yy,34.35),.43,.50,'steel_rust')
        k.beam((122.6,yy,23.9),(118,yy,34),.43,.50,'steel_rust')
    for xx in (105.02,123.05):
        k.truss((xx,.89,30.2),(xx,15.1,30.2),1.25,1.83,'metal_grey',3,.35)
    k.catwalk((105.55,.57,37.9),(122.52,.57,37.9),1.48)
    k.catwalk((122.52,.57,37.9),(122.52,15.32,37.9),1.60)
    k.ladder((123.56,15.17,2.1),(123.56,15.17,38.1))
    for z in (9.2,20.6,30.7):
        k.box((123.23,14.1,z),(2.1,2.86,.27),DARK)
        lamp_head(k,(123.31,14.75,z+1.13),(121.5,13.55,z-1.6),SODIUM,11,.55)
    for yy in (5.55,10.45):
        k.beam((111.49,yy,16.58),(121.5,yy,16.58),.39,.53,'steel_dark')
    with k.into('bin_gate_door',loc=(114,8,16.78)):
        k.part()
        k.box((114,8,16.78),(4.62,4.54,.43),'metal_yellow')
        k.collider((4.62,4.54,.43),(114,8,16.78),tag='bin_gate',friction=.61)
        k.box((116.26,8,16.79),(.49,5.20,.66),'metal_hazard')
    k.beam((123.12,.21,15.63),(123.12,15.80,15.63),.81,.91,DARK)
    for yy in (6.60,9.40):
        k.beam((120.85,yy,15.84),(123.40,yy,15.84),.50,.56,'steel_rust')
    k.box((122.0,8,16.9),(2.50,4.70,2.05),'metal_red')
    k.pipe((117.5,8,16.85),(121.38,8,16.85),.31,'steel',10)
    lamp_head(k,(121.4,4.7,22),(114,8,9),TEAL,20,1.1)
    lamp_head(k,(106.9,14.71,22.3),(113,8,15.5),SODIUM,17,.95)
    k.lamp((121.7,14.75,37.9),2.0,'beacon',RED,16,.74)


def thickener(k):
    x,y,z=74.2,22,.0
    r=10.9
    k.part()
    # A thick concrete basin with a visible return launder. The annulus is open on top.
    profile=[(.22,r-.32),(.81,r+.36),(4.65,r+.36),(5.0,r+.08),(5.,r-.68),
             (3.92,r-.68),(3.92,r-1.12),(4.46,r-1.12),(4.46,r-1.48),(2.52,r-1.6)]
    rings=[]
    for h,rad in profile:
        rings.append([(x+rad*math.cos(i*math.tau/40),y+rad*math.sin(i*math.tau/40),z+h) for i in range(40)])
    k.loft(rings,'conc',caps=False,curve=True)
    k.cyl((x,y,3.1),r-1.55,.22,'metal_green',36)
    k.torus((x,y,3.25),r-2.35,.09,'steel_rust',34,5)
    for i in range(8):
        a=i*math.tau/8+.14
        xx=x+(r+.50)*math.cos(a)
        yy=y+(r+.5)*math.sin(a)
        k.box((xx,yy,2.36),(1.18,.74,4.17),'conc_dark',math.degrees(a))
    k.truss((x-r-.7,y+.5,5.69),(x+r+.94,y+.50,5.69),1.45,1.18,'steel_rust',6,.23)
    k.catwalk((x-r-1.15,y+.5,6.36),(x+r+1.32,y+.5,6.36),1.65)
    k.cyl((x,y,5.39),1.71,1.35,FADED_BLUE,16)
    k.cyl((x,y,8.16),1.28,2.15,'metal_grey',16)
    k.lathe((x,y,0),[(9.21,1.39),(9.64,1.12),(9.67,.55)],'metal_yellow',16)
    k.pipe((x,y,3.32),(x,y,7.37),.32,'steel',10)
    with k.into('thickener_rake',loc=(x,y,3.47)):
        for i in (0,1):
            a=.38+math.pi*i
            direction=vec((math.cos(a),math.sin(a),0))
            side=vec((-direction.y,direction.x,0))
            c=vec((x,y,3.74))
            k.truss(c+direction*.61,c+direction*(r-1.93),.51,.45,'steel_rust',3,.11)
            for t in (2.5,5.4,8.0):
                p=c+direction*t
                k.beam(p-side*.31-Z*.19,p+side*.49-Z*.26,.24,.44,'hull_dark')
    k.stairs((85.2,28.2,.4),(85.6,23.6,6.33),1.60)
    for p,aim,col in [((63.2,22.6,7.55),(69,21,3.3),SODIUM),((84.8,22.8,7.58),(80,20,3.3),TEAL)]:
        lamp_head(k,p,aim,col,14,.73)
    k.tube([(74.5,11.05,1.85),(74.5,9.5,1.85),(85.8,9.5,1.85),(85.8,6.9,1.85)],.63,'steel_rust')
    valve(k,(85.85,7.84,1.85),(1,0,0),.61)
    k.marker('thickener',(x,y,3.7),(0,0,1))


def silos(k):
    for i,(x,y,r,h) in enumerate([(56.8,20.8,3.45,17.4),(57.6,30.2,4.04,22.1),(67.25,36.5,3.26,15.8)]):
        k.part()
        k.cyl((x,y,.53),r+.57,1.06,'conc_dark',18)
        for j in range(3):
            a=(j/3+.09)*math.tau
            xx=x+.80*r*math.cos(a)
            yy=y+.80*r*math.sin(a)
            k.beam((xx,yy,1.05),(xx,yy,7.41),.60,.72,'metal_grey')
        k.lathe((x,y,0),[(2.25,.78),(5.85,r-.18),(6.21,r),(h-1.2,r),(h-.71,r+.05),
                          (h+.52,r*.35),(h+.55,.62)],'hull_white' if i==1 else 'metal_green',22)
        for h0 in (6.45,h-1.55):
            k.cyl((x,y,h0),r+.07,.30,'steel_rust',22)
        k.pipe((x-r-.20,y,2),(x-r-.20,y,h-.5),.16,'steel_rust',8)
        k.ladder((x+1,y-r-.33,1.03),(x+1,y-r-.33,h-.88))
        k.box((x+1,y-r-.48,h-.80),(1.62,1.15,.21),DARK)
        for dh in (7.85,h-2.05):
            lamp_head(k,(x+.9,y-r-.42,dh),(x+1,y-r-.9,dh-3),SODIUM,10.5,.54)
        valve(k,(x,y,2.4),(0,-1,0),.43)
    k.tube([(57,20.6,17.6),(57,20.6,23.8),(57.6,30.2,23.8),(57.6,30.2,22.0)],.34,'steel')
    k.tube([(57,30.2,8.3),(62.9,30.2,8.3),(62.9,36.5,8.3),(67,36.5,8.3)],.41,'steel_rust')


def control(k):
    # Switchman's station built into a low aggregate bunker. Slanted glazing faces the working floor.
    x,y=74.1,1.6
    k.part()
    k.prism([(63.0,-4.15),(78.9,-4.15),(83.35,-.50),(83.35,7.55),(63.,7.55)],0,1.05,'conc_dark')
    k.prism([(63.66,-3.43),(78.75,-3.43),(82.59,-.27),(82.59,6.95),(63.66,6.95)],1.05,5.78,'conc_warm')
    k.box((70.15,-3.39,3.09),(8.15,.53,3.72),DARK)
    k.box((70.15,-3.72,4.16),(7.69,.19,1.15),'metal_teal')
    for i in (0,1,2):
        k.box((66.35+i*3.72,-3.83,3.12),(.29,.47,3.8),'conc')
    k.box((80.50,1.17,2.55),(2.76,2.94,2.99),'metal_grey')
    k.box((74.30,-.2,6.03),(17.3,9.52,.72),'conc')
    k.box((76.50,.73,7.71),(12.58,7.83,3.05),'metal_green')
    k.box((76.50,.55,9.49),(13.65,8.55,.66),'hull_white')
    for i in range(5):
        w=1.84 if i<4 else 1.02
        xx=71.54+i*2.16
        k.part(.2+i*.145)
        k.box((xx,-3.24,7.9),(w+.25,.39,1.64),DARK,(9,0,0))
        k.box((xx,-3.47,7.94),(w,.10,1.13),'glass_warm' if i!=1 else 'glass',(9,0,0))
        k.light((xx,-3.62,7.98),WINDOW,9,.37+.08*(i%3),'window')
    for i,yy in enumerate((-1.95,.22,2.49)):
        k.part(.21+i*.23)
        k.box((82.89,yy,7.88),(.27,1.93,1.52),DARK)
        k.box((83.09,yy,7.9),(.10,1.66,1.08),'glass_warm')
        k.light((83.22,yy,7.9),WINDOW,9.2,.45,'window')
    k.stairs((84.64,-4.9,.22),(79.22,-4.91,5.85),1.47)
    k.catwalk((70.0,-4.88,5.83),(79.25,-4.88,5.83),1.62)
    k.box((76.93,2.18,10.28),(3.74,2.89,1.12),'metal_grey')
    for xx in (75.87,78.05):
        k.cyl((xx,2.17,10.93),.63,.39,DARK,10)
    k.pipe((72.32,4.28,9.78),(72.32,4.28,15.13),.16,'steel',8)
    k.beam((71.42,4.27,14.68),(73.22,4.27,14.68),.14,DARK)
    lamp_head(k,(83.15,-.5,5.89),(86.2,-.9,1.1),TEAL,14,1.0)
    lamp_head(k,(71.0,-4.41,6.0),(68.4,-4.62,1.5),SODIUM,12,.82)
    k.marker('control_room',(x,y,7.82))


def substation(k):
    x,y=93.4,33.8
    k.part()
    k.box((x,y,.25),(15.1,9.6,.5),'conc')
    for i,(xx,yy,sz) in enumerate([(89.4,34.75,1.10),(94.7,34.65,.94),(99.0,33.48,.76)]):
        k.part()
        k.box((xx,yy,.82),(3.41*sz,3.18*sz,.65),'conc_dark')
        k.box((xx,yy,2.28*sz+.32),(2.98*sz,2.47*sz,2.85*sz),FADED_BLUE)
        for j in range(5):
            k.box((xx+(-1.04+j*.5)*sz,yy-1.39*sz,2.27*sz+.31),(.19*sz,.58*sz,2.24*sz),'steel_dark')
        for sign in (-1,1):
            ox=xx+sign*.60*sz
            k.lathe((ox,yy,3.44*sz+.41),[(0,.34),(.12,.41),(.28,.21),(.48,.37),(.58,.17),
                      (.75,.33),(.87,.14),(1.10,.17)],'conc_warm',10)
            k.pipe((ox,yy,4.45*sz+.41),(ox,yy,4.81*sz+.41),.09,'steel',7)
        if i<2:
            k.cable((xx+.60*sz,yy,4.8*sz+.42),(xx+3.64,yy+.12,4.75),.51,.055,'steel_dark')
    for xx in (85.78,101.04):
        for yy in (29.56,38.36):
            k.beam((xx,yy,.38),(xx,yy,3.2),.16,.16,'steel_dark')
    for a,b in [((85.78,29.56,.45),(85.78,38.36,.45)),((85.78,38.36,.45),(101.04,38.36,.45)),
                ((101.04,38.36,.45),(101.04,29.56,.45))]:
        k.railing(a,b,'metal_grey',2.35)
    for p in ((87,30,.49),(99.95,37.32,.49)):
        k.lamp(p,3.82,r=12,power=.65,col=TEAL)
    for xx in (87.12,99.45):
        k.pipe((xx,37.94,.42),(xx,37.94,7.52),.16,'steel_rust',8)
    k.cable((87.12,37.94,7.52),(99.45,37.94,7.52),.68,.09,'steel_dark')
    k.cable((87.12,37.94,7.43),(92.1,14.35,14.85),2.05,.11,'steel_dark')


def pump_shop(k):
    x,y=56.9,9.5
    k.part()
    k.box((x,y,.40),(10.4,8.9,.8),'conc_dark')
    k.box((x,y,3.04),(9.74,8.3,4.87),'conc')
    # An offset service canopy shelters the twin pumps along the shop frontage.
    k.loft([rect(x,y,5.44,10.05,8.77),
            [(51.87,5.11,6.1),(61.94,5.11,6.1),(61.94,13.88,6.86),(51.87,13.88,6.86)]],'metal_blue')
    for yy in (7.04,11.32):
        k.box((61.84,yy,2.55),(.17,2.36,3.8),'metal_teal')
        k.box((61.98,yy,3.32),(.10,1.89,.79),'glass_warm')
    for xx in (53.3,59.9):
        k.box((xx,5.26,2.96),(2.33,.16,1.94),'metal_dark')
        k.box((xx,5.12,3.1),(2.05,.10,.91),'glass')
    k.box((57.63,2.88,4.68),(6.9,4.6,.32),'metal_green',(-5,0,0))
    for xx in (54.38,60.77):
        k.beam((xx,1.04,.3),(xx,1.04,4.46),.22,.27,'steel_rust')
    for xx in (56.13,59.39):
        k.box((xx,2.64,.59),(2.55,2.7,.75),'conc_dark')
        drive(k,(xx,2.71,1.61),(0,-1,0),.87)
        k.tube([(xx,2.83,1.48),(xx,4.0,1.48),(xx,4.0,2.97)],.33,'steel_rust')
    lamp_head(k,(60.5,1.86,4.52),(58.9,2.66,1.0),SODIUM,12,.72)
    lamp_head(k,(62.06,11.8,5.45),(63.0,11.0,2),TEAL,13,.81)


def dry_yard(k):
    # Ore mill consumables south of the haul road. Keep all stock low, leaving the foreground legible.
    x,y=74,-81
    z=ground(x,y)
    if z is None:return
    k.part()
    k.box((x,y,z+.23),(18.75,10.58,.46),'conc_dark')
    for xx in (65.6,74.8,82.24):
        for yy in (-85.3,-76.62):
            bottom=ground(xx,yy)
            bottom=z-1 if bottom is None else bottom
            k.beam((xx,yy,min(z,bottom)),(xx,yy,z+6.22+(.73 if yy>-80 else 0)),.39,.46,'steel_rust')
    k.box((x,-76.63,z+3.63),(17.12,.39,6.36),'metal_green')
    k.box((65.52,-80.96,z+2.80),(.39,8.73,4.83),'metal_green')
    k.box((x,y,z+6.67),(18.88,11.34,.39),'metal_grey',(4.8,0,0))
    k.truss((65.42,-85.48,z+5.49),(82.31,-85.48,z+5.49),.63,1.21,DARK,4,.18)
    for xx,yy,rows in [(68,-81.2,3),(78.25,-80.4,2)]:
        for i in range(rows):
            for j in range(rows-i):
                centre=vec((xx+(j+(i*.5)-(rows-1)*.5)*.97,yy,z+.95+i*.83))
                k.pipe(centre+vec((0,-2.46,0)),centre+vec((0,2.46,0)),.46,'steel_rust' if i%2==0 else 'hull_grey',10)
                k.pipe(centre+vec((0,-2.53,0)),centre+vec((0,-2.47,0)),.34,'metal_dark',10)
    for xx,yy,count in [(87.3,-81,3),(91,-74.1,4),(60.4,-76.8,2)]:
        zz=ground(xx,yy)
        if zz is None:continue
        for j in range(count):
            k.box((xx,yy,zz+.58+j*.61),(3.66,5.62,.48),'hull_dark' if j%2 else 'hull_rust',-8)
            k.box((xx+.88,yy,zz+.29+j*.61),(.30,5.78,.19),'tarp',-8)
    for p,aim,col in [((66.12,-85.31,z+6.12),(69,-81.2,z+1),SODIUM),
                      ((81.5,-85.3,z+6),(79,-81,z+1),TEAL)]:
        lamp_head(k,p,aim,col,15,.78)


def fixtures(k):
    # Two high masts with maintenance baskets, at different elevations and orientations.
    for x,y,h,targets in [
        (58.65,-34.8,15.5,[(43,-12,8),(72,-26,4)]),
        (90.3,18.6,20.3,[(77,22,4),(98,8,9),(104,4,12)]),
    ]:
        zz=ground(x,y)
        if zz is None:continue
        pedestal(k,(x,y,zz),(2.85,2.85),.54)
        k.tower((x,y),zz+.9,zz+h,1.87,.98,DARK,4,.22)
        k.box((x,y,zz+h+.12),(3.20,2.45,.32),'steel_rust')
        k.ladder((x-.62,y+.89,zz+1.05),(x-.62,y+.89,zz+h+.21),.6)
        for i,target in enumerate(targets):
            lamp_head(k,(x+(i-1)*.91,y-.44,zz+h+.78),target,
                      SODIUM if (x>80 and i==1) else TEAL,19,.88)
    for x,y,h,col in [(32.9,7.9,4.35,SODIUM),(48.95,27.1,5.3,TEAL),(51.36,32,3.55,TEAL),
                      (54.7,-23.6,4.3,SODIUM),(67.93,-37.94,4.7,TEAL),(87.4,-30.6,3.9,TEAL),
                      (79.8,-13.4,4.21,SODIUM),(90.5,-3.3,4.8,TEAL),(88.36,25.9,3.86,SODIUM),
                      (98.7,21.9,4.7,TEAL),(61.3,17.5,3.55,SODIUM),(86.2,-81.55,4.2,TEAL)]:
        zz=ground(x,y)
        if zz is not None:k.lamp((x,y,zz+.18),h,col=col,r=12.5,power=.68)
    # Elevated wash-water and return pipes rise above service crossings.
    paths=[([(48.8,9.4,2.1),(48.8,6.8,2.1),(52.15,6.8,2.1)],.37,'steel_rust'),
           ([(61.9,11.4,3.9),(63.1,11.4,3.9),(63.1,7.8,3.9),(79.5,7.8,3.9),(79.5,8.85,3.9)],.40,'steel'),
           ([(83.0,5.80,2.85),(88.5,5.8,2.85),(88.5,11.2,2.85),(92.35,11.2,2.85)],.39,'steel_rust'),
           ([(60.1,30,2.05),(63.0,30,2.05),(63.0,33.85,2.05),(66.34,33.85,2.05)],.32,FADED_BLUE)]
    for ps,rad,mat in paths:
        k.tube(ps,rad,mat)
        for p,q in zip(ps,ps[1:]):
            p1,q1=vec(p),vec(q)
            mid=(p1+q1)*.5
            if (q1-p1).length>2.9:
                k.box((mid.x,mid.y,.5),(1.08,1.12,1.),'conc_dark')
                k.beam((mid.x,mid.y,.86),mid-Z*rad,.23,.32,DARK)
                along=(q1-p1).normalized()
                k.pipe(mid-along*.12,mid+along*.12,rad*1.21,'metal_grey',10)


def build(out,log):
    k=Kit('plant',79)
    mitt(k)
    grizzly(k)
    jig(k)
    conveyor(k,'cv1',CV1,3.35,3.2)
    conveyor(k,'cv2',CV2,3.05,3.05)
    conveyor(k,'cv3',CV3,3.22,3.35)
    updraft(k)
    buffer(k)
    thickener(k)
    silos(k)
    control(k)
    substation(k)
    pump_shop(k)
    dry_yard(k)
    fixtures(k)
    k.data['gates']={
        'jig_gate_door':{'axis':three((0,0,1)),'travel':5.6},
        'bin_gate_door':{'axis':three((1,0,0)),'travel':5.0}
    }
    k.finalize(out,log)
