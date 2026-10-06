//! Public seam for the wire-protocol documentation gate.
//!
//! The gate's whole value is that it goes red, so most of these tests damage
//! a known-good page in one specific way and assert the resulting complaint
//! names that damage. A validator that only ever sees valid input is a
//! validator nobody has tested.

use qgis_protocol::{ErrorKind, Operation, TRANSPORT_VERSION};
use xtask::protocol_docs::{self, PYTHON_FALLBACK_EXCEPTION};

/// A page that satisfies every rule, built from the protocol itself so these
/// tests do not carry a second copy of the operation list.
fn valid_page() -> String {
    let operations = Operation::all()
        .iter()
        .map(|name| format!("| `{name}` | `{{}}` | `{{}}` |"))
        .collect::<Vec<_>>()
        .join("\n");

    let errors = ErrorKind::all()
        .iter()
        .map(|kind| {
            let python = expected_python(kind.as_str());
            format!(
                "| `{}` | `{python}` | `EngineError` (`kind: \"{}\"`) |",
                kind.as_str(),
                kind.as_str()
            )
        })
        .collect::<Vec<_>>()
        .join("\n");

    format!(
        r#"---
title: Engine wire protocol
---

Everything on the wire is `snake_case`, including operation names. The
JavaScript client renames at its own edge in
`ts-packages/qgis-node/src/index.js`.

{{/* protocol-docs:transport-version:begin */}}
This page documents `TRANSPORT_VERSION` {TRANSPORT_VERSION}.
{{/* protocol-docs:transport-version:end */}}

{{/* protocol-docs:operations:begin */}}
| Operation | Payload | Result |
| --- | --- | --- |
{operations}
{{/* protocol-docs:operations:end */}}

{{/* protocol-docs:errors:begin */}}
| Kind | Python | JavaScript |
| --- | --- | --- |
{errors}
{{/* protocol-docs:errors:end */}}
"#
    )
}

/// The Python mapping the real client implements, mirrored here so a test can
/// build a correct page without reading the repository.
fn expected_python(kind: &str) -> &'static str {
    match kind {
        "project_not_found" => "ProjectNotFound",
        "io" => "EngineIOError",
        "unimplemented" => "Unimplemented",
        "unsupported_transport" => "TransportMismatch",
        _ => PYTHON_FALLBACK_EXCEPTION,
    }
}

/// The mapping the gate compares against is read from the client, not from a
/// list inside the gate — otherwise the two could drift and the gate would
/// certify the drift.
#[test]
fn the_python_mapping_is_read_from_the_client_source() {
    let source = r#"
_EXCEPTION_BY_KIND: Dict[str, Type[EngineError]] = {
    "project_not_found": ProjectNotFound,
    "io": EngineIOError,
    "unimplemented": Unimplemented,
    "unsupported_transport": TransportMismatch,
}
"#;
    let mapping = protocol_docs::python_exception_by_kind(source);
    assert_eq!(mapping.get("io").map(String::as_str), Some("EngineIOError"));
    assert_eq!(
        mapping.get("unsupported_transport").map(String::as_str),
        Some("TransportMismatch")
    );
    assert_eq!(mapping.len(), 4);
}

#[test]
fn a_complete_page_has_no_violations() {
    let mapping = protocol_docs::python_exception_by_kind(
        r#"_EXCEPTION_BY_KIND = {
        "project_not_found": ProjectNotFound,
        "io": EngineIOError,
        "unimplemented": Unimplemented,
        "unsupported_transport": TransportMismatch,
    }"#,
    );
    let violations = protocol_docs::violations(&valid_page(), &mapping);
    assert!(
        violations.is_empty(),
        "unexpected violations: {violations:?}"
    );
}

/// Build the mapping every damage test uses.
fn mapping() -> std::collections::BTreeMap<String, String> {
    protocol_docs::python_exception_by_kind(
        r#"_EXCEPTION_BY_KIND = {
        "project_not_found": ProjectNotFound,
        "io": EngineIOError,
        "unimplemented": Unimplemented,
        "unsupported_transport": TransportMismatch,
    }"#,
    )
}

#[test]
fn an_undocumented_operation_is_a_violation() {
    let page = valid_page().replace("| `plan_tiles` | `{}` | `{}` |\n", "");
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("plan_tiles")),
        "dropping an operation row must be reported: {violations:?}"
    );
}

#[test]
fn an_invented_operation_is_a_violation() {
    let page = valid_page().replace(
        "| `plan_tiles` | `{}` | `{}` |",
        "| `plan_tiles` | `{}` | `{}` |\n| `teleport` | `{}` | `{}` |",
    );
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("teleport")),
        "documenting an operation the engine does not serve must be reported: {violations:?}"
    );
}

#[test]
fn an_undocumented_error_kind_is_a_violation() {
    let page = valid_page().replace(
        "| `unknown_crs` | `InvalidInput` | `EngineError` (`kind: \"unknown_crs\"`) |\n",
        "",
    );
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("unknown_crs")),
        "dropping an error row must be reported: {violations:?}"
    );
}

#[test]
fn the_wrong_python_exception_is_a_violation() {
    let page = valid_page().replace("| `io` | `EngineIOError` |", "| `io` | `InvalidInput` |");
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations
            .iter()
            .any(|v| v.contains("io") && v.contains("EngineIOError")),
        "a row that misreports the Python exception must be reported: {violations:?}"
    );
}

#[test]
fn a_row_that_forgets_engine_error_is_a_violation() {
    let page = valid_page().replace(
        "| `qgis` | `InvalidInput` | `EngineError` (`kind: \"qgis\"`) |",
        "| `qgis` | `InvalidInput` | raises something |",
    );
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("qgis")),
        "every kind reaches JavaScript as EngineError: {violations:?}"
    );
}

#[test]
fn a_stale_transport_version_is_a_violation() {
    let page = valid_page().replace(
        &format!("`TRANSPORT_VERSION` {TRANSPORT_VERSION}"),
        "`TRANSPORT_VERSION` 99",
    );
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("transport")),
        "the page must state the version this build speaks: {violations:?}"
    );
}

#[test]
fn a_missing_marked_block_is_a_violation_rather_than_a_pass() {
    let page = valid_page()
        .replace("{/* protocol-docs:operations:begin */}", "")
        .replace("{/* protocol-docs:operations:end */}", "");
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("operations")),
        "an unparseable page must fail, not silently document nothing: {violations:?}"
    );
}

#[test]
fn the_snake_case_rule_and_the_rename_edge_are_required() {
    let page = valid_page().replace("`snake_case`", "lower case");
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("snake_case")),
        "AC#4 is the naming rule: {violations:?}"
    );

    let page = valid_page().replace("ts-packages/qgis-node/src/index.js", "somewhere");
    let violations = protocol_docs::violations(&page, &mapping());
    assert!(
        violations.iter().any(|v| v.contains("rename")),
        "AC#4 also asks where the JS client renames: {violations:?}"
    );
}

/// The real page in the real tree has to pass, which is what the gate runs.
#[test]
fn the_published_page_satisfies_the_gate() {
    protocol_docs::run(&protocol_docs::repo_root_from_manifest()).expect("published page is valid");
}
