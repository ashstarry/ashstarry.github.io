"""Measure framing and opaque sightlines in the live mine's two home views."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from serve import server

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {'desktop': (1600, 1000), 'mobile': (390, 844)}

# A diagnostic pass on the same camera records the owner and the view-space depth
# of each opaque pixel. Originals of the static batches recover the owning part.
# Vertex positions, instancing, culling and sidedness all come from the live scene.
MEASURE = r"""async () => {
  const a = window.__mine, T = a.T, cam = a.camera, renderer = a.renderer;
  const { TAG } = await import('./src/physics/world.js');
  a.draw(0);
  a.scene.updateMatrixWorld(true);
  cam.updateMatrixWorld(true);
  const width = innerWidth, height = innerHeight, scene = new T.Scene();
  const owner = ['background','terrain','lode','habitat','habitat tower','pit','pit mast',
    'rail','plant','port','bwe','fill','freighter','hatch doors','fleet','rocks','ore','orbital debris','other'];
  const num = name => owner.includes(name) ? owner.indexOf(name) : owner.indexOf('other');
  const names = Object.keys(a.layout), covered = new Set(), materials = new Map();
  const fr = a.sys.freighter, origin = cam.position, identity = new T.Vector3();
  const crown = new T.Vector3(...a.layout.terrain.lode.slice(0,3));
  const radius = a.layout.terrain.lode[3], shaft = a.mark('habitat','spire_axis');
  const mast = a.mark('pit','maw'), tip = a.mark('pit','tractor_head');
  const crest = a.mark('rail','whip_crest'), armX=mast.x-tip.x, armZ=mast.z-tip.z;
  const bounds = {};
  const fmt = (v,d=2) => +v.toFixed(d);
  const visibleRanks = ['freighter','habitat tower','pit mast','whip crest'];
  for (const name of visibleRanks) bounds[name] = {l:Infinity,t:Infinity,r:-Infinity,b:-Infinity,vertices:0};

  function category(o, part) {
    if (o.material.name==='lode') return 'lode';
    let door=false;
    for (let p=o;p;p=p.parent) {
      if (p.name==='fr_door_l' || p.name==='fr_door_r') door=true;
      if (p===fr.ship) return door?'hatch doors':'freighter';
      if (!part && names.includes(p.name)) part=p.name;
    }
    if (part) return part;
    const defs=o.material.defines||{};
    if ('GRAIN' in defs) return 'ore';
    if ('ORBITAL' in defs) return 'orbital debris';
    return 'other';
  }
  function geometryBounds(o, group) {
    if(group==='hatch doors') group='freighter';
    if (!['freighter','habitat','pit','rail'].includes(group) || o.isInstancedMesh) return;
    const attr=o.geometry.getAttribute('position');
    for (let i=0;i<attr.count;i++) {
      const p=identity.fromBufferAttribute(attr,i).applyMatrix4(o.matrixWorld);
      let key=group;
      if (group==='habitat' && p.y>47 && (p.x-shaft.x)**2+(p.z-shaft.z)**2<51**2) key='habitat tower';
      if (group==='pit' && p.y>31) {
        const u=Math.max(0,Math.min(1,((p.x-tip.x)*armX+(p.z-tip.z)*armZ)/(armX**2+armZ**2)));
        if((p.x-mast.x)**2+(p.z-mast.z)**2<34**2 ||
           (p.x-tip.x-u*armX)**2+(p.z-tip.z-u*armZ)**2<11**2) key='pit mast';
      }
      if (group==='rail' && p.y>45 && (p.x-crest.x)**2+(p.z-crest.z)**2<42**2) key='whip crest';
      const ext=bounds[key]; if (!ext) continue;
      p.project(cam); if (p.z<-1 || p.z>1) continue;
      const x=(p.x+1)*width/2, y=(1-p.y)*height/2;
      ext.l=Math.min(ext.l,x);ext.r=Math.max(ext.r,x);ext.t=Math.min(ext.t,y);ext.b=Math.max(ext.b,y);ext.vertices++;
    }
  }
  function depthMaterial(group,side) {
    const key=group+'/'+side; if (materials.has(key)) return materials.get(key);
    const mat=new T.ShaderMaterial({side,uniforms:{ident:{value:num(group)},
      tower:{value:shaft},mast:{value:mast},tip:{value:tip}},
      vertexShader:`varying float depthAt; varying vec3 worldAt;
      void main(){vec4 p=vec4(position,1.0);
      #ifdef USE_INSTANCING
      p=instanceMatrix*p;
      #endif
      worldAt=(modelMatrix*p).xyz; vec4 v=modelViewMatrix*p;
      depthAt=-v.z;gl_Position=projectionMatrix*v;}`,
      fragmentShader:`uniform float ident; uniform vec3 tower,mast,tip; varying vec3 worldAt; varying float depthAt;
      void main(){float id=ident;
        if(id==${num('habitat')}.0 && worldAt.y>47.0 && distance(worldAt.xz,tower.xz)<51.0) id=${num('habitat tower')}.0;
        vec2 arm=mast.xz-tip.xz;float u=clamp(dot(worldAt.xz-tip.xz,arm)/max(dot(arm,arm),1.0),0.0,1.0);
        if(id==${num('pit')}.0 && worldAt.y>31.0 && (distance(worldAt.xz,mast.xz)<34.0 ||
           distance(worldAt.xz,tip.xz+u*arm)<11.0)) id=${num('pit mast')}.0;
        float d=clamp(floor(depthAt*12.0+.5),0.0,65535.0);
        gl_FragColor=vec4(id,floor(d/256.0),mod(d,256.0),255.0)/255.0;}`});
    materials.set(key,mat); return mat;
  }
  function add(o,part) {
    if (!o.isMesh || !o.geometry || !o.material || o.material.transparent || !o.material.depthWrite) return;
    const group=category(o,part), mesh=o.isInstancedMesh ? o.clone(false) : new T.Mesh(o.geometry);
    mesh.material=depthMaterial(group,o.material.side); mesh.visible=true; mesh.matrixAutoUpdate=false;
    mesh.matrix.copy(o.matrixWorld); mesh.frustumCulled=o.frustumCulled; mesh.onBeforeRender=()=>{};
    scene.add(mesh); geometryBounds(o,group);
  }
  for (const part of names) {
    if (part==='fleet' || part==='rocks') continue;
    const staticNode=a.find(part,part+'_static');
    staticNode?.traverse(o=>{if(o.isMesh){covered.add(o);add(o,part);}});
  }
  a.scene.traverseVisible(o=>{if(!covered.has(o) && !o.name.startsWith('site_')) add(o,null);});
  const rt=new T.WebGLRenderTarget(width,height,{type:T.UnsignedByteType,samples:0});
  const prior=renderer.getRenderTarget(), clear=renderer.getClearColor(new T.Color()),
    alpha=renderer.getClearAlpha(), pixels=new Uint8Array(width*height*4);
  try {
    renderer.setRenderTarget(rt);renderer.setClearColor(0,1);renderer.clear();renderer.render(scene,cam);
    renderer.readRenderTargetPixels(rt,0,0,width,height,pixels);
  } finally {
    renderer.setRenderTarget(prior);renderer.setClearColor(clear,alpha);rt.dispose();
    for(const mat of materials.values()) mat.dispose();
    for(const mesh of scene.children) if(mesh.isInstancedMesh) mesh.dispose();
  }
  const groups={};
  function inspect(key,p,tolerance,label) {
    const v=p.clone().project(cam), x=(1+v.x)*width/2, y=(1-v.y)*height/2;
    const item={name:label,world:p.toArray().map(v=>fmt(v)),px:[fmt(x),fmt(y)],
      inFrame:v.z>=-1 && v.z<=1 && x>=0 && x<width && y>=0 && y<height};
    if(item.inFrame){
      const i=((height-1-Math.floor(y))*width+Math.floor(x))*4, id=pixels[i];
      const z=-(p.clone().applyMatrix4(cam.matrixWorldInverse)).z;
      const delta=z-(pixels[i+1]*256+pixels[i+2])/12;
      item.first=owner[id]||'unknown';item.behindMetres=id?fmt(delta):null;
      item.clear=!id || delta<=tolerance;
    }else{item.first=null;item.clear=false;}
    (groups[key] ||= []).push(item);
  }
  for(const [ir,rr] of [0,.30,.53,.72].entries()){
    const n=rr?16:1;
    for(let j=0;j<n;j++){
      const phi=2*Math.PI*(j+.17*ir)/n,r=radius*rr,
        p=crown.clone().add(new T.Vector3(Math.cos(phi)*r,Math.sqrt(radius*radius-r*r),Math.sin(phi)*r));
      if(p.y>=a.sim.world.ground(p.x,p.z)-.05) inspect('lodeCap',p,1.0,rr?`rim ${ir}.${j}`:'apex');
    }
  }
  const w=a.sim.world, flight=[];
  for(let k=0;k<w.count;k++){const i=w.order[k];if(w.tag[i]===TAG.SHOT)flight.push(i);}
  flight.sort((i,j)=>w.x[i]-w.x[j]);
  for(const [j,i] of flight.entries()) inspect('oreArc',new T.Vector3(w.x[i],w.y[i],w.z[i]),2+w.radius[i],`flight ${j+1}`);
  for(const name of ['tractor_head','boom_feed_start','maw','gantry_search']) inspect('mastArm',a.mark('pit',name),5,name);
  for(const [label,dx,dy,dz] of [['hatch',0,0,0],['near lip',0,0,7.3],['far lip',0,0,-7.3],
      ['inflow 6m',0,-6,0],['inflow 12m',0,-12,0],['inflow 19m',0,-19,0]]){
    const local=new T.Vector3(dx,dy,dz).applyQuaternion(fr.ship.quaternion).add(fr.hatch);
    inspect('belly',local,2.2,label);
  }
  const summary={};
  for(const [key,items] of Object.entries(groups)){
    const blocked={};for(const it of items) if(it.inFrame && !it.clear) blocked[it.first]=(blocked[it.first]||0)+1;
    summary[key]={samples:items.length,inFrame:items.filter(p=>p.inFrame).length,unobstructed:items.filter(p=>p.clear).length,blocked};
  }
  const visibleSurfaces={}, capId=num('lode'),mastId=num('pit mast'),shipId=num('freighter'),doorId=num('hatch doors');
  for(const name of ['lode','tractor head housing','belly lip','hatch doors']) visibleSurfaces[name]={count:0,box:null};
  function hitSurface(name,x,y){
    const s=visibleSurfaces[name];s.count++;
    if(!s.box) s.box=[x,y,x,y];else{s.box[0]=Math.min(s.box[0],x);s.box[1]=Math.min(s.box[1],y);
      s.box[2]=Math.max(s.box[2],x);s.box[3]=Math.max(s.box[3],y);}
  }
  const hit=new T.Vector3(), local=new T.Vector3(), toShip=fr.ship.matrixWorld.clone().invert();
  const tangent=Math.tan(cam.fov*Math.PI/360);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const i=4*((height-1-y)*width+x), id=pixels[i];
    if(id===capId){hitSurface('lode',x,y);continue;}
    if(id!==mastId && id!==shipId && id!==doorId)continue;
    const z=(pixels[i+1]*256+pixels[i+2])/12;
    hit.set((2*(x+.5)/width-1)*cam.aspect*tangent,(1-2*(y+.5)/height)*tangent,-1)
       .applyQuaternion(cam.quaternion).multiplyScalar(z).add(origin);
    if(id===mastId && hit.distanceToSquared(tip)<7.2**2)hitSurface('tractor head housing',x,y);
    if(id===doorId)hitSurface('hatch doors',x,y);
    if(id===shipId || id===doorId){
      local.copy(hit).applyMatrix4(toShip);
      if(Math.abs(local.x)<=31 && Math.abs(local.z)<=18 && local.y>=-9 && local.y<=3.2)hitSurface('belly lip',x,y);
    }
  }
  for(const [key,b] of Object.entries(bounds)){
    if(!b.vertices){bounds[key]=null;continue;}
    b.inFrame=b.l>=0 && b.r<width && b.t>=0 && b.b<height;
    b.marginPx=[b.l,b.t,width-b.r,height-b.b].map(v=>fmt(v));
    for(const k of ['l','t','r','b']) b[k]=fmt(b[k]);
  }
  return {viewport:[width,height],pixelRatio:renderer.getPixelRatio(),shadowSize:a.sun.shadow.mapSize.x,
    touch:navigator.maxTouchPoints>0,eye:origin.toArray(),target:a.controls.target.toArray(),fov:cam.fov,
    simTime:a.sim.time,freighterState:fr.state,visibleSurfaces,bounds,summary,samples:groups};
}"""


def mark_image(photo, filename, metrics):
    image = Image.open(photo).convert('RGB')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    palette = {'lodeCap': '#d2a4e2', 'oreArc': '#f5c47c', 'mastArm': '#81d3c6', 'belly': '#9bb9eb'}
    labels = {'lodeCap': 'Lode cap', 'oreArc': 'In-flight ore', 'mastArm': 'Mast / arm', 'belly': 'Hatch / inflow'}
    for key, pts in metrics['samples'].items():
        for p in pts:
            if not p['inFrame']:
                continue
            x, y = map(round, p['px'])
            color = palette[key]
            if p['clear']:
                draw.ellipse((x-2,y-2,x+2,y+2),outline=color,width=1)
            else:
                draw.line((x-2,y-2,x+2,y+2),fill=color)
                draw.line((x-2,y+2,x+2,y-2),fill=color)
    x, y = 9, 8
    for key, text in labels.items():
        draw.text((x,y),text,fill=palette[key],font=font,stroke_width=1,stroke_fill='black'); y+=14
    draw.text((x,y),'o clear   x blocked',fill='#eee',font=font,stroke_width=1,stroke_fill='black')
    image.save(filename,quality=93)


def capture(browser, uri, profile, stage, ff):
    width, height = VIEWS[profile]
    mobile = profile == 'mobile'
    with browser.new_context(viewport={'width':width,'height':height},device_scale_factor=3 if mobile else 1,
                             is_mobile=mobile,has_touch=mobile) as context:
        page = context.new_page()
        errors=[]
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.set_default_timeout(600000)
        params={'manual':1,'tags':0,'rot':0}
        if ff is not None:
            params['ff']=ff
        page.goto(uri+'/?'+urlencode(params),wait_until='domcontentloaded')
        page.wait_for_function('window.__mine?.ready || window.__mine?.fatal || document.querySelector("#boot.fail")')
        ready, fatal, missing = page.evaluate('''() => [window.__mine?.ready, window.__mine?.fatal ||
            document.querySelector('#boot.fail')?.textContent, window.__mine?.missingParts]''')
        if not ready or fatal or missing:
            raise RuntimeError(f'{profile}: {fatal or missing or "Live scene did not start"}')
        page.locator('#boot').wait_for(state='hidden')
        result=page.evaluate(MEASURE)
        if errors:
            raise RuntimeError(f'{profile}: {errors}')
        photo=stage/f'sightlines-{profile}.jpg'
        page.evaluate('() => window.__mine.draw(0)')
        page.screenshot(path=photo,quality=94,scale='css')
        mark_image(photo,stage/f'sightlines-{profile}-marked.jpg',result)
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'qa')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--ff',type=float,help='Override the live home warm-up time.')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    flags=['--disable-dev-shm-usage','--enable-unsafe-swiftshader']
    if os.getenv('LODE_SW'):
        flags+=['--use-gl=angle','--use-angle=swiftshader']
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp, server(args.port) as http, sync_playwright() as pw:
        threading.Thread(target=http.serve_forever,daemon=True).start()
        browser=pw.chromium.launch(executable_path=os.getenv('LODE_CHROME'),args=flags)
        stage=Path(tmp)
        try:
            scenes={name:capture(browser,f'http://127.0.0.1:{http.server_port}',name,stage,args.ff) for name in VIEWS}
        finally:
            browser.close()
        report={'depthStepMetres':1/12,'sampling':'Samples compare marker depth with the nearest opaque pixel. '
                'Negative behindMetres puts the recorded surface behind the marker. Visible surface counts cover the '
                'actual crown, material within 7.2 m of the tractor head, the moving doors, and the lower hull '
                'within 31 m longitudinally, 18 m laterally and -9 to +3.2 m vertically of its hatch. '
                'Alpha effects and UI are excluded.', 'views':scenes}
        (stage/'sightlines.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        for output in stage.iterdir():
            output.replace(args.output/output.name)
        for key, scene in scenes.items():
            print(key,'visible surfaces',scene['visibleSurfaces'],'samples',scene['summary'],'bounds',scene['bounds'],flush=True)


if __name__ == '__main__':
    main()
