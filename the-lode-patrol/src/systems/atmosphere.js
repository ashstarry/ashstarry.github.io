import * as T from 'three';
import { rng, clamp } from '../physics/world.js';
import { V, bl, smooth } from './view.js';
const rand = rng(61027);
function volume(app, base, end, r0, r1, lo, hi, opacity, plume = false) {
  const mat = new T.ShaderMaterial({
    transparent: true,
    blending: T.AdditiveBlending,
    depthWrite: false,
    side: T.FrontSide,
    uniforms: {
      uTime: app.U.uTime,
      uTide: app.U.uTide,
      tNoise: app.U.tNoiseA,
      col0: {
        value: new T.Color(lo)
      },
      col1: {
        value: new T.Color(hi)
      },
      alpha: {
        value: opacity
      },
      pillar: {
        value: plume ? 1 : 0
      }
    },
    vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: `varying vec2 vUv;uniform sampler2D tNoise;uniform vec3 col0,col1;uniform float alpha,uTime,uTide,pillar;void main(){float yy=clamp(vUv.y,0.,1.);float f=texture2D(tNoise,vec2(vUv.x*4.,yy*2.4-uTime*.019)).r;float stripes=.7+.3*sin(vUv.x*44.+yy*7.+uTime*.07);float gain=mix(.5+.5*f,.25+.75*f*f,pillar)*stripes;float envelope=mix(1.-smoothstep(.6,1.,yy),smoothstep(0.,.06,yy)*(1.-smoothstep(.42,1.,yy)),pillar);gl_FragColor=vec4(mix(col0,col1,yy),alpha*(mix(1.-.72*uTide,1.+.9*uTide,pillar))*envelope*gain);}`
  });
  const mesh = new T.Mesh(new T.CylinderGeometry(r1, r0, 1, plume ? 52 : 16, 1, true), mat);
  mesh.frustumCulled = false;
  mesh.renderOrder = 3;
  app.scene.add(mesh);
  const dir = V(),
    Y = V(0, 1, 0);
  function point(a, b) {
    dir.subVectors(b, a);
    const l = dir.length();
    mesh.position.copy(a).lerp(b, .5);
    mesh.scale.set(1, l, 1);
    mesh.quaternion.setFromUnitVectors(Y, dir.multiplyScalar(1 / Math.max(.001, l)));
  }
  point(base, end);
  return {
    mesh,
    point
  };
}
export function atmosphere(app) {
  const sim = app.sim,
    w = sim.world,
    L = w.field.lode;
  const aura = volume(app, V(L.x, -71, L.z), V(L.x, 569, L.z), 52, 30, 0x75352f, 0x4b3d3c, .052, true);
  const search = [['habitat', 'spire_search', [96, 96, -146], 0x978b79], ['bwe', 'bwe_search', [-190, 46, -8], 0x918c7f], ['port', 'port_search', [253, 63, 32], 0x707b7b]].map(([part, n, f, c], j) => {
    const from = app.mark(part, n, f),
      to = from.clone().add(V(-26, -56, 26));
    const v = volume(app, from, to, .32, 7, c, c, .043);
    const col = new T.Color(c);
    const lamp = app.lights.add({
      p: to.toArray(),
      c: col.toArray(),
      i: .9,
      r: 13,
      k: 'aura'
    });
    return {
      from,
      to,
      v,
      lamp
    };
  });
  let focus = 0;
  sim.add('atmosphere', {
    beams: search.length,
    pre(dt) {
      focus += (app.U.uTide.value - focus) * (1 - Math.exp(-dt * 1.75));
    },
    frame() {
      const t = sim.time;
      search.forEach((s, j) => {
        const sector = j + 1;
        const th = t * (.082 + sector * .008) + sector * 1.91;
        const x = s.from.x + Math.sin(th) * (46 + 6 * sector) - 15,
          z = s.from.z + Math.cos(th * .73 + 2 * sector) * 57 + 13;
        s.to.set(x, Math.max(w.ground(x, z), -10) + .35, z).lerp(V(L.x, -62, L.z), Math.min(1, focus * 1.7));
        s.v.point(s.from, s.to);
        if (s.lamp) {
          s.lamp.p.copy(s.to);
          s.lamp.power = .75 - .56 * focus;
          s.lamp.dirty = true;
        }
      });
    }
  });
  const max = 1300,
    count = 520,
    p = new Float32Array(max * 3),
    color = new Float32Array(max * 3),
    sizes = new Float32Array(max),
    geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(p, 3).setUsage(T.DynamicDrawUsage));
  geo.setAttribute('color', new T.BufferAttribute(color, 3).setUsage(T.DynamicDrawUsage));
  geo.setAttribute('aSize', new T.BufferAttribute(sizes, 1).setUsage(T.DynamicDrawUsage));
  const mat = new T.ShaderMaterial({
    transparent: true,
    blending: T.AdditiveBlending,
    depthWrite: false,
    uniforms: {
      scale: {
        value: 550
      }
    },
    vertexShader: `attribute vec3 color;attribute float aSize;varying vec3 tint;uniform float scale;void main(){tint=color;vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=clamp(aSize*scale/max(3.,-mv.z),.6,9.);gl_Position=projectionMatrix*mv;}`,
    fragmentShader: `varying vec3 tint;void main(){float rr=length(gl_PointCoord-.5)*2.;if(rr>1.)discard;gl_FragColor=vec4(tint,pow(max(1.-rr,0.),1.8)*.88);}`
  });
  const points = new T.Points(geo, mat);
  points.frustumCulled = false;
  points.renderOrder = 6;
  app.scene.add(points);
  const events = [],
    ambient = new Float32Array(count * 3),
    brightness = new Float32Array(count);
  function seed(i, edge = false) {
    const k = 3 * i;
    ambient[k] = L.x + (rand() - .5) * 1100;
    ambient[k + 1] = (rand() - .42) * 930;
    ambient[k + 2] = L.z + (rand() - .5) * 1100;
    if (edge) ambient[k + i % 3] += 550 * (rand() < .5 ? -1 : 1);
    brightness[i] = .07 + rand() * .17;
  }
  for (let i = 0; i < count; i++) seed(i);
  const dust = {
    puffs: 0,
    sparks: 0,
    puff(x, y, z, strength = .8) {
      if (events.length > max - count - 4) return;
      this.puffs++;
      for (let i = 0; i < 2; i++) events.push({
        x,
        y,
        z,
        u: (rand() - .5) * 2,
        v: (.8 + rand() * 2) * strength,
        w: (rand() - .5) * 2,
        age: 0,
        life: 2 + rand() * 2.8,
        s: 1.2 + rand() * 2,
        k: 0
      });
    },
    spark(p, n) {
      this.sparks += n;
      for (let i = 0; i < n && events.length < max - count - 1; i++) events.push({
        x: p.x,
        y: p.y,
        z: p.z,
        u: (rand() - .5) * 7,
        v: 2 + rand() * 5,
        w: (rand() - .5) * 7,
        age: 0,
        life: .25 + rand() * .65,
        s: .62 + rand() * .64,
        k: 1
      });
    },
    pre(dt) {
      const pull = dt * (1 + 1.7 * app.U.uTide.value);
      for (let i = 0; i < count; i++) {
        const k = i * 3,
          dx = L.x - ambient[k],
          dy = L.y - ambient[k + 1],
          dz = L.z - ambient[k + 2],
          r2 = dx * dx + dy * dy + dz * dz;
        if (r2 < 625) {
          seed(i, true);
          continue;
        }
        const f = pull * 440 / r2;
        ambient[k] += dx * f;
        ambient[k + 1] += dy * f;
        ambient[k + 2] += dz * f;
      }
      for (let i = events.length - 1; i >= 0; i--) {
        const e = events[i];
        e.age += dt;
        if (e.age > e.life) {
          events[i] = events.at(-1);
          events.pop();
          continue;
        }
        e.v -= dt * (e.k ? 2.6 : .92);
        e.x += e.u * dt;
        e.y += e.v * dt;
        e.z += e.w * dt;
      }
    },
    frame() {
      p.set(ambient, 0);
      for (let i = 0; i < count; i++) {
        const k = i * 3,
          d = brightness[i];
        color[k] = d;
        color[k + 1] = d * .81;
        color[k + 2] = d * .78;
        sizes[i] = .55 + .6 * d;
      }
      for (let i = 0; i < events.length; i++) {
        const e = events[i],
          j = i + count,
          k = j * 3,
          intensity = Math.sin(Math.PI * Math.min(1, e.age / .08) * .5) * (1 - e.age / e.life);
        p[k] = e.x;
        p[k + 1] = e.y;
        p[k + 2] = e.z;
        color[k] = intensity * (e.k ? 2.8 : .25);
        color[k + 1] = intensity * (e.k ? .78 : .15);
        color[k + 2] = intensity * (e.k ? .16 : .12);
        sizes[j] = e.s * (e.k ? 1 : 1 + e.age * .5);
      }
      for (const x of Object.values(geo.attributes)) x.needsUpdate = true;
      geo.setDrawRange(0, count + events.length);
      mat.uniforms.scale.value = app.renderer.domElement.height / (2 * Math.tan(app.camera.fov * Math.PI / 360));
    }
  };
  sim.add('dust', dust);
}
