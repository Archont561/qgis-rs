// The JavaScript client, tested across the real NAPI boundary.
//
// Domain logic is tested in the Rust crates; what this suite owns is the
// boundary — that the addon loads, that values survive the JSON round trip,
// and that an engine refusal arrives as a JavaScript exception carrying the
// wire `kind`. CI builds the addon before running it with
// QGIS_REQUIRE_NATIVE=1.

const test = require("node:test");
const assert = require("node:assert/strict");
const fc = require("fast-check");
const fs = require("node:fs");
const path = require("node:path");

const qgis = require("../src/index.js");

const BOUNDS = "14,50,15,51";
const ZOOMS = "10-14";

test("loads the compiled addon — there is no fallback behind it", () => {
	assert.equal(qgis._hasNative, true, "expected qgis-rs.node to load");
	assert.equal(typeof qgis.TRANSPORT_VERSION, "number");
	assert.equal(qgis.TRANSPORT_VERSION, qgis.engineInfo().transport_version);
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
		"invoke",
	]) {
		assert.equal(typeof qgis[name], "function", `missing export: ${name}`);
	}
	assert.match(qgis.version(), /^\d+\.\d+\.\d+/);
	assert.equal(qgis.MAX_ZOOM, 22);
});

test("the engine advertises the operations this client uses", () => {
	const { operations } = qgis.engineInfo();

	for (const name of [
		"describe_extent",
		"plan_tiles",
		"project_info",
		"api_describe",
	]) {
		assert.ok(operations.includes(name), `engine does not serve ${name}`);
	}
});

test("marshals value objects and numbers across the transport", () => {
	const extent = qgis.Extent.parse(BOUNDS);
	assert.equal(extent.minX, 14);
	assert.equal(extent.min_x, 14);
	assert.deepEqual(extent.toArray(), [14, 50, 15, 51]);
	assert.equal(extent.width(), 1);
	assert.equal(extent.contains(14.5, 50.5), true);
	assert.equal(extent.intersects("20,20,30,30"), false);

	const crs = qgis.Crs.fromEpsg(4326);
	assert.equal(crs.authId, "EPSG:4326");
	assert.equal(crs.units(), "degrees");
	assert.equal(crs.isGeographic(), true);

	const plan = new qgis.TilePlan(extent, qgis.ZoomRange.parse(ZOOMS));
	assert.equal(typeof plan.tileCount(), "number");
	assert.equal(plan.tileCount(), 4568);
	assert.equal(plan.levels()[0].tileCount(), 24);
	assert.equal(plan.level(10).xMin, 551);
});

test("an extent can be given the way the caller has it", () => {
	for (const bounds of [BOUNDS, [14, 50, 15, 51], qgis.Extent.parse(BOUNDS)]) {
		assert.equal(new qgis.TilePlan(bounds, 10).tileCount(), 24);
	}
});

test("property: finite extent text round trips through the native boundary", () => {
	fc.assert(
		fc.property(
			fc.integer({ min: -100000, max: 100000 }),
			fc.integer({ min: -100000, max: 100000 }),
			fc.integer({ min: -100000, max: 100000 }),
			fc.integer({ min: -100000, max: 100000 }),
			(firstX, secondX, firstY, secondY) => {
				const extent = new qgis.Extent(
					Math.min(firstX, secondX),
					Math.min(firstY, secondY),
					Math.max(firstX, secondX),
					Math.max(firstY, secondY),
				);
				assert.deepEqual(
					qgis.Extent.parse(String(extent)).toArray(),
					extent.toArray(),
				);
			},
		),
		{ numRuns: 40 },
	);
});

test("tiles round trip through the engine", () => {
	const tile = qgis.Tile.fromLonLat(10, 13.9, 51.1);

	assert.deepEqual([tile.z, tile.x, tile.y], [10, 551, 342]);
	assert.equal(tile.bounds().minX, 13.7109375);
	assert.equal(String(tile), "10/551/342");
});

test("marshals the plain plan result shape", () => {
	const result = qgis.planTiles(BOUNDS, ZOOMS);

	assert.equal(typeof result.total, "number");
	assert.equal(result.total, 4568);
	assert.equal(result.levels.length, 5);
	assert.equal(result.levels[0].tileCount(), 24);
	assert.equal(result.levels[0].tile_count, 24);
});

test("enumerating tiles is a separate ask", () => {
	const plan = new qgis.TilePlan(BOUNDS, 10);
	const tiles = plan.iterTiles();

	assert.equal(tiles.length, plan.tileCount());
	assert.deepEqual([tiles[0].z, tiles[0].x, tiles[0].y], [10, 551, 342]);
});

test("surfaces engine refusals as exceptions carrying the wire kind", () => {
	assert.throws(
		() => qgis.Extent.parse("not-an-extent"),
		(error) => {
			assert.ok(error instanceof qgis.EngineError);
			assert.equal(error.kind, "invalid_extent");
			assert.match(error.message, /invalid extent/i);
			return true;
		},
	);
	assert.throws(() => qgis.ZoomRange.parse("14-10"), /invalid zoom range/i);
	assert.throws(
		() => qgis.Crs.fromAuthId("3857"),
		/coordinate reference system/i,
	);
	assert.throws(
		() => qgis.Project.open("/nope/missing.qgs"),
		(error) => {
			assert.equal(error.kind, "project_not_found");
			return true;
		},
	);
});

test("a project is described from its path, and QGIS-only work says so", () => {
	const fs = require("node:fs");
	const os = require("node:os");
	const path = require("node:path");

	const dir = fs.mkdtempSync(path.join(os.tmpdir(), "qgis-node-contract-"));
	const project = path.join(dir, "map.qgs");
	fs.writeFileSync(project, "<qgis></qgis>");

	const opened = qgis.Project.open(project);
	assert.equal(opened.format, "qgs");
	assert.ok(opened.info().size_bytes > 0);
	assert.ok(opened.info().note);

	assert.throws(
		() => opened.layers(),
		(error) => {
			assert.equal(error.kind, "unimplemented");
			return true;
		},
	);
});

test("the raw transport is reachable for operations this client has no class for", () => {
	const echoed = qgis.invoke("ping", { any: "payload" });

	assert.deepEqual(echoed.echo, { any: "payload" });
	assert.equal(echoed.engine, "qgis-engine");
});

test("layer lifecycle golden values match the shared wire fixture", () => {
	const fixture = JSON.parse(
		fs.readFileSync(
			path.resolve(__dirname, "../../../test-fixtures/layer-lifecycle.json"),
			"utf8",
		),
	);
	const { operations } = qgis.engineInfo();

	for (const name of [
		"layer_open",
		"layer_info",
		"layer_close",
		"layer_features",
	]) {
		assert.ok(operations.includes(name), `engine does not serve ${name}`);
		assert.equal(
			fixture.operations[name].request.transport_version,
			qgis.TRANSPORT_VERSION,
		);
		assert.equal(fixture.operations[name].request.operation, name);
	}

	assert.deepEqual(fixture.operations.layer_open.result, {
		layer_id: 7,
		is_valid: true,
		name: "points",
	});
	assert.deepEqual(
		fixture.operations.layer_info.result.fields.map((field) => field.name),
		["fid", "name"],
	);

	const page = fixture.operations.layer_features.result;
	assert.equal(page.limit, 2);
	assert.equal(page.next_offset, 2);
	assert.equal(page.features.length, 2);
	assert.deepEqual(page.features[0].attributes, { fid: 1, name: "alpha" });
	assert.deepEqual(fixture.errors, {
		closed_layer: "invalid_object_id",
		invalid_layer: "invalid_object_id",
	});
});
