//! Node.js / TypeScript bindings for qgis-rs — native-speed API via NAPI-RS.
//!
//! This crate exposes `qgis-render` types (Extent, Crs, Tile, TilePlan, Project, etc.)
//! and plugin SDK helpers to Node.js/TypeScript at native Rust speed.
//!
//! The npm package `qgis-rs` ships:
//! - `qgis-rs.<platform>.node` — NAPI addon (this crate)
//! - `qgis-cli` / `qgis-plugin` binaries (Rust, built via cargo)
//! - TypeScript wrappers in `index.js` / `index.d.ts`

use napi_derive::napi;
use qgis_render::{Crs, Extent, Project, ProjectFormat, Tile, TilePlan, ZoomRange};
use std::path::PathBuf;

// ── Extent ──────────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct ExtentWrapper {
    inner: Extent,
}

#[napi]
impl ExtentWrapper {
    #[napi(constructor)]
    pub fn new(min_x: f64, min_y: f64, max_x: f64, max_y: f64) -> napi::Result<Self> {
        let e = Extent::new(min_x, min_y, max_x, max_y);
        if !e.is_valid() {
            return Err(napi::Error::from_reason(format!(
                "invalid extent: {min_x},{min_y},{max_x},{max_y} — must be ordered min<=max and finite"
            )));
        }
        Ok(Self { inner: e })
    }

    #[napi(factory)]
    pub fn parse(text: String) -> napi::Result<Self> {
        Extent::parse(&text)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(getter)]
    pub fn min_x(&self) -> f64 {
        self.inner.min_x
    }
    #[napi(getter)]
    pub fn min_y(&self) -> f64 {
        self.inner.min_y
    }
    #[napi(getter)]
    pub fn max_x(&self) -> f64 {
        self.inner.max_x
    }
    #[napi(getter)]
    pub fn max_y(&self) -> f64 {
        self.inner.max_y
    }

    #[napi]
    pub fn width(&self) -> f64 {
        self.inner.width()
    }
    #[napi]
    pub fn height(&self) -> f64 {
        self.inner.height()
    }
    #[napi]
    pub fn is_valid(&self) -> bool {
        self.inner.is_valid()
    }
    #[napi]
    pub fn contains(&self, x: f64, y: f64) -> bool {
        self.inner.contains(x, y)
    }
    #[napi]
    pub fn intersects(&self, other: &ExtentWrapper) -> bool {
        self.inner.intersects(&other.inner)
    }
    #[napi]
    pub fn to_string(&self) -> String {
        self.inner.to_string()
    }
    #[napi]
    pub fn to_array(&self) -> Vec<f64> {
        vec![
            self.inner.min_x,
            self.inner.min_y,
            self.inner.max_x,
            self.inner.max_y,
        ]
    }
    #[napi]
    pub fn equals(&self, other: &ExtentWrapper) -> bool {
        self.inner == other.inner
    }
}

// ── Crs ─────────────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct CrsWrapper {
    inner: Crs,
}

#[napi]
impl CrsWrapper {
    #[napi(constructor)]
    pub fn new(auth_id: String) -> napi::Result<Self> {
        Crs::from_auth_id(&auth_id)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(factory)]
    pub fn from_auth_id(auth_id: String) -> napi::Result<Self> {
        Self::new(auth_id)
    }

    #[napi(factory)]
    pub fn from_epsg(code: u32) -> napi::Result<Self> {
        Self::new(format!("EPSG:{code}"))
    }

    #[napi(factory)]
    pub fn wgs84() -> Self {
        Self {
            inner: Crs::wgs84(),
        }
    }

    #[napi(factory)]
    pub fn web_mercator() -> Self {
        Self {
            inner: Crs::web_mercator(),
        }
    }

    #[napi(getter)]
    pub fn auth_id(&self) -> String {
        self.inner.auth_id().to_string()
    }

    #[napi]
    pub fn name(&self) -> Option<String> {
        self.inner.name().map(|s| s.to_string())
    }

    #[napi]
    pub fn is_geographic(&self) -> bool {
        matches!(self.inner.units(), qgis_render::Units::Degrees)
    }

    #[napi]
    pub fn is_projected(&self) -> bool {
        matches!(self.inner.units(), qgis_render::Units::Meters)
    }

    #[napi]
    pub fn to_string(&self) -> String {
        self.inner.auth_id().to_string()
    }

    #[napi]
    pub fn equals(&self, other: &CrsWrapper) -> bool {
        self.inner == other.inner
    }
}

// ── Tile ────────────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct TileWrapper {
    inner: Tile,
}

#[napi]
impl TileWrapper {
    #[napi(constructor)]
    pub fn new(z: u32, x: u32, y: u32) -> Self {
        Self {
            inner: Tile::new(z, x, y),
        }
    }

    #[napi(factory)]
    pub fn from_lon_lat(z: u32, lon: f64, lat: f64) -> Self {
        Self {
            inner: Tile::from_lon_lat(z, lon, lat),
        }
    }

    #[napi(getter)]
    pub fn z(&self) -> u32 {
        self.inner.z
    }
    #[napi(getter)]
    pub fn x(&self) -> u32 {
        self.inner.x
    }
    #[napi(getter)]
    pub fn y(&self) -> u32 {
        self.inner.y
    }

    #[napi]
    pub fn bounds(&self) -> ExtentWrapper {
        ExtentWrapper {
            inner: self.inner.bounds(),
        }
    }

    #[napi]
    pub fn to_string(&self) -> String {
        format!("{}/{}/{}", self.inner.z, self.inner.x, self.inner.y)
    }

    #[napi]
    pub fn equals(&self, other: &TileWrapper) -> bool {
        self.inner == other.inner
    }
}

// ── ZoomRange ───────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct ZoomRangeWrapper {
    inner: ZoomRange,
}

#[napi]
impl ZoomRangeWrapper {
    #[napi(constructor)]
    pub fn new(min: u32, max: u32) -> napi::Result<Self> {
        ZoomRange::new(min, max)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(factory)]
    pub fn parse(text: String) -> napi::Result<Self> {
        ZoomRange::parse(&text)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(getter)]
    pub fn min(&self) -> u32 {
        self.inner.min
    }
    #[napi(getter)]
    pub fn max(&self) -> u32 {
        self.inner.max
    }

    #[napi]
    pub fn count(&self) -> u32 {
        self.inner.count()
    }

    #[napi]
    pub fn to_string(&self) -> String {
        if self.inner.min == self.inner.max {
            format!("{}", self.inner.min)
        } else {
            format!("{}-{}", self.inner.min, self.inner.max)
        }
    }

    #[napi]
    pub fn equals(&self, other: &ZoomRangeWrapper) -> bool {
        self.inner == other.inner
    }
}

// ── ZoomLevelPlan ───────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct ZoomLevelPlanWrapper {
    inner: qgis_render::ZoomLevelPlan,
}

#[napi]
impl ZoomLevelPlanWrapper {
    #[napi(getter)]
    pub fn zoom(&self) -> u32 {
        self.inner.zoom
    }
    #[napi(getter)]
    pub fn x_min(&self) -> u32 {
        self.inner.x_min
    }
    #[napi(getter)]
    pub fn x_max(&self) -> u32 {
        self.inner.x_max
    }
    #[napi(getter)]
    pub fn y_min(&self) -> u32 {
        self.inner.y_min
    }
    #[napi(getter)]
    pub fn y_max(&self) -> u32 {
        self.inner.y_max
    }

    #[napi]
    pub fn tile_count(&self) -> i64 {
        self.inner.tile_count() as i64
    }
}

// ── TilePlan ────────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct TilePlanWrapper {
    inner: TilePlan,
}

#[napi]
impl TilePlanWrapper {
    #[napi(constructor)]
    pub fn new(bounds: &ExtentWrapper, zooms: &ZoomRangeWrapper) -> napi::Result<Self> {
        TilePlan::new(bounds.inner, zooms.inner)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(getter)]
    pub fn bounds(&self) -> ExtentWrapper {
        ExtentWrapper {
            inner: self.inner.bounds,
        }
    }

    #[napi(getter)]
    pub fn zooms(&self) -> ZoomRangeWrapper {
        ZoomRangeWrapper {
            inner: self.inner.zooms,
        }
    }

    #[napi]
    pub fn level(&self, zoom: u32) -> ZoomLevelPlanWrapper {
        ZoomLevelPlanWrapper {
            inner: self.inner.level(zoom),
        }
    }

    #[napi]
    pub fn levels(&self) -> Vec<ZoomLevelPlanWrapper> {
        self.inner
            .levels()
            .into_iter()
            .map(|inner| ZoomLevelPlanWrapper { inner })
            .collect()
    }

    #[napi]
    pub fn tile_count(&self) -> i64 {
        self.inner.tile_count() as i64
    }

    #[napi]
    pub fn iter_tiles(&self) -> Vec<TileWrapper> {
        self.inner
            .iter()
            .map(|inner| TileWrapper { inner })
            .collect()
    }
}

// ── Project ─────────────────────────────────────────────────────────────────

#[napi]
#[derive(Clone, Debug)]
pub struct ProjectWrapper {
    inner: Project,
}

#[napi]
impl ProjectWrapper {
    #[napi(factory)]
    pub fn open(path: String) -> napi::Result<Self> {
        Project::open(&path)
            .map(|inner| Self { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi(getter)]
    pub fn path(&self) -> String {
        self.inner.path().display().to_string()
    }

    #[napi(getter)]
    pub fn format(&self) -> String {
        match self.inner.format() {
            ProjectFormat::Qgs => "qgs".to_string(),
            ProjectFormat::Qgz => "qgz".to_string(),
        }
    }

    #[napi]
    pub fn info(&self) -> napi::Result<ProjectInfoWrapper> {
        self.inner
            .info()
            .map(|inner| ProjectInfoWrapper { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }

    #[napi]
    pub fn render(
        &self,
        output: String,
        width: Option<u32>,
        height: Option<u32>,
        dpi: Option<f64>,
    ) -> napi::Result<RenderedMapWrapper> {
        use qgis_render::RenderSettings;
        let mut settings =
            RenderSettings::new(&output).map_err(|e| napi::Error::from_reason(e.to_string()))?;
        if let Some(w) = width {
            let h = height.unwrap_or(w);
            settings = settings.with_size(w, h);
        } else if let Some(h) = height {
            settings = settings.with_size(h, h);
        }
        if let Some(d) = dpi {
            settings = settings.with_dpi(d);
        }
        self.inner
            .render(&settings)
            .map(|inner| RenderedMapWrapper { inner })
            .map_err(|e| napi::Error::from_reason(e.to_string()))
    }
}

#[napi]
#[derive(Clone, Debug)]
pub struct ProjectInfoWrapper {
    inner: qgis_render::ProjectInfo,
}

#[napi]
impl ProjectInfoWrapper {
    #[napi(getter)]
    pub fn path(&self) -> String {
        self.inner.path.display().to_string()
    }
    #[napi(getter)]
    pub fn format(&self) -> String {
        self.inner.format.extension().to_string()
    }
    #[napi(getter)]
    pub fn size_bytes(&self) -> i64 {
        self.inner.size_bytes as i64
    }
    #[napi(getter)]
    pub fn crs(&self) -> Option<CrsWrapper> {
        self.inner.crs.clone().map(|inner| CrsWrapper { inner })
    }
    #[napi(getter)]
    pub fn layer_count(&self) -> Option<u32> {
        self.inner.layer_count.map(|c| c as u32)
    }
    #[napi(getter)]
    pub fn note(&self) -> Option<String> {
        self.inner.note.clone()
    }

    #[napi]
    pub fn to_json(&self) -> String {
        serde_json::to_string(&self.inner).unwrap_or_else(|_| "{}".to_string())
    }
}

#[napi]
#[derive(Clone, Debug)]
pub struct RenderedMapWrapper {
    inner: qgis_render::RenderedMap,
}

#[napi]
impl RenderedMapWrapper {
    #[napi(getter)]
    pub fn path(&self) -> String {
        self.inner.path.display().to_string()
    }
    #[napi(getter)]
    pub fn bytes(&self) -> i64 {
        self.inner.bytes as i64
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

#[napi]
pub fn plan_tiles(bounds: String, zoom: String) -> napi::Result<TilePlanResult> {
    let extent = Extent::parse(&bounds).map_err(|e| napi::Error::from_reason(e.to_string()))?;
    let zooms = ZoomRange::parse(&zoom).map_err(|e| napi::Error::from_reason(e.to_string()))?;
    let plan = TilePlan::new(extent, zooms).map_err(|e| napi::Error::from_reason(e.to_string()))?;
    let total = plan.tile_count() as i64;
    let levels = plan
        .levels()
        .into_iter()
        .map(|l| ZoomLevelInfo {
            zoom: l.zoom,
            x_min: l.x_min,
            x_max: l.x_max,
            y_min: l.y_min,
            y_max: l.y_max,
            tile_count: l.tile_count() as i64,
        })
        .collect();
    Ok(TilePlanResult { total, levels })
}

// Tile and byte counts cross the boundary as `i64`, not `u64`.
//
// napi 2.16 implements `ToNapiValue`/`FromNapiValue` for `i64` through
// `napi_create_int64`/`napi_get_value_int64` (available since N-API 1), but
// `u64` only exists on the BigInt path in `js_values/bigint.rs` — a *one-way*
// `impl ToNapiValue for u64`, with no `FromNapiValue` at all and no
// `bigint64` feature in this major version. A `#[napi(object)]` field needs
// both directions, which is exactly the six E0277s (`u64: ToNapiValue` /
// `u64: FromNapiValue`) this file used to fail with.
//
// `i64` is also what the shipped contract promises: `index.d.ts` declares these
// as `number`, and `fallback.js` computes plain numbers — returning BigInt
// would split the pure-JS fallback from the native addon. Counts of tiles and
// file sizes never approach 2^63, so the narrowing is lossless in practice.
#[napi(object)]
pub struct ZoomLevelInfo {
    pub zoom: u32,
    pub x_min: u32,
    pub x_max: u32,
    pub y_min: u32,
    pub y_max: u32,
    pub tile_count: i64,
}

#[napi(object)]
pub struct TilePlanResult {
    pub total: i64,
    pub levels: Vec<ZoomLevelInfo>,
}

#[napi]
pub fn version() -> String {
    qgis_render::VERSION.to_string()
}

#[napi]
pub fn get_max_latitude() -> f64 {
    qgis_render::MAX_LATITUDE
}

#[napi]
pub fn get_max_zoom() -> u32 {
    qgis_render::MAX_ZOOM
}
