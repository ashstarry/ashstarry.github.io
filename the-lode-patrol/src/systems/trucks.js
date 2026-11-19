import * as T from 'three';
import { TAG, clamp, rng } from '../physics/world.js';
import { Route, pose } from './tracks.js';
import { V, bl } from './view.js';
export function trucks(app) {
  const sim = app.sim,
    w = sim.world,
    flow = app.sys.ore,
    R = rng(773);
  const wall = app.layout.pit?.paths?.wall || [{
    p: [-91, 1.6, -110],
    up: [0, 1, 0]
  }, {
    p: [-88, -37, -84],
    up: [0, 0, 1]
  }, {
    p: [-85, -73.4, -60],
    up: [0, 1, 0]
  }];
  const load = app.mark('pit', 'wall_load', [-84.7, -73.4, -60]);
  let end = 0,
    err = 1e9;
  wall.forEach((s, i) => {
    const d = V(...s.p).distanceTo(load);
    if (d < err) {
      end = i;
      err = d;
    }
  });
  const data = wall.slice(0, end + 1).reverse().map(s => ({
    p: s.p,
    up: s.up
  }));
  const hh = (x, by) => w.ground(x, -by) + .15;
  const north = [[-96, 118], [-86, 108], [-60, 105], [-50, 104], [-20, 92], [8, 70], [29, 47], [35, 42], [45, 40], [50, 40]];
  const curve = new T.CatmullRomCurve3([V(...data.at(-1).p), ...north.map(([x, y]) => bl(x, y, hh(x, y)))], false, 'centripetal');
  for (let i = 1; i <= 58; i++) {
    const p = curve.getPoint(i / 58);
    p.y = Math.max(-.6, w.ground(p.x, p.z)) + .22;
    data.push({
      p: p.toArray()
    });
  }
  const route = new Route(data),
    revPoints = [];
  for (let j = 0; j <= 24; j++) {
    const t = j / 24,
      a = Math.PI / 2 * t;
    const x = 50 - 10 * Math.sin(a),
      y = 30 + 10 * Math.cos(a);
    revPoints.push({
      p: bl(x, y, hh(x, y)).toArray()
    });
  }
  const parking = new Route(revPoints),
    tr = {
      loaded: 0,
      unloaded: 0,
      trips: 0,
      cars: []
    },
    loaders = [];
  for (let j = 0; j < 2; j++) {
    const o = app.clone('fleet', 'loader');
    o.position.copy(load).add(V(j ? 8 : -8, 0, j ? 4 : -3));
    o.rotation.y = j ? Math.PI : .15;
    loaders.push(o);
  }
  const local = V(),
    front = pose(),
    rear = pose(),
    cross = V(),
    up = V(),
    basis = new T.Matrix4(),
    tilt = new T.Quaternion(),
    Z = V(0, 0, 1),
    S = .65;
  function cab(i, s, stage) {
    const obj = app.clone('fleet', 'truck'),
      bed = obj.getObjectByName('truck_bed');
    const c = {
      id: i,
      obj,
      bed,
      cargo: [],
      v: 0,
      s,
      stage,
      wait: 0,
      tip: 0,
      lean: 0,
      sink: 0,
      springV: 0,
      dumpT: 0,
      scoops: 0,
      pose: pose(),
      wheels: [],
      drive: 0
    };
    obj.traverse(o => {
      if (/^truck_wheel_(fl|fr|rl|rr)$/.test(o.name)) c.wheels.push(o);
    });
    return c;
  }
  tr.cars = [cab(0, 0, 'load'), cab(1, 41, 'out'), cab(2, route.len * .62, 'back')];
  const pending = new Int8Array(w.cap);
  function addCargo(c) {
    const i = w.spawn(TAG.TRUCK, 0, 0, 0, {
      r: .52 + .15 * R()
    });
    if (i < 0) return;
    w.hold(i, TAG.TRUCK, c.id);
    c.cargo.push(i);
    c.springV -= .35;
  }
  for (let j = 0; j < 14; j++) addCargo(tr.cars[1]);
  const floorBoxes = [];
  for (const c of tr.cars) {
    const d = app.layout.fleet?.colliders?.find(b => b.tag === 'truck_bed_floor');
    const floor = w.addBox({
      p: [0, 0, 0],
      h: d?.h || [3.9, .17, 2.8],
      q: [0, 0, 0, 1],
      tag: 'unloading_truck',
      mu: .36
    }, true);
    floor.on = false;
    floorBoxes.push(floor);
  }
  function position(c) {
    const reversing = c.stage === 'reverse' || c.stage === 'dump' || c.stage === 'leave',
      home = c.stage === 'back',
      r = reversing ? parking : route;
    const ss = reversing ? c.parkingS : c.s,
      side = reversing ? 0 : home ? -2.5 : 2.5;
    r.at(ss || 0, c.pose, side);
    r.at((ss || 0) + 3.8, front, side);
    r.at((ss || 0) - 3.8, rear, side);
    const flip = home || reversing;
    const t = c.pose.t.subVectors(front.p, rear.p).normalize();
    if (flip) t.negate();
    cross.crossVectors(t, c.pose.up).normalize();
    up.crossVectors(cross, t).normalize();
    c.pose.q.setFromRotationMatrix(basis.makeBasis(t, up, cross));
    c.obj.position.copy(c.pose.p).addScaledVector(up, c.sink);
    c.obj.quaternion.copy(c.pose.q).multiply(tilt.setFromAxisAngle(Z, c.lean));
    if (c.bed) c.bed.rotation.z = c.tip;
    for (const o of c.wheels) o.rotation.z = -c.drive / 1.9;
    const floor = floorBoxes[c.id];
    floor.on = c.stage === 'dump' && c.bed;
    if (floor.on) {
      local.set(2.79, .33, 0);
      c.bed.localToWorld(local);
      floor.p = local.toArray(floor.p);
      c.bed.getWorldQuaternion(tilt);
      floor.q = tilt.toArray(floor.q);
      floor.cache();
    }
  }
  tr.pre = dt => {
    for (const c of tr.cars) {
      const old = c.v,
        go = c.stage === 'out' || c.stage === 'back';
      if (go) {
        const sign = c.stage === 'out' ? 1 : -1,
          remain = sign === 1 ? route.len - c.s : c.s;
        route.at(c.s, c.pose);
        let max = Math.abs(c.pose.up.y) < .6 ? 6.5 : 9;
        for (const n of tr.cars) if (n !== c && n.stage === c.stage) {
          const gap = (n.s - c.s) * sign;
          if (gap > 0 && gap < 19) max = Math.min(max, Math.max(0, gap - 14) * .6);
        }
        const target = Math.min(max, Math.sqrt(Math.max(0, remain) * 4.8));
        c.v = clamp(target, c.v - 2.4 * dt, c.v + 2.3 / (1 + c.cargo.length / 18) * dt);
        c.s = clamp(c.s + c.v * sign * dt, 0, route.len);
        if (remain < .12) {
          c.v = 0;
          if (sign === 1) {
            c.stage = 'reverse';
            c.parkingS = 0;
          } else {
            c.stage = 'load';
            c.s = 0;
            c.wait = 0;
            c.scoops = 0;
          }
        }
      } else if (c.stage === 'load') {
        c.wait -= dt;
        if (c.wait <= 0) {
          for (let j = 0; j < 3 && c.cargo.length < 14; j++) {
            addCargo(c);
            tr.loaded++;
          }
          c.scoops++;
          c.wait = 1.65 + R() * 1.4;
        }
        if (c.cargo.length >= 14) {
          c.stage = 'out';
          c.wait = 0;
        }
      } else if (c.stage === 'reverse' || c.stage === 'leave') {
        const arriving = c.stage === 'reverse';
        c.v = Math.min(c.v + 1.1 * dt, 2.2);
        c.parkingS = clamp(c.parkingS + (arriving ? 1 : -1) * c.v * dt, 0, parking.len);
        if (arriving && c.parkingS >= parking.len || !arriving && c.parkingS <= 0) {
          c.v = 0;
          c.stage = arriving ? 'dump' : 'back';
          c.dumpT = 0;
        }
      } else if (c.stage === 'dump') {
        c.dumpT += dt;
        c.tip = c.dumpT < 7 ? Math.min(.907, c.tip + dt * .21) : Math.max(0, c.tip - dt * .25);
        if (c.tip > .31 && c.cargo.length && c.dumpT > (14 - c.cargo.length) * .22 + 1.3) {
          const i = c.cargo.shift();
          local.set(1.5 + R() * 3.2, .8 + R() * .8, (R() - .5) * 3);
          if (c.bed) c.bed.localToWorld(local);else local.copy(c.obj.position);
          w.release(i, TAG.DUMP, local.x, local.y, local.z, -c.pose.t.x * .7, -.2, -c.pose.t.z * .7);
          pending[i] = 1;
        }
        if (c.dumpT > 11 && !c.cargo.length) {
          c.stage = 'leave';
          tr.trips++;
        }
      }
      c.drive += c.v * dt;
      c.lean += ((old - c.v) / dt * .011 - c.lean) * Math.min(1, dt * 7);
      const sink = -.013 * c.cargo.length;
      c.springV += ((sink - c.sink) * 12 - c.springV * 4) * dt;
      c.sink += c.springV * dt;
      position(c);
    }
  };
  w.forces[TAG.DUMP] = (i, a) => {
    if (w.stageAge[i] > .8) {
      a[0] += (40 - w.x[i]) * .9 - w.vx[i] * .6;
      a[2] += (-24 - w.z[i]) * .9 - w.vz[i] * .6;
    }
  };
  tr.post = () => {
    for (let j = w.count - 1; j >= 0; j--) {
      const i = w.order[j];
      if (w.tag[i] !== TAG.DUMP) continue;
      if (w.y[i] < 2.1 && Math.hypot(w.x[i] - 40, w.z[i] + 24) < 7) {
        w.kill(i);
        flow.addCrusher();
        tr.unloaded++;
      } else if (w.stageAge[i] > 17) w.relabel(i, TAG.SPILL);
    }
  };
  tr.frame = () => {
    for (const c of tr.cars) {
      for (let k = 0; k < c.cargo.length; k++) {
        const i = c.cargo[k];
        local.set(1.2 + k % 4 * 1.2, .78 + (k / 8 | 0) * .8, ((k / 4 | 0) % 2 - .5) * 1.25);
        if (c.bed) c.bed.localToWorld(local);else local.copy(c.obj.position);
        w.x[i] = local.x;
        w.y[i] = local.y;
        w.z[i] = local.z;
      }
    }
    const working = tr.cars.find(c => c.stage === 'load');
    loaders.forEach((o, j) => {
      const arm = o.getObjectByName('loader_arm'),
        bucket = o.getObjectByName('loader_bucket'),
        t = sim.time * (working ? 2.25 : .12) + j * 2;
      if (arm) arm.rotation.z = .12 + .44 * Math.sin(t);
      if (bucket) bucket.rotation.z = -.22 + .41 * Math.sin(t + .8);
    });
  };
  sim.add('trucks', tr);
}
