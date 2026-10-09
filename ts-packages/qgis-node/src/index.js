/**
 * @archont561/qgis-node — Node.js / TypeScript bindings for qgis-rs.
 *
 * Native-speed QGIS rendering, tiling and project inspection. The addon this
 * package loads exposes exactly one function — `invoke(requestJson)` — and
 * everything below is a *client* of it: a class here holds values and asks the
 * Rust engine every question that has an answer. Parsing an extent, validating
 * a zoom range, counting the tiles in a pyramid: all of that happens in Rust,
 * once, and is reached over a versioned JSON transport.
 *
 * That is why the pure-JS fallback this package used to ship is gone. It was a
 * second implementation of the same arithmetic, it could not render anything,
 * and it answered differently from the engine the moment the two drifted. A
 * missing addon is now an error that tells you to build it.
 *
 * See .knowledge/decisions/D09-wire-protocol-over-ffi.md.
 *
 * Usage:
 *   const { Project, Extent, TilePlan, ZoomRange } = require('@archont561/qgis-node');
 */

const { platform, arch } = process;

/** Candidate module ids for the compiled addon, most specific first. */
function candidates() {
	const triples = [
		`${platform}-${arch}`,
		"linux-x64-gnu",
		"linux-arm64-gnu",
		"linux-x64-musl",
		"darwin-x64",
		"darwin-arm64",
		"win32-x64-msvc",
	];
	// `../` because the addon is built next to package.json (that is where
	// `napi build .` puts it and what the `files` list publishes), while this
	// client lives in src/.
	const ids = ["../qgis-node.node"];
	for (const triple of triples) {
		ids.push(`../qgis-node.${triple}.node`);
	}
	return ids;
}

function loadBinding() {
	const failures = [];
	for (const id of candidates()) {
		try {
			return require(id);
		} catch (error) {
			failures.push(`${id}: ${error.message}`);
		}
	}
	throw new Error(
		"@archont561/qgis-node: the native addon is not available, and this package is a client " +
			"of it — there is no JavaScript fallback.\n" +
			"  bun run build   # from ts-packages/qgis-node\n" +
			`Tried:\n  ${failures.join("\n  ")}`,
	);
}

const binding = loadBinding();

/** The envelope version this addon speaks. */
const TRANSPORT_VERSION = binding.transportVersion();

/**
 * A request the engine understood and refused.
 *
 * `kind` is the machine-readable classification from the wire, so callers
 * branch on it instead of matching on English error prose.
 */
class EngineError extends Error {
	constructor(kind, message, detail) {
		super(message);
		this.name = "EngineError";
		this.kind = kind;
		this.detail = detail ?? {};
	}
}

/** Run one engine operation and return its `result`. */
function invoke(operation, payload = null) {
	const request = JSON.stringify({
		transport_version: TRANSPORT_VERSION,
		operation,
		payload,
	});
	const response = JSON.parse(binding.invoke(request));

	if (response.transport_version !== TRANSPORT_VERSION) {
		throw new EngineError(
			"unsupported_transport",
			`engine speaks transport version ${response.transport_version}, this client speaks ${TRANSPORT_VERSION}`,
		);
	}
	if (response.ok) return response.result;

	const detail = response.result ?? {};
	throw new EngineError(
		detail.kind ?? "invalid_request",
		detail.error ?? "the engine refused the request",
		detail,
	);
}

let engineInfoCache = null;
/** What the engine behind this addon is, and what it can do. Cached. */
function engineInfo() {
	if (engineInfoCache === null) engineInfoCache = invoke("engine_info");
	return engineInfoCache;
}

/** The qgis-rs release this addon was built from. */
function version() {
	return engineInfo().version;
}

/** Anything extent-shaped, in the form the wire accepts. */
function extentPayload(value) {
	if (value instanceof Extent) return value.toObject();
	if (typeof value === "string") return value;
	if (Array.isArray(value)) {
		if (value.length !== 4)
			throw new TypeError(`an extent needs four numbers, got ${value.length}`);
		const [minX, minY, maxX, maxY] = value.map(Number);
		return { min_x: minX, min_y: minY, max_x: maxX, max_y: maxY };
	}
	if (value && typeof value === "object") return value;
	throw new TypeError(`cannot read ${typeof value} as an extent`);
}

/** Anything zoom-shaped, in the form the wire accepts. */
function zoomPayload(value) {
	if (value instanceof ZoomRange) return { min: value.min, max: value.max };
	return value;
}

/**
 * An axis-aligned rectangle, in whatever CRS produced it.
 *
 * Both spellings of each edge are exposed — `minX` for JavaScript callers and
 * `min_x` for code that reads the engine's own JSON — because this class is
 * where the two naming conventions meet.
 */
class Extent {
	constructor(minX, minY, maxX, maxY) {
		// Either four numbers or the `minx,miny,maxx,maxy` text a user typed.
		// Both go to the engine's parser, which is also what validates them —
		// an out-of-order extent throws here rather than becoming a value that
		// is wrong later.
		const request =
			typeof minX === "string"
				? minX
				: { min_x: minX, min_y: minY, max_x: maxX, max_y: maxY };
		const edges = invoke("describe_extent", { extent: request }).extent;
		this.minX = edges.min_x;
		this.minY = edges.min_y;
		this.maxX = edges.max_x;
		this.maxY = edges.max_y;
		this.min_x = edges.min_x;
		this.min_y = edges.min_y;
		this.max_x = edges.max_x;
		this.max_y = edges.max_y;
		Object.freeze(this);
	}

	static fromWire(edges) {
		return new Extent(edges.min_x, edges.min_y, edges.max_x, edges.max_y);
	}

	/** Parse `minx,miny,maxx,maxy`, as `--extent` and `--bounds` do. */
	static parse(text) {
		return Extent.fromWire(invoke("describe_extent", { extent: text }).extent);
	}

	toObject() {
		return {
			min_x: this.minX,
			min_y: this.minY,
			max_x: this.maxX,
			max_y: this.maxY,
		};
	}

	toArray() {
		return [this.minX, this.minY, this.maxX, this.maxY];
	}

	describe() {
		return invoke("describe_extent", { extent: this.toObject() });
	}

	width() {
		return this.describe().width;
	}

	height() {
		return this.describe().height;
	}

	isValid() {
		return this.describe().is_valid;
	}

	contains(x, y) {
		return invoke("extent_contains", { extent: this.toObject(), x, y })
			.contains;
	}

	intersects(other) {
		return invoke("extent_intersects", {
			extent: this.toObject(),
			other: extentPayload(other),
		}).intersects;
	}

	toString() {
		return `${this.minX},${this.minY},${this.maxX},${this.maxY}`;
	}
}

/** A coordinate reference system, addressed by authority code. */
class Crs {
	constructor(authId) {
		const described = invoke("describe_crs", { text: String(authId) });
		this.authId = described.auth_id;
		this.auth_id = described.auth_id;
		Object.freeze(this);
	}

	static fromAuthId(authId) {
		return new Crs(authId);
	}

	static fromEpsg(code) {
		return new Crs(`EPSG:${code}`);
	}

	static wgs84() {
		return new Crs("EPSG:4326");
	}

	static webMercator() {
		return new Crs("EPSG:3857");
	}

	describe() {
		return invoke("describe_crs", { text: this.authId });
	}

	name() {
		return this.describe().name;
	}

	units() {
		return this.describe().units;
	}

	isGeographic() {
		return this.describe().is_geographic;
	}

	isProjected() {
		return this.units() === "meters";
	}

	toString() {
		return this.authId;
	}
}

/** One tile in an XYZ pyramid. */
class Tile {
	constructor(z, x, y) {
		this.z = z;
		this.x = x;
		this.y = y;
		Object.freeze(this);
	}

	/** The tile covering a longitude/latitude pair, latitude clamped. */
	static fromLonLat(z, lon, lat) {
		const { tile } = invoke("tile_from_lon_lat", { z, lon, lat });
		return new Tile(tile.z, tile.x, tile.y);
	}

	/** The tile's extent in EPSG:4326. */
	bounds() {
		const { bounds } = invoke("tile_bounds", {
			tile: { z: this.z, x: this.x, y: this.y },
		});
		return Extent.fromWire(bounds);
	}

	toString() {
		return `${this.z}/${this.x}/${this.y}`;
	}
}

/** An inclusive range of zoom levels. */
class ZoomRange {
	constructor(min, max) {
		const described = invoke("describe_zoom_range", {
			zooms: { min, max: max ?? min },
		});
		this.min = described.zooms.min;
		this.max = described.zooms.max;
		Object.freeze(this);
	}

	/** Parse `12` or `10-14`. */
	static parse(text) {
		const described = invoke("describe_zoom_range", { zooms: text });
		return new ZoomRange(described.zooms.min, described.zooms.max);
	}

	count() {
		return invoke("describe_zoom_range", {
			zooms: { min: this.min, max: this.max },
		}).count;
	}

	toString() {
		return this.min === this.max ? `${this.min}` : `${this.min}-${this.max}`;
	}
}

/** The tile columns and rows that cover an extent at one zoom level. */
class ZoomLevelPlan {
	constructor(level) {
		this.zoom = level.zoom;
		this.xMin = level.x_min;
		this.xMax = level.x_max;
		this.yMin = level.y_min;
		this.yMax = level.y_max;
		this.x_min = level.x_min;
		this.x_max = level.x_max;
		this.y_min = level.y_min;
		this.y_max = level.y_max;
		this.tile_count = level.tile_count;
		Object.freeze(this);
	}

	tileCount() {
		return this.tile_count;
	}
}

/**
 * Every tile covering an EPSG:4326 extent between two zoom levels.
 *
 * One engine call plans the pyramid; the levels and the total are read off
 * that answer rather than recomputed per question.
 */
class TilePlan {
	constructor(bounds, zooms) {
		this._planned = invoke("plan_tiles", {
			bounds: extentPayload(bounds),
			zooms: zoomPayload(zooms),
		});
		this.bounds = Extent.fromWire(this._planned.bounds);
		this.zooms = new ZoomRange(
			this._planned.zooms.min,
			this._planned.zooms.max,
		);
	}

	levels() {
		return this._planned.levels.map((level) => new ZoomLevelPlan(level));
	}

	level(zoom) {
		const found = this.levels().find((level) => level.zoom === zoom);
		if (!found) throw new RangeError(`zoom ${zoom} is not in ${this.zooms}`);
		return found;
	}

	tileCount() {
		return this._planned.tile_count;
	}

	/** Every tile in the plan — a separate ask, because a plan only counts. */
	iterTiles() {
		const enumerated = invoke("plan_tiles", {
			bounds: this.bounds.toObject(),
			zooms: { min: this.zooms.min, max: this.zooms.max },
			include_tiles: true,
		});
		return enumerated.tiles.map((tile) => new Tile(tile.z, tile.x, tile.y));
	}
}

/** A QGIS project on disk. */
class Project {
	constructor(info) {
		this._info = info;
		this.path = info.path;
		this.format = info.format;
	}

	static open(path) {
		return new Project(invoke("project_info", { path: String(path) }));
	}

	/** Describe the project; the optional fields need the QGIS backend. */
	info() {
		return invoke("project_info", { path: this.path });
	}

	/** List the project's layers. Throws `unimplemented` until the operation is routed through QGIS. */
	layers() {
		return invoke("project_layers", { path: this.path }).layers;
	}

	/** Render the project through the native QGIS manager. */
	render(output, options = {}) {
		const payload = { project: this.path, output: String(output) };
		if (options.width != null) payload.width = options.width;
		if (options.height != null) payload.height = options.height;
		if (options.dpi != null) payload.dpi = options.dpi;
		if (options.crs != null)
			payload.crs =
				options.crs instanceof Crs ? options.crs.authId : options.crs;
		if (options.extent != null) payload.extent = extentPayload(options.extent);
		if (options.layers?.length) payload.layers = options.layers;
		if (options.layout != null) payload.layout = options.layout;
		return invoke("render_map", payload);
	}
}

/**
 * Plan a pyramid and return the plain shape: `{ total, levels }`.
 *
 * Each level carries `tileCount` and `tile_count`, like `ZoomLevelPlan`.
 */
function planTiles(bounds, zooms) {
	const planned = invoke("plan_tiles", {
		bounds: extentPayload(bounds),
		zooms: zoomPayload(zooms),
	});
	return {
		total: planned.tile_count,
		levels: planned.levels.map((level) => new ZoomLevelPlan(level)),
	};
}

module.exports = {
	Crs,
	EngineError,
	Extent,
	Project,
	Tile,
	TilePlan,
	ZoomLevelPlan,
	ZoomRange,
	MAX_LATITUDE: engineInfo().max_latitude,
	MAX_ZOOM: engineInfo().max_zoom,
	TRANSPORT_VERSION,
	engineInfo,
	invoke,
	planTiles,
	version,
	// Kept for the contract suite and for consumers that probed it: the addon
	// is now the only way this module can load at all, so it is always true.
	_hasNative: true,
};
