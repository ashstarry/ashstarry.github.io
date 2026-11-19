const requested = new URLSearchParams(location.search);
const tourLink = document.querySelector('#boot-tour');
if (tourLink && requested.has('focus')) {
  const tourParams = new URLSearchParams({ view: 'tour', focus: requested.get('focus') });
  tourLink.search = tourParams.toString();
}
const canvas = document.createElement('canvas');
let graphics = null;
function probeGraphics() {
  if (requested.get('view') === 'tour') return;
  try {
    graphics = canvas.getContext('webgl2',{ antialias:false, alpha:true, powerPreference:'high-performance' });
  } catch { /* the tour is available when graphics contexts are disabled */ }
}
function realtimeAvailable() {
  if (!graphics || !graphics.getExtension('EXT_color_buffer_float')) return false;
  if (requested.get('view') === 'live' || ['test','ff','manual','parts','cam','tgt','dpr'].some(k => requested.has(k))) return true;
  const vendor = graphics.getExtension('WEBGL_debug_renderer_info');
  const device = graphics.getParameter(vendor ? vendor.UNMASKED_RENDERER_WEBGL : graphics.RENDERER);
  return !/SwiftShader|llvmpipe|softpipe|software rasterizer|Microsoft Basic Render/i.test(device);
}

async function openMine() {
  const boot = window.mineBoot;
  boot.progress(2,'Starting graphics');
  await boot.paint();
  probeGraphics();
  if (realtimeAvailable()) {
    boot.mode('live');
    boot.progress(5,'Loading the 3D engine');
    const { startMine } = await import('./main.js');
    await startMine(canvas, graphics);
  } else {
    if (graphics) {
      document.documentElement.dataset.softwareRenderer = 'true';
      graphics.getExtension('WEBGL_lose_context')?.loseContext();
    }
    boot.mode('tour');
    boot.progress(8,'Loading the tour');
    const { startTour } = await import('./tour.js');
    await startTour();
  }
}

openMine().catch(error => {
  window.mineBoot.fail('MINE OFFLINE','Loading stopped. Reload to try again.');
  console.error(error);
});
