import * as T from 'three';
import { clamp } from '../physics/world.js';
import { V, UP, segments, lineInstance } from './view.js';

const advance = (a,b,limit) => a + clamp(b-a,-limit,limit);
const wrap = a => Math.atan2(Math.sin(a),Math.cos(a));

function engineBells(app,ship) {
  // A broad, translucent exhaust skirt. Brightest at the nozzle, fading to its tip.
  const profile=[new T.Vector2(1,0),new T.Vector2(.86,.24),new T.Vector2(.44,.69),new T.Vector2(.02,1)];
  const geo=new T.LatheGeometry(profile,12).rotateZ(-Math.PI/2);
  const mat=new T.ShaderMaterial({
    side:T.DoubleSide,transparent:true,depthWrite:false,blending:T.AdditiveBlending,
    uniforms:{tint:{value:new T.Color().setRGB(.17,.36,.35)}},
    vertexShader:`varying float along; varying float angle;
      void main(){along=position.x;angle=uv.x*6.2831853;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`varying float along; varying float angle;uniform vec3 tint;
      void main(){float k=clamp(1.-along,0.,1.);float f=k*k*(.69+.21*cos(2.*angle)+.10*cos(5.*angle));
      gl_FragColor=vec4(tint,.48*f);}`
  });
  const bells=[];
  for(const end of ['fore','aft']) for(const hand of ['p','s']) {
    const sign=end==='fore'?1:-1;
    const jet=new T.Mesh(geo,mat);
    jet.position.copy(app.mark('fleet','lighter_jet_'+end+'_'+hand,[sign*20.5,-.1,hand==='p'?6.2:-6.2]));
    jet.rotation.y=sign>0?0:Math.PI;
    jet.renderOrder=3;
    ship.add(jet);
    bells.push({jet,sign,hand:hand==='p'?1:-1});
  }
  return bells;
}

export function harborFlight(app) {
  const sim=app.sim, field=sim.field, ground=sim.world.ground;
  function terminal(x,z,nx,nz) {
    const orientation=-Math.atan2(nz,nx);
    const base=ground(x-17.6*nx,z-17.6*nz);
    const deck=V(x,(base>-9000?base:-4)+4.2,z);
    const cradle=app.clone('fleet','harbor_cradle');
    cradle.position.copy(deck); cradle.rotation.y=orientation;
    return {deck,hover:deck.clone().add(V(0,34,0)),seat:deck.clone().add(V(0,4.29,0)),
      q:new T.Quaternion().setFromAxisAngle(UP,orientation)};
  }
  const docks=[terminal(-213,89,-.916,.401),terminal(30,220,.102,.995)];
  const path=new T.CatmullRomCurve3([
    docks[0].hover,V(-210,75,64),V(-196,103,50),V(-172,122,61),V(-150,136,87),
    V(-128,143,130),V(-108,141,169),V(-104,127,204),V(-77,113,228),
    V(-42,102,241),V(-5,91,250),V(24,70,246),V(34,52,234),docks[1].hover
  ]);
  // Sample distance once; the route is a flight director's reference, not the ship's position.
  const samples=path.getSpacedPoints(205), length=path.getLength(), interval=length/(samples.length-1);
  function route(s,p,tangent) {
    const u=clamp(s/interval,0,samples.length-1), i=Math.min(samples.length-2,Math.floor(u));
    p.lerpVectors(samples[i],samples[i+1],u-i);
    tangent.subVectors(samples[i+1],samples[i]).normalize();
  }
  const ship=app.clone('fleet','harbor_lighter'), reel=app.clone('fleet','harbor_reel'),
    spool=reel.getObjectByName('reel_spool'), wires=segments(app,8,.26,0x97806c), jets=engineBells(app,ship);
  const shipMass=825, reelMass=184, inertia=V(1190,2960,2680);
  const position=V(), velocity=V(), target=V(), tangent=V(), desiredV=V(), command=V(),
    loadPosition=V(), loadVelocity=V(), shipA=V(), loadA=V(), torque=V(), shipTorque=V(), acceleration=[0,0,0],
    q=new T.Quaternion(), reelQ=new T.Quaternion(), inv=new T.Quaternion(), delta=new T.Quaternion(),
    aim=new T.Euler(0,0,0,'YXZ'), omega=V(), axis=V(), tmp=V(), b=V(), dir=V(), local=V(), localCommand=V(),
    r1=V(),r2=V(),v1=V(),v2=V(), shipOmega=V(), loadOmega=V(), oldPoint=V(), nextPoint=V();
  const lines=['aft','fore'].map((end,i)=>({
    fair:app.mark('fleet','lighter_fair_'+end,[i?6.15:-5.4,-2.42,0]),
    eye:app.mark('fleet','reel_eye_'+end,[i?4.44:-4.44,2.22,0]), tension:0
  }));
  const sailingLength=19.5;
  let distance=61,sign=1,speed=7.6,winch=sailingLength,stage=0,angle=0,spoolSpeed=0,
    roll=0,pitch=0,yawRate=0,pitchRate=0,rollRate=0;
  route(distance,position,tangent);
  velocity.copy(tangent).multiplyScalar(speed);
  let yaw=-Math.atan2(tangent.z,tangent.x);
  q.setFromAxisAngle(UP,yaw);
  reelQ.copy(q); loadPosition.copy(position).add(V(-3,-23,1));
  loadVelocity.copy(velocity);
  const run={position,velocity,loadPosition,loadVelocity,ship,reel,docks,phase:'haul',
    tension:0,slings:[0,0],transfers:0,pickups:0,distanceFlown:0,peakSwing:0,swing:0,
    maxRoll:0,speed:velocity.length(),loadMass:reelMass,spoolTurns:0};

  function gravity(p,acc) {
    field.accel(p.x,p.y,p.z,acceleration,8);
    return acc.set(acceleration[0],acceleration[1],acceleration[2]);
  }
  function pilot(h) {
    const dock=docks[sign>0?1:0];
    stage+=h;
    if(run.phase==='haul') {
      const remain=sign>0?length-distance:distance;
      const cruise=(8.4+.8*Math.sin(distance*.026))*(1-.10*app.U.uTide.value);
      speed=advance(speed,Math.min(cruise,Math.sqrt(2*1.58*Math.max(0,remain))),1.7*h);
      const lag=position.distanceTo(target);
      const follow=target.lengthSq()>0 && lag>14 ? clamp((36-lag)/22,.25,1):1;
      distance=clamp(distance+sign*speed*h*follow,0,length);
      route(distance,target,tangent); desiredV.copy(tangent).multiplyScalar(sign*speed);
      if(remain<.1 && position.distanceToSquared(dock.hover)<12 && velocity.lengthSq()<2.4) {
        run.phase='lower'; stage=0;
      }
    } else {
      target.copy(dock.hover); desiredV.set(0,0,0);
      if(run.phase==='lower') {
        winch=advance(winch,26.05,1.35*h);
        if(winch>25.95 && loadPosition.distanceToSquared(dock.seat)<1.0 && loadVelocity.lengthSq()<.85) {
          run.phase='exchange';stage=0;run.transfers++;
        }
      } else if(run.phase==='exchange') {
        if(stage>3.2+.28*(run.transfers%4)) { run.phase='lift';stage=0; }
      } else {
        winch=advance(winch,sailingLength,1.85*h);
        if(winch<sailingLength+.01 && stage>6) {
          run.phase='haul';sign*=-1;stage=0;speed=0;run.pickups++;
        }
      }
    }
    // Subtract the field at both ends of the drive. Finite thrust and actual cable
    // reactions still determine the path, bank and stopping distance of the lighter.
    gravity(position,shipA);
    command.subVectors(target,position).multiplyScalar(.50).addScaledVector(desiredV,1.48)
      .addScaledVector(velocity,-1.48).sub(shipA).clampLength(0,4.8);
    shipA.add(command);
    let heading=-Math.atan2(sign*tangent.z,sign*tangent.x);
    const toEnd=sign>0?length-distance:distance;
    if(run.phase!=='haul'||toEnd<24) {
      const dockYaw=2*Math.atan2(dock.q.y,dock.q.w);
      heading+=wrap(dockYaw-heading)*(run.phase==='haul'?clamp(1-toEnd/24,0,1):1);
    }
    const dyaw=wrap(heading-yaw);
    yawRate=advance(yawRate,clamp(dyaw*.88,-.43,.43),.28*h);
    yaw=wrap(yaw+yawRate*h);
    inv.copy(q).invert(); localCommand.copy(command).applyQuaternion(inv);
    const bank=clamp(-localCommand.z*.070+yawRate*.18,-.27,.27);
    const climb=clamp(desiredV.y*.024+localCommand.x*.012,-.19,.19);
    rollRate+=(2.4*(bank-roll)-2.15*rollRate)*h;
    pitchRate+=(2.0*(climb-pitch)-1.95*pitchRate)*h;
    roll+=rollRate*h; pitch+=pitchRate*h;
    q.setFromEuler(aim.set(roll,yaw,pitch,'YXZ'));
    shipOmega.set(rollRate,0,pitchRate).applyQuaternion(q);shipOmega.y+=yawRate;
    run.maxRoll=Math.max(run.maxRoll,Math.abs(roll));
  }
  function integrate(h) {
    pilot(h);
    const dock=docks[sign>0?1:0], seated=run.phase==='exchange';
    gravity(loadPosition,loadA); torque.set(0,0,0);shipTorque.set(0,0,0);run.tension=0;
    loadOmega.copy(omega).applyQuaternion(reelQ);
    // Two independent unilateral Kelvin–Voigt ropes. Equal and opposite reactions
    // also act at the reel's off-centre eyes, so a turning lighter leaves it swinging.
    for(let i=0;i<lines.length;i++) {
      const line=lines[i];
      r1.copy(line.fair).applyQuaternion(q);r2.copy(line.eye).applyQuaternion(reelQ);
      dir.copy(loadPosition).add(r2).sub(position).sub(r1);
      const dist=dir.length();dir.multiplyScalar(1/Math.max(.001,dist));
      v1.crossVectors(shipOmega,r1).add(velocity);
      v2.crossVectors(loadOmega,r2).add(loadVelocity);
      const separating=v2.sub(v1).dot(dir);
      const stretch=dist-winch;
      const force=stretch>0?clamp(2100*stretch+318*separating,0,11800):0;
      line.tension=force;run.slings[i]=force;run.tension+=force;
      shipA.addScaledVector(dir,force/shipMass);
      loadA.addScaledVector(dir,-force/reelMass);
      torque.add(tmp.crossVectors(r2,dir).multiplyScalar(-force));
      shipTorque.add(tmp.crossVectors(r1,dir).multiplyScalar(force));
    }
    shipTorque.applyQuaternion(inv.copy(q).invert());
    rollRate+=shipTorque.x*h/37900;
    yawRate+=shipTorque.y*h/138000;
    pitchRate+=shipTorque.z*h/123000;
    // The two magnetic skid shoes hold the steel stillage clear of the keel in
    // free fall. The limited repulsive force and its recoil leave lateral swing free.
    if(run.phase==='haul') {
      axis.set(0,1,0).applyQuaternion(q);
      const below=tmp.subVectors(position,loadPosition).dot(axis);
      const closing=b.subVectors(loadVelocity,velocity).dot(axis);
      const press=clamp(.80+.096*(17-below)+.20*closing,0,2.4);
      loadA.addScaledVector(axis,-press);
      shipA.addScaledVector(axis,press*reelMass/shipMass);
    }
    if(run.phase==='lower' || seated || run.phase==='lift') {
      // The receiver grips the stillage with a damped magnetic brake in its last
      // few metres. The cradle spins the reel only while its brake is physically set.
      const goal=nextPoint.copy(dock.seat);
      if(run.phase==='lift') goal.y+=26.05-winch;
      if(run.phase==='lower')goal.y+=Math.max(0,26.05-winch);
      loadA.add(tmp.subVectors(goal,loadPosition).multiplyScalar(1.8)
        .addScaledVector(loadVelocity,-2.35).clampLength(0,8));
      reelQ.slerp(dock.q,1-Math.exp(-1.1*h));
      omega.multiplyScalar(Math.exp(-1.8*h));
    }
    if(!seated) {
      velocity.addScaledVector(shipA,h);
      loadVelocity.addScaledVector(loadA,h);
      loadPosition.addScaledVector(loadVelocity,h);
      inv.copy(reelQ).invert();torque.applyQuaternion(inv).divide(inertia);
      omega.addScaledVector(torque,h).multiplyScalar(1/(1+.22*h));
      const spin=omega.length();
      if(spin>.00001)reelQ.multiply(delta.setFromAxisAngle(axis.copy(omega).divideScalar(spin),spin*h)).normalize();
      // The underside's two skegs act as bump stops if angular overshoot closes a sling.
      local.subVectors(loadPosition,position).applyQuaternion(inv.copy(q).invert());
      if(Math.abs(local.x)<17 && Math.abs(local.z)<9 && local.y>-7.0) {
        loadPosition.addScaledVector(tmp.set(0,1,0).applyQuaternion(q),-7.0-local.y);
        const relative=b.subVectors(loadVelocity,velocity).dot(tmp);
        if(relative>0)loadVelocity.addScaledVector(tmp,-relative*1.08);
      }
    } else {
      velocity.addScaledVector(shipA,h);
      loadPosition.copy(dock.seat);loadVelocity.set(0,0,0);reelQ.copy(dock.q);omega.set(0,0,0);
    }
    const travel=velocity.length()*h; position.addScaledVector(velocity,h);run.distanceFlown+=travel;
    spoolSpeed=advance(spoolSpeed,seated?sign*1.85:0,(seated?1.30:.58)*h);
    angle+=spoolSpeed*h;run.spoolTurns+=Math.abs(spoolSpeed*h)/(2*Math.PI);
    run.speed=travel/h;
    local.subVectors(loadPosition,position).applyQuaternion(inv.copy(q).invert());
    run.swing=Math.hypot(local.x,local.z);run.peakSwing=Math.max(run.swing,run.peakSwing);
  }
  run.pre=dt=>{integrate(dt/2);integrate(dt/2);};
  run.frame=()=>{
    ship.position.copy(position);ship.quaternion.copy(q);reel.position.copy(loadPosition);reel.quaternion.copy(reelQ);
    if(spool)spool.rotation.z=angle;
    for(let i=0;i<lines.length;i++) {
      const l=lines[i];
      r1.copy(l.fair).applyQuaternion(q).add(position);r2.copy(l.eye).applyQuaternion(reelQ).add(loadPosition);
      const gap=r1.distanceTo(r2), droop=Math.min(5.3,Math.sqrt(Math.max(0,winch*winch-gap*gap))*.34);
      oldPoint.copy(r1);
      for(let k=1;k<=4;k++) {
        const u=k*.25;nextPoint.lerpVectors(r1,r2,u);nextPoint.y-=4*u*(1-u)*droop;
        lineInstance(wires,i*4+k-1,oldPoint,nextPoint);oldPoint.copy(nextPoint);
      }
    }
    wires.count=8;wires.instanceMatrix.needsUpdate=true;
    for(const e of jets) {
      const power=clamp(.035-e.sign*(localCommand.x*.30+e.hand*yawRate*.61)
        +Math.abs(localCommand.y)*.055,0,1);
      e.jet.visible=power>.06;
      e.jet.scale.set(.6+14.5*power,1.20+.40*power,1.20+.40*power);
    }
  };
  run.frame();
  sim.add('harborFlight',run);
}
