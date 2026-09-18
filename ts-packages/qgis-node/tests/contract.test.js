// Contract tests for the `qgis-rs` npm package.
//
// These run twice in CI (`.github/workflows/node.yml`): once with no addon
// present, where `index.js` transparently loads `fallback.js`, and once after
// `napi build`, where the native addon answers the same calls. So every
// assertion here must hold for *both* implementations — that is the point: the
// pure-JS fallback and the Rust addon are one contract.
//
// Run with: npm test            (node's built-in test runner, no jest)
//           bun test tests/     (same files, Bun's runner)
//           BQGIS_NODE_FORCE_FALLBACK=1 is not a thing; delete the .node file
//           locally to force the fallback.

const test = require("node:test");
const assert = require("node:assert/strict");

const qgis = require("../index.js");

// The tile-plan numbers come from README.md and apps/docs — 4568 tiles for
// z10..z14 over a 1x1 degree box. If either implementation drifts, this fails.
const BOUNDS = "14,50,15,51";
const ZOOMS = "10-14";
const EXPECTED_TILES = 4568;

test("exports the documented surface", () => {
  for (const name of [
    "Extent",
    "Tile",
    "TilePlan",
    "ZoomRange",
    "Project",
    "planTiles",
    "version",
    "getMaxLatitude",
    "getMaxZoom",
  ]) {
    assert.ok(name in qgis, `missing export: ${name}`);
  }
});

test("version() reports a version", () => {
  assert.equal(typeof qgis.version(), "string");
  assert.match(qgis.version(), /^\d+\.\d+\.\d+/);
});

test("Web Mercator limits, in both spellings", () => {
  // index.js exports the constants, the addon exposes getters — both must answer.
  assert.equal(qgis.MAX_LATITUDE, qgis.getMaxLatitude());
  assert.equal(qgis.MAX_ZOOM, qgis.getMaxZoom());
  assert.ok(Math.abs(qgis.MAX_LATITUDE - 85.0511287798066) < 1e-9);
  assert.equal(qgis.getMaxZoom(), 22); // crates/qgis-render/src/tiles.rs
});

test("Extent.parse and geometry", () => {
  const e = qgis.Extent.parse(BOUNDS);
  assert.equal(e.minX, 14);
  assert.equal(e.minY, 50);
  assert.equal(e.maxX, 15);
  assert.equal(e.maxY, 51);
  assert.equal(e.width(), 1);
  assert.equal(e.height(), 1);
  assert.ok(e.contains(14.5, 50.5));
  assert.ok(!e.contains(13.5, 50.5));
  // snake_case aliases exist for every camelCase member the binding generates.
  assert.equal(e.min_x, 14);
  assert.equal(e.max_y, 51);
});

test("Extent.parse rejects garbage", () => {
  assert.throws(() => qgis.Extent.parse("not-an-extent"));
});

test("ZoomRange.parse and membership", () => {
  const z = qgis.ZoomRange.parse(ZOOMS);
  assert.equal(z.min, 10);
  assert.equal(z.max, 14);
  assert.ok(!z.equals(qgis.ZoomRange.parse("10-13")));
  assert.throws(() => qgis.ZoomRange.parse("9-3")); // inverted
  assert.throws(() => qgis.ZoomRange.parse("99")); // above MAX_ZOOM
});

test("TilePlan counts tiles as a JS number, not a BigInt", () => {
  const plan = new qgis.TilePlan(qgis.Extent.parse(BOUNDS), qgis.ZoomRange.parse(ZOOMS));
  const count = plan.tileCount();
  // The binding crosses as i64 (see crates/qgis-node/src/lib.rs): a JS number.
  assert.equal(typeof count, "number");
  assert.ok(Number.isSafeInteger(count));
  assert.equal(count, EXPECTED_TILES);
  assert.equal(plan.tile_count(), EXPECTED_TILES);
});

test("TilePlan.levels describes every zoom", () => {
  const plan = new qgis.TilePlan(qgis.Extent.parse(BOUNDS), qgis.ZoomRange.parse(ZOOMS));
  const levels = plan.levels();
  assert.equal(levels.length, 5);
  let sum = 0;
  for (const level of levels) {
    assert.ok(level.zoom >= 10 && level.zoom <= 14);
    assert.ok(level.xMax >= level.xMin && level.yMax >= level.yMin);
    // levels() hands back wrapper instances (method), planTiles() hands back a
    // plain object (field); both spellings are part of the contract.
    assert.equal(typeof level.tileCount, "function");
    assert.equal(
      level.tileCount(),
      (level.xMax - level.xMin + 1) * (level.yMax - level.yMin + 1),
    );
    sum += level.tileCount();
  }
  assert.equal(sum, EXPECTED_TILES);
  assert.equal(plan.level(12).tileCount(), levels[2].tileCount());
});

test("planTiles matches the TilePlan surface", () => {
  const result = qgis.planTiles(BOUNDS, ZOOMS);
  assert.equal(result.total, EXPECTED_TILES);
  assert.equal(result.levels.length, 5);
  assert.equal(typeof result.total, "number");
  assert.equal(typeof result.levels[0].tileCount, "number");
  assert.equal(result.levels[0].tile_count, result.levels[0].tileCount);
});

test("Tile round-trips through x/y/z", () => {
  const t = new qgis.Tile(12, 2048, 1365);
  assert.equal(t.z, 12);
  assert.equal(t.x, 2048);
  assert.equal(t.y, 1365);
  assert.equal(t.toString(), "12/2048/1365");
});

test("Project.open reports missing files instead of throwing raw", () => {
  assert.throws(() => qgis.Project.open("/nonexistent/map.qgs"));
});
