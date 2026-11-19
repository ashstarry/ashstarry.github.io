import * as T from 'three';
import { rope } from '../physics/rigid.js';
import { rng, clamp } from '../physics/world.js';
import { V, segments, updateLines, instances, setInstance, smooth } from './view.js';
export function portWork(app) {
  const sim = app.sim,
    r = sim.rigid,
    w = sim.world,
    R = rng(54362),
    crane = app.find('port', 'crane'),
    trolley = app.find('port', 'crane_trolley'),
    sp = app.find('port', 'crane_spreader'),
    home = crane?.position.clone() || V(291.5, -6.25, 38),
    tHome = trolley?.position.clone() || V(-7, 27.45, 0);
  const sg = app.layout.port?.quayGravity;
  if (sg) w.field.addZone({
    who: 2,
    minx: sg.min[0],
    miny: sg.min[1],
    minz: sg.min[2],
    maxx: sg.max[0],
    maxy: sg.max[1],
    maxz: sg.max[2],
    test: () => 1,
    g: sg.g
  });
  const initial = app.mark('port', 'crane_hook', [284.5, 7.2, 38]),
    spread = r.body(initial, 31, 3.8, {
      mutual: false,
      boxes: false,
      ground: false,
      damping: .51,
      balls: [{
        p: V(),
        r: .7
      }]
    });
  const x0 = app.mark('port', 'crane_line_a', [280.8, 21.2, 38]),
    x1 = app.mark('port', 'crane_line_b', [288.2, 21.2, 38]),
    top = x0.clone().lerp(x1, .5),
    beam = top.clone(),
    vel = V();
  const rigs = [];
  for (const [j, start] of [x0, x1].entries()) {
    const off = start.clone().sub(top),
      net = rope(out => out.copy(beam).add(off), {
        body: spread,
        offset: V(off.x, 0, 0)
      }, 14, 8, 1e-7);
    net.ground = false;
    net.multipleAttachments = true;
    net.drag = 1.2;
    r.nets.push(net);
    rigs.push([net, segments(app, 8, .11, 0x584f42)]);
  }
  if (sp) app.scene.attach(sp);
  const crates = [];
  for (let j = 0; j < 4; j++) {
    const src = app.mark('port', 'crane_src_' + j, [284.5, -5.05, 38 - j * 8]),
      dst = app.mark('port', 'crane_dst_' + j, [299, -5.05, 38 - j * 8]),
      body = r.body(src.clone(), 66, 5.8, {
        mutual: false,
        damping: .38,
        balls: [{
          p: V(-3.7, 0, 0),
          r: 1.43
        }, {
          p: V(3.7, 0, 0),
          r: 1.43
        }]
      });
    crates.push({
      src,
      dst,
      body,
      obj: app.clone('fleet', 'container_' + ['a', 'b', 'c', 'b'][j]),
      at: 0
    });
  }
  const s = {
      moves: 0,
      index: 0,
      phase: 'approach',
      age: 0,
      attached: false,
      ropeLength: 14,
      grabbed: 0,
      pivot: spread,
      crates
    },
    goal = V(),
    dif = V();
  const ties = [],
    offset = V(.37, 1.45, .18);
  function change(name) {
    s.phase = name;
    s.age = 0;
  }
  function attach(k) {
    k.landing = false;
    k.body.kinematic = false;
    k.body.force.set(0, 0, 0);
    k.body.wake();
    for (const xx of [-3.7, 3.7]) {
      const net = rope({
        body: spread,
        offset: V(xx, -.32, 0)
      }, {
        body: k.body,
        offset: V(xx + .37, 1.45, .18)
      }, .52, 1, 3e-7);
      net.ground = false;
      net.multipleAttachments = true;
      r.nets.push(net);
      ties.push(net);
    }
    s.attached = true;
    s.grabbed++;
  }
  function guide(k, slot) {
    const body = k.body;
    body.force.set(clamp((slot.x - body.p.x) * 1.6 - body.v.x * 1.8, -3, 3), 0, clamp((slot.z - body.p.z) * 1.6 - body.v.z * 1.8, -3, 3));
  }
  s.pre = dt => {
    s.age += dt;
    for (const c of crates) {
      if (!c.landing) continue;
      const slot = c.at ? c.dst : c.src;
      guide(c, slot);
      if (c.body.p.distanceToSquared(slot) < .18 && c.body.v.lengthSq() < .14) {
        c.body.kinematic = true;
        c.body.v.set(0, 0, 0);
        c.body.w.set(0, 0, 0);
        c.body.force.set(0, 0, 0);
        c.landing = false;
      }
    }
    const k = crates[s.index],
      from = k.body.p,
      to = k.at ? k.src : k.dst,
      arr = ['transport', 'lower', 'release'].includes(s.phase);
    goal.copy(arr ? to : from);
    if (s.phase === 'lift') goal.copy(k.at ? k.dst : k.src);
    goal.y = beam.y;
    if (s.phase === 'lower') guide(k, to);
    dif.subVectors(goal, beam);
    vel.addScaledVector(dif, dt * .53).multiplyScalar(1 / (1 + 1.35 * dt));
    if (vel.length() > 2.8) vel.setLength(2.8);
    beam.addScaledVector(vel, dt);
    const close = dif.length() < .52 && vel.length() < .6;
    let length = 14;
    if (s.phase === 'grab' || s.phase === 'lower' || s.phase === 'release') length = clamp(beam.y - (s.phase === 'grab' ? k.body.p.y : to.y) - 2.0, 4, 32);
    s.ropeLength += clamp(length - s.ropeLength, -2.7 * dt, 2.7 * dt);
    for (const [net] of rigs) {
      for (let j = 0; j < net.edges.length - 1; j++) net.edges[j].rest = s.ropeLength / 8;
      net.edges.at(-1).rest = s.ropeLength;
    }
    if (s.phase === 'approach' && close) change('grab');else if (s.phase === 'grab' && s.age > 3 && Math.abs(s.ropeLength - length) < .28 && Math.hypot(spread.p.x - k.body.p.x, spread.p.z - k.body.p.z) < 3.1) {
      attach(k);
      change('lift');
    } else if (s.phase === 'lift' && Math.abs(s.ropeLength - 14) < .4) change('transport');else if (s.phase === 'transport' && close) change('lower');else if (s.phase === 'lower' && Math.abs(s.ropeLength - length) < .3 && s.age > 4.5 && Math.hypot(k.body.p.x - to.x, k.body.p.z - to.z) < 1.9 && k.body.p.y < to.y + 1.1) {
      for (const t of ties) r.nets.splice(r.nets.indexOf(t), 1);
      ties.length = 0;
      s.attached = false;
      k.at = 1 - k.at;
      k.landing = true;
      s.moves++;
      change('release');
    } else if (s.phase === 'release' && s.age > 1.5) {
      s.index = (s.index + 1) % 4;
      change('approach');
    }
  };
  s.frame = () => {
    if (crane) crane.position.z = home.z + beam.z - top.z;
    if (trolley) trolley.position.x = tHome.x + beam.x - top.x;
    if (sp) {
      sp.position.copy(spread.p);
      sp.quaternion.copy(spread.q);
    }
    for (const [net, mesh] of rigs) updateLines(mesh, net.nodes);
    for (const k of crates) {
      k.obj.position.copy(k.body.p);
      k.obj.quaternion.copy(k.body.q);
    }
  };
  sim.add('crane', s);
  const breech = app.mark('port', 'md_breech', [266, -7, 128]),
    exit = app.mark('port', 'md_muzzle', [272, 16, 52]),
    direction = exit.clone().sub(breech).normalize(),
    len = exit.distanceTo(breech),
    sled = app.find('port', 'md_sled'),
    rest = sled?.position.clone(),
    charge = app.lights.add({
      p: breech.toArray(),
      r: 14,
      i: .1,
      c: [.52, .19, .075],
      k: 'aura'
    });
  const projectile = app.clone('fleet', 'pod', false),
    launch = {
      shots: 0,
      next: 35 + R() * 30,
      phase: 'idle',
      speed: 0,
      travel: 0,
      recoil: 0,
      rv: 0
    };
  projectile.visible = false;
  const pv = V(),
    pp = V();
  launch.pre = dt => {
    if (launch.phase === 'idle' && sim.time >= launch.next) {
      launch.phase = 'rail';
      launch.speed = launch.travel = 0;
      launch.shots++;
      launch.rv = -16;
      projectile.visible = true;
      app.sys.dust?.spark(breech, 10);
    }
    if (launch.phase === 'rail') {
      launch.speed += 420 * dt;
      launch.travel += launch.speed * dt;
      pp.copy(breech).addScaledVector(direction, Math.min(len, launch.travel));
      if (launch.travel >= len) {
        launch.phase = 'flight';
        pv.copy(direction).multiplyScalar(launch.speed);
        app.sys.dust?.spark(exit, 4);
      }
    } else if (launch.phase === 'flight') {
      const a = [0, 0, 0];
      w.field.accel(pp.x, pp.y, pp.z, a, 8);
      pv.addScaledVector(dif.set(...a), dt);
      pp.addScaledVector(pv, dt);
      if (pp.distanceTo(exit) > 1200) {
        launch.phase = 'idle';
        launch.next = sim.time + 40 + R() * 70;
        projectile.visible = false;
      }
    }
    launch.rv += (-4.6 * launch.recoil - 1.9 * launch.rv) * dt;
    launch.recoil += launch.rv * dt;
  };
  launch.frame = () => {
    projectile.position.copy(pp);
    projectile.quaternion.setFromUnitVectors(V(1, 0, 0), direction);
    if (sled) sled.position.copy(rest).addScaledVector(direction, launch.recoil);
    if (charge) {
      charge.power = .84 * smooth(1 - (launch.next - sim.time) / 6) * (launch.phase === 'idle');
      charge.dirty = true;
    }
  };
  sim.add('launcher', launch);
}
