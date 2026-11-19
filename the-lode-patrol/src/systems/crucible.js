import * as T from 'three';
import { rng, clamp } from '../physics/world.js';
import { V, instances, setInstance, smooth } from './view.js';
export function crucible(app) {
  const sim = app.sim,
    w = sim.world,
    R = rng(73221),
    home = app.mark('fill', 'crucible', [64, 31, 158]),
    tap = app.mark('fill', 'furnace_tap', [49.5, 10.2, 151.2]),
    base = app.mark('fill', 'crucible_base', [64, -2.4, 158]),
    L = w.field.lode,
    center = home.clone(),
    vel = V(),
    axis = V(),
    acc = [0, 0, 0];
  const modes = new Float32Array(10),
    deriv = new Float32Array(10);
  const uniforms = {
    uModes: {
      value: modes
    },
    uAxis: {
      value: V()
    },
    uPull: {
      value: .05
    },
    uTime: app.U.uTime,
    uTide: app.U.uTide,
    tNoise: app.U.tNoiseA,
    tFlow: app.U.tNoiseB
  };
  const mat = new T.ShaderMaterial({
    uniforms,
    vertexShader: `uniform float uModes[10];uniform vec3 uAxis;uniform float uPull;varying vec3 n,p,vdir;void main(){vec3 d=normalize(position);float x=d.x,y=d.y,z=d.z;float f=uModes[0]*(x*x-y*y)+uModes[1]*(3.*z*z-1.)*.5+uModes[2]*2.*x*y+uModes[3]*2.*y*z+uModes[4]*2.*z*x+uModes[5]*x*(5.*z*z-1.)+uModes[6]*z*(5.*z*z-3.)*.5+uModes[7]*y*(3.*x*x-y*y)+uModes[8]*(35.*z*z*z*z-30.*z*z+3.)*.125+uModes[9]*x*y*(x*x-y*y)*4.;vec3 q=d*(1.+clamp(f,-.22,.22))+uAxis*dot(d,uAxis)*uPull;p=q;n=d;vec4 wp=modelMatrix*vec4(q,1.);vdir=cameraPosition-wp.xyz;gl_Position=projectionMatrix*viewMatrix*wp;}`,
    fragmentShader: `varying vec3 n,p,vdir;uniform sampler2D tNoise,tFlow;uniform float uTime,uTide;void main(){vec3 N=normalize(n),W=pow(abs(N),vec3(8.));W/=max(.001,W.x+W.y+W.z);vec3 q=p*.29+vec3(.14,uTime*.0018,.42);vec3 cells=vec3(texture2D(tNoise,q.zy).g,texture2D(tNoise,q.xz).g,texture2D(tNoise,q.xy).g);float edges=dot(W,vec3(1.)-smoothstep(vec3(.012),vec3(.17),cells));float flow=texture2D(tFlow,q.xy*.8+texture2D(tNoise,q.xz*.4).rg*.23).r;float fissure=edges*(.37+.73*flow);float edge=pow(max(1.-abs(dot(N,normalize(vdir))),0.),3.5);float light=.28+.7*max(dot(N,normalize(vec3(-.83,.5,.31))),0.);vec3 c=vec3(.061,.027,.019)*light*(.65+.7*flow);c+=vec3(2.1,.31,.045)*fissure+vec3(.65,.077,.018)*edge*(.7+.46*flow);gl_FragColor=vec4(c*(1.-.35*uTide),1.);}`
  });
  const sphere = new T.Mesh(new T.IcosahedronGeometry(1, 6), mat);
  app.scene.add(sphere);
  const beads = [],
    dripMat = new T.MeshStandardMaterial({
      color: 0x722c17,
      emissive: 0xa5320d,
      emissiveIntensity: .85,
      roughness: .5
    }),
    beadMesh = instances(app, new T.IcosahedronGeometry(1, 1), dripMat, 180);
  const light = app.lights.add({
      p: home.toArray(),
      c: [1, .24, .05],
      r: 95,
      i: 1.1,
      k: 'aura'
    }),
    s = {
      radius: 10.55,
      volume: 10.55 ** 3,
      drains: 0,
      absorbed: 0,
      castDrops: 0,
      draining: 0,
      center,
      modes
    };
  let clock = 0,
    drainClock = 0,
    front = -1;
  const tmp = V(),
    dropDir = V();
  const omega = [1.5, 1.5, 1.5, 1.5, 1.5, 2.9, 2.9, 2.9, 4.5, 4.5];
  function perturb(dir, impulse) {
    const {
      x,
      y,
      z
    } = dir;
    const basis = [x * x - y * y, (3 * z * z - 1) / 2, 2 * x * y, 2 * y * z, 2 * z * x, x * (5 * z * z - 1), z * (5 * z * z - 3) / 2, y * (3 * x * x - y * y), (35 * z ** 4 - 30 * z * z + 3) / 8, 4 * x * y * (x * x - y * y)];
    for (let j = 0; j < 10; j++) deriv[j] += basis[j] * impulse;
  }
  for (let i = 0; i < 10; i++) modes[i] = (R() - .5) * .055;
  s.pre = dt => {
    w.field.accel(center.x, center.y, center.z, acc, 16);
    tmp.copy(home).sub(center).multiplyScalar(.48);
    tmp.x += acc[0];
    tmp.y += acc[1];
    tmp.z += acc[2];
    vel.addScaledVector(tmp, dt).multiplyScalar(1 / (1 + dt * .46));
    center.addScaledVector(vel, dt);
    axis.set(L.x - center.x, L.y - center.y, L.z - center.z).normalize();
    const d = Math.hypot(center.x - L.x, center.z - L.z);
    if (w.field.wave.r >= d && front !== app.sys.tides.count) {
      front = app.sys.tides.count;
      perturb(axis, .13 * app.sys.tides.power);
      vel.addScaledVector(axis, 1.15 * app.sys.tides.power);
    }
    for (let j = 0; j < 10; j++) {
      const om = omega[j] * (9.3 / s.radius) ** 1.5;
      deriv[j] += (-om * om * modes[j] - .28 * deriv[j] + .005 * Math.sin(sim.time * (.24 + .025 * j) + j)) * dt;
      modes[j] = clamp(modes[j] + deriv[j] * dt, -.22, .22);
    }
    clock += dt;
    if (clock > .55) {
      clock -= .55;
      const p = tap.clone().add(V((R() - .5) * .4, .12, (R() - .5) * .45)),
        v = V(2.4 + R(), 7.2 + R() * 2, 2.1 + R());
      beads.push({
        p,
        v,
        r: .45 + .5 * R(),
        out: false,
        age: 0
      });
    }
    if (!s.draining && s.radius >= 10.6) {
      s.draining = 9;
      s.drains++;
    }
    if (s.draining > 0) {
      s.draining = Math.max(0, s.draining - dt);
      s.volume -= (10.6 ** 3 - 8.5 ** 3) / 9 * dt;
      drainClock += dt;
      if (drainClock > .105) {
        drainClock -= .105;
        beads.push({
          p: center.clone().add(V((R() - .5) * .65, -s.radius * .95, (R() - .5) * .65)),
          v: V(0, -4 - R() * 2, 0),
          r: .36 + R() * .38,
          out: true,
          age: 0
        });
      }
    }
    for (let j = beads.length - 1; j >= 0; j--) {
      const b = beads[j];
      b.age += dt;
      if (b.out) {
        b.v.y -= 2.6 * dt;
        b.v.x += (base.x - b.p.x) * .5 * dt;
        b.v.z += (base.z - b.p.z) * .5 * dt;
      } else {
        dropDir.subVectors(center, b.p);
        const d = dropDir.length();
        b.v.addScaledVector(dropDir, (2.8 + 22 / Math.max(d, 1)) * dt / Math.max(d, .1));
        b.v.y -= .46 * dt;
        if (d < s.radius) {
          s.volume += b.r ** 3;
          s.absorbed++;
          perturb(dropDir.normalize(), .033 + b.r * .014);
          beads.splice(j, 1);
          continue;
        }
      }
      b.p.addScaledVector(b.v, dt);
      if (b.out && b.p.y < base.y + 1) {
        s.castDrops++;
        app.sys.dust?.spark(b.p, 3);
        beads.splice(j, 1);
      } else if (b.age > 15) beads.splice(j, 1);
    }
    s.radius = Math.cbrt(Math.max(8.4 ** 3, s.volume));
  };
  s.frame = () => {
    sphere.position.copy(center);
    sphere.scale.setScalar(s.radius);
    uniforms.uAxis.value.copy(axis);
    uniforms.uPull.value = .05 + .2 * app.U.uTide.value;
    beads.forEach((b, i) => setInstance(beadMesh, i, b.p.x, b.p.y, b.p.z, b.r, 0, 0, 0, 1, b.out ? 1.65 : 1, 1));
    beadMesh.count = Math.min(180, beads.length);
    beadMesh.instanceMatrix.needsUpdate = true;
    if (light) {
      light.p.copy(center);
      light.power = 1.05 + .18 * Math.sin(sim.time * .31);
      light.dirty = true;
    }
  };
  sim.add('crucible', s);
}
