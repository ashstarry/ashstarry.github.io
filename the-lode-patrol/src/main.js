import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { U, prepareTextures } from './materials.js';
import { selectedFocus, views, viewpoints, homeForAspect, fieldOfView } from './views.js';
import { Lights } from './lights.js';
import { buildSky, KEY_DIR, DARK_STAR } from './sky.js';
import { post } from './post.js';
import { loadAssets } from './assets.js';
import { install } from './systems/index.js';
const boot = window.mineBoot,
  params = new URLSearchParams(location.search);
const initialView = selectedFocus(params);
const initialHome = homeForAspect(innerWidth/innerHeight);
const initialCamera = initialView === 'home' ? initialHome : views[initialView];
const HOME = { position: initialHome.eye, target: initialHome.target };
const app = window.__mine = {
  T,
  U,
  params,
  HOME,
  layout: {},
  objects: {},
  sys: {},
  fatal: null,
  ready: false,
  paused: false,
  handheld: matchMedia('(pointer: coarse)').matches && Math.min(innerWidth, innerHeight) <= 768,
  holdTide: false,
  time: 0,
  metrics: {},
  tagsOn: params.get('tags') === '1'
};
function fatal(e) {
  if (app.fatal) return;
  app.fatal = String(e?.stack || e);
  const heading = String(e?.message || e).startsWith('SHADER ERROR') ? 'SHADER ERROR' : 'MINE OFFLINE';
  boot.fail(heading, /WebGL|context/i.test(app.fatal) ? 'Graphics interrupted. Reload or open the recorded tour.' : 'The mine could not load. Reload or open the tour.');
  console.error(app.fatal);
}
window.addEventListener('error', e => fatal(e.error || e.message));
window.addEventListener('unhandledrejection', e => fatal(e.reason));
function fromURL(name, base) {
  const p = params.get(name)?.split(',').map(Number);
  return p?.length === 3 && p.every(Number.isFinite) ? p : base;
}
async function start(canvas, context) {
  const r = app.renderer = new T.WebGLRenderer({
    canvas,
    context,
    antialias: false,
    powerPreference: 'high-performance'
  });
  r.debug.onShaderError = (gl, program, vs, fs) => fatal(Error('SHADER ERROR\n' + gl.getProgramInfoLog(program) + '\n' + gl.getShaderInfoLog(vs) + '\n' + gl.getShaderInfoLog(fs)));
  function targetPixelRatio() {
    const limit = app.handheld ? Math.max(1,Math.min(2,Math.sqrt(1250000 / (innerWidth * innerHeight)))) : 1.5;
    return Math.max(.3,Math.min(2,Number(params.get('dpr')) || Math.min(devicePixelRatio,limit)));
  }
  r.setPixelRatio(targetPixelRatio());
  r.setSize(innerWidth, innerHeight);
  r.outputColorSpace = T.SRGBColorSpace;
  r.toneMapping = T.ACESFilmicToneMapping;
  r.toneMappingExposure = 1.32;
  r.shadowMap.enabled = true;
  r.shadowMap.type = T.PCFShadowMap;
  document.body.prepend(r.domElement);
  const scene = app.scene = new T.Scene();
  scene.background = new T.Color(0x010102);
  const cam = app.camera = new T.PerspectiveCamera(fieldOfView(innerWidth/innerHeight), innerWidth/innerHeight, 5, 9000);
  cam.position.fromArray(fromURL('cam', initialCamera.eye));
  const controls = app.controls = new OrbitControls(cam, r.domElement);
  controls.target.fromArray(fromURL('tgt', initialCamera.target));
  controls.enableDamping = true;
  controls.dampingFactor = .06;
  controls.minDistance = 40;
  controls.maxDistance = 1600;
  controls.autoRotateSpeed = .12;
  controls.update();
  let interaction = performance.now(), atHome = true;
  controls.addEventListener('start', () => {
    atHome = false;
    interaction = performance.now();
    controls.autoRotate = false;
  });
  controls.addEventListener('end', () => interaction = performance.now());
  const moveView = viewpoints(app, initialView, () => {
    interaction = performance.now();
    controls.autoRotate = false;
  });
  const sun = app.sun = new T.DirectionalLight(0xcfe3e6, 2.6);
  sun.position.copy(KEY_DIR).multiplyScalar(620).add(new T.Vector3(20, -20, 0));
  sun.target.position.set(20, -20, 0);
  sun.castShadow = true;
  const ss = params.has('shadow') ? Number(params.get('shadow')) : (app.handheld ? 1024 : 4096);
  sun.shadow.mapSize.set(ss, ss);
  Object.assign(sun.shadow.camera, {
    left: -360,
    right: 360,
    top: 330,
    bottom: -330,
    near: 50,
    far: 1300
  });
  sun.shadow.bias = -.0015;
  sun.shadow.normalBias = 1.4;
  scene.add(sun, sun.target);
  const ember = new T.DirectionalLight(0xff2a3c, 2.3);
  ember.position.copy(DARK_STAR).multiplyScalar(900);
  scene.add(ember, new T.HemisphereLight(0x1d3a44, 0x2a0a10, .55));
  app.lights = new Lights(app);
  boot.progress(9,'Building the dark-star sky');
  await boot.paint();
  buildSky(app);
  post(app);
  let models = 0, textures = 0;
  function updateAssets() {
    boot.progress(14 + 40 * models + 12 * textures, models === 1 ? 'Loading surface textures' : 'Loading machinery and terrain');
  }
  updateAssets();
  await boot.paint();
  await Promise.all([
    loadAssets(app, value => { models = value; updateAssets(); }),
    prepareTextures(r, value => { textures = value; updateAssets(); })
  ]);
  boot.progress(67,'Connecting the machinery');
  await boot.paint();
  await install(app);
  app.batchStatic();
  function resize() {
    const a = innerWidth / innerHeight;
    const home = homeForAspect(a);
    HOME.position = home.eye; HOME.target = home.target;
    if (cam.aspect !== a && atHome && app.focus === 'home' && !params.has('cam') && !params.has('tgt')) {
      cam.position.fromArray(home.eye);
      controls.target.fromArray(home.target);
      controls.update(0);
    }
    cam.aspect = a;
    cam.fov = fieldOfView(a);
    cam.updateProjectionMatrix();
    const ratio = targetPixelRatio();
    if (ratio !== r.getPixelRatio()) {
      r.setPixelRatio(ratio);
      app.composer.setPixelRatio(ratio);
    }
    r.setSize(innerWidth, innerHeight);
    app.composer.setSize(innerWidth, innerHeight);
  }
  addEventListener('resize', resize);
  resize();
  const toggle = () => {
    app.tagsOn = !app.tagsOn;
    document.querySelector('#labels').setAttribute('aria-pressed', app.tagsOn);
  };
  document.querySelector('#labels').onclick = toggle;
  addEventListener('keydown', e => {
    if (!e.repeat && e.key.toLowerCase() === 'l') toggle();
  });
  const step = app.step = (n = 1) => {
    for (let i = 0; i < n; i++) {
      app.sim?.step(1 / 60);
      app.time += 1 / 60;
    }
    U.uTime.value = app.time;
  };
  const ff = params.has('ff') ? Math.max(0, Math.min(3600, Number(params.get('ff')) || 0)) : (views[initialView].ff ?? views.home.ff);
  const steps = Math.round(ff * 60);
  boot.progress(70,'Warming up the simulation','WARMING UP THE MINE');
  await boot.paint();
  // Yield according to wall time so a slower CPU still gets paints and input.
  for (let i = 0; i < steps;) {
    const until = performance.now() + 12;
    do { const count = Math.min(4,steps-i); step(count); i += count; }
    while (i < steps && performance.now() < until);
    boot.progress(70 + 18 * i / steps, 'Warming up the simulation');
    if (i < steps) await new Promise(ok => setTimeout(ok,0));
  }
  function draw(dt = 0) {
    app.sim?.frame(dt);
    app.sky.mat.uniforms.uTime.value = app.time;
    app.sky.mat.uniforms.uTide.value = U.uTide.value;
    app.sky.dome.position.copy(cam.position);
    app.lights.update();
    app.composer.render(dt);
    app.labels?.();
  }
  app.draw = draw;
  let last = performance.now(),
    acc = 0,
    mean = 1 / 30,
    hudAt = 0;
  if (initialView === 'harbor' && !params.has('cam') && !params.has('tgt')) app.setView('harbor', false);
  boot.progress(89,'Compiling materials and lighting');
  await boot.paint();
  await r.compileAsync(scene,cam);
  if (app.fatal) return;
  boot.progress(96,'Drawing the full-resolution opening frame');
  await boot.paint();
  const opening = window.mineOpening;
  let angle = 0, zoom = 1;
  function applyOpeningPose() {
    if (!opening?.active || initialView !== 'home') return;
    const next = opening.visibleYaw(), scale = opening.zoom;
    if (next === angle && scale === zoom) return;
    const offset = new T.Spherical().setFromVector3(cam.position.clone().sub(controls.target));
    offset.theta += next - angle;
    offset.radius = T.MathUtils.clamp(offset.radius * zoom / scale, controls.minDistance, controls.maxDistance);
    cam.position.copy(controls.target).add(new T.Vector3().setFromSpherical(offset));
    atHome = false; controls.update(0); angle = next; zoom = scale;
  }
  applyOpeningPose();
  draw(0);
  if (app.fatal) return;
  // The WebGL call only submits work. Let the browser keep painting the loader
  // while the GPU actually finishes the full-resolution postprocessed image.
  const gl = r.getContext(), fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);
  if (fence) {
    gl.flush();
    try {
      for (;;) {
        const result = gl.clientWaitSync(fence,0,0);
        if (result === gl.WAIT_FAILED || gl.isContextLost()) throw Error('WebGL context interrupted');
        if (result !== gl.TIMEOUT_EXPIRED) break;
        await new Promise(requestAnimationFrame);
      }
    } finally { gl.deleteSync(fence); }
  }
  await boot.paint();
  applyOpeningPose();
  draw(0);
  if (app.fatal) return;
  app.metrics.opening = {epoch:ff, mediaTime:0, liveTime:app.time, yaw:angle, zoom, width:canvas.width, height:canvas.height};
  interaction = last = performance.now();
  const manual = params.has('manual');
  function tick(now) {
    if (app.fatal) return;
    requestAnimationFrame(tick);
    if (manual || app.paused) return;
    const dt = Math.max(0, (now - last) / 1000);
    last = now;
    mean = mean * .93 + Math.min(dt, 2) * .07;
    acc = Math.min(.05, acc + dt);
    const n = Math.min(3, Math.floor(acc * 60 + 1e-8));
    acc -= n / 60;
    step(n);
    moveView(Math.min(dt,.15));
    const rotate = params.has('rot') ? params.get('rot') !== '0' : app.focus === 'home';
    controls.autoRotate = rotate && now - interaction > 45000;
    controls.update(Math.min(dt, .05));
    draw(Math.min(dt, .05));
    if (now - hudAt > 400) {
      hudAt = now;
      app.updateHUD(1 / Math.max(.001, mean));
    }
  }
  app.updateHUD = (fps = null) => {
    const tide = U.uTide.value > .06;
    document.querySelector('#hud').classList.toggle('tide', tide);
    document.querySelector('#state').textContent = (tide ? 'Gravity tide ▲ ' + (1 + app.sim.field.lode.tide).toFixed(2) + '×' : 'Gravity steady') + '   Rocks ' + (app.sim?.count || 0) + (Number.isFinite(fps) ? '   ' + fps.toFixed(0) + ' fps ' : ' ');
  };
  app.updateHUD();
  app.ready = true;
  boot.finish();
  requestAnimationFrame(tick);
}
export function startMine(canvas, context) {
  return start(canvas, context).catch(fatal);
}
