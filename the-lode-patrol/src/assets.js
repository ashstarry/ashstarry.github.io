import * as T from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { U, builtMaterial, surface, rockMaterial } from './materials.js';
import { missingPart, placeholder, coarseHeight, surfaceStandIn } from './fallback.js';
const loader = new GLTFLoader(),
  mats = new Map();
function apply(mesh) {
  const src = mesh.material,
    n = src.name;
  if (!mats.has(n)) {
    let m;
    if (n === 'ground' || n === 'lode' || n === 'relic') m = surface(n);else if (n.startsWith('rock')) m = rockMaterial(.31, 1, n.includes('moon') ? 0x9c879d : 0xffffff, n.includes('inner') ? {
      INNER: ''
    } : {}, true);else m = builtMaterial(n, src.color) || src;
    m.name = n;
    mats.set(n, m);
  }
  mesh.material = mats.get(n);
  mesh.castShadow = !n.startsWith('emit');
  mesh.receiveShadow = true;
}
export async function loadAssets(app, onProgress = () => {}) {
  const wanted = (app.params.get('parts') || 'terrain,habitat,rail,plant,pit,bwe,port,fleet,rocks,fill,watchcrew,rimworks').split(',');
  app.missingParts = [];
  const progress = new Float32Array(wanted.length + 1);
  function report(index, fraction) {
    progress[index] = Math.max(progress[index], fraction);
    onProgress(progress.reduce((a,b) => a+b,0) / progress.length);
  }
  const result = await Promise.all(wanted.map(async (part, index) => {
    let layout = {};
    try {
      const meta = await fetch('./assets/' + part + '.json');
      if (meta.ok) layout = await meta.json();
      report(index,.05);
      const gltf = await loader.loadAsync('./assets/' + part + '.glb', event => {
        if (event.lengthComputable && event.total > 0) report(index,.05 + .78 * Math.min(1,event.loaded / event.total));
      });
      return {
        part,
        layout,
        root: gltf.scene
      };
    } catch (e) {
      app.missingParts.push(part);
      return missingPart(part, layout);
    } finally {
      report(index,1);
    }
  }));
  for (const item of result) {
    if (!item) continue;
    const {
      part,
      layout,
      root
    } = item;
    app.layout[part] = layout;
    const map = app.objects[part] = {};
    root.name = part;
    root.traverse(o => {
      map[o.name] = o;
      if (o.isMesh && !item.placeholder) apply(o);
    });
    app.scene.add(root);
    root.updateMatrixWorld(true);
    if (part === 'fleet' || part === 'rocks' || part === 'watchcrew') {
      for (const o of root.children) if (!o.name.endsWith('_static')) o.visible = false;
    }
    const template = map.bridge_seg;
    if (template) template.visible = false;
    for (const l of layout.lights || []) {
      if ((part === 'rocks' || part === 'fleet' || part === 'watchcrew') && l.obj !== 'static') continue;
      if (l.obj === 'bridge_seg') continue;
      app.lights.add(l, l.obj === 'static' ? null : map[l.obj]);
    }
  }
  try {
    const grid = await fetch('./assets/height.bin');
    if (!grid.ok) throw Error('height.bin');
    app.height = new Float32Array(await grid.arrayBuffer());
    if (app.height.length !== 1024 * 1024) throw Error('height grid size');
  } catch {
    app.height = coarseHeight();
    app.missingParts.push('height');
  }
  report(wanted.length,1);
  if (app.missingParts.includes('terrain')) surfaceStandIn(app.objects.terrain.terrain, app.height);
  const t = new T.DataTexture(app.height, 1024, 1024, T.RedFormat, T.FloatType);
  t.needsUpdate = true;
  U.tHeight.value = t;
  app.find = (part, name) => app.objects[part]?.[name] || null;
  app.mark = (part, name, fallback) => new T.Vector3(...(app.layout[part]?.markers?.[name]?.p || fallback || [0, 0, 0]));
  app.clone = (part, name, register = true) => {
    const orig = app.find(part, name);
    let c;
    if (orig) {
      c = orig.clone(true);
      c.visible = true;
    } else {
      c = new T.Group();
      const fallback = placeholder(name);
      c.add(fallback);
    }
    app.scene.add(c);
    if (register && orig) {
      for (const l of app.layout[part].lights || []) {
        const obj = c.getObjectByName(l.obj);
        if (obj) app.lights.add(l, obj);
      }
    }
    return c;
  };
  // Draw the static steel of all buildings once per material. Dynamic pivots and templates stay independent.
  app.batchStatic = () => {
    const groups = new Map();
    app.scene.updateMatrixWorld(true);
    for (const part of Object.keys(app.objects)) {
      let s = app.find(part, part + '_static');
      if (!s || part === 'rocks') continue;
      s.traverse(o => {
        if (o.isMesh && o.geometry && o.visible) {
          const list = groups.get(o.material) || [];
          list.push(o);
          groups.set(o.material, list);
        }
      });
    }
    for (const [m, meshes] of groups) {
      if (meshes.length < 2) continue;
      const geos = meshes.map(o => o.geometry.clone().applyMatrix4(o.matrixWorld));
      const g = mergeGeometries(geos, false);
      if (!g) continue;
      const mesh = new T.Mesh(g, m);
      mesh.name = 'site_' + m.name;
      mesh.castShadow = meshes[0].castShadow;
      mesh.receiveShadow = true;
      app.scene.add(mesh);
      for (const o of meshes) o.visible = false;
      for (const geo of geos) geo.dispose();
    }
  };
}
