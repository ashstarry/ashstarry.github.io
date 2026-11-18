import * as THREE from 'three';

// Local construction stand-ins keep each mechanism addressable during a rebuild.
const landmarks = {
  habitat: [['hab_ring', [96, 56, -146], [64, 3, 18]], ['spire', [96, 65, -146], [9, 110, 9]]],
  plant: [['mitt', [40, 17, 8], [24, 17, 24]], ['jig_gate_door', [84, 4, 27], [1, 6, 6]], ['shaft', [98, 31, -8], [9, 59, 9]], ['bin_gate_door', [114, 17, -8], [4, .5, 4]]],
  bwe: [['bwe_super', [-194, 14, -2], [25, 12, 17]], ['bwe_wheel', [-157, 3, -50], [5, 20, 20]], ['sling', [-167, 25, 60], [12, 4, 5]]],
  pit: [['mast', [27, 32, -13], [8, 65, 9]], ['maw', [27, 65, -13], [16, 4, 12]], ['tractor_head', [-62, 46, -62], [6, 4, 6]]],
  rail: [['whip', [241, 46, 88], [10, 105, 14]]],
  port: [['quay', [284, -7, 48], [26, 3, 102]], ['crane', [291.5, 9, 38], [9, 27, 8]], ['port_radar', [244, 24, -2], [8, 3, 5]]],
  fill: [['furnace', [50, 10, 151], [11, 27, 10]], ['wreck', [-48, -1, 173], [73, 7, 18]]]
};
const sizes = {
  freighter: [148, 15, 27],
  breaker: [41, 12, 16],
  truck: [15, 5.5, 7],
  wagon: [10, 4, 4],
  tug: [18, 6, 8],
  person_a: [.65, 2, .43],
  person_b: [.65, 2, .43],
  bridge_seg: [3.3, .7, 11]
};
const steel = new THREE.MeshStandardMaterial({
  color: 0x746555,
  roughness: .83
});
export function placeholder(name) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...(sizes[name] || [3, 2, 2])), steel);
  mesh.castShadow = mesh.receiveShadow = true;
  return mesh;
}
export function missingPart(part, layout = {}) {
  const root = new THREE.Group();
  for (const [name, p, s] of landmarks[part] || []) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...s), steel);
    mesh.name = name;
    mesh.position.fromArray(p);
    mesh.castShadow = mesh.receiveShadow = true;
    root.add(mesh);
  }
  return {
    part,
    layout,
    root,
    placeholder: true
  };
}
export function coarseHeight() {
  const data = new Float32Array(1024 * 1024);
  for (let j = 0; j < 1024; j++) for (let i = 0; i < 1024; i++) {
    const x = -256 + i * 576 / 1023,
      y = -288 + j * 576 / 1023,
      bite = 138 + .0045 * (y + 60) ** 2;
    const d = Math.hypot((x + 78) / 98, (y - 12) / 84),
      main = x < bite && Math.hypot(x, y) < 220;
    const sx = x - 70,
      sy = y + 20,
      shard = sx >= 138 + .0045 * (sy + 60) ** 2 && Math.hypot(sx, sy) < 220;
    data[j * 1024 + i] = main ? d < 1 ? -76 * (1 - d * d) : .025 * y : shard ? -8 : -9999;
  }
  return data;
}
export function surfaceStandIn(root, height) {
  const p = [],
    faces = [],
    n = 128,
    step = 8;
  for (let j = 0; j <= n; j++) for (let i = 0; i <= n; i++) {
    const a = Math.min(1023, i * step),
      b = Math.min(1023, j * step);
    p.push(-256 + a * 576 / 1023, height[b * 1024 + a], 288 - b * 576 / 1023);
  }
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const a = j * (n + 1) + i,
      b = a + 1,
      c = a + n + 1,
      d = c + 1;
    if ([a, b, c, d].every(k => p[k * 3 + 1] > -9000)) faces.push(a, b, d, a, d, c);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
  g.setIndex(faces);
  g.computeVertexNormals();
  const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: 0x645345,
    roughness: .94
  }));
  mesh.receiveShadow = true;
  root.add(mesh);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(34, 32, 20), new THREE.MeshStandardMaterial({
    color: 0x040405,
    roughness: .22
  }));
  cap.position.set(-78, -96, -12);
  root.add(cap);
}
