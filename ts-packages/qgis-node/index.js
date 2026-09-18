/**
 * qgis-rs — Node.js / TypeScript bindings for qgis-rs
 * 
 * Native-speed QGIS rendering, tiling, and plugin tools via NAPI-RS.
 * 
 * Install:
 *   npm install qgis-rs
 * 
 * Usage:
 *   const { Project, Extent, TilePlan, ZoomRange } = require('qgis-rs');
 *   // or
 *   import { Project, Extent } from 'qgis-rs';
 */

const { platform, arch } = process;

// Try to load native addon
let nativeBinding = null;
let loadError = null;

function loadNative() {
  if (nativeBinding) return nativeBinding;
  
  try {
    // Try local build first (for development)
    nativeBinding = require('./qgis-rs.node');
    return nativeBinding;
  } catch (e) {
    // Try platform-specific packages
    const triples = [
      `${platform}-${arch}`,
      `linux-x64-gnu`,
      `linux-arm64-gnu`,
      `darwin-x64`,
      `darwin-arm64`,
      `win32-x64-msvc`,
    ];
    
    for (const triple of triples) {
      try {
        nativeBinding = require(`./qgis-rs.${triple}.node`);
        return nativeBinding;
      } catch (_) {
        // continue
      }
      try {
        nativeBinding = require(`@qgis-rs/node-${triple}`);
        return nativeBinding;
      } catch (_) {
        // continue
      }
    }
    
    loadError = e;
    // Fallback to pure JS implementation
    console.warn(
      `qgis-rs: native binding not found (${e.message}), using pure JS fallback. ` +
      `For native speed, build with: npm run build`
    );
    nativeBinding = require('./fallback.js');
    return nativeBinding;
  }
}

// Load on require
const binding = loadNative();

// Re-export with JS-friendly wrappers
class Extent {
  constructor(minX, minY, maxX, maxY) {
    if (typeof minX === 'string') {
      // Parse from string like "14,50,15,51"
      this._inner = binding.ExtentWrapper.parse(minX);
    } else if (minX instanceof binding.ExtentWrapper) {
      this._inner = minX;
    } else {
      this._inner = new binding.ExtentWrapper(minX, minY, maxX, maxY);
    }
  }

  static parse(text) {
    const inner = binding.ExtentWrapper.parse(text);
    const e = Object.create(Extent.prototype);
    e._inner = inner;
    return e;
  }

  get minX() { return this._inner.minX; }
  get minY() { return this._inner.minY; }
  get maxX() { return this._inner.maxX; }
  get maxY() { return this._inner.maxY; }
  get min_x() { return this._inner.minX; }
  get min_y() { return this._inner.minY; }
  get max_x() { return this._inner.maxX; }
  get max_y() { return this._inner.maxY; }

  width() { return this._inner.width(); }
  height() { return this._inner.height(); }
  isValid() { return this._inner.isValid(); }
  is_valid() { return this._inner.isValid(); }
  contains(x, y) { return this._inner.contains(x, y); }
  intersects(other) { return this._inner.intersects(other._inner); }
  toString() { return this._inner.toString(); }
  toArray() { return this._inner.toArray(); }
  toTuple() { return this._inner.toArray(); }
  equals(other) { return this._inner.equals(other._inner); }
}

class Crs {
  constructor(authId) {
    if (authId instanceof binding.CrsWrapper) {
      this._inner = authId;
    } else {
      this._inner = new binding.CrsWrapper(authId);
    }
  }

  static fromAuthId(authId) {
    const inner = binding.CrsWrapper.fromAuthId(authId);
    const c = Object.create(Crs.prototype);
    c._inner = inner;
    return c;
  }

  static fromEpsg(code) {
    const inner = binding.CrsWrapper.fromEpsg(code);
    const c = Object.create(Crs.prototype);
    c._inner = inner;
    return c;
  }

  static from_epsg(code) { return Crs.fromEpsg(code); }
  static from_auth_id(authId) { return Crs.fromAuthId(authId); }

  static wgs84() {
    const inner = binding.CrsWrapper.wgs84();
    const c = Object.create(Crs.prototype);
    c._inner = inner;
    return c;
  }

  static webMercator() {
    const inner = binding.CrsWrapper.webMercator();
    const c = Object.create(Crs.prototype);
    c._inner = inner;
    return c;
  }

  static web_mercator() { return Crs.webMercator(); }

  get authId() { return this._inner.authId; }
  get auth_id() { return this._inner.authId; }
  name() { return this._inner.name(); }
  isGeographic() { return this._inner.isGeographic(); }
  isProjected() { return this._inner.isProjected(); }
  is_geographic() { return this._inner.isGeographic(); }
  is_projected() { return this._inner.isProjected(); }
  toString() { return this._inner.toString(); }
  equals(other) { return this._inner.equals(other._inner); }
}

class Tile {
  constructor(z, x, y) {
    if (z instanceof binding.TileWrapper) {
      this._inner = z;
    } else {
      this._inner = new binding.TileWrapper(z, x, y);
    }
  }

  static fromLonLat(z, lon, lat) {
    const inner = binding.TileWrapper.fromLonLat(z, lon, lat);
    const t = Object.create(Tile.prototype);
    t._inner = inner;
    return t;
  }

  static from_lon_lat(z, lon, lat) { return Tile.fromLonLat(z, lon, lat); }

  get z() { return this._inner.z; }
  get x() { return this._inner.x; }
  get y() { return this._inner.y; }

  bounds() {
    const inner = this._inner.bounds();
    const e = Object.create(Extent.prototype);
    e._inner = inner;
    return e;
  }

  toString() { return this._inner.toString(); }
  equals(other) { return this._inner.equals(other._inner); }
}

class ZoomRange {
  constructor(min, max) {
    if (min instanceof binding.ZoomRangeWrapper) {
      this._inner = min;
    } else if (typeof min === 'string') {
      this._inner = binding.ZoomRangeWrapper.parse(min);
    } else {
      this._inner = new binding.ZoomRangeWrapper(min, max);
    }
  }

  static parse(text) {
    const inner = binding.ZoomRangeWrapper.parse(text);
    const z = Object.create(ZoomRange.prototype);
    z._inner = inner;
    return z;
  }

  get min() { return this._inner.min; }
  get max() { return this._inner.max; }
  count() { return this._inner.count(); }
  toString() { return this._inner.toString(); }
  equals(other) { return this._inner.equals(other._inner); }
}

class TilePlan {
  constructor(bounds, zooms) {
    const b = bounds instanceof Extent ? bounds._inner : bounds;
    const z = zooms instanceof ZoomRange ? zooms._inner : zooms;
    this._inner = new binding.TilePlanWrapper(b, z);
  }

  get bounds() {
    const inner = this._inner.bounds;
    const e = Object.create(Extent.prototype);
    e._inner = inner;
    return e;
  }

  get zooms() {
    const inner = this._inner.zooms;
    const z = Object.create(ZoomRange.prototype);
    z._inner = inner;
    return z;
  }

  level(zoom) { return this._inner.level(zoom); }
  levels() { return this._inner.levels(); }
  tileCount() { return this._inner.tileCount(); }
  tile_count() { return this._inner.tileCount(); }
  iterTiles() { return this._inner.iterTiles().map(t => { const tile = Object.create(Tile.prototype); tile._inner = t; return tile; }); }
  iter_tiles() { return this.iterTiles(); }
}

class Project {
  constructor(inner) {
    this._inner = inner;
  }

  static open(path) {
    const inner = binding.ProjectWrapper.open(path);
    return new Project(inner);
  }

  get path() { return this._inner.path; }
  get format() { return this._inner.format; }

  info() { return this._inner.info(); }

  render(output, options = {}) {
    return this._inner.render(output, options.width, options.height, options.dpi);
  }
}

function planTiles(bounds, zoom) {
  return binding.planTiles(bounds, zoom);
}

function plan_tiles(bounds, zoom) {
  return planTiles(bounds, zoom);
}

function version() {
  return binding.version();
}

const MAX_LATITUDE = binding.getMaxLatitude ? binding.getMaxLatitude() : 85.0511287798066;
const MAX_ZOOM = binding.getMaxZoom ? binding.getMaxZoom() : 22;

module.exports = {
  Extent,
  Crs,
  Tile,
  ZoomRange,
  TilePlan,
  Project,
  planTiles,
  plan_tiles,
  version,
  MAX_LATITUDE,
  MAX_ZOOM,
  // Raw binding for advanced use
  _binding: binding,
  _hasNative: !loadError,
};

// ES module interop
module.exports.default = module.exports;
