/**
 * Example: using qgis-rs TypeScript API at native Rust speed
 *
 * Install:
 *   npm install qgis-rs
 *
 * Run:
 *   npx ts-node examples/typescript_api.ts
 *   # or compile: tsc examples/typescript_api.ts && node examples/typescript_api.js
 */

import { Project, Extent, TilePlan, ZoomRange, Crs, planTiles, version, MAX_LATITUDE, MAX_ZOOM } from 'qgis-rs';
// For local dev: import from '../ts-packages/qgis-node'

console.log(`qgis-rs version: ${version()}`);
console.log(`MAX_LATITUDE: ${MAX_LATITUDE}, MAX_ZOOM: ${MAX_ZOOM}`);
console.log();

// Extent parsing (pure Rust, no QGIS)
console.log('=== Extent ===');
const extent = Extent.parse('14,50,15,51');
console.log(`Parsed: ${extent.toString()}`);
console.log(`Width: ${extent.width()}, Height: ${extent.height()}`);
console.log(`Contains 14.5,50.5: ${extent.contains(14.5, 50.5)}`);
console.log();

// CRS handling
console.log('=== CRS ===');
const crs4326 = Crs.fromEpsg(4326);
const crs3857 = Crs.fromEpsg(3857);
console.log(`4326: ${crs4326.authId}, geographic=${crs4326.isGeographic()}`);
console.log(`3857: ${crs3857.authId}, projected=${crs3857.isProjected()}`);
console.log();

// Tile planning
console.log('=== Tile planning (pure Rust, no QGIS) ===');
const zooms = ZoomRange.parse('10-14');
const plan = new TilePlan(extent, zooms);
console.log(`Total tiles: ${plan.tileCount()}`); // 4568
for (const level of plan.levels()) {
  console.log(`  z=${level.zoom}: ${level.tileCount()} tiles`);
}

const result = planTiles('14,50,15,51', '10-14');
console.log(`\nplanTiles() fast path: ${result.total} tiles`);
console.log();

// Project
console.log('=== Project ===');
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qgis-rs-test-'));
const projectPath = path.join(tmpDir, 'map.qgs');
fs.writeFileSync(projectPath, '<qgis></qgis>');

const project = Project.open(projectPath);
console.log(`Opened: ${project.path}, format=${project.format}`);
const info = project.info();
console.log(`Info: ${info.toJson()}`);

fs.rmSync(tmpDir, { recursive: true });

console.log('\nDone — for full rendering, install QGIS: conda install -c conda-forge qgis');
