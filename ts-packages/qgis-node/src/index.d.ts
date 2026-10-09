/**
 * Type definitions for @archont561/qgis-node.
 *
 * The addon exposes one function; everything here is the JavaScript client
 * written against it (see index.js and
 * .knowledge/decisions/D09-wire-protocol-over-ffi.md).
 */

/** The envelope version this package speaks. */
export declare const TRANSPORT_VERSION: number;

/** The deepest zoom level the engine will plan for. */
export declare const MAX_ZOOM: number;

/** The latitude beyond which Web Mercator is undefined. */
export declare const MAX_LATITUDE: number;

/** Always `true`: without the addon this module cannot load at all. */
export declare const _hasNative: boolean;

/** The machine-readable classification carried by every engine refusal. */
export type EngineErrorKind =
	| "invalid_request"
	| "unsupported_transport"
	| "invalid_payload"
	| "io"
	| "project_not_found"
	| "unsupported_project"
	| "invalid_extent"
	| "invalid_zoom_range"
	| "unknown_crs"
	| "unknown_image_format"
	| "unimplemented";

/** A request the engine understood and refused. */
export declare class EngineError extends Error {
	kind: EngineErrorKind;
	detail: Record<string, unknown>;
}

/** What the engine behind this addon is, and what it can do. */
export interface EngineInfo {
	engine: string;
	version: string;
	transport_version: number;
	max_zoom: number;
	max_latitude: number;
	operations: string[];
}

/** The four edges, in the engine's own spelling. */
export interface ExtentObject {
	min_x: number;
	min_y: number;
	max_x: number;
	max_y: number;
}

/** Anything this package will read as an extent. */
export type ExtentLike = Extent | string | number[] | ExtentObject;

/** Anything this package will read as a zoom range. */
export type ZoomLike =
	| ZoomRange
	| string
	| number
	| { min: number; max: number };

/** An axis-aligned rectangle, in whatever CRS produced it. */
export declare class Extent {
	constructor(
		minX: number | string,
		minY?: number,
		maxX?: number,
		maxY?: number,
	);
	static parse(text: string): Extent;
	static fromWire(edges: ExtentObject): Extent;
	readonly minX: number;
	readonly minY: number;
	readonly maxX: number;
	readonly maxY: number;
	readonly min_x: number;
	readonly min_y: number;
	readonly max_x: number;
	readonly max_y: number;
	toObject(): ExtentObject;
	toArray(): [number, number, number, number];
	width(): number;
	height(): number;
	isValid(): boolean;
	contains(x: number, y: number): boolean;
	intersects(other: ExtentLike): boolean;
	toString(): string;
}

/** A coordinate reference system, addressed by authority code. */
export declare class Crs {
	constructor(authId: string);
	static fromAuthId(authId: string): Crs;
	static fromEpsg(code: number): Crs;
	static wgs84(): Crs;
	static webMercator(): Crs;
	readonly authId: string;
	readonly auth_id: string;
	name(): string | null;
	units(): "degrees" | "meters" | "unknown";
	isGeographic(): boolean;
	isProjected(): boolean;
	toString(): string;
}

/** One tile in an XYZ pyramid. */
export declare class Tile {
	constructor(z: number, x: number, y: number);
	static fromLonLat(z: number, lon: number, lat: number): Tile;
	readonly z: number;
	readonly x: number;
	readonly y: number;
	bounds(): Extent;
	toString(): string;
}

/** An inclusive range of zoom levels. */
export declare class ZoomRange {
	constructor(min: number, max?: number);
	static parse(text: string): ZoomRange;
	readonly min: number;
	readonly max: number;
	count(): number;
	toString(): string;
}

/** The tile columns and rows that cover an extent at one zoom level. */
export declare class ZoomLevelPlan {
	readonly zoom: number;
	readonly xMin: number;
	readonly xMax: number;
	readonly yMin: number;
	readonly yMax: number;
	readonly x_min: number;
	readonly x_max: number;
	readonly y_min: number;
	readonly y_max: number;
	readonly tile_count: number;
	tileCount(): number;
}

/** Every tile covering an EPSG:4326 extent between two zoom levels. */
export declare class TilePlan {
	constructor(bounds: ExtentLike, zooms: ZoomLike);
	readonly bounds: Extent;
	readonly zooms: ZoomRange;
	levels(): ZoomLevelPlan[];
	level(zoom: number): ZoomLevelPlan;
	tileCount(): number;
	iterTiles(): Tile[];
}

/** What qgis-rs can say about a project; optional fields need QGIS. */
export interface ProjectInfo {
	path: string;
	format: "qgs" | "qgz";
	size_bytes: number;
	crs: { auth_id: string } | null;
	layer_count: number | null;
	extent: ExtentObject | null;
	note: string | null;
}

/** A layer inside a project. */
export interface LayerSummary {
	name: string;
	provider: string;
	crs: { auth_id: string } | null;
	feature_count: number | null;
	geometry_type: string | null;
}

/** How to render a project; omitted fields keep the engine's defaults. */
export interface RenderOptions {
	width?: number;
	height?: number;
	dpi?: number;
	crs?: Crs | string;
	extent?: ExtentLike;
	layers?: string[];
	layout?: string;
}

/** A rendered image, once rendering exists. */
export interface RenderedMap {
	path: string;
	format: string;
	bytes: number;
}

/** A QGIS project on disk. */
export declare class Project {
	static open(path: string): Project;
	readonly path: string;
	readonly format: "qgs" | "qgz";
	info(): ProjectInfo;
	layers(): LayerSummary[];
	render(output: string, options?: RenderOptions): RenderedMap;
}

/** Plan a pyramid and return the plain shape. */
export declare function planTiles(
	bounds: ExtentLike,
	zooms: ZoomLike,
): { total: number; levels: ZoomLevelPlan[] };

/** The qgis-rs release this addon was built from. */
export declare function version(): string;

/** What the engine behind this addon is, and what it can do. Cached. */
export declare function engineInfo(): EngineInfo;

/**
 * Run one engine operation and return its `result`.
 *
 * The escape hatch: an operation this client has no class for is still
 * reachable, which is what keeps a newer engine usable from an older package.
 */
export declare function invoke(operation: string, payload?: unknown): unknown;

/** What running the bundled qgis-cli produced. */
export interface CliResult {
	/** The process exit code; 1 when it was killed by a signal. */
	exitCode: number;
	stdout: string;
	stderr: string;
}

/** Options for locating and running the bundled qgis-cli. */
export interface CliOptions {
	/** Directory to run the command in. */
	cwd?: string;
}

/**
 * Absolute path of the qgis-cli binary for this machine, from the platform
 * package that npm installed. Throws when the platform has no build.
 */
export declare function resolveCliBinary(options?: {
	platform?: NodeJS.Platform;
	arch?: string;
	isMusl?: () => boolean;
}): string;

/**
 * Run the bundled qgis-cli and capture its output. A failing command is
 * reported through `exitCode`; only a binary that cannot start throws.
 */
export declare function runCli(
	argv?: readonly string[],
	options?: CliOptions,
): CliResult;
