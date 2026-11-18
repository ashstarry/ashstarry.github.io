import { Host } from '../physics/host.js';
import { sandbox } from '../physics/sandbox.js';
import { geometry, instances, GrainView } from './view.js';
import { anomaly } from './anomaly.js';
import { ore } from './ore.js';
import { railway } from './railway.js';
import { trucks } from './trucks.js';
import { tractor, moorings } from './tractor.js';
import { breaker } from './breaker.js';
import { portWork } from './port.js';
import { atmosphere } from './atmosphere.js';
import { space, debris } from './space.js';
import { crucible } from './crucible.js';
import { crew } from './crew.js';
import { labels } from './labels.js';
import { salvage } from './salvage.js';
import { rockfall } from './rockfall.js';
import { towerMotion } from './tower-motion.js';
import { harborFlight } from './harbor-flight.js';
import { watchCrew } from './watchcrew.js';
export async function install(app) {
  const name = app.params.get('test');
  app.sim = new Host(app, !!name);
  app.geometry = (p, n) => geometry(app, p, n);
  app.instances = (g, m, n) => instances(app, g, m, n);
  if (name) {
    for (const key of Object.keys(app.objects)) {
      const obj = app.scene.getObjectByName(key);
      if (obj) obj.visible = false;
    }
    sandbox(app, name);
    return;
  }
  anomaly(app);
  ore(app);
  railway(app);
  trucks(app);
  tractor(app);
  moorings(app);
  breaker(app);
  portWork(app);
  atmosphere(app);
  space(app);
  debris(app);
  crucible(app);
  crew(app);
  salvage(app);
  rockfall(app);
  towerMotion(app);
  harborFlight(app);
  watchCrew(app);
  labels(app);
  app.sim.add('grains', new GrainView(app, app.sim.world));
}
