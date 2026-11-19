import { TAG, SLEEP, clamp, rng } from '../physics/world.js';
import { V, bl, smooth } from './view.js';
export function anomaly(app) {
  const {
      sim,
      U
    } = app,
    w = sim.world,
    F = w.field,
    L = F.lode,
    R = rng(57281);
  F.addZone({
    minx: -25,
    maxx: 205,
    miny: -12,
    maxy: 85,
    minz: -237,
    maxz: -52,
    test: (x, y, z) => smooth((88 - Math.hypot(x - 96, z + 146)) / 9) * smooth((85 - y) / 10),
    g: [0, -9.8, 0]
  });
  F.addZone({
    minx: -137,
    maxx: -42,
    miny: -83,
    maxy: 8,
    minz: -99,
    maxz: -67,
    test: (x, y, z) => {
      const dx = x + 78,
        dz = z + 12,
        s = -.13917 * dx - .99027 * dz - 76,
        t = -.99027 * dx + .13917 * dz;
      return smooth((12 - Math.abs(s + 4)) / 6) * smooth((37 - Math.abs(t)) / 5);
    },
    g: [-.13917 * 3.2, 0, -.99027 * 3.2]
  });
  F.addZone({
    minx: -134,
    maxx: -22,
    miny: -130,
    maxy: 0,
    minz: -68,
    maxz: 44,
    test: (x, y, z) => smooth((54 - Math.hypot(x - L.x, z - L.z)) / 16),
    g: [0, 0, 0]
  });
  F.addZone({
    who: 1 | 2 | 8 | 16,
    minx: -27,
    maxx: 219,
    miny: -22,
    maxy: 143,
    minz: -269,
    maxz: -23,
    mode: 'add',
    test: (x, y, z) => Math.exp(-Math.abs(Math.hypot(x - 96, y - 10, z + 146) - 112) / 7),
    fn: (x, y, z, o) => {
      const f = 26 / Math.max(1, Math.hypot(x - 96, y - 10, z + 146));
      o[0] = (x - 96) * f;
      o[1] = (y - 10) * f;
      o[2] = (z + 146) * f;
    }
  });
  w.spheres.push({
    x: -78,
    y: -96,
    z: -12,
    r: 34,
    mu: .15
  });
  const tide = {
    count: 0,
    power: 0,
    envelope: 0,
    start: -100,
    next: 20.8,
    hold: 4,
    shadowTime: 19,
    angle: 1,
    paused: false,
    onFront: [],
    trigger(strength) {
      this.start = sim.time;
      this.power = strength ?? .7 + 1.6 * R();
      this.hold = 2 + 4 * R();
      this.shadowTime = 17 + 6 * R();
      this.angle = R() * Math.PI * 2;
      this.count++;
      this.next = this.start + 2.2 + this.hold + 6.5 + 28 + 70 * R();
      for (const fn of this.onFront) fn(this);
    },
    pre() {
      if (this.paused || app.holdTide) return;
      if (sim.time >= this.next) this.trigger();
      const t = sim.time - this.start;
      const env = t < 2.2 ? smooth(t / 2.2) : t < 2.2 + this.hold ? 1 : 1 - smooth((t - 2.2 - this.hold) / 6.5);
      this.envelope = env;
      L.tide = .085 * Math.sin(sim.time * .097) + env * this.power;
      U.uTide.value = env * Math.min(1, this.power / 1.6);
      const front = t * 30,
        enabled = front <= 760;
      F.wave.r = enabled ? front : -1000;
      F.wave.a = enabled ? Math.min(1.35, this.power) * smooth(t / .65) : 0;
      U.uWave.value.set(F.wave.r, F.wave.a, 0, 0);
      U.uArt.value.x = 1.2 + .12 * Math.sin(sim.time * .17) + .86 * U.uTide.value;
      const d = (t / this.shadowTime - .5) * 690;
      U.uShadow.value.set(L.x + Math.cos(this.angle) * d, L.z + Math.sin(this.angle) * d, this.angle, t < this.shadowTime ? smooth(t / 2) * smooth((this.shadowTime - t) / 3) * .84 : 0);
    }
  };
  sim.add('tides', tide);
  function seedHalo() {
    const th = R() * Math.PI * 2,
      r = 13 + R() * 20,
      v = Math.sqrt(70) * (.93 + .14 * R());
    return w.spawn(TAG.HALO, L.x + Math.cos(th) * r, L.y + 2 + R() * 4, L.z + Math.sin(th) * r, {
      kind: 3,
      r: .5 + R() * .72,
      vx: Math.sin(th) * v,
      vy: (R() - .48) * 1.4,
      vz: -Math.cos(th) * v
    });
  }
  for (let i = 0; i < 150; i++) seedHalo();
  const halo = {
    captured: 0,
    released: 0,
    settled: 0,
    capture(i) {
      w.relabel(i, TAG.HALO);
      w.kind[i] = 3;
      w.vx[i] *= .7;
      w.vy[i] *= .48;
      w.vz[i] *= .7;
      this.captured++;
    },
    post(dt) {
      for (let j = w.count - 1; j >= 0; j--) {
        const i = w.order[j];
        if (w.tag[i] !== TAG.HALO) continue;
        const dx = w.x[i] - L.x,
          dz = w.z[i] - L.z;
        if (dx * dx + dz * dz > 74 * 74 || w.y[i] < -99 || w.age[i] > 80 && w.state[i] === SLEEP) {
          w.kill(i);
          this.released++;
        }
      }
      if (w.counts[TAG.HALO] > 162) {
        const orbit = [];
        for (let j = 0; j < w.count; j++) {
          const i = w.order[j];
          if (w.tag[i] === TAG.HALO) orbit.push(i);
        }
        orbit.sort((a, b) => w.stageAge[b] - w.stageAge[a]);
        for (let j = 0; j < orbit.length - 151; j++) {
          const i = orbit[j];
          w.relabel(i, TAG.SPILL);
          w.vx[i] *= .38;
          w.vz[i] *= .38;
          this.settled++;
        }
      }
      if (w.counts[TAG.HALO] < 149 && R() < dt * 3) seedHalo();
    }
  };
  sim.add('halo', halo);
  // Historic tailings are physical, initially settled, and batch-woken to check support.
  for (const [cx, cy, rx, ry, total] of [[-158, -92, 25, 9, 270], [-98, -152, 19, 8, 220], [-176, -40, 13, 8, 160], [60, -68, 12, 9, 120], [71, 43, 11, 7, 120]]) {
    for (let j = 0; j < total; j++) {
      const a = R() * 6.283,
        r = Math.sqrt(R()),
        x = cx + Math.cos(a) * r * rx,
        z = -(cy + Math.sin(a) * r * ry),
        rad = .36 + R() * .37;
      const y = w.ground(x, z);
      if (y > -9000) w.spawn(TAG.GROUND, x, y + rad, z, {
        r: rad,
        kind: R() < .46 ? 1 : 2,
        state: SLEEP
      });
    }
  }
}
