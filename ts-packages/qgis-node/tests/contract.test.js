// Smoke tests for the public qgis-rs Node API and its native NAPI boundary.
// Domain logic is tested in the Rust crates; CI builds the addon before running
// this suite with QGIS_REQUIRE_NATIVE=1.

const test = require("node:test");
const assert = require("node:assert/strict");

const qgis = require("../index.js");

const BOUNDS = "14,50,15,51";
const ZOOMS = "10-14";

test("loads the compiled addon when CI requires the native path", () => {
  if (process.env.QGIS_REQUIRE_NATIVE === "1") {
    assert.equal(qgis._hasNative, true, "expected qgis-rs.node to load");
  }
});

test("exports the documented API and package version", () => {
  for (const name of [
    "Extent",
    "Crs",
    "Tile",
    "ZoomRange",
    "TilePlan",
    "Project",
    "planTiles",
    "version",
  ]) {
    assert.equal(typeof qgis[name], "function", `missing export: ${name}`);
  }
  assert.match(qgis.version(), /^\d+\.\d+\.\d+/);
});

test("marshals value objects and numbers across NAPI", () => {
  const extent = qgis.Extent.parse(BOUNDS);
  assert.equal(extent.minX, 14);
  assert.equal(extent.min_x, 14);
  assert.deepEqual(extent.toArray(), [14, 50, 15, 51]);

  const crs = qgis.Crs.fromEpsg(4326);
  assert.equal(crs.authId, "EPSG:4326");

  const plan = new qgis.TilePlan(extent, qgis.ZoomRange.parse(ZOOMS));
  assert.equal(typeof plan.tileCount(), "number");
  assert.equal(plan.tileCount(), 4568);
  assert.equal(plan.levels()[0].tileCount(), 24);
});

test("marshals the plain plan result shape", () => {
  const result = qgis.planTiles(BOUNDS, ZOOMS);

  assert.equal(typeof result.total, "number");
  assert.equal(result.total, 4568);
  assert.equal(result.levels.length, 5);
  assert.equal(result.levels[0].tileCount, 24);
  assert.equal(result.levels[0].tile_count, 24);
});

test("surfaces Rust errors as JavaScript exceptions", () => {
  assert.throws(() => qgis.Extent.parse("not-an-extent"), /invalid extent/i);
  assert.throws(() => qgis.ZoomRange.parse("14-10"), /invalid zoom range/i);
});
