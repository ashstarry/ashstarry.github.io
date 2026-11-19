const atlas = './assets/tour/';
const openings = './assets/opening/intro-';
const titles = {
  intro:'Opening', orbit:'Orbit', plan:'Site Plan', tide:'Gravity Tide', watch:'Tower Watch', mast:'Crane Catwalk', harbor:'Work Barge',
  dust:'North Dust Works', winch:'Rim Winch', salvage:'Salvage Beam', face:'Bench Collapse', hull:'Cargo Hold', yard:'Axle Shop', hab:'Habitat', pit:'Open Pit', south:'South Rim', wide:'Dark Star'
};
const recordings = { tide:'tide.mp4', dust:'patrol.mp4', mast:'mast-watch.mp4', salvage:'salvage.mp4', face:'rockfall.mp4' };
const circle = Math.PI*2;
const clamp = (value,min,max) => Math.max(min,Math.min(max,value));
const mediaURL = path => new URL(window.mineMediaURL?.(path) || path, document.baseURI).href;

// Observe native buffered media. If a browser blocks preloading, the decoded
// photograph and working tour controls can still be handed to the visitor.
function mediaReady(media, report) {
  return new Promise(resolve => {
    const events = ['progress','loadedmetadata','loadeddata','canplay','error'];
    let timer;
    function finish(result) {
      clearTimeout(timer);
      for (const event of events) media.removeEventListener(event,check);
      resolve(result);
    }
    function check() {
      if (media.error) return finish('error');
      if (media.readyState >= 2 && !media.seeking) return finish('frame');
      const end = media.buffered.length ? media.buffered.end(0) : 0;
      report(Math.min(.95,(media.readyState >= 1 ? .22 : 0) + Math.min(1,end) * .70));
    }
    for (const event of events) media.addEventListener(event,check);
    timer = setTimeout(() => finish('poster'),8000);
    check();
  });
}

// Keep a decoded frame under the next native video until it can paint. The
// second recording has no source at all until the first screening reaches it.
function openingFilms(plate, lead, isTall, reduceMotion, onChange, onLeadError) {
  const shift=document.createElement('video'), films=[lead,shift];
  const poster=new Image(), hold=document.createElement('canvas');
  poster.className='tour-film-poster';poster.alt='';poster.draggable=false;
  hold.style.cssText='position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none';
  hold.setAttribute('aria-hidden','true');
  for(const [i,media] of films.entries()) {
    media.removeAttribute('style');media.removeAttribute('id');media.className=i?'tour-shift':'tour-opening';
    media.style.pointerEvents='none';media.loop=false;media.muted=media.defaultMuted=media.playsInline=true;
    media.autoplay=false;media.controls=false;media.setAttribute('muted','');media.setAttribute('playsinline','');
    media.setAttribute('aria-label',i?'Mine operations after the tide':'Opening shift recording');
  }
  shift.preload='none';poster.hidden=hold.hidden=lead.hidden=shift.hidden=true;
  plate.append(poster,hold,lead,shift);
  let locked=true, phase=0, shown=false, wanted=false, posterOnly=false, ready=false;
  let request=0, expected='', seekTime=null, fadeStart=0, raf=0;
  const variant=()=>isTall()?'tall':'wide';
  const active=()=>films[phase];
  const smooth=value=>{const x=clamp(value,0,1);return x*x*(3-2*x);};

  function preserve(source) {
    const width=source?.videoWidth || source?.naturalWidth, height=source?.videoHeight || source?.naturalHeight;
    if(!width || !height)return;
    const alpha=source===active()?Number(source.style.opacity || 1):1;
    const underlay=hold.hidden?poster:hold;
    if(alpha<1 && (!hold.hidden || poster.complete && poster.naturalWidth)){
      const mix=document.createElement('canvas');mix.width=width;mix.height=height;
      const pixels=mix.getContext('2d');
      if(underlay===poster){
        const shot=window.minePlates.select(isTall()?.5:1.6,'tour');
        const size=window.minePlates.extent(shot,width,height);
        pixels.drawImage(poster,(width-size.width)/2,(height-size.height)/2,size.width,size.height);
      }else pixels.drawImage(underlay,0,0,width,height);
      pixels.globalAlpha=alpha;pixels.drawImage(source,0,0);source=mix;
    }
    hold.width=width;hold.height=height;
    hold.getContext('2d').drawImage(source,0,0);hold.hidden=false;
  }
  function paint() {
    cancelAnimationFrame(raf);raf=0;
    const media=active();
    if(locked || !shown || posterOnly || seekTime!==null || media.currentSrc!==expected || media.readyState<2 || media.seeking)return;
    if(!ready){ready=true;fadeStart=performance.now();}
    const entered=smooth((performance.now()-fadeStart)/180);
    // The shift ends in quiet production. Let that picture settle back into
    // the opening poster before the next gravity front begins its approach.
    const remaining=media.duration-media.currentTime;
    const ending=phase===1 && Number.isFinite(remaining) && poster.complete && poster.naturalWidth ? smooth((remaining-.10)/.58) : 1;
    media.style.opacity=String(entered*ending);media.hidden=false;
    if(entered===1)hold.hidden=true;
    if((wanted&&!media.paused) || entered<1)raf=requestAnimationFrame(paint);
  }
  function play() {
    const serial=request;
    active().play().catch(()=>{
      if(serial===request && shown){wanted=false;onChange();}
    });
  }
  function applyOffset() {
    const media=active();
    if(!shown || media.currentSrc!==expected || media.readyState<1 || seekTime===null)return;
    const t=Math.min(seekTime,Math.max(0,media.duration-.01));seekTime=null;
    if(Number.isFinite(t) && Math.abs(media.currentTime-t)>.035)media.currentTime=t;
    paint();
  }
  function select(index, time, holdFrame=false) {
    if(holdFrame===true){if(ready && !active().hidden && active().readyState>=2)preserve(active());}
    else if(holdFrame)preserve(holdFrame);
    else hold.hidden=true;
    request++;ready=false;cancelAnimationFrame(raf);
    const old=active();phase=index;const media=active();
    if(old!==media){old.pause();old.hidden=true;}
    media.hidden=true;media.style.opacity='0';seekTime=Math.max(0,time);
    const mode=variant(), cover=new URL(window.minePlates.url(window.minePlates.select(isTall()?.5:1.6,'tour')),document.baseURI).href;
    if(poster.src!==cover)poster.src=cover;

    poster.hidden=false;
    if(posterOnly && !hold.hidden){
      const serial=request;
      poster.decode().then(()=>{if(serial===request && posterOnly)hold.hidden=true;}).catch(()=>{});
    }
    expected=mediaURL((index?atlas+'shift-':openings)+mode+'.mp4');
    media.preload=posterOnly?'none':'auto';
    if(media.src!==expected || media.error)media.src=expected;
    applyOffset();
    if(wanted && !locked)play();else media.pause();
    onChange();
  }
  function ended(media) {
    if(!shown || media!==active() || !media.ended || !wanted)return;
    if(phase===0)select(1,0,true);
    else select(0,0);
  }
  for(const media of films) {
    media.addEventListener('loadedmetadata',()=>{if(media===active())applyOffset();});
    for(const event of ['canplay','playing','seeked','loadeddata'])media.addEventListener(event,()=>{if(media===active())paint();});
    media.addEventListener('ended',()=>ended(media));
    media.addEventListener('pause',()=>{
      if(shown && media===active() && ready && media.paused && !media.ended && !media.seeking){wanted=false;onChange();}
    });
    media.addEventListener('error',()=>{
      if(!shown || media!==active() || media.currentSrc!==expected)return;
      wanted=false;media.hidden=true;onChange();if(!phase && !locked)onLeadError();
    });
  }
  return {
    async prepare(report) {
      const photo=poster.decode().then(()=>true,()=>false);
      if(reduceMotion)return photo;
      const [image, media]=await Promise.all([photo,mediaReady(lead,report)]);
      if(media==='frame')return true;
      if(image && media==='poster'){posterOnly=true;wanted=false;return true;}
      return false;
    },
    place(width,height) {
      window.minePlates.fit(poster,window.minePlates.select(isTall()?.5:1.6,'tour'),width,height);
    },
    unlock() {
      locked=false;
      if(shown && wanted){play();paint();}
    },
    get playing(){return wanted;},
    get hasPicture(){return !poster.hidden || !hold.hidden || films.some(v=>!v.hidden);},
    get failed(){return shown && phase===0 && Boolean(lead.error);},
    enter(handoff, previous) {
      const t=handoff?lead.currentTime:0;
      shown=true;posterOnly=reduceMotion;wanted=!posterOnly;
      select(0,t,previous);
    },
    leave(keepPicture=false) {
      shown=wanted=false;request++;cancelAnimationFrame(raf);films.forEach(v=>v.pause());
      if(!keepPicture){poster.hidden=hold.hidden=true;films.forEach(v=>{v.hidden=true;});}
    },
    toggle() {
      if(wanted){wanted=false;active().pause();}
      else {
        wanted=true;posterOnly=false;
        if(active().ended)ended(active());
        else if(active().error)select(phase,0,true);
        else {if(seekTime!==null)applyOffset();play();paint();}
      }
      onChange();
    },
    resize() {if(shown)select(phase,seekTime ?? active().currentTime,true);},
  };
}

export async function startTour() {
  const params = new URLSearchParams(location.search), opening = window.mineOpening;
  const boot=window.mineBoot;
  boot.progress(18,'Preparing the tour');
  const root = document.createElement('main');
  root.id = 'tour'; root.inert = true;
  root.innerHTML = `
    <div class="tour-stage has-still" tabindex="0" aria-label="Mine view. Use the arrow keys to orbit and L to toggle labels.">
      <div class="tour-plate"><img alt="The mine viewed from orbit" draggable="false"><video class="tour-detail-film" controls muted loop playsinline preload="none" hidden aria-label="Recorded mine simulation"></video></div>
      <div class="tour-marks" aria-hidden="true"></div>
    </div>
    <header class="tour-heading"><h1>The Lode <span>Deep-Space Mine</span></h1><p><span class="tour-status">Recorded tour</span> <a class="tour-live" href="?view=live">Live 3D</a></p></header>
    <div class="tour-tools tour-box" role="group" aria-label="View controls">
      <button type="button" data-transport>Pause</button><button type="button" data-labels aria-keyshortcuts="L" aria-pressed="false">Labels</button>
      <button type="button" data-zoom="-1" class="tour-zoom" aria-label="Zoom out">−</button><button type="button" data-zoom="1" class="tour-zoom" aria-label="Zoom in">+</button>
      <button type="button" data-reset title="Reset the view">Reset</button>
    </div>
    <div class="tour-bottom"><nav class="tour-nav tour-box" aria-label="Mine viewpoints"></nav>
      <div class="tour-bearing tour-box" role="group" aria-label="Orbit controls"><button type="button" data-step="-1" class="tour-step" aria-label="Orbit left">‹</button>
      <output aria-label="Orbit angle">0°</output><button type="button" data-step="1" class="tour-step" aria-label="Orbit right">›</button></div></div>`;
  const get = selector => root.querySelector(selector);
  const stage=get('.tour-stage'), plate=get('.tour-plate'), img=get('img'), film=get('.tour-detail-film');
  const marks=get('.tour-marks'), tools=get('.tour-tools'), labelButton=get('[data-labels]');
  const nav=get('nav'), bearing=get('.tour-bearing'), output=get('output'), transport=get('[data-transport]');
  const orientation = matchMedia('(max-aspect-ratio: 4/5)');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let tall = orientation.matches, manifest = null, display = null, sequence = 0, width = 0, height = 0;
  let detailMovie = false, pinch = 0, lastIndex = -1;
  let down = null;
  const cache = new Map(), pointers = new Map();
  const state = {view:'intro', yaw: Number(opening?.yaw)||0, zoom:clamp(Number(opening?.zoom)||1,.7,4),
                 x:0, y:0, labels:params.get('tags')==='1'};
  const openingFilm=openingFilms(plate,document.createElement('video'),
    ()=>tall,reduced,()=>{if(state.view==='intro')controls();},()=>{if(manifest)toOrbit();});
  const filmOn = () => state.view==='tide' || detailMovie;
  const frames = () => (tall && manifest?.portrait?.length ? manifest.portrait : manifest?.orbit) || [];
  const angleIndex = (angle,n) => ((Math.round(angle/circle*n)%n)+n)%n;
  const detailRecord = () => {const r=manifest?.views?.[state.view]; return (tall && r?.portrait) || r;};
  const selectBox=document.createElement('select');
  selectBox.setAttribute('aria-label','Close-ups'); selectBox.add(new Option('Close-ups','')); selectBox.options[0].disabled=true;
  for (const [key,title] of Object.entries(titles)) {
    if (['intro','orbit','plan','tide'].includes(key)) {
      const button=document.createElement('button'); button.type='button'; button.dataset.view=key; button.textContent=title;
      button.addEventListener('click',()=>choose(key));nav.append(button);
    } else selectBox.add(new Option(title,key));
  }
  selectBox.addEventListener('change',()=>choose(selectBox.value));nav.append(selectBox);

  function controls() {
    const liveParams = new URLSearchParams(location.search);
    liveParams.set('view','live');
    const liveFocus = ({intro:'home',orbit:'home',tide:'home',wide:'sky'})[state.view] || state.view;
    if (liveFocus==='home' && !params.has('focus')) liveParams.delete('focus');
    else liveParams.set('focus',liveFocus);
    get('.tour-live').search=liveParams.toString();
    for (const button of nav.querySelectorAll('button')) button.setAttribute('aria-pressed',String(button.dataset.view===state.view));
    selectBox.value=['intro','orbit','plan','tide'].includes(state.view)?'':state.view;
    labelButton.setAttribute('aria-pressed',String(state.labels));
    transport.hidden=!(state.view==='intro' || (recordings[state.view] && state.view!=='tide'));
    transport.textContent=state.view==='intro'?(openingFilm.playing?'Pause':'Play'):(detailMovie?'Show still':'Play footage');
    bearing.hidden=state.view!=='orbit';
    stage.classList.toggle('has-still',!filmOn());
    stage.setAttribute('data-view',state.view);
    for(const button of tools.querySelectorAll('[data-zoom]')) button.disabled=+button.dataset.zoom>0?state.zoom>=4:state.zoom<=.7;
  }
  function paintLabels() {
    marks.replaceChildren();
    if (!state.labels || !display || state.view==='intro' || filmOn()) return;
    const sw=stage.clientWidth,sh=stage.clientHeight, occupied=[];
    const blocked=[get('.tour-heading'),tools,get('.tour-bottom')].flatMap(el=>el===get('.tour-bottom')?[...el.children]:[el])
      .filter(el=>!el.hidden).map(el=>el.getBoundingClientRect());
    for (const [name,description,u,v] of display.labels) {
      const px=(sw-width)/2+state.x+u*width, py=(sh-height)/2+state.y+v*height;
      if(px<1||px>=sw-1||py<1||py>=sh-1)continue;
      const tag=document.createElement('span'); tag.className='tour-mark'; tag.textContent=name;
      const note=document.createElement('small');note.textContent=description;tag.append(note);marks.append(tag);
      const w=tag.offsetWidth,h=tag.offsetHeight;let accepted=false;
      for(const [x,y] of [[px+5,py-h-3],[px+5,py+3],[px-w-5,py-h-3],[px-w-5,py+3]]) {
        if(x<4||x+w>sw-4||y<3||y+h>sh-3)continue;
        if(occupied.some(b=>x<b[2]+3 && x+w>b[0]-3 && y<b[3]+2 && y+h>b[1]-2))continue;
        if(blocked.some(b=>x<b.right+4&&x+w>b.left-4&&y<b.bottom+4&&y+h>b.top-4))continue;
        tag.style.transform=`translate(${Math.round(x)}px,${Math.round(y)}px)`;occupied.push([x,y,x+w,y+h]);accepted=true;break;
      }
      if(!accepted)tag.remove();
    }
  }
  function place() {
    const sw=stage.clientWidth, sh=stage.clientHeight;
    const fallback = tall && (state.view==='intro' || frames()===manifest?.portrait) ? .5 : 1.6;
    const aspect=state.view==='intro'?(tall?.5:1.6):filmOn()?(film.videoWidth/film.videoHeight||1.6):
      (display?.width/display?.height || fallback);
    height=Math.min(sh,sw/aspect)*state.zoom; width=height*aspect;
    state.x=clamp(state.x,-Math.max(0,(width-sw)/2),Math.max(0,(width-sw)/2));
    state.y=clamp(state.y,-Math.max(0,(height-sh)/2),Math.max(0,(height-sh)/2));
    if(state.view==='intro')openingFilm.place(width,height);
    plate.style.width=width+'px';plate.style.height=height+'px';
    plate.style.transform=`translate(${state.x-width/2}px,${state.y-height/2}px)`;
    paintLabels();
  }
  function cached(file) {
    let promise=cache.get(file);
    if(!promise) {
      const picture=new Image();picture.src=mediaURL(atlas+file);
      promise=picture.decode().then(()=>picture);cache.set(file,promise);
      if(cache.size>13)cache.delete(cache.keys().next().value);
      promise.catch(()=>cache.delete(file));
    }
    return promise;
  }
  async function drawFrame(force=false) {
    const strip=frames();
    if(state.view==='intro' || filmOn())return;
    const orbit=state.view==='orbit', count=strip.length || (tall?24:60);
    const i=angleIndex(state.yaw,count);
    // The filename and aspect are known before the annotation index arrives.
    const provisional=orbit && !strip.length ? {image:(tall?'p':'o')+String(i).padStart(2,'0')+'.webp',
      width:tall?528:1056,height:tall?1056:660,labels:[]} : null;
    const record=orbit ? (strip[i] || provisional) : detailRecord();
    if(!record || (!force&&orbit&&i===lastIndex))return;
    lastIndex=orbit?i:-1;const id=++sequence;
    try {
      const picture=await cached(record.image);
      if(sequence!==id)return;
      img.src=picture.src;img.alt='The Lode · '+titles[state.view];img.hidden=false;
      openingFilm.leave();film.hidden=true;display=record;
      output.textContent=Math.round(i*360/count)+'°';place();
      if(orbit && strip.length)for(const step of [-1,1])cached(strip[(i+step+count)%count].image).catch(()=>{});
      return true;
    }catch{
      if(sequence===id){lastIndex=-1;get('.tour-status').textContent='View unavailable. Choose another viewpoint.';}
    }
  }
  function showMovie() {
    const name=recordings[state.view]; if(!name)return;
    openingFilm.leave();img.hidden=true;film.hidden=false;display=null;
    const record=manifest?.views?.[state.view];film.poster=mediaURL(record?atlas+record.image:openings+'wide.jpg');
    const source=mediaURL(atlas+name);
    if(film.src!==source)film.src=source;
    film.setAttribute('aria-label',titles[state.view]+' recording');film.play().catch(()=>{});
  }
  function choose(view, keepTransform=false) {
    let prepared;
    ++sequence;lastIndex=-1;detailMovie=false;
    const wasIntro=state.view==='intro';state.view=view;display=null;
    if(!keepTransform) {state.zoom=1;state.x=state.y=0;}
    if(view==='intro') {
      const previous=!film.hidden && film.readyState>=2 ? film : !img.hidden && img.complete ? img : null;
      state.yaw=0;state.labels=false;film.pause();film.hidden=img.hidden=true;
      openingFilm.enter(keepTransform,previous);
    } else if(view==='tide') showMovie();
    else {
      openingFilm.leave(wasIntro);film.pause();film.hidden=true;
      if(!wasIntro || !openingFilm.hasPicture){
        img.hidden=false;
        if(!manifest && view!=='orbit')img.src=mediaURL(atlas+(tall?'v-':'')+view+'.webp');
      }
      prepared=drawFrame(true);
    }
    controls();place();
    return prepared;
  }
  function toOrbit() { if(state.view!=='orbit')choose('orbit',true); }
  function turn(steps) {
    if(!steps)return;
    toOrbit();state.yaw+=steps*circle/(frames().length || (tall?24:60));drawFrame();
  }
  function zoomTo(next,x=0,y=0) {
    if(state.view==='intro'||filmOn()) toOrbit();
    const former=state.zoom;state.zoom=clamp(next,.7,4);const scale=state.zoom/former;
    state.x=x+(state.x-x)*scale;state.y=y+(state.y-y)*scale;
    controls();place();
  }
  function labelToggle() {
    if(state.view==='intro'||state.view==='tide')toOrbit();
    else if(detailMovie)choose(state.view);
    state.labels=!state.labels;controls();paintLabels();
  }
  labelButton.addEventListener('click',labelToggle);
  transport.addEventListener('click',()=>{
    if(state.view==='intro') openingFilm.toggle();
    else if(recordings[state.view]) {
      if(detailMovie){choose(state.view);return;}detailMovie=true;++sequence;showMovie();controls();place();
    }
  });
  film.addEventListener('error',()=>{if(filmOn())choose(state.view==='tide'?'orbit':state.view);});
  film.addEventListener('loadedmetadata',place);
  for(const b of root.querySelectorAll('[data-step]'))b.addEventListener('click',()=>turn(+b.dataset.step));
  for(const b of tools.querySelectorAll('[data-zoom]'))b.addEventListener('click',()=>zoomTo(state.zoom*1.33**(+b.dataset.zoom)));
  get('[data-reset]').addEventListener('click',()=>{state.yaw=0;choose(filmOn()||state.view==='intro'?'intro':state.view);});
  function fingerGap() {const [a,b]=pointers.values();return Math.hypot(a.x-b.x,a.y-b.y);}
  stage.addEventListener('pointerdown',e=>{
    if(e.button!==0||e.target===film)return;
    stage.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
    down={x:e.clientX,y:e.clientY};pinch=pointers.size===2?fingerGap():0;
    stage.classList.add('is-dragging');
  });
  stage.addEventListener('pointermove',e=>{
    const hand=pointers.get(e.pointerId);if(!hand)return;
    const dx=e.clientX-hand.x,dy=e.clientY-hand.y;hand.x=e.clientX;hand.y=e.clientY;
    if(pointers.size===2) {
      if(state.view==='intro')toOrbit();
      const gap=fingerGap(),[a,b]=pointers.values();
      if(pinch>0)zoomTo(state.zoom*gap/pinch,(a.x+b.x-stage.clientWidth)/2,(a.y+b.y-stage.clientHeight)/2);
      pinch=gap;
    } else {
      if(state.view==='intro' && down && Math.hypot(e.clientX-down.x,e.clientY-down.y)>2)toOrbit();
      if(state.view==='intro')return;
      if(state.view==='orbit' && state.zoom<1.02){state.yaw-=dx*Math.PI*1.65/Math.max(240,stage.clientWidth);drawFrame();}
      else if(!filmOn() && state.zoom>1.01){state.x+=dx;state.y+=dy;place();}
    }
  });
  function release(e) {
    pointers.delete(e.pointerId);pinch=pointers.size===2?fingerGap():0;
    if(!pointers.size){down=null;stage.classList.remove('is-dragging');}
  }
  for(const e of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(e,release);
  stage.addEventListener('wheel',e=>{
    if(e.target===film)return;e.preventDefault();zoomTo(state.zoom*Math.exp(-e.deltaY*.002),e.clientX-stage.clientWidth/2,e.clientY-stage.clientHeight/2);
  },{passive:false});
  window.addEventListener('keydown',e=>{
    if(root.inert || e.metaKey||e.ctrlKey||e.altKey||e.target===film)return;
    if(e.target===selectBox && e.key.toLowerCase()!=='l')return;
    if(e.key==='ArrowLeft'||e.key==='ArrowRight')turn(e.key==='ArrowLeft'?-1:1);
    else if(e.key.toLowerCase()==='l'&&!e.repeat)labelToggle();
    else if(['+','=','-'].includes(e.key))zoomTo(state.zoom*(e.key==='-'?1/1.33:1.33));
    else if(e.key==='Home')choose('intro');
    else if(e.code==='Space' && state.view==='intro' && !e.target.closest?.('button,select,a'))transport.click();
    else return;
    e.preventDefault();
  });
  const syncOrientation=()=>{
    if(tall!==orientation.matches){tall=orientation.matches;display=null;lastIndex=-1;
      if(state.view==='intro') openingFilm.resize();
      else drawFrame(true);
    }
    place();
  };
  orientation.addEventListener('change',syncOrientation);
  document.querySelector('#hud').hidden=true;
  document.body.prepend(root);
  new ResizeObserver(syncOrientation).observe(stage);
  const focus=params.get('focus');
  const initial=focus==='sky'?'wide':focus==='home'?null:focus;
  const response=await fetch(mediaURL(atlas+'views.json'));
  if(!response.ok)throw Error('Missing tour');
  manifest=await response.json();
  if(!manifest.orbit?.length)throw Error('Empty tour');
  boot.progress(56,'Decoding the opening frame');
  const requested=Object.hasOwn(titles,initial)?initial:null;
  const readGesture=() => {
    state.yaw=opening?.visibleYaw() || 0;
    state.zoom=clamp(opening?.zoom || 1,.7,4);
  };
  readGesture();
  const start=requested || (opening?.turned || state.zoom!==1 || state.labels?'orbit':'intro');
  const prepared=choose(start,true);
  const buffer=f=>boot.progress(62+30*f,'Buffering the opening shot');
  let ok;
  if(start==='intro')ok=await openingFilm.prepare(buffer);
  else if(start==='tide')ok=(await mediaReady(film,buffer))==='frame';
  else ok=await prepared;
  if (!ok || (!requested && opening?.turned)) {
    readGesture();
    if(!await choose('orbit',true))throw Error('Tour frame unavailable');
  } else if (start==='intro' && opening?.zoom!==1) {
    readGesture();
    if(!await choose('orbit',true))throw Error('Tour frame unavailable');
  }
  boot.progress(97,'Opening the mine');
  await boot.paint();
  root.inert=false;
  openingFilm.unlock();
  controls();
  boot.finish();
  if(state.view==='intro')cached(frames()[0].image).catch(()=>{});
}
