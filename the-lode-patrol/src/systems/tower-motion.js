// The two vertical inertia blocks share a hydraulic equalising line. Forces are kN,
// masses tonnes, spring rates kN/m. The guide rails remove the other five freedoms.
export function towerMotion(app) {
  const { sim } = app;
  const frame = app.layout.habitat?.markers;
  const design = [
    { id: 'a', sign: 1, mass: 126, spring: 55, damper: 30 },
    { id: 'b', sign: -1, mass: 115, spring: 52, damper: 33 }
  ];

  const axes = [];
  for (const spec of design) {
    const prefix = 'tuner_' + spec.id;
    const body = app.find('habitat', prefix + '_mass');
    if (!body || !frame?.[prefix + '_low'] || !frame[prefix + '_high']) continue;
    const low = app.mark('habitat', prefix + '_low');
    const high = app.mark('habitat', prefix + '_high');
    const centre = low.clone().lerp(high, .5);
    const head = app.mark('habitat', prefix + '_head');
    const eye = app.mark('habitat', prefix + '_eye');
    const reference = [0, 0, 0];
    sim.field.accel(centre.x, centre.y, centre.z, reference, 0);
    const wheel = app.find('habitat', prefix + '_sheave');
    axes.push({ ...spec, body, centre, low, high, head, eye, reference,
      wheel, rope: app.find('habitat', prefix + '_pendant'), localRest: body.position.y,
      wheelAxis: centre.clone().fromArray(frame[prefix + '_head'].axis).normalize(),
      wheelRest: wheel?.quaternion.clone(), gravity: [0, 0, 0], front: 0,
      x: spec.sign * -1.7, speed: spec.sign * .64, direction: spec.sign,
      min: 0, max: 0, travel: 0, force: 0
    });
  }
  const system = {
    axes, enabled: axes.length === 2, reversals: 0, fronts: 0, stops: 0, peakSpeed: 0,
    stroke: 0, pressure: 0, bearingForce: 0
  };
  if (!system.enabled) return sim.add('towerMotion', system);
  const gauge = axes[1].centre.clone().sub(axes[0].centre); gauge.y = 0; gauge.normalize();
  let lastFront = -1;

  system.pre = function (dt) {
    let tilt = 0;
    const wave = sim.field.wave;
    for (const a of axes) {
      // These blocks are rigidly guided and preloaded against the normal local gravity.
      // A passing change in the gradient bends the shoulder toward the anomaly.
      sim.field.accel(a.centre.x, a.centre.y + a.x, a.centre.z, a.gravity, 0);
      tilt += ((a.gravity[0] - a.reference[0]) * gauge.x +
               (a.gravity[2] - a.reference[2]) * gauge.z) * .5;
      const distance = Math.hypot(a.centre.x - wave.x, a.centre.z - wave.z);
      const band = (distance - wave.r) / 23;
      a.front = wave.a > 0 && Math.abs(band) < 3.4 ? wave.a * Math.exp(-band*band) : 0;
    }
    const tideCount = app.sys.tides?.count || 0;
    if (tideCount && lastFront !== tideCount && Math.max(axes[0].front, axes[1].front) > .1) {
      lastFront = tideCount;
      this.fronts++;
    }
    // The imbalance turns with the occupied ring (.11 rad/s). Each pass of its four
    // spokes across the fixed race adds a second, faster torque to the shoulder.
    const phase = sim.time * .11;
    this.bearingForce = 103 * Math.sin(phase - .58) + 204 * Math.sin(4 * phase + .24)
                      + 32 * Math.sin(2 * phase - 1.31) - 620 * tilt;
    const h = dt / 2;
    for (let pass = 0; pass < 2; pass++) {
      // Equal pressure acts on both cylinders; one descending block tends to lift its mate.
      this.pressure = 137 * (axes[0].x + axes[1].x) + 37 * (axes[0].speed + axes[1].speed);
      for (const a of axes) {
        const minX = a.low.y - a.centre.y, maxX = a.high.y - a.centre.y;
        const contact = a.x < minX + 1.65 ? a.x - minX - 1.65 :
                        a.x > maxX - 1.65 ? a.x - maxX + 1.65 : 0;
        const snubber = contact ? 315 * contact + (contact * a.speed > 0 ? 87 * a.speed : 0) : 0;
        a.force = a.sign * (this.bearingForce + 455 * a.front) + a.mass * (a.gravity[1] - a.reference[1])
                - a.spring * a.x - a.damper * a.speed - this.pressure - snubber;
        a.speed += (a.force / a.mass) * h;
        const previous = a.x;
        a.x += a.speed * h;
        if (a.x > maxX || a.x < minX) {
          a.x = Math.max(minX, Math.min(maxX, a.x));
          a.speed *= -.08;
          this.stops++;
        }
        if (a.speed * a.direction < -.13) { this.reversals++; a.direction = -a.direction; }
        a.min = Math.min(a.min, a.x); a.max = Math.max(a.max, a.x);
        a.travel += Math.abs(a.x - previous);
        this.peakSpeed = Math.max(this.peakSpeed, Math.abs(a.speed));
        this.stroke = Math.max(this.stroke, a.max - a.min);
      }
    }
  };
  system.frame = function () {
    for (const a of axes) {
      a.body.position.y = a.localRest + a.x;
      if (a.wheel) a.wheel.quaternion.setFromAxisAngle(a.wheelAxis, -a.x / 2.02).multiply(a.wheelRest);
      if (a.rope) a.rope.scale.y = 1 - a.x / (a.head.y - a.eye.y);
    }
  };
  return sim.add('towerMotion', system);
}
