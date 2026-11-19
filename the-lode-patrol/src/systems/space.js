import * as T from 'three';
import { rng, clamp, TAG } from '../physics/world.js';
import { rockMaterial } from '../materials.js';
import { V, instances, geometry, setInstance } from './view.js';
export function space(app) {
  const sim = app.sim,
    w = sim.world,
    L = w.field.lode,
    R = rng(87011),
    N = 960,
    M = 90,
    x = new Float64Array(N * 3),
    v = new Float32Array(N * 3),
    size = new Float32Array(N),
    angles = new Float32Array(N),
    kinds = new Uint8Array(N);
  const meshes = [0, 1, 2].map(i => instances(app, geometry(app, 'rocks', ['chunk_a', 'chunk_b', 'chunk_c'][i]), rockMaterial(i + 31, 6 + i * 2, 0xf3e5e0, {
    ORBITAL: ''
  }), Math.ceil((N + M) / 3) + 4));
  const phi = .27,
    forward = V(.402, 0, .916).normalize(),
    b = forward.clone().multiplyScalar(Math.cos(phi));
  b.y = -Math.sin(phi);
  const a = V(forward.z, 0, -forward.x),
    normal = V().crossVectors(a, b).normalize(),
    center = V(L.x, L.y, L.z);
  for (let i = 0; i < N; i++) {
    const ang = R() * Math.PI * 2,
      c = Math.cos(ang),
      s = Math.sin(ang),
      radius = 395 + 230 * R() ** 1.9,
      height = (R() - .5) * (7 + 14 * R()),
      speed = Math.sqrt(70) * (.97 + .06 * R());
    kinds[i] = i % 3;
    angles[i] = 6.28 * R();
    size[i] = i < 68 ? (4 + 11 * R() ** 1.5) * .66 : (.9 + 3.1 * R()) * .66;
    for (let j = 0; j < 3; j++) {
      const n = ['x', 'y', 'z'][j];
      x[3 * i + j] = center[n] + radius * (a[n] * c + b[n] * s) + normal[n] * height;
      v[i * 3 + j] = speed * (-a[n] * s + b[n] * c);
    }
  }
  const moon = app.clone('rocks', 'moon', false);
  moon.position.set(-2700, -1150, -4300);
  moon.scale.setScalar(600);
  const moonMats = new Map();
  moon.traverse(o => {
    if (!o.isMesh) return;
    const name = o.material.name;
    const inner = /inner|core/.test(name);
    let m = moonMats.get(name);
    if (!m) {
      m = rockMaterial(8, 360, inner ? 0x746169 : 0x847c91, inner ? {
        INNER: ''
      } : {}, true);
      if (inner) m.emissive.setRGB(.0015, .0001, .00018);
      moonMats.set(name, m);
    }
    o.material = m;
    o.castShadow = false;
  });
  const phases = new Float32Array(M),
    noise = new Float32Array(3 * M),
    sizes = new Float32Array(M);
  for (let i = 0; i < M; i++) {
    phases[i] = R();
    sizes[i] = (5 + 25 * R() ** 2) * .5;
    for (let j = 0; j < 3; j++) noise[3 * i + j] = (R() - .5) * 85;
  }
  const streamStart = moon.position.clone().add(V(100, 48, 95)),
    mid = V(-1350, -125, -2250),
    end = V(-210, 72, -418),
    p = V();
  const ring = {
    orbiters: N,
    moonStream: M,
    rmin: 0,
    rmax: 0,
    meanRadius: 0,
    pre(dt) {
      const k = L.k * (1 + L.tide);
      let mean = 0,
        low = Infinity,
        high = 0;
      for (let i = 0, j = 0; i < N; i++, j += 3) {
        const dx = x[j] - L.x,
          dy = x[j + 1] - L.y,
          dz = x[j + 2] - L.z,
          r2 = dx * dx + dy * dy + dz * dz,
          r = Math.sqrt(r2),
          vr = (v[j] * dx + v[j + 1] * dy + v[j + 2] * dz) / r,
          g = -k / r2 - .03 * vr / r;
        v[j] += dx * g * dt;
        v[j + 1] += dy * g * dt;
        v[j + 2] += dz * g * dt;
        x[j] += v[j] * dt;
        x[j + 1] += v[j + 1] * dt;
        x[j + 2] += v[j + 2] * dt;
        mean += r;
        if (r < low) low = r;
        if (r > high) high = r;
      }
      this.meanRadius = mean / N;
      this.rmin = low;
      this.rmax = high;
      for (let i = 0; i < M; i++) {
        phases[i] = (phases[i] + dt * (.0016 + .0045 * phases[i] ** 2)) % 1;
      }
    },
    frame() {
      const bins = [0, 0, 0],
        t = sim.time;
      for (let i = 0, j = 0; i < N; i++, j += 3) {
        const k = i % 3,
          ang = angles[i] + t * (.013 + i % 11 * .002);
        setInstance(meshes[k], bins[k]++, x[j], x[j + 1], x[j + 2], size[i], ang, ang * .7, ang * .3, 1.27, .78, 1);
      }
      for (let i = 0; i < M; i++) {
        const k = i % 3,
          u = phases[i],
          s = 1 - u;
        const spread = .26 + .74 * s;
        p.copy(streamStart).multiplyScalar(s * s).addScaledVector(mid, 2 * s * u).addScaledVector(end, u * u);
        p.x += noise[3 * i] * spread;
        p.y += noise[3 * i + 1] * spread;
        p.z += noise[3 * i + 2] * spread;
        setInstance(meshes[k], bins[k]++, p.x, p.y, p.z, sizes[i], t * .012 + i, t * .016 + i * .34, .24 * i);
      }
      for (let j = 0; j < 3; j++) {
        meshes[j].count = bins[j];
        meshes[j].instanceMatrix.needsUpdate = true;
      }
      moon.rotation.y = t * .0011;
    }
  };
  sim.add('wheel', ring);
}
const roads = [[[36, -26], [58, -50], [94, -60], [129, -58]], [[-128, 100], [-90, 106], [-50, 104], [-20, 92], [8, 70], [30, 48], [38, 22]], [[36, -26], [24, -70], [4, -110], [-6, -144]], [[4, -110], [-56, -120], [-118, -118], [-166, -66], [-188, -30]], [[30, 48], [52, 66], [70, 80], [92, 100]]];
function reserved(x, y) {
  if (x > 17 && x < 137 && y > -66 && y < 63 || x > 27 && x < 162 && y > 72 && y < 187 || x < -158 && x > -219 && y > -61 && y < 65 || x > -5 && x < 145 && y > -190 && y < -99 || x > -113 && x < -20 && y > -116 && y < -83 || ((x + 78) / 106) ** 2 + ((y - 12) / 88) ** 2 < 1) return true;
  for (const pts of roads) for (let j = 1; j < pts.length; j++) {
    const [a, b] = pts[j - 1],
      [c, d] = pts[j],
      dx = c - a,
      dy = d - b,
      t = clamp(((x - a) * dx + (y - b) * dy) / (dx * dx + dy * dy), 0, 1);
    if ((x - a - t * dx) ** 2 + (y - b - t * dy) ** 2 < 60) return true;
  }
  return false;
}
export function debris(app) {
  const sim = app.sim,
    w = sim.world,
    L = w.field.lode,
    R = rng(4452),
    N = 360,
    rocks = [],
    active = [],
    m = instances(app, geometry(app, 'rocks', 'rubble_a'), rockMaterial(39, 3.2, 0xc2afa4), N),
    a = [0, 0, 0];
  for (let i = 0; i < N; i++) {
    let x, z, g;
    do {
      x = R() * 440 - 220;
      z = R() * 440 - 220;
      g = w.ground(x, z);
    } while (g < -40 || reserved(x, -z));
    const r = .4 + 1.2 * R() ** 1.5;
    rocks.push({
      x,
      y: g + r * .63,
      z,
      r,
      vx: 0,
      vy: 0,
      vz: 0,
      angle: R() * 6,
      spin: (R() - .5) * 2.6,
      dist: Math.hypot(x - L.x, z - L.z),
      id: i,
      mode: 0,
      bounced: 0,
      seen: 0
    });
  }
  const ordered = rocks.slice().sort((a, b) => a.dist - b.dist);
  let cursor = 0;
  const field = {
    lifted: 0,
    landed: 0,
    escaped: 0,
    front: 0,
    pre(dt) {
      const wave = w.field.wave,
        r = wave.r;
      if (r < 0) {
        cursor = 0;
      } else {
        while (cursor < ordered.length && ordered[cursor].dist <= r) {
          const o = ordered[cursor++];
          if (!o.mode && o.seen !== app.sys.tides.count) {
            o.seen = app.sys.tides.count;
            const power = app.sys.tides.power;
            o.mode = 1;
            o.bounced = 0;
            o.vy = (4.5 + 6.5 * R()) * power;
            const v = (.7 + 1.8 * R()) / Math.max(o.dist, 1);
            o.vx = (o.x - L.x) * v;
            o.vz = (o.z - L.z) * v;
            active.push(o);
            this.lifted++;
            if (R() < .20) app.sys.dust?.puff(o.x, o.y, o.z, .8);
          }
        }
      }
      for (let j = active.length - 1; j >= 0; j--) {
        const o = active[j];
        w.field.accel(o.x, o.y, o.z, a, 2);
        o.vx += a[0] * dt;
        o.vy += a[1] * dt;
        o.vz += a[2] * dt;
        o.x += o.vx * dt;
        o.y += o.vy * dt;
        o.z += o.vz * dt;
        o.angle += o.spin * dt;
        const g = w.ground(o.x, o.z);
        if (g > -9000 && o.y < g + o.r * .63 && o.vy < 0) {
          o.y = g + o.r * .63;
          if (o.bounced++) {
            o.mode = 0;
            o.dist = Math.hypot(o.x - L.x, o.z - L.z);
            active.splice(j, 1);
            this.landed++;
          } else {
            o.vy *= -.28;
            o.vx *= .5;
            o.vz *= .5;
            app.sys.dust?.puff(o.x, o.y, o.z, 1);
          }
        } else if (o.y < -220) {
          o.mode = 2;
          active.splice(j, 1);
          this.escaped++;
        }
      }
    },
    frame() {
      let k = 0;
      for (const o of rocks) {
        if (o.mode === 2) continue;
        setInstance(m, k++, o.x, o.y, o.z, o.r, o.angle, o.id * .3, o.angle * .6, 1.12, .75, .95);
      }
      m.count = k;
      m.instanceMatrix.needsUpdate = true;
    }
  };
  app.sys.tides.onFront.push(() => {
    cursor = 0;
    ordered.sort((a, b) => a.dist - b.dist);
  });
  sim.add('ejecta', field);
  const vents = [[-158, -128, 88], [-20, 178, 102], [-196, 78, 82], [118, -150, 94]].map(([x, y, h]) => ({
      x,
      z: -y,
      y: w.ground(x, -y),
      h,
      clock: R()
    })),
    particles = [],
    seepMesh = instances(app, geometry(app, 'rocks', 'chunk_c'), rockMaterial(31, 2.5, 0xb29ca9), 235);
  function spawn(v, height = 0) {
    const ang = R() * 6.28,
      r = 1.6 + 4.2 * R();
    particles.push({
      x: v.x + Math.cos(ang) * r,
      z: v.z + Math.sin(ang) * r,
      y: v.y + height + 1,
      vy: 4.2,
      vx: 0,
      vz: 0,
      t: height / 4.2,
      r: .4 + .92 * R(),
      angle: ang,
      v,
      free: false
    });
  }
  for (const v of vents) for (let j = 0; j < 13; j++) spawn(v, R() * v.h);
  const seep = {
    released: 0,
    captured: 0,
    particles,
    pre(dt) {
      for (const v of vents) {
        v.clock += dt * (1.16 + .36 * Math.sin(sim.time * .217 + v.x)) * (1 + 1.5 * app.U.uTide.value);
        while (v.clock > 1) {
          if (particles.length < 235) spawn(v);
          v.clock--;
        }
      }
      for (let j = particles.length - 1; j >= 0; j--) {
        const p = particles[j],
          v = p.v;
        p.t += dt;
        w.field.accel(p.x, p.y, p.z, a, 16);
        if (!p.free) {
          const th = p.angle + p.t * .35,
            gx = v.x + Math.cos(th) * (3.2 + p.r),
            gz = v.z + Math.sin(th) * (3.2 + p.r);
          a[0] += (gx - p.x) * 1.2 - p.vx * 1.35;
          a[2] += (gz - p.z) * 1.2 - p.vz * 1.35;
          a[1] += (4.2 - p.vy) * 2.3;
          if (p.y - v.y >= v.h) {
            p.free = true;
            this.released++;
          }
        }
        p.vx += a[0] * dt;
        p.vy += a[1] * dt;
        p.vz += a[2] * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.z += p.vz * dt;
        if (p.free && Math.hypot(p.x - L.x, p.y - L.y, p.z - L.z) < 38) {
          const i = w.spawn(TAG.HALO, p.x, p.y, p.z, {
            kind: 3,
            r: p.r,
            vx: p.vx * .75,
            vy: p.vy * .65,
            vz: p.vz * .75
          });
          if (i >= 0) this.captured++;
          particles.splice(j, 1);
        } else if (p.t > 138 || p.y < -160) particles.splice(j, 1);
      }
    },
    frame() {
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        setInstance(seepMesh, i, p.x, p.y, p.z, p.r, p.t * .22 + p.angle, p.t * .13, p.t * .08);
      }
      seepMesh.count = particles.length;
      seepMesh.instanceMatrix.needsUpdate = true;
    }
  };
  sim.add('seep', seep);
}
