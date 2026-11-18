# The Lode modeling guide

Work in Blender coordinates and metres. X points east, Y north and Z up. The opening camera looks across the disc from the southeast. Block out the silhouette first. Add footings, load-bearing sections, maintenance walks, pipes, equipment and lighting. A baffle, an anchor block or a hatch hinge should explain what the machine does. Leave large panels for the weathering shader. Keep roads, the ore arc, the tractor column, the bridge lanes and railway clearances open.

## Build a part

Each module exposes `build(out, log)`. The habitat in `parts/habitat.py` is the reference. Import `Kit` and `V` from `lib.kit`, `G` from `lib.ground`, and shared site coordinates from `lib.layout`. Construct the part with `K = Kit('part_name')`. `G.z(x, y)` returns the surface elevation, or −9999 outside the rock. Call `K.part(user=0)` for each visually distinct assembly so it receives its own weathering seed. Finish with `K.finalize(out, log)` to export the GLB and matching JSON.

## Geometry and materials

See `lib/kit.py` for the complete kit. `box(center, size, mat, rot=0)` accepts a Z rotation or three Euler angles in degrees. Common structural primitives are `beam(a, b, w, h=None, mat='steel_dark')`, `pipe(a, b, r, mat, n=8)`, `truss(a, b, w, h, mat, bays, member)` and `tower((x, y), z0, z1, base, top, mat, bays, member)`. Rings passed to `loft(rings, mat, caps, curve)` wind counterclockwise when viewed from above. Use `face(points, mat, curve=False, color=None)` for individual panels and `torus(center, major, minor, mat, n, m, normal)` for pipe bends and chain links. Vertex colors are linear RGBA. The kit batches geometry by moving object and material. Each face carries metric coordinates in UV0, half extents in UV1 and the part and face seeds in its vertex colors.

## Pivots and runtime data

Inside `with K.into('name', parent='parent', loc=(gx, gy, gz)):`, keep drawing in absolute modeling coordinates. The location is the world-space pivot. Export converts it to the parent’s frame. Use `loc=(0, 0, 0)` for a root template. Node names are case-sensitive.

Register markers with `K.marker(name, pos, axis=(1, 0, 0), up=(0, 0, 1))`, lamps with `K.light(pos, color, radius, power, kind)` and colliders with `K.collider(size, loc, rot=0, tag='solid', friction=.75)`. JSON positions, directions and quaternions use Three.js axes. Marker positions use world coordinates. Lamps use their parent node’s local coordinates and are registered on visible template instances. Path samples take the form `{'p': three(position), 'up': three(up)}`.

## Verify the export

```sh
blender -b --offline-mode --factory-startup --python-exit-code 1 --python blender/build.py -- habitat
blender -b --factory-startup --python-exit-code 1 --python blender/preview.py -- habitat
```

Inspect the three-quarter preview in `qa/`. Check dimensions, winding, axes and road clearance. Record named moving objects, markers, colliders and triangle counts when delivering a new part.
