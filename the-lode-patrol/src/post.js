import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { U } from './materials.js';
const vert = 'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}';
export function post(app) {
  const {
    renderer: r,
    scene,
    camera
  } = app;
  const w = innerWidth,
    h = innerHeight;
  const rt = new THREE.WebGLRenderTarget(w * r.getPixelRatio(), h * r.getPixelRatio(), {
    type: THREE.HalfFloatType,
    samples: Math.min(4, r.capabilities.maxSamples),
    depthBuffer: true
  });
  const composer = new EffectComposer(r, rt);
  composer.setPixelRatio(r.getPixelRatio());
  composer.setSize(w, h);
  composer.addPass(new RenderPass(scene, camera));
  const clean = new ShaderPass({
    uniforms: {
      tDiffuse: {
        value: null
      }
    },
    vertexShader: vert,
    fragmentShader: `uniform sampler2D tDiffuse;varying vec2 vUv;void main(){vec3 c=texture2D(tDiffuse,vUv).rgb;if(isnan(c.r)||isinf(c.r))c.r=0.;if(isnan(c.g)||isinf(c.g))c.g=0.;if(isnan(c.b)||isinf(c.b))c.b=0.;gl_FragColor=vec4(clamp(c,0.,16.),1.);}`
  });
  composer.addPass(clean);
  if (app.params.get('bloom') !== '0') {
    const bloom = new UnrealBloomPass(new THREE.Vector2(w, h), .34, .6, 1.1);
    composer.addPass(bloom);
  }
  const grade = new ShaderPass({
    uniforms: {
      tDiffuse: {
        value: null
      },
      uTime: {
        value: 0
      },
      uTide: {
        value: 0
      }
    },
    vertexShader: vert,
    fragmentShader: `uniform sampler2D tDiffuse;
uniform float uTime,uTide; varying vec2 vUv;
float h(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
void main() {
  vec2 c=vUv-.5;
  vec3 col=min(texture2D(tDiffuse,vUv).rgb,vec3(12.));
  float l=dot(col,vec3(.3,.55,.15));
  col=mix(vec3(l),col,.80-.035*uTide);
  col*=vec3(.985,1.,1.005);
  col*=1.-.6*smoothstep(.16,.75,dot(c,c)*1.6);
  col+=(h(vUv*913.+fract(uTime)*71.)-.5)*mix(.0008,.010,smoothstep(.004,.18,l));
  gl_FragColor=vec4(max(col,vec3(0.)),1.);
}`
  });
  grade.uniforms.uTime = U.uTime;
  grade.uniforms.uTide = U.uTide;
  composer.addPass(grade);
  composer.addPass(new OutputPass());
  app.composer = composer;
}
