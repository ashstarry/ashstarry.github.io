export const FREE = 1,
  SLEEP = 2,
  HELD = 3;
export const TAG = Object.freeze({
  GROUND: 0,
  HALO: 1,
  BOOM: 2,
  DISCHARGE: 3,
  AMMO: 4,
  SHOT: 5,
  MITT: 6,
  CV1: 7,
  JIG: 8,
  CV2: 9,
  WELL: 10,
  BIN: 11,
  CV3: 12,
  WASTE: 13,
  TRAIN: 14,
  THROWN: 15,
  SHIP: 16,
  TRUCK: 17,
  DUMP: 18,
  CONE: 19,
  CABLE: 20,
  SPILL: 21
});
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export function rng(seed = 0x41c6ce57) {
  return () => {
    seed |= 0;
    seed = seed + 0x6d2b79f5 | 0;
    let x = Math.imul(seed ^ seed >>> 15, 1 | seed);
    x = x + Math.imul(x ^ x >>> 7, 61 | x) ^ x;
    return ((x ^ x >>> 14) >>> 0) / 4294967296;
  };
}
export class Height {
  constructor(values) {
    this.values = values;
  }
  at(x, z) {
    const u = (x + 256) * 1023 / 576,
      v = (288 - z) * 1023 / 576;
    if (u < 0 || v < 0 || u >= 1023 || v >= 1023) return -9999;
    const i = u | 0,
      j = v | 0,
      k = j * 1024 + i,
      a = u - i,
      b = v - j,
      h = this.values,
      h0 = h[k],
      h1 = h[k + 1],
      h2 = h[k + 1024],
      h3 = h[k + 1025];
    if (Math.min(h0, h1, h2, h3) > -9000) return (h0 + (h1 - h0) * a) * (1 - b) + (h2 + (h3 - h2) * a) * b;
    const w0 = h0 > -9000 ? (1 - a) * (1 - b) : 0,
      w1 = h1 > -9000 ? a * (1 - b) : 0,
      w2 = h2 > -9000 ? (1 - a) * b : 0,
      w3 = h3 > -9000 ? a * b : 0,
      w = w0 + w1 + w2 + w3;
    return w > .5 ? (w0 * h0 + w1 * h1 + w2 * h2 + w3 * h3) / w : -9999;
  }
}
export class Field {
  constructor(world) {
    this.world = world;
    this.plateG = 2.6;
    this.plateTop = 46;
    this.plateFade = 26;
    this.zones = [];
    this.lode = {
      x: -78,
      y: -60.5,
      z: -12,
      k: 70,
      tide: 0,
      swirl: 30,
      rmin: 7,
      on: true
    };
    this.noPlate = 24;
    this.wave = {
      x: -78,
      z: -12,
      r: -1000,
      a: 0
    };
    this.tmp = [0, 0, 0];
  }
  addZone(z) {
    z.mode ||= 'replace';
    z.on = z.on !== false;
    this.zones.push(z);
    return z;
  }
  accel(x, y, z, o, who = 0) {
    let gx = 0,
      gy = 0,
      gz = 0;
    const ground = who & this.noPlate ? -9999 : this.world.ground(x, z);
    if (ground > -9000) {
      const h = y - ground;
      let f = h < this.plateTop ? 1 : Math.max(0, 1 - (h - this.plateTop) / this.plateFade);
      if (h < -6) f = 0;
      gy = -this.plateG * f;
      const w = this.wave;
      if (w.a > 0) {
        const d = Math.abs(Math.hypot(x - w.x, z - w.z) - w.r);
        if (d < 34) gy *= 1 - 1.7 * w.a * (1 - d / 34);
      }
    }
    for (const a of this.zones) {
      if (!a.on || a.who && !(a.who & who) || x < a.minx || x > a.maxx || y < a.miny || y > a.maxy || z < a.minz || z > a.maxz) continue;
      const w = a.test(x, y, z);
      if (w <= 0) continue;
      let g = a.g;
      if (a.fn) {
        g = this.tmp;
        a.fn(x, y, z, g);
      }
      if (a.mode === 'add') {
        gx += g[0] * w;
        gy += g[1] * w;
        gz += g[2] * w;
      } else {
        gx += (g[0] - gx) * w;
        gy += (g[1] - gy) * w;
        gz += (g[2] - gz) * w;
      }
    }
    const L = this.lode;
    if (L.on) {
      const dx = L.x - x,
        dy = L.y - y,
        dz = L.z - z,
        r2 = dx * dx + dy * dy + dz * dz,
        r = Math.sqrt(r2),
        rr = Math.max(L.rmin, r),
        a = L.k * (1 + L.tide) / (rr * Math.max(r, 1.e-8));
      gx += dx * a;
      gy += dy * a;
      gz += dz * a;
      if (r < 70) {
        const s = L.swirl * (1 + .6 * L.tide) / (rr * rr) * (1 - r / 70);
        gx -= dz * s;
        gz += dx * s;
      }
    }
    o[0] = gx;
    o[1] = gy;
    o[2] = gz;
    return o;
  }
}
// The linear hash makes the 27 neighbour keys constant offsets. Cell coordinates
// are still compared, so collisions in the 16-bit table cannot invent contacts.
const hash = (a, b, c) => a * 199 + b * 11329 + c * 41 & 65535;
const neighbors = new Int32Array(27);
for (let dx = -1, k = 0; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) neighbors[k++] = dx * 199 + dy * 11329 + dz * 41;
const cellKey = (a, b, c) => ((a + 512) * 1024 + (b + 512)) * 1024 + c + 512;
export class Box {
  constructor(d) {
    Object.assign(this, d);
    this.q ||= [0, 0, 0, 1];
    this.v = d.surfaceVelocity || [0, 0, 0];
    this.mu = d.mu ?? .75;
    this.on = true;
    this.extent = [0, 0, 0];
    this.gridExtent = [0, 0, 0];
    this.cache();
  }
  cache() {
    const [x, y, z, w] = this.q;
    this.m = [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)];
    const m = this.m,
      h = this.h;
    for (let axis = 0; axis < 3; axis++) {
      const j = axis * 3;
      this.extent[axis] = Math.abs(m[j]) * h[0] + Math.abs(m[j + 1]) * h[1] + Math.abs(m[j + 2]) * h[2];
      this.gridExtent[axis] = this.extent[axis] + 1.3;
    }
  }
  contact(x, y, z, r, out) {
    if (!this.on) return false;
    const a = x - this.p[0],
      b = y - this.p[1],
      c = z - this.p[2],
      m = this.m,
      h = this.h;
    if (Math.abs(a) > this.extent[0] + r || Math.abs(b) > this.extent[1] + r || Math.abs(c) > this.extent[2] + r) return false;
    const u = m[0] * a + m[3] * b + m[6] * c,
      v = m[1] * a + m[4] * b + m[7] * c,
      w = m[2] * a + m[5] * b + m[8] * c;
    if (Math.abs(u) > h[0] + r || Math.abs(v) > h[1] + r || Math.abs(w) > h[2] + r) return false;
    let nx = u - clamp(u, -h[0], h[0]),
      ny = v - clamp(v, -h[1], h[1]),
      nz = w - clamp(w, -h[2], h[2]),
      d = Math.sqrt(nx * nx + ny * ny + nz * nz),
      depth;
    if (d > 1.e-7) {
      depth = r - d;
      if (depth <= 0) return false;
      nx /= d;
      ny /= d;
      nz /= d;
    } else {
      const xx = h[0] - Math.abs(u),
        yy = h[1] - Math.abs(v),
        zz = h[2] - Math.abs(w);
      depth = r + Math.min(xx, yy, zz);
      nx = ny = nz = 0;
      if (xx <= yy && xx <= zz) nx = Math.sign(u) || 1;else if (yy <= zz) ny = Math.sign(v) || 1;else nz = Math.sign(w) || 1;
    }
    out[0] = m[0] * nx + m[1] * ny + m[2] * nz;
    out[1] = m[3] * nx + m[4] * ny + m[5] * nz;
    out[2] = m[6] * nx + m[7] * ny + m[8] * nz;
    out[3] = depth;
    return true;
  }
}
export class World {
  constructor(ground, cap = 7000) {
    this.ground = ground;
    this.field = new Field(this);
    this.cap = cap;
    this.count = 0;
    this.time = 0;
    this.tick = 0;
    this.rand = rng(27183);
    this.acc = [0, 0, 0];
    this.hit = [0, 0, 0, 0];
    this.grid = new Map();
    this.dynamicGrid = new Map();
    this.movingBuckets = [];
    this.moving = [];
    this.boxes = [];
    this.spheres = [];
    this.forces = [];
    for (const k of ['x', 'y', 'z', 'ox', 'oy', 'oz']) this[k] = new Float64Array(cap);
    for (const k of ['vx', 'vy', 'vz', 'rx', 'ry', 'rz', 'wx', 'wy', 'wz', 'radius', 'age', 'stageAge', 'shine', 'nx', 'ny', 'nz', 'vin', 'mu', 'svx', 'svy', 'svz']) this[k] = new Float32Array(cap);
    for (const k of ['state', 'kind', 'tag', 'sleep']) this[k] = new Uint8Array(cap);
    this.owner = new Int16Array(cap);
    this.order = new Uint16Array(cap);
    this.slot = new Uint16Array(cap);
    this.free = Array.from({
      length: cap
    }, (_, i) => cap - i - 1);
    this.counts = new Int32Array(32);
    this.head = new Int32Array(65536);
    this.stamp = new Int32Array(65536);
    this.next = new Int32Array(cap);
    this.cx = new Int32Array(cap);
    this.cy = new Int32Array(cap);
    this.cz = new Int32Array(cap);
    this.freeOrder = new Uint16Array(cap);
    this.activeN = 0;
    this.neighborMask = new Uint32Array(65536);
    this.bucketsLast = new Uint16Array(cap);
    this.bucketsNow = new Uint16Array(cap);
    this.bucketsLastCount = 0;
    this.bucketsNowCount = 0;
  }
  indexBox(box, grid) {
    const p = box.p,
      b = box.gridExtent;
    for (let a = Math.floor((p[0] - b[0]) / 8); a <= Math.floor((p[0] + b[0]) / 8); a++) for (let y = Math.floor((p[1] - b[1]) / 8); y <= Math.floor((p[1] + b[1]) / 8); y++) for (let z = Math.floor((p[2] - b[2]) / 8); z <= Math.floor((p[2] + b[2]) / 8); z++) {
      const k = cellKey(a, y, z);
      let items = grid.get(k);
      if (!items) grid.set(k, items = []);
      if (grid === this.dynamicGrid && !items.length) this.movingBuckets.push(items);
      items.push(box);
    }
  }
  addBox(d, moving = false) {
    const box = new Box(d);
    this.boxes.push(box);
    if (moving) this.moving.push(box);else this.indexBox(box, this.grid);
    return box;
  }
  staticAt(x, y, z) {
    return this.grid.get(cellKey(Math.floor(x / 8), Math.floor(y / 8), Math.floor(z / 8)));
  }
  spawn(tag, x, y, z, opt = {}) {
    if (!this.free.length) return -1;
    const i = this.free.pop();
    this.slot[i] = this.count;
    this.order[this.count++] = i;
    this.state[i] = opt.state || FREE;
    this.tag[i] = tag;
    this.counts[tag]++;
    this.kind[i] = opt.kind || 0;
    this.owner[i] = opt.owner ?? -1;
    this.radius[i] = opt.r || .35 + .55 * this.rand();
    this.age[i] = this.stageAge[i] = this.sleep[i] = 0;
    this.x[i] = this.ox[i] = x;
    this.y[i] = this.oy[i] = y;
    this.z[i] = this.oz[i] = z;
    this.vx[i] = opt.vx || 0;
    this.vy[i] = opt.vy || 0;
    this.vz[i] = opt.vz || 0;
    this.rx[i] = this.rand() * 6;
    this.ry[i] = this.rand() * 6;
    this.rz[i] = this.rand() * 6;
    this.wx[i] = this.rand() * 1.8 - .9;
    this.wy[i] = this.rand() * 1.8 - .9;
    this.wz[i] = this.rand() * 1.8 - .9;
    this.shine[i] = .82 + .36 * this.rand();
    return i;
  }
  relabel(i, tag) {
    this.counts[this.tag[i]]--;
    this.tag[i] = tag;
    this.counts[tag]++;
    this.stageAge[i] = 0;
    this.wake(i);
  }
  kill(i) {
    if (!this.state[i]) return;
    this.counts[this.tag[i]]--;
    this.state[i] = 0;
    const last = this.order[--this.count];
    this.order[this.slot[i]] = last;
    this.slot[last] = this.slot[i];
    this.free.push(i);
  }
  wake(i) {
    if (this.state[i] === SLEEP) this.state[i] = FREE;
    this.sleep[i] = 0;
  }
  hold(i, tag, owner) {
    this.relabel(i, tag);
    this.owner[i] = owner;
    this.state[i] = HELD;
  }
  release(i, tag, x, y, z, vx = 0, vy = 0, vz = 0) {
    this.relabel(i, tag);
    this.owner[i] = -1;
    this.state[i] = FREE;
    this.x[i] = this.ox[i] = x;
    this.y[i] = this.oy[i] = y;
    this.z[i] = this.oz[i] = z;
    this.vx[i] = vx;
    this.vy[i] = vy;
    this.vz[i] = vz;
  }
  insert(i) {
    const cx = this.cx[i] = Math.floor(this.x[i] / 2),
      cy = this.cy[i] = Math.floor(this.y[i] / 2),
      cz = this.cz[i] = Math.floor(this.z[i] / 2),
      k = hash(cx, cy, cz);
    const lastSeen = this.stamp[k];
    this.next[i] = lastSeen === this.tick ? this.head[k] : -1;
    if (lastSeen !== this.tick) {
      this.bucketsNow[this.bucketsNowCount++] = k;
      if (lastSeen !== this.tick - 1 || this.tick === 1) this.updateNeighbors(k, true);
    }
    this.head[k] = i;
    this.stamp[k] = this.tick;
  }
  updateNeighbors(key, present) {
    // Substeps rarely change bucket occupancy. Only a gained or lost bucket
    // changes the 27-bit lookup in the surrounding cells.
    for (let i = 0; i < neighbors.length; i++) {
      const center = (key - neighbors[i]) & 65535;
      const bit = 1 << i;
      if (present) this.neighborMask[center] |= bit;
      else this.neighborMask[center] &= ~bit;
    }
  }
  pairs(i, h) {
    const cx = this.cx[i],
      cy = this.cy[i],
      cz = this.cz[i];
    let x = this.x[i],
      y = this.y[i],
      z = this.z[i],
      r = this.radius[i];
    const mid = hash(cx, cy, cz);
    let occupied = this.neighborMask[mid];
    while (occupied) {
      const bit = 31 - Math.clz32(occupied & -occupied);
      occupied &= occupied - 1;
      const key = (mid + neighbors[bit]) & 65535;
      for (let j = this.head[key]; j >= 0; j = this.next[j]) {
        if (i === j || j > i && this.state[j] === FREE) continue;
        const rad = r + this.radius[j],
          dx = x - this.x[j];
        if (Math.abs(dx) >= rad) continue;
        const dy = y - this.y[j],
          dz = z - this.z[j],
          d2 = dx * dx + dy * dy + dz * dz;
        if (d2 >= rad * rad) continue;
        const d = Math.sqrt(d2),
          inv = 1 / Math.max(d, 1.e-7),
          nx = d > 1.e-7 ? dx * inv : 1,
          ny = dy * inv,
          nz = dz * inv;
        const vn = (this.vx[i] - this.vx[j]) * nx + (this.vy[i] - this.vy[j]) * ny + (this.vz[i] - this.vz[j]) * nz;
        if (this.state[j] === SLEEP && vn < -.45) this.wake(j);
        const fj = this.state[j] === SLEEP ? 0 : .5,
          fi = 1 - fj,
          dep = rad - d,
          old = Math.max(0, dep - Math.max(0, -vn) * h);
        x += nx * dep * fi;
        y += ny * dep * fi;
        z += nz * dep * fi;
        this.ox[i] += nx * old * fi;
        this.oy[i] += ny * old * fi;
        this.oz[i] += nz * old * fi;
        this.x[j] -= nx * dep * fj;
        this.y[j] -= ny * dep * fj;
        this.z[j] -= nz * dep * fj;
        this.ox[j] -= nx * old * fj;
        this.oy[j] -= ny * old * fj;
        this.oz[j] -= nz * old * fj;
        if (ny > .22) {
          this.nx[i] = nx;
          this.ny[i] = ny;
          this.nz[i] = nz;
          this.vin[i] = Math.min(this.vin[i], vn);
          this.mu[i] = .62;
        }
      }
    }
    this.x[i] = x;
    this.y[i] = y;
    this.z[i] = z;
  }
  resolve(i, nx, ny, nz, dep, mu, h, sv) {
    if (dep <= 0) return;
    const sx = sv ? sv[0] : 0,
      sy = sv ? sv[1] : 0,
      sz = sv ? sv[2] : 0;
    const vn = (this.vx[i] - sx) * nx + (this.vy[i] - sy) * ny + (this.vz[i] - sz) * nz,
      old = Math.max(0, dep - Math.max(0, -vn) * h);
    this.x[i] += dep * nx;
    this.y[i] += dep * ny;
    this.z[i] += dep * nz;
    this.ox[i] += old * nx;
    this.oy[i] += old * ny;
    this.oz[i] += old * nz;
    this.nx[i] = nx;
    this.ny[i] = ny;
    this.nz[i] = nz;
    this.mu[i] = mu;
    this.vin[i] = Math.min(vn, this.vin[i]);
    this.svx[i] = sx;
    this.svy[i] = sy;
    this.svz[i] = sz;
  }
  boxContacts(i, list, h) {
    if (!list) return;
    const hit = this.hit;
    for (const b of list) if (b.contact(this.x[i], this.y[i], this.z[i], this.radius[i], hit)) this.resolve(i, hit[0], hit[1], hit[2], hit[3], b.mu, h, b.v);
  }
  sub(h) {
    this.tick++;
    this.bucketsNowCount = 0;
    let nf = 0;
    for (let k = 0; k < this.count; k++) {
      const i = this.order[k],
        s = this.state[i];
      if (s === HELD) continue;
      if (s === SLEEP) {
        this.insert(i);
        continue;
      }
      const x = this.x[i],
        y = this.y[i],
        z = this.z[i];
      this.ox[i] = x;
      this.oy[i] = y;
      this.oz[i] = z;
      const a = this.field.accel(x, y, z, this.acc, 1),
        fn = this.forces[this.tag[i]];
      if (fn) fn(i, a, h);
      this.vx[i] += a[0] * h;
      this.vy[i] += a[1] * h;
      this.vz[i] += a[2] * h;
      this.x[i] = x + this.vx[i] * h;
      this.y[i] = y + this.vy[i] * h;
      this.z[i] = z + this.vz[i] * h;
      this.vin[i] = this.mu[i] = this.svx[i] = this.svy[i] = this.svz[i] = 0;
      this.insert(i);
      this.freeOrder[nf++] = i;
    }
    for (let k = 0; k < this.bucketsLastCount; k++) {
      const key = this.bucketsLast[k];
      if (this.stamp[key] !== this.tick) this.updateNeighbors(key, false);
    }
    const previous = this.bucketsLast;
    this.bucketsLast = this.bucketsNow;
    this.bucketsNow = previous;
    this.bucketsLastCount = this.bucketsNowCount;
    for (let j = 0; j < nf; j++) {
      const i = this.freeOrder[j];
      this.pairs(i, h);
      const r = this.radius[i],
        x = this.x[i],
        y = this.y[i],
        z = this.z[i],
        g = this.ground(x, z);
      if (g > -9000 && y - r < g) {
        let nx = 0,
          ny = 1,
          nz = 0;
        const gx = this.ground(x + .7, z),
          gz = this.ground(x, z + .7);
        if (gx > -9000 && gz > -9000) {
          nx = clamp((g - gx) / .7, -3, 3);
          nz = clamp((g - gz) / .7, -3, 3);
          const inv = 1 / Math.sqrt(1 + nx * nx + nz * nz);
          nx *= inv;
          ny = inv;
          nz *= inv;
        }
        this.resolve(i, nx, ny, nz, (g + r - y) * ny, .75, h);
      }
      const key = cellKey(Math.floor(x / 8), Math.floor(y / 8), Math.floor(z / 8));
      this.boxContacts(i, this.grid.get(key), h);
      this.boxContacts(i, this.dynamicGrid.get(key), h);
      for (const s of this.spheres) {
        const dx = this.x[i] - s.x,
          dy = this.y[i] - s.y,
          dz = this.z[i] - s.z,
          rr = r + s.r,
          d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < rr * rr) {
          const d = Math.sqrt(d2) || .0001;
          this.resolve(i, dx / d, dy / d, dz / d, rr - d, s.mu, h);
        }
      }
    }
    for (let j = 0; j < nf; j++) {
      const i = this.freeOrder[j],
        inv = 1 / h;
      let u = (this.x[i] - this.ox[i]) * inv,
        v = (this.y[i] - this.oy[i]) * inv,
        w = (this.z[i] - this.oz[i]) * inv;
      if (this.mu[i]) {
        const nx = this.nx[i],
          ny = this.ny[i],
          nz = this.nz[i],
          sx = this.svx[i],
          sy = this.svy[i],
          sz = this.svz[i],
          vn = (u - sx) * nx + (v - sy) * ny + (w - sz) * nz;
        const want = this.vin[i] < -1.25 ? -.18 * this.vin[i] : 0,
          dn = Math.max(0, want - vn);
        u += dn * nx;
        v += dn * ny;
        w += dn * nz;
        const tx = u - sx - (vn + dn) * nx,
          ty = v - sy - (vn + dn) * ny,
          tz = w - sz - (vn + dn) * nz;
        const f = Math.min(1, this.mu[i] * (Math.max(0, -this.vin[i]) + 2.6 * h) / Math.max(.0001, Math.sqrt(tx * tx + ty * ty + tz * tz)));
        u -= f * tx;
        v -= f * ty;
        w -= f * tz;
      }
      this.vx[i] = u;
      this.vy[i] = v;
      this.vz[i] = w;
      if (u * u + v * v + w * w < .03 && this.mu[i]) {
        if (++this.sleep[i] >= 45) {
          this.state[i] = SLEEP;
          this.vx[i] = this.vy[i] = this.vz[i] = 0;
        }
      } else this.sleep[i] = 0;
    }
    this.activeN = nf;
  }
  step(dt) {
    this.time += dt;
    for (const bucket of this.movingBuckets) bucket.length = 0;
    this.movingBuckets.length = 0;
    for (const b of this.moving) if (b.on) this.indexBox(b, this.dynamicGrid);
    for (let k = 0; k < this.count; k++) {
      const i = this.order[k];
      this.age[i] += dt;
      this.stageAge[i] += dt;
      if (this.state[i] === SLEEP && i % 32 === (this.tick / 3 | 0) % 32 && (this.tick / 3 | 0) % 96 < 32) {
        this.wake(i);
        this.sleep[i] = 21;
      }
      if (this.state[i] === FREE) {
        this.rx[i] += this.wx[i] * dt;
        this.ry[i] += this.wy[i] * dt;
        this.rz[i] += this.wz[i] * dt;
      }
    }
    const h = dt / 3;
    for (let k = 0; k < 3; k++) this.sub(h);
  }
}
