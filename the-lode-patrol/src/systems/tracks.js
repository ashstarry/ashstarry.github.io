import * as T from 'three';
import { V, UP } from './view.js';
export function pose() {
  return {
    p: V(),
    t: V(1, 0, 0),
    up: V(0, 1, 0),
    side: V(0, 0, 1),
    q: new T.Quaternion(),
    kind: 'road'
  };
}
const matrix = new T.Matrix4();
export class Route {
  constructor(data, closed = false) {
    this.closed = closed;
    this.nodes = [];
    this.len = 0;
    for (const d of data) {
      const p = V(...(d.p || d)),
        prev = this.nodes.at(-1),
        len = prev ? p.distanceTo(prev.p) : 0;
      if (prev && len < .0001) continue;
      this.len += len;
      this.nodes.push({
        p,
        up: V(...(d.up || [0, 1, 0])).normalize(),
        t: d.tangent ? V(...d.tangent).normalize() : null,
        s: this.len,
        kind: d.kind || 'road'
      });
    }
    for (let i = 0; i < this.nodes.length; i++) {
      const n = this.nodes[i];
      n.t ||= this.nodes[Math.min(i + 1, this.nodes.length - 1)].p.clone().sub(this.nodes[Math.max(0, i - 1)].p).normalize();
    }
  }
  at(s, out, offset = 0) {
    const n = this.nodes,
      last = n.length - 1,
      L = this.len;
    if (this.closed) s = (s % L + L) % L;
    const edge = s < 0 ? s : s > L ? s - L : 0;
    s = Math.max(0, Math.min(L, s));
    let lo = 0,
      hi = last;
    while (lo + 1 < hi) {
      const mid = lo + hi >> 1;
      if (n[mid].s <= s) lo = mid;else hi = mid;
    }
    const a = n[lo],
      b = n[hi],
      u = (s - a.s) / Math.max(.00001, b.s - a.s);
    out.p.copy(a.p).lerp(b.p, u);
    out.t.copy(a.t).lerp(b.t, u).normalize();
    out.up.copy(a.up).lerp(b.up, u).normalize();
    out.side.crossVectors(out.t, out.up);
    if (out.side.lengthSq() < .001) out.side.set(0, 0, 1);
    out.side.normalize();
    out.up.crossVectors(out.side, out.t).normalize();
    out.p.addScaledVector(out.side, offset).addScaledVector(out.t, edge);
    out.q.setFromRotationMatrix(matrix.makeBasis(out.t, out.up, out.side));
    out.kind = a.kind;
    return out;
  }
}
