// RGB stores irradiance. Alpha stores the luminance-weighted height, including negative mine levels.
import * as THREE from 'three';
import { U } from './materials.js';
import { pressureGLSL } from './pressure.js';
export class Lights {
  constructor(app, max = 1400) {
    this.app = app;
    this.max = max;
    this.n = 0;
    this.items = [];
    this.v = new THREE.Vector3();
    this.clearColor = new THREE.Color();
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
    g.setIndex([0, 1, 2, 0, 2, 3]);
    g.instanceCount = 0;
    this.aPos = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4).setUsage(THREE.DynamicDrawUsage);
    this.aCol = new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('aPos', this.aPos);
    g.setAttribute('aCol', this.aCol);
    this.geo = g;
    const common = `attribute vec4 aPos,aCol; uniform float uTime,uTide; uniform vec4 uLode,uWave;
varying vec2 vC; varying vec3 vCol; varying float vH;
${pressureGLSL}
float gain() {
  float k=floor(aCol.w), ph=fract(aCol.w);
  if(k==4.) return 1.;
  float load=max(.16*uTide,pressureAt(aPos.xz));
  if(k==1. || k==2.) {
    float t=.5+.5*sin(uTime*(.5+.35*ph)+ph*40.);
    return (.10+.9*t*t)*(1.+.35*load);
  }
  float intensity=k==3. ? .9+.1*sin(uTime*(.6+ph)+ph*40.) : 1.;
  return intensity*(1.-.82*load);
}`;
    this.splatMat = new THREE.ShaderMaterial({
      uniforms: {
        uRect: U.uWorldRect,
        uTime: U.uTime,
        uWave: U.uWave,
        uLode: U.uLode,
        uTide: U.uTide
      },
      blending: THREE.CustomBlending,
      blendEquation: THREE.AddEquation,
      blendSrc: THREE.OneFactor,
      blendDst: THREE.OneFactor,
      blendSrcAlpha: THREE.OneFactor,
      blendDstAlpha: THREE.OneFactor,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      side: THREE.DoubleSide,
      vertexShader: common + `uniform vec4 uRect;void main(){vC=position.xy;vCol=aCol.rgb*gain();vH=aPos.y;vec2 wp=aPos.xz+position.xy*aPos.w;vec2 uv=vec2(wp.x-uRect.x,-wp.y-uRect.y)/uRect.z;gl_Position=vec4(uv*2.-1.,0.,1.);}`,
      fragmentShader: `varying vec2 vC;varying vec3 vCol;varying float vH;void main(){float r2=dot(vC,vC);if(r2>1.)discard;float f=1.-r2;f=f*f/(1.+7.*r2);vec3 c=vCol*f;gl_FragColor=vec4(c,dot(c,vec3(.3,.5,.2))*vH);}`
    });
    this.splatScene = new THREE.Scene();
    this.splatMesh = new THREE.Mesh(g, this.splatMat);
    this.splatMesh.frustumCulled = false;
    this.splatScene.add(this.splatMesh);
    this.cam = new THREE.Camera();
    this.rt = new THREE.WebGLRenderTarget(1024, 1024, {
      type: THREE.HalfFloatType,
      format: THREE.RGBAFormat,
      depthBuffer: false
    });
    this.rt.texture.minFilter = this.rt.texture.magFilter = THREE.LinearFilter;
    U.tSplat.value = this.rt.texture;
    this.glowMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: U.uTime,
        uWave: U.uWave,
        uLode: U.uLode,
        uTide: U.uTide,
        uPx: {
          value: 1
        }
      },
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true,
      vertexShader: common + `uniform float uPx;void main(){vC=position.xy;vCol=aCol.rgb*gain();vec4 mv=viewMatrix*vec4(aPos.xyz,1.);float k=floor(aCol.w);float s=((k==3.||k==4.)?0.:1.)*(.4+.012*aPos.w);float minS=(k==4.?0.:1.)*(-mv.z)*uPx*(k==1.?2.2:1.3);mv.xy+=position.xy*max(s,minS);gl_Position=projectionMatrix*mv;}`,
      fragmentShader: `varying vec2 vC;varying vec3 vCol;void main(){float r=length(vC);if(r>1.)discard;float f=pow(max(1.-r,0.),3.)*1.4+.25*pow(max(1.-r,0.),12.);gl_FragColor=vec4(vCol*f*.42,1.);}`
    });
    this.glow = new THREE.Mesh(g, this.glowMat);
    this.glow.frustumCulled = false;
    this.glow.renderOrder = 5;
    app.scene.add(this.glow);
  }
  add(def, obj = null) {
    if (this.n >= this.max) return null;
    const kinds = {
      lamp: 0,
      flood: 0,
      beacon: 1,
      strobe: 1,
      window: 3,
      aura: 4
    };
    let c = def.c,
      power = def.i;
    if (c[2] > .72 * c[0] && c[1] > .6 * c[0]) {
      c = [.53, .65, .65];
      power *= .75;
    } else if (c[0] > .9 && c[1] < .2) power *= 1.3;
    const it = {
      i: this.n++,
      obj,
      p: new THREE.Vector3(...def.p),
      c,
      r: def.r,
      power,
      k: kinds[def.k] || 0,
      ph: this.n * .61803398875 % 1 * .98,
      on: 1
    };
    this.items.push(it);
    this.write(it);
    this.geo.instanceCount = this.n;
    return it;
  }
  write(it) {
    const v = this.v.copy(it.p);
    if (it.obj) it.obj.localToWorld(v);
    this.aPos.setXYZW(it.i, v.x, v.y, v.z, it.r);
    let visible = 1;
    for (let o = it.obj; o; o = o.parent) if (!o.visible) {
      visible = 0;
      break;
    }
    const s = it.power * it.on * visible;
    this.aCol.setXYZW(it.i, it.c[0] * s, it.c[1] * s, it.c[2] * s, it.k + it.ph);
  }
  update() {
    for (const it of this.items) if (it.obj || it.dirty) {
      this.write(it);
      it.dirty = false;
    }
    this.aCol.needsUpdate = this.aPos.needsUpdate = true;
    const r = this.app.renderer,
      cam = this.app.camera;
    this.glowMat.uniforms.uPx.value = Math.tan(cam.fov * Math.PI / 360) / (r.domElement.height / r.getPixelRatio() / 2);
    const old = r.getRenderTarget(),
      oc = r.getClearColor(this.clearColor),
      oa = r.getClearAlpha();
    r.setRenderTarget(this.rt);
    r.setClearColor(0, 0);
    r.clear();
    r.render(this.splatScene, this.cam);
    r.setRenderTarget(old);
    r.setClearColor(oc, oa);
  }
}
