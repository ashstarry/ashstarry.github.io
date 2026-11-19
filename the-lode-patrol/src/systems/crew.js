import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { rng, clamp } from '../physics/world.js';
import { V, bl } from './view.js';
export function templateBatch(app, part, name, count) {
  const src = app.find(part, name),
    groups = new Map(),
    meshes = [];
  if (src) {
    src.updateWorldMatrix(true, true);
    const inv = src.matrixWorld.clone().invert(),
      rel = new T.Matrix4();
    src.traverse(o => {
      if (!o.isMesh) return;
      const g = o.geometry.clone().applyMatrix4(rel.multiplyMatrices(inv, o.matrixWorld));
      let set = groups.get(o.material);
      if (!set) groups.set(o.material, set = []);
      set.push(g);
    });
  }
  if (!groups.size) groups.set(new T.MeshStandardMaterial({
    color: 0x81653e
  }), [new T.BoxGeometry(1, 2, 1)]);
  for (const [m, gs] of groups) {
    const geo = gs.length > 1 ? mergeGeometries(gs, false) : gs[0];
    if (!geo) continue;
    const inst = new T.InstancedMesh(geo, m, count);
    inst.instanceMatrix.setUsage(T.DynamicDrawUsage);
    inst.receiveShadow = true;
    inst.frustumCulled = false;
    app.scene.add(inst);
    meshes.push(inst);
  }
  return {
    meshes,
    set(i, obj) {
      obj.updateMatrix();
      for (const mesh of meshes) mesh.setMatrixAt(i, obj.matrix);
    },
    finish() {
      for (const mesh of meshes) mesh.instanceMatrix.needsUpdate = true;
    }
  };
}
export function crew(app) {
  const sim = app.sim,
    w = sim.world,
    R = rng(14124),
    s = {
      people: 64,
      drones: 4,
      cuts: 0
    },
    ring = app.find('habitat', 'hab_ring'),
    radar = app.find('port', 'port_radar'),
    dum = new T.Object3D();
  const routes = [[[47, 89], [60, 87], [70, 88], [82, 87]], [[63, 103], [66, 112], [85, 114]], [[55, 127], [70, 129], [82, 134]], [[109, 124], [122, 118], [137, 119]], [[107, 156], [110, 167], [120, 171]], [[47, 153], [50, 163], [65, 169]], [[80, 81], [93, 79], [111, 80]], [[86, 132], [95, 126], [106, 127]], [[24, 8], [34, 3], [47, 4]], [[63, -37], [73, -39], [82, -36]], [[92, -44], [103, -38], [109, -31]], [[36, 33], [47, 37], [55, 35]], [[-182, -37], [-180, -47], [-169, -48]], [[-92, 104], [-78, 105], [-64, 103]], [[42, -147], [54, -146], [68, -145]], [[91, -112], [105, -109], [119, -111]], [[-48, -149], [-58, -146], [-69, -146]], [[229, -88], [242, -90], [255, -88]], [[242, -19], [252, -15], [263, -14]], [[257, -104], [264, -109], [267, -117]]];
  const batches = [templateBatch(app, 'fleet', 'person_a', 32), templateBatch(app, 'fleet', 'person_b', 32)],
    people = [];
  for (let i = 0; i < 64; i++) {
    const j = i % routes.length,
      list = routes[j].map(([x, y]) => bl(x, y, w.ground(x, -y))),
      hab = j < 8,
      t = R();
    const lamp = app.lights.add({
      p: [0, 0, 0],
      c: [1, .53, .21],
      i: .32,
      r: 4,
      k: 'lamp'
    });
    people.push({
      list,
      hab,
      seg: R() * (list.length - 1) | 0,
      dir: R() < .5 ? 1 : -1,
      t,
      speed: hab ? 1.1 + R() * .6 : 2.2 + 1.2 * R(),
      cycle: 1.6 + R() * .8,
      phase: R() * 5,
      lamp,
      p: V(),
      theta: 0,
      delay: R() * 2
    });
  }
  const drones = [];
  for (let j = 0; j < 4; j++) {
    const o = app.clone('fleet', 'drone');
    drones.push({
      o,
      p: bl(-70 + j * 49, 20 * j - 75, 32 + j * 6),
      v: V(),
      target: V(),
      until: 0,
      j
    });
  }
  const yard = [['truck', -15, -151, .25], ['loader', 5, -148, .4], ['rover', -5, -160, 1.1], ['container_a', -25, -152, .15], ['container_c', -20, -159, -.12], ['truck', 115, -99, 1.4], ['shuttle', 121, -116, -.27]];
  for (const [n, x, y, a] of yard) {
    const o = app.clone('fleet', n);
    o.position.copy(n === 'shuttle' ? app.mark('fill', 'shuttle_pad', [x, w.ground(x, -y), -y]) : bl(x, y, w.ground(x, -y)));
    o.rotation.y = a;
  }
  const cuts = [0, 1, 2].map(j => {
    const p = app.mark('fill', 'wreck_cut_' + j, [-60 + j * 21, -9, 166]);
    const light = app.lights.add({
      p: p.toArray(),
      c: [1, .34, .085],
      i: 0,
      r: 9,
      k: 'aura'
    });
    return {
      p,
      light,
      next: 1 + j * 2,
      until: -1
    };
  });
  s.pre = dt => {
    for (const h of people) {
      if (h.delay > 0) h.delay -= dt;else {
        const a = h.list[h.seg],
          b = h.list[h.seg + 1],
          len = a.distanceTo(b);
        h.t += h.dir * h.speed * dt / Math.max(1, len);
        if (h.t >= 1 || h.t <= 0) {
          if (h.t >= 1 && h.seg + 2 < h.list.length) {
            h.seg++;
            h.t = 0;
          } else if (h.t <= 0 && h.seg > 0) {
            h.seg--;
            h.t = 1;
          } else {
            h.t = clamp(h.t, 0, 1);
            h.dir *= -1;
            h.delay = .45 + R() * 3.5;
          }
        }
      }
    }
    for (const d of drones) {
      if (d.until < sim.time || d.p.distanceToSquared(d.target) < 16) {
        d.target.set(-125 + R() * 270, 23 + R() * 50, -145 + R() * 285);
        d.until = sim.time + 8 + R() * 13;
      }
      const v = V().subVectors(d.target, d.p).multiplyScalar(.105).addScaledVector(d.v, -.45);
      if (v.lengthSq() > 9) v.setLength(3);
      d.v.addScaledVector(v, dt);
      d.p.addScaledVector(d.v, dt);
    }
    for (const c of cuts) {
      if (sim.time >= c.next) {
        c.until = sim.time + .65 + R() * 1.2;
        c.next = c.until + 2 + R() * 9;
        s.cuts++;
      }
      if (sim.time < c.until && R() < dt * 12) app.sys.dust?.spark(c.p, 2);
    }
  };
  s.frame = () => {
    if (ring) ring.rotation.y = sim.time * .11;
    if (radar) radar.rotation.y = sim.time * .28;
    for (let i = 0; i < people.length; i++) {
      const h = people[i],
        a = h.list[h.seg],
        b = h.list[h.seg + 1],
        t = h.t;
      h.p.copy(a).lerp(b, t);
      const g = w.ground(h.p.x, h.p.z);
      if (g > -9000) h.p.y = g;
      const cycle = (sim.time / h.cycle + h.phase) % 1;
      h.p.y += h.hab ? .035 * Math.sin(sim.time * 6 + h.phase) : h.delay > 0 ? 0 : 1.05 * 4 * cycle * (1 - cycle);
      dum.position.copy(h.p);
      dum.rotation.set(0, Math.atan2(-(b.z - a.z) * h.dir, (b.x - a.x) * h.dir), 0);
      batches[i % 2].set(i >> 1, dum);
      if (h.lamp) {
        h.lamp.p.copy(h.p).y += 1.55;
        h.lamp.dirty = true;
      }
    }
    for (const b of batches) b.finish();
    for (const d of drones) {
      d.o.position.copy(d.p);
      d.o.rotation.y = Math.atan2(-d.v.z, d.v.x);
      d.o.rotation.z = clamp(d.v.y * .09, -.22, .22);
    }
    for (const c of cuts) if (c.light) {
      c.light.power = sim.time < c.until ? .95 * Math.sin(Math.min(1, (c.until - sim.time) / .5) * Math.PI * .5) : 0;
      c.light.dirty = true;
    }
  };
  sim.add('crew', s);
}
