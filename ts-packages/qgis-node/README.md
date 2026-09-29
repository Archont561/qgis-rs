# qgis-rs — Node.js / TypeScript bindings with Rust-native CLI

[![npm](https://img.shields.io/npm/v/qgis-rs)](https://www.npmjs.com/package/qgis-rs)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

**qgis-rs** for Node.js — native-speed QGIS rendering, tiling, and plugin tools via NAPI-RS.

- **npm**: `npm install qgis-rs` → `require('qgis-rs')` + `qgis-cli` binary on PATH
- **API**: TypeScript types, pure Rust geometry (Extent, Crs, TilePlan) via NAPI, QGIS backend optional
- **CLI**: `qgis-cli` and `qgis-plugin` Rust binaries + Node.js wrappers, both native speed

`qgis-rs` (Python) and `qgis-sdk` (Python plugin SDK) can stay — this is the TypeScript counterpart, same Rust workspace.

## Installation

```bash
npm install qgis-rs
# or
yarn add qgis-rs
pnpm add qgis-rs
```

Pre-built binaries for Linux x86_64 (gnu + musl) and Linux arm64 (gnu). If no binary matches, falls back to pure JS (slower) and you can build from source with `bun run build` (requires Rust ≥1.96).

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rs
cd qgis-rs

# Install the whole Bun workspace from the root lockfile.
# ts-packages/qgis-node is a member, so there is nothing to install here.
pixi run bun-install

# Build native addon (napi build, driven by bun)
pixi run node-build

# Smoke-test the compiled NAPI API
# (`pixi run node-test` from the repository root wires build + test together)
pixi run -e bun bun test tests/contract.test.js

# Inspect the CLI wrapper
pixi run -e bun bunx qgis-cli --help
```

There is no Node.js toolchain in this repository: the addon is built, tested and
packed with bun (`pixi run -e bun …`). The published package still declares
`"engines": { "node": ">= 18" }` because that describes the addon's runtime for
whoever installs it from npm, not the CLI used to build it.

## TypeScript API

```typescript
import { Project, Extent, TilePlan, ZoomRange, Crs, planTiles, version } from 'qgis-rs';

// Open a project (cheap — only checks path, no QGIS needed)
const project = Project.open('map.qgs');
console.log(project.path, project.format);

const info = project.info();
console.log(info.toJson());

// Pure-Rust geometry — native speed, no QGIS
const extent = Extent.parse('14,50,15,51');
console.log(extent.width(), extent.height()); // 1, 1
console.log(extent.contains(14.5, 50.5)); // true

const crs = Crs.fromEpsg(3857);
console.log(crs.authId, crs.isProjected()); // EPSG:3857 true

// Tile planning — counts tiles without rendering
const zooms = ZoomRange.parse('10-14');
const plan = new TilePlan(extent, zooms);
console.log(`Would render ${plan.tileCount()} tiles`); // 4568
for (const level of plan.levels()) {
  console.log(`z=${level.zoom} ${level.tileCount()} tiles`);
}

// Fast function
const result = planTiles('14,50,15,51', '10-14');
console.log(result.total); // 4568

// Rendering (needs QGIS backend — via conda-forge qgis or system QGIS)
try {
  const rendered = project.render('output.png', { width: 1920, height: 1080, dpi: 150 });
  console.log(`Wrote ${rendered.path} (${rendered.bytes} bytes)`);
} catch (e) {
  console.log(`Rendering needs QGIS backend: ${e.message}`);
}

console.log(version());
```

### With Express (server)

```typescript
import express from 'express';
import { Project } from 'qgis-rs';

const app = express();
const project = Project.open('map.qgs');

app.get('/info', (req, res) => {
  const info = project.info();
  res.json(JSON.parse(info.toJson()));
});

app.get('/tiles/:z/:x/:y.png', async (req, res) => {
  const { z, x, y } = req.params;
  // When QGIS backend available:
  // const tile = await project.renderTile(+z, +x, +y);
  // res.type('image/png').send(tile.pngBytes);
  res.status(501).send('Tile rendering needs QGIS backend');
});

app.listen(3000);
```

## CLI

Same Rust code as Python packages, but via Node.js wrappers.

```bash
# Binary on PATH (installed via npm)
npx qgis-cli --help
npx qgis-cli --version
npx qgis-cli info map.qgs --json
npx qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 -o ./tiles/ --dry-run

# Plugin SDK
npx qgis-plugin --help
npx qgis-plugin new my_plugin --type processing --rust
npx qgis-plugin validate ./my_plugin

# Via Node.js API
const { execSync } = require('child_process');
execSync('npx qgis-cli info map.qgs --json', { stdio: 'inherit' });
```

## Architecture

```
qgis-rs npm package
├── qgis-rs.<platform>.node  → NAPI addon (Rust cdylib) — native speed
├── index.js                 → JS wrapper (Extent, Crs, TilePlan, etc.)
├── index.d.ts               → TypeScript types
├── fallback.js              → pure JS fallback when native not built
├── bin/
│   ├── qgis-cli.js          → Node wrapper that tries Rust binary, falls back to JS
│   ├── qgis-plugin.js       → same for plugin SDK
│   └── qgis-sdk.js          → alias
└── (Rust binaries built via cargo, optional)
```

- Rust: `crates/qgis-render` (pure Rust), `crates/qgis-cli`, `crates/qgis-sdk` (plugin CLI)
- Node: `ts-packages/qgis-node/` — package.json, `index.js`, `fallback.js`, `bin/` wrappers; the NAPI crate it builds is `crates/qgis-node/` (`napi build --cargo-cwd ../../crates/qgis-node .`)
- Python: `py-packages/qgis-rs/` and `py-packages/qgis-sdk/` — same Rust code via PyO3

## Conda-forge (Node.js)

For conda, install Node.js + Rust package:

```bash
conda install -c conda-forge nodejs qgis qgis-rs
# the binary qgis-cli is in $PREFIX/bin
```

`nodejs` here is only the runtime needed to *consume* the published addon — the
build itself needs nothing but cargo and bun. The npm package is primary for
TypeScript; a conda-forge recipe for it could be added similarly to Python
(build Rust binary + NAPI addon).

## Performance

Pure-Rust ops (no QGIS):

| Operation | Rust (NAPI) | JS fallback | Speedup |
|-----------|-------------|-------------|---------|
| Extent parse | 0.5µs | 5µs | 10× |
| TilePlan 10-14 (4568 tiles) | 0.2ms | 3ms | 15× |

## License

GPL-2.0-or-later, matching QGIS and qgis-rs.
