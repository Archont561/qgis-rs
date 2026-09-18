/**
 * Pure-JS fallback for qgis-rs Node.js package when native binding not built.
 * Mirrors Rust API but slower — allows development and tests without cargo.
 */

const MAX_LATITUDE = 85.0511287798066;
const MAX_ZOOM = 22;

class ExtentWrapper {
  constructor(minX, minY, maxX, maxY) {
    if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) {
      throw new Error(`invalid extent: ${minX},${minY},${maxX},${maxY} — not finite`);
    }
    if (minX > maxX || minY > maxY) {
      throw new Error(`invalid extent: ${minX},${minY},${maxX},${maxY} — must be ordered`);
    }
    this.minX = minX;
    this.minY = minY;
    this.maxX = maxX;
    this.maxY = maxY;
  }

  static parse(text) {
    const parts = text.split(',').map(s => s.trim());
    if (parts.length !== 4) throw new Error(`invalid extent: ${text}`);
    const vals = parts.map(Number);
    if (vals.some(isNaN)) throw new Error(`invalid extent: ${text} — not numbers`);
    return new ExtentWrapper(vals[0], vals[1], vals[2], vals[3]);
  }

  width() { return this.maxX - this.minX; }
  height() { return this.maxY - this.minY; }
  isValid() { return this.minX <= this.maxX && this.minY <= this.maxY; }
  contains(x, y) { return x >= this.minX && x <= this.maxX && y >= this.minY && y <= this.maxY; }
  intersects(other) {
    return this.minX <= other.maxX && other.minX <= this.maxX &&
           this.minY <= other.maxY && other.minY <= this.maxY;
  }
  toString() { return `${this.minX},${this.minY},${this.maxX},${this.maxY}`; }
  toArray() { return [this.minX, this.minY, this.maxX, this.maxY]; }
  equals(other) { return this.minX === other.minX && this.minY === other.minY && this.maxX === other.maxX && this.maxY === other.maxY; }
}

class CrsWrapper {
  constructor(authId) {
    const trimmed = authId.trim();
    if (!trimmed.includes(':')) throw new Error(`unknown CRS: ${authId}`);
    const [auth, code] = trimmed.split(':');
    if (!auth || !/^[a-zA-Z]+$/.test(auth) || !/^\d+$/.test(code)) {
      throw new Error(`unknown CRS: ${authId}`);
    }
    this.authId = trimmed.toUpperCase();
  }

  static fromAuthId(authId) { return new CrsWrapper(authId); }
  static fromEpsg(code) { return new CrsWrapper(`EPSG:${code}`); }
  static wgs84() { return new CrsWrapper('EPSG:4326'); }
  static webMercator() { return new CrsWrapper('EPSG:3857'); }

  name() {
    const known = {
      'EPSG:4326': 'WGS 84',
      'EPSG:3857': 'WGS 84 / Pseudo-Mercator',
    };
    return known[this.authId] || null;
  }

  isGeographic() { return this.authId === 'EPSG:4326'; }
  isProjected() { return this.authId !== 'EPSG:4326'; }
  toString() { return this.authId; }
  equals(other) { return this.authId === other.authId; }
}

function tilesPerSide(z) { return 1 << z; }
function latToY(z, lat) {
  const side = tilesPerSide(z);
  const clamped = Math.max(Math.min(lat, MAX_LATITUDE), -MAX_LATITUDE);
  const rad = clamped * Math.PI / 180;
  const merc = Math.log(Math.tan(rad) + 1 / Math.cos(rad));
  return (1 - merc / Math.PI) / 2 * side;
}
function xToLon(x, side) { return x / side * 360 - 180; }
function yToLat(y, side) {
  const n = Math.PI * (1 - 2 * y / side);
  return Math.atan(Math.sinh(n)) * 180 / Math.PI;
}
function clampIndex(v, side) { return Math.max(0, Math.min(v, side - 1)); }

class TileWrapper {
  constructor(z, x, y) { this.z = z; this.x = x; this.y = y; }
  static fromLonLat(z, lon, lat) {
    const side = tilesPerSide(z);
    const x = Math.floor((lon + 180) / 360 * side);
    const y = latToY(z, lat);
    return new TileWrapper(z, Math.floor(clampIndex(x, side)), Math.floor(clampIndex(y, side)));
  }
  bounds() {
    const side = tilesPerSide(this.z);
    return new ExtentWrapper(
      xToLon(this.x, side),
      yToLat(this.y + 1, side),
      xToLon(this.x + 1, side),
      yToLat(this.y, side)
    );
  }
  toString() { return `${this.z}/${this.x}/${this.y}`; }
  equals(other) { return this.z === other.z && this.x === other.x && this.y === other.y; }
}

class ZoomRangeWrapper {
  constructor(min, max) {
    if (min > max || max > MAX_ZOOM) throw new Error(`invalid zoom range: ${min}-${max}`);
    this.min = min;
    this.max = max;
  }
  static parse(text) {
    const t = text.trim();
    if (t.includes('-')) {
      const [low, high] = t.split('-').map(s => s.trim());
      const mn = parseInt(low, 10), mx = parseInt(high, 10);
      if (isNaN(mn) || isNaN(mx)) throw new Error(`invalid zoom range: ${text}`);
      return new ZoomRangeWrapper(mn, mx);
    } else {
      const v = parseInt(t, 10);
      if (isNaN(v)) throw new Error(`invalid zoom range: ${text}`);
      return new ZoomRangeWrapper(v, v);
    }
  }
  count() { return this.max - this.min + 1; }
  toString() { return this.min === this.max ? `${this.min}` : `${this.min}-${this.max}`; }
  equals(other) { return this.min === other.min && this.max === other.max; }
}

class ZoomLevelPlanWrapper {
  constructor(zoom, xMin, xMax, yMin, yMax) {
    this.zoom = zoom;
    this.xMin = xMin;
    this.xMax = xMax;
    this.yMin = yMin;
    this.yMax = yMax;
  }
  get x_min() { return this.xMin; }
  get x_max() { return this.xMax; }
  get y_min() { return this.yMin; }
  get y_max() { return this.yMax; }
  tileCount() { return (this.xMax - this.xMin + 1) * (this.yMax - this.yMin + 1); }
  tile_count() { return this.tileCount(); }
}

class TilePlanWrapper {
  constructor(bounds, zooms) {
    if (!bounds.isValid()) throw new Error(`invalid extent: ${bounds}`);
    this.bounds = bounds;
    this.zooms = zooms;
  }
  level(zoom) {
    const side = tilesPerSide(zoom);
    const xMin = Math.floor(clampIndex(Math.floor((this.bounds.minX + 180) / 360 * side), side));
    const xMax = Math.floor(clampIndex(Math.floor((this.bounds.maxX + 180) / 360 * side), side));
    const yMin = Math.floor(clampIndex(latToY(zoom, this.bounds.maxY), side));
    const yMax = Math.floor(clampIndex(latToY(zoom, this.bounds.minY), side));
    return new ZoomLevelPlanWrapper(zoom, xMin, xMax, yMin, yMax);
  }
  levels() {
    const res = [];
    for (let z = this.zooms.min; z <= this.zooms.max; z++) res.push(this.level(z));
    return res;
  }
  tileCount() { return this.levels().reduce((sum, l) => sum + l.tileCount(), 0); }
  tile_count() { return this.tileCount(); }
  iterTiles() {
    const tiles = [];
    for (const lvl of this.levels()) {
      for (let y = lvl.yMin; y <= lvl.yMax; y++) {
        for (let x = lvl.xMin; x <= lvl.xMax; x++) {
          tiles.push(new TileWrapper(lvl.zoom, x, y));
        }
      }
    }
    return tiles;
  }
  iter_tiles() { return this.iterTiles(); }
}

class ProjectWrapper {
  constructor(path, format) { this.path = path; this.format = format; }
  static open(path) {
    const fs = require('fs');
    if (!fs.existsSync(path)) throw new Error(`project not found: ${path}`);
    const ext = path.split('.').pop().toLowerCase();
    if (!['qgs', 'qgz'].includes(ext)) throw new Error(`unsupported project: ${path}`);
    return new ProjectWrapper(path, ext);
  }
  info() {
    const fs = require('fs');
    const stat = fs.statSync(this.path);
    return new ProjectInfoWrapper(this.path, this.format, stat.size, "CRS, layer count and extent need the QGIS backend, which is not wired up yet");
  }
  render() { throw new Error("rendering a project: needs the QGIS backend, which is not wired up yet"); }
}

class ProjectInfoWrapper {
  constructor(path, format, sizeBytes, note) {
    this.path = path;
    this.format = format;
    this.sizeBytes = sizeBytes;
    this.note = note;
    this.crs = null;
    this.layerCount = null;
  }
  get size_bytes() { return this.sizeBytes; }
  get layer_count() { return this.layerCount; }
  toJson() { return JSON.stringify({ path: this.path, format: this.format, size_bytes: this.sizeBytes, note: this.note }); }
  to_json() { return this.toJson(); }
}

class RenderedMapWrapper {
  constructor(path, bytes) { this.path = path; this.bytes = bytes; }
}

function planTiles(bounds, zoom) {
  const extent = ExtentWrapper.parse(bounds);
  const zooms = ZoomRangeWrapper.parse(zoom);
  const plan = new TilePlanWrapper(extent, zooms);
  return {
    total: plan.tileCount(),
    levels: plan.levels().map(l => ({
      zoom: l.zoom,
      xMin: l.xMin,
      xMax: l.xMax,
      yMin: l.yMin,
      yMax: l.yMax,
      tileCount: l.tileCount(),
      x_min: l.xMin,
      x_max: l.xMax,
      y_min: l.yMin,
      y_max: l.yMax,
      tile_count: l.tileCount(),
    })),
  };
}

function version() { return "0.1.0-fallback"; }
function getMaxLatitude() { return MAX_LATITUDE; }
function getMaxZoom() { return MAX_ZOOM; }

module.exports = {
  ExtentWrapper,
  CrsWrapper,
  TileWrapper,
  ZoomRangeWrapper,
  ZoomLevelPlanWrapper,
  TilePlanWrapper,
  ProjectWrapper,
  ProjectInfoWrapper,
  RenderedMapWrapper,
  planTiles,
  version,
  getMaxLatitude,
  getMaxZoom,
  // Same names index.js re-exports, so the fallback object is a drop-in for the
  // addon from either side.
  MAX_LATITUDE,
  MAX_ZOOM,
};
