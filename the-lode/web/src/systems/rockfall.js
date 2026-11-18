import * as T from 'three';
import { TAG, rng } from '../physics/world.js';
import { V, UP, instances } from './view.js';

// A worked face beside the bucket wheel. Cutting weakens local bonds; once a plate
// slips, part of its load transfers to its neighbours. The slope comes from height.bin.
export function rockfall(app) {
  const sim=app.sim, world=sim.world, random=rng(91407);
  const plates=[], count=21, meshes=[];
  const source=app.find('rocks','bench_slab'), inverse=new T.Matrix4(), local=new T.Matrix4();
  if (source) {
    source.updateWorldMatrix(true,true);
    inverse.copy(source.matrixWorld).invert();
    source.traverse(o => {
      if (!o.isMesh) return;
      const geometry=o.geometry.clone().applyMatrix4(local.multiplyMatrices(inverse,o.matrixWorld));
      const mesh=instances(app,geometry,o.material,count);
      mesh.receiveShadow=true; mesh.castShadow=true;
      meshes.push(mesh);
    });
  }
  if (!meshes.length) meshes.push(instances(app,app.geometry('rocks','chunk_b'),new T.MeshStandardMaterial({color:0x756253}),count));
  const norm=V(), arm=V(), slide=V(), scale=V(), axis=V();
  const turn=new T.Quaternion(), incline=new T.Quaternion(), matrix=new T.Matrix4(), acc=[0,0,0];
  function groundNormal(x,z) {
    const h=1.05;
    return norm.set(world.ground(x-h,z)-world.ground(x+h,z),2*h,world.ground(x,z-h)-world.ground(x,z+h)).normalize();
  }
  for (let j=0;j<3;j++) for (let i=0;i<7;i++) {
    const angle=(131+4.05*i+random()*2.3+j*.55)*Math.PI/180;
    const r=56+9*j+2.8*random(), size=2.3+2.5*random();
    const x=-78+Math.cos(angle)*r, z=-12-Math.sin(angle)*r;
    const n=groundNormal(x,z);
    const yaw=new T.Quaternion().setFromAxisAngle(UP,angle+Math.PI/2+(random()-.5)*.46);
    const rest=incline.setFromUnitVectors(UP,n).clone().multiply(yaw);
    const spawn=V(x,world.ground(x,z)+size*.285/Math.max(.27,n.y),z);
    plates.push({p:spawn.clone(),spawn,q:rest.clone(),rest,v:V(),w:V(),size,
      mode:'seam',age:0,pending:0,damage:.11+.64*random(),bond:.84+.48*random(),
      wear:.0013+.0016*random(),hold:0,display:1,neighbours:[]});
  }
  for (const a of plates) for (const b of plates) if (a!==b && a.spawn.distanceToSquared(b.spawn)<13.7**2) a.neighbours.push(b);
  function shed(s,system) {
    if (sim.time-system.lastSlip>7) system.cascades++;
    system.failures++; system.lastSlip=sim.time;
    s.mode='sliding'; s.age=0; s.hold=0;
    slide.set(-78-s.p.x,0,-12-s.p.z).normalize();
    s.v.copy(slide).multiplyScalar(2.6+2.4*random()); s.v.y=.3+random();
    s.w.set(.08-random()*.16,(random()-.5)*.33, .22-random()*.45);
    for (const other of s.neighbours) if (other.mode==='seam') other.pending+=.19+random()*.12;
    for(let k=0;k<4;k++) world.spawn(TAG.SPILL,s.p.x+(random()-.5)*s.size,s.p.y+.7,s.p.z+(random()-.5)*s.size,{
      kind:k===0?1:2,r:.35+random()*.4,vx:s.v.x+random()-.5,vy:1.2+random()*1.6,vz:s.v.z+random()-.5
    });
    app.sys.dust?.puff(s.p.x,s.p.y,s.p.z,1);
  }
  function move(s,dt,system) {
    const p=s.p,v=s.v;
    sim.field.accel(p.x,p.y,p.z,acc,2);
    v.x+=acc[0]*dt; v.y+=acc[1]*dt; v.z+=acc[2]*dt;
    p.addScaledVector(v,dt);
    const g=world.ground(p.x,p.z), n=groundNormal(p.x,p.z);
    // Ellipsoid support along the actual slope normal, using the current orientation.
    arm.copy(n).applyQuaternion(incline.copy(s.q).conjugate());
    const support=s.size*Math.hypot(arm.x,arm.y*.28,arm.z*.5);
    const depth=support-(p.y-g)*n.y;
    if (depth>0 && g>-9000) {
      const vn=v.dot(n), incoming=Math.max(0,-vn);
      p.addScaledVector(n,Math.min(depth,.16+incoming*dt));
      if (incoming>0) v.addScaledVector(n,incoming*(incoming>2.6?1.17:1));
      slide.copy(v).addScaledVector(n,-v.dot(n));
      const friction=.38*(incoming+Math.max(0,-n.x*acc[0]-n.y*acc[1]-n.z*acc[2])*dt);
      v.addScaledVector(slide,-Math.min(1,friction/Math.max(.001,slide.length())));
      arm.crossVectors(n,slide).divideScalar(Math.max(.6,s.size*.65));
      s.w.lerp(arm,Math.min(1,dt*(incoming>2?6.2:3.4)));
      if (incoming>3.4 && sim.time-s.lastDust>.5) {
        app.sys.dust?.puff(p.x,p.y,p.z,1.2); s.lastDust=sim.time;
      }
      s.hold=v.lengthSq()<.18?s.hold+dt:0;
    } else s.hold=0;
    const omega=s.w.length();
    if (omega>.0001) s.q.premultiply(turn.setFromAxisAngle(axis.copy(s.w).divideScalar(omega),Math.min(.08,omega*dt))).normalize();
    system.maxRunout=Math.max(system.maxRunout,s.p.distanceTo(s.spawn));
    if (s.mode==='eroding') return;
    if (s.hold>.95 || (depth>=0 && s.age>34 && s.v.lengthSq()<1.4)) {
      s.mode='bed'; s.age=0; system.deposited++;
    } else if (Math.hypot(p.x+78,p.z+12)<29 && p.y< -55 || p.y< -90) {
      s.mode='eroding'; s.age=0; system.eroded++;
      for (let k=0;k<3;k++) world.spawn(TAG.HALO,p.x+random()*2,p.y+random()*2,p.z+random()*2,{
        r:.5+random()*.4,kind:3,vx:v.x,vy:v.y*.2,vz:v.z
      });
    }
  }
  function uncover(s) {
    s.mode='expose'; s.age=0; s.display=.001; s.p.copy(s.spawn); s.q.copy(s.rest);
    s.v.set(0,0,0); s.w.set(0,0,0); s.damage=.08+.2*random(); s.pending=0;
  }
  function separateLoose() {
    // Coarse contact spheres cover the dense cores of two moving plates.
    for(let i=0;i<plates.length;i++) {
      const a=plates[i];
      if(a.mode!=='sliding') continue;
      for(let j=0;j<i;j++) {
        const b=plates[j];
        if(b.mode!=='sliding') continue;
        arm.subVectors(a.p,b.p);
        const min=.58*(a.size+b.size), distance=arm.length();
        if(distance>=min || distance<.001) continue;
        arm.divideScalar(distance);
        const share=b.size**3/(a.size**3+b.size**3);
        const correction=Math.min(min-distance,.20);
        a.p.addScaledVector(arm,correction*share);
        b.p.addScaledVector(arm,-correction*(1-share));
        const vn=slide.subVectors(a.v,b.v).dot(arm);
        if(vn<0) {
          a.v.addScaledVector(arm,-1.14*vn*share);
          b.v.addScaledVector(arm,1.14*vn*(1-share));
        }
      }
    }
  }
  for(const s of plates) s.lastDust=-100;
  let previousDug=0;
  const system={failures:0,cascades:0,deposited:0,reclaimed:0,eroded:0,active:0,maxRunout:0,lastSlip:-100,
    face:plates[10].spawn,plates,
    pre(dt) {
      const dug=app.sys.ore?.dug||0, cut=Math.max(0,dug-previousDug);
      previousDug=dug; this.active=0;
      const wave=sim.field.wave;
      for(const s of plates) {
        s.age+=dt;
        if (s.mode==='seam') {
          const transfer=s.pending*(1-Math.exp(-dt*1.6));
          s.pending-=transfer;
          const front=Math.max(0,1-Math.abs(Math.hypot(s.p.x+78,s.p.z+12)-wave.r)/19);
          s.damage+=transfer+s.wear*cut+.24*dt*front*wave.a;
          if(s.damage>=s.bond) shed(s,this);
        } else if (s.mode==='sliding') {
          this.active++; move(s,dt,this);
        } else if (s.mode==='eroding') {
          s.display=Math.max(.001,1-s.age/1.7);
          move(s,dt,this);
          if(s.age>=1.7) uncover(s);
        } else if (s.mode==='bed') {
          // A downstream cut reclaims talus. A new layer is exposed at the upper face as work continues.
          if(s.age>17 && cut && random()<.055) {s.mode='bury'; s.age=0;}
        } else if (s.mode==='bury') {
          s.display=Math.max(.001,1-s.age/4.8);
          if(s.age>=4.8) {
            this.reclaimed++; uncover(s);
          }
        } else {
          s.display=Math.min(1,.001+s.age/9.5);
          if(s.display>=1) {s.mode='seam';s.age=0;}
        }
      }
      if (this.active>1) separateLoose();
    },
    frame() {
      for(let i=0;i<count;i++) {
        const s=plates[i], k=Math.max(.001,s.size*s.display);
        matrix.compose(s.p,s.q,scale.setScalar(k));
        for(const mesh of meshes) mesh.setMatrixAt(i,matrix);
      }
      for(const mesh of meshes) {mesh.count=count;mesh.instanceMatrix.needsUpdate=true;}
    }
  };
  sim.add('rockfall',system);
}
