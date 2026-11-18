import * as THREE from 'three';
export const DARK_STAR = new THREE.Vector3(-0.50, -0.33, -0.80).normalize();
export const KEY_DIR = new THREE.Vector3(-0.83, 0.5, 0.31).normalize();
const FRAG = /* glsl */`
varying vec3 vDir; uniform float uTime; uniform float uTide; uniform vec3 uStar; uniform vec3 uKey; uniform float uBake;
float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float vnoise(vec3 x){vec3 i=floor(x);vec3 f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float fbm(vec3 p){float a=.5,s=0.;for(int i=0;i<5;i++){s+=a*vnoise(p);p=p*2.03+7.1;a*=.5;}return s;}
float ridge(vec3 p){float a=.5,s=0.;for(int i=0;i<4;i++){float n=1.-abs(vnoise(p)*2.-1.);s+=a*n*n;p=p*2.1+3.7;a*=.5;}return s;}
float stars(vec3 d,float sc,float th){vec3 p=d*sc;vec3 i=floor(p),f=fract(p)-.5;float h=hash(i);float r=length(f+(vec3(hash(i+3.1),hash(i+5.7),hash(i+9.2))-.5)*.6);return step(th,h)*(1.-smoothstep(0.,.09,r))*(.4+.6*hash(i+1.3));}
// A long interstellar dust bank attenuates the far sky along one open edge.
float cloudTransmission(vec3 d, vec3 star, float time){
  vec3 east=normalize(cross(star,vec3(0.,1.,0.)));
  vec3 north=cross(east,star);
  float facing=dot(d,star);
  if(facing<.28) return 1.;
  vec2 sky=vec2(dot(d,east),dot(d,north))/facing;
  // Tangent plane at the stellar limb, ten degrees north of its eastern ansa.
  float along=dot(sky,vec2(.98480775,.17364818));
  float across=dot(sky,vec2(-.17364818,.98480775));
  along+=.012*sin(time*.0021); across+=.008*sin(time*.00165);
  if(along<.19 || abs(across)>.58) return 1.;
  float broad=vnoise(vec3(along*6.8,across*9.2,3.17))-.5;
  float fold=vnoise(vec3(along*14.1+across*6.4,across*17.,6.2))-.5;
  float grains=vnoise(vec3(along*23.0+fold*1.5,across*31.,.7));
  float front=along-.272+.049*broad+.023*fold;
  float run=max(front,0.);
  float spine=-.047*(along-.42)+.018*sin((along-.42)*10.)+.022*broad;
  // A torn fold hangs below the main bank. Its ragged skirts transmit the stars' own light.
  float weight=(along-.54)/.086;
  float foldFoot=.032*exp(-weight*weight)*(.62+.65*grains);
  float upper=spine+.013+.184*run+.024*broad+.018*fold+.010*(grains-.5)-across;
  float lower=across-spine+.011+.148*run-.016*broad+.014*fold+foldFoot+.013*(grains-.5);
  float depth=min(front*.68,min(upper,lower));
  float skirt=smoothstep(-.064,.023,depth+.014*fold);
  float veil=smoothstep(-.032,.024,depth);
  float core=smoothstep(-.003,.032,depth);
  float opticalDepth=(.29*skirt+veil*(.61+.49*grains)+core*(3.1+2.8*grains))*smoothstep(.28,.58,facing);
  return exp(-opticalDepth);
}
void main(){
 vec3 d=normalize(vDir);float ang=acos(clamp(dot(d,uStar),-1.,1.));const float R=.40;
 vec3 q=d*1.7+vec3(.3,1.7,-.6);vec3 wq=q+1.6*vec3(fbm(q*1.3),fbm(q*1.3+4.),fbm(q*1.3+8.));
 float cloud=fbm(wq),fil=ridge(wq*1.9+2.),lane=smoothstep(.5,.78,fbm(q*2.6+3.));
 float nearKey=pow(max(dot(d,uKey),0.),2.2),nearStar=1.-smoothstep(R,1.5,ang);
 vec3 col=vec3(.003,.0038,.007),teal=vec3(.020,.075,.085),indigo=vec3(.030,.034,.090),blood=vec3(.130,.018,.030);
 float neb=smoothstep(.38,.80,cloud);
 col+=neb*mix(indigo,teal,clamp(nearKey*1.6+.15,0.,1.))*(.55+1.3*nearKey);
 col+=pow(max(fil,0.),3.)*mix(vec3(.03,.05,.07),blood*.9,nearStar)*(.35+.9*neb);
 col+=nearStar*nearStar*blood*(.035+.10*cloud);col*=1.-.8*lane*(1.-.6*nearKey);
 float st=stars(d,190.,.80)*1.5+stars(d,420.,.72)*.7+stars(d,80.,.955)*3.4+stars(d,900.,.62)*.3;
 float tw=.8+.2*sin(uTime*.9+hash(floor(d*80.))*40.);
 vec3 scol=mix(vec3(.72,.86,1.),vec3(1.,.82,.66),hash(floor(d*190.)+2.));
 col+=st*tw*scol*(1.-.7*lane)*(.4+.6*(1.-neb))*smoothstep(R*1.02,R*1.9,ang)*(1.-uBake);
 float x=ang/R;
 if(x<1.){
  vec3 sp=d*9.+uStar*uTime*.004;float cell=fbm(sp*1.4+2.*fbm(sp*.6));float limb=pow(max(x,0.),6.);
  vec3 body=vec3(.0075,.0012,.002)*(.3+1.7*cell)*(.35+.65*(1.-x*x));body+=vec3(.085,.007,.012)*limb*(.5+.8*cell);body+=vec3(.42,.045,.04)*pow(max(x,0.),60.)*(.5+.7*vnoise(d*40.));col=body;
 }else{
  float o=ang-R;float streak=ridge(vec3(atan(d.x-uStar.x,d.z-uStar.z)*3.,ang*6.,1.)+.6*fbm(d*5.));
  col+=vec3(.15,.012,.018)*exp(-o*46.)*(.6+.6*streak);col+=vec3(.011,.0012,.004)*exp(-o*8.)*(.4+.9*streak);
 }
 col=mix(col,col*vec3(1.35,.62,.6)+vec3(.006,0,.001),uTide*.7);col*=cloudTransmission(d,uStar,uTime);col*=1.+5.*uBake;gl_FragColor=vec4(col,1.);
}`;
export function buildSky(app) {
  const geo = new THREE.SphereGeometry(6000, 48, 32);
  const mk = bake => new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      uTime: {
        value: 0
      },
      uTide: {
        value: 0
      },
      uStar: {
        value: DARK_STAR
      },
      uKey: {
        value: KEY_DIR
      },
      uBake: {
        value: bake
      }
    },
    vertexShader: 'varying vec3 vDir; void main(){vDir=normalize(position);vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_Position.z=gl_Position.w;}',
    fragmentShader: FRAG
  });
  const mat = mk(0),
    dome = new THREE.Mesh(geo, mat);
  dome.frustumCulled = false;
  dome.renderOrder = -10;
  app.scene.add(dome);
  const bakeScene = new THREE.Scene(),
    bakeMat = mk(1);
  bakeScene.add(new THREE.Mesh(geo, bakeMat));
  const cubeRT = new THREE.WebGLCubeRenderTarget(256, {
      type: THREE.HalfFloatType
    }),
    cc = new THREE.CubeCamera(1, 8000, cubeRT);
  cc.update(app.renderer, bakeScene);
  const pmrem = new THREE.PMREMGenerator(app.renderer),
    envRT = pmrem.fromCubemap(cubeRT.texture);
  app.scene.environment = envRT.texture;
  app.scene.environmentIntensity = 1.;
  pmrem.dispose();
  cubeRT.dispose();
  bakeMat.dispose();
  app.sky = {
    dome,
    mat,
    env: envRT.texture,
    envRT
  };
}
