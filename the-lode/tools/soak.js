() => {
  const app = window.__mine,
    {
      sim,
      sys
    } = app,
    w = sim.world;
  const numbers = object => Object.fromEntries(Object.entries(object).filter(([, v]) => typeof v === 'number' || typeof v === 'string'));
  const times = [...sim.samples].sort((a, b) => a - b);
  const q = p => times[Math.min(times.length - 1, Math.floor(times.length * p))];
  let invalid = 0;
  for (let j = 0; j < w.count; j++) {
    const i = w.order[j];
    if (![w.x[i], w.y[i], w.z[i], w.vx[i], w.vy[i], w.vz[i]].every(Number.isFinite)) invalid++;
  }
  return {
    seconds: Math.round(sim.time),
    history: sim.history,
    invalidGrains: invalid,
    capacity: w.cap,
    physicsMs: {
      p50: q(.5),
      p95: q(.95),
      p99: q(.99),
      max: q(1),
      ewma: sim.ms,
      samples: times.length
    },
    ore: numbers(sys.ore),
    aim: sys.ore.solution,
    trains: numbers(sys.rail),
    freighter: numbers(sys.freighter),
    trucks: numbers(sys.trucks),
    tractor: numbers(sys.tractor),
    breaker: numbers(sys.breaker),
    crane: numbers(sys.crane),
    bridge: numbers(sys.bridge),
    ejecta: numbers(sys.ejecta),
    crucible: numbers(sys.crucible),
    tides: numbers(sys.tides),
    seep: numbers(sys.seep),
    orbit: numbers(sys.wheel),
    launcher: numbers(sys.launcher),
    halo: numbers(sys.halo),
    harbor: numbers(sys.harborFlight),
    tower: numbers(sys.towerMotion),
    watchCrew: { count: sys.watchCrew.workers.length },
    salvage: numbers(sys.salvage),
    rockfall: numbers(sys.rockfall),
    lights: app.lights.n,
    parts: Object.keys(app.objects)
  };
};
