# qgis-rs — Node.js / TypeScript bindings with Rust-native CLI

[![npm](https://img.shields.io/npm/v/qgis-rs)](https://www.npmjs.com/package/qgis-rs)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue)](LICENSE)

**qgis-rs** for Node.js — native-speed QGIS rendering, tiling, and plugin tools via NAPI-RS.

- **npm**: `npm install qgis-rs` → `require('qgis-rs')` + `qgis-cli` binary on PATH
- **API**: TypeScript types, pure Rust geometry (Extent, Crs, TilePlan) via NAPI, QGIS backend optional
- **CLI**: `qgis-cli` and `qgis-plugin` Rust binaries + Node.js wrappers, both native speed

`qgis-py` (Python) and `qgis-sdk` (Python plugin SDK) can stay — this is the TypeScript counterpart, same Rust workspace.

## Installation

```bash
npm install qgis-rs
# or
yarn add qgis-rs
pnpm add qgis-rs
```

Pre-built binaries for Linux x86_64 (gnu + musl) and Linux arm64 (gnu). There is no JavaScript fallback — every value this package returns is computed by Rust — so if no binary matches your platform, build from source with `bun run build` (requires Rust ≥1.96).

### From source (development)

```bash
git clone https://github.com/Archont561/qgis-rs
cd qgis-rs

# Install the whole Bun workspace from the root lockfile.
# ts-packages/qgis-node is a member, so there is nothing to install here.
pixi run bun-install

# Build native addon (napi build, driven by bun)
# (run from the repository root — turbo delegates to this package's scripts)
bun x turbo run build --filter=qgis-rs

# Smoke-test the compiled NAPI API
bun x turbo run test --filter=qgis-rs

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

// Rendering through the native QGIS backend
try {
  const rendered = project.render('output.png', { width: 1920, height: 1080, dpi: 150 });
  console.log(`Wrote ${rendered.path} (${rendered.bytes} bytes)`);
} catch (e) {
  console.log(`QGIS rendering failed: ${e.message}`);
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
├── src/
│   ├── index.js             → JS wrapper (Extent, Crs, TilePlan, etc.) over one `invoke(json)` call
│   └── index.d.ts           → TypeScript types
├── tests/                   → the contract suite, run against the real addon
├── bin/
│   ├── qgis-cli.js          → Node wrapper that tries Rust binary, falls back to JS
│   ├── qgis-plugin.js       → same for plugin SDK
│   └── qgis-sdk.js          → alias
└── (Rust binaries built via cargo, optional)
```

- Rust: `crates/qgis-render` (pure Rust), `crates/qgis-cli`, `crates/qgis-sdk` (plugin CLI)
- Node: `ts-packages/qgis-node/` — package.json, `src/index.js`, `bin/` wrappers; the NAPI crate it builds is `crates/qgis-node/` (`napi build --cargo-cwd ../../crates/qgis-node .`), and that crate exposes exactly one function, `invoke(requestJson) -> responseJson` (see `.knowledge/decisions/D09-wire-protocol-over-ffi.md`)
- Python: `py-packages/qgis-py/` and `py-packages/qgis-sdk/` — same Rust code via PyO3

## Conda-forge (Node.js)

For conda, install Node.js + Rust package:

```bash
conda install -c conda-forge nodejs qgis qgis-py
# the binary qgis-cli is in $PREFIX/bin
```

`nodejs` here is only the runtime needed to *consume* the published addon — the
build itself needs nothing but cargo and bun. The npm package is primary for
TypeScript; a conda-forge recipe for it could be added similarly to Python
(build Rust binary + NAPI addon).

## Performance

Pure-Rust ops (no QGIS). The addon is called once per operation with a JSON
request and answers with a JSON response, so the cost of a call is the Rust
work plus one serialize/parse pair — which is why `planTiles` does not return
the 4568 tiles unless you ask for them (`includeTiles: true`):

| Operation | Time (bun 1.3, x86_64) |
|-----------|------------------------|
| `new Extent("14,50,15,51")` | ~4µs |
| `planTiles` z10-14 — counts and per-level extents | ~18µs |
| `TilePlan#iterTiles()` — the same plan, all 4568 tiles materialised | ~3.5ms |

That last row is the reason a plan counts by default and enumerates only when
asked: the maths is the cheap part, and 4568 objects crossing the boundary is
the expensive one.

## License

GPL-2.0-or-later, matching QGIS and qgis-rs.
