import { V } from './view.js';
export function labels(app) {
  const root = document.querySelector('#tags'),
    s = app.sys;
  const all = [
    ['The Lode', 'Rocks orbit in a 1/r field that swells with the tide.', [-78, -62, -12]],
    ['Freighter', () => 'Cargo ' + s.freighter.cargo.length + '/250 · departs when full', () => s.freighter.ship.position],
    ['The Sling', 'The Lode bends the shot. The launcher corrects its aim.', [-167, 27, 60]],
    ['The Whip', 'The track turns. The ore flies straight on.', [241, 101, 88]],
    ['The Crucible', 'Surface tension ripples the metal. Tides stretch it.', () => s.crucible?.center || V(64, 31, 158)],
    ['Suspension Bridge', () => 'Deck deflection ' + s.bridge.deflection.toFixed(2) + ' m', [168, -2, 70]],
    ['Ore Vortex', 'The beam lifts a spiral of ore. Tides strip its edges.', [-62, 8, -62]],
    ['Gravity Wall', 'Gravity pulls trucks into the vertical road.', [-87, -28, -84]],
    ['Habitat Ring', 'Rotating quarters with Earth-normal gravity.', [96, 56, -146]],
    ['The Updraft', 'Ore falls upward through the shaft.', [98, 47, -8]],
    ['Bucket-Wheel Excavator', 'The heavy wheel coasts to a stop when feed backs up.', [-183, 32, -13]],
    ['The Mitt', 'The capture field slows and gathers incoming rock.', [40, 26, 8]],
    ['Debris Ring', 'Equal orbital speeds. The inner rocks lap the outer ring.', [-280, 20, -330]],
    ['Moored Boulder', 'A lift field raises the rock against its anchor chain.', () => s.moorings.stones[0].body.p],
    ['Breaker Station', 'The ram splits the rock. Fragments conserve momentum.', [27, 107, -13]],
    ['Dock Crane', 'An off-center load swings and twists on two cables.', () => s.crane.pivot.p],
    ['Pulse Jig', 'Pale waste rises above the ore on each stroke.', [74, 6, 26]],
    ['Tailings Fall', 'Waste curves under the disc toward the Lode.', [149, 1, 36]],
    ['Surge Bin', 'Ore piles up until the gate opens over a wagon.', [114, 27, -8]],
    ['Mass Driver', 'The departing payload drives the sled backward.', [273, 13, 56]],
    ['Gravity Seep', 'Rock rises from old craters and arcs toward the pit.', [-158, 47, 128]],
    ['Repulsion Dome', 'Incoming debris bends around the crew quarters.', [130, 72, -156]],
    ['Tipper Bay', 'Ore slides down a steel bed in low gravity.', [40, 3, -24]],
    ['Tug', 'The asteroid overshoots and pulls its towline taut.', () => s.breaker.tugPoint || V(-41, 120, -74), () => s.breaker.phase === 'tow'],
    ['Tide Front', 'Gravity reverses and loose stones lift in a ring.', () => V(-78 + app.U.uWave.value.x * .78, 2, app.U.uWave.value.x * .62 - 12), () => app.U.uWave.value.y > 0]
  ];
  all.unshift(['Salvage Beam', () => s.salvage.phase === 'free' ? 'In free flight the beam flips about its middle axis.' : 'A second winch catches the spinning beam.', () => s.salvage.position]);
  all.splice(9, 0, ['Bench Collapse', () => s.rockfall.active ? 'Loose slabs slide to the bench below.' : 'The excavator undercuts the fractured face.', () => s.rockfall.face]);
  all.push(['Axle Shop', 'A detached axle rests in the service pit.', app.mark('fill','wheel_service_pit',[59,-2,108])],
    ['Life Support', 'Heat exchangers return water to the quarters.', app.mark('habitat','hab_reclaim',[116,13,-68])]);
  all.splice(4,0,
    ['Tower Counterweights','Opposed weights settle on damped springs.',[96,119,-145]],
    ['West Yard Barge','The cable drum swings wide as the barge turns.',() => s.harborFlight.position]);
  all.push(['Crane Watch','Crew height 1.7 m · rail height 1.1 m.',[12,69,22]]);
  const entries = all.map(([name, text, p, on]) => {
    const el = document.createElement('div');
    el.className = 'tag';
    const h = document.createElement('b'),
      small = document.createElement('small');
    h.textContent = name;
    small.textContent = typeof text === 'string' ? text : text();
    el.append(h, small);
    el.style.opacity = '0';
    root.append(el);
    return {
      el,
      small,
      text,
      p: typeof p === 'function' ? p : V(...p),
      on,
      w: el.offsetWidth,
      h: el.offsetHeight
    };
  });
  const v = V(),
    boxes = [];
  let dirty = true;
  let measureAll = true;
  window.addEventListener("resize", () => {
    measureAll = true;
  });
  const hide = e => {
    e.el.style.opacity = '0';
  };
  app.labels = () => {
    if (!app.tagsOn) {
      if (dirty) {
        for (const e of entries) hide(e);
        dirty = false;
      }
      return;
    }
    dirty = true;
    boxes.length = 0;
    for (const e of entries) {
      if (e.on && !e.on()) {
        hide(e);
        continue;
      }
      v.copy(typeof e.p === 'function' ? e.p() : e.p).project(app.camera);
      if (Math.abs(v.x) > 1.04 || Math.abs(v.y) > .97 || v.z < -1 || v.z > 1) {
        hide(e);
        continue;
      }
      let measure = measureAll;
      if (typeof e.text === 'function') {
        const caption = e.text();
        if (caption !== e.small.textContent) {
          e.small.textContent = caption;
          measure = true;
        }
      }
      if (measure) {
        e.w = e.el.offsetWidth;
        e.h = e.el.offsetHeight;
      }
      const x0 = (.5 + v.x * .5) * innerWidth,
        y0 = (.5 - v.y * .5) * innerHeight;
      let placed = false;
      for (const [dx, dy] of [[7, -e.h - 4], [7, 5], [-e.w - 7, -e.h - 4], [-e.w - 7, 4]]) {
        const x = x0 + dx,
          y = y0 + dy;
        if (x < 6 || y < 6 || x + e.w > innerWidth - 6 || y + e.h > innerHeight - 32) continue;
        const rect = [x, y, x + e.w, y + e.h];
        if (boxes.some(b => rect[0] < b[2] + 4 && rect[2] + 4 > b[0] && rect[1] < b[3] + 3 && rect[3] + 3 > b[1])) continue;
        boxes.push(rect);
        e.el.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px)';
        e.el.style.opacity = '1';
        placed = true;
        break;
      }
      if (!placed) hide(e);
    }
    measureAll = false;
  };
}
