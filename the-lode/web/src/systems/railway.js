import * as T from 'three';
import { TAG, HELD, clamp, rng } from '../physics/world.js';
import { Net } from '../physics/rigid.js';
import { templateBatch } from './crew.js';
import { Route, pose } from './tracks.js';
import { V, bl, UP, segments, lineInstance, geometry, instances } from './view.js';
const tmp = V(),
  a = V(),
  b = V(),
  c = V(),
  mx = new T.Matrix4(),
  dummy = new T.Object3D(),
  rand = rng(6262);
export function railway(app) {
  const sim = app.sim,
    w = sim.world,
    layout = app.layout.rail || {},
    rig = sim.rigid,
    flow = app.sys.ore;
  const W = bl(131, -59.5, -1),
    E = bl(207, -79.5, -8),
    dir = E.clone().sub(W);
  dir.y = 0;
  dir.normalize();
  const side = V(-dir.z, 0, dir.x),
    N = 24,
    net = new Net();
  net.ground = false;
  net.drag = 1.6;
  net.iterations = 4;
  const decks = [],
    cables = [],
    plumb = [],
    beds = [];
  const anchors = [];
  for (let i = 0; i <= N; i++) {
    const t = i / N,
      mid = W.clone().lerp(E, t);
    for (let k = 0; k < 4; k++) {
      const roof = k >= 2,
        z = (k % 2 ? 1 : -1) * (roof ? 6 : 5.5),
        p = mid.clone().addScaledVector(side, z);
      p.y += roof ? 5 + 31 * (2 * t - 1) ** 2 : 0;
      const pinned = i === 0 || i === N;
      net.node(p, roof ? 28 : 18, pinned ? o => o.copy(p) : null);
      anchors.push(p.clone());
      if (i) net.edge((i - 1) * 4 + k, i * 4 + k, null, roof ? 1.e-9 : 1.e-8, roof);
    }
    const j = i * 4;
    net.edge(j, j + 1, null, 1e-8);
    net.edge(j, j + 2, null, 2.e-7, true);
    net.edge(j + 1, j + 3, null, 2.e-7, true);
    plumb.push([j, j + 2], [j + 1, j + 3]);
    if (i) {
      net.edge(j - 4, j + 1, null, 1e-7);
      net.edge(j - 3, j, null, 1e-7);
      cables.push([j - 2, j + 2], [j - 1, j + 3]);
    }
  }
  rig.nets.push(net);
  const deckView = templateBatch(app, 'port', 'bridge_seg', N);
  for (let i = 0; i < N; i++) decks.push(new T.Object3D());
  const lines = segments(app, cables.length, .28, 0x51463c),
    hangers = segments(app, plumb.length, .115, 0x76695c);
  const rest = new Float32Array((N + 1) * 2);
  const bridge = {
    net,
    live: 0,
    deflection: 0,
    peak: 0,
    loads: 0,
    vehicles: [],
    restReady: false,
    pre() {
      for (let i = 0; i < net.nodes.length; i++) {
        const n = net.nodes[i],
          origin = anchors[i];
        n.load = 0;
        if (n.pin) continue;
        if (i % 4 < 2) {
          n.f.copy(origin).sub(n.p).multiplyScalar(42);
          n.f.y += 2.65;
        } else n.f.copy(origin).sub(n.p).multiplyScalar(3);
      }
      this.live = 0;
      for (const car of this.vehicles) {
        const p = car.pose.p,
          dx = p.x - W.x,
          dz = p.z - W.z,
          along = dx * dir.x + dz * dir.z,
          cross = dx * side.x + dz * side.z;
        if (along < 1 || along > 77.6 || Math.abs(cross) > 5 || Math.abs(p.y - (W.y + (E.y - W.y) * along / 78.6)) > 3) continue;
        const index = along / 78.59 * N,
          j = Math.min(N - 1, index | 0),
          u = index - j,
          mass = 34 + 2.2 * car.cargo.length,
          weight = mass * 2.6,
          ratio = clamp(.5 + cross / 11, .1, .9);
        this.live += weight;
        for (let k = 0; k <= 1; k++) {
          net.nodes[4 * j + k].load += weight * (1 - u) * (k ? ratio : 1 - ratio);
          net.nodes[4 * (j + 1) + k].load += weight * u * (k ? ratio : 1 - ratio);
        }
      }
    },
    post() {
      let max = 0;
      for (let i = 0; i <= N; i++) for (let k = 0; k < 2; k++) {
        const id = i * 4 + k,
          n = net.nodes[id];
        const dy = anchors[id].y - n.p.y;
        if (!this.restReady || !this.live && sim.time < 18) rest[i * 2 + k] = dy;
        max = Math.max(max, dy - rest[i * 2 + k]);
      }
      this.restReady = true;
      this.deflection = max;
      this.peak = Math.max(this.peak, max);
    },
    frame() {
      for (let i = 0; i < N; i++) {
        const n = net.nodes;
        const o = decks[i];
        a.copy(n[i * 4].p).lerp(n[i * 4 + 1].p, .5);
        b.copy(n[i * 4 + 4].p).lerp(n[i * 4 + 5].p, .5);
        c.subVectors(n[i * 4 + 1].p, n[i * 4].p).normalize();
        o.position.copy(a).lerp(b, .5);
        a.subVectors(b, a).normalize();
        b.crossVectors(c, a).normalize();
        o.quaternion.setFromRotationMatrix(mx.makeBasis(a, b, c));
        deckView.set(i, o);
      }
      deckView.finish();
      for (const [arr, mesh] of [[cables, lines], [plumb, hangers]]) {
        for (let i = 0; i < arr.length; i++) {
          const [j, k] = arr[i];
          lineInstance(mesh, i, net.nodes[j].p, net.nodes[k].p);
        }
        mesh.count = arr.length;
        mesh.instanceMatrix.needsUpdate = true;
      }
    }
  };
  sim.add('bridge', bridge);
  const fallback = [[114, 8, -8], [114, 8, -35], [128, 0, -25], [131, -1, 59.5], [207, -8, 79.5], [233, 92, 83], [241, 101, 88], [254, 74, 92], [239, 26, 99], [207, -8, 85], [131, -1, 65], [110, 4, 40], [114, 8, -8]];
  const route = new Route(layout.paths?.rail || fallback, true),
    mark = layout.railMarks || {
      signal: 100,
      release: 330,
      crest: 345,
      bridgeOutStart: 134,
      bridgeOutEnd: 213,
      bridgeInStart: 488,
      bridgeInEnd: 567
    };
  const release = Number(mark.release) || 330;
  const berth = app.mark('rail', 'freighter_berth', [228, 150, 92]),
    fr = {
      cargo: [],
      received: 0,
      departures: 0,
      arrivals: 1,
      firstReceived: null,
      state: 'docked',
      lastCargo: 0,
      stage: 0,
      doors: 1,
      serving: true,
      ship: null,
      old: [],
      pool: [],
      peak: 0
    };
  const hatchLocal=app.mark('fleet','fr_hatch',[0,0,0]), hatchWorld=berth.clone(), hatchPrevious=berth.clone(),
    hatchVelocity=V(), hatchUp=V(0,1,0), hatchInv=new T.Quaternion(), hullVelocity=V(),
    dockTarget=V(), impulse=V(), angular=V(), rotation=V(), angularTarget=V(),
    relative=V(), relVelocity=V(), lateral=V(), correction=V(),
    approachVector=V(1,.11,-.25), departureVector=V(1,.19,.36);
  fr.hatch=hatchWorld;
  fr.velocity=hullVelocity;
  fr.offset=0;
  fr.attitudePulses=0;
  // Reuse departed ships, including their registered lamps and engine bells.
  const driveGeo = new T.ConeGeometry(1, 1, 14, 1, true).translate(0, .5, 0).rotateZ(Math.PI / 2);
  const driveMat = new T.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: T.AdditiveBlending,
    side: T.DoubleSide,
    vertexShader: 'varying float t;void main(){t=uv.y;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: 'varying float t;void main(){gl_FragColor=vec4(vec3(.10,.42,.46),.18*(1.-t)*(1.-t));}'
  });
  function vessel() {
    let o = fr.pool.pop();
    if (o) {
      o.visible = true;
      app.scene.add(o);
    } else {
      o = app.clone('fleet', 'freighter');
      o.userData.plumes = [];
      o.userData.maneuverJets = [];
      for (let k = 0; k < 4; k++) {
        const jet = new T.Mesh(driveGeo, driveMat);
        jet.position.copy(app.mark('fleet', 'fr_engine_' + k, [-75, 6, k % 2 ? 9 : -9]));
        jet.renderOrder = 3;
        o.add(jet);
        o.userData.plumes.push(jet);
      }
      // These four paired nozzles are the reaction units modelled in the side shell.
      for(const [px,py,pz,side] of [[-53,9,16,1],[-45,12,-16.7,-1],
          [52,10.8,15.1,1],[56,13.2,-13.35,-1]]) {
        const group=new T.Group();
        group.position.set(px,py,pz);
        group.rotation.y=side*Math.PI*.5;
        for(const dx of [-1.3,1.35]) {
          const jet=new T.Mesh(driveGeo,driveMat);
          jet.position.z=side*dx;
          jet.renderOrder=3;
          group.add(jet);
        }
        o.add(group);o.userData.maneuverJets.push({group,px,side,level:0});
      }
    }
    o.position.copy(berth);
    o.rotation.set(0,-.23,0,'YXZ');
    return o;
  }
  fr.ship = vessel();
  function thrust(ship, power) {
    for (const jet of ship.userData.plumes) {
      jet.visible = power > .02;
      jet.scale.set(2 + 25 * power, 2.05, 2.05);
    }
  }
  function maneuver(ship, force, turn, dt) {
    for(const unit of ship.userData.maneuverJets) {
      // A lateral push or a yaw couple opens a fore/aft pair and the opposite unit.
      const demand=clamp(-unit.side*force*.72+unit.side*Math.sign(unit.px)*turn*7.2,0,.88);
      unit.level+=(demand-unit.level)*Math.min(1,dt*2.7);
      unit.group.visible=unit.level>.035;
      for(const jet of unit.group.children)jet.scale.set(.4+9.8*unit.level,.51+.24*unit.level,.51+.24*unit.level);
    }
  }
  function stationKeep(dt) {
    const t=sim.time, load=fr.cargo.length/250, tide=app.U.uTide.value;
    const moment=1+.55*load;
    // An off-axis hot plume and the tide keep drawing the hull across its moor.
    // A slow flight director corrects the error, while ore transfer kicks the ship.
    dockTarget.copy(berth);
    dockTarget.x+=2.6*Math.sin(t*.147+.75)+.77*Math.sin(t*.292);
    dockTarget.z+=2.4*Math.sin(t*.108-.6)+1.05*Math.sin(t*.227)+tide*.85;
    dockTarget.y+=1.08*Math.sin(t*.116+.28)-load*1.75+.52*tide;
    impulse.subVectors(dockTarget,fr.ship.position).multiplyScalar(.22/moment)
      .addScaledVector(hullVelocity,-.68).clampLength(0,1.25);
    hullVelocity.addScaledVector(impulse,dt);
    fr.ship.position.addScaledVector(hullVelocity,dt);
    angularTarget.set(-impulse.z*.077+Math.sin(t*.142)*.023,
      .04*Math.sin(t*.119)+.012*Math.sin(t*.251)-impulse.z*.025,
      impulse.x*.049+Math.sin(t*.174+.45)*.019);
    angular.addScaledVector(correction.subVectors(angularTarget,rotation).multiplyScalar(.66/moment)
      .addScaledVector(angular,-1.02),dt);
    rotation.addScaledVector(angular,dt);
    fr.ship.rotation.set(rotation.x,-.23+rotation.y,rotation.z,'YXZ');
    fr.offset=fr.ship.position.distanceTo(berth);
    // The command is resolved into ship-local lateral force before firing the paired jets.
    maneuver(fr.ship,impulse.x*Math.sin(-.23)+impulse.z*Math.cos(-.23),angular.y,dt);
  }
  function updateHatch(dt) {
    hatchPrevious.copy(hatchWorld);
    hatchInv.copy(fr.ship.quaternion).invert();
    hatchWorld.copy(hatchLocal).applyQuaternion(fr.ship.quaternion).add(fr.ship.position);
    hatchUp.set(0,1,0).applyQuaternion(fr.ship.quaternion);
    hatchVelocity.subVectors(hatchWorld,hatchPrevious).multiplyScalar(1/dt);
  }
  function doors(obj, val) {
    const l = obj.getObjectByName('fr_door_l'),
      r = obj.getObjectByName('fr_door_r');
    if (l) l.rotation.x = val * 1.26;
    if (r) r.rotation.x = -val * 1.26;
  }
  function cargoPos(arr, obj, ship) {
    for (let k = 0; k < arr.length; k++) {
      const i = arr[k];
      if (ship) tmp.set((k % 17 - 8) * 1.28, 2.65 + (k / 102 | 0) * 1.27, ((k / 17 | 0) % 6 - 2.5) * 1.15);else tmp.set((k % 6 - 2.5) * 1.05, 2.09 + (k / 18 | 0) * .85, ((k / 6 | 0) % 3 - 1) * .83);
      tmp.applyQuaternion(obj.quaternion).add(obj.position);
      w.x[i] = tmp.x;
      w.y[i] = tmp.y;
      w.z[i] = tmp.z;
    }
  }
  fr.pre = dt => {
    fr.stage += dt;
    if(fr.state==='docked'||fr.state==='closing')stationKeep(dt);
    if (fr.state === 'docked') {
      fr.doors = Math.min(1, fr.doors + dt / 3.5);
      if (fr.cargo.length >= 250 || fr.cargo.length >= 80 && sim.time - fr.lastCargo > 150) {
        fr.state = 'closing';
        fr.stage = 0;
        fr.serving = false;
      }
    } else if (fr.state === 'closing') {
      fr.doors = Math.max(0, 1 - fr.stage / 4.5);
      if (fr.stage >= 4.5) {
        fr.old.push({
          obj: fr.ship,
          cargo: fr.cargo,
          start:fr.ship.position.clone(),velocity:hullVelocity.clone(),
          attitude:rotation.clone(),
          t: 0
        });
        fr.departures++;
        fr.cargo = [];
        fr.ship = vessel();
        fr.ship.position.copy(berth).addScaledVector(approachVector,620);
        fr.doors=0;
        angular.set(0,0,0);rotation.set(0,0,0);hullVelocity.set(0,0,0);
        fr.state = 'arriving';
        fr.stage = 0;
      }
    } else {
      const f = Math.min(1, fr.stage / 43),
        p = (1 - f) ** 2;
      fr.ship.position.copy(berth).addScaledVector(approachVector,620*p);
      fr.ship.rotation.z=.065*Math.sin(f*Math.PI);
      maneuver(fr.ship,0,0,dt);
      if (f >= 1) {
        fr.state = 'docked';
        fr.stage = 0;
        fr.arrivals++;
        fr.serving = true;
        fr.lastCargo = sim.time;
      }
    }
    for (let j = fr.old.length - 1; j >= 0; j--) {
      const v = fr.old[j];
      v.t += dt;
      const s = .125 * v.t * v.t;
      const settle=1-Math.exp(-v.t*.24);
      v.obj.position.copy(v.start).addScaledVector(v.velocity,settle/.24).addScaledVector(departureVector,s);
      v.obj.rotation.set(v.attitude.x*(1-settle),-.23+v.attitude.y*(1-settle)-.102*settle,
        v.attitude.z*(1-settle)+.13*settle,'YXZ');
      maneuver(v.obj,0,0,dt);
      if (v.t > 90) {
        for (const i of v.cargo) w.kill(i);
        v.obj.visible = false;
        app.scene.remove(v.obj);
        fr.pool.push(v.obj);
        fr.old.splice(j, 1);
      }
    }
    updateHatch(dt);
  };
  w.forces[TAG.THROWN] = (i, a) => {
    a[1] -= 2.6;
    if(!fr.serving)return;
    relative.set(w.x[i],w.y[i],w.z[i]).sub(hatchWorld);
    const height=relative.dot(hatchUp);
    lateral.copy(relative).addScaledVector(hatchUp,-height);
    if(lateral.lengthSq()>=42*42 || height<=-42)return;
    relVelocity.set(w.vx[i],w.vy[i],w.vz[i]).sub(hatchVelocity);
    const rising=relVelocity.dot(hatchUp);
    correction.copy(lateral).multiplyScalar(-.66).addScaledVector(relVelocity,-1.35)
      .addScaledVector(hatchUp,1.35*rising+2.6+(7-rising)*1.3+(height>-3?(2.2-rising)*1.4:0));
    a[0]+=correction.x;a[1]+=correction.y;a[2]+=correction.z;
  };
  fr.post = () => {
    for (let j = w.count - 1; j >= 0; j--) {
      const i = w.order[j];
      if (w.tag[i] !== TAG.THROWN) continue;
      relative.set(w.x[i],w.y[i],w.z[i]).sub(hatchWorld).applyQuaternion(hatchInv);
      if (fr.serving && relative.y>1 && Math.abs(relative.z)<7.05 &&
          Math.hypot(relative.x,relative.z)<8 && fr.cargo.length < 250) {
        const kick=clamp((w.vy[i]-hullVelocity.y)*.0018,-.014,.014);
        hullVelocity.y+=kick;
        hullVelocity.x+=clamp((w.vx[i]-hullVelocity.x)*.0009,-.008,.008);
        hullVelocity.z+=clamp((w.vz[i]-hullVelocity.z)*.0009,-.008,.008);
        angular.x-=relative.z*kick*.0025;angular.z+=relative.x*kick*.0019;
        fr.attitudePulses++;
        w.hold(i, TAG.SHIP, 0);
        fr.cargo.push(i);
        fr.received++;
        if(fr.firstReceived===null)fr.firstReceived=sim.time;
        fr.peak = Math.max(fr.peak, fr.cargo.length);
        fr.lastCargo = sim.time;
      } else if (w.stageAge[i] > 35) {
        w.relabel(i, TAG.SPILL);
      }
    }
  };
  fr.frame = () => {
    thrust(fr.ship, fr.state === 'arriving' ? .12 + .34 * (1 - Math.min(1, fr.stage / 43)) : 0);
    doors(fr.ship, fr.doors);
    cargoPos(fr.cargo, fr.ship, true);
    for (const old of fr.old) {
      doors(old.obj, 0);
      thrust(old.obj, Math.min(1, old.t / 10));
      cargoPos(old.cargo, old.obj, true);
    }
  };
  sim.add('freighter', fr);
  const trains = {
    trains: [],
    route,
    loaded: 0,
    released: 0,
    firstRelease: null,
    laps: 0,
    departSignal: 0
  };
  function makeTrain(index, s) {
    const train = {
      s,
      v: 0,
      loadIdx: 0,
      nextLoad: index === 0 ? 0 : route.len,
      stop: 0,
      state: index === 0 ? 'loading' : 'run',
      cars: []
    };
    for (let k = 0; k < 3; k++) {
      const car = {
        box: w.addBox({
          p: [0, 0, 0],
          h: [3.375, .14, 1.39],
          q: [0, 0, 0, 1],
          tag: 'wagon_floor',
          mu: .62
        }, true),
        id: index * 3 + k,
        offset: 11.6 * k,
        pose: pose(),
        cargo: [],
        obj: app.clone('fleet', 'wagon')
      };
      train.cars.push(car);
      bridge.vehicles.push(car);
      route.at(s - car.offset, car.pose);
      car.obj.position.copy(car.pose.p);
      car.obj.quaternion.copy(car.pose.q);
    }
    return train;
  }
  // The first loaded consist has cleared the loading train by fifty metres.
  // It still crosses the bridge and works up the entire climb in the opening shift.
  trains.trains = [makeTrain(0, 0), makeTrain(1, Math.max(49,release-280))];
  for (const car of trains.trains[1].cars) for (let k = 0; k < 14; k++) {
    const i = w.spawn(TAG.TRAIN, 0, 0, 0, {
      state: HELD,
      r: .51,
      owner: car.id
    });
    car.cargo.push(i);
  }
  trains.pre = dt => {
    flow.binRequest = false;
    flow.train = null;
    for (let j = 0; j < 2; j++) {
      const t = trains.trains[j],
        other = trains.trains[1 - j],
        old = t.s,
        loc = (t.s % route.len + route.len) % route.len;
      const cargo = t.cars.reduce((n, c) => n + c.cargo.length, 0);
      const car = t.cars[t.loadIdx] || t.cars[0];
      const loadAt = t.nextLoad + car.offset;
      if (t.state === 'loading') {
        t.stop += dt;
        flow.binRequest = true;
        flow.train = car;
        t.v = 0;
        if (car.cargo.length >= 26 || t.stop >= 15) {
          if (++t.loadIdx >= 3) {
            t.loadIdx = 0;
            t.nextLoad += route.len;
            trains.laps++;
          }
          t.state = 'run';
          t.stop = 0;
        }
      } else {
        const gap = (other.s - old + route.len * 100) % route.len;
        let vmax = loc >= mark.signal && loc < release ? 15.5 : loc >= release && loc < mark.bridgeInStart ? 9.5 : 7.2;
        const left = loadAt - t.s;
        if (left >= -.04) vmax = Math.min(vmax, Math.sqrt(2 * 2.4 * Math.max(0, left)));
        const sig = (mark.signal - loc + route.len) % route.len;
        if (cargo && (!fr.serving || fr.cargo.length + w.counts[TAG.THROWN] >= 250) && sig < 30) vmax = Math.min(vmax, Math.sqrt(2 * 2.4 * Math.max(0, sig - .3)));
        if (gap < 48) vmax = Math.min(vmax, Math.max(0, gap - 32) * .6);
        t.v = clamp(vmax, t.v - 2.4 * dt, t.v + 2.6 / (1 + cargo / 60) * dt);
        t.s += Math.max(0, t.v) * dt;
        if (left >= -.06 && t.s >= loadAt - .055) {
          t.s = loadAt;
          t.state = 'loading';
          t.stop = 0;
          t.v = 0;
        }
      }
      for (const car of t.cars) {
        const s = t.s - car.offset,
          prev = old - car.offset;
        route.at(s, car.pose);
        const near = car.pose.p,
          dx = near.x - W.x,
          dz = near.z - W.z,
          u = (dx * dir.x + dz * dir.z) / 78.5888,
          cross = dx * side.x + dz * side.z;
        if (u > 0 && u < 1 && Math.abs(cross) < 5 && Math.abs(near.y - (W.y + (E.y - W.y) * u)) < 3) {
          const f = u * N,
            idx = Math.min(N - 1, Math.floor(f)) * 4,
            k = f - Math.floor(f),
            n = net.nodes;
          const l = (n[idx].p.y - anchors[idx].y) * (1 - k) + (n[idx + 4].p.y - anchors[idx + 4].y) * k,
            r = (n[idx + 1].p.y - anchors[idx + 1].y) * (1 - k) + (n[idx + 5].p.y - anchors[idx + 5].y) * k;
          near.y += l + (r - l) * clamp(.5 + cross / 11, 0, 1);
          car.pose.q.premultiply(dummy.quaternion.setFromAxisAngle(dir, -Math.atan2(r - l, 11)));
        }
        car.obj.position.copy(near);
        car.obj.quaternion.copy(car.pose.q);
        tmp.set(0, 1.51, 0).applyQuaternion(car.pose.q).add(near).toArray(car.box.p);
        car.pose.q.toArray(car.box.q);
        car.box.cache();
        tmp.copy(car.pose.t).multiplyScalar(t.v).toArray(car.box.v);
        if (car.cargo.length && Math.floor((s - release) / route.len) > Math.floor((prev - release) / route.len)) {
          const v = Math.max(11.8, t.v),
            space = fr.serving ? Math.max(0, 250 - fr.cargo.length - w.counts[TAG.THROWN]) : 0,
            releaseN = Math.min(car.cargo.length, space);
          for (let k = 0; k < releaseN; k++) {
            const i = car.cargo[k];
            const up = k * .055;
            w.release(i, TAG.THROWN, near.x + (k % 5 - 2) * .82, near.y + 2 + up, near.z + ((k / 5 | 0) % 4 - 1.5) * .9, car.pose.t.x * v + (rand() - .5) * .32, car.pose.t.y * v, car.pose.t.z * v + (rand() - .5) * .3);
            trains.released++;
            if(trains.firstRelease===null)trains.firstRelease=sim.time;
          }
          car.cargo.splice(0, releaseN);
        }
      }
    }
    trains.loaded = flow.loaded;
  };
  trains.frame = () => {
    for (const train of trains.trains) for (const c of train.cars) cargoPos(c.cargo, c.obj, false);
  };
  sim.add('rail', trains);
}
