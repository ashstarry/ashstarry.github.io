import * as T from 'three';
import { TAG } from '../physics/world.js';
import { rockMaterial } from '../materials.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
export const V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z);
export const bl = (x, y, z) => V(x, z, -y);
export const smooth = x => (x = Math.max(0, Math.min(1, x)), x * x * (3 - 2 * x));
export const UP = V(0, 1, 0),
  dummy = new T.Object3D();
const m = new T.Matrix4(),
  iv = new T.Matrix4(),
  cur = V();
const geometries = new Map();
export function geometry(app, part, name) {
  const key = part + '/' + name;
  if (geometries.has(key)) return geometries.get(key);
  const root = app.find(part, name);
  let g;
  if (root) {
    root.updateWorldMatrix(true, true);
    iv.copy(root.matrixWorld).invert();
    const pieces = [];
    root.traverse(o => {
      if (o.isMesh) {
        let v = o.geometry.clone().applyMatrix4(m.multiplyMatrices(iv, o.matrixWorld));
        for (const n of Object.keys(v.attributes)) if (n !== 'position' && n !== 'normal') v.deleteAttribute(n);
        if (v.index) v = v.toNonIndexed();
        pieces.push(v);
      }
    });
    if (pieces.length) g = mergeGeometries(pieces);
  }
  if (!g) g = new T.IcosahedronGeometry(1, 0);
  geometries.set(key, g);
  return g;
}
export function instances(app, g, mat, max) {
  const mesh = new T.InstancedMesh(g, mat, max);
  mesh.instanceMatrix.setUsage(T.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.count = 0;
  app.scene.add(mesh);
  return mesh;
}
export function setInstance(mesh, i, x, y, z, s, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) {
  dummy.position.set(x, y, z);
  dummy.rotation.set(rx, ry, rz);
  dummy.scale.set(s * sx, s * sy, s * sz);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
}
export function segments(app, pairs, r = .25, color = 0x55483f) {
  const msh = instances(app, new T.CylinderGeometry(r, r, 1, 5, 1), new T.MeshStandardMaterial({
    color,
    roughness: .77,
    metalness: .31
  }), pairs);
  return msh;
}
export function lineInstance(mesh, i, a, b) {
  dummy.position.copy(a).lerp(b, .5);
  cur.copy(b).sub(a);
  const l = cur.length();
  dummy.scale.set(1, Math.max(l, .001), 1);
  dummy.quaternion.setFromUnitVectors(UP, cur.multiplyScalar(1 / Math.max(l, .001)));
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
}
export function updateLines(mesh, points) {
  for (let i = 1; i < points.length; i++) lineInstance(mesh, i - 1, points[i - 1].p || points[i - 1], points[i].p || points[i]);
  mesh.count = points.length - 1;
  mesh.instanceMatrix.needsUpdate = true;
}
export class GrainView {
  constructor(app, w) {
    this.w = w;
    this.mesh = ['chunk_a', 'chunk_b', 'chunk_c'].map((n, i) => instances(app, geometry(app, 'rocks', n), rockMaterial(i + 12, 2.4, 0xffffff, {
      GRAIN: ''
    }), Math.ceil(w.cap / 3) + 1));
    this.color = new T.Color();
    for (const m of this.mesh) m.setColorAt(0, this.color);
  }
  frame() {
    const w = this.w,
      bins = [0, 0, 0],
      color = this.color,
      tones = [[.80, .80, .86], [2.3, 2, 1.55], [1.25, .85, .6], [.55, .55, .6]];
    for (let k = 0; k < w.count; k++) {
      const i = w.order[k],
        v = i % 3,
        j = bins[v]++,
        tag = w.tag[i],
        flight = tag === TAG.SHOT || tag === TAG.THROWN,
        haul = flight || tag === TAG.CONE || tag === TAG.CABLE || tag === TAG.WELL,
        s = w.radius[i] * (flight ? 1.26 : 1),
        m = this.mesh[v];
      setInstance(m, j, w.x[i], w.y[i], w.z[i], s, w.rx[i], w.ry[i], w.rz[i], 1.12, .92, 1);
      const c = tones[w.kind[i]];
      color.setRGB(...c).multiplyScalar(w.shine[i] * (haul ? 2.05 : 1));
      m.setColorAt(j, color);
    }
    for (let v = 0; v < 3; v++) {
      const m = this.mesh[v];
      m.count = bins[v];
      m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
    }
  }
}
