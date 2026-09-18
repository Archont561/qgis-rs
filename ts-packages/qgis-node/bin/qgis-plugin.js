#!/usr/bin/env node
/**
 * qgis-plugin — Node.js wrapper for Rust-native qgis-plugin binary
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function findBinary(name) {
  const possiblePaths = [
    path.join(__dirname, '..', 'target', 'release', name),
    path.join(__dirname, '..', '..', '..', 'target', 'release', name),
    path.join(__dirname, name),
  ];
  const cargoHome = process.env.CARGO_HOME || path.join(require('os').homedir(), '.cargo', 'bin');
  possiblePaths.push(path.join(cargoHome, name));

  try {
    const { execSync } = require('child_process');
    const which = process.platform === 'win32' ? 'where' : 'which';
    const result = execSync(`${which} ${name}`, { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'] });
    const found = result.trim().split('\n')[0];
    if (found) possiblePaths.unshift(found);
  } catch (_) {}

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) return p;
    if (process.platform === 'win32' && fs.existsSync(p + '.exe')) return p + '.exe';
  }
  return null;
}

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log('qgis-plugin — QGIS plugin SDK (Rust-native, from qgis-rs npm)');
    console.log('');
    console.log('Usage: qgis-plugin <command> [options]');
    console.log('');
    console.log('Commands:');
    console.log('  new       Scaffold a new plugin');
    console.log('  build     Build plugin');
    console.log('  test      Run tests');
    console.log('  install   Install into QGIS');
    console.log('  dev       Watch mode');
    console.log('  package   Create .zip');
    console.log('  validate  Check structure');
    console.log('  info      Show plugin info');
    console.log('  version   Print version');
    console.log('');
    return 0;
  }

  const binary = findBinary('qgis-plugin');
  if (binary) {
    const child = spawn(binary, args, { stdio: 'inherit' });
    child.on('exit', (code) => process.exit(code || 0));
    child.on('error', () => {
      console.error('qgis-plugin: binary failed, falling back to Python CLI if available');
      process.exit(1);
    });
  } else {
    console.log(`qgis-plugin: Rust binary not found, trying Python fallback...`);
    // Try Python CLI
    const { spawn: pySpawn } = require('child_process');
    const pyChild = pySpawn('python', ['-m', 'qgis_sdk.cli', ...args], { stdio: 'inherit' });
    pyChild.on('exit', (code) => process.exit(code || 0));
    pyChild.on('error', () => {
      console.error('qgis-plugin: no binary found. Install via: npm install qgis-rs or pip install qgis-sdk');
      process.exit(1);
    });
  }
}

main();
