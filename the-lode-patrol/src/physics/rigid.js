import * as T from 'three';
import { clamp } from './world.js';
const V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z),
  a = V(),
  b = V(),
  d = V(),
  normal = V(),
  scratch = V(),
  spin = V(),
  q = new T.Quaternion(),
  acc = [0, 0, 0],
  hit = [0, 0, 0, 0];
export class Body {
  constructor(p, m = 1, r = 1, options = {}) {
    this.p = p.clone();
    this.old = p.clone();
    this.v = V();
    this.w = V();
    this.q = new T.Quaternion();
    this.mass = m;
    this.inv = 1 / m;
    this.r = r;
    this.ii = 1 / (.4 * m * r * r);
    this.who = 2;
    this.group = 0;
    this.groupTime = 0;
    this.kinematic = false;
    this.on = true;
    this.ground = true;
    this.mutual = true;
    this.boxes = true;
    this.damping = .035;
    this.force = V();
    this.sleep = 0;
    this.asleep = false;
    this.balls = [{
      p: V(),
      r
    }];
    Object.assign(this, options);
  }
  point(offset, out) {
    return out.copy(offset).applyQuaternion(this.q).add(this.p);
  }
  wake() {
    this.asleep = false;
    this.sleep = 0;
  }
  impact(arm, n, penetration, other, otherArm, h, mu = .55) {
    const iv = this.kinematic ? 0 : this.inv,
      ov = other && !other.kinematic ? other.inv : 0;
    if (iv + ov === 0) return;
    const rel = a.crossVectors(this.w, arm).add(this.v);
    if (other) rel.sub(b.crossVectors(other.w, otherArm).add(other.v));
    const vn = rel.dot(n);
    const cap = Math.min(penetration, Math.max(-vn, 0) * h + 2 * h),
      ratio = iv / (iv + ov);
    this.p.addScaledVector(n, cap * ratio);
    if (other) other.p.addScaledVector(n, -cap * (1 - ratio));
    if (vn >= 0) return;
    const t = scratch.copy(rel).addScaledVector(n, -vn),
      tl = t.length();
    if (tl > 1.e-6) t.multiplyScalar(1 / tl);
    const ri = spin.crossVectors(arm, n).lengthSq() * this.ii;
    const rj = other ? spin.crossVectors(otherArm, n).lengthSq() * other.ii : 0;
    const impulse = -(1 + (vn < -1 ? .22 : 0)) * vn / (iv + ov + ri + rj);
    d.copy(n).multiplyScalar(impulse).addScaledVector(t, -Math.min(mu * impulse, tl / Math.max(iv + ov, 1.e-6)));
    if (iv) {
      this.v.addScaledVector(d, iv);
      this.w.addScaledVector(spin.crossVectors(arm, d), this.ii);
    }
    if (ov) {
      other.v.addScaledVector(d, -ov);
      other.w.addScaledVector(spin.crossVectors(otherArm, d), -other.ii);
      other.wake();
    }
  }
}
export class Net {
  constructor() {
    this.nodes = [];
    this.edges = [];
    this.ground = true;
    this.drag = .55;
    this.iterations = 5;
    this.on = true;
  }
  node(p, m = 1, pin = null) {
    const n = {
      p: p.clone(),
      old: p.clone(),
      v: V(),
      f: V(),
      inv: m > 0 ? 1 / m : 0,
      pin,
      bind: V(),
      load: 0
    };
    this.nodes.push(n);
    return this.nodes.length - 1;
  }
  edge(i, j, rest = null, compliance = 1.e-6, tension = false) {
    if (rest === null) rest = this.nodes[i].p.distanceTo(this.nodes[j].p);
    const e = {
      i,
      j,
      rest,
      compliance,
      tension,
      lambda: 0
    };
    this.edges.push(e);
    return e;
  }
  step(h, world) {
    if (!this.on) return;
    for (const n of this.nodes) {
      n.old.copy(n.p);
      if (n.pin) {
        if (n.pin.body) {
          const body = n.pin.body;
          body.point(n.pin.offset, n.p);
          n.bind.copy(n.p);
          n.inv = body.kinematic ? 0 : body.inv;
        } else {
          n.pin(n.p);
          n.inv = 0;
        }
        continue;
      }
      if (!n.inv) continue;
      world.field.accel(n.p.x, n.p.y, n.p.z, acc, 4);
      n.v.x += acc[0] * h;
      n.v.y += (acc[1] - n.load * n.inv) * h;
      n.v.z += acc[2] * h;
      n.v.addScaledVector(n.f, h);
      n.v.multiplyScalar(1 / (1 + this.drag * h));
      n.p.addScaledVector(n.v, h);
    }
    for (const e of this.edges) e.lambda = 0;
    for (let pass = 0; pass < this.iterations; pass++) {
      for (const e of this.edges) {
        const a = this.nodes[e.i],
          b = this.nodes[e.j],
          dx = b.p.x - a.p.x,
          dy = b.p.y - a.p.y,
          dz = b.p.z - a.p.z,
          len = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1.e-8,
          C = len - e.rest;
        if (e.tension && C <= 0 && e.lambda === 0) continue;
        const alpha = e.compliance / (h * h),
          den = a.inv + b.inv + alpha;
        if (!den) continue;
        let dl = (-C - alpha * e.lambda) / den;
        if (e.tension) dl = Math.min(0, e.lambda + dl) - e.lambda;
        e.lambda += dl;
        const da = -a.inv * dl / len,
          db = b.inv * dl / len;
        a.p.x += dx * da;
        a.p.y += dy * da;
        a.p.z += dz * da;
        b.p.x += dx * db;
        b.p.y += dy * db;
        b.p.z += dz * db;
      }
      if (this.ground) for (const n of this.nodes) {
        if (n.pin || !n.inv) continue;
        const yy = world.ground(n.p.x, n.p.z) + .12;
        if (n.p.y < yy) n.p.y = yy;
      }
    }
    for (const n of this.nodes) {
      if (n.pin?.body) {
        const body = n.pin.body;
        if (body.kinematic) continue;
        d.copy(n.p).sub(n.bind);
        // A single tether carries its load through the fairlead. A lifting spreader has
        // several attachment points on the same body and must share their rotational mass.
        if (!this.multipleAttachments) {
          body.p.add(d);
          body.v.addScaledVector(d, 1 / h);
          const arm = scratch.copy(n.pin.offset).applyQuaternion(body.q);
          body.w.addScaledVector(spin.crossVectors(arm, d), body.ii * body.mass / h * .2);
          if (d.lengthSq() > 1.e-8) body.wake();
          continue;
        }
        const distance = d.length();
        if (distance < 1.e-9) continue;
        d.multiplyScalar(1 / distance);
        const arm = scratch.copy(n.pin.offset).applyQuaternion(body.q),
          lever = spin.crossVectors(arm, d),
          eff = body.inv + body.ii * lever.lengthSq();
        // Split an anchor correction between translation and rotation using its effective mass.
        // Use the change since the last solved anchor to remove separating velocity. The
        // pre-existing stretch is position bias and cannot impart a launch impulse.
        const pointV = a.crossVectors(body.w, arm).add(body.v);
        const solvedV = b.subVectors(n.p, n.old).multiplyScalar(1 / h);
        const vImpulse = clamp(solvedV.sub(pointV).dot(d), 0, Math.min(distance / h, 12)) / eff;
        const posImpulse = Math.min(distance, .25) / eff;
        body.p.addScaledVector(d, body.inv * posImpulse);
        const angle = lever.length() * body.ii * posImpulse;
        if (angle > 1.e-8) body.q.premultiply(q.setFromAxisAngle(a.copy(lever).normalize(), Math.min(.12, angle))).normalize();
        body.v.addScaledVector(d, body.inv * vImpulse);
        body.w.addScaledVector(lever, body.ii * vImpulse);
        if (distance > 2.e-4) body.wake();
      } else if (n.inv) n.v.copy(n.p).sub(n.old).multiplyScalar(1 / h);
    }
  }
}
export function rope(start, end, length, n = 20, comp = 2e-6) {
  const net = new Net(),
    get = (p, into) => p.body ? p.body.point(p.offset, into) : p(into),
    a = get(start, V()),
    b = get(end, V()),
    sag = Math.sqrt(Math.max(0, length * length - a.distanceToSquared(b))) * .32;
  for (let j = 0; j <= n; j++) {
    const t = j / n,
      p = a.clone().lerp(b, t);
    p.y -= 4 * sag * t * (1 - t);
    net.node(p, .8, j === 0 ? start : j === n ? end : null);
    if (j) net.edge(j - 1, j, length / n, comp, true);
  }
  net.edge(0, n, length, 1e-9, true);
  return net;
}
export class Rigids {
  constructor(world) {
    this.world = world;
    this.bodies = [];
    this.nets = [];
    this.time = 0;
  }
  body(p, m, r, opt) {
    const o = new Body(p, m, r, opt);
    this.bodies.push(o);
    return o;
  }
  step(h) {
    this.time += h;
    const w = this.world,
      ra = V(),
      rb = V(),
      pa = V(),
      pb = V();
    for (const o of this.bodies) {
      if (!o.on || o.kinematic) continue;
      if (o.asleep) {
        if (o.force.lengthSq() > .001) o.wake();else continue;
      }
      const p = o.p;
      let supported = false;
      w.field.accel(p.x, p.y, p.z, acc, o.who);
      o.v.x += (acc[0] + o.force.x) * h;
      o.v.y += (acc[1] + o.force.y) * h;
      o.v.z += (acc[2] + o.force.z) * h;
      o.v.multiplyScalar(1 / (1 + h * o.damping));
      o.old.copy(p);
      p.addScaledVector(o.v, h);
      const ang = o.w.length();
      if (ang > 1e-7) o.q.premultiply(q.setFromAxisAngle(spin.copy(o.w).multiplyScalar(1 / ang), Math.min(ang * h, .3))).normalize();
      o.w.multiplyScalar(1 / (1 + h * .045));
      for (const ball of o.balls) {
        ra.copy(ball.p).applyQuaternion(o.q);
        pa.copy(p).add(ra);
        if (o.ground) {
          const g = w.ground(pa.x, pa.z),
            dep = g + ball.r - pa.y;
          if (g > -9000 && dep > 0) {
            supported = true;
            o.impact(ra, normal.set(0, 1, 0), dep, null, null, h);
          }
        }
        if (o.boxes) {
          const list = w.staticAt(pa.x, pa.y, pa.z);
          if (list) for (const box of list) if (box.contact(pa.x, pa.y, pa.z, ball.r, hit)) {
            if (hit[1] > .5) supported = true;
            o.impact(ra, normal.set(hit[0], hit[1], hit[2]), hit[3], null, null, h, box.mu);
          }
        }
      }
      if (supported && o.force.lengthSq() < .0001 && o.v.lengthSq() + o.w.lengthSq() * o.r * o.r < .016) {
        if (++o.sleep > 90) {
          o.asleep = true;
          o.v.set(0, 0, 0);
          o.w.set(0, 0, 0);
        }
      } else o.sleep = 0;
    }
    for (let i = 0; i < this.bodies.length; i++) {
      const l = this.bodies[i];
      if (!l.on || !l.mutual) continue;
      for (let j = 0; j < i; j++) {
        const r = this.bodies[j];
        if (!r.on || !r.mutual || l.group && l.group === r.group && this.time < Math.max(l.groupTime, r.groupTime)) continue;
        if (l.p.distanceToSquared(r.p) > (l.r + r.r + 4) ** 2) continue;
        for (const ll of l.balls) for (const rr of r.balls) {
          ra.copy(ll.p).applyQuaternion(l.q);
          rb.copy(rr.p).applyQuaternion(r.q);
          pa.copy(l.p).add(ra);
          pb.copy(r.p).add(rb);
          normal.copy(pa).sub(pb);
          const len = normal.length(),
            dep = ll.r + rr.r - len;
          if (dep <= 0) continue;
          normal.multiplyScalar(1 / Math.max(len, 1e-7));
          l.impact(ra, normal, dep, r, rb, h);
        }
      }
    }
    for (const net of this.nets) net.step(h, w);
  }
}
