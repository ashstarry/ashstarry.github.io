"""The south shift: a dismantled freighter, the listening bank and the old casting yard."""
import math
from mathutils import Vector

from lib.ground import G
from lib.kit import Kit, Z, circle
from lib.layout import PIT_C

V = Vector
WARM = (1.0, .49, .19)
COOL = (.59, .81, .83)
RED = (1., .095, .045)
TAU = math.tau


def xy_rotate(x, y, angle):
    a = math.radians(angle)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def clipped_pad(k, cx, cy, sx, sy, angle=0, bevel=1.2, mat='conc_dark', clearance=.22):
    """Variable-depth bedrock footing with one level working surface."""
    a, b = sx / 2, sy / 2
    corners = [(-a+bevel,-b),(a-bevel,-b),(a,-b+bevel),(a,b-bevel),
               (a-bevel,b),(-a+bevel,b),(-a,b-bevel),(-a,-b+bevel)]
    pts = [(cx+u,cy+v) for u,v in (xy_rotate(x,y,angle) for x,y in corners)]
    heights = [G.z(x,y) for x,y in pts] + [G.z(cx,cy)]
    if min(heights) < -9000:
        raise ValueError(f'unsupported foundation {cx}, {cy}')
    top = max(heights)+clearance
    k.prism(pts,min(heights)-.55,top,mat)
    return top


def small_flood(k, pos, normal, color=COOL, radius=19, power=1.1):
    """Hood projects past the lamp glass; it stays visibly hooded when seen in silhouette."""
    p, n = V(pos), V(normal).normalized()
    right = n.cross(Z)
    if right.length_squared < .001:
        right = V((1,0,0))
    right.normalize()
    up = right.cross(n)
    k.beam(p-.52*n, p+.02*n, 1.05, .78,'metal_dark')
    k.face([p+.12*n+right*x+up*y for x,y in ((-.43,-.26),(-.43,.26),(.43,.26),(.43,-.26))],
        'emit_cool' if color==COOL else 'emit_sodium')
    k.beam(p-.3*n+up*.42, p+.49*n+up*.42,1.22,.13,'metal_green')
    k.light(p+ .3*n,color,radius,power,'flood')


def south_wreck(k):
    """The dead vessel stays on its launch cradles. Port shell and upper deck are being peeled off."""
    angle = -10.3
    x0,y0 = -41.5,-189.0
    # v is starboard (in this yard north), h is above the keel.
    def pos(s,v,h):
        # A bow half yawed and rolled on its blocking after the centre was broken.
        if s > 1:
            a = math.radians(3.)
            ss=(s-3)*math.cos(a)-v*math.sin(a)+3
            vv=(s-3)*math.sin(a)+v*math.cos(a)+1.9
            bank=.065
            zz=-7.95+.014*s
        else:
            ss=s
            vv=v
            bank=-.09
            zz=-8.55+.012*s
        wx,wy=xy_rotate(ss,vv,angle)
        return V((x0+wx,y0+wy,zz+h+v*bank))
    profile=[(-.84,.88),(-1,.60),(-.88,.30),(-.48,.07),(-.29,0),(.43,0),
             (.88,.24),(1,.60),(.83,.92),(.28,1),(-.48,.98)]
    # (chainage, half-beam, height). The last part of the bow closes to a near-vertical knife edge.
    aft=[(-75,7.2,8.6),(-68,10.6,10.2),(-58,11.3,12.2),(-44,11.95,13.4),
         (-34,11.95,13.4),(-24,12,13.3),(-15,11.8,13),(-8.0,11.6,12.8)]
    fore=[(6,11.8,13.3),(14,12,13.4),(24,12.2,13.5),(37,12,13.8),(46,11.65,14.25),
          (56,9.5,15.6),(66,5.8,16.2),(73,2.15,16.8),(77,.44,16.9)]
    ends_a=[2.6,-.8,-1.5,2.9,5.1,3.9,1.3,-1.2,-4.6,-2.2,1.5]
    ends_b=[1.5,3.8,-1.9,-3.0,.2,-1.5,2.8,3.7,5.8,2.1,.3]
    def shape(station,end=None):
        s,w,h=station
        return [pos(s+(end[j] if end else 0.),v*w,t*h) for j,(v,t) in enumerate(profile)]
    def rib(st):
        # Rolled transverse frames have visible flanges; the middle of each hold is clear.
        s,w,h=st
        outer=shape(st)
        inner=[pos(s,v*(w-.58),.62+t*(h-1.14)) for v,t in profile]
        shift=pos(s+.36,0,0)-pos(s-.36,0,0)
        shift=shift.normalized()*.40
        for j in range(len(outer)):
            q=(j+1)%len(outer)
            if j in (8,9,10) and (-35<s< -7 or 6<s<52):
                continue
            k.face([outer[j]-shift,outer[q]-shift,inner[q]-shift,inner[j]-shift],'steel_rust')
            k.face([outer[j]+shift,inner[j]+shift,inner[q]+shift,outer[q]+shift],'hull_rust')
            k.face([outer[j]-shift,outer[j]+shift,outer[q]+shift,outer[q]-shift],'steel_dark')
            k.face([inner[j]-shift,inner[q]-shift,inner[q]+shift,inner[j]+shift],'metal_grey')
            # The front dismantling cut exposes the broadened inner edge of each rib.
            if j in (0,1,2,6,7):
                k.beam(inner[j],inner[q],1.45,.27,'steel_rust')

    def skin(a,b,side,paint,thickness=.12):
        i=(side+1)%len(profile)
        verts=[a[side],a[i],b[i],b[side]]
        normal=(verts[1]-verts[0]).cross(verts[3]-verts[0]).normalized()
        if normal.length_squared<.1:
            return
        inside=[p-normal*thickness for p in verts]
        k.face(verts,paint)
        k.face(list(reversed(inside)),'steel_rust')
        for j in (0,2):
            k.face([verts[j],inside[j],inside[(j+1)%4],verts[(j+1)%4]],'hull_rust')

    k.part()
    for half,stations in enumerate((aft,fore)):
        rings=[shape(st,ends_a if half==0 and i==len(stations)-1 else
                        ends_b if half==1 and i==0 else None) for i,st in enumerate(stations)]
        for st in stations[1:-1]:rib(st)
        count=len(stations)-1
        for i in range(count):
            for j in range(len(profile)):
                # Deep side plating remains on the back and keel. Large connected patches are missing.
                intact=(j in (2,3,4,5,6,7))
                if half==0:
                    intact |= i in (0,1) or (i==2 and j not in (9,10)) or (j==1 and i in (3,6)) or (j==8 and i<4)
                    if i==count-1 and j in (2,6,7):intact=j!=6
                else:
                    intact |= i>=5 or (j==1 and i in (0,3,4)) or (j in (0,8) and i==4)
                if intact:
                    k.part()
                    mat=('hull_rust' if j in (1,2,3,4,5) or ((i*5+j+half*7)%11==1)
                         else 'hull_white' if j==8 and i in (2,5,6) else 'hull_grey')
                    skin(rings[i],rings[i+1],j,mat)
        if not half:k.face(list(reversed(rings[0])),'hull_dark')
        else:k.face(rings[-1],'hull_rust')
        start,end=(stations[0][0]+1,stations[-1][0]-1)
        # Offset stringers, double bottom, deck girder, utility runs and partial inner decks.
        for v,h in [(-4.0,1.9),(3.1,2.2),(7.9,4.8),(8.3,7.2)]:
            stop=end if not half else min(end,56)
            k.beam(pos(start,v,h),pos(stop,v,h),.62,.9,'steel_rust')
        for v in (-1.3,.8):
            k.pipe(pos(start+1,v,3.15),pos(end-9,v,3.15),.28,'metal_teal',8)
        for u1,u2 in ([(-58,-46),(-31,-23)] if not half else [(15,23),(36,45)]):
            k.beam(pos(u1,2.1,4.9),pos(u2,2.1,4.9),12.0,.60,'hull_rust')
            k.beam(pos(u1,-1.0,4.35),pos(u2,-1.0,4.35),.56,.84,'steel_dark')
            k.railing(pos(u1,-3.3,5.18),pos(u2,-3.3,5.18),'steel_rust')
        # Late-period shell patch plates peel and curl back from the guillotine cut.
        edge=rings[-1] if not half else rings[0]
        for j in (0,2,6,8):
            p=edge[j];q=edge[(j+1)%len(edge)];d=(q-p)
            mid=p+d*.52
            tear=mid+V(((-1 if half else 1)*(1.3+.4*(j%3)),-1.4,.48))
            triangle=[p,mid+.1*Z,tear]
            k.face(triangle,'hull_rust');k.face(list(reversed(triangle)),'steel_rust')
    # Fractured pressure bulkheads: a rectangular access opening is still visible
    # right through the aft section; the bow has a partially dismantled off-centre doorway.
    for s,v0,sill,head,w,h in [(-13.7,-1.7,3.25,8.7,10.1,11.),(16.8,2.5,2.65,8.1,10.4,10.7)]:
        span=3.28 if s<0 else 2.72
        left,right=v0-span,v0+span
        def plate(a,b,z1,z2,paint,t=.38):
            q=[pos(s,a,z1),pos(s,b,z1),pos(s,b,z2),pos(s,a,z2)]
            off=(pos(s+.1,0,0)-pos(s-.1,0,0)).normalized()*t
            k.face(q,paint);k.face([p-off for p in reversed(q)],'steel_rust')
            for j in range(4):k.face([q[j],q[j]-off,q[(j+1)%4]-off,q[(j+1)%4]],'hull_rust')
        k.part();plate(-w*.87,w*.87,2.52,sill,'hull_rust')
        plate(-w*.88,left,sill,h if s<0 else h*.83,'hull_rust')
        plate(right,w*.88,sill,h,'hull_grey')
        plate(left,right,head,h,'hull_grey')
        for v in [left-.24,right+.24]:
            k.beam(pos(s+.12,v,sill),pos(s+.12,v,head+.45),.71,.55,'steel_dark')
        k.beam(pos(s+.12,left-.45,head+.2),pos(s+.12,right+.45,head+.2),.72,.63,'steel_rust')
        # A loose burst-pipe, cut fibre bundle, and part of a chained lifting davit.
        p1=pos(s,7.1,h-1.04);p2=pos(s+(3.5 if s<0 else -5.5),7.72,h-1.02);p3=p2+V((-.45,-.78,-1.24))
        k.tube([p1,p2,p3],.47,'metal_teal')
        k.cable(pos(s,6,h),pos(s+(5.2 if s<0 else -4.1),4.4,5.5),.95,.13,'rubber',7)
    for s in [-30.7,29.2]:
        # Bare transverse frames survived where shell, hatches, and coamings were cut away.
        pts=shape((s,11.64,12.8))
        for j in (0,1,2,3,4,5,6,7,8):k.beam(pts[j],pts[(j+1)%len(pts)],.66,.69,'hull_rust')
        k.beam(pts[0],pts[8],.64,.52,'steel_dark')
    # The double-bottom cells are hollow all the way through. Worn cut webs expose
    # the thickness of a spar and its internal floors at the two facing fractures.
    def broken_spar(start, end, center_v, sill, width, depth, tears):
        towards = 1 if end > start else -1
        def section(s, inset, broken=False):
            w = width*.5-inset
            h = depth*.5-inset
            shoulder = min(w,h)*.24
            loop = [(-w+shoulder,-h),(w-shoulder,-h),(w,-h+shoulder),(w,h-shoulder),
                    (w-shoulder,h),(-w+shoulder,h),(-w,h-shoulder),(-w,-h+shoulder)]
            return [pos(s+(tears[j] if broken else 0),center_v+v,sill+h0+depth*.5)
                    for j,(v,h0) in enumerate(loop)]
        outer=section(end,0,True);inner=section(end,.22,True)
        outer_back=section(start,0);inner_back=section(start,.22)
        for j in range(8):
            i=(j+1)%8
            surfaces=[([outer_back[j],outer_back[i],outer[i],outer[j]],'hull_rust'),
                      ([inner[j],inner[i],inner_back[i],inner_back[j]],'metal_dark'),
                      ([outer[j],outer[i],inner[i],inner[j]],'steel' if j in (3,4,6) else 'steel_rust')]
            for points,mat in surfaces:k.face(points if towards>0 else list(reversed(points)),mat)
        # Ship floors have lightening holes. A cross web recessed in each open mouth
        # leaves two dark passages either side, visible from the working face.
        web=end-towards*1.75
        for o in [-.33,.28]:
            v=center_v+width*o
            k.beam(pos(web,v,sill+.16),pos(web,v,sill+depth-.14),.22,.31,'steel_rust')
            k.beam(pos(web-.41,v,sill+depth-.3),pos(web+.46,v,sill+depth-.3),.37,.23,'metal_grey')
        for v in [-.34,.32]:
            k.beam(pos(start,center_v+v*width,sill+depth+.05),
                   pos(end-towards*.47,center_v+v*width,sill+depth+.05),.17,.15,'steel_dark')
    for specs in [(-22,-4.1,-2.25,3.1,4.15,2.57,(-.5,.75,.38,-.2,.82,.44,-.72,-.35)),
                  (-21,-6.7,2.48,3.25,3.72,2.0,(-.4,.36,.95,.24,-.65,-.25,.14,-.7)),
                  (25,7.2,-2.1,3.0,4.20,2.68,(.76,.13,-.48,.29,-.91,.21,.46,.96)),
                  (25,9.4,2.41,3.25,3.61,2.10,(.75,-.23,-.65,.17,.9,.22,.58,-.22))]:
        k.part();broken_spar(*specs)
    # Forked knees at the sawn ribs replace the unbroken rectangular section
    # at the joint. The broad flange faces catch grazing light around each opening.
    for s,lean in [(-24,1.),(-8.5,.66),(7.1,-.94),(23,-.8)]:
        k.part()
        for side in [-1,1]:
            a=pos(s,side*9.62,3.85);b=pos(s+lean*.7,side*11.42,7.4);c=pos(s+lean,side*10.05,11.3)
            for u,v in [(a,b),(b,c)]:
                k.beam(u,v,.65,.77,'hull_rust')
                k.beam(u+V((-.13,side*.24,.02)),v+V((-.13,side*.24,.02)),1.28,.22,'metal_grey')
            for hand in [-1,1]:
                points=[pos(s+hand*.18,side*10.72,6.05),pos(s+hand*2.0,side*10.6,6.18),
                        pos(s+hand*.56,side*11.25,7.87)]
                k.face(points,'steel_rust');k.face(list(reversed(points)),'hull_rust')
    # The removed side belt peeled back from its inner liner; the two sheets are
    # joined by short stools, so the visible fracture has relief even at a distance.
    for s0,s1,v,h in [(-32,-17.1,-11.1,6.2),(10,24.5,-11.08,7.3)]:
        k.part()
        points=[pos(s0,v,h),pos(s1-.3,v-.34,h+.45),pos(s1+1.45,v-.75,h+2.17),
                pos(s1-2.32,v-.85,h+2.91),pos(s0+2.5,v-.22,h+3.65),pos(s0,v,h+3.38)]
        inner=[p+V((.1,.24,-.04)) for p in points]
        k.face(points,'hull_grey');k.face(list(reversed(inner)),'hull_rust')
        for j,p in enumerate(points):
            i=(j+1)%len(points);k.face([p,inner[j],inner[i],points[i]],'steel_rust')
        for s in [s0+2,s1-2.8]:
            k.beam(pos(s,v+.02,h+.85),pos(s,v+1.54,h+1.29),.54,.48,'steel_dark')
            k.beam(pos(s,v-.13,h+2.05),pos(s,v+1.68,h+2.55),.52,.3,'steel_rust')
    # The port service crane is stripped to its jib, gearbox and sheave housing.
    base=pos(-48,6.0,11.7);mast=base+V((-.6,.6,4.9));outboard=pos(-36,-1.2,17.0)
    k.cyl(base+Z*.19,1.95,.7,'steel_dark',12)
    k.beam(base+Z*.3,mast,1.55,1.45,'metal_green')
    k.truss(mast,outboard,1.48,1.55,'steel_rust',4,.24)
    k.beam(mast-Z*1.4,outboard+Z*.19,.25,'steel')
    k.cable(outboard,outboard-Z*2.82,.12,.09,'rubber',4)
    k.box(base+V((-1.8,-.5,1.2)),(2.9,2.4,1.8),'metal_grey',angle)
    k.light(base+Z*2.3,WARM,13,.43,'lamp')
    # Remaining stern blast-bell pair and angular aft generator deck.
    for v,rr in [(-3.5,2.45),(3.1,2.12)]:
        k.part()
        c=pos(-73.8,v,5.25);n=(pos(-75,v,5.25)-c).normalized()
        k.pipe(c,c+n*4.8,rr,'hull_dark',16)
        k.torus(c+n*4.9,rr,.33,'steel_rust',18,6,n)
        k.torus(c+n*5.15,rr*.65,.22,'steel_dark',16,5,n)
        for i in range(4):
            a=TAU*i/4+.31
            t=V((0,math.cos(a),math.sin(a)))
            k.beam(c+n*2.1+t*(rr+.2),c+n*4.7+t*rr,.28,'hull_grey')
    deck=pos(-59,1.8,11.1)
    k.box(deck,(16.2,9.0,3.1),'hull_dark',(0,-3,angle))
    k.box(deck+V((-.2,.2,2.35)),(9.1,6.3,2.8),'hull_grey',(0,-3,angle))
    for j in [-2.6,-.6,1.35]:
        k.box(pos(-59+j,-1.45,13.65),(1.52,.25,.70),'glass',angle)
    k.tube([pos(-61,4,13.7),pos(-61,4,17.2),pos(-65,4.5,17.7)],.46,'steel_rust')
    # A service trunk remains bolted to the starboard wall.
    k.tube([pos(11,9.5,8.3),pos(33,9.7,8.7),pos(47,8.9,8.9),pos(50,7.5,8.1)],.45,'metal_green',10)
    # Steel and concrete cribbing under both hull sections, supported even where the apron undulates.
    for s,span in [(-65,7),(-42,8),(-18,8),(12,8),(40,8),(61,5)]:
        for v in [-span*.62,span*.62]:
            p=pos(s,v,1.8);g=G.z(p.x,p.y);k.part()
            k.box((p.x,p.y,(g+p.z)/2),(3.1,2.4,max(.55,p.z-g+.3)),'conc_warm',angle)
            k.box(p+Z*.20,(3.23,2.67,.6),'steel_dark',angle)
        k.beam(pos(s,-span,2.0),pos(s,span,2.0),1.75,1.0,'steel_rust')
    # A guillotine at the opening, scaffolds, hose reels and arms sit outside the torn hull.
    for num,(s,v) in enumerate([(-37,-10.4),(-8,-8.3),(26,-10.5)]):
        target=pos(s,v,8.8 if num!=1 else 6.5)
        a=pos(s-3.8,v-2.0,0);b=pos(s+4.7,v-2.0,0);ground=G.z(a.x,a.y)
        deckh=max(ground+2.9,target.z-2.85)
        a.z=deckh;b.z=deckh;k.part()
        k.catwalk(a,b,2.65,'steel_rust')
        for f in [0,.53,1]:
            for side in [-1,1]:
                p=a.lerp(b,f)+V((0,.99*side,0));g=G.z(p.x,p.y)
                k.beam((p.x,p.y,g-.1),p,.21,'steel_dark')
                if f!=1:
                    q=p+(b-a)*.41;k.beam(p-Z*.4,(q.x,q.y,g+.45),.15,'metal_grey')
        k.ladder((a.x,a.y-.8,ground),(a.x,a.y-.8,deckh),.7)
        base=b-Z*.06;tip=target+V((-.18,-.3,.16))
        elbow=base*.49+tip*.51+Z*2.05
        k.pipe(base+Z*.3,elbow,.32,'metal_yellow');k.beam(elbow,tip,.36,'hull_white')
        k.pipe(tip,tip+(target-tip)*1.2,.13,'steel')
        k.cable(base+Z*.4,elbow,.48,.10,'rubber')
        k.marker('wreck_cut_'+str(num),target);small_flood(k,a+Z*2.35,(.1,.8,-.4),WARM,19,.86)
        k.beam(a,a+Z*2.44,.12,'metal_grey')
    # A shed on the far side shelters the mobile cutting-gas manifold.
    for s,v in [(-56,12),(18,13),(53,10)]:
        p=pos(s,v,0);pad=clipped_pad(k,p.x,p.y,5,3.5,angle,.4)
        k.box((p.x,p.y,pad+1.55),(4.35,3,3.10),'metal_green',angle)
        k.box((p.x,p.y-.34,pad+3.4),(5.3,4.1,.46),'hull_grey',angle)
        k.lamp((p.x+1.9,p.y-2,pad),3.6,col=WARM,r=16,power=.72)
    for s,v in [(-64,-10.7),(-39,11),(-10,11.8),(8,-12.3),(32,12),(62,-7)]:
        p=pos(s,v,8);k.light(p,WARM if s<0 else COOL,13.5,.42,'window')
    k.marker('wreck_spine',pos(-8,0,6))


def receivers(k):
    for i,(cx,cy,rad,offset) in enumerate([(-98,-97,10.7,0.),(-66,-98,10.2,-1.1),(-36,-99,9.15,1.4)]):
        k.part()
        z=clipped_pad(k,cx,cy,11.7,9.8,9-13*i)
        k.lathe((cx,cy,z),[(0,3.55),(.9,3.75),(2.1,3.57),(2.6,2.83)],'conc',14)
        k.cyl((cx,cy,z+2.77),2.8,.5,'steel_rust',16)
        hub=V((cx,cy,z+11.5+offset))
        aim=V((PIT_C[0]-cx,PIT_C[1]-cy,-48-offset*5)).normalized()
        right=V((aim.y,-aim.x,0)).normalized()
        up=aim.cross(right)
        back=hub-aim*2.5
        for side in [-1,1]:
            p=back+right*(2.15*side)
            a=V((cx,cy,z+2.8))+right*2.15*side
            k.beam(a-aim*.9,p,.98,1.33,'metal_green')
            k.beam(a+aim*.9,p,.62,.85,'steel_rust')
        k.pipe(back-right*3.2,back+right*3.2,1.04,'hull_grey',14)
        k.beam(back,hub+aim*.3,2.7,2.1,'metal_dark')
        def bowl(r,a):
            return hub+right*(r*math.cos(a))+up*(r*math.sin(a))+aim*(r*r/(3.22*rad))
        rings=[.12*rad,.51*rad,.80*rad,rad]
        panels=20 if i!=1 else 18
        for j in range(panels):
            a=TAU*j/panels;b=TAU*(j+1)/panels;k.part()
            for tier,(r0,r1) in enumerate(zip(rings,rings[1:])):
                # Small joints at panel seams reveal the radial armature.
                da=.0025 if tier>0 else .0035
                p=[bowl(r0,a+da),bowl(r1,a+da),bowl(r1,b-da),bowl(r0,b-da)]
                shade='hull_white' if (i+j*3+tier*7)%17 not in (2,7) else 'hull_grey'
                k.face(p,shade);k.face([p0-aim*.15 for p0 in reversed(p)],'hull_grey')
            k.beam(bowl(rad,a),bowl(rad,b),.29,.23,'steel_dark')
            if j%2==i%2:
                k.beam(back-aim*.35,bowl(rad*.55,a)-aim*.28,.34,.55,'steel_dark')
                k.beam(bowl(rad*.52,a)-aim*.34,bowl(rad*.96,a)-aim*.2,.22,.33,'steel_rust')
                k.beam(bowl(rad*.55,a)-aim*.32,bowl(rad*.83,b)-aim*.30,.16,.23,'steel_rust')
        focus=hub+aim*(rad*.82)
        for a in [0,2.12,4.12]:
            k.pipe(bowl(rad*.88,a),focus,.16,'steel_dark',7)
        k.pipe(focus-aim*.38,focus+aim*.40,.56,'metal_teal',10)
        k.pipe(hub-aim*.25,hub+aim*.22,rad*.13,'metal_grey',12)
        k.ladder((cx-2,cy-1.6,z+1),(cx-2,cy-1.6,z+7.8),.72)
        k.catwalk((cx-3.2,cy-2.0,z+5.9),(cx+2.7,cy-2.0,z+5.9),1.2)
        k.lamp((cx+3.8,cy-3.8,z),4.15,col=COOL,r=13,power=.65)
        k.light(back,WARM,13,.45,'lamp')
        k.marker('listen_'+str(i),hub)
        if i<2:
            k.cable((cx+2.7,cy-1.1,z+4.1),(cx+21,cy-.6,G.z(cx+21,cy-.6)+3.5),
                    1.8,.10,'rubber',9)
    cx,cy=-80,-87
    z=clipped_pad(k,cx,cy,11.5,6.8,-9,.6)
    k.box((cx,cy,z+2.05),(10.9,6.2,4.1),'conc_warm',-9)
    k.box((cx,cy,z+4.28),(11.8,7.3,.52),'metal_green',-9)
    k.box((cx+2.5,cy-3.35,z+1.55),(2,.24,3.1),'metal_green',-9)
    k.box((cx-1,cy-2.98,z+2.55),(2.6,.24,.9),'glass_warm',-9)
    k.lamp((cx+4.8,cy-3.8,z),3.5,col=WARM,r=14,power=.95)

def old_derrick(k):
    # A braced headframe built over an abandoned inclined shaft, west of the receivers.
    cx,cy=-126,-85
    zz=clipped_pad(k,cx,cy,10.8,8.2,-11)
    eastern=V((cx+1,cy+1,zz+24.2));west=V((cx-4.7,cy+1.4,zz+20.4))
    k.part();k.tower((cx+.7,cy+.6),zz+.3,zz+22.6,6.8,3.55,'hull_rust',4,.64)
    for side in (-1,1):
        foot=V((cx-6.3,cy+side*3.75,zz+.18))
        k.box(foot+Z*.4,(2.4,2.4,.85),'conc_warm')
        k.beam(foot,eastern+V((0,side*2,0)),.78,1.12,'steel_rust')
        k.beam(foot+Z*.45,west+V((0,side*1.55,0)),.49,.59,'steel_dark')
    k.box((cx+.65,cy+.6,zz+22.4),(5.5,5.55,.74),'metal_dark')
    for side in [-1,1]:
        p=eastern+V((0,side*1.15,0))
        k.torus(p,1.72,.33,'steel_dark',18,5,(0,1,0))
        k.pipe(p-V((0,.33,0)),p+V((0,.33,0)),.42,'steel',8)
        for a in range(3):
            f=V((math.cos(a*math.pi/3),0,math.sin(a*math.pi/3)))*1.53
            k.beam(p-f,p+f,.20,'hull_rust')
        k.cable(p+Z*1.7,(cx-11,cy+side*.9,zz+4.3),.5,.18,'steel_dark',8)
    k.lathe((cx+1.1,cy+.4,zz),[(0,2.2),(.8,2.25),(1.4,1.7)],'metal_dark',8)
    k.ladder((cx+1.75,cy-2.1,zz+1),(cx+1.75,cy-2.1,zz+20.7))
    k.railing((cx-2,cy-2.17,zz+22.76),(cx+3.5,cy-2.17,zz+22.76),'steel_rust')
    k.lamp((cx-1,cy+1.6,zz+22.8),2.45,'beacon',RED,16,.8)
    k.marker('old_headframe',eastern)
    # Hoist machinery: an open gear case and its winding drum with end brakes.
    k.part()
    ho=V((cx-10.3,cy,zz+2.6))
    k.box(ho-Z*1.36,(5.4,4.9,1.25),'conc')
    k.pipe(ho-V((0,2,0)),ho+V((0,2,0)),1.38,'steel_dark',12)
    for side in [-1,1]:k.pipe(ho+V((0,side*2,0)),ho+V((0,side*2.3,0)),1.65,'hull_rust',14)
    k.lamp((cx+4.3,cy-3.2,zz),3.85,col=WARM,r=16,power=.8)
    # Written-off undercarriages and buckled runway bogies are kept together inside the south-west yard.
    for i,(x,y,ang) in enumerate([(-132,-132,21),(-145,-118,-16),(-119,-140,-6)]):
        gr=G.z(x,y)
        k.part()
        sx=6.4 if i==1 else 8.6
        k.box((x,y,gr+1.25),(sx,3.4,1.22),'hull_rust',(0,6-i*2,ang))
        for off in [-sx*.32,sx*.32]:
            a,b=xy_rotate(off,0,ang)
            for side in [-1,1]:
                e,f=xy_rotate(0,side*2.2,ang);p=V((x+a+e,y+b+f,gr+1.45))
                axis=V((*xy_rotate(0,1,ang),0))
                k.torus(p,1.27,.38,'rubber',14,6,axis)
                k.pipe(p-axis*.24,p+axis*.24,.61,'metal_grey',8)
        if i!=1:
            k.truss((x-2.3,y,gr+2.1),(x+4.8,y+1.8,gr+6.1),1.55,1.8,'metal_yellow',3,.25)
        else:k.box((x-1,y,gr+2.3),(2.7,3.3,1.9),'metal_blue',ang)
    for x,y,r,ang in [(-146,-126,1.5,8),(-143,-129,2.0,-18),(-116,-134,1.3,11),(-134,-142,2.1,10)]:
        g=G.z(x,y);k.torus((x,y,g+.49),r,.48,'rubber',14,6,(.13*math.sin(ang),.15,1))
    for x,y,ang in [(-120,-134,12),(-131,-143,28),(-142,-137,-10),(-110,-139,41)]:
        g=G.z(x,y);k.part()
        for j in range(3):
            k.box((x+.23*j,y-.17*j,g+.24+j*.37),(5.8-j*.25,2.3,.28),'hull_rust' if j==0 else 'metal_grey',(0,1.7*j,ang+j*3))
    for x,y in [(-132,-126),(-124,-146),(-115,-130)]:k.lamp((x,y,G.z(x,y)),4.8,col=COOL,r=17,power=.7)


def foundry(k):
    """Hot-blast furnace, receiving ladle, the old crucible mount and casting beds."""
    fx,fy=41,-140
    z=clipped_pad(k,fx,fy,17,16,-5,2)
    k.part()
    k.lathe((fx,fy,z),[(0,6.8),(.85,7.1),(2.6,6.75),(3.8,4.15),
                        (7.2,4.35),(10.0,5.65),(14.5,5.85),(20.9,5.0),
                        (27.1,3.05),(29.1,2.95),(30.1,1.8)],'hull_rust',20)
    for h,r,height,mat in [(4.8,4.72,.98,'steel_dark'),(9.5,5.87,1.28,'metal_grey'),
                            (14.3,6.04,.52,'steel_dark'),(19.7,5.37,.48,'metal_grey'),
                            (27.3,3.62,1.05,'steel_dark')]:
        k.cyl((fx,fy,z+h),r,height,mat,20)
    # The bustle main feeds individual tuyere elbows near the hearth.
    k.torus((fx,fy,z+9.3),5.47,.88,'metal_dark',20,8)
    for a in (.34,1.12,2.52,3.79,4.64,5.57):
        u=V((math.cos(a),math.sin(a),0));p=V((fx,fy,z))+u*5.6
        k.tube([p+Z*9.1,p+u*.47+Z*7.25,p-u*1.13+Z*6.25],.55,'steel_rust')
        k.beam(p+u*.32+Z*7.35,p+u*.52+Z*8.4,.34,'metal_grey')
    # Main support columns and two maintenance balconies on the taphole face.
    for a in (.15,1.63,3.28,4.81):
        u=V((math.cos(a),math.sin(a),0));p=V((fx,fy,z))+u*6.35
        k.box(p+Z*.46,(2.35,2.35,.92),'conc_warm')
        k.beam(p+Z*.9,p-u*.95+Z*17.1,1.0,1.25,'steel_dark')
    for h,r in [(11.7,6.29),(23.0,4.56)]:
        pts=[]
        for i in range(11):
            a=math.radians(183+i*15)
            pts.append((fx+r*math.cos(a),fy+r*math.sin(a),z+h))
        for a,b in zip(pts,pts[1:]):
            k.beam(a,b,1.35,.29,'steel_dark')
            outer_a=V((fx+(a[0]-fx)*1.10,fy+(a[1]-fy)*1.10,a[2]+.12))
            outer_b=V((fx+(b[0]-fx)*1.10,fy+(b[1]-fy)*1.10,b[2]+.12))
            k.railing(outer_a,outer_b,'metal_yellow',1.02)
        small_flood(k,V(pts[4])+Z*1.4,(0,-.9,-.45),WARM,20,.75)
    k.ladder((fx-4.8,fy-3.25,z+1.3),(fx-4.8,fy-3.25,z+22.9))
    for a in [3.3,5.3]:
        u=V((math.cos(a),math.sin(a),0));p=V((fx,fy,z))
        k.tube([p+u*2.5+Z*26.5,p+u*3.85+Z*29.3,p+u*3.9+Z*33.1,
                p+u*2.5+V((-2,1,34.6)),p+V((-5.1,2.7,34.4))],.86,'steel_dark',10)
    # Offgas downcomer is an inclined industrial elbow running to the coarse dust catcher.
    tx,ty=30,-146
    tz=clipped_pad(k,tx,ty,6.4,6.4,-10,.65)
    k.lathe((tx,ty,tz),[(0,2.1),(.7,2.7),(3,2.4),(4.8,1.2),(7.0,2.75),
                         (16,2.75),(18,2.18),(19.2,1.1)],'metal_grey',16)
    k.tube([(fx-5.1,fy+2.7,z+34.4),(fx-7.5,fy+2.9,z+32.8),
            (tx,ty,tz+20.3),(tx,ty,tz+18.6)],1.05,'steel_rust',12)
    # One lower hot stove and its asymmetrically placed downpipe.
    sx,sy=33,-155
    sz=clipped_pad(k,sx,sy,6.9,7.1,8,.8)
    k.lathe((sx,sy,sz),[(0,2.2),(.7,2.94),(3,2.86),(16.8,2.86),(18.1,2.37),
                         (19,1.38),(19.3,.48)],'metal_red',16)
    k.tube([(sx+2.6,sy,sz+3.75),(sx+5.7,sy,sz+3.75),(fx-4.3,fy-3.2,z+8.85)],
           .76,'steel_dark',10)
    k.ladder((sx-1,sy-2.9,sz+.8),(sx-1,sy-2.9,sz+17.4))
    # Hot-metal runner with two scorched refractory cheeks, sloping into the induction throat.
    tap=V((49.5,-151.2,10.2))
    throat=V((fx+3.8,fy-4.2,z+9.6))
    bend=V((47.2,-146.8,10.4))
    k.tube([throat,bend,tap],.69,'steel_rust',10)
    for d in [-.63,.63]:
        k.beam(bend+V((d,0,.39)),tap+V((d,0,.12)),.36,.68,'conc_dark')
    k.pipe(tap-V((.33,-.22,.12)),tap+V((.08,-.02,.04)),.52,'emit_molten',10)
    k.marker('furnace_tap',tap,(.75,-.37,.64));k.light(throat,WARM,19,1.22)
    # The four magnetic pole shoes lie below the lowest possible edge of the molten ball.
    cx,cy=64,-158
    cb=clipped_pad(k,cx,cy,29.4,26.5,4,3.55)
    rc=V((cx,cy,0));centre=V((cx,cy,31));base=V((cx,cy,cb+2.45))
    k.marker('crucible',centre);k.marker('crucible_base',base)
    k.lathe((cx,cy,cb),[(0,4.55),(.5,5.0),(.95,4.16),(1.52,3.85),(2.05,4.25)],'metal_dark',20)
    k.torus((cx,cy,cb+2.3),3.48,.6,'steel_rust',20,6)
    k.cyl((cx,cy,cb+2.15),2.96,.3,'conc_dark',20)
    k.torus((cx,cy,cb+1.4),12.3,.56,'steel_rust',36,7)
    k.torus((cx,cy,12.65),13.5,.65,'metal_dark',32,8)
    k.torus((cx,cy,13.51),13.45,.25,'steel',32,6)
    for j,a in enumerate((.46,2.1,3.43,4.98)):
        u=V((math.cos(a),math.sin(a),0));side=V((-u.y,u.x,0));pole=rc+u*13.5+Z*13.0
        f=rc+u*12.2+Z*(cb+.3)
        k.part();k.box(f+Z*.73,(3.9,4,1.4),'conc',math.degrees(a))
        k.beam(f+Z*1.2,pole+u*.1,.96,1.55,'steel_dark')
        k.beam(f+side*1.85+Z*.65,pole-Z*1.4,.57,'steel_rust')
        k.beam(f-side*1.4+Z*.68,pole-Z*1.4,.52,'steel_rust')
        # Iron C-yoke and removable lamination pack in the old crucible ring.
        k.box(pole+Z*1.03,(3.32,3.1,2.05),'hull_dark',math.degrees(a))
        k.beam(pole+u*.58+Z*1.27,pole-u*.31+Z*3.67,1.9,2.35,'metal_teal')
        k.beam(pole-u*.31+Z*3.67,pole-u*1.65+Z*3.98,2.1,1.5,'steel')
        k.box(pole+u*1.8+Z*.78,(.23,2.55,.66),'metal_hazard',math.degrees(a))
        k.tube([f+u*1.5+Z*.4,f+u*1.5+Z*3.6,pole+u*1.4+Z*.76],.38,'steel_rust')
        k.light(f+Z*2.5,WARM,17,.55)
    k.collider((22,18,.8),(cx,cy,cb-.23),rot=4,tag='casting_bed')
    # A casting floor with actual mould cavities, pouring channels and a rail-mounted receiving ladle.
    for i,(bx,by,szx) in enumerate([(83,-165,16.5),(85,-159.3,12.8)]):
        bz=clipped_pad(k,bx,by,szx+1.6,4.5,0,.65)
        k.box((bx,by,bz+.43),(szx,3.65,.85),'conc_warm')
        for j in [-1,1]:
            k.box((bx,by+j*1.68,bz+1.04),(szx,.42,.47),'steel_rust')
        n=4 if i==0 else 3
        for j in range(n):
            xx=bx-szx*.5+1.35+(szx-2.7)*j/max(1,n-1)
            k.box((xx,by,bz+.89),(1.92,2.42,.12),'metal_dark')
            if (i,j) in ((0,1),(1,0)):
                k.box((xx,by,bz+.99),(1.55,2.07,.17),'hull_rust')
    for by in [-153.4,-150.9]:k.beam((78,by,cb+.72),(89,by,cb+.72),.28,.36,'steel')
    k.lathe((84,-152,cb+.73),[(0,1.86),(.9,1.71),(2.4,1.54),(3.75,2.44),(4.2,2.75)],'hull_rust',14)
    k.cyl((84,-152,cb+4.99),2.14,.14,'metal_dark',14)
    k.torus((84,-152,cb+5),2.42,.32,'steel',14,6)
    for yy in (-154.9,-149.1):k.pipe((84,yy,cb+3.25),(84,yy+(.48 if yy<-152 else -.48),cb+3.25),.63,'steel_dark')
    # Vessel shop is set back so the casting and sphere stay visible from the front.
    hx,hy=87,-137;hh=clipped_pad(k,hx,hy,18.2,10.4,-4)
    for xx in (-7.7,.6,7.8):
        for yy in (-3.9,3.9):
            k.beam((hx+xx,hy+yy,hh),(hx+xx,hy+yy,hh+7.2),.56,.72,'steel_dark')
        k.truss((hx+xx,hy-4.7,hh+6.5),(hx+xx,hy+4.7,hh+7.8),1.08,1.1,'steel_rust',2,.19)
    k.box((hx,hy,hh+7.6),(18.5,10.7,.49),'hull_grey',(7,0,0))
    k.box((hx,hy+4.1,hh+3.5),(16.3,.38,7.0),'metal_green')
    k.box((hx+7.9,hy+.8,hh+2.85),(.34,6.4,5.7),'hull_rust')
    k.box((hx-2.6,hy,hh+1.2),(7.2,2.4,2.4),'metal_dark')
    k.light((hx-3,hy-.9,hh+5.8),WARM,17,.95)
    # Vacuum plumbing, service canisters, and a gated room at the start of the metallurgical road.
    k.tube([(30,-147,tz+3),(28.7,-149,tz+3),(28.7,-155,sz+3),(30.3,-155,sz+3)],
           .32,'metal_teal')
    for p,col,r in [((49,-149),WARM,21),((37,-149),WARM,19),((28,-143),COOL,18),
                     ((69,-145),WARM,18),((81,-160),WARM,17),((92,-139),COOL,16),
                     ((78,-167),WARM,18),((50,-166),COOL,14)]:
        k.lamp((p[0],p[1],G.z(*p)),4.3,col=col,r=r,power=.8)
    k.lamp((fx+1,fy-.3,z+30.6),3.2,'beacon',RED,20,.77)


def flightline(k):
    cx,cy=121,-116;angle=-12.
    z=clipped_pad(k,cx,cy,35.5,28.2,angle,4.2,'conc',.34)
    ex,ey=xy_rotate(1,0,angle);dx,dy=xy_rotate(0,1,angle)
    def p(u,v,h=.025):return V((cx+ex*u+dx*v,cy+ey*u+dy*v,z+h))
    k.collider((32,24,.45),(cx,cy,z-.22),angle,tag='flight_apron')
    k.marker('shuttle_pad',p(0,0,.08),(ex,ey,0))
    k.marker('landing_field',p(0,0,.1))
    # Outriggers land inside four painted brackets. Concrete wear has opened a gap in the north box.
    for sx in [-1,1]:
        for sy in [-1,1]:
            a,b=(sx*12.45,sy*9.1)
            k.part()
            k.beam(p(a,b),p(a-sx*(3.9 if sy==1 else 5.1),b),.53,.065,'metal_white')
            k.beam(p(a,b),p(a,b-sy*3.25),.53,.065,'metal_white')
    # Incised brass perimeter, interrupted by the wheeled access cart approach.
    for i in [0,1,3,4,6,7,9,10]:
        u1=i*math.pi/6+.06;u2=u1+.28
        a=p(7.1*math.cos(u1),7.1*math.sin(u1));b=p(7.1*math.cos(u2),7.1*math.sin(u2))
        k.beam(a,b,.25,.06,'metal_yellow')
    for u,v in [(-14,-9.8),(-16,.5),(-12.6,10.3),(9.4,11.5),(14,-6.3),(1.4,-12)]:
        a=p(u,v,.15);k.cyl(a,.52,.32,'metal_dark',8)
        k.cyl(a+Z*.22,.34,.16,'emit_amber',8);k.light(a+Z*.3,WARM,7.7,.43,'lamp')
    sx,sy=107,-96
    h=clipped_pad(k,sx,sy,13.8,8.6,7)
    k.part();k.box((sx,sy,h+2.2),(12.6,7.8,4.4),'conc_warm',7)
    k.box((sx-.1,sy,h+4.76),(13.65,8.76,.78),'metal_grey',7)
    k.box((sx+1.9,sy-3.72,h+2.2),(4.8,.35,3.74),'metal_teal',7)
    k.box((sx-2.5,sy-3.82,h+2.9),(2.8,.24,1.05),'glass_warm',7)
    k.lamp((sx+4.2,sy-3.63,h),4.2,col=COOL,r=17,power=.88)
    k.tank(129,-91,G.z(129,-91),2.75,4.1,'metal_white')
    k.tube([(129,-93.7,G.z(129,-91)+1.6),(128,-96,G.z(129,-91)+1.6),
            (121,-98,G.z(121,-98)+1.3),(119,-99,G.z(119,-99)+1.3)],.34,'steel_rust')
    # Survey instruments follow the crater rim rather than flattening the anomaly into the landing slab.
    cx,cy,r=118,-150,7.3
    for j,a in enumerate((.21,.89,1.57,2.22,2.95,3.51,4.30,4.94,5.73)):
        u=V((math.cos(a),math.sin(a),0));x=cx+r*u.x;y=cy+r*u.y;gr=G.z(x,y)
        k.part();k.cyl((x,y,gr+.45),.62,.95,'conc_dark',7)
        k.beam((x,y,gr+.65),(x,y,gr+1.85),.22,'metal_grey')
        k.beam((x,y,gr+1.7),(x-u.x*.7,y-u.y*.7,gr+1.71),.35,.3,'metal_yellow')
        if j in (0,3,7):k.light((x,y,gr+1.81),RED,7.1,.50,'beacon')
        if j<8:
            aa=(.21,.89,1.57,2.22,2.95,3.51,4.30,4.94,5.73)[j+1]
            xx,yy=cx+r*math.cos(aa),cy+r*math.sin(aa)
            k.cable((x,y,gr+1.0),(xx,yy,G.z(xx,yy)+1.0),.5,.068,'rubber',5)


def standing_stones(k):
    # Each stone has a scarred crest, one clean polished face and a partly buried, offset lower block.
    cx,cy=-62,158
    angles=[.05,.62,1.55,2.10,2.72,3.32,4.17,4.87,5.57]
    heights=[9.5,7.6,11.8,15.3,8.4,13.0,6.5,11.1,8.9]
    for i in range(10):
        if i<9:
            a=angles[i];rad=15.2+(1.1 if i%3==0 else -.6);x=cx+rad*math.cos(a);y=cy+rad*.85*math.sin(a);h=heights[i]
        else:a=-.73;x,y=-18,150;h=17.5
        g=G.z(x,y);rot=math.degrees(a)+39;width=2.3+.075*h
        frame=[(-.65,-.50),(.57,-.52),(.72,.12),(.36,.53),(-.55,.49),(-.76,.17)]
        rings=[]
        for tier,scale,leanx,leany,hf in [(0,1.06,0,0,0),(1,1.0,-.02,.03,.33),(2,.86,.10,.11,.82),(3,.63,.15,.13,1.)]:
            ring=[]
            for j,(u,v) in enumerate(frame):
                rough=.06*math.sin(i*3+j*1.9+tier*2.2)
                wx,wy=xy_rotate((u*scale+leanx+rough)*width*1.75,(v*scale+leany)*width,rot)
                dz=(.18+(j==2)*.5+(.35 if j==1 else 0))*math.sin(j*1.65+i*.6) if tier==3 else rough*.4
                ring.append((x+wx,y+wy,g-.9+h*hf+dz))
            rings.append(ring)
        k.part();k.loft(rings,'relic')
        k.marker('standing_'+str(i),(x,y,g+h-.8))
        if i in (2,5,9):
            qx=x+3.4;qy=y-1.3;d=G.z(qx,qy)
            k.cyl((qx,qy,d+.34),.75,.68,'conc_warm',8)
            k.pipe((qx,qy,d+.65),(qx,qy,d+1.73),.16,'steel',7)
            k.box((qx-.34,qy,d+1.67),(1.10,.49,.47),'metal_teal',rot)
            k.light((qx,qy,d+1.79),RED,8.0,.37,'beacon')
    k.marker('relic_ring',(cx,cy,G.z(cx,cy)))


def turned(k, center, axis, profile, mat, segments=20, closed=True):
    """Axial section in (distance along spindle, outside radius), including open bores."""
    axis=V(axis).normalized()
    first=axis.cross(Z if abs(axis.z)<.94 else V((0,1,0))).normalized()
    second=axis.cross(first)
    rim=[first*math.cos(TAU*i/segments)+second*math.sin(TAU*i/segments) for i in range(segments)]
    k.loft([[center+axis*offset+direction*radius for direction in rim] for offset,radius in profile],
           mat,closed,True)


def axle_works(k):
    """Open rebuild bay. The two shoulders carry wheel loads above the greasing trench."""
    x,y,angle=60.,-108.,-6.
    ex=V((*xy_rotate(1,0,angle),0));ey=V((*xy_rotate(0,1,angle),0))
    center=V((x,y,0))
    def point(u,v,h=0):
        return center+ex*u+ey*v+Z*h
    # Cutting the rock mesh is unnecessary here: the old shops were built on fill.
    # Sample inside the floor as well as at its corners so rock cannot bleed through the pit.
    support=[point(u,v) for u in (-17,-10,-4,2,9,16) for v in (-9,-5,0,5,10)]
    grade=max(G.z(p.x,p.y) for p in support)+.25
    center.z=grade
    deck=3.3
    def slab(u0,u1,v0,v1,z0,z1,mat):
        k.box(point((u0+u1)*.5,(v0+v1)*.5,(z0+z1)*.5),(u1-u0,v1-v0,z1-z0),mat,angle)
    def p(xoff,yoff,h=0):
        return point(xoff,yoff,deck+h)
    k.part()
    foundation=[point(u,v) for u,v in [(-17,-7.9),(-15.4,-9.5),(13.8,-9.5),(16.7,-6.8),
                                         (16.7,9),(15.4,10),(-15,10),(-17,8)]]
    low=min(G.z(p0.x,p0.y) for p0 in foundation)-.4
    k.prism([(p0.x,p0.y) for p0 in foundation],low,grade,'conc_dark')
    slab(-16.7,15.1,-7.15,-2.65,.03,deck,'conc_warm')
    # The apron is hollow on the service side. Cast the cap and kick separately
    # so the drain manifold and the extraction grille sit in actual deep cutouts.
    slab(-16.7,15.1,-8.15,-7.15,.03,.48,'conc_dark')
    slab(-16.7,15.1,-8.15,-7.15,2.55,deck,'conc_warm')
    for a,b in [(-16.7,-11.8),(-7.45,6.9),(10.24,15.1)]:
        slab(a,b,-8.15,-7.15,.48,2.55,'conc_warm')
    for a,b in [(-11.8,-7.45),(6.9,10.24)]:
        slab(a+.04,b-.04,-7.24,-7.16,.53,2.50,'steel_dark')
        k.beam(point(a-.13,-8.28,2.52),point(b+.12,-8.28,2.52),.53,.23,'steel_rust')
    for u,r,h in [(-10.54,.51,1.45),(-8.7,.35,1.33)]:
        c=point(u,-7.28,h)
        turned(k,c,-ey,[(0,r*.78),(.33,r*.78),(.36,r),(.55,r),
                         (.56,r*.73),(1.10,r*.73),(1.12,r*.53),(.60,r*.53)],
               'steel_rust',14,False)
        k.pipe(c-ey*.59,c-ey*.62,r*.53,'metal_dark',12)
    for j in range(4):
        k.beam(point(6.99,-7.61,.74+j*.46),point(10.16,-7.61,.74+j*.46),.35,.18,'metal_grey')
    for u,w in [(-14.07,1.2),(-4.08,.78),(3.3,.90),(12.52,1.12)]:
        base=point(u,-9.09,.12); knee=point(u,-8.27,2.12)
        k.beam(base,knee,w,.85,'conc_dark')
    p1,p2=point(-5.90,-8.35,1.27),point(3.00,-8.35,1.27)
    k.pipe(p1,p2,.21,'metal_green',12)
    k.pipe(p2,p2+Z*.69,.21,'metal_green',12)
    k.pipe(p2+Z*.69,p2+Z*.69+ey*.43,.21,'steel',12)
    for q in [p1+ex*.12,p1+ex*2.93,p2-ex*.14]:
        k.pipe(q-ex*.10,q+ex*.10,.31,'steel_rust',12)
    slab(-16.6,15.6,2.65,9.45,.03,deck,'conc')
    slab(-16.55,-11.55,-2.65,2.65,.03,deck,'conc_warm')
    slab(12.9,15.1,-2.65,2.65,.03,deck,'conc')
    slab(-11.55,12.9,-2.64,2.64,.03,.14,'steel_dark')
    for v in [-2.69,2.69]:
        k.beam(p(-11.65,v,.04),p(13.,v,.04),.26,.29,'steel')
        k.beam(p(-11.55,v*.87,-1.57),p(8.75,v*.87,-1.57),.15,.18,'metal_teal')
        for u in [-10.8,-5.2,.05,5.9]:
            k.beam(p(u,v*.965,-3),p(u,v*.965,-.15),.29,.41,'steel_rust')
    # Pale concrete lip around a genuine 3.2-m recess. Catwalk ladders and a sump
    # stay below the axle, clear of the moving bogie path.
    k.stairs(point(6.55,-.65,.22),p(12.82,-.65,-.07),1.66)
    k.cyl(point(-8.1,.71,.23),.90,.17,'metal_dark',16)
    for t in [-.44,-.15,.15,.44]:
        k.beam(point(-8.7,.71+t,.34),point(-7.49,.71+t,.34),.11,.13,'steel_rust')
    k.railing(p(13.26,.0),p(13.26,2.62),'steel_dark')
    k.marker('wheel_service_pit',point(-.8,0,1.45),tuple(ex))
    for u0,u1,v0,v1 in [(-16.7,15.1,-8.15,-2.65),(-16.6,15.6,2.65,9.45),
                            (-16.55,-11.55,-2.65,2.65),(12.9,15.1,-2.65,2.65)]:
        k.collider((u1-u0,v1-v0,deck),point((u0+u1)/2,(v0+v1)/2,deck/2),
                   rot=angle,tag='axle_shop_deck')
    # The entrance rises from the road on a wedge instead of a sheer wall.
    far=point(-29,-.85)
    bottom=G.z(far.x,far.y)-grade+.14
    footprint=[(-29,-5.65,bottom),(-16.65,-5.15,deck),(-16.65,5.25,deck),(-29,4.25,bottom)]
    top=[point(*v) for v in footprint]
    k.face(top,'conc')
    for j,a in enumerate(top):
        b=top[(j+1)%4]; k.face([a,a-Z*(a.z-low+.45),b-Z*(b.z-low+.45),b],'conc_warm')
    for v in [-4.58,4.16]:
        k.beam(point(-27.8,v,bottom+.4),point(-16.75,v,deck+.1),.34,.27,'steel_rust')
    # Truck rear axle, laid across the two rim flanges. Tread has staggered
    # individual shoes; each hub has a shoulder, a planetary cover and wheel studs.
    axle_u=-5.5
    axle=p(axle_u,.0,2.52)
    k.part()
    turned(k,axle,ey,[(-4.65,.62),(-3.35,.61),(-2.7,.41),(-1.55,.52),(-.77,.9),
                      (.69,.93),(1.36,.56),(2.73,.41),(3.45,.62),(4.63,.62)],'hull_rust',16)
    k.sphere(axle+ex*.32,(1.23,1.15,.98),'metal_grey',16,8)
    turned(k,axle+ex*1.08,ex,[(-.46,.75),(.21,.63),(.53,.37),(.81,.55),(.95,.52)],'steel_dark',16)
    for sign in [-1,1]:
        k.part()
        c=axle+ey*(4.15*sign)
        turned(k,c,ey,[(-.76,1.16),(-.83,1.48),(-.77,1.89),(-.55,2.25),(-.34,2.37),
                       (.34,2.37),(.55,2.25),(.77,1.89),(.83,1.48),(.76,1.16),(-.76,1.16)],
               'rubber',28,False)
        for j in range(17):
            for half in [-1,1]:
                a=TAU*(j+.12*half)/17
                n=ex*math.cos(a)+Z*math.sin(a);t=-ex*math.sin(a)+Z*math.cos(a)
                foot=c+n*2.32+ey*(half*.3)
                k.beam(foot-t*.21-ey*.23,foot+t*.22+ey*.18,.24,.20,'rubber')
        axis=ey*sign
        turned(k,c,axis,[(-.62,1.06),(-.49,1.25),(-.3,1.12),(.37,1.11),
                          (.56,1.31),(.74,1.29),(.81,1.08),(.91,1.01)],'metal_yellow',24)
        turned(k,c,axis,[(.86,.67),(.99,.79),(1.10,.69),(1.19,.43)],'metal_dark',16)
        for j in range(8):
            a=TAU*j/8
            root=c+axis*.94+(ex*math.cos(a)+Z*math.sin(a))*.86
            k.pipe(root,root+axis*.11,.112,'steel',6)
        for bearing in [-.52,.52]:
            k.beam(p(axle_u+bearing*1.8,sign*2.10,-2.98),
                   axle+ex*bearing+ey*(sign*2.10)-Z*.26,.44,.51,'metal_green')
        k.beam(axle+ey*sign*1.64-Z*.46,axle+ey*sign*2.54-Z*.46,1.41,.48,'metal_grey')
    # Second remanufactured final drive, one bare bull gear and a stripped brake
    # pack on narrow trestles. This bay reads differently from another row of tyres.
    c=p(8.5,5.67,2.03);axis=(ey+ex*.14).normalized()
    k.part()
    turned(k,c,axis,[(-2.74,.29),(-2.32,.55),(-1.93,.38),(-1.4,.66),(-.89,.82),(-.35,.66),
                     (.92,.45),(1.31,.75),(1.60,.63),(2.29,.43),(2.71,.33)],'steel',18)
    for d in [-1.37,1.6]:
        q=c+axis*d
        k.box(q-Z*1.77,(2.72,1.25,.42),'metal_green',angle)
        for side in [-1,1]:
            k.beam(q+ex*side*.99-Z*1.62,q+ex*side*.41-Z*.34,.33,.48,'steel_rust')
    g=c-axis*1.94
    turned(k,g,axis,[(-.28,1.52),(.27,1.52),(.27,1.10),(-.28,1.10),(-.28,1.52)],
                                'steel_rust',24,False)
    for j in range(6):
        a=TAU*j/6+.18;n=(ex*math.cos(a)+Z*math.sin(a))
        k.beam(g+n*.35,g+n*1.32,.34,.29,'metal_grey')
    for j in range(18):
        a=TAU*j/18
        q=g+(ex*math.cos(a)+Z*math.sin(a))*1.52
        k.beam(q-axis*.28,q+axis*.28,.29,.31,'steel')
    for d in [.85,1.12,1.40]:
        turned(k,c+axis*d,axis,[(-.055,.99),(.055,.99)],'steel_dark',18)
    # A single long travelling beam serves the open south trench and the inlet at
    # the west end. Only the back bench is covered: the open roof reveals the work.
    for u in [-12.,11.5]:
        for v in [-6.8,8.2]:
            k.part();slab(u-.83,u+.83,v-.83,v+.83,deck,deck+.58,'conc_dark')
            k.beam(p(u,v,.57),p(u,v,7.9),.65,.80,'steel_dark')
            k.beam(p(u,v,5.91),p(u+(-1 if u>0 else 1)*2.3,v,7.94),.38,.44,'steel_rust')
    for v in [-6.8,8.2]:
        a=p(-14.5,v,8.01);b=p(14,v,8.01)
        k.beam(a,b,.39,1.01,'steel_rust');k.beam(a+Z*.53,b+Z*.53,.79,.18,'metal_grey')
    u=-4.71
    for v in [-6.8,8.2]:
        k.box(p(u,v,8.91),(3.30,1.06,.74),'metal_dark',angle)
    k.beam(p(u,-7.5,9.42),p(u,8.89,9.42),1.38,1.05,'metal_yellow')
    k.box(p(u,-.5,9.87),(1.75,2.86,1.08),'metal_green',angle)
    k.pipe(p(u,-.93,8.9),p(u,-.93,4.02),.08,'steel',6)
    k.pipe(p(u-.25,-.60,8.9),p(u-.25,-.60,4.05),.08,'steel_dark',6)
    k.torus(p(u-.11,-.76,3.83),.37,.12,'steel_rust',12,5,ex)
    # North wall, clipped roof sheets and the raised lantern above a single
    # workbench. Frames project beyond the weather skin at the east repair end.
    slab(-15.74,1.7,8.38,8.70,deck,deck+5.8,'conc_warm')
    for u in [-14.5,-5.9,2.2]:
        k.beam(p(u,8.54,.2),p(u,8.54,7.13),.37,.47,'steel_rust')
        k.truss(p(u,1.65,6.29),p(u,9.22,7.24),.76,.88,'metal_dark',2,.15)
    for a,b,h in [(-15.66,-7.55,6.64),(-7.32,2.95,7.05)]:
        points=[p(a,1.52,h-.48),p(b,1.52,h-.48),p(b,9.6,h+.43),p(a,9.6,h+.43)]
        k.face(points,'metal_teal');k.face([q-Z*.22 for q in reversed(points)],'metal_grey')
        k.beam(points[0],points[1],.38,.42,'steel_dark')
        k.beam(points[2],points[3],.29,.45,'steel_rust')
    for u in [-12.9,-9.3]:
        k.box(p(u,6.64,1.14),(2.48,1.51,2.28),'hull_grey',angle)
    k.box(p(-11.16,6.58,2.34),(6.56,1.9,.26),'steel_dark',angle)
    k.torus(p(-12.21,6.64,2.63),.54,.15,'steel_rust',15,6)
    k.box(p(-9.52,6.48,2.85),(.90,.94,.72),'metal_green',angle)
    small_flood(k,p(-4.6,3.55,6.2),(.18,-.8,-.48),WARM,14,.62)
    small_flood(k,p(11.38,-6.73,6.7),(-.67,.50,-.42),COOL,17,.81)


def salvage_davits(k):
    """Two independently founded scrap-transfer davits project over the southern void."""
    for receiving, foot, hook, wheel_z in [
        (False,(-70.,-204.4),(-67.,-232.,16.),41.),
        (True,(-11.5,-212.25),(-14.,-242.,19.),45.)
    ]:
        x,y=foot
        carry=V(hook)
        tip=V((carry.x,carry.y,wheel_z))
        fwd=V((tip.x-x,tip.y-y,0)).normalized()
        side=Z.cross(fwd)
        heading=math.degrees(math.atan2(fwd.y,fwd.x))
        anchor=clipped_pad(k,x,y,8.25,11.3,heading,.90,'conc_dark')
        base=V((x,y,anchor));top_height=wheel_z-(4.7 if receiving else 3.4)
        def local(forward,across,z):
            return V((x,y,z))+fwd*forward+side*across
        m='metal_green' if receiving else 'steel_rust'
        k.part()
        # A pair of narrow sheerlegs keeps the silhouette open above the hull;
        # the outriggers converge into one shaft bearing at the jib heel.
        heel_z=top_height-17.7
        for sign in [-1,1]:
            a=local(-2.92,sign*3.8,anchor+.83);b=local(2.77,sign*4.21,anchor+.83)
            q=local(.6,sign*1.71,heel_z)
            for root in [a,b]:
                k.box(root-Z*.26,(2.73,2.45,.94),'conc_warm',heading)
                k.box(root+Z*.28,(2.04,1.74,.26),'steel_dark',heading)
                for dx in [-.66,.66]:
                    k.cyl(root+fwd*dx+Z*.46,.15,.18,'steel',6)
            k.beam(a,q,1.10,1.30,m);k.beam(b,q,1.18,1.44,m)
            for t in [.32,.66]:
                low=a.lerp(q,t);high=b.lerp(q,min(.93,t+.21))
                k.beam(low,high,.38,.44,'metal_grey')
            crown=local(2.0,sign*1.38,top_height+.49)
            k.beam(q,crown,.93,1.10,m)
            rear=local(-2.85,sign*1.4,top_height-2.2)
            k.beam(a,rear,.58,.78,'steel_dark')
            k.beam(rear,crown,.57,.72,'steel_rust')
            k.beam(local(4.0,sign*1.73,heel_z+.2),crown,.48,.69,'metal_grey')
        machine=local(-.15,0,heel_z+.14)
        k.box(machine,(7.93,5.54,.94),'metal_dark',heading)
        k.beam(local(-4.33,-2.75,heel_z+.5),local(2.85,-2.75,heel_z+.5),.50,.32,'hull_grey')
        for s0,s1 in [(-3.9,-1.0),(.42,3.5)]:
            k.railing(local(s0,-2.84,heel_z+.63),local(s1,-2.84,heel_z+.63),'steel_rust')
        # Open winding drum, clutch, flank brake and motor at the inspection deck.
        w=machine-fwd*.7+Z*2.01
        turned(k,w,side,[(-2.01,.42),(-1.64,.42),(-1.59,1.48),(-1.36,1.48),
                         (-1.31,1.12),(1.18,1.12),(1.26,1.48),(1.5,1.48),(1.61,.53),(2.09,.50)],
               'steel_dark',20)
        for a0 in [-.89,-.47,.04,.55,.89]:
            k.torus(w+side*a0,1.10,.06,'steel_rust',16,4,side)
        k.box(w+side*2.04,(1.68,1.09,1.43),'metal_green',heading)
        k.ladder(local(-2.15,-3.43,anchor+.25),local(-2.15,-3.43,heel_z+.57),.83)
        # A tapered lattice cantilever with actual chords and triangulated flanks.
        heel=local(1.65,0,top_height)
        axis=(tip-heel).normalized();right=Z.cross(axis).normalized();up=axis.cross(right)
        def section(t):
            c=heel.lerp(tip,t)
            halfwidth=(2.32 if receiving else 1.96)*(1-t)+.73*t
            halfheight=(2.05 if receiving else 2.45)*(1-t)+.76*t
            return [c+right*s*halfwidth+up*h*halfheight for s,h in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        sections=[section(t) for t in [0,.21,.49,.74,1]]
        for j,(a,b) in enumerate(zip(sections,sections[1:])):
            for i in range(4):
                k.beam(a[i],b[i],.53 if i<2 else .41,.49,m)
            for i,l in [(0,3),(1,2),(0,1)]:
                k.beam(a[i],a[l],.32,.30,'steel_dark')
                k.beam(a[i if j%2 else l],b[l if j%2 else i],.35,.32,'steel_rust')
        # Counterweight tray and upper stay form the characteristic hammerhead at the receiving end.
        tail=local(-5.9 if receiving else -4.4,0,top_height)
        peak=local(-1.56,0,wheel_z+(4.6 if receiving else 3.2))
        k.beam(tail,heel,3.29,.77,'steel_dark')
        for j in range(3 if receiving else 2):
            k.box(tail+Z*(.22+j*.56),(2.94,3.58,.52),'conc_warm',heading)
        for sign in [-1,1]:
            k.beam(tail+side*1.57,peak+side*.6,.55,.62,'steel_rust')
            k.beam(heel+side*1.54,peak+side*.6,.66,.74,m)
            k.cable(peak+side*.58,sections[3][3 if sign<0 else 2],.42,.145,'steel_dark',7)
        # Wire runs from the drum over the heel to the outboard sheave.
        along=w+Z*1.15+side*.82
        roller=local(.95,.83,top_height+2.00)
        k.pipe(along,roller,.145,'steel',7)
        k.cable(roller,tip+side*.83+Z*1.24,.36,.135,'steel',7)
        k.pipe(tip-side*1.39,tip+side*1.39,.31,'steel',12)
        for at in [-.50,.48]:
            wheel=tip+side*at
            k.torus(wheel,1.23,.20,'metal_yellow',20,7,side)
            for i in range(4):
                a=math.pi*i/4
                rad=(fwd*math.cos(a)+Z*math.sin(a))*1.18
                k.beam(wheel-rad,wheel+rad,.18,.19,'steel_dark')
        for sign in [-1,1]:
            plate=tip+side*sign*.96
            k.beam(plate-axis*2.32+up*.40,plate+up*.04,.29,.92,'hull_grey')
            k.pipe(plate-side*.16,plate+side*.16,.47,'steel_rust',12)
        small_flood(k,machine+side*2.39+Z*2.39,(fwd.x,fwd.y,-.42),COOL if receiving else WARM,19,.69)
        k.light(w-fwd*1.54+Z*1.46,WARM,9,.37,'lamp')
        k.marker('salvage_catch' if receiving else 'salvage_lift',carry,tuple(fwd))
        k.marker('salvage_catch_sheave' if receiving else 'salvage_lift_sheave',tip,tuple(fwd))
        k.collider((7.9,5.5,.94),machine,heading,tag='salvage_winch_deck')


def service_traces(k):
    # Runs align with the shoulders. Spans split at grade changes and junctions.
    for route in [[(-111,-128),(-93,-128),(-78,-130),(-55,-129),(-39,-126)],
                  [(23,-91),(16,-103),(12,-118),(7,-132)],
                  [(98,-75),(112,-77),(124,-81)]]:
        pts=[V((x,y,G.z(x,y)+1.05)) for x,y in route]
        for p,q in zip(pts,pts[1:]):
            k.part();k.pipe(p,q,.35,'steel_rust',8)
            k.pipe(p+V((0,.72,-.13)),q+V((0,.72,-.13)),.23,'metal_teal',8)
            spans=max(1,round((q-p).length/7))
            for i in range(spans):
                f=(i+.23)/spans;a=p.lerp(q,f);gr=G.z(a.x,a.y)
                k.box((a.x,a.y+.2,(a.z+gr)/2),(.77,1.85,max(.3,a.z-gr-.42)),'conc_dark')
                k.box((a.x,a.y+.2,a.z-.45),(.78,1.75,.28),'steel')
    # Pump hut on the eastern edge of the truck motorpool. Centre pad stays free for parked vehicles.
    x,y=25,-128
    d=clipped_pad(k,x,y,7.2,6.3,8,.75)
    k.box((x,y,d+1.85),(6.62,5.65,3.7),'metal_teal',8)
    k.box((x,y,d+3.96),(7.35,6.55,.55),'metal_grey',8)
    k.box((x+1.4,y-2.61,d+1.38),(1.76,.24,2.75),'metal_dark',8)
    k.lamp((x+3.0,y-3.3,d),3.7,col=WARM,r=15,power=.73)
    for i,(x,y) in enumerate([(-101,-129),(-80,-131),(-49,-128),(-33,-125),
        (-12,-129),(11,-126),(23,-143),(19,-112),(32,-88),(39,-101),(76,-90),
        (96,-78),(116,-81),(109,-131),(109,-155),(28,-169)]):
        gr=G.z(x,y)
        if gr>-9000:
            k.part()
            if i in (2,6,10):
                k.lamp((x,y,gr+.08),3.6,'beacon',RED,12,.61)
            else:
                k.lamp((x,y,gr+.08),3.35+1.15*((i*7)%4)/3,col=WARM if i%4 else COOL,r=14.7,power=.65)
    for x,y in [(-86,-128),(13,-120),(101,-78),(30,-169)]:
        gr=G.z(x,y);k.box((x,y,gr+.95),(1.43,1.1,1.9),'metal_green')
        k.box((x,y,gr+1.99),(1.67,1.38,.24),'hull_grey')


def build(out,log):
    k=Kit('fill',611729)
    south_wreck(k)
    receivers(k)
    old_derrick(k)
    foundry(k)
    flightline(k)
    standing_stones(k)
    service_traces(k)
    axle_works(k)
    salvage_davits(k)
    k.finalize(out,log)
