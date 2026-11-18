async () => {
  const app = window.__mine,
    {
      T,
      renderer,
      composer,
      sim,
      sys,
      U
    } = app;
  const frameCount = Number(app.params.get('frames')) || 120;
  const lut = new Float32Array(65536);
  for (let i = 0; i < lut.length; i++) lut[i] = T.DataUtils.fromHalfFloat(i);
  // WebGL allocates whole pixels even when CSS size × device pixel ratio is fractional.
  const width = Math.floor(composer.readBuffer.width),
    height = Math.floor(composer.readBuffer.height);
  const pixels = new Uint16Array(width * height * 4);
  const xTile = new Uint8Array(width),
    yTile = new Uint8Array(height);
  for (let x = 0; x < width; x++) xTile[x] = Math.floor(x * 16 / width);
  for (let y = 0; y < height; y++) yTile[y] = 16 * Math.floor(y * 10 / height);
  const sizes = new Uint32Array(160);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) sizes[xTile[x] + yTile[y]]++;
  function scan(rt) {
    renderer.readRenderTargetPixels(rt, 0, 0, width, height, pixels);
    const blocks = new Float64Array(160);
    let sum = 0,
      invalid = 0,
      peak = 0;
    for (let y = 0, i = 0; y < height; y++) for (let x = 0; x < width; x++, i += 4) {
      const r = lut[pixels[i]],
        g = lut[pixels[i + 1]],
        b = lut[pixels[i + 2]];
      if (!Number.isFinite(r + g + b + lut[pixels[i + 3]])) {
        invalid++;
        continue;
      }
      const value = .3 * r + .55 * g + .15 * b;
      sum += value;
      blocks[xTile[x] + yTile[y]] += value;
      if (value > peak) peak = value;
    }
    for (let j = 0; j < 160; j++) blocks[j] /= sizes[j];
    return {
      mean: sum / (width * height),
      invalid,
      peak,
      blocks
    };
  }
  function lightMap() {
    const rt = app.lights.rt,
      n = rt.width * rt.height,
      raw = new Uint16Array(n * 4);
    renderer.readRenderTargetPixels(rt, 0, 0, rt.width, rt.height, raw);
    let lit = 0,
      invalid = 0,
      peak = 0;
    for (let i = 0; i < n * 4; i += 4) {
      const l = .3 * lut[raw[i]] + .5 * lut[raw[i + 1]] + .2 * lut[raw[i + 2]];
      if (!Number.isFinite(l + lut[raw[i + 3]])) invalid++;
      if (l > .001) lit++;
      peak = Math.max(peak, l);
    }
    return {
      pixels: n,
      lit,
      invalid,
      peak
    };
  }
  // Tap the original scene target before the finite-value guard and bloom.
  let raw = null;
  const probe = {
    enabled: false,
    needsSwap: false,
    setSize() {},
    render(r, unused, rt) {
      const s = scan(rt);
      raw = {
        invalid: s.invalid,
        mean: s.mean,
        peak: s.peak
      };
    }
  };
  composer.insertPass(probe, 1);
  composer.renderToScreen = false;
  app.holdTide = true;
  sim.field.wave.a = 0;
  sim.field.wave.r = -1000;
  U.uTide.value = 0;
  U.uWave.value.set(-1000, 0, 0, 0);
  U.uShadow.value.w = 0;
  const means = [];
  let prev = null,
    maxTileDelta = 0,
    blackOrBrightTiles = 0,
    invalid = 0;
  let calmRaw, calmFinal;
  for (let f = 0; f < frameCount; f++) {
    app.step(1);
    probe.enabled = f === 0;
    app.draw(1 / 60);
    const s = scan(composer.readBuffer);
    if (f === 0) {
      calmRaw = raw;
      calmFinal = {
        invalid: s.invalid,
        mean: s.mean,
        peak: s.peak
      };
    }
    means.push(s.mean);
    invalid += s.invalid;
    if (prev) for (let j = 0; j < 160; j++) {
      const delta = Math.abs(s.blocks[j] - prev[j]);
      maxTileDelta = Math.max(maxTileDelta, delta);
      if (delta > .12 || Math.max(s.blocks[j], prev[j]) > .05 && Math.min(s.blocks[j], prev[j]) < .005) blackOrBrightTiles++;
    }
    prev = s.blocks;
    if (f % 8 === 0) await new Promise(done => setTimeout(done, 0));
  }
  const mean = means.reduce((t, v) => t + v, 0) / means.length;
  const std = Math.sqrt(means.reduce((t, v) => t + (v - mean) ** 2, 0) / means.length);
  const splat = lightMap();
  app.holdTide = false;
  sys.tides.trigger(1.9);
  app.step(195);
  probe.enabled = true;
  app.draw(1 / 60);
  const tideRaw = raw;
  const tide = scan(composer.readBuffer);
  composer.removePass(probe);
  composer.renderToScreen = true;
  app.draw(0);
  app.updateHUD();
  const gl = renderer.getContext(),
    ext = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    frames: frameCount,
    width,
    height,
    msaa: composer.renderTarget1.samples,
    tileGrid: [16, 10],
    luminanceMean: mean,
    luminanceStd: std,
    frameMeans: means,
    maxAdjacentTileDelta: maxTileDelta,
    blackOrBrightTiles,
    invalidFinalAcrossFrames: invalid,
    calmRaw,
    calmFinal,
    tideRaw,
    tideFinal: {
      invalid: tide.invalid,
      mean: tide.mean,
      peak: tide.peak
    },
    tideEnvelope: U.uTide.value,
    splat,
    renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)
  };
};
