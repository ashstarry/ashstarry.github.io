// Start this probe at ff=20. The second render of each frozen instant removes
// only the optical response to the front. The gravity field and work continue.
() => {
  const app = window.__mine;
  const {renderer, composer, U} = app;
  const gl = renderer.getContext();
  const width = gl.drawingBufferWidth, height = gl.drawingBufferHeight;
  const image = () => new Uint8Array(width * height * 4);
  const litImage = image(), referenceImage = image();
  const rt = app.lights.rt;
  const litMap = new Uint16Array(rt.width * rt.height * 4);
  const referenceMap = new Uint16Array(litMap.length);
  const half = Float32Array.from({length:65536}, (_,i) => app.T.DataUtils.fromHalfFloat(i));
  function render(pixels, lamps) {
    app.lights.update();
    composer.render(0);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    renderer.readRenderTargetPixels(rt, 0, 0, rt.width, rt.height, lamps);
  }
  function surfaceDifference() {
    let red = 0, cyan = 0, changed = 0;
    for (let i=0; i<litImage.length; i+=4) {
      const r=litImage[i]-referenceImage[i], g=litImage[i+1]-referenceImage[i+1],
        b=litImage[i+2]-referenceImage[i+2];
      if (r>13 && r-g>8 && r-b>8) red++;
      if (g>15 && b>8 && g-r>8) cyan++;
      if (Math.max(Math.abs(r),Math.abs(g),Math.abs(b))>6) changed++;
    }
    return {red,cyan,changed};
  }
  function lampResponse(radius) {
    const wake = {samples:0, live:0, reference:0};
    const ahead = {samples:0, live:0, reference:0};
    const rect=U.uWorldRect.value, center=U.uLode.value;
    const luminance=(rgb,i)=>.3*half[rgb[i]]+.5*half[rgb[i+1]]+.2*half[rgb[i+2]];
    for(let y=1;y<rt.height;y+=5) {
      const wz=-(rect.y+(y+.5)*rect.z/rt.height);
      for(let x=1;x<rt.width;x+=5) {
        const wx=rect.x+(x+.5)*rect.z/rt.width;
        const passed=radius-Math.hypot(wx-center.x,wz-center.z);
        const bucket=passed>12 && passed<45 ? wake : passed < -55 ? ahead : null;
        if(!bucket)continue;
        const i=4*(x+rt.width*y), ref=luminance(referenceMap,i);
        if(ref<.08)continue;
        bucket.samples++; bucket.reference+=ref; bucket.live+=luminance(litMap,i);
      }
    }
    for(const b of [wake,ahead]) b.ratio=b.samples ? b.live/b.reference : null;
    return {wake,ahead};
  }
  const results=[];
  for(const t of [20,22.5,24.2,25.3,26.5,28.6,31.7,34.8,40]) {
    app.step(Math.max(0,Math.round((t-app.time)*60)));
    app.draw(0);
    const {r,a}=app.sim.field.wave;
    const u=U.uWave.value;
    if (Math.abs(u.x-r)>1e-8 || Math.abs(u.y-a)>1e-7) throw Error('Light and gravity fronts diverged.');
    try {
      render(litImage,litMap);
      u.y=0;
      render(referenceImage,referenceMap);
    } finally { u.y=a; }
    results.push({time:app.time,radius:r,strength:a,lifted:app.sys.ejecta.lifted,
      pixels:surfaceDifference(),lamps:lampResponse(r)});
  }
  app.draw(0);
  const linked=name=>app.renderer.info.programs.some(p=>p.program && gl.getUniformLocation(p.program,name)!==null);
  if(!linked('uWave') || linked('uEcho') || linked('uRise')) throw Error('Unexpected lighting pass.');
  if(results[0].pixels.changed || results.at(-1).pixels.red>width*height*.001) throw Error('Wave visible outside its passage.');
  const peak = Math.max(...results.map(s=>s.pixels.red));
  if(peak < .018*width*height) throw Error('Pressure front is too faint in the panorama.');
  if(results.some(s=>s.pixels.cyan>width*height*.001)) throw Error('A cyan front is crossing the panorama.');
  if(!results.some(s=>s.lamps.wake.samples>30 && s.lamps.wake.ratio<.55 && s.lamps.ahead.samples>30 && s.lamps.ahead.ratio>.92)) throw Error('Light-map dimming did not follow the front.');
  return {width,height,samples:results,redFrontLinked:true,secondaryBandsLinked:false};
};
