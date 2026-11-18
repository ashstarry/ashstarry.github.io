"""Pressure workwear for the gallery crews. Template faces +X; boot soles are at Z=0."""
import math

from lib.kit import Kit, MATS, V


CLOTH = 'metal_watch_canvas'
DARK = 'metal_watch_rubber'
IVORY = 'metal_watch_ivory'
FRAME = 'metal_watch_hardware'
VISOR = 'glass_watch'


def shells(k, rows, material, facets=12):
    """Elliptical sections in ascending height, with independent shoulder/hip taper."""
    rings = [[(x + rx * math.cos(a * math.tau / facets),
               y + ry * math.sin(a * math.tau / facets), z) for a in range(facets)]
             for z, x, y, rx, ry in rows]
    k.loft(rings, material, curve=True)


def sleeve(k, start, end, sections, material):
    start, end = V(start), V(end)
    axis = (end - start).normalized()
    side = V((1, 0, 0))
    side = (side - axis * side.dot(axis)).normalized()
    cross = axis.cross(side)
    rings = []
    for t, rx, ry in sections:
        p = start.lerp(end, t)
        rings.append([p + side * (rx * math.cos(a * math.tau / 10)) +
                      cross * (ry * math.sin(a * math.tau / 10)) for a in range(10)])
    k.loft(rings, material, curve=True)


def mask(k, width, levels, material):
    """Curved wraparound visor and its gasket, separate from the pressure helmet."""
    rows = []
    for z, rx, ry, dip in levels:
        ring = []
        for i in range(17):
            a = math.radians(width) * (i / 8 - 1)
            ring.append((.036 + rx * math.cos(a), ry * math.sin(a), z + dip * (1 - math.cos(a))))
        rows.append(ring)
    for lower, upper in zip(rows, rows[1:]):
        for i in range(16):
            k.face([lower[i], lower[i+1], upper[i+1], upper[i]], material, True)


def work_suit(k):
    with k.into('watch_suit'):
        for s in (-1, 1):
            y = s * .115
            dx = .032 * s
            k.part()
            # Broad, separately moulded welt, toe cap and ankle gaiter.
            shells(k, [(0, dx+.042, y, .160, .089), (.035, dx+.044, y, .168, .097),
                       (.071, dx+.043, y, .166, .096), (.104, dx+.034, y, .155, .090)], DARK)
            shells(k, [(.071, dx+.04, y, .152, .088), (.123, dx+.026, y, .149, .094),
                       (.18, dx-.012, y, .109, .095), (.224, dx-.016, y, .093, .085)], FRAME)
            shells(k, [(.198, dx-.016, y, .098, .088), (.24, dx-.016, y, .099, .090),
                       (.285, dx-.013, y, .086, .080)], DARK)
            shells(k, [(.239, dx-.015, y, .090, .085), (.285, dx-.01, y, .100, .092),
                       (.38, dx-.008, y, .093, .089), (.49, dx+.021, y, .099, .094),
                       (.539, dx+.034, y, .093, .092), (.606, dx+.038, y, .111, .106),
                       (.68, dx+.017, y, .112, .105), (.84, dx, y, .128, .114),
                       (.957, dx-.015, y*.91, .129, .117), (1.020, dx-.02, y*.84, .119, .114)], CLOTH)
            shells(k, [(.298, dx-.011, y, .101, .094), (.329, dx-.011, y, .099, .093)], IVORY)
            k.sphere((dx+.107, y, .579), (.050, .073, .082), FRAME, 10, 6)
        shells(k, [(.945, -.015, 0, .166, .205), (1.024, -.017, 0, .180, .216),
                   (1.115, -.012, 0, .163, .180), (1.245, -.010, 0, .124, .182),
                   (1.402, .004, 0, .149, .213), (1.498, .009, 0, .141, .245),
                   (1.56, .018, 0, .105, .165)], CLOTH, 16)
        shells(k, [(1.061, -.012, 0, .177, .213), (1.127, -.008, 0, .164, .196)], DARK, 16)
        k.box((.159,-.017,1.10), (.03,.08,.048), FRAME)
        k.box((.113,.141,1.26), (.039,.10,.121), CLOTH)
        k.beam((.118,.183,1.44),(.150,.078,1.19),.032,.022,IVORY)
        k.beam((.118,-.183,1.44),(.150,-.079,1.19),.032,.022,IVORY)
        for s in (-1, 1):
            k.part()
            shoulder = (.005,s*.223,1.485)
            elbow = (-.039 if s>0 else .024,s*.287,1.285)
            wrist = (.078 if s>0 else .141,s*.280,1.122 if s>0 else 1.195)
            hand = (.096 if s>0 else .181,s*.271,1.042 if s>0 else 1.119)
            sleeve(k,elbow,shoulder,[(0,.078,.078),(.22,.091,.089),(.70,.103,.098),
                                     (.86,.100,.090),(1,.073,.072)],CLOTH)
            sleeve(k,elbow,shoulder,[(.46,.101,.095),(.60,.103,.098)],IVORY)
            sleeve(k,wrist,elbow,[(0,.070,.067),(.17,.077,.075),(.65,.084,.081),
                                  (.9,.076,.077),(1,.081,.077)],CLOTH)
            sleeve(k,wrist,elbow,[(0,.073,.072),(.18,.081,.077)],FRAME)
            sleeve(k,hand,wrist,[(0,.037,.034),(.32,.060,.049),(.70,.067,.057),(1,.057,.057)],DARK)
            k.sphere((hand[0]+.040,hand[1]-s*.027,hand[2]+.042),(.029,.027,.048),DARK,8,5)
        # The backpack bolts to the harness; two bottle bands and a pressure
        # manifold make its function legible on the silhouettes looking away.
        k.box((-.145,0,1.315),(.115,.299,.426),DARK)
        for s in (-1,1):
            y = s*.078
            shells(k,[(1.126,-.224,y,.052,.053),(1.156,-.224,y,.070,.067),
                      (1.395,-.221,y,.070,.067),(1.455,-.216,y,.054,.054),
                      (1.474,-.216,y,.031,.029)],IVORY)
            for z in (1.215,1.373):
                shells(k,[(z,-.223,y,.073,.070),(z+.029,-.223,y,.073,.070)],FRAME)
        k.box((-.234,0,1.493),(.082,.214,.063),FRAME)
        k.tube([(-.244,.084,1.50),(-.251,.174,1.56),(-.180,.204,1.62),(-.088,.181,1.66)],
               .022,DARK,7)
        shells(k,[(1.503,.018,0,.101,.129),(1.55,.020,0,.143,.148),
                  (1.593,.025,0,.129,.140),(1.619,.031,0,.126,.139)],FRAME,16)
        # A heavy mining helmet, with a projecting brow above a green smoked visor.
        shells(k,[(1.584,.024,0,.127,.137),(1.637,.027,0,.165,.163),
                  (1.739,.033,0,.175,.181),(1.839,.028,0,.187,.187),
                  (1.912,.015,0,.174,.167),(1.968,.000,0,.119,.130),
                  (1.997,.003,0,.050,.057)],IVORY,20)
        mask(k,73,[(1.638,.168,.180,.061),(1.679,.193,.193,.027),
                   (1.805,.204,.192,.003),(1.837,.198,.190,-.006)], DARK)
        mask(k,64,[(1.668,.182,.191,.039),(1.695,.208,.204,.011),
                   (1.802,.209,.202,.004),(1.817,.205,.199,.002)], VISOR)
        shells(k,[(1.821,.047,0,.203,.189),(1.842,.050,0,.211,.192),
                  (1.858,.044,0,.196,.191)],IVORY,20)
        for s in (-1,1):
            y = .167*s
            k.pipe((-.018,y,1.734),(-.018,y+s*.030,1.734),.069,FRAME,14)
            k.pipe((-.018,y+s*.029,1.734),(-.018,y+s*.039,1.734),.044,IVORY,12)
        # An optical lens on a real waist fitting keeps a close camera legible
        # without creating a point sprite in the opening panorama.
        k.box((.102,-.169,1.102),(.092,.071,.080),FRAME)
        k.pipe((.145,-.169,1.103),(.153,-.169,1.103),.028,IVORY,10)


def build(out, log):
    MATS.update({CLOTH: ((.43,.152,.055),.87,0), DARK: ((.043,.046,.043),.84,0),
                 IVORY: ((.53,.49,.354),.64,0), FRAME: ((.12,.137,.139),.64,.12),
                 VISOR: ((.040,.090,.094),.18,.14)})
    k = Kit('watchcrew', 349)
    work_suit(k)
    k.finalize(out, log)
