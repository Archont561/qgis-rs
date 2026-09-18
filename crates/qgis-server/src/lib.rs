//! The qgis-rs HTTP server: WMS, WFS, XYZ tiles and OGC API Features.
//!
//! Routing is implemented here and fully covered by tests; the HTTP listener
//! itself is not wired up yet, so [`Server::serve`] returns
//! [`qgis_render::Error::Unimplemented`].
//!
//! ```
//! use qgis_server::{Endpoint, ServerConfig, Server};
//!
//! let server = Server::new(ServerConfig::new(8080));
//! assert_eq!(server.address(), "0.0.0.0:8080");
//! assert!(matches!(server.route("/wms").endpoint, Endpoint::Wms));
//! ```

use std::path::PathBuf;

use qgis_render::{Error, Result};

/// Which OGC endpoint a request is asking for.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Endpoint {
    /// `GET /` — the landing page.
    Landing,
    /// `GET /health` — liveness probe.
    Health,
    /// `GET /wms` — OGC Web Map Service.
    Wms,
    /// `GET /wfs` — OGC Web Feature Service.
    Wfs,
    /// `GET /tiles/{z}/{x}/{y}.png` — XYZ tile pyramid.
    Tiles,
    /// `GET /collections` — OGC API Features collection list.
    Collections,
    /// `GET /collections/{name}/items` — OGC API Features items.
    CollectionItems,
    /// Nothing is served at that path.
    NotFound,
}

/// The result of routing a request path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Route {
    /// The project the request is for, in multi-project mode.
    pub project: Option<String>,
    /// The endpoint behind it.
    pub endpoint: Endpoint,
}

/// How the server should be started.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ServerConfig {
    /// Interface to bind to. `0.0.0.0` serves every interface.
    pub host: String,
    /// TCP port.
    pub port: u16,
    /// Single-project mode: serve this project.
    pub project: Option<PathBuf>,
    /// Multi-project mode: serve every project in this directory, routed by
    /// the first path segment.
    pub projects_dir: Option<PathBuf>,
    /// Send CORS headers so browser maps can use the server directly.
    pub cors: bool,
    /// Rendered-tile cache size, in megabytes.
    pub cache_mb: u32,
}

impl ServerConfig {
    /// A configuration bound to `0.0.0.0:port`, serving no project yet.
    #[must_use]
    pub fn new(port: u16) -> Self {
        Self {
            host: "0.0.0.0".to_string(),
            port,
            project: None,
            projects_dir: None,
            cors: true,
            cache_mb: 256,
        }
    }

    /// Serve a single project.
    #[must_use]
    pub fn with_project(mut self, project: impl Into<PathBuf>) -> Self {
        self.project = Some(project.into());
        self
    }

    /// Serve every project in a directory.
    #[must_use]
    pub fn with_projects_dir(mut self, projects_dir: impl Into<PathBuf>) -> Self {
        self.projects_dir = Some(projects_dir.into());
        self
    }

    /// Turn CORS headers on or off.
    #[must_use]
    pub const fn with_cors(mut self, cors: bool) -> Self {
        self.cors = cors;
        self
    }

    /// `true` when exactly one of the two project modes is configured.
    #[must_use]
    pub fn is_configured(&self) -> bool {
        self.project.is_some() != self.projects_dir.is_some()
    }
}

/// A configured server.
#[derive(Debug, Clone, PartialEq)]
pub struct Server {
    config: ServerConfig,
}

impl Server {
    /// Build a server from a configuration.
    #[must_use]
    pub const fn new(config: ServerConfig) -> Self {
        Self { config }
    }

    /// The configuration this server was built with.
    #[must_use]
    pub const fn config(&self) -> &ServerConfig {
        &self.config
    }

    /// The `host:port` the server will bind to.
    #[must_use]
    pub fn address(&self) -> String {
        format!("{}:{}", self.config.host, self.config.port)
    }

    /// Work out which project and endpoint a request path refers to.
    ///
    /// In multi-project mode the first path segment names the project, unless
    /// it is itself an endpoint name — `/berlin/wms` is the WMS of the
    /// `berlin` project, while `/health` is still the health probe.
    #[must_use]
    pub fn route(&self, path: &str) -> Route {
        let mut segments = path
            .split('/')
            .filter(|segment| !segment.is_empty())
            .map(str::to_string);

        let first = match segments.next() {
            None => {
                return Route {
                    project: None,
                    endpoint: Endpoint::Landing,
                }
            }
            Some(segment) => segment,
        };

        let as_endpoint = endpoint_for(&first, segments.clone().collect::<Vec<_>>().as_slice());
        if as_endpoint != Endpoint::NotFound || self.config.projects_dir.is_none() {
            return Route {
                project: None,
                endpoint: as_endpoint,
            };
        }

        let rest = segments.collect::<Vec<_>>();
        let endpoint = rest.first().map_or(Endpoint::Landing, |segment| {
            endpoint_for(segment, &rest[1..])
        });
        Route {
            project: Some(first),
            endpoint,
        }
    }

    /// Bind the port and start serving.
    ///
    /// # Errors
    ///
    /// Always [`qgis_render::Error::Unimplemented`] until the HTTP listener
    /// lands.
    pub fn serve(&self) -> Result<()> {
        Err(Error::Unimplemented {
            feature: "the HTTP listener",
        })
    }
}

/// Map a single path segment (plus whatever follows it) onto an endpoint.
fn endpoint_for(segment: &str, rest: &[String]) -> Endpoint {
    match segment {
        "health" => Endpoint::Health,
        "wms" => Endpoint::Wms,
        "wfs" => Endpoint::Wfs,
        "tiles" => Endpoint::Tiles,
        "collections" => match rest {
            [_name, tail] if tail == "items" => Endpoint::CollectionItems,
            [] => Endpoint::Collections,
            _ => Endpoint::NotFound,
        },
        _ => Endpoint::NotFound,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn single_project() -> Server {
        Server::new(ServerConfig::new(8080).with_project("map.qgs"))
    }

    fn multi_project() -> Server {
        Server::new(ServerConfig::new(8080).with_projects_dir("./maps"))
    }

    #[test]
    fn routes_single_project_requests() {
        let server = single_project();
        let cases = [
            ("/", Endpoint::Landing),
            ("/health", Endpoint::Health),
            ("/wms", Endpoint::Wms),
            ("/wfs", Endpoint::Wfs),
            ("/tiles/10/551/342.png", Endpoint::Tiles),
            ("/collections", Endpoint::Collections),
            ("/collections/buildings/items", Endpoint::CollectionItems),
            ("/collections/buildings", Endpoint::NotFound),
            ("/nope", Endpoint::NotFound),
        ];
        for (path, expected) in cases {
            let route = server.route(path);
            assert_eq!(route.endpoint, expected, "{path}");
            assert_eq!(route.project, None, "{path}");
        }
    }

    #[test]
    fn routes_multi_project_requests() {
        let server = multi_project();

        let route = server.route("/berlin/wms");
        assert_eq!(route.project.as_deref(), Some("berlin"));
        assert_eq!(route.endpoint, Endpoint::Wms);

        let route = server.route("/paris/collections/buildings/items");
        assert_eq!(route.project.as_deref(), Some("paris"));
        assert_eq!(route.endpoint, Endpoint::CollectionItems);

        // Reserved names win over project names.
        let route = server.route("/health");
        assert_eq!(route.project, None);
        assert_eq!(route.endpoint, Endpoint::Health);

        // A bare project name is that project's landing page.
        let route = server.route("/warsaw");
        assert_eq!(route.project.as_deref(), Some("warsaw"));
        assert_eq!(route.endpoint, Endpoint::Landing);
    }

    #[test]
    fn reports_the_bind_address() {
        assert_eq!(single_project().address(), "0.0.0.0:8080");
    }

    #[test]
    fn a_configuration_needs_exactly_one_project_mode() {
        assert!(single_project().config().is_configured());
        assert!(multi_project().config().is_configured());
        assert!(!ServerConfig::new(8080).is_configured());
    }

    #[test]
    fn serving_is_not_wired_up_yet() {
        let error = single_project().serve().expect_err("no listener yet");
        assert!(matches!(error, Error::Unimplemented { .. }));
        assert!(error.to_string().contains("QGIS backend"));
    }
}
