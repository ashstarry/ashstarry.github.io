"""Photograph the fifteen inspection views from the running WebGL scene."""
import argparse
import json
import os
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from serve import server

ROOT = Path(__file__).resolve().parents[1]
VIEWS = [
    ('04-wide-dark-star', [485,525,1015], [5,-64,0], False),
    ('05-south-foreground', [106,113,292], [-12,-2,146], False),
    ('06-pit-close', [-17,115,171], [-86,-27,-17], False),
    ('07-top-down-labelled', [5,692,0.01], [5,-18,0], True),
]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8137)
    parser.add_argument('--output',type=Path,default=ROOT/'qa')
    args=parser.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    stats={}
    overlaps={}
    with server(args.port) as srv, sync_playwright() as pw:
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        flags=['--disable-dev-shm-usage','--enable-unsafe-swiftshader']
        if os.getenv('LODE_SW'): flags+=['--use-gl=angle','--use-angle=swiftshader']
        browser=pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'),args=flags)
        pg=browser.new_page(viewport={'width':1600,'height':1000},device_scale_factor=1)
        errors=[]
        pg.on('pageerror',lambda e:errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{args.port}/?ff=20&manual=1&rot=0&dpr=1',wait_until='domcontentloaded',timeout=600000)
        pg.wait_for_function('window.__mine?.ready || window.__mine?.fatal',timeout=600000)
        if error:=pg.evaluate('__mine.fatal'): raise RuntimeError(error)
        pg.evaluate("document.querySelector('#boot').style.display='none'")
        def capture(name,pos,target,tags,focus=None):
            pg.evaluate("""([p,t,tags,focus])=>{const a=window.__mine;
              if(focus) a.setView(focus,false);
              else {a.setView('home',false);a.camera.position.fromArray(p);a.controls.target.fromArray(t);a.controls.update(0);}
              a.camera.updateMatrixWorld(true);a.tagsOn=tags;a.draw(0);a.updateHUD();}""",[pos,target,tags,focus])
            pg.wait_for_timeout(450)
            stats[name]=pg.locator('.tag').evaluate_all("tags=>tags.filter(el=>getComputedStyle(el).opacity>.9).map(el=>el.querySelector('b').textContent)")
            overlaps[name]=pg.locator('.tag').evaluate_all('tags=>{const rects=tags.filter(e=>getComputedStyle(e).opacity>.9).map(e=>e.getBoundingClientRect());let n=0;for(let i=0;i<rects.length;i++)for(let j=0;j<i;j++){const a=rects[i],b=rects[j];if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)n++;}return n;}')
            if overlaps[name]: raise RuntimeError(f'Overlapping labels in {name}')
            pg.screenshot(path=str(out/(name+'.jpg')),type='jpeg',quality=93,timeout=600000)
            print(name,len(stats[name]),flush=True)
        def advance_to(second):
            pg.evaluate('t => { const a=__mine; a.step(Math.round((t-a.time)*60)); }',second)
        capture('01-panorama',None,None,False,'home')
        capture('02-panorama-labelled',None,None,True,'home')
        advance_to(25.3)
        capture('08-working-face',None,None,False,'face')
        advance_to(26)
        front=pg.evaluate('({count:__mine.sys.tides.count,radius:__mine.U.uWave.value.x,strength:__mine.U.uTide.value})')
        if front['count']!=1 or not 130<front['radius']<180 or front['strength']<.2:
            raise RuntimeError(f'First tide missed the active decks at 26 seconds: {front}')
        capture('03-panorama-tide',None,None,False,'home')
        advance_to(45)
        for view in VIEWS:capture(*view)
        for name,key in [('09-salvage','salvage'),('10-freighter','hull'),('11-wheel-workshop','yard'),('12-habitat','hab'),('13-watch','watch'),('14-mast','mast'),('15-harbor','harbor')]:
            capture(name,None,None,False,key)
        if error:=pg.evaluate('__mine.fatal'): raise RuntimeError(error)
        print(json.dumps({'firstTide':front,'visibleLabels':stats,'labelOverlaps':overlaps,'pageErrors':errors},ensure_ascii=False),flush=True)
        if errors: raise RuntimeError('Browser raised an error while capturing the mine')
        browser.close()
if __name__=='__main__':
    main()
