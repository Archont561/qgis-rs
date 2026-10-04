//! Routing, which is the part of the server that exists: every OGC path maps
//! to one [`Endpoint`], in single-project and multi-project mode alike.
//! Binding a socket does not, and says so.
//!
//! The two server shapes are rstest fixtures rather than helper functions, so
//! a test that needs one declares it in its signature and the table of paths
//! below is a list of `#[case]`s — one test per path, named after the path it
//! checks, instead of one test with a loop whose first failure hides the rest.

use qgis_render::Error;
use qgis_server::*;
use rstest::{fixture, rstest};

/// A server serving exactly one project file.
#[fixture]
fn single_project() -> Server {
    Server::new(ServerConfig::new(8080).with_project("map.qgs"))
}

/// A server serving a directory of projects, addressed by name.
#[fixture]
fn multi_project() -> Server {
    Server::new(ServerConfig::new(8080).with_projects_dir("./maps"))
}

#[rstest]
#[case("/", Endpoint::Landing)]
#[case("/health", Endpoint::Health)]
#[case("/wms", Endpoint::Wms)]
#[case("/wfs", Endpoint::Wfs)]
#[case("/tiles/10/551/342.png", Endpoint::Tiles)]
#[case("/collections", Endpoint::Collections)]
#[case("/collections/buildings/items", Endpoint::CollectionItems)]
#[case("/collections/buildings", Endpoint::NotFound)]
#[case("/nope", Endpoint::NotFound)]
fn routes_single_project_requests(
    single_project: Server,
    #[case] path: &str,
    #[case] expected: Endpoint,
) {
    let route = single_project.route(path);
    assert_eq!(route.endpoint, expected, "{path}");
    assert_eq!(route.project, None, "{path}");
}

#[rstest]
#[case("/berlin/wms", Some("berlin"), Endpoint::Wms)]
#[case(
    "/paris/collections/buildings/items",
    Some("paris"),
    Endpoint::CollectionItems
)]
// Reserved names win over project names.
#[case("/health", None, Endpoint::Health)]
// A bare project name is that project's landing page.
#[case("/warsaw", Some("warsaw"), Endpoint::Landing)]
fn routes_multi_project_requests(
    multi_project: Server,
    #[case] path: &str,
    #[case] project: Option<&str>,
    #[case] expected: Endpoint,
) {
    let route = multi_project.route(path);
    assert_eq!(route.project.as_deref(), project, "{path}");
    assert_eq!(route.endpoint, expected, "{path}");
}

#[rstest]
fn reports_the_bind_address(single_project: Server) {
    assert_eq!(single_project.address(), "0.0.0.0:8080");
}

#[rstest]
fn a_configuration_needs_exactly_one_project_mode(single_project: Server, multi_project: Server) {
    assert!(single_project.config().is_configured());
    assert!(multi_project.config().is_configured());
    assert!(!ServerConfig::new(8080).is_configured());
}

#[rstest]
fn serving_is_not_wired_up_yet(single_project: Server) {
    let error = single_project.serve().expect_err("no listener yet");
    assert!(matches!(error, Error::Unimplemented { .. }));
    assert!(error.to_string().contains("QGIS backend"));
}
