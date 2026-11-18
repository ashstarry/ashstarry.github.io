import * as T from 'three';
import { FreeRotor } from '../physics/rotor.js';
import { rng } from '../physics/world.js';
import { V, segments, lineInstance } from './view.js';

export function salvage(app) {
  const sim = app.sim, random = rng(19071);
  const docks = [
    app.mark('fill', 'salvage_lift', [-67, 16, 232]),
    app.mark('fill', 'salvage_catch', [-14, 19, 242])
  ];
  const sheaves = [
    app.mark('fill', 'salvage_lift_sheave', [-67,41,232]),
    app.mark('fill', 'salvage_catch_sheave', [-14,45,242])
  ];
  const eye = app.mark('fleet', 'salvage_eye', [.2, 2.2, .1]);
  const moments = app.layout.fleet?.rigids?.salvage_yoke?.inertiaPerMass || [36, 101, 68];
  const rotor = new FreeRotor(moments), load = app.clone('fleet', 'salvage_yoke', false);
  const resting = [new T.Quaternion().setFromEuler(new T.Euler(-.32,-.43,.12)),
    new T.Quaternion().setFromEuler(new T.Euler(.21,.29,-.11))];
  rotor.q.copy(resting[0]);
  const position = docks[0].clone(), velocity = V(), axis = V(0,0,1);
  const temp = V(), trial = V(), trialV = V(), spinup = new T.Quaternion(), acceleration = [0,0,0];
  const hooks = docks.map(p => p.clone()), liftEye = V(), target = V(), next = V(), prev = V();
  const cables = segments(app, 12, .19, 0x51473c);
  const hookMesh = new T.InstancedMesh(new T.TorusGeometry(.76,.18,6,15), cables.material, 2);
  hookMesh.frustumCulled = false;
  app.scene.add(hookMesh);
  const matrix = new T.Matrix4();
  let from = 0, age = 0, spinTime = 3.4, flight = 14.2, motor = 1.48;
  let earliest = 2.2, lastCut = -1, polarity = 1, launchEnergy = 1;
  function advance(p, v, h) {
    sim.field.accel(p.x,p.y,p.z,acceleration,2);
    v.x += acceleration[0]*h; v.y += acceleration[1]*h; v.z += acceleration[2]*h;
    p.addScaledVector(v,h);
  }
  function cast() {
    const goal = docks[1-from];
    velocity.subVectors(goal,position).divideScalar(flight);
    // Aim the powered handoff from a short test flight in the field as it is now.
    for (let pass=0; pass<3; pass++) {
      trial.copy(position); trialV.copy(velocity);
      for (let i=0; i<40; i++) advance(trial,trialV,flight/40);
      velocity.addScaledVector(temp.subVectors(goal,trial),1/flight);
    }
    rotor.release(temp.set(.082+.025*random(),-.045,from ? -motor : motor));
    launchEnergy = Math.max(1e-8,rotor.energy());
    polarity = from ? -1 : 1;
    run.phase = 'free'; age = 0; run.released++;
  }
  function updateHooks(dt) {
    liftEye.copy(eye).applyQuaternion(rotor.q).add(position);
    for (let j=0; j<2; j++) {
      const held = (j===from && (run.phase==='service' || run.phase==='spin')) || (j!==from && run.phase==='brake');
      if (held) { hooks[j].copy(liftEye); continue; }
      target.copy(sheaves[j]); target.y-=3.4;
      if (j!==from && run.phase==='free' && age>flight*.45) {
        target.copy(docks[j]).addScaledVector(temp.copy(liftEye).sub(position),1);
        if (position.distanceTo(docks[j])<9) target.copy(liftEye);
      }
      temp.subVectors(target,hooks[j]);
      hooks[j].addScaledVector(temp,Math.min(1,dt*7/Math.max(.001,temp.length())));
    }
  }
  const run = {
    phase:'service', position, rotor, transfers:0, released:0, flips:0, maxEnergyError:0, lastMiss:0,
    pre(dt) {
      age += dt;
      if (this.phase==='service') {
        rotor.q.slerp(resting[from],1-Math.exp(-1.6*dt));
        const cuts = app.sys.crew?.cuts || 0;
        if (age>=earliest && (cuts>lastCut || age>=earliest+7) && app.U.uTide.value<.68) {
          this.phase='spin'; age=0; lastCut=cuts;
          spinTime=3.1+random()*1.3; flight=13.5+random()*2.4; motor=1.43+random()*.18;
        }
      } else if (this.phase==='spin') {
        const speed=(from?-1:1)*motor*Math.min(1,age/spinTime);
        rotor.q.multiply(spinup.setFromAxisAngle(axis,speed*dt)).normalize();
        if (age>=spinTime) cast();
      } else if (this.phase==='free') {
        advance(position,velocity,dt);
        rotor.step(dt/2); rotor.step(dt/2);
        const alignment = temp.copy(axis).applyQuaternion(rotor.q).dot(rotor.L)/Math.max(.001,rotor.L.length());
        if (alignment*polarity<-.76) { this.flips++; polarity*=-1; }
        this.maxEnergyError = Math.max(this.maxEnergyError,Math.abs(rotor.energy()/launchEnergy-1));
        if (age>=flight) {
          this.lastMiss = position.distanceTo(docks[1-from]);
          this.phase='brake'; age=0;
        }
      } else {
        const goal = docks[1-from];
        // The powered recovery block absorbs the incoming load over several metres.
        temp.subVectors(goal,position).multiplyScalar(2.2).addScaledVector(velocity,-2.45).clampLength(0,5.5);
        velocity.addScaledVector(temp,dt);
        position.addScaledVector(velocity,dt);
        rotor.L.multiplyScalar(Math.exp(-1.05*dt));
        rotor.step(dt);
        if (age>.8) rotor.q.slerp(resting[1-from],1-Math.exp(-1.5*dt));
        if (age>3 && position.distanceToSquared(goal)<.023 && velocity.lengthSq()<.055) {
          from=1-from; this.transfers++; this.phase='service'; age=0;
          earliest=3.8+random()*4.5; lastCut=app.sys.crew?.cuts || 0;
          velocity.set(0,0,0);
        }
      }
      updateHooks(dt);
    },
    frame() {
      load.position.copy(position); load.quaternion.copy(rotor.q);
      for (let j=0; j<2; j++) {
        const a=sheaves[j], b=hooks[j];
        const sag=Math.min(1.8,Math.hypot(a.x-b.x,a.z-b.z)*.05);
        prev.copy(a);
        for (let k=1;k<=6;k++) {
          const t=k/6;
          next.copy(a).lerp(b,t); next.y-=sag*4*t*(1-t);
          lineInstance(cables,j*6+k-1,prev,next);
          prev.copy(next);
        }
        hookMesh.setMatrixAt(j,matrix.makeTranslation(b.x,b.y,b.z));
      }
      cables.count=12; cables.instanceMatrix.needsUpdate=true; hookMesh.instanceMatrix.needsUpdate=true;
    }
  };
  sim.add('salvage',run);
}
