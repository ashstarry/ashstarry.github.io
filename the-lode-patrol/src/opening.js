// This is a real photograph at simulation time 20. The clock and the GPU are
// deliberately independent of the time the browser spends on this screen.
(() => {
  const boot = document.querySelector('#boot'), host = document.querySelector('#opening');
  const frame = document.querySelector('#opening-frame'), plate = document.querySelector('#op-plate');
  const angleImage = document.querySelector('#op-turn'), bar = document.querySelector('#boot-track');
  const fill = document.querySelector('#boot-fill'), percent = document.querySelector('#boot-percent');
  const label = document.querySelector('#boot-detail'), title = document.querySelector('#boot-title');
  const params = new URLSearchParams(location.search), plates = window.minePlates;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let mode = params.get('view'), shot = null, displayShot = null, showPlate = plates.home;
  let value = 0, ended = false, failed = false, sequence = 0, shownYaw = 0, pinch = 0;
  const pointers = new Map();
  const opening = window.mineOpening = { active: true, yaw: 0, zoom: 1, turned: false };
  const nextPaint = () => new Promise(resolve => requestAnimationFrame(resolve));
  const clockPaint = async () => { await nextPaint(); await nextPaint(); };

  function resize() {
    if (!opening.active) return;
    let w = innerWidth, h = innerHeight;
    const aspect = w / h;
    const guided = mode === 'tour';
    if (guided || !angleImage.hidden) {
      const filmAspect = aspect <= .8 ? .5 : 1.6;
      h = Math.min(h, w / filmAspect); w = h * filmAspect;
    }
    frame.style.width = w + 'px'; frame.style.height = h + 'px';
    if (showPlate) {
      const next = plates.select(aspect, mode);
      if (shot !== next) {
        shot = next;
        const photo = new Image(); photo.fetchPriority = 'high'; photo.src = plates.url(next);
        photo.decode().then(() => {
          if (shot !== next || !opening.active) return;
          displayShot = next; plate.src = photo.src; resize();
        }).catch(() => {});
      }
      if (displayShot) plates.fit(plate, displayShot, w, h);
    }
    frame.style.transform = 'translate(-50%, -50%) scale(' + opening.zoom + ')';
  }
  function changeMode(next) { mode = next; resize(); }
  if (!showPlate) {
    const focus = params.get('focus');
    if (['watch','mast','dust','winch','harbor','hab','hull','face','yard','salvage','sky'].includes(focus) &&
        !['manual','parts','test','cam','tgt','ff'].some(key => params.has(key))) {
      const variant = innerWidth / innerHeight <= .8 ? 'v-' : '';
      plate.src = window.mineMediaURL('./assets/tour/' + variant + (focus === 'sky' ? 'wide' : focus) + '.webp');
      plate.classList.add('focus-plate');
    } else plate.hidden = true;
  }
  resize();
  addEventListener('resize',resize);

  function progress(n, text, heading) {
    if (ended || failed) return;
    value = Math.max(value, Math.min(99, Math.floor(n)));
    bar.setAttribute('aria-valuenow',String(value));
    percent.textContent = value + '%'; fill.style.transform = 'scaleX(' + value / 100 + ')';
    if (text && label.textContent !== text) label.textContent = text;
    if (heading) title.textContent = heading;
  }
  function turn() {
    const tall = innerWidth / innerHeight <= .8, n = tall ? 24 : 60;
    const step = Math.round(opening.yaw * n / (2 * Math.PI));
    const url = window.mineMediaURL('./assets/tour/' + (tall ? 'p' : 'o') + String((step % n + n) % n).padStart(2,'0') + '.webp');
    if (angleImage.getAttribute('src') === url) { sequence++; return; }
    const serial = ++sequence, next = new Image();
    next.src = url;
    next.decode().then(() => {
      if (serial !== sequence || !opening.active) return;
      shownYaw = step * Math.PI * 2 / n; angleImage.src = url; angleImage.hidden = false;
      resize();
    }).catch(() => {});
  }
  function zoom(ratio) {
    opening.zoom = Math.min(3.5, Math.max(.7, opening.zoom * ratio)); resize();
  }
  const gap = () => { const [a,b] = pointers.values(); return Math.hypot(a.x-b.x,a.y-b.y); };
  host.addEventListener('pointerdown', e => {
    if (!showPlate || !opening.active || e.button !== 0) return;
    host.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if (pointers.size === 2) pinch = gap();
  });
  host.addEventListener('pointermove', e => {
    const p = pointers.get(e.pointerId); if (!p || !opening.active) return;
    const dx = e.clientX-p.x; p.x = e.clientX; p.y = e.clientY;
    if (pointers.size === 2) { const d = gap(); if (d && pinch) zoom(d / pinch); pinch = d; }
    else if (dx) { opening.turned = true; opening.yaw -= dx * Math.PI * 1.65 / Math.max(240,innerWidth); turn(); }
  });
  for (const event of ['pointerup','pointercancel','lostpointercapture']) host.addEventListener(event, e => pointers.delete(e.pointerId));
  host.addEventListener('wheel', e => {
    if (!showPlate || !opening.active) return;
    e.preventDefault(); zoom(Math.exp(-e.deltaY * .001));
  },{passive:false});
  opening.visibleYaw = () => angleImage.hidden ? opening.yaw : shownYaw;
  function detach() {
    opening.active = false; sequence++; pointers.clear();
    removeEventListener('resize',resize);
  }
  function finish() {
    if (ended || failed) return;
    ended = true; detach();
    value = 100; bar.setAttribute('aria-valuenow','100'); fill.style.transform = 'scaleX(1)'; percent.textContent = '100%';
    label.textContent = 'Mine ready';
    // A user can orbit throughout the dissolve, even on a very slow device.
    host.style.pointerEvents = 'none';
    requestAnimationFrame(() => {
      if (failed) return;
      host.classList.add('off'); boot.classList.add('off');
      function hide() {
        if (failed) return;
        host.hidden = true; boot.hidden = true;
      }
      if (reduced.matches) hide();
      else setTimeout(hide,410);
    });
  }
  function fail(heading, detail) {
    failed = true; detach(); host.hidden = true;
    boot.hidden = false; boot.className = 'fail';
    title.textContent = heading; label.textContent = detail;
  }
  window.mineBoot = { progress, mode: changeMode, finish, fail, paint: clockPaint };
})();
