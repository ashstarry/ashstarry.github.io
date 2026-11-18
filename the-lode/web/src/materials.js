import * as THREE from 'three';
import { pressureGLSL } from './pressure.js';
const loader = new THREE.TextureLoader();
const materialImages = [];
function tex(name, repeat = true) {
  let complete, fail;
  const decoded = new Promise((ok, error) => { complete = ok; fail = error; });
  // Downloads start as the module loads. Retain errors until the boot screen can report them.
  decoded.catch(() => {});
  const t = loader.load('./assets/tex/' + name + '.png', texture => {
    Promise.resolve(texture.image.decode?.()).then(complete, fail);
  }, undefined, () => fail(Error('Texture failed to load: ' + name)));
  materialImages.push({ texture: t, decoded });
  t.colorSpace = THREE.NoColorSpace;
  t.anisotropy = repeat ? 8 : 4;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}
export function prepareTextures(renderer, onProgress) {
  let done = 0;
  return Promise.all(materialImages.map(async item => {
    await item.decoded;
    renderer.initTexture(item.texture);
    onProgress(++done / materialImages.length);
  }));
}
export const U = {
  tNoiseA: {
    value: tex('noise_a')
  },
  tNoiseB: {
    value: tex('noise_b')
  },
  tRockN: {
    value: tex('rock_n')
  },
  tMetalN: {
    value: tex('metal_n')
  },
  tConcN: {
    value: tex('conc_n')
  },
  tMask: {
    value: tex('terrain_mask', false)
  },
  tMask2: {
    value: tex('terrain_mask2', false)
  },
  tSplat: {
    value: null
  },
  tHeight: {
    value: null
  },
  uWorldRect: {
    value: new THREE.Vector4(-256, -288, 576, 0)
  },
  uTime: {
    value: 0
  },
  uSplatGain: {
    value: 1.3
  },
  uTide: {
    value: 0
  },
  uLode: {
    value: new THREE.Vector4(-78, -96, -12, 34)
  },
  uArt: {
    value: new THREE.Vector4(1.2, 0, .00020, 0)
  },
  uWave: {
    value: new THREE.Vector4(-1000, 0, 0, 0)
  },
  uShadow: {
    value: new THREE.Vector4(0, 0, 0, 0)
  }
};
const PARS_V = `varying vec3 vLPos;varying vec3 vLNrm;varying vec3 vWPos;varying mat3 vO2V;
#ifdef BUILT
#ifndef USE_UV1
attribute vec2 uv1;
#endif
varying vec2 vUvM;varying vec2 vUvH;
#endif`;
const MAIN_V = `vLPos=position;vLNrm=normal;
#ifdef BUILT
vUvM=vec2(uv.x,1.-uv.y);vUvH=max(vec2(uv1.x,1.-uv1.y),vec2(.001));
#endif
{vec4 wp_=vec4(transformed,1.);mat3 o2v_=normalMatrix;
#ifdef USE_INSTANCING
wp_=instanceMatrix*wp_;mat3 im_=mat3(instanceMatrix);im_[0]/=max(length(im_[0]),1.e-6);im_[1]/=max(length(im_[1]),1.e-6);im_[2]/=max(length(im_[2]),1.e-6);o2v_=o2v_*im_;
#endif
vWPos=(modelMatrix*wp_).xyz;vO2V=o2v_;}`;
const PARS_F = `uniform sampler2D tNoiseA,tNoiseB,tRockN,tMetalN,tConcN,tMask,tMask2,tSplat,tHeight;uniform vec4 uWorldRect,uLode,uArt,uWave,uShadow;uniform float uTime,uSplatGain,uTide;
${pressureGLSL}
varying vec3 vLPos;varying vec3 vLNrm;varying vec3 vWPos;varying mat3 vO2V;
#ifdef BUILT
varying vec2 vUvM;varying vec2 vUvH;uniform vec2 uPanel;uniform vec4 uP;
#endif
vec3 safeN(vec3 n){return n*inversesqrt(max(dot(n,n),1.e-12));}
vec3 triW(vec3 n){vec3 w=pow(abs(n),vec3(5.));return w/max(w.x+w.y+w.z,1.e-6);}
vec4 tri(sampler2D t,vec3 p,vec3 w,float s){return texture2D(t,p.zy*s)*w.x+texture2D(t,p.xz*s)*w.y+texture2D(t,p.xy*s)*w.z;}
vec3 triN(sampler2D t,vec3 p,vec3 n,vec3 w,float s,float k){
 vec3 tx=texture2D(t,p.zy*s).xyz*2.-1.,ty=texture2D(t,p.xz*s).xyz*2.-1.,tz=texture2D(t,p.xy*s).xyz*2.-1.;tx.xy*=k;ty.xy*=k;tz.xy*=k;
 tx=vec3(tx.xy+n.zy,abs(tx.z)*n.x);ty=vec3(ty.xy+n.xz,abs(ty.z)*n.y);tz=vec3(tz.xy+n.xy,abs(tz.z)*n.z);return safeN(tx.zyx*w.x+ty.xzy*w.y+tz.xyz*w.z);}
vec2 worldUV(vec3 p){return vec2(p.x-uWorldRect.x,-p.z-uWorldRect.y)/uWorldRect.z;}
float hash11(float p){p=fract(p*.1031);p*=p+33.33;p*=p+p;return fract(p);}
vec3 rockColor(vec3 p,vec3 n,vec3 w,out float rough){
 vec4 na=tri(tNoiseA,p,w,1./41.),nb=tri(tNoiseA,p,w,1./7.3),nc=tri(tNoiseB,p,w,1./13.);
 float hgt=p.y+5.*(na.r-.5)+.8*(nb.r-.5);
 float s1=texture2D(tNoiseA,vec2(.13,hgt/67.)).r,s2=texture2D(tNoiseA,vec2(.71,hgt/17.)).r,s3=texture2D(tNoiseB,vec2(.37,hgt/5.3)).r;
 vec3 c=mix(vec3(.034,.033,.034),vec3(.095,.083,.072),smoothstep(.25,.75,s1));
 c=mix(c,vec3(.150,.070,.036),smoothstep(.52,.78,s2)*.55);c=mix(c,vec3(.21,.19,.165),smoothstep(.62,.72,s3)*.35*smoothstep(.3,.6,na.g));
 c*=.84+.32*nb.r;c*=mix(.72,1.,smoothstep(.02,.2,nb.g));c*=mix(.78,1.,smoothstep(.15,.5,nc.r));rough=.86+.1*nb.b;return c;
}`;
const SURF = {};
SURF.ground = `{
 vec3 p=vLPos,n=safeN(vLNrm),w=triW(n);float rr;vec3 c=rockColor(p,n,w,rr);vec2 uv=worldUV(vWPos);vec3 m=texture2D(tMask,uv).rgb,m2=texture2D(tMask2,uv).rgb;float top=smoothstep(.35,.8,n.y);
 float inR=step(0.,uv.x)*step(uv.x,1.)*step(0.,uv.y)*step(uv.y,1.)*top;
 float macro=texture2D(tNoiseA,p.xz/310.).r,fine=texture2D(tNoiseA,p.xz/3.1).b,med=texture2D(tNoiseA,p.xz/23.).r;
 vec3 dust=vec3(.165,.140,.118)*(.62+.75*macro)*(.8+.4*fine);float flat_=smoothstep(.80,.97,n.y)*smoothstep(.25,.6,med+.25*macro+.2);
 c=mix(c,dust,flat_*(1.-.6*m2.g*inR));float nearL=1.-smoothstep(26.,70.,distance(vWPos,uLode.xyz+vec3(0,22,0)));c=mix(c,c*vec3(.38,.40,.46),nearL*.8);
 float road=m.g*inR,ruts=texture2D(tNoiseB,p.xz/5.).g;c=mix(c,vec3(.058,.052,.047)*(.75+.5*ruts)*(.8+.4*fine),road*.88);
 vec3 pc=vec3(.17,.165,.155)*(.7+.45*med)*(.85+.3*fine);pc*=mix(.6,1.,smoothstep(0.,.12,texture2D(tNoiseA,p.xz/9.).g));c=mix(c,pc,m.b*inR*.9);c*=1.-.75*m2.r*inR;
 sAlb=c;sRough=mix(mix(rr,.97,flat_),.74,road*.7+nearL*.5);sMetal=0.;float lod_=clamp(1.-length(vViewPosition)/900.,.25,1.);
 vec3 n1=triN(tRockN,p,n,w,1./31.,.34),n2=triN(tRockN,p,n,w,1./5.3,.3*lod_*(1.-.7*flat_));sNrm=safeN(n1+n2-n);sAO=mix(1.,m.r,inR);sEmit=vec3(0.);
}`;
SURF.rock = `{
 vec3 p=vLPos*uScale+uSeed,n=safeN(vLNrm),w=triW(n);
 #ifdef GRAIN
 p+=vColor.rgb*37.;
 #endif
 float rr;vec3 c=rockColor(p,n,w,rr)*uTint;sAO=1.;
 #ifdef GRAIN
 c*=vColor.rgb;
 #elif defined(USE_COLOR) || defined(USE_COLOR_ALPHA)
 sAO=vColor.r;c*=.35+.65*vColor.r;
 #endif
 #ifdef INNER
 c=mix(c*1.5,vec3(.20,.16,.13),.35);
 #endif
 sAlb=c;sRough=rr;sMetal=0.;sNrm=safeN(triN(tRockN,p,n,w,1./17.,.9)+triN(tRockN,p,n,w,1./3.7,.6)-n);sEmit=vec3(0.);
}`;
SURF.lode = `{vec3 n=safeN(vLNrm),d=vWPos-uLode.xyz;float ring=sin(length(d.xz)*2.6)*.5+.5;sAlb=vec3(.0025,.0027,.003);sRough=mix(.16,.34,smoothstep(.92,1.,ring));sMetal=0.;vec3 radial=safeN(vec3(d.x,0.,d.z)+1.e-5);sNrm=safeN(n+radial*(smoothstep(.9,1.,ring)-smoothstep(0.,.1,ring))*.05);sAO=1.;sEmit=vec3(0.);}`;
SURF.relic = `{vec3 n=safeN(vLNrm);float g=tri(tNoiseB,vLPos*vec3(1.,.12,1.),triW(n),1./2.6).g;sAlb=vec3(.004,.0042,.005);sRough=mix(.14,.42,smoothstep(.55,.8,g));sMetal=0.;sNrm=n;sAO=1.;sEmit=vec3(.30,.02,.05)*smoothstep(.78,.95,g)*(.05+.5*uTide);}`;
SURF.glass = `{vec3 n=safeN(vLNrm);vec4 na=tri(tNoiseA,vLPos,triW(n),1./5.);sAlb=diffuse*.25;sRough=.12+.25*na.r;sMetal=0.;sNrm=n;sAO=1.;sEmit=diffuse*uP.x*(.5+.9*na.g)*(.7+.3*na.r);}`;
SURF.built = `{
 vec3 p=vLPos,n=safeN(vLNrm),w=triW(n);vec2 hs=max(vUvH,vec2(.001)),q=clamp(vUvM,-hs,hs);float edge=max(min(hs.x-abs(q.x),hs.y-abs(q.y)),0.);
 float partR=.5,faceR=.5;
 #if defined(USE_COLOR) || defined(USE_COLOR_ALPHA)
 partR=vColor.r;faceR=vColor.g;
 #endif
 vec4 na=tri(tNoiseA,p+partR*31.,w,1./11.),nb=tri(tNoiseA,p,w,1./1.9),nc=tri(tNoiseB,p+partR*17.,w,1./4.3);
 float vert=1.-smoothstep(.35,.8,abs(n.y)),upF=smoothstep(.55,.95,n.y),top=max(hs.y-q.y,0.),bot=max(hs.y+q.y,0.);
 float sx=texture2D(tNoiseB,vec2(q.x*.21+faceR*9.,q.y*.012+partR)).g,sx2=texture2D(tNoiseB,vec2(q.x*.9+faceR*3.,q.y*.03)).g;
 float streak=(smoothstep(.5,.85,sx)*.7+smoothstep(.6,.9,sx2)*.3)*exp(-top/(3.+9.*faceR))*vert;
 vec2 pg=q/uPanel+vec2(faceR*.37,partR*.61),pf=(.5-abs(fract(pg)-.5))*uPanel;
 float seam=1.-smoothstep(0.,.05,min(pf.x,pf.y)),pid=hash11(dot(floor(pg),vec2(17.,59.))+faceR*91.+partR*13.);
 vec3 c;float rough,metal=0.;
 #ifdef K_CONC
 c=diffuse*(.80+.36*partR)*(.9+.2*pid)*(.78+.44*na.r);c*=1.-.35*seam;vec2 th=abs(fract(pg*2.)-.5)*uPanel*.5;c*=1.-.5*(1.-smoothstep(.05,.09,length(th)));
 c=mix(c,c*vec3(.36,.33,.31),streak*.9);c=mix(c,c*.5,exp(-bot/1.6)*vert*.8);
 float spall=smoothstep(.56,.62,nb.r*.5+nc.r*.5+.35*(1.-smoothstep(0.,.5,edge))-.12+.2*uP.x);
 c=mix(c,vec3(.20,.17,.145)*(.6+.8*nb.b),spall*.8);c=mix(c,vec3(.16,.07,.035),smoothstep(.72,.8,nc.r)*spall*.7*uP.y);rough=.92-.1*streak;sNrm=triN(tConcN,p,n,w,1./3.1,.55);
 #else
 vec3 paint=diffuse*(.80+.4*partR)*(.86+.28*pid);paint=mix(paint,vec3(dot(paint,vec3(.333)))*1.1,.3*na.r);
 #ifdef K_HAZARD
 paint=mix(vec3(.02),paint,step(.5,fract((q.x+q.y)/1.6)));
 #endif
 paint*=1.-.55*seam;float chipN=nb.r*.55+nc.r*.45,wm=(1.-smoothstep(0.,.34,edge))*.40+(na.r-.5)*.45*uP.x+uP.x*.07;
 float chip=smoothstep(.52,.56,chipN*.55+wm),rustA=smoothstep(.35,.7,nc.r*.7+na.r*.5)*uP.y;
 vec3 bare=mix(vec3(.20,.195,.19),vec3(.105,.052,.028)*(.6+.8*nb.r),rustA);c=mix(paint,bare,chip);metal=mix(uP.z,mix(.85,.05,rustA),chip);
 c=mix(c,vec3(.13,.055,.025),streak*(.35+.5*uP.y)*(1.-chip));c=mix(c,c*.42,exp(-bot/1.1)*vert*.75);
 rough=mix(mix(.5,.68,na.r),mix(.38,.9,rustA),chip);rough=mix(rough,.85,streak*.6);sNrm=triN(tMetalN,p,n,w,1./2.7,.45);
 #endif
 float dust=upF*(.35+.65*na.r)*uP.w;c=mix(c,vec3(.115,.10,.088),dust*.7);sAlb=clamp(c,0.,1.);sRough=mix(rough,.96,dust*.7);sMetal=metal*(1.-dust*.7);sAO=1.;sEmit=vec3(0.);
}`;
SURF.emit = `{
 float partR=.5,faceR=.5,userV=.5;
 #if defined(USE_COLOR) || defined(USE_COLOR_ALPHA)
 partR=vColor.r;faceR=vColor.g;userV=vColor.b;
 #endif
 float h1=hash11(userV*91.7+faceR*13.),h2=hash11(userV*57.3+7.);vec3 col=diffuse;
 float load=max(.16*uTide,pressureAt(vWPos.xz));
 #ifdef K_WINDOW
 float cycle=uTime/(37.+140.*h2)+h1*10.,slot=floor(cycle);float previous=step(.16,hash11((slot-1.)*3.7+h1*100.)),current=step(.16,hash11(slot*3.7+h1*100.));
 float on=mix(previous,current,smoothstep(0.,1.,fract(cycle)*(37.+140.*h2)/2.5)),lvl=(.25+.75*h1)*on;
 col=mix(col,col*vec3(1.,.8,.55),h2);col=mix(col,vec3(.55,.75,1.)*dot(col,vec3(.4)),step(.9,h2));
 float blind=mix(1.,.25,step(.55,h2)*step(vUvM.y/max(vUvH.y,1.e-3),-.1+.8*h1));sEmit=col*lvl*blind*uP.x*(1.-.75*load);
 #elif defined(K_BEACON)
 float ph=.5+.5*sin(uTime*(.5+.35*partR)+partR*40.);sEmit=col*(.10+.9*ph*ph)*uP.x*(1.+.35*load);
 #else
 #ifdef K_COOL
 col=vec3(.41,.52,.52);
 #endif
 sEmit=col*uP.x*(.85+.15*h1)*(1.-.80*load);
 #endif
 sAlb=vec3(.01);sRough=.5;sMetal=0.;sNrm=safeN(vLNrm);sAO=1.;
}`;
const LIGHT = `{
 vec2 suv=worldUV(vWPos);vec4 sp=texture2D(tSplat,suv);float lum=dot(sp.rgb,vec3(.3,.5,.2))+1.e-4,ly=sp.a/lum,e=1.5/1024.;
 float gx=dot(texture2D(tSplat,suv+vec2(e,0)).rgb-texture2D(tSplat,suv-vec2(e,0)).rgb,vec3(.3,.5,.2));
 float gz=dot(texture2D(tSplat,suv+vec2(0,e)).rgb-texture2D(tSplat,suv-vec2(0,e)).rgb,vec3(.3,.5,.2));
 vec2 g=vec2(gx,-gz)/lum;float gLen=length(g);vec3 Lv=vec3(g.x,0,g.y)/max(gLen,1.e-4)*clamp(gLen*4.,0.,1.)+vec3(0,clamp((ly-vWPos.y)/9.,-1.,1.)+.3,0);
 vec3 Ld=Lv/max(length(Lv),1.e-3),nW=inverseTransformDirection(normal,viewMatrix);float ndl=.22+.78*max(dot(nW,Ld),0.);float att=exp(-abs(vWPos.y-ly)/24.);
 reflectedLight.directDiffuse+=sp.rgb*uSplatGain*ndl*att*material.diffuseColor;reflectedLight.indirectDiffuse*=sAO;reflectedLight.directDiffuse*=mix(1.,sAO,.55);
 #ifdef ORBITAL
 vec3 skyBounce=vec3(.18,.28,.32)*(.3+.7*max(dot(nW,vec3(-.83,.5,.31)),0.));
 reflectedLight.indirectDiffuse+=material.diffuseColor*(skyBounce+vec3(.24,.039,.032)*max(dot(nW,vec3(-.50,-.33,-.8)),0.));
 #endif
 float rr=length(vWPos.xz-uLode.xz);vec3 toL=vec3(uLode.x,uLode.y+64.,uLode.z)-vWPos;float dL=length(toL);
 float nlL=max(dot(nW,toL/max(dL,.001))*.7+.3,0.);
 vec3 lodeCol=mix(vec3(.86,.125,.095),vec3(.34,.235,.22),smoothstep(50.,300.,dL));
 vec3 art=lodeCol*uArt.x*nlL*pow(max(110./(dL+110.),0.),1.5);
 if (uWave.y > 0.0) {
   // Signed horizontal distance to the actual gravity reversal, in metres.
   float passage = uWave.x - rr;
   float ground = texture2D(tHeight, suv).r;
   float altitude = vWPos.y - (ground < -9000.0 ? -4.0 : ground);
   float coupled = (1.0-smoothstep(12.0,80.0,abs(altitude))) * (1.0-smoothstep(370.0,550.0,rr));
   float load = coupled * loadBehindFront(passage);
   reflectedLight.directDiffuse *= 1.0-.23*load;
   reflectedLight.indirectDiffuse *= 1.0-.12*load;
   // A steep advancing edge and a broader trailing shoulder form one pressure pulse.
   float roughEdge = (texture2D(tNoiseA, vWPos.xz/96.0).r-.5)*3.4;
   float dist = passage + roughEdge;
   float width = mix(9.0,26.0,smoothstep(-4.0,7.0,dist));
   float front = exp(-dist*dist/(width*width));
   art += vec3(1.0,.065,.043)*front*uWave.y*coupled*(.78+.22*nlL)*2.85;
 }
 reflectedLight.directDiffuse+=art*material.diffuseColor;
 vec2 sq=vWPos.xz-uShadow.xy;float cA=cos(uShadow.z),sA=sin(uShadow.z);sq=vec2(sq.x*cA+sq.y*sA,-sq.x*sA+sq.y*cA)/vec2(200.,125.);
 float thS=atan(sq.y,sq.x),eS=1.+.34*sin(thS*5.+uTime*.25)+.24*sin(thS*9.-uTime*.4);float shS=uShadow.w*(1.-smoothstep(eS*.5,eS,length(sq)));
 reflectedLight.directDiffuse*=1.-.9*shS;reflectedLight.indirectDiffuse*=1.-.75*shS;reflectedLight.directSpecular*=1.-.9*shS;reflectedLight.indirectSpecular*=1.-.75*shS;
}`;
export function surface(kind, opts = {}) {
  const m = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 1,
    metalness: 0,
    ...opts.params
  });
  m.userData.kind = kind;
  m.defines = {
    ...m.defines,
    ...opts.defines
  };
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, U, opts.uniforms);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + PARS_V).replace('#include <begin_vertex>', '#include <begin_vertex>\n' + MAIN_V);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + PARS_F + (kind === 'rock' ? '\nuniform float uScale;uniform vec3 uSeed,uTint;' : '') + (opts.pars || '')).replace('#include <color_fragment>', 'vec3 sAlb,sNrm,sEmit;float sRough,sMetal,sAO;\n' + SURF[kind] + '\ndiffuseColor.rgb=sAlb;').replace('#include <roughnessmap_fragment>', 'float roughnessFactor=clamp(sRough,.04,1.);').replace('#include <metalnessmap_fragment>', 'float metalnessFactor=clamp(sMetal,0.,1.);').replace('#include <normal_fragment_maps>', 'normal=safeN(vO2V*sNrm)*faceDirection;').replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance+=sEmit;').replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\n' + LIGHT).replace('#include <opaque_fragment>', 'if(any(isnan(outgoingLight))||any(isinf(outgoingLight))) outgoingLight=vec3(0.);outgoingLight=clamp(outgoingLight,vec3(0.),vec3(24.));outgoingLight=mix(outgoingLight,vec3(.012,.010,.022),1.-exp(-length(vViewPosition)*uArt.z));\n#include <opaque_fragment>');
  };
  m.customProgramCacheKey = () => kind + Object.keys(opts.defines || {}).join('.') + (opts.key || '');
  return m;
}
export function rockMaterial(seed = 0, scale = 1, tint = 0xffffff, defines = {}, colors = false) {
  return surface('rock', {
    defines,
    uniforms: {
      uScale: {
        value: scale
      },
      uSeed: {
        value: new THREE.Vector3(seed * 13.7, seed * 7.1, seed * 3.3)
      },
      uTint: {
        value: new THREE.Color(tint)
      }
    },
    params: {
      vertexColors: colors
    }
  });
}
const FAMILY = [[/^metal_hazard/, 'built', [2.4, 1.6], [.55, .7, 0, 1], {
  K_HAZARD: ''
}], [/^metal_/, 'built', [2.6, 1.7], [.5, .75, 0, 1]], [/^steel_rust/, 'built', [40, 40], [.9, 1, .2, 1]], [/^steel/, 'built', [40, 40], [.55, .8, .75, .9]], [/^hull_/, 'built', [5.2, 2.9], [.4, .5, .15, .35]], [/^conc/, 'built', [3.6, 1.8], [.5, .8, 0, 1], {
  K_CONC: ''
}], [/^rubber/, 'built', [50, 50], [0, 0, 0, 1]], [/^tarp/, 'built', [50, 50], [0, 0, 0, .6], {
  K_CONC: ''
}], [/^solar/, 'built', [1, 1.6], [0, 0, .6, .5]], [/^emit_red|^emit_amber/, 'emit', null, [2.6, 0, 0, 0], {
  K_BEACON: ''
}], [/^emit_warm|^emit_white$/, 'emit', null, [1.25, 0, 0, 0], {
  K_WINDOW: ''
}], [/^emit_cool|^emit_blue/, 'emit', null, [1.2, 0, 0, 0], {
  K_COOL: ''
}], [/^emit_/, 'emit', null, [1.6, 0, 0, 0]], [/^glass_warm/, 'glass', null, [.9, 0, 0, 0]], [/^glass/, 'glass', null, [0, 0, 0, 0]]];
export function builtMaterial(name, color) {
  for (const [re, kind, panel, p, defs] of FAMILY) if (re.test(name)) {
    const m = surface(kind, {
      defines: {
        BUILT: '',
        ...defs
      },
      uniforms: {
        uPanel: {
          value: new THREE.Vector2(...(panel || [3, 2]))
        },
        uP: {
          value: new THREE.Vector4(...p)
        }
      },
      params: {
        vertexColors: true,
        side: /^tarp|^glass_warm/.test(name) ? THREE.DoubleSide : THREE.FrontSide
      }
    });
    m.color.copy(color);
    m.name = name;
    return m;
  }
  return null;
}
