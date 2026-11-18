"""Calved-shard cargo harbour. All construction coordinates are metres, Z up."""
import math

from lib.ground import G
from lib.kit import Kit, V, Z
from lib.layout import BRIDGE_E, BRIDGE_W, bite_xc


COLD = (.58, .78, .82)
SODIUM = (1., .49, .21)
RED = (1., .085, .04)
CRANE_Y = -38.
SLOTS_Y = (-38., -30., -21., -12.)
DECK = -3.5


def ground(x, y, fallback=-11.):
    z = G.z(x, y)
    return z if z > -9000 else fallback


def chamfered_rect(cx, cy, sx, sy, bevel):
    """Octagonal plan with longer flat sides for welded knees and concrete shutters."""
    a, b = sx / 2, sy / 2
    return [(cx + x, cy + y) for x, y in (
        (-a + bevel, -b), (a - bevel, -b), (a, -b + bevel), (a, b - bevel),
        (a - bevel, b), (-a + bevel, b), (-a, b - bevel), (-a, -b + bevel))]


def housing(k, centre, levels, mat, bevel=.75):
    cx, cy = centre
    rings = []
    for z, sx, sy in levels:
        cut = min(bevel, sx * .18, sy * .18)
        rings.append([(x, y, z) for x, y in chamfered_rect(cx, cy, sx, sy, cut)])
    k.loft(rings, mat)


def fixture(k, p, col=COLD, radius=14., power=.7, kind='lamp', face=(0, -1, -.22)):
    """Low glares: a recessed lens and a short cast hood, aimed off the mounting face."""
    p, d = V(p), V(face).normalized()
    k.part()
    k.beam(p - d * .45, p + d * .15, .95, .54, 'metal_dark')
    lens = 'emit_red' if kind == 'beacon' else ('emit_sodium' if col[2] < .4 else 'emit_cool')
    if kind == 'beacon':
        k.cyl(p + Z * .25, .29, .56, lens, 8)
        k.cyl(p + Z * .60, .34, .12, 'steel_dark', 8)
    else:
        k.beam(p + d * .15, p + d * .22, .71, .29, lens)
    k.light(p + d * .48, col, radius, power, kind)


def bridges(k):
    dx, dy = BRIDGE_E[0] - BRIDGE_W[0], BRIDGE_E[1] - BRIDGE_W[1]
    span = math.hypot(dx, dy)
    x, y = dx / span, dy / span
    az = math.degrees(math.atan2(dy, dx))
    for suffix, centre, floor, land in [('w', BRIDGE_W, -1., -1.), ('e', BRIDGE_E, -8., 1.)]:
        def p(u, v, h):
            return V((centre[0] + x*u - y*v, centre[1] + y*u + x*v, floor+h))

        def ring(u, v, h, width, depth):
            return [p(u+a*depth/2, v+b*width/2, h) for a, b in (
                (-1, -1), (1, -1), (1, 1), (-1, 1))]

        k.part()
        # A narrow abutment cap aligns with the deck surface without entering the span.
        k.box(p(land * 2.45, 0, -1.1), (4.9, 18.9, 1.7), 'conc', az)
        k.collider((4.9, 18.9, 1.65), p(land * 2.45, 0, -1.14), az, 'port_abutment')
        for s in (-1, 1):
            k.part()
            # Face of the fissure is undercut: straight bearing plus raked wall key.
            k.loft([ring(land*3.6, s*8.95, -13.5, 4.7, 8.2),
                    ring(land*2, s*8.7, -3.9, 5.4, 8.2),
                    ring(.15, s*8.5, 2.4, 5.7, 6.8)], 'conc_dark')
            k.loft([ring(.15, s*8.5, 1.8, 4.45, 5.6),
                    ring(.3*land, s*8.1, 9., 3.4, 4.4),
                    ring(0, s*6.55, 27., 2.35, 2.95),
                    ring(0, s*6.05, 34.7, 2.25, 2.9)], 'conc_warm')
            # The offset elevator duct is independent of the pylon's load-bearing shaft.
            k.beam(p(land*2.6, s*8.7, 2.), p(land*1.8, s*6.8, 29.4),
                   1.05, 1.0, 'metal_teal' if s > 0 else 'metal_dark')
            k.pipe(p(-land*2.02, s*7.8, 4.), p(-land*1.2, s*6.4, 31.), .22, 'steel_rust', 8)
            k.box(p(0, s*6., 34.8), (4.1, 3.4, 1.9), 'metal_dark', az)
            axle = -V((y, -x, 0)) * 1.75
            k.pipe(p(0, s*6., 35.5) - axle, p(0, s*6., 35.5) + axle, .56, 'steel', 12)
            k.box(p(land*.65, s*7.2, 29.2), (4.2, 3.05, .52), 'metal_grey', az)
            k.railing(p(-1.5, s*8.45, 29.46), p(1.85, s*8.45, 29.46), 'steel_rust')
            k.ladder(p(land*1.8,s*8.86,6.),p(land*1.77,s*7.1,29.45))
            k.marker('bridge_saddle_'+suffix+('_n' if s > 0 else '_s'),p(0,s*6.,36.))
            fixture(k,p(land*.6,s*7.,35.95),RED,18.,.85,'beacon',(x,y,0))
            fixture(k,p(-land*2.3,s*8.7,4.2),COLD,17.,.8)
            fixture(k,p(land*.75,s*6.65,25.35),SODIUM,14.,.45)

            # Anchor plunges into the island on a line fanned away from the rail envelope.
            u, v = land*(19.3 if suffix=='w' else 17.), s*(11.6 if suffix=='w' else 12.6)
            a=p(u,v,0); bearing=ground(a.x,a.y,floor-2.0)
            top=bearing+3.-floor
            k.part()
            k.loft([ring(u,v,top-6.4,6.3,9.),ring(u,v,top-.7,5.8,7.4),
                    ring(u-land*.85,v,top+.65,4.3,5.6)],'conc')
            k.box(p(u-land*2.1,v,top+.9),(1.9,3.1,.75),'steel_dark',az)
            for off in (-.25,.25):
                a0=p(u-land*2.,v+off,top+1.3); a1=p(0,s*6.+off,36.)
                k.cable(a0,a1,.72,.18,'steel_dark',6)
            k.marker('bridge_anchor_'+suffix+('_n' if s>0 else '_s'),p(u,v,top+1.3))
        k.part()
        k.truss(p(0,-6.3,30.65),p(0,6.3,30.65),2.05,1.85,'metal_grey',3,.44)
        for s in (-1,1):
            k.beam(p(0,s*7.2,23.2),p(0,s*3.65,30.5),.78,.98,'steel_dark')
        k.catwalk(p(land*1.4,-6.1,31.7),p(land*1.4,6.1,31.7),1.3)
        k.marker('bridge_'+suffix,p(0,0,0),(x,y,0))
    # Only this repeated unit belongs to the simulated span. Top of plate is local Z=0.
    length = span / 24.
    with k.into('bridge_seg',loc=(0,0,0)):
        k.part()
        k.box((0,0,-.20),(length+.045,11.5,.40),'hull_grey')
        k.beam((0,-5.67,-.68),(0,5.67,-.68),.66,.74,'steel_dark')
        for side in (-1,1):
            k.box((0,side*5.49,-.49),(length,.49,.88),'steel_rust')
            k.box((0,side*5.48,.25),(length,.37,.49),'conc_dark')
            k.beam((-length/2,side*5.57,1.02),(length/2,side*5.57,1.02),.115,'metal_grey')
            k.beam((0,side*5.57,.4),(0,side*5.57,1.03),.12,'metal_grey')
            for gauge in (-1.05,1.05):
                k.box((0,side*2.85+gauge,.13),(length,.24,.26),'steel')


def deck_and_stacks(k):
    """Cantilever on the east face. Gussets terminate in the rock below the quay."""
    deck_plan=[(274.,-53),(307.1,-53),(311.9,-49),(315.9,-49),(318.7,-45),(318.7,-7),(315.3,1),
               (311.9,4),(279.,4),(274.,0)]
    k.part()
    k.prism(deck_plan,DECK-2.2,DECK,'conc')
    for a,b in zip(deck_plan,deck_plan[1:]+deck_plan[:1]):
        k.beam((*a,DECK-1.75),(*b,DECK-1.75),.7,.84,'steel_dark')
    for i,yy in enumerate((-46.,-34.,-17.,-6.)):
        outer=V((317.3,yy,DECK-1.8))
        inner_x=(270.,275.,284.,287.)[i]
        k.part()
        k.box((inner_x,yy,-20.2),(5.7,6.2,20.),'conc_dark')
        k.truss((inner_x-1.5,yy,DECK-3.8),outer,3.6,4.6,'steel_rust',5,.83)
        k.beam((inner_x,yy,-28.1),outer,1.4,2.1,'steel_dark')
        k.beam((inner_x,yy,-28.1),((inner_x+317.3)/2,yy,DECK-2.1),1.04,1.48,'metal_grey')
        k.box((317.44,yy,DECK-3.0),(2.2,4.15,6.9),'rubber',(0,-8,0))
        fixture(k,(317.712,yy+.85,DECK-.55),SODIUM,9.,.4,face=(1,0,-.25))
    # Split collision grid: the long quay does not occupy an unbounded range of hash cells.
    for y0,y1,x0,x1 in [(-52.9,-49.,274.,307.0),(-49.,-45.,274.,315.8),
                         (-45.,-31.,274.,318.6),(-31.,-17.,274.,318.6),(-17.,-7.,274.,318.6),
                         (-7.,0.,274.,315.1),(0.,3.9,279.1,311.8)]:
        count=math.ceil((x1-x0)/13.)
        width=(x1-x0)/count
        for j in range(count):
            k.collider((width,y1-y0,2.),(x0+(j+.5)*width,(y0+y1)/2,DECK-1.),tag='port_quay')
    k.data['quayGravity']={'min':[274.,DECK-1.,-4.],'max':[318.7,DECK+46.,53.],
                           'g':[0.,-2.6,0.],'who':2}
    for xx in (277.8,305.2):
        k.part()
        k.box((xx,-25.,DECK+.12),(.8,50,.24),'metal_dark')
        k.box((xx,-25.,DECK+.29),(.29,50,.18),'steel')
        for yy in (-49.3,-.8):
            k.box((xx,yy,DECK+.75),(1.18,1.35,1.15),'metal_hazard')
    for yy in SLOTS_Y:
        for xx in (284.5,299.0):
            for sx,sy in ((-1,-1),(1,1)):
                k.box((xx+sx*5.68,yy+sy*1.76,DECK+.035),(1.5,.17,.06),'metal_white')
                k.box((xx+sx*6.32,yy+sy*1.25,DECK+.035),(.17,1.12,.06),'metal_white')
    for i,yy in enumerate(SLOTS_Y):
        k.marker('crane_src_'+str(i),(284.5,yy,DECK+1.45))
        k.marker('crane_dst_'+str(i),(299.0,yy,DECK+1.45))
    def boxcar(cx,cy,z,paint):
        k.part()
        k.box((cx,cy,z+1.44),(12.16,2.52,2.83),paint)
        for sy in (-1,1):
            k.box((cx,cy+sy*1.28,z+.13),(12.17,.14,.2),'steel_dark')
            k.box((cx,cy+sy*1.28,z+2.70),(12.17,.14,.16),paint)
            # Three grouped field stiffeners, divided by broad panels.
            for a in (-4.7,-2.2,.35,3.2,4.9):
                k.box((cx+a,cy+sy*1.29,z+1.43),(.14,.12,2.43),paint)
        for a in (-5.92,5.92):
            for b in (-1.18,1.18):
                k.box((cx+a,cy+b,z+1.43),(.23,.24,2.9),'hull_dark')
        for sy in (-.71,.71):
            k.pipe((cx+6.14,cy+sy,z+.40),(cx+6.14,cy+sy,z+2.44),.067,'steel',6)
        k.box((cx+3.58,cy-1.328,z+1.76),(1.3,.05,.51),'hull_white')
    for i,(yy,n) in enumerate(((-44.,1),(-40.9,2),(-37.8,2),(-28.5,1),(-25.4,3),
                               (-22.3,2),(-13.5,1),(-10.4,2),(-7.3,2))):
        for j in range(n):
            boxcar(311.524+(i%3-1)*.17, yy, DECK+2.90*j,
                   ('metal_red','hull_grey','metal_blue','metal_green','hull_rust')[(i*2+j)%5])
    for xx,yy in ((316.624,-41.),(316.624,-18.),(314.584,-3.),(280.0,-51.),(277.0,1.)):
        k.part()
        k.cyl((xx,yy,DECK+.25),1.02,.5,'metal_dark',10)
        k.lathe((xx,yy,DECK+.47),[(0,.62),(.92,.46),(1.16,.73),(1.43,.71)],'steel_rust',10)
    k.railing((279.4,3.4,DECK),(311.184,3.4,DECK),'metal_grey')
    k.railing((307.376,-52.2,DECK),(277.2,-52.2,DECK),'metal_grey')
    for x,y,h in ((275.6,-47,5.),(317.304,-30.,4.6),(314.924,-4.1,5.5),(276.1,-10.,4.3),(280.4,1.5,4.)):
        k.lamp((x,y,DECK),h,'flood',COLD,20,1.)
    k.marker('quay_east',(317.304,-24.,DECK),(1,0,0))
    # Inboard lift ramp carries forklifts from the rock apron to the higher unloading deck.
    k.beam((251.7,-33.7,-8.32),(274.5,-33.7,DECK-.31),5.25,.60,'conc_dark')
    for sy in (-1,1):
        k.beam((251.7,-33.7+sy*2.47,-7.99),(274.5,-33.7+sy*2.47,DECK+.03),.23,.64,'conc')
    for xx in (260.7,268.8):
        floor=ground(xx,-33.7)
        underside=-8.62+(DECK-.61+8.62)*(xx-251.7)/(274.5-251.7)
        k.box((xx,-33.7,(floor-1.1+underside)/2),(1.2,4.2,underside-floor+1.1),'conc_dark')


def gantry(k):
    cy=CRANE_Y
    with k.into('crane',loc=(291.5,cy,-3.25)):
        for xx,legside in ((277.8,-1),(305.2,1)):
            k.part()
            k.box((xx,cy,-2.24),(1.8,12.75,1.04),'metal_dark')
            for sy in (-1,1):
                yy=cy+sy*4.85
                for off in (-.98,.98):
                    k.pipe((xx-.77,yy+off,-2.64),(xx+.77,yy+off,-2.64),.56,'steel',12)
                k.box((xx,yy,-1.75),(2.25,3.9,.98),'metal_orange')
                k.beam((xx,yy,-1.3),(xx-legside*1.3,cy+sy*2.,23.5),1.25,1.66,'metal_orange')
                k.beam((xx,yy,1.0),(xx+legside*1.15,cy+sy*1.62,13.7),.55,.77,'steel_dark')
                k.box((xx,yy,-0.95),(2.,3.1,.44),'metal_yellow')
            k.beam((xx,cy-3.6,6.4),(xx,cy+3.6,6.4),.8,.87,'hull_grey')
            fixture(k,(xx+.93,cy-4.9,-0.5),SODIUM,12.,.69)
            fixture(k,(xx-legside,cy+.4,18.7),COLD,16.,.68)
        # Quayside export cantilever and offset machinery house, balanced by a shorter backreach.
        for yy in (cy-2.25,cy+2.25):
            k.part()
            k.truss((277.75,yy,25.3),(317.0,yy,25.3),.94,3.55,'metal_orange',7,.48)
            k.beam((277.8,yy,24.0),(313.0,yy,24.0),.55,.32,'steel')
        for xx in (278.0,283.6,291.7,303.4,315.6):
            k.beam((xx,cy-2.6,27.02),(xx,cy+2.6,27.02),.60,.52,'metal_orange')
        for sy in (-1,1):
            a=(278.4,cy+sy*2.35,27.0);b=(286.0,cy+sy*1.55,37.3)
            k.beam(a,b,.69,.88,'metal_orange')
            k.beam((289.8,cy+sy*2.35,27.0),b,.55,.71,'metal_orange')
            k.cable(b,(315.3,cy+sy*2.2,27.1),.44,.14,'steel',8)
        k.beam((286.0,cy-1.7,37.3),(286.0,cy+1.7,37.3),.68,.62,'metal_grey')
        k.box((281.9,cy+.18,27.35),(5.9,5.7,.8),'metal_dark')
        housing(k,(281.8,cy+.3),[(27.5,4.9,4.8),(31.65,4.9,4.8),(32.18,4.25,4.55)],'metal_red',.4)
        k.box((281.8,cy-2.15,30.15),(3.6,.15,1.19),'glass_warm')
        for xx in (280.2,281.7,283.2):
            k.box((xx,cy-2.28,30.15),(.17,.2,1.3),'metal_grey')
        k.box((281.75,cy-2.64,31.07),(5.35,1.75,.31),'hull_white')
        k.box((282.0,cy+.95,32.48),(2.45,1.38,.69),'metal_green')
        k.catwalk((277.8,cy+3.61,27.4),(308.0,cy+3.61,27.4),1.52)
        k.stairs((277.8,cy+5.25,-1.37),(278.4,cy+1.6,5.1),1.36)
        k.ladder((277.9,cy+2.9,5.0),(277.9,cy+2.9,26.9),.74)
        fixture(k,(316.4,cy-2.42,25.95),RED,14.,.7,'beacon')
        fixture(k,(281.4,cy-2.4,28.3),SODIUM,15.,.69)
        fixture(k,(293.9,cy-2.3,24.0),COLD,24.,.9)
        fixture(k,(286.1,cy,37.55),RED,18.,.82,'beacon')
        with k.into('crane_trolley',parent='crane',loc=(284.5,cy,24.2)):
            k.part()
            k.box((284.5,cy,24.37),(9.1,4.74,.81),'metal_yellow')
            for xx in (280.8,288.2):
                k.pipe((xx,cy-1.35,24.12),(xx,cy+1.35,24.12),.54,'steel_dark',12)
                for sy in (-1,1):
                    k.pipe((xx,cy+sy*1.82,24.68),(xx,cy+sy*2.48,24.68),.59,'steel',10)
                k.marker('crane_line_'+('a' if xx<284.5 else 'b'),(xx,cy,24.2))
            k.box((283.8,cy,25.5),(4.3,2.54,1.67),'metal_grey')
            fixture(k,(284.5,cy-.9,23.86),COLD,20.,.89,face=(0,-.3,-1))
        with k.into('crane_spreader',parent='crane_trolley',loc=(284.5,cy,10.2)):
            k.part()
            for sy in (-1,1):
                k.beam((278.55,cy+sy*.92,10.18),(290.45,cy+sy*.92,10.18),.35,.55,'metal_yellow')
            for xx in (278.65,284.45,290.35):
                k.beam((xx,cy-1.17,10.15),(xx,cy+1.17,10.15),.57,.51,'metal_dark')
            for xx in (280.8,288.2):
                k.torus((xx,cy,10.63),.42,.1,'steel',10,5,normal=(0,1,0))
                k.marker('crane_hitch_'+('a' if xx<284.5 else 'b'),(xx,cy,10.2))
            for xx in (278.85,290.15):
                for sy in (-1,1):
                    k.box((xx,cy+sy*1.08,9.87),(.62,.46,.52),'metal_hazard')
            k.marker('crane_hook',(284.5,cy,10.2))
            fixture(k,(284.7,cy-1.05,10.38),RED,9.5,.46,'beacon')


def mass_driver(k):
    breech, muzzle = V((266,-128,-7)),V((272,-52,16))
    delta=muzzle-breech;direction=delta.normalized()
    lateral=V((direction.y,-direction.x,0)).normalized()
    up=lateral.cross(direction).normalized()
    def rail(t,side=0.,height=0.):
        return breech+delta*t+lateral*side+up*height
    k.marker('md_breech',breech,direction,up)
    k.marker('md_muzzle',muzzle,direction,up)
    # Rear span is suspended off the edge of the shard and tied back to the head house.
    k.part()
    for x,yy,sx,sy in [(253.2,-126.,12.7,10.8),(256.2,-120.,13.8,14.9)]:
        k.box((x,yy,-9.74),(sx,sy,3.8),'conc_dark')
    housing(k,(255.,-123.6),[(-8.1,14.,13.),(-5.5,14.,12.4),(-.15,11.,10.8),(1.2,9.,8.5)],
            'conc_warm',1.6)
    k.box((257.2,-129.,-2.5),(5.2,.5,2.5),'metal_dark')
    k.box((257.4,-129.35,-2.25),(3.7,.27,.81),'glass_warm')
    for i,t in enumerate((.025,.17,.32,.51,.70,.87,.975)):
        p=rail(t,0,-1.9);yy=p.y
        land_x=p.x if t>.36 else 252.8+11.*t
        z=ground(land_x,yy,-11.)
        if i<3:
            k.part()
            k.box((land_x,yy,z-1.),(5.6,4.6,7.8),'conc_dark')
            k.truss((land_x,yy,z+.35),p,2.16,2.24,'steel_rust',3,.46)
            k.beam((land_x-1.7,yy,z-4.4),p,.87,1.22,'steel_dark')
        else:
            for s in (-1,1):
                a=rail(t,s*3.4,-2.1)
                foot_z=ground(a.x+s*.55,a.y,z-5.)
                base=(a.x+s*.55,a.y,foot_z-.4)
                k.box((base[0],base[1],foot_z+.23),(2.8,4.1,1.35),'conc')
                k.beam(base,a,.95,1.37,'metal_grey')
            k.beam(rail(t,-3.7,-2.2),rail(t,3.7,-2.2),1.17,1.03,'metal_grey')
    for s in (-1,1):
        k.part()
        k.truss(rail(.005,s*2.94,-1.58),rail(.997,s*2.94,-1.58),.83,1.68,
                'steel_rust',10,.34)
        k.beam(rail(-.035,s*2.24,-.22),rail(1.015,s*2.24,-.22),.65,.62,'metal_grey')
        k.beam(rail(-.02,s*2.2,.1),rail(1.01,s*2.2,.1),.24,.14,'steel')
    # Each iron yoke is a split C with removable transformer cassettes. The bore remains open.
    for i,t in enumerate((.095,.235,.405,.585,.78,.965)):
        thick=1.6 if i in (0,5) else .98
        k.part()
        for side in (-1,1):
            a,b,c,d=(rail(t,side*q,h) for q,h in [(3.55,-1.77),(4.02,.38),(3.53,3.61),(2.37,4.54)])
            k.beam(a,b,thick,.91,'metal_grey');k.beam(b,c,thick,1.15,'metal_grey')
            k.beam(c,d,thick,.83,'metal_orange' if i in (0,3,5) else 'metal_dark')
            k.beam(rail(t-.024,side*4.02,.85),rail(t+.024,side*4.02,.85),1.08,2.52,'hull_rust')
            k.beam(rail(t-.027,side*4.53,-.25),rail(t+.027,side*4.53,-.25),.34,.77,'metal_teal')
        k.beam(rail(t,-3.96,-1.48),rail(t,3.96,-1.48),thick,.8,'steel_dark')
    for s in (-1,1):
        k.tube([rail(t,s*3.9,-1.61) for t in (.075,.34,.59,.88)],.24,'steel_rust')
    k.catwalk(rail(.26,-4.8,-1.57),rail(.81,-4.8,-1.57),1.18)
    k.catwalk(rail(.865,-4.86,-1.56),rail(1.015,-4.86,-1.56),1.35)
    k.ladder(rail(.905,-5.12,-1.78)-Z*17.6,rail(.905,-5.12,-1.51),.8)
    k.part()
    for yy in (-125.5,-120.1):
        k.box((254.4,yy,1.55),(5.55,2.02,1.53),'metal_green')
        k.pipe((255.,yy,2.33),(255.,yy,3.88),.55,'steel_rust',10)
    k.tube([(249.,-126.,-5.5),(249.,-132.,-5.5),(258.,-132.,-5.5),
            tuple(rail(-.025,-3.1,-1.2))],.68,'steel_dark')
    k.marker('md_charge',(260.1,-127.7,.35))
    k.light((260.1,-127.7,.35),(.56,.21,.64),15.,.45,'aura')
    for t,col in ((.065,SODIUM),(.265,COLD),(.612,SODIUM),(.826,COLD),(.983,RED)):
        fixture(k,rail(t,-3.88,1.2),col,14.,.7,'beacon' if col==RED else 'lamp')
    fixture(k,(258.3,-128.9,-1.35),SODIUM,15.,.72)
    fixture(k,rail(.12,4.6,-.4),COLD,15.,.58,face=(1,0,-.4))
    with k.into('md_sled',loc=breech):
        k.part()
        for s in (-1,1):
            k.beam(rail(-.042,s*1.9,.45),rail(.049,s*1.9,.45),.56,.7,'metal_hazard')
        for t in (-.034,.037):
            k.beam(rail(t,-1.95,.53),rail(t,1.95,.53),.64,.52,'hull_dark')
        k.beam(rail(-.026,0,.5),rail(.028,0,.5),2.67,.63,'metal_grey')
        k.marker('md_sled_axis',breech,direction,up)


def capstan(k, p, scale=1.0):
    x,y,z=p;s=scale
    k.part()
    k.box((x,y,z+.44*s),(4.4*s,2.96*s,.88*s),'conc_dark')
    for sy in (-1,1):
        k.box((x,y+sy*.97*s,z+1.31*s),(2.65*s,.38*s,1.56*s),'metal_grey')
        k.pipe((x,y+sy*1.08*s,z+1.64*s),(x,y+sy*1.25*s,z+1.64*s),1.10*s,'hull_rust',14)
    k.pipe((x,y-.94*s,z+1.64*s),(x,y+.94*s,z+1.64*s),.83*s,'steel',14)


def pump_house(k):
    """Shore manifolds feed the ship hose via a raised pipe bridge over the haul road."""
    x,y=256.,-40.5
    z=ground(x,y)
    k.part()
    k.box((x,y,z+.23),(9.2,13.55,.66),'conc_dark')
    for sign in (-1,1):
        k.box((x+sign*4.48,y,z+.72),(.38,13.4,1.16),'conc')
    for px,yy,rr,length in ((254.,-40.9,1.44,7.6),(257.5,-41.7,1.12,5.2)):
        for dy in (-length*.32,length*.32):
            k.box((px,yy+dy,z+1.18),(rr*1.9,1.33,1.52),'conc_dark')
        k.pipe((px,yy-length*.5,z+2.6),(px,yy+length*.5,z+2.6),rr,'hull_grey',14)
        for side in (-1,1):
            k.sphere((px,yy+side*length*.5,z+2.6),(rr,rr*.46,rr),'hull_grey',12,6)
            k.pipe((px,yy+side*length*.5,z+2.6),(px,yy+side*(length*.5+.17),z+2.6),
                   rr*1.07,'hull_rust',14)
        k.cyl((px,yy,z+2.76+rr),.42,.66,'steel_dark',8)
        k.torus((px+.32,yy-.29,z+3.36+rr),.47,.075,'metal_red',12,5,normal=(.63,-.76,.13))
    # Manifold clears the north-bound truck road by just over seven metres.
    for xx in (236.4,253.5):
        k.box((xx,-37.55,-7.55),(2.45,3.18,1.28),'conc_dark')
        k.tower((xx,-37.55),-7.25,-.3,2.,1.55,'steel_rust',2,.25)
    k.truss((236.4,-37.55,0.),(253.5,-37.55,0.),2.2,1.37,'steel_rust',4,.24)
    for i,r in enumerate((.29,.40)):
        yy=-37.15-.82*i
        k.tube([(235.25,yy,-5.58),(235.25,yy,.58),(236.65,yy,1.10),(252.71,yy,1.10),
                (254.14+i*.75,yy,.35),(254.14+i*.75,yy,-4.3)],r,'steel_dark' if i else 'hull_rust',8)
    k.tube([(257.65,-39.5,-5.65),(261.6,-39.5,-5.65),(264.35,-42.25,-5.65),
            (267.65,-42.25,-5.65),(267.65,-42.25,-7.2),(273.15,-42.25,-7.2),
            (273.15,-42.25,-8.5),(285.5,-42.25,-8.5)],.43,'steel_dark',9)
    for xx,yy in ((251.92,-46.2),(259.9,-36.1)):
        fixture(k,(xx,yy,z+2.6),SODIUM,13.2,.57)
    k.lamp((252.1,-34.9,z),4.4,'flood',COLD,15.,.72)


def moor(k):
    x,y=262.6,11.4
    floor=ground(x,y)
    k.part()
    housing(k,(x,y),[(floor-1,16.2,13.3),(floor+2,16.2,13.3),(floor+4,13.7,11.8)],
            'conc_dark',2.)
    housing(k,(x,y),[(floor+3,9.1,8.8),(16,7.3,7.2),(24.5,5.8,5.6)],
            'conc',1.15)
    for i,(sx,sy) in enumerate(((-1,-1),(1,-1),(1,1),(-1,1))):
        k.part()
        a=(x+sx*6.7,y+sy*5.2,floor+1.9);b=(x+sx*3.45,y+sy*2.8,19.6)
        k.beam(a,b,2.4,2.85,'conc_warm')
        k.beam(b,(x+sx*2.71,y+sy*2.31,46.3),1.05,1.27,'metal_grey')
        fixture(k,(b[0],b[1],b[2]+.4),COLD if i%2 else SODIUM,18.,.67)
    k.tower((x,y),21.8,78.4,7.42,4.4,'metal_grey',7,.82)
    k.box((x-.50,y+.3,50.7),(2.15,1.75,51.9),'metal_teal')
    k.tube([(x-1.65,y-1.15,16.),(x-1.65,y-1.15,49.),(x-1.42,y-1.15,52.),
            (x-1.42,y-1.15,81.3)],.35,'steel_rust')
    for zz in (25.,48.5,72.8):
        k.part()
        k.box((x,y,zz),(8.65 if zz<55 else 6.3,6.7,.73),'hull_dark')
        k.railing((x-3.4,y+3.02,zz+.38),(x+3.3,y+3.02,zz+.38),'steel_rust')
        k.box((x+1.8,y-1.25,zz+1.29),(2.4,2.35,2.24),'hull_white')
        fixture(k,(x+3.55,y-2.56,zz+1.37),SODIUM,15.,.55)
    # Swivel and articulated docking horns. An asymmetric swinging head reads against the dark sky.
    k.cyl((x,y,79.),3.42,3.25,'metal_dark',16)
    housing(k,(x,y),[(80.5,6.75,5.95),(89.,4.5,4.1),(103.,3.6,3.4)],
            'hull_grey',.65)
    k.truss((x-.6,y,86.2),(x+12.0,y-1.8,91.5),2.56,2.52,'hull_rust',3,.44)
    k.beam((x+1.0,y,81.2),(x+11.4,y-1.85,90.75),.78,1.18,'metal_dark')
    k.pipe((x+10.4,y-1.85,90.2),(x+15.5,y-1.85,93.58),.92,'steel',12)
    k.pipe((x+14.05,y-1.85,93.4),(x+15.95,y-1.85,93.4),1.8,'rubber',14)
    k.beam((x-6.,y+.4,95.4),(x+6.5,y+.4,102.4),1.26,1.65,'metal_grey')
    k.pipe((x,y,102.),(x,y,114.4),.84,'steel',10)
    k.cyl((x,y,108.3),1.32,.86,'hull_rust',10)
    k.pipe((x,y,113.),(x,y,117.55),.52,'metal_grey',8)
    k.box((x+1.7,y+.25,111.6),(4.5,1.,.8),'metal_dark')
    k.cable((x+5.8,y-.4,102.2),(x+.3,y-.4,111.6),.36,.16,'steel_dark',5)
    fixture(k,(x,y,117.55),RED,22.,1.1,'beacon')
    fixture(k,(x+11.35,y-2.58,90.9),RED,18.,.87,'beacon')
    for ax,ay,zz in ((256.0,23.6,53.5),(274.0,26.6,67.5)):
        bottom=ground(ax,ay)
        k.part()
        k.box((ax,ay,bottom+.65),(4.6,4.25,2.11),'conc_dark')
        k.cable((ax,ay,bottom+1.75),(x+(ax-x)*.2,y+2.55,zz),1.45,.25,'steel_dark',10)
        fixture(k,(ax+1.,ay-1.6,bottom+1.84),SODIUM,12.,.55)
    capstan(k,(x+6.8,y+3.3,floor+.2),1.18)
    k.marker('mooring_top',(x,y,118.))
    k.marker('mooring_collar',(x+15.2,y-1.85,93.4),(1,0,0))
    k.collider((12.8,10.6,9.),(x,y,floor+3.8),tag='port_mooring')


def tower_and_tank_farm(k):
    x,y=225.5,-54.8;z=ground(x,y)
    k.part()
    housing(k,(x,y),[(z-.9,12.8,11.4),(z+2.2,12.8,11.4),(z+3.4,10.8,10.2)],'conc_dark',1.1)
    housing(k,(x,y),[(z+2.2,8.45,8.2),(5.5,7.4,7.25),(22.,5.52,5.6),(28.7,6.,5.9)],
            'conc_warm',.9)
    k.beam((x-5.2,y+2.6,z+1.),(x-2.22,y+1.95,22.75),1.55,1.68,'conc')
    k.box((x+2.05,y+2.6,11.5),(2.15,2.8,29.0),'metal_green')
    k.pipe((x+3.28,y-.7,z+1.45),(x+3.28,y-.7,17.4),.30,'steel_rust',8)
    k.tube([(x+3.28,y-.7,17.3),(x+2.86,y-.7,18.4),(x+2.86,y-.7,26.)],.22,'steel_rust',8)
    k.part()
    housing(k,(x+.7,y-.45),[(23.7,6.2,6.7),(26.1,13.6,11.9),(27.,14.,12.3),
                              (28.15,13.7,12.1)],'metal_dark',1.55)
    housing(k,(x+.7,y-.45),[(27.95,12.4,10.95),(31.,13.6,11.95),(31.7,14.,12.1)],
            'glass',1.38)
    for off in (-4.2,-1.3,1.9,4.4):
        k.part(k.rng.random())
        k.box((x+.7+off,y-6.32,29.96),(1.84,.16,1.12),
              'glass_warm' if off>0 else 'emit_warm',(-9,0,0))
        k.beam((x+.7+off-1.12,y-5.91,28.0),(x+.7+off-1.12,y-6.53,31.2),.17,.21,'hull_grey')
    for off in (-2.55,.42,2.85):
        k.part(k.rng.random())
        k.box((x+7.23,y-.45+off,30.1),(.15,1.55,.93),'glass_warm',(0,9,0))
    housing(k,(x+.7,y-.45),[(31.5,14.1,12.15),(32.5,14.65,12.65),(33.0,13.3,11.3)],
            'hull_grey',1.52)
    k.catwalk((x-4.8,y-6.65,26.1),(x+5.7,y-6.65,26.1),1.45)
    k.ladder((x-3.1,y+3.42,5.8),(x-3.1,y+3.42,25.9),.9)
    for q,col in [((x+5.25,y-6.,26.45),SODIUM),((x-3.9,y-6.,26.45),SODIUM),
                  ((x+6.85,y+.11,30.1),SODIUM),((x-4.55,y-5.14,z+2.8),COLD)]:
        fixture(k,q,col,18.,.7)
    k.light((x+.8,y-4.2,29.6),SODIUM,18.,.74,'window')
    k.marker('port_search',(x-4.55,y-5.7,32.98),(-.74,.62,-.2))
    k.box((x-4.55,y-5.7,33.85),(1.65,1.45,1.3),'metal_dark')
    fixture(k,(x-5.25,y-5.9,33.85),COLD,20.,.68,face=(-.7,.62,-.2))
    k.pipe((x+3.8,y+2.25,32.6),(x+3.8,y+2.25,42.1),.13,'steel',6)
    k.cyl((x,y,34.16),1.4,2.36,'metal_dark',12)
    with k.into('port_radar',loc=(x,y,35.4)):
        k.cyl((x,y,35.58),1.87,.42,'steel_rust',14)
        for side in (-1,1):
            k.beam((x+side*1.28,y,35.53),(x+side*1.86,y,38.2),.45,.59,'metal_grey')
        c=V((x,y,38.1));dirs=V((.15,-.91,.385)).normalized()
        horiz=Z.cross(dirs).normalized();vert=dirs.cross(horiz).normalized()
        def dish(u,v):
            return c+horiz*(u*5.8)+vert*(v*3.2)+dirs*.97*(u*u+v*v)
        # Slotted reflector panels, a gently cupped aeronautical radar basket.
        for row in range(-3,4):
            v=row*.24
            width=math.sqrt(max(.1,1-v*v))
            for col in range(4):
                lo=width*(-1+col*.5)+.018; hi=width*(-.5+col*.5)-.018
                front=[dish(lo,v-.085),dish(hi,v-.085),dish(hi,v+.085),dish(lo,v+.085)]
                k.face(front,'metal_grey' if col!=1 else 'steel')
                k.face([q-dirs*.09 for q in reversed(front)],'steel_dark')
        outline=[dish(math.cos(math.tau*j/24),math.sin(math.tau*j/24)) for j in range(25)]
        k.tube(outline,.105,'hull_rust',6)
        for j in (0,3,7,10,13,17,20):
            th=math.tau*j/21;k.beam(c-dirs*.4,dish(math.cos(th),math.sin(th)),.13,'steel_dark')
        feed=c+dirs*3.8
        for u,v in ((-.81,-.35),(.81,-.35),(0.,.85)):k.pipe(dish(u,v),feed,.12,'steel_dark',6)
        k.pipe(feed-dirs*.23,feed+dirs*.33,.26,'metal_white',8)
        k.marker('port_radar_axis',(x,y,35.4),(0,0,1))
        fixture(k,(x,y+.7,36.1),RED,12.,.65,'beacon')
    k.collider((8.2,8.1,17.1),(x,y,z+8.0),tag='port_control')

    for i,(tx,ty,r,h) in enumerate(((229.3,-40.6,3.45,7.3),(233.4,-32.4,3.15,6.0),
                                   (230.5,-22.2,2.45,4.7))):
        floor=ground(tx,ty)
        k.tank(tx,ty,floor,r,h,('hull_grey','metal_teal','metal_white')[i])
        k.pipe((tx+r,ty,floor+2.4),(tx+r+2.15,ty,floor+2.4),.32,'steel_rust')
        k.torus((tx+r+1.25,ty-.57,floor+3.08),.46,.075,'metal_red',12,5,normal=(0,1,0))
        fixture(k,(tx+r*.2,ty-r-.15,floor+3.9),SODIUM,13.,.54)
    k.part()
    k.tube([(234.,-40.6,-5.6),(238.,-40.6,-5.6),(238.,-31.3,-5.6),(236.9,-30.2,-5.6),
            (236.9,-21.5,-5.6),(233.4,-21.5,-5.6)],.53,'steel_rust',10)
    for yy in (-39.4,-34.,-25.8):
        k.box((237.3,yy,-6.85),(2.4,1.23,2.2),'conc_dark')
    for ax,ay in ((219.6,-45.8),(234.4,-20.5),(227.7,-32.8)):
        k.lamp((ax,ay,ground(ax,ay)),4.2,'flood',COLD,14.,.63)


def south_quarters(k):
    # A small heavy landing pad projects off the narrow tip. Most furnishings stay under 4 m.
    x,y=236.0,-142.0;level=-7.45
    k.part()
    k.prism(chamfered_rect(x,y,23.,23.,4.2),level-1.45,level,'conc')
    for yy in (-149.,-135.4):
        z=ground(x,yy,-21.)
        soffit=level-1.40
        if soffit>z:
            k.box((x,yy,(z+soffit)/2),(7.5,4.4,soffit-z),'conc_dark')
        for sx in (-1,1):
            k.beam((x+sx*2.75,yy,z-1.8),(x+sx*10.65,yy,level-.72),.95,1.36,'steel_rust')
    for i in range(8):
        a=math.pi*(i+.5)/4;b=math.pi*(i+1.36)/4
        p=(x+8.4*math.cos(a),y+8.4*math.sin(a),level+.054)
        q=(x+8.4*math.cos(b),y+8.4*math.sin(b),level+.054)
        k.beam(p,q,.32,.072,'metal_white')
    for xx in (x-2.22,x+2.22):
        k.box((xx,y,level+.057),(.67,5.7,.08),'metal_white')
    k.box((x,y,level+.057),(4.55,.68,.082),'metal_white')
    for px,py in ((227.7,-147.3),(244.2,-147.3),(243.9,-137.9),(229.8,-134.2)):
        fixture(k,(px,py,level+.28),COLD,8.4,.47,face=(0,-1,.1))
    k.marker('port_pad',(x,y,level));k.collider((18.5,18.8,1.2),(x,y,level-.6),tag='port_pad')
    k.catwalk((242.1,-132.2,level+.10),(244.7,-125.5,-7.6),1.7)
    # Narrow warehouse on the inboard ledge; road to the pad runs east of its doors.
    x,y=217.7,-109.9;z=ground(x,y)
    k.part()
    k.box((x,y,z+.52),(11.9,20.2,1.18),'conc_dark')
    housing(k,(x,y),[(z+1,10.85,18.9),(z+6.8,10.85,18.9),(z+7.7,8.25,18.2)],
            'metal_green',.65)
    k.box((x-2.4,y+1.,z+8.45),(3.25,13.9,1.65),'hull_grey')
    for yy in (-115.25,-107.2):
        k.box((x+5.48,yy,z+3.42),(.27,4.95,4.5),'steel_dark')
        k.box((x+5.64,yy,z+3.37),(.16,4.1,3.5),'hull_grey')
        k.box((x+6.62,yy,z+5.98),(2.9,5.6,.37),'metal_red',(0,5,0))
        for sy in (-1,1):
            k.beam((x+5.55,yy+sy*2.03,z+4.85),(x+7.76,yy+sy*2.03,z+5.81),.18,'steel')
        fixture(k,(x+5.85,yy+1.95,z+4.66),SODIUM,14.,.66,face=(1,0,-.4))
    for dy in (-7.3,-3.5,2.5,6.2):
        k.part(k.rng.random())
        k.box((x-2.42,y+dy,z+8.61),(2.8,1.86,.31),'glass_warm',(0,-15,0))
    k.box((x+5.95,y,z+.63),(2.75,16.,1.15),'conc')
    k.ladder((x-3.12,y-9.63,z+.2),(x-3.12,y-9.63,z+7.2))
    k.collider((11.,18.8,6.8),(x,y,z+3.3),tag='port_warehouse')
    fixture(k,(x+2.2,y-9.62,z+4.34),COLD,14.,.68)
    capstan(k,(217.4,-94.7,ground(217.4,-94.7)),.81)
    k.lamp((224.6,-124.,ground(224.6,-124.)),4.9,'flood',SODIUM,15.,.67)


def sutures(k):
    # Each pair starts in sound rock and disappears beneath the cut surface at midspan.
    for i,(yy,offset,sag) in enumerate(((-113.,-3.8,8.7),(-96.,3.,7.5),(-38.,-5.,10.5),
                                        (-18.,4.,11.3),(6.,-3.,13.8),(21.,.9,9.7))):
        cx=bite_xc(yy)
        a=V((cx-6.7,yy,0));b=V((cx+76.,yy-20.+offset,0))
        az=math.degrees(math.atan2(b.y-a.y,b.x-a.x))
        d=(b-a).normalized();side=Z.cross(d)
        za=G.z(a.x,a.y);zb=G.z(b.x,b.y)
        if min(za,zb)<-9000:continue
        a.z=za+.9;b.z=zb+.9
        for sgn,p in ((-1,a),(1,b)):
            k.part()
            k.box(p-Z*.58,(5.8,3.7,2.65),'conc_dark',az)
            k.box(p-Z*.03,(4.65,3.15,2.1),'conc_warm',az)
            k.box(p+Z*.90,(3.42,2.61,.71),'metal_dark',az)
            k.pipe(p+side*1.55+Z*1.31,p-side*1.55+Z*1.31,.45,'steel',10)
            for j in (-1,1):k.beam(p+side*j*1.23+Z*.35,p+side*j*1.23+Z*1.68,.42,'hull_grey')
            if (i+sgn)%3==0:fixture(k,p+side*1.46+Z*1.7,SODIUM,9.3,.45)
        for j in (-1,1):
            k.cable(a+Z*1.30+side*(j*.53),b+Z*1.30+side*(j*.53),sag+.35*j,
                    .21 if i%2 else .28,'steel_dark' if j<0 else 'steel_rust',12)


def build(out,log):
    k=Kit('port',790)
    bridges(k)
    deck_and_stacks(k)
    gantry(k)
    mass_driver(k)
    pump_house(k)
    moor(k)
    tower_and_tank_farm(k)
    south_quarters(k)
    sutures(k)
    for x,y,height,colour in [(215.,-72.5,4.9,SODIUM),(232.,-66.0,5.6,COLD),
                              (246.,-56.,5.1,SODIUM),(236.,-47.6,6.35,COLD),
                              (251.5,-30.,4.5,SODIUM),(244.8,-17.5,4.9,COLD),
                              (257.2,9.3,4.4,SODIUM),(222.3,-100.4,4.5,COLD),
                              (243.,-112.1,6.1,COLD),(242.,-131.1,4.0,SODIUM)]:
        k.lamp((x,y,ground(x,y)),height,'flood',colour,17.5,.8)
    k.finalize(out,log)
