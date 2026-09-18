#!/usr/bin/env node
/**
 * qgis-cli — Node.js wrapper for Rust-native qgis-cli binary
 * 
 * When installed via npm, this script tries to run the Rust binary
 * qgis-cli at native speed. If binary not found, falls back to Node.js
 * implementation using the NAPI addon.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Try to find Rust binary
function findBinary(name) {
  const possiblePaths = [
    path.join(__dirname, '..', 'target', 'release', name),
    path.join(__dirname, '..', '..', '..', 'target', 'release', name),
    path.join(__dirname, name),
    path.join(__dirname, '..', name),
  ];

  // Also check for binary installed via cargo
  const cargoHome = process.env.CARGO_HOME || path.join(require('os').homedir(), '.cargo', 'bin');
  possiblePaths.push(path.join(cargoHome, name));

  // Check if binary is on PATH
  const { execSync } = require('child_process');
  try {
    const which = process.platform === 'win32' ? 'where' : 'which';
    const result = execSync(`${which} ${name}`, { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] });
    const found = result.trim().split('\n')[0];
    if (found) possiblePaths.unshift(found);
  } catch (_) {
    // ignore
  }

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
    // Try with .exe on Windows
    if (process.platform === 'win32' && fs.existsSync(p + '.exe')) {
      return p + '.exe';
    }
  }
  return null;
}

function runWithFallback(args) {
  // Pure JS fallback for commands that don't need QGIS
  const qgisRs = require('../index.js');
  
  const command = args[0];
  
  if (command === 'version' || args.includes('--version') || args.includes('-V')) {
    console.log(`qgis-cli ${qgisRs.version()} (Node.js ${qgisRs._hasNative ? 'native' : 'fallback'})`);
    return 0;
  }
  
  if (command === 'info') {
    const projectPath = args[1];
    if (!projectPath) {
      console.error('qgis-cli: info requires a project path');
      return 1;
    }
    try {
      const project = qgisRs.Project.open(projectPath);
      const info = project.info();
      const isJson = args.includes('--json');
      if (isJson) {
        console.log(info.toJson ? info.toJson() : JSON.stringify({
          path: info.path,
          format: info.format,
          size_bytes: info.sizeBytes || info.size_bytes,
          note: info.note,
        }, null, 2));
      } else {
        console.log(`path:    ${info.path}`);
        console.log(`format:  ${info.format}`);
        console.log(`size:    ${info.sizeBytes || info.size_bytes} bytes`);
        console.log(`crs:     ${info.crs ? info.crs.authId : 'unknown'}`);
        if (info.note) console.log(`note:    ${info.note}`);
      }
      return 0;
    } catch (e) {
      console.error(`qgis-cli: ${e.message}`);
      return 1;
    }
  }
  
  if (command === 'tiles') {
    // Parse args: -z, -b, -o, --dry-run
    let zoom = null, bounds = null, output = null, dryRun = false;
    for (let i = 0; i < args.length; i++) {
      if ((args[i] === '-z' || args[i] === '--zoom') && i + 1 < args.length) zoom = args[++i];
      if ((args[i] === '-b' || args[i] === '--bounds') && i + 1 < args.length) bounds = args[++i];
      if ((args[i] === '-o' || args[i] === '--output') && i + 1 < args.length) output = args[++i];
      if (args[i] === '--dry-run') dryRun = true;
    }
    
    if (!zoom || !bounds) {
      console.error('qgis-cli: tiles requires --zoom and --bounds');
      return 1;
    }
    
    try {
      const result = qgisRs.planTiles(bounds, zoom);
      if (dryRun) {
        for (const level of result.levels) {
          console.log(`z=${level.zoom.toString().padEnd(3)} x ${level.xMin}..${level.xMax}  y ${level.yMin}..${level.yMax}  ${level.tileCount} tiles`);
        }
        console.log(`Would render ${result.total} tiles across zoom levels ${zoom}`);
        return 0;
      } else {
        console.error('qgis-cli: tile rendering needs the QGIS backend, which is not wired up yet');
        console.error(`Plan would render ${result.total} tiles — use --dry-run to see breakdown`);
        return 1;
      }
    } catch (e) {
      console.error(`qgis-cli: ${e.message}`);
      return 1;
    }
  }
  
  console.error(`qgis-cli: unknown command ${command} (and Rust binary not found)`);
  console.error('Available commands in fallback: info, tiles --dry-run, version');
  return 1;
}

function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log('qgis-cli — Render, tile, inspect and serve QGIS projects (native Rust speed)');
    console.log('');
    console.log('Usage: qgis-cli <command> [options]');
    console.log('');
    console.log('Commands:');
    console.log('  render    Render a project to an image (needs QGIS backend)');
    console.log('  tiles     Render a tile pyramid (dry-run works without QGIS)');
    console.log('  info      Describe a project');
    console.log('  serve     Start HTTP server (needs QGIS backend)');
    console.log('  export    Export features (needs QGIS backend)');
    console.log('  mcp       Model Context Protocol server');
    console.log('  version   Print version');
    console.log('');
    console.log('Examples:');
    console.log('  qgis-cli info map.qgs --json');
    console.log('  qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/ --dry-run');
    console.log('  qgis-cli render map.qgs -o map.png');
    console.log('');
    console.log('Node.js API:');
    console.log('  const { Project, Extent, TilePlan } = require("qgis-rs");');
    return 0;
  }

  // Try Rust binary first for native speed
  const binary = findBinary('qgis-cli');
  if (binary) {
    const child = spawn(binary, args, { stdio: 'inherit' });
    child.on('exit', (code) => process.exit(code || 0));
    child.on('error', (err) => {
      console.error(`qgis-cli: failed to run binary ${binary}: ${err.message}`);
      console.error('Falling back to Node.js implementation...');
      process.exit(runWithFallback(args));
    });
  } else {
    // Fallback to JS implementation
    process.exit(runWithFallback(args));
  }
}

main();
