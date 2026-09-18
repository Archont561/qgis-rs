/**
 * qgis-rs — TypeScript definitions for native-speed QGIS bindings
 */

export const MAX_LATITUDE: number;
export const MAX_ZOOM: number;

export class Extent {
  constructor(minX: number, minY: number, maxX: number, maxY: number);
  constructor(extentString: string);

  static parse(text: string): Extent;

  get minX(): number;
  get minY(): number;
  get maxX(): number;
  get maxY(): number;
  get min_x(): number;
  get min_y(): number;
  get max_x(): number;
  get max_y(): number;

  width(): number;
  height(): number;
  isValid(): boolean;
  is_valid(): boolean;
  contains(x: number, y: number): boolean;
  intersects(other: Extent): boolean;
  toString(): string;
  toArray(): [number, number, number, number];
  toTuple(): [number, number, number, number];
  equals(other: Extent): boolean;
}

export class Crs {
  constructor(authId: string);

  static fromAuthId(authId: string): Crs;
  static fromEpsg(code: number): Crs;
  static from_auth_id(authId: string): Crs;
  static from_epsg(code: number): Crs;
  static wgs84(): Crs;
  static webMercator(): Crs;
  static web_mercator(): Crs;

  get authId(): string;
  get auth_id(): string;

  name(): string | null;
  isGeographic(): boolean;
  isProjected(): boolean;
  is_geographic(): boolean;
  is_projected(): boolean;
  toString(): string;
  equals(other: Crs): boolean;
}

export class Tile {
  constructor(z: number, x: number, y: number);

  static fromLonLat(z: number, lon: number, lat: number): Tile;
  static from_lon_lat(z: number, lon: number, lat: number): Tile;

  get z(): number;
  get x(): number;
  get y(): number;

  bounds(): Extent;
  toString(): string;
  equals(other: Tile): boolean;
}

export class ZoomRange {
  constructor(min: number, max: number);
  constructor(rangeString: string);

  static parse(text: string): ZoomRange;

  get min(): number;
  get max(): number;

  count(): number;
  toString(): string;
  equals(other: ZoomRange): boolean;
}

export interface ZoomLevelPlan {
  readonly zoom: number;
  readonly xMin: number;
  readonly xMax: number;
  readonly yMin: number;
  readonly yMax: number;
  readonly x_min: number;
  readonly x_max: number;
  readonly y_min: number;
  readonly y_max: number;
  tileCount(): number;
  tile_count(): number;
}

export class TilePlan {
  constructor(bounds: Extent, zooms: ZoomRange);

  get bounds(): Extent;
  get zooms(): ZoomRange;

  level(zoom: number): ZoomLevelPlan;
  levels(): ZoomLevelPlan[];
  tileCount(): number;
  tile_count(): number;
  iterTiles(): Tile[];
  iter_tiles(): Tile[];
}

export class Project {
  static open(path: string): Project;

  get path(): string;
  get format(): string;

  info(): ProjectInfo;
  render(output: string, options?: { width?: number; height?: number; dpi?: number }): RenderedMap;
}

export interface ProjectInfo {
  readonly path: string;
  readonly format: string;
  readonly sizeBytes: number;
  readonly size_bytes: number;
  readonly crs: Crs | null;
  readonly layerCount: number | null;
  readonly layer_count: number | null;
  readonly note: string | null;
  toJson(): string;
  to_json(): string;
}

export interface RenderedMap {
  readonly path: string;
  readonly bytes: number;
}

export interface TilePlanResult {
  total: number;
  levels: {
    zoom: number;
    xMin: number;
    xMax: number;
    yMin: number;
    yMax: number;
    tileCount: number;
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
    tile_count: number;
  }[];
}

export function planTiles(bounds: string, zoom: string): TilePlanResult;
export function plan_tiles(bounds: string, zoom: string): TilePlanResult;
export function version(): string;

export const _hasNative: boolean;
export const _binding: any;
