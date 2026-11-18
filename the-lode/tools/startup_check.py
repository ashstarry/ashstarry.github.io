"""Cold-start regression check. Set LODE_CHROME to a Chromium executable for an offline run."""
import argparse
import asyncio
import io
import json
import os
import threading
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.async_api import async_playwright
from serve import server


TRACE = """addEventListener('DOMContentLoaded',() => {
  const bar=document.querySelector('#boot-track');
  window.checkStartup=[+bar.getAttribute('aria-valuenow')];
  new MutationObserver(()=>checkStartup.push(+bar.getAttribute('aria-valuenow'))).observe(bar,{attributes:true});
  const finish=mineBoot.finish;
  mineBoot.finish=()=>{
    if(window.__mine)window.__mine.paused=true;
    finish();
  };
});"""


def composition(cover, live):
    def grayscale(data):
        pic = Image.open(io.BytesIO(data)).convert('L')
        w, h = pic.size
        # Exclude the bottom HUD and measure actual structures across the mine.
        area = pic.crop((int(.04*w),int(.08*h),int(.96*w),int(.86*h)))
        return np.asarray(area.resize((360,240),Image.Resampling.LANCZOS),dtype=float)
    a, b = grayscale(cover), grayscale(live)
    return {'correlation': round(float(np.corrcoef(a.ravel(),b.ravel())[0,1]),5),
            'mean_difference_255': round(float(np.abs(a-b).mean()),3)}


async def run(args, origin):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'), args=[
            '--disable-dev-shm-usage','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        errors, results = [], {}
        for name, width, height, mode, gesture in [
            ('desktop',1600,1000,'live',False),('phone',390,844,'live',False),
            ('tablet',944,920,'live',False),('wide',1440,810,'live',False),
            ('drag',800,500,'live',True),('guide-wide',1440,900,'tour',False),
            ('guide-phone',390,844,'tour',False),('quiet-phone',390,844,'reduced',False)]:
            if args.case and name not in args.case:
                continue
            context = await browser.new_context(viewport={'width':width,'height':height},
                                                device_scale_factor=3 if width<500 else 1,has_touch=width<500,is_mobile=width<500,
                                                reduced_motion='reduce' if mode=='reduced' else 'no-preference')
            await context.add_init_script(script=TRACE)
            page=await context.new_page()
            page.set_default_timeout(240000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            files=[]
            page.on('request',lambda req:files.append(req.url))
            release, entered=asyncio.Event(),asyncio.Event()
            async def hold(route):
                entered.set()
                await release.wait()
                await route.continue_()
            await page.route('**/assets/tex/rock_n.png' if mode=='live' else '**/tour/views.json*',hold)
            # Only force the software GPU for the live cases. Automatic selection
            # should bring an ordinary browser backed by SwiftShader to the guide.
            await page.goto(origin+('/?view=live' if mode=='live' else '/'),wait_until='domcontentloaded')
            await asyncio.wait_for(entered.wait(),180)
            await page.wait_for_function("""document.querySelector('#op-plate').naturalWidth > 0 &&
                getComputedStyle(document.querySelector('#op-plate')).visibility==='visible'""")
            bar=page.get_by_role('progressbar')
            await page.wait_for_function("""n=>+document.querySelector('#boot-track').getAttribute('aria-valuenow')>=n""",
                                         arg=63 if mode=='live' else 18)
            pct=int(await bar.get_attribute('aria-valuenow'))
            await page.wait_for_timeout(240)
            assert int(await bar.get_attribute('aria-valuenow'))<100 and await bar.is_visible()
            meta=await page.locator('#op-plate').evaluate("e=>[e.naturalWidth,e.naturalHeight,e.currentSrc.split('/').pop()]")
            assert meta[0]>=1000 and not any('.mp4' in f for f in files),files[-6:]
            cover=await page.screenshot(path=str(args.output/(name+'-loading.png')))
            if gesture:
                await page.mouse.move(325,213)
                await page.mouse.down(); await page.mouse.move(429,215,steps=8); await page.mouse.up()
                await page.mouse.wheel(0,-110)
                await page.wait_for_function("!document.querySelector('#op-turn').hidden && mineOpening.zoom>1")
            release.set()
            await page.wait_for_function("document.querySelector('#boot').hidden || document.querySelector('#boot').classList.contains('fail')")
            assert await page.locator('#boot').get_attribute('class')!='fail',await page.locator('#boot').inner_text()
            trace=await page.evaluate('checkStartup')
            assert trace==sorted(trace) and trace[-1]==100,trace
            result={'blocked_percent':pct,'plate':meta,'distinct_progress_values':len(set(trace))}
            if mode=='live':
                result['live']=await page.evaluate("""()=>({fatal:__mine.fatal,missing:__mine.missingParts,time:__mine.time,...__mine.metrics.opening})""")
                info=result['live']
                assert not info['fatal'] and not info['missing'] and abs(info['time']-20)<.0001
                if width<500: assert info['width']>=int(width*1.5) and info['width']*info['height']<=1250000
                assert (abs(info['yaw'])>.1 and info['zoom']>1) if gesture else info['yaw']==0 and info['zoom']==1
                assert not any('.mp4' in f for f in files)
                live=await page.screenshot(path=str(args.output/(name+'-ready.png')))
                if not gesture:
                    result['registration']=composition(cover,live)
                    assert result['registration']['correlation']>.96 and result['registration']['mean_difference_255']<7,result
                await page.keyboard.press('l')
                assert await page.evaluate('__mine.tagsOn')
            else:
                video=page.locator('.tour-opening')
                if mode=='reduced':
                    assert not any('.mp4' in f for f in files),files
                    assert await page.locator('[data-transport]').inner_text()=='Play'
                else:
                    await page.wait_for_function("document.querySelector('.tour-opening').currentTime>.16")
                    result['playing']=await video.evaluate('v=>!v.paused')
                    assert result['playing']
                await page.keyboard.press('ArrowRight')
                await page.wait_for_function("document.querySelector('.tour-stage').dataset.view==='orbit' && document.querySelector('.tour-plate img').naturalWidth>0")
            results[name]=result
            print(name,json.dumps(result,ensure_ascii=False),flush=True)
            await context.close()
        await browser.close()
        assert not errors,errors
        (args.output/'startup.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with server(0) as srv:
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        asyncio.run(run(args,f'http://127.0.0.1:{srv.server_port}'))
