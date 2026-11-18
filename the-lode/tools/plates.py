"""Photograph each responsive loading plate through the live WebGL camera."""
import argparse
import base64
import io
import os
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from serve import server


def main():
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=project / 'web/assets/opening')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    flags = ['--enable-unsafe-swiftshader', '--disable-dev-shm-usage']
    if os.getenv('LODE_SW'):
        flags.extend(['--use-gl=angle', '--use-angle=swiftshader'])
    with server(0) as srv, sync_playwright() as pw:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        browser = pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'), args=flags)
        page = browser.new_page(viewport={'width': 800, 'height': 500}, device_scale_factor=1)
        page.set_default_timeout(600000)
        page.goto(f'http://127.0.0.1:{srv.server_port}/?manual=1&rot=0&dpr=1&shadow=2048', wait_until='domcontentloaded')
        page.wait_for_function('window.__mine?.ready || window.__mine?.fatal')
        if page.evaluate('__mine.fatal || __mine.missingParts.length'):
            raise RuntimeError('Incomplete live scene')
        if not page.evaluate('!!window.minePlates'):
            page.add_script_tag(url='./src/plates.js')
        shots = page.evaluate('minePlates.shots')
        for shot in shots:
            page.set_viewport_size({'width': shot['width'], 'height': shot['height']})
            page.wait_for_function('__mine.camera.aspect === innerWidth / innerHeight')
            data = page.evaluate("""async shot => {
              const {homeForAspect} = await import('./src/views.js');
              const app = window.__mine, home = homeForAspect(shot.bearing);
              app.camera.position.fromArray(home.eye);
              app.controls.target.fromArray(home.target);
              app.controls.update(0);
              app.camera.zoom = shot.zoom;
              app.camera.updateProjectionMatrix();
              app.camera.updateMatrixWorld(true);
              app.draw(0);
              if(app.fatal || Math.abs(app.time-20) > 1e-5) throw Error('Invalid entry frame');
              return app.renderer.domElement.toDataURL('image/png').split(',')[1];
            }""", shot)
            image = Image.open(io.BytesIO(base64.b64decode(data))).convert('RGB')
            assert image.size == (shot['width'], shot['height'])
            dest = args.output / ('plate-' + shot['name'] + '.webp')
            image.save(dest, quality=94, method=6)
            print(f'{dest.name} {image.width} × {image.height}, {dest.stat().st_size} bytes', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
