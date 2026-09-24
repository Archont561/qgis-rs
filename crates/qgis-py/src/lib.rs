//! Python bindings for qgis-rs — native-speed API exposed via PyO3.
//!
//! This crate is the Rust side of the `qgis-rs` Python package. It wraps
//! `qgis-render` (pure Rust, no QGIS needed) and, when the `qgis-sys` backend
//! is available, the full QGIS operations.
//!
//! The Python package layout is:
//!
//! ```text
//! python/qgis_rs/__init__.py   → high-level Python API (imports from _core)
//! python/qgis_rs/_core.so      → this crate (cdylib)
//! ```
//!
//! Users install via `pip install qgis-rs` or `conda install -c conda-forge qgis-rs`
//! and get both `import qgis_rs` and the `qgis-cli` binary at native speed.

// pyo3's `#[pyfunction]`/`#[pymethods]` wrappers perform an identity
// `From<PyErr> for PyErr` conversion for the `PyResult<T>` alias; clippy's
// `useless_conversion` flags it but `#[allow]` on the item does not reach the
// macro output (PyO3/pyo3#4828, fixed upstream in 0.23.5). Module-level allow
// is the documented workaround.
#![allow(clippy::useless_conversion)]

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use qgis_render::{Crs, Extent, Project, ProjectFormat, Tile, TilePlan, ZoomRange};

// ── Extent ──────────────────────────────────────────────────────────────────

#[pyclass(name = "Extent")]
#[derive(Clone, Debug)]
pub struct PyExtent {
    inner: Extent,
}

#[pymethods]
impl PyExtent {
    #[new]
    fn new(min_x: f64, min_y: f64, max_x: f64, max_y: f64) -> PyResult<Self> {
        let e = Extent::new(min_x, min_y, max_x, max_y);
        if !e.is_valid() {
            return Err(PyValueError::new_err(format!(
                "invalid extent: {min_x},{min_y},{max_x},{max_y} — must be ordered min<=max and finite"
            )));
        }
        Ok(Self { inner: e })
    }

    #[staticmethod]
    fn parse(text: &str) -> PyResult<Self> {
        Extent::parse(text)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[getter]
    fn min_x(&self) -> f64 {
        self.inner.min_x
    }
    #[getter]
    fn min_y(&self) -> f64 {
        self.inner.min_y
    }
    #[getter]
    fn max_x(&self) -> f64 {
        self.inner.max_x
    }
    #[getter]
    fn max_y(&self) -> f64 {
        self.inner.max_y
    }

    fn width(&self) -> f64 {
        self.inner.width()
    }
    fn height(&self) -> f64 {
        self.inner.height()
    }

    fn is_valid(&self) -> bool {
        self.inner.is_valid()
    }

    fn contains(&self, x: f64, y: f64) -> bool {
        self.inner.contains(x, y)
    }

    fn intersects(&self, other: &PyExtent) -> bool {
        self.inner.intersects(&other.inner)
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }
    fn __repr__(&self) -> String {
        format!(
            "Extent({},{},{},{})",
            self.inner.min_x, self.inner.min_y, self.inner.max_x, self.inner.max_y
        )
    }

    fn __eq__(&self, other: &PyExtent) -> bool {
        self.inner == other.inner
    }

    fn to_tuple(&self) -> (f64, f64, f64, f64) {
        (
            self.inner.min_x,
            self.inner.min_y,
            self.inner.max_x,
            self.inner.max_y,
        )
    }

    fn to_list(&self) -> Vec<f64> {
        vec![
            self.inner.min_x,
            self.inner.min_y,
            self.inner.max_x,
            self.inner.max_y,
        ]
    }
}

// ── Crs ─────────────────────────────────────────────────────────────────────

#[pyclass(name = "Crs")]
#[derive(Clone, Debug)]
pub struct PyCrs {
    inner: Crs,
}

#[pymethods]
impl PyCrs {
    #[new]
    fn new(auth_id: &str) -> PyResult<Self> {
        Crs::from_auth_id(auth_id)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn from_auth_id(auth_id: &str) -> PyResult<Self> {
        Self::new(auth_id)
    }

    #[staticmethod]
    fn from_epsg(code: u32) -> PyResult<Self> {
        Self::new(&format!("EPSG:{code}"))
    }

    #[staticmethod]
    fn wgs84() -> Self {
        Self {
            inner: Crs::wgs84(),
        }
    }

    #[staticmethod]
    fn web_mercator() -> Self {
        Self {
            inner: Crs::web_mercator(),
        }
    }

    #[getter]
    fn auth_id(&self) -> String {
        self.inner.auth_id().to_string()
    }

    fn name(&self) -> Option<String> {
        self.inner.name().map(|s| s.to_string())
    }

    fn is_geographic(&self) -> bool {
        matches!(self.inner.units(), qgis_render::Units::Degrees)
    }

    fn is_projected(&self) -> bool {
        matches!(self.inner.units(), qgis_render::Units::Meters)
    }

    fn __str__(&self) -> String {
        self.inner.auth_id().to_string()
    }
    fn __repr__(&self) -> String {
        format!("Crs({})", self.inner.auth_id())
    }
    fn __eq__(&self, other: &PyCrs) -> bool {
        self.inner == other.inner
    }
}

// ── Tile ────────────────────────────────────────────────────────────────────

#[pyclass(name = "Tile")]
#[derive(Clone, Debug)]
pub struct PyTile {
    inner: Tile,
}

#[pymethods]
impl PyTile {
    #[new]
    fn new(z: u32, x: u32, y: u32) -> Self {
        Self {
            inner: Tile::new(z, x, y),
        }
    }

    #[staticmethod]
    fn from_lon_lat(z: u32, lon: f64, lat: f64) -> Self {
        Self {
            inner: Tile::from_lon_lat(z, lon, lat),
        }
    }

    #[getter]
    fn z(&self) -> u32 {
        self.inner.z
    }
    #[getter]
    fn x(&self) -> u32 {
        self.inner.x
    }
    #[getter]
    fn y(&self) -> u32 {
        self.inner.y
    }

    fn bounds(&self) -> PyExtent {
        PyExtent {
            inner: self.inner.bounds(),
        }
    }

    fn __str__(&self) -> String {
        format!("{}/{}/{}", self.inner.z, self.inner.x, self.inner.y)
    }
    fn __repr__(&self) -> String {
        format!(
            "Tile(z={}, x={}, y={})",
            self.inner.z, self.inner.x, self.inner.y
        )
    }
    fn __eq__(&self, other: &PyTile) -> bool {
        self.inner == other.inner
    }
    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

// ── ZoomRange ───────────────────────────────────────────────────────────────

#[pyclass(name = "ZoomRange")]
#[derive(Clone, Debug)]
pub struct PyZoomRange {
    inner: ZoomRange,
}

#[pymethods]
impl PyZoomRange {
    #[new]
    fn new(min: u32, max: u32) -> PyResult<Self> {
        ZoomRange::new(min, max)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn parse(text: &str) -> PyResult<Self> {
        ZoomRange::parse(text)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[getter]
    fn min(&self) -> u32 {
        self.inner.min
    }
    #[getter]
    fn max(&self) -> u32 {
        self.inner.max
    }

    fn count(&self) -> u32 {
        self.inner.count()
    }

    fn __str__(&self) -> String {
        if self.inner.min == self.inner.max {
            format!("{}", self.inner.min)
        } else {
            format!("{}-{}", self.inner.min, self.inner.max)
        }
    }
    fn __repr__(&self) -> String {
        format!("ZoomRange({}-{})", self.inner.min, self.inner.max)
    }
    fn __eq__(&self, other: &PyZoomRange) -> bool {
        self.inner == other.inner
    }
}

// ── ZoomLevelPlan ───────────────────────────────────────────────────────────

#[pyclass(name = "ZoomLevelPlan")]
#[derive(Clone, Debug)]
pub struct PyZoomLevelPlan {
    inner: qgis_render::ZoomLevelPlan,
}

#[pymethods]
impl PyZoomLevelPlan {
    #[getter]
    fn zoom(&self) -> u32 {
        self.inner.zoom
    }
    #[getter]
    fn x_min(&self) -> u32 {
        self.inner.x_min
    }
    #[getter]
    fn x_max(&self) -> u32 {
        self.inner.x_max
    }
    #[getter]
    fn y_min(&self) -> u32 {
        self.inner.y_min
    }
    #[getter]
    fn y_max(&self) -> u32 {
        self.inner.y_max
    }

    fn tile_count(&self) -> u64 {
        self.inner.tile_count()
    }

    fn __repr__(&self) -> String {
        format!(
            "ZoomLevelPlan(zoom={}, x={}..{}, y={}..{}, count={})",
            self.inner.zoom,
            self.inner.x_min,
            self.inner.x_max,
            self.inner.y_min,
            self.inner.y_max,
            self.inner.tile_count()
        )
    }
}

// ── TilePlan ────────────────────────────────────────────────────────────────

#[pyclass(name = "TilePlan")]
#[derive(Clone, Debug)]
pub struct PyTilePlan {
    inner: TilePlan,
}

#[pymethods]
impl PyTilePlan {
    #[new]
    fn new(bounds: &PyExtent, zooms: &PyZoomRange) -> PyResult<Self> {
        TilePlan::new(bounds.inner, zooms.inner)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[getter]
    fn bounds(&self) -> PyExtent {
        PyExtent {
            inner: self.inner.bounds,
        }
    }

    #[getter]
    fn zooms(&self) -> PyZoomRange {
        PyZoomRange {
            inner: self.inner.zooms,
        }
    }

    fn level(&self, zoom: u32) -> PyZoomLevelPlan {
        PyZoomLevelPlan {
            inner: self.inner.level(zoom),
        }
    }

    fn levels(&self) -> Vec<PyZoomLevelPlan> {
        self.inner
            .levels()
            .into_iter()
            .map(|inner| PyZoomLevelPlan { inner })
            .collect()
    }

    fn tile_count(&self) -> u64 {
        self.inner.tile_count()
    }

    fn iter_tiles(&self) -> Vec<PyTile> {
        self.inner.iter().map(|inner| PyTile { inner }).collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "TilePlan(bounds={}, zooms={}-{}, tiles={})",
            self.inner.bounds,
            self.inner.zooms.min,
            self.inner.zooms.max,
            self.inner.tile_count()
        )
    }
}

// ── Project ─────────────────────────────────────────────────────────────────

#[pyclass(name = "Project")]
#[derive(Clone, Debug)]
pub struct PyProject {
    inner: Project,
}

#[pymethods]
impl PyProject {
    #[staticmethod]
    fn open(path: &str) -> PyResult<Self> {
        Project::open(path)
            .map(|inner| Self { inner })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[getter]
    fn path(&self) -> String {
        self.inner.path().display().to_string()
    }

    #[getter]
    fn format(&self) -> String {
        match self.inner.format() {
            ProjectFormat::Qgs => "qgs".to_string(),
            ProjectFormat::Qgz => "qgz".to_string(),
        }
    }

    fn info(&self) -> PyResult<PyProjectInfo> {
        self.inner
            .info()
            .map(|info| PyProjectInfo { inner: info })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    fn layers(&self) -> PyResult<Vec<PyLayerSummary>> {
        self.inner
            .layers()
            .map(|layers| {
                layers
                    .into_iter()
                    .map(|l| PyLayerSummary { inner: l })
                    .collect()
            })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    #[pyo3(signature = (output, width=None, height=None, extent=None, crs=None, dpi=None))]
    fn render(
        &self,
        output: &str,
        width: Option<u32>,
        height: Option<u32>,
        extent: Option<&PyExtent>,
        crs: Option<&PyCrs>,
        dpi: Option<f64>,
    ) -> PyResult<PyRenderedMap> {
        use qgis_render::RenderSettings;
        let mut settings =
            RenderSettings::new(output).map_err(|e| PyValueError::new_err(e.to_string()))?;
        if let Some(w) = width {
            let h = height.unwrap_or(w);
            settings = settings.with_size(w, h);
        } else if let Some(h) = height {
            settings = settings.with_size(h, h);
        }
        if let Some(e) = extent {
            settings = settings.with_extent(e.inner);
        }
        if let Some(c) = crs {
            settings = settings.with_crs(c.inner.clone());
        }
        if let Some(d) = dpi {
            settings = settings.with_dpi(d);
        }
        self.inner
            .render(&settings)
            .map(|rendered| PyRenderedMap { inner: rendered })
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> String {
        format!("Project(path={})", self.inner.path().display())
    }
}

#[pyclass(name = "ProjectInfo")]
#[derive(Clone, Debug)]
pub struct PyProjectInfo {
    inner: qgis_render::ProjectInfo,
}

#[pymethods]
impl PyProjectInfo {
    #[getter]
    fn path(&self) -> String {
        self.inner.path.display().to_string()
    }
    #[getter]
    fn format(&self) -> String {
        self.inner.format.extension().to_string()
    }
    #[getter]
    fn size_bytes(&self) -> u64 {
        self.inner.size_bytes
    }
    #[getter]
    fn crs(&self) -> Option<PyCrs> {
        self.inner.crs.clone().map(|inner| PyCrs { inner })
    }
    #[getter]
    fn layer_count(&self) -> Option<usize> {
        self.inner.layer_count
    }
    #[getter]
    fn extent(&self) -> Option<PyExtent> {
        self.inner.extent.map(|inner| PyExtent { inner })
    }
    #[getter]
    fn note(&self) -> Option<String> {
        self.inner.note.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "ProjectInfo(path={}, format={}, size={})",
            self.inner.path.display(),
            self.inner.format.extension(),
            self.inner.size_bytes
        )
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("path", self.inner.path.display().to_string())?;
        dict.set_item("format", self.inner.format.extension())?;
        dict.set_item("size_bytes", self.inner.size_bytes)?;
        dict.set_item("crs", self.inner.crs.as_ref().map(|c| c.auth_id()))?;
        dict.set_item("layer_count", self.inner.layer_count)?;
        dict.set_item("extent", self.inner.extent.map(|e| e.to_string()))?;
        dict.set_item("note", self.inner.note.clone())?;
        Ok(dict.into())
    }
}

#[pyclass(name = "LayerSummary")]
#[derive(Clone, Debug)]
pub struct PyLayerSummary {
    inner: qgis_render::LayerSummary,
}

#[pymethods]
impl PyLayerSummary {
    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }
    #[getter]
    fn provider(&self) -> String {
        self.inner.provider.clone()
    }
    #[getter]
    fn crs(&self) -> Option<PyCrs> {
        self.inner.crs.clone().map(|inner| PyCrs { inner })
    }
    #[getter]
    fn feature_count(&self) -> Option<i64> {
        self.inner.feature_count
    }
    #[getter]
    fn geometry_type(&self) -> Option<String> {
        self.inner.geometry_type.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "LayerSummary(name={}, provider={})",
            self.inner.name, self.inner.provider
        )
    }
}

#[pyclass(name = "RenderedMap")]
#[derive(Clone, Debug)]
pub struct PyRenderedMap {
    inner: qgis_render::RenderedMap,
}

#[pymethods]
impl PyRenderedMap {
    #[getter]
    fn path(&self) -> String {
        self.inner.path.display().to_string()
    }
    #[getter]
    fn bytes(&self) -> u64 {
        self.inner.bytes
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderedMap(path={}, bytes={})",
            self.inner.path.display(),
            self.inner.bytes
        )
    }
}

// ── RenderSettings ──────────────────────────────────────────────────────────

#[pyclass(name = "RenderSettings")]
#[derive(Clone, Debug)]
pub struct PyRenderSettings {
    inner: qgis_render::RenderSettings,
}

#[pymethods]
impl PyRenderSettings {
    #[new]
    #[pyo3(signature = (output, width=1024, height=768, dpi=96.0))]
    fn new(output: &str, width: u32, height: u32, dpi: f64) -> PyResult<Self> {
        let inner = qgis_render::RenderSettings::new(output)
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .with_size(width, height)
            .with_dpi(dpi);
        Ok(Self { inner })
    }

    #[getter]
    fn width(&self) -> u32 {
        self.inner.width
    }
    #[getter]
    fn height(&self) -> u32 {
        self.inner.height
    }
    #[getter]
    fn dpi(&self) -> f64 {
        self.inner.dpi
    }

    fn with_extent(&self, extent: &PyExtent) -> Self {
        Self {
            inner: self.inner.clone().with_extent(extent.inner),
        }
    }

    fn with_crs(&self, crs: &PyCrs) -> Self {
        Self {
            inner: self.inner.clone().with_crs(crs.inner.clone()),
        }
    }

    fn with_dpi(&self, dpi: f64) -> Self {
        Self {
            inner: self.inner.clone().with_dpi(dpi),
        }
    }

    fn with_layers(&self, layers: Vec<String>) -> Self {
        Self {
            inner: self.inner.clone().with_layers(layers),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderSettings(width={}, height={}, dpi={})",
            self.inner.width, self.inner.height, self.inner.dpi
        )
    }
}

// ── Helpers for CLI ─────────────────────────────────────────────────────────

type PlanLevel = (u32, u32, u32, u32, u32, u64);

#[pyfunction]
fn plan_tiles(bounds: &str, zoom: &str) -> PyResult<(u64, Vec<PlanLevel>)> {
    let extent = Extent::parse(bounds).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let zooms = ZoomRange::parse(zoom).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let plan = TilePlan::new(extent, zooms).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let total = plan.tile_count();
    let levels = plan
        .levels()
        .into_iter()
        .map(|l| (l.zoom, l.x_min, l.x_max, l.y_min, l.y_max, l.tile_count()))
        .collect();
    Ok((total, levels))
}

#[pyfunction]
fn version() -> String {
    qgis_render::VERSION.to_string()
}

// ── Module definition ───────────────────────────────────────────────────────

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyExtent>()?;
    m.add_class::<PyCrs>()?;
    m.add_class::<PyTile>()?;
    m.add_class::<PyZoomRange>()?;
    m.add_class::<PyZoomLevelPlan>()?;
    m.add_class::<PyTilePlan>()?;
    m.add_class::<PyProject>()?;
    m.add_class::<PyProjectInfo>()?;
    m.add_class::<PyLayerSummary>()?;
    m.add_class::<PyRenderedMap>()?;
    m.add_class::<PyRenderSettings>()?;

    m.add_function(wrap_pyfunction!(plan_tiles, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;

    m.add("__version__", qgis_render::VERSION)?;
    m.add("MAX_LATITUDE", qgis_render::MAX_LATITUDE)?;
    m.add("MAX_ZOOM", qgis_render::MAX_ZOOM)?;

    Ok(())
}
