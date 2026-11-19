import * as T from 'three';

const up = new T.Vector3(0,1,0);
const down = new T.Vector3(0,-1,0);
const cold = new T.Color(0xe5f2ff);
const silver = new T.Color(0xfff4df);

function head(app, position, color) {
  const pivot = new T.Group();
  const steel = new T.MeshStandardMaterial({color:0x504b40,metalness:.72,roughness:.42});
  const back = new T.Mesh(new T.CylinderGeometry(.81,1.02,1.65,16),steel);
  const lip = new T.Mesh(new T.CylinderGeometry(1.04,1.04,.22,20),steel);
  lip.position.y = -.78;
  const glass = new T.Mesh(new T.CircleGeometry(.84,24),
    new T.MeshBasicMaterial({color:color.clone().multiplyScalar(4.2)}));
  glass.rotation.x = Math.PI/2;
  glass.position.y = -.91;
  pivot.add(back,lip,glass);
  pivot.position.copy(position);
  app.scene.add(pivot);
  return pivot;
}

// The halo is angular and depth-tested. Looking across the lens creates a brief glint.
function lens(app, color) {
  const uniforms = {tint:{value:color}, gain:{value:0}, pixelAngle:{value:0}};
  const material = new T.ShaderMaterial({
    uniforms, transparent:true, blending:T.AdditiveBlending,depthWrite:false,
    vertexShader:`varying vec2 vP; uniform float gain,pixelAngle;
      void main(){vP=position.xy*2.;vec4 mv=modelViewMatrix*vec4(0.,0.,0.,1.);
      float size=max(2.7,-mv.z*pixelAngle*3.8)*(1.+.68*gain);
      mv.xy+=vP*size;gl_Position=projectionMatrix*mv;}`,
    fragmentShader:`varying vec2 vP;uniform vec3 tint;uniform float gain;
      void main(){float r=length(vP);float core=exp(-88.*r*r), veil=exp(-8.*r*r);
      float star=exp(-45.*abs(vP.x))*exp(-5.*abs(vP.y))+
                 exp(-52.*abs(vP.y+.11*vP.x))*exp(-4.*abs(vP.x));
      float a=(core*(1.1+gain*2.2)+veil*.21+star*gain*.25)*(1.-smoothstep(.75,1.,r));
      gl_FragColor=vec4(tint,a);}`
  });
  const mesh=new T.Mesh(new T.PlaneGeometry(1,1),material);
  mesh.renderOrder=5;
  app.scene.add(mesh);
  return mesh;
}

function dustShaft(app,color) {
  const material = new T.ShaderMaterial({
    uniforms:{ tint:{value:color}, intensity:{value:1},clock:app.U.uTime,noiseMap:app.U.tNoiseA },
    transparent:true,depthWrite:false,blending:T.AdditiveBlending,side:T.FrontSide,
    vertexShader:`varying vec2 vUV;varying vec3 vFace,vEye;void main(){
      vUV=uv;vec4 mv=modelViewMatrix*vec4(position,1.);
      vFace=normalMatrix*normal;vEye=-mv.xyz;gl_Position=projectionMatrix*mv;}`,
    fragmentShader:`varying vec2 vUV;varying vec3 vFace,vEye;uniform vec3 tint;
      uniform float intensity,clock;uniform sampler2D noiseMap;
      void main(){float t=vUV.y;float density=texture2D(noiseMap,vec2(vUV.x*3.,t*1.9-clock*.021)).r;
      float soft=pow(clamp(dot(normalize(vFace),normalize(vEye)),0.,1.),.72);
      float a=intensity*(.027+.046*density)*soft*pow(max(0.,1.-t),.8);
      gl_FragColor=vec4(tint,a);}`
  });
  // Local +Y points down the beam. Unit mouth gets scaled to match the spot aperture.
  const mesh=new T.Mesh(new T.CylinderGeometry(1,.033,1,32,1,true),material);
  app.scene.add(mesh);
  mesh.renderOrder=3;
  return mesh;
}

function routeAt(route,time,target) {
  const n=route.length;
  const step=Math.floor(time);
  const u=time-step;
  // A short dwell at each inspection point lets a flange or a stair become legible.
  const v=Math.max(0,Math.min(1,(u-.09)/.82));
  return target.lerpVectors(route[step%n],route[(step+1)%n],v*v*(3-2*v));
}

function instrument(app,origin,route,color,phase,leg,aperture) {
  const {camera,scene}=app;
  const lamp = new T.SpotLight(color,1,310,aperture,.68,2);
  lamp.castShadow = true;
  lamp.shadow.mapSize.set(app.handheld ? 256 : 512,app.handheld ? 256 : 512);
  lamp.shadow.camera.near=2.2;
  lamp.shadow.bias=-.00035;
  lamp.shadow.normalBias=.14;
  lamp.shadow.autoUpdate=false;
  let nextShadow=-1;
  lamp.position.copy(origin);
  scene.add(lamp,lamp.target);
  const housing=head(app,origin,color), shine=lens(app,color), shaft=dustShaft(app,color);
  const target=new T.Vector3(), direction=new T.Vector3(), eye=new T.Vector3();
  const rim=app.sim.field.lode;
  const tideTarget=new T.Vector3(rim.x,-53,rim.z);
  return {
    target, origin, lamp,
    frame(time,tide) {
      routeAt(route,time/leg+phase,target);
      target.lerp(tideTarget, Math.min(1,tide*1.55));
      direction.subVectors(target,origin);
      const distance=Math.max(1,direction.length());
      direction.multiplyScalar(1/distance);
      lamp.target.position.copy(target);
      lamp.target.updateMatrixWorld();
      if(time>=nextShadow) {
        lamp.shadow.needsUpdate=true;
        nextShadow=time+(app.handheld ? .24 : .13);
      }
      // Hold roughly the same illuminance as the travel distance changes.
      lamp.intensity=Math.min(190000,Math.max(2200,distance*distance*12.5))*(1-.72*tide);
      housing.quaternion.setFromUnitVectors(down,direction);
      shine.position.copy(origin).addScaledVector(direction,.98);
      const alignment=eye.subVectors(camera.position,shine.position).normalize().dot(direction);
      const glint=T.MathUtils.smoothstep(alignment,-.22,.72);
      shine.material.uniforms.gain.value=(.10+1.42*glint*glint)*(1-.64*tide);
      shine.material.uniforms.pixelAngle.value=2*Math.tan(camera.fov*Math.PI/360)/app.renderer.getSize(pixelSize).y;
      shaft.position.copy(origin).addScaledVector(direction,distance*.50);
      const width=Math.tan(aperture)*distance;
      shaft.scale.set(width,distance,width);
      shaft.quaternion.setFromUnitVectors(up,direction);
      shaft.material.uniforms.intensity.value=.96-.58*tide;
    }
  };
}
const pixelSize=new T.Vector2();

export function patrol(app) {
  const mark=(part,name,fallback)=>app.mark(part,name,fallback);
  const onGround=(x,z,offset=1.3)=>new T.Vector3(x,app.sim.world.ground(x,z)+offset,z);
  const central=mark('pit','gantry_search',[27,69,-13]);
  const lights=[instrument(app,central,[
    mark('plant','updraft_top',[98,62,-8]),new T.Vector3(120,12,56),
    mark('rimworks','cable_brake',[96,5,159]),mark('plant','mitt_mouth',[40,26,8]),new T.Vector3(74,17,8)
  ],silver,.28,4.7,.125)];
  let wheel=null;
  if(app.layout.rimworks?.markers?.patrol_mount) {
    const north=mark('rimworks','patrol_mount');
    lights.push(instrument(app,north,[
      mark('rimworks','fan_inlet'),mark('rimworks','cyclone_shell'),onGround(-100,-106,3),
      mark('pit','wall_rim',[-89,2,-93]),onGround(-24,-100),onGround(-32,-119)
    ],cold,2.55,5.6,.128));
    wheel=app.find('rimworks','north_impeller');
  }
  let load=0,angle=0;
  app.sim.add('patrol',{
    lights,
    pre(dt) {
      load+=(app.U.uTide.value-load)*(1-Math.exp(-dt*1.75));
      angle=(angle+dt*(1.87-.86*load))%(Math.PI*2);
    },
    frame() {
      for(const light of lights) light.frame(app.sim.time,load);
      if(wheel)wheel.rotation.z=-angle;
    }
  });
}
