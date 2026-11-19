import * as T from 'three';
import { rng } from '../physics/world.js';
import { templateBatch } from './crew.js';

// The two rails are measured from the deck markers. Floor height is the sole plane.
function deck(app, part, a, b, halfWidth, markerAboveFloor = 0) {
  const markers = app.layout[part]?.markers;
  if (!markers?.[a] || !markers?.[b]) return null;
  const start = app.mark(part, a), end = app.mark(part, b);
  start.y -= markerAboveFloor;
  end.y -= markerAboveFloor;
  return walkway(part, start, end, halfWidth);
}

function walkway(name, start, end, halfWidth) {
  const axis = end.clone().sub(start);
  const length = axis.length();
  axis.divideScalar(length);
  const outward = new T.Vector3(-axis.z, 0, axis.x).normalize();
  return { name, start, end, axis, outward, length, halfWidth };
}

function serviceApron(app) {
  const marker = app.layout.fill?.markers?.wheel_service_pit;
  if (!marker) return null;
  const axis = new T.Vector3(...marker.axis);
  const south = new T.Vector3(-axis.z, 0, axis.x);
  const start = app.mark('fill', 'wheel_service_pit').addScaledVector(axis, -.55).addScaledVector(south, 5.40);
  start.y += 1.85; // rim at +3.30 m, axle marker at +1.45 m on the same foundation
  return walkway('axle', start, start.clone().addScaledVector(axis, 9.1), 2.75);
}

// +X is the template's nose. A foot moving back against the deck stays planted;
// its opposite foot rises on the return stroke. The belt and boot soles stay level.
const STEP = `
  vec2 bootStep(float sideW, vec2 gait) {
    float t = fract(gait.x + .5 * step(0.0, sideW));
    float groundStep = min(t * 2.0, 1.0);
    float airborne = max(t * 2.0 - 1.0, 0.0);
    float reach = .388 - .776 * groundStep + .776 * smoothstep(0.0, 1.0, airborne);
    float lift = sin(3.14159265 * airborne);
    return vec2(reach, .11 * lift * lift) * gait.y;
  }`;
const POSE = `
  float sideW = sign(position.z);
  float legW = 1.0 - smoothstep(.18, .92, position.y);
  float armW = smoothstep(.23, .35, abs(position.z)) *
    (1.0 - smoothstep(1.11, 1.5, position.y)) * smoothstep(1.01, 1.09, position.y);
  float gazeW = smoothstep(1.45, 1.70, position.y);
  vec2 bootW = bootStep(sideW, watchPose.xy);
  transformed.x += bootW.x * (legW - .77 * armW);
  transformed.y += bootW.y * legW;
  transformed.x += watchPose.z * max(position.y - .97, 0.0);
  transformed.y -= gazeW * position.x * watchPose.z * 1.32;
  transformed.y += armW * step(0.0, sideW) * watchPose.w * .22;
  transformed.x += armW * step(0.0, sideW) * watchPose.w * .13;
`;

function animateSuit(shader) {
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', '#include <common>\nattribute vec4 watchPose;\n' + STEP)
    .replace('#include <begin_vertex>', '#include <begin_vertex>\n' + POSE);
}

// The 720-m-wide sun map can represent a person's shadow but misses the much
// smaller area shaded directly under each sole. Evaluate those two contacts on
// the supporting plane using the very same stride and instance transform.
function bootContacts(app, instances, pose) {
  const geometry = new T.PlaneGeometry(1.53, .76).rotateX(-Math.PI / 2).translate(.045, .014, 0);
  geometry.setAttribute('watchPose', pose);
  const material = new T.ShaderMaterial({
    transparent: true, depthWrite: false,
    vertexShader: `attribute vec4 watchPose; varying vec2 vGround; varying vec2 vGait;
      void main(){vGround=position.xz; vGait=watchPose.xy;
        gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.0);}`,
    fragmentShader: STEP + `
      varying vec2 vGround; varying vec2 vGait;
      float contact(float sideW){
        vec2 k=bootStep(sideW,vGait);
        vec2 delta=(vGround-vec2(.042-sideW*.032+k.x,sideW*.115))/(vec2(.31,.185)+k.y*.38);
        float w=max(1.0-dot(delta,delta),0.0);
        return w*w*(.55-k.y*2.9);
      }
      void main(){gl_FragColor=vec4(.012,.012,.014,min(.70,contact(1.0)+contact(-1.0)));}`
  });
  const contacts = new T.InstancedMesh(geometry, material, instances.count);
  contacts.name = 'watch_boot_contacts';
  contacts.frustumCulled = false;
  contacts.instanceMatrix = instances.instanceMatrix;
  app.scene.add(contacts);
}

function suitBatch(app, count, detailed) {
  const batch = detailed
    ? templateBatch(app, 'watchcrew', 'watch_suit', count)
    : templateBatch(app, 'fleet', 'person_a', count);
  const pose = new T.InstancedBufferAttribute(new Float32Array(count * 4), 4);
  pose.setUsage(T.DynamicDrawUsage);
  const bounds = new T.Box3();
  const depth = new T.MeshDepthMaterial({ depthPacking: T.RGBADepthPacking });
  depth.onBeforeCompile = animateSuit;
  depth.customProgramCacheKey = () => 'watch_suit_shadow';
  for (const mesh of batch.meshes) {
    const base = mesh.material;
    const material = base.clone();
    material.defines = { ...base.defines };
    const waistLamp = base.name === 'emit_cool';
    if (waistLamp) mesh.geometry.translate(0, -.46, 0);
    mesh.geometry.computeBoundingBox();
    bounds.union(mesh.geometry.boundingBox);
    mesh.geometry.setAttribute('watchPose', pose);
    mesh.name = 'watch_crew_' + base.name;
    mesh.castShadow = !waistLamp && base.userData.kind !== 'glass';
    mesh.customDepthMaterial = depth;
    material.onBeforeCompile = (shader, renderer) => {
      base.onBeforeCompile(shader, renderer);
      animateSuit(shader);
      if (detailed && base.userData.kind === 'built') {
        // Suit panels are centimetres wide. The metre-scale edge treatment used
        // for structural steel would strip the paint off each entire fitting.
        shader.fragmentShader = shader.fragmentShader.replace(/diffuseColor\.rgb\s*=\s*sAlb;/, 'diffuseColor.rgb = mix(sAlb, diffuse, .72);');
      }
      if (waistLamp) {
        shader.fragmentShader = shader.fragmentShader.replace(/totalEmissiveRadiance\s*\+=\s*sEmit;/, 'totalEmissiveRadiance += sEmit * .12;');
      }
    };
    material.customProgramCacheKey = () => base.customProgramCacheKey() + (detailed ? '_work_suit' : '_watch') + (waistLamp ? '_lamp' : '');
    mesh.material = material;
  }
  bootContacts(app, batch.meshes[0], pose);
  return { batch, pose, sole: bounds.min.y, stature: bounds.max.y - bounds.min.y };
}

const HEIGHTS = [[1.70, 1.82, 1.75], [1.67, 1.78, 1.73], [1.81, 1.69, 1.76]];
const STOPS = [.91, .53, .08, .50];

export function watchCrew(app) {
  const detailed = app.find('watchcrew', 'watch_suit');
  if (detailed) detailed.visible = false;
  else if (!app.find('fleet', 'person_a')) return;
  const routes = [
    deck(app, 'habitat', 'watch_hab_a', 'watch_hab_b', 1.90, .05),
    deck(app, 'pit', 'watch_mast_a', 'watch_mast_b', 1.45),
    serviceApron(app)
  ];
  const workers = [];
  const random = rng(44091);
  for (const [station, route] of routes.entries()) {
    if (!route) continue;
    const startingPositions = [.43, .58, [.18, .79, .23][station]];
    const lanes = [.55, .43, -.51];
    for (const [role, height] of HEIGHTS[station].entries()) {
      const lamp = app.lights.add({ p: route.start.toArray(), c: [.38, .63, .60], r: 2.25, i: .13, k: 'aura' });
      workers.push({
        route, role, height, along: startingPositions[role] * route.length, lane: route.halfWidth * lanes[role], p: new T.Vector3(),
        yaw: 0, lamp, speed: 0, pace: [.95, .77, 1.08][station], phase: random() * 6.28,
        stop: station === 1 ? 2 : 0, wait: 0, inspections: 0
      });
    }
  }
  if (!workers.length) return;
  const { batch, pose, sole, stature } = suitBatch(app, workers.length, detailed);
  const figure = new T.Object3D();
  const heading = new T.Vector3();
  function locate(w) {
    w.p.copy(w.route.start).addScaledVector(w.route.axis, w.along).addScaledVector(w.route.outward, w.lane);
  }
  function setHeading(w, along, outside, dt) {
    const across = w.route.name === 'axle' ? -outside : outside;
    heading.copy(w.route.axis).multiplyScalar(along).addScaledVector(w.route.outward, across);
    const goal = -Math.atan2(heading.z, heading.x);
    w.yaw += Math.atan2(Math.sin(goal - w.yaw), Math.cos(goal - w.yaw)) * Math.min(1, 2.8 * dt);
  }
  function advance(w, dt) {
    const target = STOPS[w.stop] * w.route.length;
    const distance = target - w.along;
    if (w.wait > 0) {
      w.wait -= dt;
      if (w.wait <= 0) w.stop = (w.stop + 1) % STOPS.length;
      return;
    }
    w.speed = Math.min(w.pace, w.speed + 1.20 * dt, Math.sqrt(2.40 * Math.abs(distance)));
    const step = Math.min(Math.abs(distance), w.speed * dt);
    w.along += Math.sign(distance) * step;
    w.phase += step * 4.05 / (w.height * .5);
    if (Math.abs(distance) - step < .002) {
      w.along = target;
      w.speed = 0;
      w.inspections++;
      w.wait = (w.stop % 2 ? 8 : 4) + random() * 5;
    }
  }
  function post(dt) {
    for (let i = 0; i < workers.length; i++) {
      const w = workers[i];
      if (w.role === 2) advance(w, dt);
      locate(w);
      if (w.role === 2 && w.wait <= 0) {
        setHeading(w, Math.sign(STOPS[w.stop] * w.route.length - w.along), 0, dt);
      } else {
        const partner = workers[i - w.role + 2];
        const near = Math.abs(partner.along / w.route.length - .52) < .105;
        if (w.role === 0) setHeading(w, near ? .77 : -.56, .76, dt);
        else if (w.role === 1) setHeading(w, -.89, near ? -.33 : .33, dt);
        else setHeading(w, -.25, w.stop % 2 ? 1 : -.8, dt);
      }
    }
  }
  function frame() {
    const t = app.sim.time;
    for (const [i, w] of workers.entries()) {
      const scale = w.height / stature;
      const gait = w.speed / w.pace;
      const bend = (w.role === 0 ? .13 : .045) + .016 * Math.sin(.53 * t + i);
      const gesture = w.role === 1 ? Math.pow(.5 + .5 * Math.sin(.26 * t + i * .81), 4) : 0;
      figure.position.copy(w.p);
      figure.position.y -= sole * scale;
      figure.rotation.y = w.yaw;
      figure.scale.setScalar(scale);
      batch.set(i, figure);
      pose.setXYZW(i, (w.phase / (2 * Math.PI)) % 1, gait, bend, gesture);
      if (w.lamp) {
        w.lamp.p.set(.20, 1.05, .19).applyMatrix4(figure.matrix);
        w.lamp.on = 1 - .64 * app.U.uTide.value;
        w.lamp.dirty = true;
      }
    }
    batch.finish();
    pose.needsUpdate = true;
  }
  post(0);
  for (const w of workers) {
    if (w.role === 2) setHeading(w, Math.sign(STOPS[w.stop] * w.route.length - w.along), 0, 1);
    else setHeading(w, w.role === 0 ? -.56 : -.89, w.role === 0 ? .76 : .33, 1);
  }
  frame();
  return app.sim.add('watchCrew', { workers, count: workers.length, drawCalls: batch.meshes.length + 1, post, frame });
}
