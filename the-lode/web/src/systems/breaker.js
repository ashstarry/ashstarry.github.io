import * as T from 'three';
import { rng, clamp } from '../physics/world.js';
import { rope } from '../physics/rigid.js';
import { bl, V, segments, updateLines, smooth } from './view.js';
export function breaker(app) {
  const sim = app.sim,
    rig = sim.rigid,
    rand = rng(371),
    maw = app.mark('pit', 'maw', [27, 66, -13]),
    grip = maw.clone().add(V(0, 40, 0)),
    station = app.clone('fleet', 'breaker'),
    tug = app.clone('fleet', 'tug');
  station.position.copy(grip);
  const jaws = ['br_jaw_a', 'br_jaw_b'].map(n => station.getObjectByName(n)),
    jawRest = jaws.map(o => o?.position.clone()),
    ram = station.getObjectByName('br_ram'),
    ramX = ram?.position.x || -57;
  const tugBody = rig.body(grip.clone(), 90, 4, {
      who: 8,
      ground: false,
      boxes: false,
      mutual: false,
      damping: .03
    }),
    stone = rig.body(grip.clone(), 2600, 14, {
      who: 8,
      ground: false,
      boxes: false,
      mutual: false,
      damping: .008
    });
  const s = {
    phase: 'idle',
    cycles: 0,
    impacts: 0,
    ground: 0,
    lost: 0,
    fragments: [],
    age: 0,
    models: [],
    jaw: 0,
    hammer: 0,
    hammerV: 0,
    tension: 0,
    momentumError: 0,
    table: null,
    feedTimer: 0
  };
  let ropeNet,
    ropeMesh,
    rock,
    which = 0;
  const dir = V(),
    target = V(),
    force = V(),
    acc = [0, 0, 0, 0],
    tmp = V(),
    qx = new T.Quaternion(),
    forward = V(1, 0, 0);
  const vec = (v, max) => {
    if (v.lengthSq() > max * max) v.setLength(max);
    return v;
  };
  function begin() {
    const name = which++ % 2 ? 'ast_B' : 'ast_A';
    rock = app.clone('rocks', name, false);
    s.table = app.layout.rocks?.fractures?.[name] || [];
    s.age = 0;
    s.phase = 'tow';
    s.jaw = s.hammer = s.hammerV = 0;
    tug.visible = true;
    const start = grip.clone().add(V(-114 - rand() * 35, 21 + rand() * 16, -75 + rand() * 20));
    stone.on = true;
    stone.kinematic = false;
    stone.p.copy(start);
    stone.q.identity();
    stone.v.subVectors(grip, start).setLength(9);
    stone.w.set(.025, -.019, .014);
    stone.force.set(0, 0, 0);
    dir.subVectors(grip, start).normalize();
    tugBody.on = true;
    tugBody.kinematic = false;
    tugBody.p.copy(start).addScaledVector(dir, 46);
    tugBody.v.copy(stone.v);
    ropeNet = rope({
      body: tugBody,
      offset: V(-3, 0, 0)
    }, {
      body: stone,
      offset: V(4, 1, 0)
    }, 46, 20, 3.e-7);
    ropeNet.ground = false;
    ropeNet.drag = .5;
    rig.nets.push(ropeNet);
    if (!ropeMesh) ropeMesh = segments(app, 20, .15, 0x796953);
    ropeMesh.visible = true;
  }
  function unhook() {
    const k = rig.nets.indexOf(ropeNet);
    if (k >= 0) rig.nets.splice(k, 1);
    ropeNet.on = false;
    ropeMesh.visible = false;
    tugBody.v.set(4, 3, -1);
  }
  function impact() {
    s.phase = 'fractured';
    s.age = 0;
    s.impacts++;
    stone.on = false;
    rock.updateMatrixWorld(true);
    const list = s.table.length ? s.table : Array.from({
      length: 32
    }, (_, k) => ({
      name: 'piece' + k,
      p: [(rand() - .5) * 14, (rand() - .5) * 14, (rand() - .5) * 14],
      massFraction: 1 / 32,
      radius: 2.8
    }));
    const average = V(),
      bulk = stone.v.clone().add(V(.92, .05, 0));
    let mass = 0;
    for (const part of list) {
      let obj = rock.getObjectByName(part.name);
      if (!obj) obj = app.clone('rocks', 'chunk_a', false);
      app.scene.attach(obj);
      const dp = V(...part.p).applyQuaternion(stone.q),
        m = 2600 * part.massFraction;
      const body = rig.body(stone.p.clone().add(dp), m, part.radius, {
        who: 8,
        ground: false,
        boxes: false,
        group: which,
        groupTime: rig.time + 1,
        damping: .075
      });
      body.q.copy(stone.q);
      body.v.copy(dp).normalize().multiplyScalar(2.4 + rand() * 3.7).add(V(.9 + rand() * 2, (rand() - .5) * 2, (rand() - .5) * 2));
      body.w.set((rand() - .5) * 1.2, (rand() - .5) * 1.3, (rand() - .5) * 1.4);
      average.addScaledVector(body.v, m);
      mass += m;
      s.fragments.push({
        body,
        obj,
        grind: 0,
        start: 1,
        r: part.radius
      });
    }
    average.multiplyScalar(1 / mass);
    const sum = V();
    for (const p of s.fragments) {
      p.body.v.sub(average).add(bulk);
      sum.addScaledVector(p.body.v, p.body.mass);
    }
    s.momentumError = sum.distanceTo(bulk.clone().multiplyScalar(mass));
    rock.visible = false;
    app.scene.remove(rock);
    app.sys.dust?.spark(grip, 18);
  }
  begin();
  s.tugPoint = tugBody.p;
  s.pre = dt => {
    s.age += dt;
    if (s.phase === 'tow') {
      dir.subVectors(grip, stone.p);
      const dist = dir.length();
      force.copy(dir).multiplyScalar(.082).addScaledVector(stone.v, -.82);
      sim.field.accel(stone.p.x, stone.p.y, stone.p.z, acc, 8);
      force.sub(tmp.set(...acc));
      vec(force, 3.4);
      target.copy(stone.p).addScaledVector(force.clone().normalize(), 48 + Math.min(14, force.length() * 5));
      tugBody.force.copy(target).sub(tugBody.p).multiplyScalar(1.8).addScaledVector(stone.v, 2.4).addScaledVector(tugBody.v, -2.4);
      vec(tugBody.force, 52);
      s.tension = Math.max(0, tugBody.p.distanceTo(stone.p) - 44);
      if (dist < 18) {
        stone.force.copy(dir).multiplyScalar(.21).addScaledVector(stone.v, -.85);
      } else stone.force.set(0, 0, 0);
      if (dist < 5.5 && stone.v.length() < 3.6) {
        s.phase = 'clamp';
        s.age = 0;
        unhook();
        stone.force.set(0, 0, 0);
      }
    } else if (s.phase === 'clamp') {
      s.jaw = smooth(s.age / 3);
      stone.force.subVectors(grip, stone.p).multiplyScalar(2.6).addScaledVector(stone.v, -3.3);
      tugBody.force.set(3, 1.3, -1.7);
      if (s.age > 3.8) {
        stone.kinematic = true;
        stone.v.set(0, 0, 0);
        s.phase = 'wait';
        s.age = 0;
      }
    } else if (s.phase === 'wait' && s.age > 6) {
      s.phase = 'strike';
      s.age = 0;
    } else if (s.phase === 'strike') {
      s.hammerV += 55 * dt;
      s.hammer += s.hammerV * dt;
      if (s.hammer >= 40) {
        s.hammer = 40;
        impact();
      }
    } else if (s.phase === 'fractured') {
      s.jaw = Math.max(0, s.jaw - dt * .28);
      s.hammer = Math.max(0, s.hammer - dt * 4.7);
      for (const p of s.fragments) {
        if (p.grind) continue;
        const body = p.body;
        dir.subVectors(maw, body.p);
        const dist = dir.length();
        body.force.copy(dir).multiplyScalar((2.6 * Math.max(0, 1 - dist / 120) + .7) / Math.max(dist, .1)).addScaledVector(body.v, -.22);
      }
    } else if (s.phase === 'idle' && s.age > s.feedTimer) begin();
  };
  s.post = dt => {
    for (let k = s.fragments.length - 1; k >= 0; k--) {
      const p = s.fragments[k],
        b = p.body,
        d = b.p.distanceTo(maw);
      if (!p.grind && d < 7.5) {
        p.grind = .0001;
        b.kinematic = true;
        b.v.set(0, 0, 0);
        app.sys.dust?.spark(maw, 6);
      }
      if (p.grind) {
        p.grind += dt;
        b.p.lerp(maw, Math.min(1, dt * 3.4));
      }
      if (p.grind > 1.2 || d > 330) {
        if (d > 330) s.lost++;else {
          s.ground++;
          app.sys.ore.addCrusher(3);
        }
        b.on = false;
        rig.bodies.splice(rig.bodies.indexOf(b), 1);
        p.obj.visible = false;
        app.scene.remove(p.obj);
        s.fragments.splice(k, 1);
      }
    }
    if (s.phase === 'fractured' && !s.fragments.length) {
      s.cycles++;
      s.phase = 'idle';
      s.age = 0;
      s.feedTimer = 14 + rand() * 30;
    }
  };
  s.frame = () => {
    if (rock.visible) {
      rock.position.copy(stone.p);
      rock.quaternion.copy(stone.q);
    }
    tug.position.copy(tugBody.p);
    if (tugBody.v.length() > .1) tug.quaternion.slerp(qx.setFromUnitVectors(forward, dir.copy(tugBody.v).normalize()), .22);
    tug.visible = tugBody.p.distanceTo(grip) < 480;
    if (ropeNet.on) updateLines(ropeMesh, ropeNet.nodes);
    jaws.forEach((o, j) => {
      if (o) o.position.z = jawRest[j].z + (j ? -1 : 1) * 5 * s.jaw;
    });
    if (ram) ram.position.x = ramX + s.hammer;
    for (const p of s.fragments) {
      p.obj.position.copy(p.body.p);
      p.obj.quaternion.copy(p.body.q);
      p.obj.scale.setScalar(Math.max(.015, 1 - p.grind / 1.2));
    }
  };
  sim.add('breaker', s);
}
