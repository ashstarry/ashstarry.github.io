"""Record the three mine events at their original simulation speed. Requires ffmpeg and Playwright."""
import argparse
import base64
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import threading

from playwright.sync_api import sync_playwright
from serve import server

ROOT = Path(__file__).resolve().parents[1]
FPS = 12
CLIPS = [
    ('The-Lode-Salvage', 'salvage', 4, 17),
    ('The-Lode-Tide', 'home', 17, 35),
    ('The-Lode-Rockfall', 'face', 22, 31),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8137)
    parser.add_argument('--output', type=Path, default=ROOT / 'qa')
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    with server(args.port) as srv, sync_playwright() as pw, ExitStack() as stack:
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        flags = ['--disable-dev-shm-usage', '--enable-unsafe-swiftshader']
        if os.getenv('LODE_SW'):
            flags.extend(['--use-gl=angle', '--use-angle=swiftshader'])
        browser = pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'), args=flags)
        page = browser.new_page(viewport={'width':768, 'height':480}, device_scale_factor=1)
        page.set_default_timeout(900000)
        page.goto(f'http://127.0.0.1:{srv.server_port}/?ff=4&manual=1&rot=0&dpr=1&shadow=1024',wait_until='domcontentloaded')
        page.wait_for_function('window.__mine?.ready || window.__mine?.fatal')
        error = page.evaluate('__mine.fatal')
        if error:
            raise RuntimeError(error)
        processes = {}
        for name, _, _, _ in CLIPS:
            command = ['ffmpeg','-v','error','-y','-f','image2pipe','-c:v','mjpeg','-framerate',str(FPS),
                       '-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                       '-movflags','+faststart','-threads','1',str(out / (name + '.mp4'))]
            processes[name] = stack.enter_context(subprocess.Popen(command,stdin=subprocess.PIPE))
        for frame in range(4*FPS,35*FPS):
            for name, key, start, stop in CLIPS:
                if start*FPS <= frame < stop*FPS:
                    shot = page.evaluate("""key => {
                      const a = window.__mine;
                      if(a.focus !== key) a.setView(key,false);
                      a.camera.updateMatrixWorld(true);
                      a.draw(0);
                      return a.renderer.domElement.toDataURL('image/jpeg',.91).split(',')[1];
                    }""", key)
                    processes[name].stdin.write(base64.b64decode(shot))
            page.evaluate('__mine.step(5)')
            if frame % (3*FPS) == 0:
                print('Recorded simulation second',frame//FPS,flush=True)
        for proc in processes.values():
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError('Video encoding failed')
        print('Recorded', [p[0] for p in CLIPS], flush=True)
        browser.close()


if __name__=='__main__':
    main()
