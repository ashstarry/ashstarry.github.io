import * as T from 'three';
import { TAG } from './world.js';
import { rope, Net } from './rigid.js';
import { V, GrainView, segments, updateLines } from '../systems/view.js';
export function sandbox(app, name) {
  const sim = app.sim,
    w = sim.world,
    rig = sim.rigid;
  w.field.lode.on = false;
  w.field.plateG = 9.8;
  const names = {
    pile: 'Granular pile',
    grains: 'Granular pile',
    funnel: 'Hopper flow',
    rigid: 'Rigid-body collisions',
    rope: 'Suspended load',
    bridge: 'Off-center bridge load'
  };
  const group = new T.Group();
  app.scene.add(group);
  const objects = [];
  const box = (p, s, color, quat = null) => {
    const o = new T.Mesh(new T.BoxGeometry(...s), new T.MeshStandardMaterial({
      color,
      roughness: .73,
      metalness: .24
    }));
    o.position.fromArray(p);
    if (quat) o.quaternion.copy(quat);
    o.receiveShadow = o.castShadow = true;
    group.add(o);
    return o;
  };
  box([0, -1, 0], [78, 2, 48], 0x66615a);
  app.camera.position.set(40, 35, 64);
  app.controls.target.set(0, 8, 0);
  app.controls.update();
  app.controls.minDistance = 12;
  const grains = new GrainView(app, w),
    nets = [];
  if (name === 'pile' || name === 'grains' || name === 'funnel') {
    if (name === 'funnel') {
      for (let k = 0; k < 4; k++) {
        const an = k * Math.PI / 2,
          quat = new T.Quaternion().setFromEuler(new T.Euler(-.7, an, 0, 'YXZ'));
        const p = [Math.sin(an) * 4.9, 9, Math.cos(an) * 4.9],
          s = [14, .65, 8];
        box(p, s, 0x906442, quat);
        w.addBox({
          p,
          h: s.map(a => a / 2),
          q: quat.toArray()
        });
      }
    }
    for (let i = 0; i < 190; i++) {
      const r = w.rand;
      w.spawn(TAG.GROUND, (r() - .5) * 10, 13 + (i / 30 | 0) * 1.8, (r() - .5) * 10, {
        r: .52 + r() * .35,
        kind: i % 3
      });
    }
  } else if (name === 'rigid') {
    for (let i = 0; i < 8; i++) {
      const body = rig.body(V(i % 2 * 2, i * 2.5 + 2, 0), 14, 1.6, {
        balls: [{
          p: V(-.7, 0, 0),
          r: .93
        }, {
          p: V(.7, 0, 0),
          r: .93
        }]
      });
      body.w.set(.1 * i, .12, .35);
      objects.push([body, box(body.p.toArray(), [3.1, 1.8, 1.8], i % 2 ? 0x91623c : 0x67695d)]);
    }
  } else if (name === 'rope') {
    const fixed = v => v.set(-7, 27, 0),
      body = rig.body(V(10, 10, 0), 35, 2),
      net = rope(fixed, {
        body,
        offset: V(0, 1.5, 0)
      }, 24, 22);
    rig.nets.push(net);
    nets.push([net, segments(app, 22, .16)]);
    objects.push([body, box(body.p.toArray(), [4, 3, 3], 0x946030)]);
    box([-7, 13, -2], [1.2, 26, 1.2], 0x625c56);
  } else {
    const net = new Net();
    net.ground = false;
    for (let i = 0; i <= 24; i++) {
      for (let s = 0; s < 2; s++) {
        const p = V(-25 + 50 * i / 24, 9, (s - .5) * 6);
        net.node(p, 8, i === 0 || i === 24 ? v => v.copy(p) : null);
        if (i) net.edge(i * 2 + s - 2, i * 2 + s, null, 1e-8);
      }
      net.edge(2 * i, 2 * i + 1, null, 1.e-8);
      if (i) {
        net.edge(i * 2 - 2, i * 2 + 1, null, 1e-7);
        net.edge(i * 2 - 1, i * 2, null, 1e-7);
      }
    }
    rig.nets.push(net);
    const planks = Array.from({
      length: 24
    }, () => box([0, 9, 0], [2.1, .45, 6.3], 0x796b5d));
    const load = box([-20, 10, 2], [3, 2, 2], 0xb18743);
    sim.add('load', {
      pre() {
        const f = (.5 + .48 * Math.sin(sim.time * .28)) * 23;
        for (const n of net.nodes) n.load = 0;
        net.nodes[(f | 0) * 2 + 1].load = 1100;
        load.position.copy(net.nodes[(f | 0) * 2 + 1].p).y += 1.25;
      },
      frame() {
        planks.forEach((o, i) => o.position.copy(net.nodes[i * 2].p).lerp(net.nodes[i * 2 + 3].p, .5));
      }
    });
  }
  app.sys.sandbox = {
    name: names[name] || name
  };
  sim.add('sandView', {
    frame() {
      grains.frame();
      for (const [b, o] of objects) {
        o.position.copy(b.p);
        o.quaternion.copy(b.q);
      }
      for (const [net, o] of nets) updateLines(o, net.nodes);
    }
  });
}
