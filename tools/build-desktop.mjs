import { execFileSync } from 'node:child_process';
import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(root, '_desktop');
const dist = join(source, 'dist');
const manifestPath = join(root, 'desktop-build.json');
execFileSync('npm', ['run', 'build'], { cwd: source, stdio: 'inherit' });

async function listFiles(directory, prefix = '') {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const name = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await listFiles(join(directory, entry.name), name));
    else if (entry.isFile()) result.push(name);
  }
  return result;
}
function destination(file) {
  const target = resolve(root, file);
  if (relative(root, target).startsWith('..') || file.startsWith('.') || file.includes('\\')) throw new Error('Unsafe build path');
  return target;
}
const files = (await listFiles(dist)).sort();
let previous = [];
try { previous = JSON.parse(await readFile(manifestPath, 'utf8')).files || []; } catch { /* First build. */ }
for (const file of previous) {
  if (!files.includes(file) && file.startsWith('assets/')) await rm(destination(file), { force: true });
}
for (const file of files) {
  const target = destination(file);
  await mkdir(dirname(target), { recursive: true });
  await cp(join(dist, file), target);
}
await writeFile(manifestPath, JSON.stringify({ files }, null, 2) + '\n');
console.log(`Updated ${files.length} desktop files. Blog and Pages configuration were preserved.`);
