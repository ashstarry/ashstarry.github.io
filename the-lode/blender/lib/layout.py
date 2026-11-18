"""Shared site plan in Blender metres: east, north, up."""
import math

R_DISC = 220.0
PIT_C = (-78., 12.)
PIT_A, PIT_B, PIT_ROT, PIT_DEPTH, PIT_ZREF = 98.,84., math.radians(20),76.,1.
WALL_TH, WALL_DIST, WALL_HALF = math.radians(98),76.,36.
SHARD_OFF, SHARD_DROP = (70.,-20.), -8.
WX0, WX1, WY0, WY1, NFINE = -256.,320.,-288.,288.,2048
CELL = (WX1-WX0)/NFINE
BRIDGE_W, BRIDGE_E=(131.,-59.5),(207.,-79.5)
GANTRY_BASE, BWE_POS, TOWER_POS=(27.,13.),(-194.,2.),(96.,146.)
WALL_ZTOP,WALL_ZFOOT=1.6,-73.4

def bite_xc(y):
    return 138. + .0045*(y+60.)**2

ROADS=[
 ('haul',13,[(2,-25),(18,-30),(36,-26)]),('main',13,[(36,-26),(58,-50),(94,-60),(129,-58)]),
 ('north',12,[(-128,100),(-90,106),(-50,104),(-20,92),(8,70),(30,48),(38,22)]),
 ('hab',9,[(30,48),(52,66),(70,80),(92,100)]),('south',10,[(36,-26),(24,-70),(4,-110),(-6,-144)]),
 ('west',10,[(4,-110),(-56,-120),(-118,-118),(-166,-66),(-188,-30)]),
 ('port',12,[(206,-80),(236,-74),(246,-30),(250,12)]),('port_s',10,[(236,-74),(232,-112),(220,-140)])]
PADS=[('bwe',-194,2,44,58,0,None),('plant',74,-4,104,92,0,0.),('hab_low',84,100,104,44,0,5.),('hab_high',100,150,110,62,0,10.),
 ('depot',-6,-152,52,34,10,None),('walltop',-89,101,84,14,-8,1.),('port',246,-62,52,150,-6,-8.),
 ('abut_w',121,-57,14,22,-16,-1.),('pier_w',-206,-62,14,14,0,None),('pier_s',58,-196,14,14,0,None),
 ('pier_n',-120,176,14,14,0,None),('pier_a',-128,-162,14,14,0,None),('pier_c',14,204,14,14,0,None)]
ANCHORS=[(-128,-162),(-120,176),(14,204)]
CRATERS=[(-158,-128,15,3.6),(62,-176,9,2.),(-20,178,11,2.6),(-196,78,8,1.8),(118,-150,6,1.4)]
def three(p):
    return [float(p[0]),float(p[2]),float(-p[1])]
def wall_path():
    n=(math.cos(WALL_TH),math.sin(WALL_TH))
    # s increases out of the pit. The vertical deck is four metres in front of the face.
    face=(PIT_C[0]+n[0]*WALL_DIST, PIT_C[1]+n[1]*WALL_DIST)
    pts=[]
    def add(s,z,ang):
        pts.append({'p':three((face[0]+s*n[0],face[1]+s*n[1],z)),
                    'up':three((-n[0]*math.sin(ang),-n[1]*math.sin(ang),math.cos(ang)))})
    for i in range(9): add(30-i*3, WALL_ZTOP,0)
    for i in range(1,19):
        a=i*math.pi/36;add(6-10*math.sin(a),WALL_ZTOP-10+10*math.cos(a),a)
    for i in range(1,19): add(-4,WALL_ZTOP-10+(WALL_ZFOOT+10-(WALL_ZTOP-10))*i/18,math.pi/2)
    for i in range(1,19):
        a=i*math.pi/36;add(-14+10*math.cos(a),WALL_ZFOOT+10-10*math.sin(a),math.pi/2-a)
    for i in range(1,12):add(-14-34*i/11,WALL_ZFOOT,0)
    return pts
