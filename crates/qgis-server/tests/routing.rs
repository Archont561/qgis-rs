//! Routing, which is the part of the server that exists: every OGC path maps
//! to one [`Endpoint`], in single-project and multi-project mode alike.
//! Binding a socket does not, and says so.

use qgis_render::Error;
use qgis_server::*;

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
