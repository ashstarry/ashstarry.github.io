"""Record opening views, the quiet production shift, or the tour's crane watch stage."""

import argparse
import base64
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright
from serve import server


ROOT = Path(__file__).resolve().parents[1]
SHOTS = {
    'wide': ((896, 560), 'intro-wide', 'home'),
    'tall': ((480, 960), 'intro-tall', 'home'),
    'shift-wide': ((896, 560), 'shift-wide', 'home'),
    'shift-tall': ((480, 960), 'shift-tall', 'home'),
    'mast-watch': ((640, 400), 'mast-watch', 'mast'),
}
OPENING_SHOTS = ('wide', 'tall')
SHIFT_SHOTS = ('shift-wide', 'shift-tall')
OUTPUT = ROOT / 'web' / 'assets' / 'opening'

# Read only the WebGL backbuffer. The renderer applies the same tone mapping and
# post-processing as the live view, while HTML controls stay outside the camera.
SHOOT = """([steps, frameTime]) => {
  const app = window.__mine;
  if (steps) app.step(steps);
  app.camera.updateMatrixWorld(true);
  app.draw(frameTime);
  if (app.fatal) throw Error(app.fatal);
  return app.renderer.domElement.toDataURL('image/jpeg', .94).split(',')[1];
}"""

RECORD_STATE = """() => {
  const a = window.__mine;
  return {
    time: a.time,
    eye: a.camera.position.toArray(),
    target: a.controls.target.toArray(),
    fov: a.camera.fov,
    focus: a.focus,
    tideCount: a.sys.tides?.count ?? 0,
    tideStart: a.sys.tides?.count ? a.sys.tides.start : null,
    tide: a.U.uTide.value,
    gravityFrontRadius: a.sim.field.wave.r,
    orbitingRocks: a.sys.wheel?.orbiters ?? 0,
    breakerPhase: a.sys.breaker?.phase,
    impacts: a.sys.breaker?.impacts,
    fragments: a.sys.breaker?.fragments.length,
    railReleased: a.sys.rail?.released ?? 0,
    freighterReceived: a.sys.freighter?.received ?? 0,
    firstFreighterReceipt: a.sys.freighter?.firstReceived ?? null,
    harborPhase: a.sys.harborFlight?.phase,
    towerCrew: a.sys.watchCrew?.count
  };
}"""

RENDER_FEATURES = """() => {
  const a = window.__mine, gl = a.renderer.getContext();
  const programs = a.renderer.info.programs.map(p => p.program).filter(Boolean);
  const linked = name => programs.some(p => gl.getUniformLocation(p, name) !== null);
  const sky = a.sky.mat.fragmentShader;
  return {
    linkedPrograms: programs.length,
    tideFrontUniform: linked('uWave'),
    reflectedColorEchoUniform: linked('uEcho'),
    towerColorBandUniform: linked('uRise'),
    resonanceSystem: Boolean(a.sys.resonance),
    backgroundAnnulusShader: sky.includes('ringDust('),
    passingDustCloudShader: sky.includes('cloudTransmission(')
  };
}"""


def options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--shot', '--orientation', choices=['both', 'shift', *SHOTS], default='both')
    parser.add_argument('--ff', type=float, help='Simulation seconds at frame zero. Default uses the live home view.')
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--fps', type=int, choices=(10, 12, 15, 20, 30, 60))
    parser.add_argument('--scale', type=float, default=1, help='Scale both dimensions for diagnostic captures.')
    parser.add_argument('--shadow', type=int, default=1024)
    parser.add_argument('--port', type=int, default=8191)
    args = parser.parse_args()
    start, duration, rate, destination = None, 18, 15, OUTPUT
    if args.shot == 'mast-watch':
        start, duration, rate, destination = 25.3, 6.75, 12, OUTPUT.parent / 'tour'
    elif args.shot == 'shift' or args.shot in SHIFT_SHOTS:
        start, duration, rate, destination = 38, 24, 12, OUTPUT.parent / 'tour'
    if args.output is None:
        args.output = destination
    if args.ff is None:
        args.ff = start
    if args.seconds is None:
        args.seconds = duration
    if args.fps is None:
        args.fps = rate
    if args.seconds <= 0 or not 0 < args.scale <= 2:
        parser.error('Duration and scale must be positive; scale must be at most two.')
    return args


def verify_video(path, width, height, frames, fps):
    probe = subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,pix_fmt,codec_name,nb_frames,avg_frame_rate,duration',
        '-of', 'json', str(path)
    ])
    stream = json.loads(probe)['streams'][0]
    if not (stream['width'] == width and stream['height'] == height
            and stream['pix_fmt'] == 'yuv420p' and stream['codec_name'] == 'h264'
            and int(stream['nb_frames']) == frames and Fraction(stream['avg_frame_rate']) == fps
            and abs(float(stream['duration']) - frames / fps) < .002):
        raise RuntimeError(f'Incomplete opening movie: {stream}')
    # The browser can start displaying the first GOP while the rest downloads.
    with path.open('rb') as movie:
        while header := movie.read(8):
            size = int.from_bytes(header[:4], 'big')
            if size < 8 or header[4:8] == b'mdat':
                break
            if header[4:8] == b'moov':
                return stream
            movie.seek(size - 8, 1)
    raise RuntimeError('The MP4 index must precede the media for progressive playback.')


def record(browser, origin, name, args, stage):
    dimensions, basename, focus = SHOTS[name]
    width, height = (max(2, 2 * round(d * args.scale / 2)) for d in dimensions)
    options = dict(viewport={'width': width, 'height': height}, device_scale_factor=1,
                   has_touch=name.endswith('tall'), is_mobile=name.endswith('tall'))
    dst = stage / basename
    params = dict(manual=1, tags=0, rot=0, dpr=1, shadow=args.shadow, focus=focus)
    if args.ff is not None:
        params['ff'] = args.ff
    frame_count = max(1, round(args.seconds * args.fps))
    steps_per_frame = 60 // args.fps
    with browser.new_context(**options) as context:
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.set_default_timeout(900000)
        page.goto(origin + '/?' + urlencode(params), wait_until='domcontentloaded')
        page.wait_for_function('window.__mine?.ready || window.__mine?.fatal')
        if error := page.evaluate('window.__mine.fatal'):
            raise RuntimeError(error)
        missing = page.evaluate('window.__mine.missingParts')
        if missing:
            raise RuntimeError(f'Incomplete set: {missing}')
        command = [
            'ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(args.fps),
            '-c:v', 'mjpeg', '-i', 'pipe:0', '-an',
            '-vf', 'scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=full:out_range=tv:flags=accurate_rnd+full_chroma_int',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
            '-c:v', 'libx264', '-profile:v', 'high',
            '-pix_fmt', 'yuv420p', '-preset', 'fast', '-threads', '2', '-crf', '21',
            '-g', str(2 * args.fps), '-maxrate', '2300k', '-bufsize', '3500k',
            '-movflags', '+faststart', str(dst.with_suffix('.mp4'))
        ]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            try:
                timeline = []
                last_event = None
                for frame in range(frame_count):
                    dt = 1 / args.fps if frame else 0
                    jpeg = page.evaluate(SHOOT, [steps_per_frame if frame else 0, dt])
                    data = base64.b64decode(jpeg, validate=True)
                    if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
                        raise RuntimeError('Browser did not return a complete JPEG frame.')
                    state = page.evaluate(RECORD_STATE)
                    if frame == 0:
                        dst.with_suffix('.jpg').write_bytes(data)
                        first = state
                        features = page.evaluate(RENDER_FEATURES)
                    event = (state['tideCount'], state['breakerPhase'], state['railReleased'],
                             state['freighterReceived'] > 0)
                    if event != last_event or frame + 1 == frame_count:
                        timeline.append({key: state[key] for key in (
                            'time', 'tideCount', 'tideStart', 'tide', 'gravityFrontRadius', 'breakerPhase',
                            'impacts', 'fragments', 'railReleased', 'freighterReceived')})
                    last_event = event
                    encoder.stdin.write(data)
                    if frame % (3 * args.fps) == 0:
                        print(f'{name}: frame {frame + 1}/{frame_count}', flush=True)
                encoder.stdin.close()
                if encoder.wait() != 0:
                    raise RuntimeError('Encoding the opening failed.')
            except BaseException:
                encoder.kill()
                raise
        last = state
        expected_end = first['time'] + (frame_count - 1) / args.fps
        if errors or not math.isclose(last['time'], expected_end, abs_tol=1e-6):
            raise RuntimeError(f'Opening simulation discontinuity or browser error: {last}, {errors}')
    stream = verify_video(dst.with_suffix('.mp4'), width, height, frame_count, args.fps)
    return dict(first=first, last=last, timeline=timeline, rendering=features, media=stream,
                bytes=dst.with_suffix('.mp4').stat().st_size)


def main():
    args = options()
    args.output.mkdir(parents=True, exist_ok=True)
    flags = ['--disable-dev-shm-usage', '--enable-unsafe-swiftshader']
    if os.getenv('LODE_SW'):
        flags += ['--use-gl=angle', '--use-angle=swiftshader']
    groups = {'both': OPENING_SHOTS, 'shift': SHIFT_SHOTS}
    selected = groups.get(args.shot, (args.shot,))
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temp, server(args.port) as srv, sync_playwright() as pw:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        stage = Path(temp)
        results = {}
        for name in selected:
            browser = pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'), args=flags)
            try:
                result = record(browser, f'http://127.0.0.1:{srv.server_port}', name, args, stage)
            finally:
                browser.close()
            if results and abs(result['first']['time'] - results[selected[0]]['first']['time']) > 1e-6:
                raise RuntimeError('Landscape and portrait openings use different simulation times.')
            results[name] = result
            for ext in (('.mp4', '.jpg') if name in OPENING_SHOTS else ('.mp4',)):
                part = stage / (SHOTS[name][1] + ext)
                part.replace(args.output / part.name)
            print(name + ' complete ' + json.dumps(result), flush=True)
    print('OPENING ' + json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
