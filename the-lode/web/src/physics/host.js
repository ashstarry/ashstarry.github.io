import { Height, World } from './world.js';
import { Rigids } from './rigid.js';
export class Host {
  constructor(app, flat = false) {
    const h = new Height(app.height);
    this.world = new World(flat ? () => 0 : (x, z) => h.at(x, z));
    this.field = this.world.field;
    this.rigid = new Rigids(this.world);
    this.systems = [];
    this.ms = 0;
    this.samples = [];
    this.steps = 0;
    this.history = [];
    this.time = 0;
    this.app = app;
  }
  get count() {
    return this.world.count;
  }
  add(name, system) {
    this.app.sys[name] = system;
    this.systems.push(system);
    return system;
  }
  step(dt) {
    const measure = (this.steps++ & 31) === 0,
      b = measure ? performance.now() : 0;
    this.time += dt;
    for (const s of this.systems) s.pre?.(dt);
    this.world.step(dt);
    for (let i = 0; i < 3; i++) this.rigid.step(dt / 3);
    for (const s of this.systems) s.post?.(dt);
    if (this.steps % 3600 === 0) {
      const s = this.app.sys,
        ore = s.ore;
      if (ore) {
        let free = 0,
          sleeping = 0,
          held = 0;
        const w = this.world;
        for (let j = 0; j < w.count; j++) {
          const st = w.state[w.order[j]];
          if (st === 1) free++;else if (st === 2) sleeping++;else if (st === 3) held++;
        }
        this.history.push({
          seconds: Math.round(this.time),
          grains: w.count,
          free,
          sleeping,
          held,
          launches: ore.launched,
          caught: ore.caught,
          screened: ore.screened,
          raised: ore.raised,
          binned: ore.binned,
          waste: ore.wasteDropped,
          loaded: s.rail.loaded,
          received: s.freighter.received,
          tides: s.tides.count,
          casts: s.crucible?.drains || 0
        });
        if (this.history.length > 60) this.history.shift();
      }
    }
    if (measure) {
      const ms = performance.now() - b;
      this.ms = this.ms ? this.ms * .9 + ms * .1 : ms;
      this.samples.push(ms);
      if (this.samples.length > 160) this.samples.shift();
    }
  }
  frame(dt) {
    for (const s of this.systems) s.frame?.(dt);
  }
}
