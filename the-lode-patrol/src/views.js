import { Spherical, Vector3 } from 'three';

export const views = {
  home: { title: 'Panorama', eye: [327,370,685], target: [34,4,6], ff: 20 },
  dust: { title: 'North Dust Works', eye: [-73,52,-62], target: [-121,21,-138], ff: 20 },
  winch: { title: 'Rim Winch', eye: [125,26,190], target: [94,5,161], ff: 20 },
  watch: { title: 'Tower Watch', eye: [116.8,158.8,-135.6], target: [62,130,-115] },
  mast: { title: 'Crane Catwalk', eye: [31.3,80.4,30.3], target: [-22,49.4,7.8] },
  harbor: { title: 'Work Barge', eye: [-208,138,211], target: [-204,88,109], ff: 36 },
  salvage: { title: 'Salvage Beam', eye: [-7,43,345], target: [-42,16,228], ff: 39 },
  face: { title: 'Bench Collapse', eye: [-57,26,53], target: [-127,-27,-43], ff: 22 },
  hull: { title: 'Cargo Hold', eye: [401,7,232], target: [229,167,93] },
  yard: { title: 'Axle Shop', eye: [90,17,149], target: [54,0,109] },
  hab: { title: 'Habitat', eye: [166,76,6], target: [91,40,-130] },
  sky: { title: 'Dark Star', eye: [485,525,1015], target: [5,-64,0] }
};

const narrowHome = { ...views.home, eye: [357,351,668], target: [30,11,3] };

export function homeForAspect(aspect) {
  const blend = Math.max(0, Math.min(1, (aspect - .78) / .47));
  const mix = (a,b) => a.map((v,i) => v + (b[i] - v) * blend);
  return { ...views.home, eye: mix(narrowHome.eye, views.home.eye), target: mix(narrowHome.target, views.home.target) };
}

export function fieldOfView(aspect) {
  const half = 31.2 * Math.PI / 360;
  return 2 * Math.atan(Math.tan(half) * Math.max(1, 1.43 / aspect)) * 180 / Math.PI;
}

export function selectedFocus(params) {
  const key = params.get('focus');
  return Object.hasOwn(views,key) ? key : 'home';
}

export function viewpoints(app, initial, stopRotation) {
  const selector = document.querySelector('#viewpoint');
  const { camera, controls } = app;
  for (const [key, view] of Object.entries(views)) {
    selector.add(new Option(view.title,key));
  }
  selector.value = initial;
  const startTarget = new Vector3(), endTarget = new Vector3(), offset = new Vector3();
  const start = new Spherical(), end = new Spherical(), current = new Spherical();
  let elapsed = Infinity;
  function frame(dt) {
    if (elapsed >= 1) return;
    elapsed = Math.min(1,elapsed + dt);
    const u = elapsed*elapsed*(3-2*elapsed);
    controls.target.lerpVectors(startTarget,endTarget,u);
    current.set(start.radius+(end.radius-start.radius)*u,start.phi+(end.phi-start.phi)*u,start.theta+(end.theta-start.theta)*u);
    camera.position.copy(controls.target).add(offset.setFromSpherical(current));
    controls.update(0);
  }
  function move(key, animate = true) {
    if (!Object.hasOwn(views,key)) return;
    const view = key === 'home' ? homeForAspect(camera.aspect) : views[key];
    selector.value = key;
    app.focus = key;
    stopRotation();
    startTarget.copy(controls.target);
    start.setFromVector3(offset.subVectors(camera.position,startTarget));
    endTarget.fromArray(view.target);
    if (key === 'harbor' && app.sys.harborFlight) {
      const ship = app.sys.harborFlight;
      endTarget.copy(ship.position).lerp(ship.loadPosition,.48);
      end.setFromVector3(offset.set(-71,34,-31));
    } else {
      end.setFromVector3(offset.fromArray(view.eye).sub(endTarget));
    }
    end.theta = start.theta + Math.atan2(Math.sin(end.theta-start.theta),Math.cos(end.theta-start.theta));
    elapsed = 0;
    if (!animate || app.paused || app.params.has('manual') || matchMedia('(prefers-reduced-motion: reduce)').matches) frame(1);
  }
  selector.addEventListener('change',() => move(selector.value));
  controls.addEventListener('start',() => { elapsed=Infinity; });
  app.setView = move;
  app.focus = initial;
  return frame;
}
