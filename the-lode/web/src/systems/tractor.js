import * as T from 'three';
import { TAG, clamp, rng } from '../physics/world.js';
import { V, bl, segments, updateLines } from './view.js';
import { rope } from '../physics/rigid.js';
export function tractor(app) {
  const sim = app.sim,
    w = sim.world,
    R = rng(9422),
    head = app.mark('pit', 'tractor_head', [-62, 46, -62]),
    foot = app.mark('pit', 'tractor_foot', [-62, -74, -62]),
    maw = app.mark('pit', 'maw', [27, 66, -13]);
  const t = {
      lifted: 0,
      conveyed: 0,
      stolen: 0,
      maw: 0,
      power: 1
    },
    col = w.counts;
  let clock = 0;
  const rollers = ['maw_roller_a', 'maw_roller_b'].map(n => app.find('pit', n));
  function make(y) {
    const k = clamp((y - foot.y) / 120, 0, 1),
      r = 5 + 6.5 * k,
      an = R() * Math.PI * 2,
      v = 7;
    return w.spawn(TAG.CONE, foot.x + r * Math.cos(an), y, foot.z + r * Math.sin(an), {
      r: .6 + R() * .64,
      kind: R() < .32 ? 2 : 0,
      vx: -v * Math.sin(an),
      vz: v * Math.cos(an),
      vy: 4.6
    });
  }
  for (let j = 0; j < 93; j++) make(foot.y + 2 + R() * 116);
  w.forces[TAG.CONE] = (i, a) => {
    const k = clamp((w.y[i] - foot.y) / 120, 0, 1),
      dx = w.x[i] - foot.x,
      dz = w.z[i] - foot.z,
      r = Math.max(.1, Math.hypot(dx, dz)),
      target = 5 + 6.5 * k,
      px = dx / r,
      pz = dz / r,
      v = 7 * t.power,
      radial = w.vx[i] * px + w.vz[i] * pz,
      rad = (target - r) * 3.6 - radial * 2.8 - v * v / r;
    a[0] += (rad * px + (-pz * v - w.vx[i] + radial * px) * 2.4) * t.power;
    a[2] += (rad * pz + (px * v - w.vz[i] + radial * pz) * 2.4) * t.power;
    a[1] += (2.9 + (5.4 * t.power - w.vy[i]) * 1.3) * t.power;
  };
  const feed = [head.clone(), V(-49, 45.5, -55), V(18, 45.5, -18), V(26, 66.5, -13)];
  const tangents = feed.slice(1).map((point, j) => V().subVectors(point, feed[j]).normalize());
  const lengths = feed.slice(1).map((point, j) => point.distanceTo(feed[j]));
  const seg = new Uint8Array(w.cap);
  w.forces[TAG.CABLE] = (i, a) => {
    let j = seg[i],
      p = feed[j];
    const d = tangents[j],
      u = clamp((w.x[i] - p.x) * d.x + (w.y[i] - p.y) * d.y + (w.z[i] - p.z) * d.z, 0, lengths[j]);
    const ahead = Math.min(lengths[j], u + 3);
    a[0] += (p.x + d.x * ahead - w.x[i]) * 4 - w.vx[i] * 2.1;
    a[1] += (p.y + d.y * ahead - w.y[i]) * 4 - w.vy[i] * 2.1 + 2.6;
    a[2] += (p.z + d.z * ahead - w.z[i]) * 4 - w.vz[i] * 2.1;
    if (u > lengths[j] - 1.7 && j < 2) seg[i]++;
  };
  t.pre = dt => {
    t.power = 1 - .75 * app.U.uTide.value;
    clock += 4.6 * dt * t.power;
    while (clock >= 1) {
      if (col[TAG.CONE] < 330) {
        make(foot.y + 2.2);
        t.lifted++;
      }
      clock--;
    }
  };
  t.post = dt => {
    for (let j = w.count - 1; j >= 0; j--) {
      const i = w.order[j];
      if (w.tag[i] === TAG.CONE) {
        if (w.y[i] > head.y - 1) {
          w.relabel(i, TAG.CABLE);
          seg[i] = 0;
          t.conveyed++;
        } else if (t.power < .76 && w.y[i] > -70 && R() < dt * .20 && Math.hypot(w.x[i] - foot.x, w.z[i] - foot.z) > 5) {
          app.sys.halo.capture(i);
          t.stolen++;
        } else if (w.stageAge[i] > 65) w.relabel(i, TAG.SPILL);
      } else if (w.tag[i] === TAG.CABLE) {
        if (seg[i] === 2 && Math.hypot(w.x[i] - maw.x, w.y[i] - maw.y, w.z[i] - maw.z) < 5) {
          w.kill(i);
          t.maw++;
          app.sys.dust?.spark(maw, 3);
        } else if (w.stageAge[i] > 40) w.relabel(i, TAG.SPILL);
      }
    }
  };
  t.frame = () => {
    rollers.forEach((o, j) => {
      if (o) o.rotation.z = sim.time * (j ? -.9 : .92);
    });
  };
  sim.add('tractor', t);
}
export function moorings(app) {
  const sim = app.sim,
    w = sim.world,
    rig = sim.rigid,
    moored = {
      stones: [],
      maxTension: 0
    };
  const chainGeo = app.find('rocks', 'chain_link');
  const names = ['boulder_a', 'boulder_b', 'boulder_c'],
    anchors = [[-128, -162], [-120, 176], [14, 204]],
    radii = [24, 20, 16];
  const zaxis = V(0, 1, 0),
    spin = new T.Quaternion(),
    dummy = new T.Object3D(),
    diff = V();
  for (let j = 0; j < 3; j++) {
    const [x, y] = anchors[j],
      g = w.ground(x, -y),
      anchor = app.mark('rail', 'anchor_' + String.fromCharCode(97 + j), [x, g + 3, -y]);
    const rad = radii[j],
      name = names[j],
      obj = app.clone('rocks', name, false),
      proxies = app.layout.rocks?.bodies?.[name]?.spheres;
    const p = anchor.clone().add(V((j - 1) * 8, 65 + 2 * j, 9));
    const body = rig.body(p, 550 + j * 110, rad, {
      who: 40,
      mutual: false,
      boxes: false,
      ground: true,
      damping: .12,
      balls: proxies?.map(s => ({
        p: V(...s.p),
        r: s.r
      })) || [{
        p: V(),
        r: rad * .72
      }]
    });
    body.v.set(.45, .22, -.16);
    body.w.set(.006, .012 + .001 * j, .008);
    const at = app.layout.rocks?.markers?.[name + '_attachment']?.p || [0, -rad * .6, 0];
    const fixed = o => o.copy(anchor),
      net = rope(fixed, {
        body,
        offset: V(...at)
      }, [77, 86, 70][j], 30, 3e-7);
    net.iterations = 4;
    rig.nets.push(net);
    w.field.addZone({
      who: 32,
      minx: x - 126,
      maxx: x + 126,
      miny: g - 170,
      maxy: g + 180,
      minz: -y - 126,
      maxz: -y + 126,
      mode: 'add',
      test: (xx, yy, zz) => clamp((110 - Math.hypot(xx - x, zz + y)) / 25, 0, 1),
      fn: (xx, yy, zz, o) => {
        o[0] = 0;
        o[1] = 3.6 * Math.exp(-Math.max(-60, yy - g) / 70);
        o[2] = 0;
      }
    });
    const geom = app.geometry('rocks', 'chain_link');
    const links = app.instances(geom, new T.MeshStandardMaterial({
      color: 0x706052,
      metalness: .65,
      roughness: .59
    }), 40);
    moored.stones.push({
      body,
      obj,
      net,
      links,
      anchor
    });
  }
  moored.frame = () => {
    for (const s of moored.stones) {
      s.obj.position.copy(s.body.p);
      s.obj.quaternion.copy(s.body.q);
      let k = 0;
      const nodes = s.net.nodes;
      for (let i = 1; i < nodes.length; i++) {
        const a = nodes[i - 1].p,
          b = nodes[i].p;
        diff.subVectors(b, a);
        const len = diff.length();
        dummy.position.copy(a).lerp(b, .5);
        dummy.quaternion.setFromUnitVectors(zaxis, diff.normalize()).multiply(spin.setFromAxisAngle(zaxis, i % 2 * Math.PI / 2));
        dummy.scale.set(1.15, len / 2.05, 1.15);
        dummy.updateMatrix();
        s.links.setMatrixAt(k++, dummy.matrix);
      }
      s.links.count = k;
      s.links.instanceMatrix.needsUpdate = true;
    }
  };
  sim.add('moorings', moored);
}
