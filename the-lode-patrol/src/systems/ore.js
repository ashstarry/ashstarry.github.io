import * as T from 'three';
import { TAG, FREE, HELD, SLEEP, clamp, rng } from '../physics/world.js';
import { V } from './view.js';
const fallback = {
  boom: [[-161.8, 6.2, -49], [-195.2, 19.8, -5.6]],
  dis: [[-194, 14.7, -3.2], [-186, 19, 50]],
  cv1: [[48, 5, 8], [64, 11, 22]],
  cv2: [[84, 2, 27], [92, 2.5, 22], [98, 4, -4]],
  cv3: [[70, 4, 18], [103, 13, 18], [134, 13, 33], [146, 12, 34]]
};
function rail(points) {
  let s = 0;
  const seg = [];
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1],
      b = points[i],
      dx = b[0] - a[0],
      dy = b[1] - a[1],
      dz = b[2] - a[2],
      len = Math.hypot(dx, dy, dz);
    if (len < .01) continue;
    seg.push({
      a,
      b,
      dx: dx / len,
      dy: dy / len,
      dz: dz / len,
      len,
      s
    });
    s += len;
  }
  return {
    seg,
    len: s
  };
}
export function ore(app) {
  const {
      sim
    } = app,
    w = sim.world,
    R = rng(996811);
  const flow = {
    dug: 0,
    onDischarge: 0,
    ammunition: 24,
    launched: 0,
    caught: 0,
    missed: 0,
    crushed: 0,
    crusher: 14,
    screened: 0,
    oreOut: 0,
    wasteOut: 0,
    raised: 0,
    binned: 0,
    loaded: 0,
    pulses: 0,
    wasteDropped: 0,
    transportLoss: 0,
    rotor: .62,
    wheelAngle: 0,
    slew: 0,
    gate: 0,
    binOpen: 0,
    binRequest: false,
    train: null,
    solution: {
      speed: 19,
      az: -.24,
      residual: 0
    },
    motor: {},
    open: true
  };
  const p = app.layout.plant || {},
    bwe = app.layout.bwe || {},
    defs = (l, n, f) => l.paths?.[n]?.map(o => o.p) || f;
  const paths = {
    boom: rail(defs(bwe, 'bwe_belt', fallback.boom)),
    dis: rail(defs(bwe, 'discharge_belt', fallback.dis)),
    cv1: rail(defs(p, 'cv1', fallback.cv1)),
    cv2: rail(defs(p, 'cv2', fallback.cv2)),
    cv3: rail(defs(p, 'cv3', fallback.cv3))
  };
  const stages = [[TAG.BOOM, 'boom', 4.2], [TAG.DISCHARGE, 'dis', 4.05], [TAG.CV1, 'cv1', 3.2], [TAG.CV2, 'cv2', 3.2], [TAG.CV3, 'cv3', 3.5]];
  const start = app.mark('bwe', 'bwe_drop', [-161.51, 7.83, -49.37]);
  const muzzle = [-167, 27, 60],
    target = [40, 26, 8],
    axis = app.find('bwe', 'bwe_wheel'),
    superObj = app.find('bwe', 'bwe_super'),
    jigDoor = app.find('plant', 'jig_gate_door'),
    binDoor = app.find('plant', 'bin_gate_door'),
    rake = app.find('plant', 'thickener_rake');
  const jigRest = jigDoor?.position.clone(),
    binRest = binDoor?.position.clone();
  const wheelAxis = V(.79229, 0, .61015);
  const idx = new Uint16Array(w.cap),
    distance = new Float32Array(w.cap),
    pos = [0, 0, 0];
  const motors = {},
    beltBoxes = [];
  for (const [, name] of stages) motors[name] = true;
  flow.motor = motors;
  const colliderMap = {};
  for (const [part, layout] of Object.entries(app.layout)) {
    if (part === 'fleet' || part === 'rocks') continue;
    for (const d of layout.colliders || []) {
      const moving = d.obj && d.obj !== 'static' && (d.tag?.startsWith('bwe_arm') || /^(jig_gate|bin_gate)$/.test(d.tag));
      const box = w.addBox({
        ...d,
        p: [...d.p],
        q: [...d.q]
      }, moving);
      (colliderMap[d.tag] ??= []).push(box);
      if (d.surfaceVelocity) beltBoxes.push([box, d.surfaceVelocity, d.tag.startsWith('bwe_arm') ? 'boom' : d.tag.includes('discharge') ? 'dis' : d.tag]);
    }
  }
  flow.colliders = colliderMap;
  function place(i, tag, x, y, z, vx = 0, vy = 0, vz = 0) {
    w.release(i, tag, x, y, z, vx, vy, vz);
    idx[i] = 0;
    distance[i] = 0;
  }
  function feed(i, tag, name) {
    const q = paths[name].seg[0];
    place(i, tag, q.a[0] + q.dx * .4 + (R() - .5) * .75, q.a[1] + w.radius[i] + .24, q.a[2] + q.dz * .4 + (R() - .5) * .75, q.dx, q.dy, q.dz);
  }
  // Along each belt, the motor and side skirting supply tangential traction and lateral contact.
  for (const [tag, name, speed] of stages) {
    const path = paths[name];
    w.forces[tag] = (i, a) => {
      let j = Math.min(idx[i], path.seg.length - 1),
        q = path.seg[j];
      let dx = w.x[i] - q.a[0],
        dy = w.y[i] - w.radius[i] - q.a[1],
        dz = w.z[i] - q.a[2],
        s = dx * q.dx + dy * q.dy + dz * q.dz;
      if (s > q.len - .25 && j + 1 < path.seg.length) {
        q = path.seg[++j];
        idx[i] = j;
        dx = w.x[i] - q.a[0];
        dy = w.y[i] - w.radius[i] - q.a[1];
        dz = w.z[i] - q.a[2];
        s = dx * q.dx + dy * q.dy + dz * q.dz;
      }
      distance[i] = q.s + s;
      const u = clamp(s, 0, q.len),
        tx = q.a[0] + q.dx * u,
        tz = q.a[2] + q.dz * u,
        ty = q.a[1] + q.dy * u + w.radius[i] + .10;
      const v = motors[name] ? speed : 0;
      const along = w.vx[i] * q.dx + w.vy[i] * q.dy + w.vz[i] * q.dz;
      const drive = clamp((v - along) * 6, -10, 10);
      a[0] += drive * q.dx + (tx - w.x[i]) * 12 - (w.vx[i] - along * q.dx) * 4;
      a[2] += drive * q.dz + (tz - w.z[i]) * 12 - (w.vz[i] - along * q.dz) * 4;
      a[1] += drive * q.dy + clamp((ty - w.y[i]) * 17 - (w.vy[i] - q.dy * along) * 5, -16, 24);
    };
  }
  const theta = 42 * Math.PI / 180,
    cs = Math.cos(theta),
    sn = Math.sin(theta),
    aa = [0, 0, 0];
  // Shoot to the target's vertical plane. Solve height and lateral miss simultaneously.
  function trial(speed, az) {
    let [x, y, z] = muzzle,
      u = speed * cs * Math.cos(az),
      v = speed * sn,
      t = speed * cs * Math.sin(az);
    const dt = .12,
      tx = target[0];
    for (let j = 0; j < 750; j++) {
      const ox = x,
        oy = y,
        oz = z;
      w.field.accel(x, y, z, aa, 1);
      u += aa[0] * dt;
      v += aa[1] * dt;
      t += aa[2] * dt;
      x += u * dt;
      y += v * dt;
      z += t * dt;
      if (x >= tx) {
        const f = (tx - ox) / (x - ox);
        return [oy + (y - oy) * f - target[1], oz + (z - oz) * f - target[2]];
      }
      if (y < -250) break;
    }
    return [-300, z - target[2]];
  }
  function fireControl() {
    let {
      speed,
      az
    } = flow.solution;
    for (let j = 0; j < 6; j++) {
      const [hy, hz] = trial(speed, az);
      if (Math.abs(hy) + Math.abs(hz) < .12) break;
      const dv = trial(speed + .14, az),
        da = trial(speed, az + .002);
      const a = (dv[0] - hy) / .14,
        c = (dv[1] - hz) / .14,
        b = (da[0] - hy) / .002,
        d = (da[1] - hz) / .002,
        det = a * d - b * c;
      if (Math.abs(det) < 1e-6) {
        speed = clamp(speed + 1, 15, 40);
        continue;
      }
      speed = clamp(speed + clamp((-hy * d + b * hz) / det, -4, 4), 15, 40);
      az = clamp(az + clamp((c * hy - a * hz) / det, -.14, .14), -.7, .28);
    }
    const miss = trial(speed, az);
    flow.solution = {
      speed,
      az,
      residual: Math.hypot(...miss)
    };
  }
  w.forces[TAG.MITT] = (i, a) => {
    a[0] += (40 - w.x[i]) * 2.9 - w.vx[i] * 2.6;
    a[2] += (8 - w.z[i]) * 2.9 - w.vz[i] * 2.6;
    a[1] += (-7.8 - w.vy[i]) * 2.5;
  };
  const ARM = paths.boom.seg.map(q => ({
      a: q.a.slice(),
      b: q.b.slice(),
      dx: q.dx,
      dy: q.dy,
      dz: q.dz
    })),
    pivot = superObj?.position || V(-194, 0, -2),
    armV = V(),
    armQ = new T.Quaternion(),
    yaw = new T.Quaternion(),
    Y = V(0, 1, 0);
  const movingArm = w.moving.filter(q => q.tag?.startsWith('bwe_arm')).map(o => ({
    o,
    p: V(...o.p),
    q: new T.Quaternion(...o.q),
    v: V(...(o.surfaceVelocity || [0, 0, 0]))
  }));
  function swingArm() {
    yaw.setFromAxisAngle(Y, flow.slew);
    const rate = .07 * .043 * Math.cos(sim.time * .043);
    for (let k = 0; k < ARM.length; k++) {
      const q = paths.boom.seg[k],
        rest = ARM[k];
      armV.fromArray(rest.a).sub(pivot).applyQuaternion(yaw).add(pivot).toArray(q.a);
      armV.fromArray(rest.b).sub(pivot).applyQuaternion(yaw).add(pivot).toArray(q.b);
      armV.set(rest.dx, rest.dy, rest.dz).applyQuaternion(yaw);
      q.dx = armV.x;
      q.dy = armV.y;
      q.dz = armV.z;
    }
    for (const ref of movingArm) {
      const o = ref.o;
      armV.copy(ref.p).sub(pivot).applyQuaternion(yaw).add(pivot).toArray(o.p);
      armQ.copy(yaw).multiply(ref.q).toArray(o.q);
      o.cache();
      armV.copy(ref.v).multiplyScalar(motors.boom ? 1 : 0).applyQuaternion(yaw);
      armV.x += rate * (o.p[2] - pivot.z);
      armV.z -= rate * (o.p[0] - pivot.x);
      o.v = armV.toArray(o.v === o.surfaceVelocity ? [] : o.v);
    }
  }
  let lift = true,
    pulseClock = .47,
    launchClock = 0,
    crusherClock = 0,
    fcClock = 0,
    tips = 0,
    lastTip = 0,
    wakeClock = 0;
  w.forces[TAG.JIG] = (i, a) => {
    const waste = w.kind[i] === 1,
      resp = waste ? 1.8 : 1.;
    a[1] += lift ? 2.6 + 3.4 * resp : -2.2;
    if (waste) {
      a[0] += (70 - w.x[i]) * 1.4 - w.vx[i] * 1.1;
      a[2] += (20.1 - w.z[i]) * 1.25 - w.vz[i] * .8;
      if (w.z[i] < 24 && w.x[i] < 73) {
        a[1] += Math.max(0, 8.3 - w.y[i]) * 3.6;
        a[2] -= 3.3;
      }
    } else if (motors.cv2) {
      a[0] += (lift ? 4.6 : 3.9) - w.vx[i] * .8;
      a[2] += (27 - w.z[i]) * 1.8 - w.vz[i];
      if (w.x[i] > 79) a[0] += (2.8 - w.vx[i]) * 2.3;
    }
  };
  w.forces[TAG.WELL] = (i, a) => {
    const top = w.y[i] > 58;
    const x = top ? 114 : 98,
      z = -8;
    a[0] += (x - w.x[i]) * (top ? 2.4 : 3.4) - w.vx[i] * (top ? 2.2 : 3.3);
    a[2] += (z - w.z[i]) * 3.3 - w.vz[i] * 3.2;
    if (w.x[i] < 105) a[1] += motors.well ? 2.6 + 3.4 * (1 - w.vy[i] / 7.5) : -w.vy[i] * 4 + 2.6;else a[1] += -4.8 - w.vy[i] * .3;
  };
  w.forces[TAG.BIN] = (i, a) => {
    if (w.y[i] > 37) {
      a[1] += (-5.7 - w.vy[i]) * 2.15;
      a[0] += (114 - w.x[i]) * 1.2 - w.vx[i] * 1.4;
      a[2] += (-8 - w.z[i]) * 1.2 - w.vz[i] * 1.4;
    }
    if (flow.binRequest && w.y[i] < 25) {
      a[0] += (114 - w.x[i]) * 1.2 - w.vx[i];
      a[2] += (-8 - w.z[i]) * 1.2 - w.vz[i];
    }
  };
  flow.addCrusher = (n = 1) => {
    flow.crusher += n;
  };
  flow.takeBin = (i, car) => {
    w.hold(i, TAG.TRAIN, car.id);
    car.cargo.push(i);
    flow.loaded++;
  };
  function setGate(tag, x, y) {
    const list = colliderMap[tag] || [];
    for (const obj of list) {
      if (!obj.rest) obj.rest = obj.p.slice();
      obj.p[0] = obj.rest[0] + x;
      obj.p[1] = obj.rest[1] + y;
    }
  }
  flow.pre = dt => {
    const n = w.counts;
    motors.well = n[TAG.BIN] < 150;
    motors.cv2 = n[TAG.WELL] < 70 && motors.well;
    motors.cv1 = n[TAG.JIG] < 520;
    motors.boom = motors.dis = flow.ammunition <= 45;
    motors.cv3 = true;
    const canShoot = n[TAG.MITT] < 90 && flow.crusher < 80,
      goal = motors.boom ? .62 : 0;
    flow.rotor += (goal - flow.rotor) * (1 - Math.exp(-dt / 4));
    flow.wheelAngle += flow.rotor * dt;
    flow.slew = .07 * Math.sin(sim.time * .043);
    swingArm();
    tips = flow.wheelAngle * 14 / (Math.PI * 2);
    if ((tips | 0) > lastTip) {
      lastTip = tips | 0;
      for (let j = 0; j < 4; j++) {
        const i = w.spawn(TAG.BOOM, start.x + (R() - .5) * 1.8, start.y + .15 * j, start.z + (R() - .5) * 1.4, {
          r: .43 + R() * .3
        });
        if (i >= 0) {
          idx[i] = 0;
          flow.dug++;
        }
      }
    }
    fcClock -= dt;
    if (fcClock <= 0) {
      fireControl();
      fcClock = 1.5;
    }
    launchClock -= dt;
    if (canShoot && launchClock <= 0 && flow.ammunition > 0) {
      const v = flow.solution.speed * (.994 + .012 * R()),
        az = flow.solution.az + (R() - .5) * .009;
      w.spawn(TAG.SHOT, ...muzzle, {
        r: .66 + R() * .24,
        vx: v * cs * Math.cos(az),
        vy: v * sn,
        vz: v * cs * Math.sin(az)
      });
      flow.ammunition--;
      flow.launched++;
      launchClock = .195 + R() * .018;
    }
    crusherClock -= dt;
    if (cover() && crusherClock <= 0 && flow.crusher > 0) {
      const i = w.spawn(TAG.CV1, 48, 6, 8, {
        r: .42 + .22 * R(),
        kind: R() < .32 ? 1 : 0
      });
      if (i >= 0) {
        feed(i, TAG.CV1, 'cv1');
        flow.crusher--;
        flow.crushed++;
      }
      crusherClock = .17;
    }
    pulseClock -= dt;
    if (pulseClock <= 0) {
      lift = !lift;
      pulseClock = lift ? .42 + R() * .16 : 1.5 + R() * .58 + n[TAG.JIG] / 700;
      if (lift) {
        flow.pulses++;
        for (let j = 0; j < w.count; j++) {
          const i = w.order[j];
          if (w.tag[i] === TAG.JIG) w.wake(i);
        }
      }
    }
    flow.gate += (Number(motors.cv2) - flow.gate) * dt * 2.8;
    flow.binOpen += (Number(flow.binRequest) - flow.binOpen) * dt * 3;
    setGate('jig_gate', 0, flow.gate * 5.6);
    setGate('bin_gate', flow.binOpen * 5, 0);
    for (const [box, v, label] of beltBoxes) {
      if (label === 'boom') continue;
      const powered = motors[label] !== false;
      box.v = powered ? v : zero;
    }
    if (flow.binRequest && (wakeClock -= dt) <= 0) {
      for (let j = 0; j < w.count; j++) {
        const i = w.order[j];
        if (w.tag[i] === TAG.BIN && w.y[i] < 32) w.wake(i);
      }
      wakeClock = .48;
    }
  };
  function cover() {
    return motors.cv1 && w.counts[TAG.CV1] < 90;
  }
  const zero = [0, 0, 0];
  flow.post = () => {
    for (let j = w.count - 1; j >= 0; j--) {
      const i = w.order[j],
        t = w.tag[i],
        x = w.x[i],
        y = w.y[i],
        z = w.z[i],
        age = w.stageAge[i];
      switch (t) {
        case TAG.BOOM:
          if (distance[i] > paths.boom.len - .8) {
            feed(i, TAG.DISCHARGE, 'dis');
            flow.onDischarge++;
          }
          break;
        case TAG.DISCHARGE:
          if (distance[i] > paths.dis.len - .8) {
            w.kill(i);
            flow.ammunition++;
          }
          break;
        case TAG.SHOT:
          if (w.vy[i] < 0 && y < 68 && Math.hypot(x - 40, z - 8) < 30) {
            w.relabel(i, TAG.MITT);
            flow.caught++;
          } else if (age > 36 || y < 2 && x > -145) {
            flow.missed++;
            if (Math.hypot(x + 78, z + 12) < 66) app.sys.halo.capture(i);else w.relabel(i, TAG.SPILL);
          }
          break;
        case TAG.MITT:
          if (y < 12.5 && Math.hypot(x - 40, z - 8) < 7) {
            w.kill(i);
            flow.crusher++;
          }
          break;
        case TAG.CV1:
          if (distance[i] > paths.cv1.len - .75) {
            w.relabel(i, TAG.JIG);
            w.vx[i] = 3.15;
            w.vz[i] = .7;
            w.vy[i] = -.3;
            flow.screened++;
          }
          break;
        case TAG.JIG:
          if (w.kind[i] === 1 && z < 21.8 && y > 4.65) {
            feed(i, TAG.CV3, 'cv3');
            flow.wasteOut++;
          } else if (w.kind[i] !== 1 && motors.cv2 && x > 82.25 && Math.abs(z - 27) < 3) {
            feed(i, TAG.CV2, 'cv2');
            flow.oreOut++;
          }
          break;
        case TAG.CV2:
          if (distance[i] > paths.cv2.len - .65) {
            w.relabel(i, TAG.WELL);
            flow.raised++;
          }
          break;
        case TAG.WELL:
          if (x > 106 && y > 49) {
            w.relabel(i, TAG.BIN);
            flow.binned++;
          }
          break;
        case TAG.BIN:
          if (flow.train && flow.binOpen > .53 && y < 12.05 && Math.abs(x - 114) < 5 && Math.abs(z + 8) < 5 && flow.train.cargo.length < 26) flow.takeBin(i, flow.train);else if (y < 7) w.relabel(i, TAG.SPILL);
          break;
        case TAG.CV3:
          if (distance[i] > paths.cv3.len - .65) {
            w.relabel(i, TAG.WASTE);
            w.vx[i] = 3.5;
            w.vy[i] = -.8;
            flow.wasteDropped++;
          }
          break;
        case TAG.WASTE:
          if (age > 32 || y < -170) w.kill(i);
          break;
        case TAG.SPILL:
          if (age > 18) w.kill(i);
          break;
      }
      if (y < -280 && w.state[i]) {
        w.kill(i);
        flow.transportLoss++;
      } else if (t >= TAG.BOOM && t <= TAG.CV3 && t !== TAG.BIN && t !== TAG.SHOT && age > 105 && w.state[i]) {
        w.relabel(i, TAG.SPILL);
        flow.transportLoss++;
      }
    }
  };
  flow.frame = () => {
    if (axis) axis.quaternion.setFromAxisAngle(wheelAxis, flow.wheelAngle);
    if (superObj) superObj.rotation.y = flow.slew;
    if (jigDoor) jigDoor.position.y = jigRest.y + flow.gate * 5.6;
    if (binDoor) binDoor.position.x = binRest.x + flow.binOpen * 5;
    if (rake) rake.rotation.y = sim.time * .036;
  };
  // The first shift starts with broken ore in transit. Counters start at zero.
  for (let i = 0; i < 46; i++) w.spawn(TAG.BIN, 114 + (R() - .5) * 6, 24 + i * .13, -8 + (R() - .5) * 5, {
    r: .46 + R() * .17
  });
  for (let i = 0; i < 44; i++) w.spawn(TAG.JIG, 69 + R() * 10, 4 + R() * 2.8, 23 + R() * 6, {
    r: .45 + R() * .16,
    kind: R() < .32 ? 1 : 0
  });
  for (const [tag, name, number] of [[TAG.BOOM, 'boom', 41], [TAG.DISCHARGE, 'dis', 50], [TAG.CV2, 'cv2', 12], [TAG.CV3, 'cv3', 15]]) {
    const line = paths[name];
    for (let k = 0; k < number; k++) {
      const ss = (k + .2) * line.len / number,
        j = Math.max(0, line.seg.findIndex(q => ss <= q.s + q.len)),
        q = line.seg[j],
        u = ss - q.s;
      const i = w.spawn(tag, q.a[0] + q.dx * u + (R() - .5) * .9, q.a[1] + q.dy * u + .78, q.a[2] + q.dz * u + (R() - .5) * .9, {
        r: .44 + R() * .22,
        vx: 3.8 * q.dx,
        vy: 3.8 * q.dy,
        vz: 3.8 * q.dz,
        kind: tag === TAG.CV3 ? 1 : 0
      });
      idx[i] = j;
      distance[i] = ss;
    }
  }
  for (let j = 0; j < 13; j++) w.spawn(TAG.WELL, 98 + (R() - .5) * 1.4, 6 + j * 3.8, -8 + (R() - .5) * 1.4, {
    r: .48,
    vy: 6.7
  });
  sim.add('ore', flow);
}
