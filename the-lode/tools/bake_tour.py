"""Photograph the working mine for WebGL-free browsers, with object-space annotations."""
import argparse
import base64
from functools import partial
from http.server import ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import tempfile
import threading

from playwright.sync_api import sync_playwright
from serve import Handler

ROOT = Path(__file__).resolve().parents[1]
OPENING_TIME = 20.0
# Keep these aspect ratios identical to the two live-action opening films.
FORMATS = [('orbit', 'o', 60, (1056, 660), (1280, 800)),
           ('portrait', 'p', 24, (528, 1056), (600, 1200))]
FIXED_VIEWS = {'pit': ([-17,115,171], [-86,-27,-17]), 'south': ([106,113,292], [-12,-2,146]),
               'plan': ([5,692,.01], [5,-18,0])}
NAMED_VIEWS = {'watch':'watch', 'mast':'mast', 'harbor':'harbor', 'hab':'hab', 'salvage':'salvage',
               'face':'face', 'hull':'hull', 'yard':'yard', 'wide':'sky'}
DETAIL_TIMES = [(OPENING_TIME, ('wide', 'plan', 'pit', 'south')),
                (25.3, ('watch', 'mast', 'hull', 'yard', 'hab', 'face')),
                (36.0, ('harbor',)), (39.0, ('salvage',))]

CAPTURE = """([position, target, detail]) => {
  const a=window.__mine,s=a.sys,V=a.T.Vector3;
  a.camera.position.fromArray(position); a.controls.target.fromArray(target); a.controls.update(0);
  a.camera.updateMatrixWorld(true); a.draw(0);
  if (a.fatal) throw Error(a.fatal);
  const image=a.renderer.domElement.toDataURL('image/webp', .86).split(',')[1];
  const marker=(part, name)=>a.layout[part]?.markers?.[name] ? a.mark(part,name) : null;
  const midpoint=(part,from,to)=>{const x=marker(part,from),y=marker(part,to);return x&&y?x.lerp(y,.5):null;};
  const axis=s.towerMotion?.axes?.[0];
  const hatch=marker('fleet','fr_hatch');
  if(hatch && s.freighter?.ship) s.freighter.ship.localToWorld(hatch);
  const towerWatch=midpoint('habitat','watch_hab_a','watch_hab_b');
  const mastWatch=midpoint('pit','watch_mast_a','watch_mast_b');
  const slabs=detail==='face' ? (s.rockfall?.plates||[]).filter(p=>p.mode==='sliding') : [];
  const movingSlab=slabs.find(p=>{const u=p.p.clone().project(a.camera);return Math.abs(u.x)<.7 && Math.abs(u.y)<.7 && Math.abs(u.z)<1;});
  const sites=[
    ['Tower Watch','Two keep watch. A third patrols the 1.1 m rail.',towerWatch,'watch'],
    ['Crane Catwalk','A maintenance crew crosses between the trusses.',mastWatch,'mast'],
    ['Tuned Counterweights','One weight rises as the other falls.',axis?.body?.getWorldPosition(new V()),'watch'],
    ['Work Barge','Thrusters trim the barge. Winches pay out both lines.',s.harborFlight?.position,'harbor'],
    ['Suspended Cable Drum','The drum swings sideways on two taut lines.',s.harborFlight?.loadPosition,'harbor'],
    ['Salvage Beam','Between winches, the loose beam tumbles in vacuum.',s.salvage?.position,'salvage'],
    ['Bench Collapse',movingSlab ? `${slabs.length} slabs broke loose and are sliding to the next bench.` : 'The wheel undercuts the face. Slabs slide one bench down.',movingSlab?.p||s.rockfall?.face,'face'],
    detail==='hull' ? ['Cargo Hold','The open belly hatch gathers ore thrown up from below.',hatch||s.freighter?.ship?.position,'hull'] :
                     ['Freighter','The freighter holds its hatch over the rising ore.',s.freighter?.ship?.position,'hull'],
    ['Axle Shop','A crew repairs a detached axle in the service pit.',marker('fill','wheel_service_pit'),'yard'],
    ['The Lode','The black crown pulls inward with a 1/r field.',new V(-78,-62,-12),'pit'],
    ['Bucket-Wheel Excavator','Fourteen buckets cut into the working face.',marker('bwe','bwe_wheel_axis'),'face'],
    ['The Sling','The launcher corrects its aim as gravity shifts.',marker('bwe','sling_mouth'),'pit'],
    ['Habitat Ring','Pressurized corridors link the rotating quarters.',new V(116,56,-115),'hab'],
    ['Water Reclamation','Heat exchangers return water to the crew quarters.',marker('habitat','hab_reclaim'),'hab'],
    ['The Crucible','Surface tension ripples a free-floating ball of metal.',s.crucible?.center||marker('fill','crucible'),'south'],
    ['Suspension Bridge','A loaded train twists the deck and pulls it down.',midpoint('port','bridge_w','bridge_e')],
    ['The Mitt','A capture field slows ore over the hopper mouth.',marker('plant','mitt_mouth')],
    ['Ore Vortex','Ore spirals up from the pit floor.',midpoint('pit','tractor_head','tractor_foot'),'pit'],
    ['The Whip','The track bends back. The ore keeps climbing.',marker('rail','whip_crest')],
    ['The Updraft','Ore falls upward into the bend at the shaft head.',midpoint('plant','updraft_base','updraft_top')],
    ['Pulse Jig','Each pulse lifts pale waste above the darker ore.',marker('plant','jig')],
    ['Tailings Fall','Tailings curl beneath the edge of the disc.',marker('plant','waste_out')],
    ['The Maw','The rollers catch rock carried along the jib.',marker('pit','maw'),'mast'],
    ['Dock Crane','An off-center load hangs from two cables.',s.crane?.pivot?.p],
    ['South Rim Wreck','Cutters strip the ribs of an old freighter.',marker('fill','wreck_spine'),'south'],
    ['Moored Boulder','A lift field holds the boulder against its chain.',s.moorings?.stones?.[0]?.body?.p,'pit'],
    ['Gravity Wall','Haul trucks drive straight up the rock face.',marker('pit','wall_mid'),'pit']
  ];
  if (detail) sites.sort((l,r)=>Number(r[3]===detail)-Number(l[3]===detail));
  const labels=[];
  for (const [title,text,point] of sites) {
    if (!point) continue;
    const p=point.clone().project(a.camera);
    if (Math.abs(p.x)<1 && Math.abs(p.y)<1 && Math.abs(p.z)<1)
      labels.push([title,text,+((1+p.x)/2).toFixed(5),+((1-p.y)/2).toFixed(5)]);
  }
  return {image,labels,time:+a.time.toFixed(4)};
}"""


def bake(page, out):
    manifest = {'openingTime': OPENING_TIME, 'orbit': [], 'portrait': [], 'views': {}}
    page.wait_for_function('window.__mine?.ready || window.__mine?.fatal')
    if error := page.evaluate('window.__mine.fatal || window.__mine.missingParts?.join(",")'):
        raise RuntimeError(error)
    # The sun and every simulated object stay fixed across a full turn around the model.
    page.evaluate('''()=>{const s=__mine.renderer.shadowMap;s.autoUpdate=false;s.needsUpdate=true;}''')

    def photograph(stem, position, target, size, epoch, detail=None):
        shot = page.evaluate(CAPTURE, [position, target, detail]); file = stem+'.webp'
        if abs(shot['time'] - epoch) > .001:
            raise RuntimeError(f"{file} rendered at {shot['time']}s, expected {epoch}s")
        image = base64.b64decode(shot['image'], validate=True)
        if image[8:12] != b'WEBP' or len(image) < 9000:
            raise ValueError('Incomplete browser image: '+file)
        (out/file).write_bytes(image)
        return {'image': file, 'time': shot['time'], 'width': size[0], 'height': size[1], 'labels': shot['labels']}

    def resize(size):
        page.set_viewport_size({'width':size[0], 'height':size[1]})
        page.wait_for_function('''s=>Math.abs(__mine.camera.aspect-s[0]/s[1])<.00001 &&
            __mine.renderer.domElement.width===s[0] && __mine.renderer.domElement.height===s[1]''', arg=size)

    named_cam = '''key=>{const a=__mine;a.setView(key,false);return [a.camera.position.toArray(),a.controls.target.toArray()];}'''
    for key, prefix, count, size, _ in FORMATS:
        resize(size)
        position, target = page.evaluate(named_cam, 'home')
        dx, dz = position[0]-target[0], position[2]-target[2]
        for i in range(count):
            angle = math.tau*i/count
            camera=[target[0]+dx*math.cos(angle)+dz*math.sin(angle), position[1],
                    target[2]+dz*math.cos(angle)-dx*math.sin(angle)]
            manifest[key].append(photograph(f'{prefix}{i:02}',camera,target,size,OPENING_TIME))
            if i % 10 == 0:
                print(f'{key} {i+1}/{count}', flush=True)

    for epoch, names in DETAIL_TIMES:
        page.evaluate('''t=>{ const a=__mine, steps=Math.round((t-a.time)*60);
          if (steps<0) throw Error('Cannot rewind a running mine');
          a.step(steps); a.sim.frame(0); a.renderer.shadowMap.needsUpdate=true;
        }''', epoch)
        for key, _prefix, _count, _orbit_size, detail_size in FORMATS:
            resize(detail_size)
            for name in names:
                if name in FIXED_VIEWS:
                    camera, look = FIXED_VIEWS[name]
                else:
                    camera, look = page.evaluate(named_cam, NAMED_VIEWS[name])
                photo=photograph(('v-' if key=='portrait' else '')+name,camera,look,detail_size,epoch,name)
                if key=='portrait':manifest['views'][name]['portrait']=photo
                else:manifest['views'][name]=photo
        print(f"{epoch:g}s details complete: {', '.join(names)}",flush=True)
    (out/'views.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--input',type=Path,default=ROOT/'web')
    args.add_argument('--output',type=Path,default=ROOT/'web'/'assets'/'tour')
    args.add_argument('--browser',default=os.getenv('LODE_CHROME'))
    args.add_argument('--software',action='store_true',default=bool(os.getenv('LODE_SW')))
    args.add_argument('--port',type=int,default=0)
    opt=args.parse_args()
    flags=['--disable-dev-shm-usage','--enable-unsafe-swiftshader']
    if opt.software:flags.extend(['--use-gl=angle','--use-angle=swiftshader'])
    out=opt.output.resolve();out.mkdir(exist_ok=True,parents=True)
    with ThreadingHTTPServer(('127.0.0.1',opt.port),partial(Handler,directory=str(opt.input.resolve()))) as http, \
            tempfile.TemporaryDirectory(dir=out.parent) as stage, sync_playwright() as pw:
        threading.Thread(target=http.serve_forever,daemon=True).start()
        browser=pw.chromium.launch(executable_path=opt.browser,args=flags)
        try:
            page=browser.new_page(viewport={'width':1056,'height':660},device_scale_factor=1)
            page.set_default_timeout(480000)
            page.goto(f'http://127.0.0.1:{http.server_port}/?ff={OPENING_TIME:g}&manual=1&rot=0&tags=0&dpr=1&shadow=1024',wait_until='domcontentloaded')
            bake(page,Path(stage))
        finally:browser.close()
        for image in Path(stage).glob('*.webp'): image.replace(out/image.name)
        (Path(stage)/'views.json').replace(out/'views.json')


if __name__=='__main__':
    main()
