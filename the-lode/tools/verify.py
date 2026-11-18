#!/usr/bin/env python3
"""Inspect the real viewer on loopback. Playwright is an optional QA dependency."""
import argparse
import json
import os
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from serve import server


ROOT = Path(__file__).resolve().parents[1]
PHYSICS_BATCH = """() => {
  const ms = [];
  for (let i = 0; i < 30; i++) {
    const start = performance.now();
    window.__mine.step(1);
    ms.push(performance.now() - start);
  }
  return ms;
}"""
RENDER_BENCH = """() => {
  const app = window.__mine, renderer = app.renderer, gl = renderer.getContext();
  const extension = gl.getExtension('WEBGL_debug_renderer_info');
  const sample = new Uint8Array(4), ms = [];
  const previous = renderer.info.autoReset;
  renderer.info.autoReset = false;
  for (let i = 0; i < 3; i++) {
    renderer.info.reset();
    const start = performance.now();
    app.step(1);
    app.draw(1/60);
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, sample);
    ms.push(performance.now() - start);
  }
  const result = {
    width: renderer.domElement.width, height: renderer.domElement.height,
    dpr: renderer.getPixelRatio(), msaa: app.composer.renderTarget1.samples,
    shadow: app.sun.shadow.mapSize.x,
    renderer: gl.getParameter(extension ? extension.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
    drawCalls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
    frameMilliseconds: ms, fps: 3000 / ms.reduce((a,b) => a+b,0)
  };
  renderer.info.autoReset = previous;
  return result;
}"""


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bench', action='store_true')
    parser.add_argument('--port', type=int, default=8137)
    parser.add_argument('--url', default='?ff=45&rot=0&manual=1')
    parser.add_argument('--shot', default='qa/panorama.png')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=1000)
    parser.add_argument('--script')
    parser.add_argument('--timeout', type=int, default=600)
    return parser.parse_args()


def stats(values):
    samples = sorted(values)
    return dict(mean=sum(samples) / len(samples), p50=samples[len(samples) // 2],
                p95=samples[min(len(samples) - 1, int(len(samples) * .95))], max=samples[-1])


def benchmark(page, outcome):
    session = page.context.new_cdp_session(page)
    session.send('Performance.enable', {'timeDomain': 'threadTicks'})
    page.evaluate('window.__mine.renderer.getContext().finish()')

    def cpu_seconds():
        metrics = session.send('Performance.getMetrics')['metrics']
        return next(m['value'] for m in metrics if m['name'] == 'ThreadTime')

    cpu, wall = [], []
    for _ in range(24):
        before = cpu_seconds()
        wall.extend(page.evaluate(PHYSICS_BATCH))
        cpu.append((cpu_seconds() - before) * 1000 / 30)
    outcome['physicsBenchmark'] = dict(fromSecond=round(outcome.get('seconds', 0)),
        steps=len(wall), stepsPerCpuSample=30, mainThreadCpuMs=stats(cpu),
        singleStepWallMs=stats(wall))
    outcome['renderBenchmark'] = page.evaluate(RENDER_BENCH)


def main():
    args = arguments()
    with server(args.port) as srv, sync_playwright() as playwright:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        flags = ['--no-sandbox', '--disable-dev-shm-usage', '--enable-unsafe-swiftshader']
        if os.environ.get('LODE_SW'):
            flags.extend(['--use-gl=angle', '--use-angle=swiftshader'])
        browser = playwright.chromium.launch(executable_path=os.getenv('LODE_CHROME'), args=flags)
        page = browser.new_page(viewport=dict(width=args.width, height=args.height),
                                device_scale_factor=1)
        messages = []
        page.on('pageerror', lambda error: messages.append(str(error)))

        def console(message):
            if message.type in ('warning', 'error') and 'ReadPixels' not in message.text:
                messages.append(message.type + ' ' + message.text)

        page.on('console', console)
        target = f'http://127.0.0.1:{args.port}/' + args.url
        page.goto(target, wait_until='domcontentloaded', timeout=args.timeout * 1000)
        try:
            page.wait_for_function('window.__mine?.ready || window.__mine?.fatal',
                                   timeout=args.timeout * 1000)
        except Exception:
            print('Readiness', page.locator('#boot').inner_text(), messages[-8:], flush=True)
            raise
        if error := page.evaluate('window.__mine.fatal'):
            raise RuntimeError(error)
        page.evaluate("document.querySelector('#boot').style.display='none'")
        outcome = page.evaluate(Path(args.script).read_text()) if args.script else {}
        if args.bench:
            benchmark(page, outcome)
        if args.shot:
            dest = ROOT / args.shot
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(dest), timeout=args.timeout * 1000)
        print('RESULT', json.dumps(dict(page=target, outcome=outcome, messages=messages),
                                   ensure_ascii=False), flush=True)
        browser.close()


if __name__ == '__main__':
    main()
