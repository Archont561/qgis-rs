#!/usr/bin/env node
/**
 * Example: using qgis-rs Node.js API at native Rust speed (or JS fallback)
 *
 * Install:
 *   npm install qgis-rs
 *   # or for dev:
 *   # cd ts-packages/qgis-node && npm install && npm run build
 *
 * Run:
 *   node examples/typescript_api.js
 */

const path = require('path');
const fs = require('fs');
const os = require('os');

// Try to load from npm package or local dev
let qgisRs;
try {
  qgisRs = require('qgis-rs');
} catch (_) {
  try {
    qgisRs = require('../ts-packages/qgis-node/index.js');
  } catch (e) {
    console.error('qgis-rs not found. Install with: npm install qgis-rs or cd ts-packages/qgis-node && npm install');
    process.exit(1);
  }
}

console.log(`qgis-rs version: ${qgisRs.version()}`);
console.log(`Has native: ${qgisRs._hasNative}`);
console.log();

console.log('=== Extent ===');
const extent = qgisRs.Extent.parse('14,50,15,51');
console.log(`Parsed: ${extent.toString()}`);
console.log(`Width: ${extent.width()}, Height: ${extent.height()}`);
console.log(`Contains 14.5,50.5: ${extent.contains(14.5, 50.5)}`);
console.log();

console.log('=== CRS ===');
const crs4326 = qgisRs.Crs.fromEpsg(4326);
const crs3857 = qgisRs.Crs.fromEpsg(3857);
console.log(`4326: ${crs4326.authId}, geographic=${crs4326.isGeographic()}`);
console.log(`3857: ${crs3857.authId}, projected=${crs3857.isProjected()}`);
console.log();

console.log('=== Tile planning (pure Rust, no QGIS) ===');
const zooms = qgisRs.ZoomRange.parse('10-14');
const plan = new qgisRs.TilePlan(extent, zooms);
console.log(`Bounds: ${plan.bounds.toString()}`);
console.log(`Zooms: ${plan.zooms.min}-${plan.zooms.max}`);
console.log(`Total tiles: ${plan.tileCount()}`);
for (const level of plan.levels()) {
  console.log(`  z=${level.zoom}: x ${level.xMin}..${level.xMax}, y ${level.yMin}..${level.yMax}, ${level.tileCount()} tiles`);
}

const result = qgisRs.planTiles('14,50,15,51', '10-14');
console.log(`\nplanTiles() fast path: ${result.total} tiles`);
console.log();

console.log('=== Project ===');
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qgis-rs-test-'));
const projectPath = path.join(tmpDir, 'map.qgs');
fs.writeFileSync(projectPath, '<qgis></qgis>');
const project = qgisRs.Project.open(projectPath);
console.log(`Opened: ${project.path}, format=${project.format}`);
const info = project.info();
console.log(`Info: ${info.toJson ? info.toJson() : JSON.stringify(info)}`);
console.log();

console.log('=== CLI via Node.js (native speed when binary present) ===');
console.log('$ qgis-cli info map.qgs');
console.log(`Would run: npx qgis-cli info ${projectPath}`);
console.log('For demo, using JS API:');
console.log(`path:    ${info.path}`);
console.log(`format:  ${info.format}`);
console.log(`size:    ${info.sizeBytes || info.size_bytes} bytes`);
console.log();

fs.rmSync(tmpDir, { recursive: true });

console.log('Done — for full rendering, install QGIS: conda install -c conda-forge qgis');
