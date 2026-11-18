import { Quaternion, Vector3 } from 'three';

// Principal moments are in the model frame. In free flight L stays in world space.
// A Lie midpoint step advances orientation on the unit-quaternion sphere.
export class FreeRotor {
  constructor(moments) {
    this.inverseMoments = new Vector3(...moments.map(i => 1 / i));
    this.q = new Quaternion();
    this.L = new Vector3();
    this.inverse = new Quaternion();
    this.half = new Quaternion();
    this.increment = new Quaternion();
    this.omega = new Vector3();
  }
  release(localOmega) {
    this.L.copy(localOmega).divide(this.inverseMoments).applyQuaternion(this.q);
  }
  velocity(rotation) {
    this.inverse.copy(rotation).conjugate();
    return this.omega.copy(this.L).applyQuaternion(this.inverse)
      .multiply(this.inverseMoments).applyQuaternion(rotation);
  }
  rotationStep(orientation, h, dest) {
    const omega = this.velocity(orientation);
    const speed = omega.length();
    if (speed < 1e-10) return dest.identity();
    return dest.setFromAxisAngle(omega.multiplyScalar(1 / speed), speed * h);
  }
  step(h) {
    this.rotationStep(this.q, h * .5, this.increment);
    this.half.copy(this.increment).multiply(this.q);
    this.rotationStep(this.half, h, this.increment);
    this.q.premultiply(this.increment).normalize();
  }
  energy() {
    return .5 * this.L.dot(this.velocity(this.q));
  }
}
