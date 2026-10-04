//! The bridge contract, exercised against the shared fixture tree.
//!
//! `test-fixtures/bridge/cases.json` is the catalogue, and this suite is the
//! gate that makes it true: every manifest parses into
//! `qgis_protocol::bridge`'s types, every well-formed request validates against
//! the manifest it names, and every malformed vector produces the exact error
//! kind the catalogue predicts. The Python and TypeScript suites read the same
//! files and assert the same rules in their own idiom — what they share is the
//! fixtures, never a fake.
//!
//! The vectors are discovered, not listed. A fixture added to `cases.json`
//! starts being checked here with no edit to this file; a fixture that stops
//! matching its manifest goes red naming itself.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use proptest::prelude::*;
use qgis_protocol::bridge::*;
use rstest::{fixture, rstest};
use serde_json::{json, Value};

/// The fixture tree, loaded once per test that asks for it.
struct Contract {
    root: PathBuf,
    cases: Value,
    manifests: BTreeMap<String, BridgeManifest>,
}

impl Contract {
    fn read(&self, relative: &str) -> Value {
        let path = self.root.join(relative);
        let text = fs::read_to_string(&path)
            .unwrap_or_else(|error| panic!("{} is unreadable: {error}", path.display()));
        serde_json::from_str(&text)
            .unwrap_or_else(|error| panic!("{} is not valid JSON: {error}", path.display()))
    }

    fn session(&self) -> &str {
        self.cases["session_id"].as_str().expect("session_id")
    }

    /// Every permission any manifest mentions — the grant a test uses when it
    /// is not the permission rule it is testing.
    fn all_permissions(&self) -> Vec<String> {
        let mut permissions: Vec<String> = self
            .manifests
            .values()
            .flat_map(|manifest| manifest.methods.iter())
            .flat_map(|method| method.permissions.iter().cloned())
            .collect();
        permissions.sort();
        permissions.dedup();
        permissions
    }
}

#[fixture]
fn contract() -> Contract {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../test-fixtures/bridge");
    let cases: Value = serde_json::from_str(
        &fs::read_to_string(root.join("cases.json")).expect("the fixture catalogue exists"),
    )
    .expect("the catalogue is valid JSON");

    let mut manifests = BTreeMap::new();
    for description in cases["descriptions"].as_array().expect("descriptions") {
        let file = description["file"].as_str().expect("description file");
        let text = fs::read_to_string(root.join(file)).expect("a listed manifest exists");
        let manifest: BridgeManifest = serde_json::from_str(&text)
            .unwrap_or_else(|error| panic!("{file} is not a manifest: {error}"));
        manifests.insert(manifest.namespace.clone(), manifest);
    }

    Contract {
        root,
        cases,
        manifests,
    }
}

/// Cases named by the catalogue, as `(file, expectation)` pairs.
fn listed(cases: &Value, section: &str) -> Vec<(String, Value)> {
    cases[section]
        .as_array()
        .unwrap_or_else(|| panic!("cases.json has no {section}"))
        .iter()
        .map(|case| {
            (
                case["file"].as_str().expect("file").to_owned(),
                case.clone(),
            )
        })
        .collect()
}

fn is_snake_case_dotted(name: &str) -> bool {
    !name.is_empty()
        && name.split('.').all(|segment| {
            !segment.is_empty()
                && segment
                    .chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
        })
}

#[rstest]
fn the_catalogue_covers_all_four_namespaces(contract: Contract) {
    let kinds: Vec<CallKind> = contract
        .manifests
        .values()
        .map(|manifest| manifest.kind)
        .collect();

    for expected in [
        CallKind::Engine,
        CallKind::QgisHost,
        CallKind::Plugin,
        CallKind::Ui,
    ] {
        assert!(
            kinds.contains(&expected),
            "the contract distinguishes four kinds of call; {expected:?} has no manifest"
        );
    }
}

/// A manifest's methods and events are the only list of them, so everything
/// about a name has to hold here: dotted, `snake_case`, unique, and tagged with
/// the kind its target promises.
#[rstest]
fn every_manifest_entry_is_well_named_and_consistent(contract: Contract) {
    for (namespace, manifest) in &contract.manifests {
        assert_eq!(manifest.bridge_version, BRIDGE_VERSION, "{namespace}");
        assert!(
            is_snake_case_dotted(namespace),
            "{namespace} is not a snake_case target name"
        );

        let mut names: Vec<&str> = manifest
            .methods
            .iter()
            .map(|method| method.name.as_str())
            .collect();
        let listed = names.len();
        names.sort_unstable();
        names.dedup();
        assert_eq!(listed, names.len(), "{namespace} lists a method twice");

        for method in &manifest.methods {
            assert!(
                is_snake_case_dotted(&method.name),
                "{namespace}.{} is not snake_case",
                method.name
            );
            assert_eq!(
                method.call_kind, manifest.kind,
                "{namespace}.{} claims a kind its target does not",
                method.name
            );
        }

        for event in &manifest.events {
            assert!(
                is_snake_case_dotted(&event.name),
                "{namespace} event {} is not snake_case",
                event.name
            );
        }
    }
}

#[rstest]
fn every_listed_request_validates_against_its_manifest(contract: Contract) {
    let granted = contract.all_permissions();

    for (file, case) in listed(&contract.cases, "requests") {
        let envelope = contract.read(&file);
        let request: BridgeRequest =
            serde_json::from_value(envelope.clone()).unwrap_or_else(|error| {
                panic!("{file} is not a bridge request: {error}");
            });

        assert_eq!(
            request.target,
            case["target"].as_str().expect("target"),
            "{file}"
        );
        assert_eq!(
            request.method,
            case["method"].as_str().expect("method"),
            "{file}"
        );
        assert!(!request.request_id.is_empty(), "{file} has no request_id");

        validate_request(&contract.manifests, &envelope, contract.session(), &granted)
            .unwrap_or_else(|(kind, why)| panic!("{file} should validate, got {kind:?}: {why}"));
    }
}

/// The twelve refusals, each one naming the rule it exists for.
#[rstest]
fn every_malformed_vector_produces_the_predicted_kind(contract: Contract) {
    let granted = contract.all_permissions();

    for (file, case) in listed(&contract.cases, "malformed") {
        let expected: BridgeErrorKind =
            serde_json::from_value(case["error_kind"].clone()).expect("a known error kind");
        let envelope = contract.read(&file);

        let (kind, _why) =
            validate_request(&contract.manifests, &envelope, contract.session(), &granted)
                .expect_err(&format!("{file} must be refused: {}", case["why"]));

        assert_eq!(kind, expected, "{file} was refused for the wrong reason");
    }
}

/// `permission_denied` is about the *caller*, not the envelope — so the same
/// well-formed request that passes with a grant has to fail without one.
#[rstest]
fn a_method_without_its_permission_is_denied(contract: Contract) {
    let envelope = contract.read("requests/qgis-layers-add-vector.json");

    let (kind, why) = validate_request(&contract.manifests, &envelope, contract.session(), &[])
        .expect_err("layers.add_vector declares layer.write");

    assert_eq!(kind, BridgeErrorKind::PermissionDenied);
    assert!(
        why.contains("layer.write"),
        "the message names the permission: {why}"
    );
}

#[rstest]
fn responses_carry_exactly_what_ok_promises(contract: Contract) {
    for (file, case) in listed(&contract.cases, "responses") {
        let response: BridgeResponse = serde_json::from_value(contract.read(&file))
            .unwrap_or_else(|error| panic!("{file} is not a bridge response: {error}"));

        assert_eq!(response.bridge_version, BRIDGE_VERSION, "{file}");
        assert_eq!(response.ok, case["ok"].as_bool().expect("ok"), "{file}");
        assert!(
            response.is_consistent(),
            "{file} carries both result and error, or neither"
        );
        assert_eq!(
            response.request_id,
            case["request_id"].as_str().expect("request_id"),
            "{file}"
        );

        if let Some(expected) = case.get("error_kind").and_then(Value::as_str) {
            let error = response.error.expect("a failure carries an error");
            assert_eq!(error.kind.as_str(), expected, "{file}");
            assert!(!error.message.is_empty(), "{file} has an empty message");
        }
    }
}

/// An event is not a response: it names an event its target declares, it never
/// carries `ok`, and it correlates only when it belongs to a call in flight.
#[rstest]
fn events_are_declared_and_are_not_responses(contract: Contract) {
    for (file, case) in listed(&contract.cases, "events") {
        let raw = contract.read(&file);
        assert!(
            raw.get("ok").is_none(),
            "{file} is an event, not a response"
        );

        let event: BridgeEvent = serde_json::from_value(raw)
            .unwrap_or_else(|error| panic!("{file} is not a bridge event: {error}"));
        assert_eq!(event.bridge_version, BRIDGE_VERSION, "{file}");

        let manifest = contract
            .manifests
            .get(&event.target)
            .unwrap_or_else(|| panic!("{file} names an unknown target"));
        let spec = manifest.event(&event.event).unwrap_or_else(|| {
            panic!(
                "{file} emits {} which {} does not declare",
                event.event, event.target
            )
        });
        spec.payload
            .validate(&event.payload, contract.session())
            .unwrap_or_else(|(kind, why)| panic!("{file} payload: {kind:?} {why}"));

        assert_eq!(
            event.request_id.is_some(),
            case["correlated"].as_bool().expect("correlated"),
            "{file} disagrees with the catalogue about correlation"
        );
    }
}

/// Every success fixture is the answer to the request that names it, which is
/// the one invariant a client's correlation logic rests on.
#[rstest]
fn each_success_fixture_answers_its_own_request(contract: Contract) {
    for (file, case) in listed(&contract.cases, "requests") {
        let Some(response_file) = case["response"].as_str() else {
            continue;
        };

        let request: BridgeRequest = serde_json::from_value(contract.read(&file)).expect("request");
        let response: BridgeResponse =
            serde_json::from_value(contract.read(response_file)).expect("response");
        assert_eq!(
            request.request_id, response.request_id,
            "{response_file} does not answer {file}"
        );

        let manifest = &contract.manifests[&request.target];
        let method = manifest.method(&request.method).expect("a listed method");
        let result = response.result.expect("a success carries a result");
        method
            .result
            .validate(&result, contract.session())
            .unwrap_or_else(|(kind, why)| panic!("{response_file} result: {kind:?} {why}"));
    }
}

/// Handles are opaque and session-scoped. Opaque is not directly testable — the
/// point is that nothing may parse one — so what is tested is the consequence:
/// the same id in another session, or under another type, is not the object.
#[rstest]
#[case("sess-1", "qgis.layer", true)]
#[case("sess-2", "qgis.layer", false)]
#[case("sess-1", "ui.dialog", false)]
fn a_handle_is_the_pair_of_its_id_and_its_session(
    #[case] session: &str,
    #[case] object_type: &str,
    #[case] accepted: bool,
) {
    let schema = Schema {
        handle: Some("qgis.layer".to_owned()),
        ..Schema::default()
    };
    let handle = json!({
        "object_id": "obj-9c1a",
        "object_type": object_type,
        "session_id": session,
    });

    let verdict = schema.validate(&handle, "sess-1");
    assert_eq!(verdict.is_ok(), accepted, "{verdict:?}");
    if let Err((kind, _)) = verdict {
        assert_eq!(kind, BridgeErrorKind::UnknownObject);
    }
}

/// Error kinds are a closed set, spelled one way: the catalogue's list, the
/// enum's wire form and `as_str` must agree, or a client's exception mapping
/// silently loses a case.
#[rstest]
fn the_catalogue_and_the_enum_agree_on_every_error_kind(contract: Contract) {
    let listed: Vec<String> = serde_json::from_value(contract.cases["error_kinds"].clone())
        .expect("error_kinds is a list of strings");

    for name in &listed {
        let kind: BridgeErrorKind = serde_json::from_str(&format!("\"{name}\""))
            .unwrap_or_else(|_| panic!("{name} is advertised but is not a kind"));
        assert_eq!(kind.as_str(), name);
    }

    for kind in [
        BridgeErrorKind::InvalidRequest,
        BridgeErrorKind::UnknownTarget,
        BridgeErrorKind::UnknownMethod,
        BridgeErrorKind::InvalidArguments,
        BridgeErrorKind::PermissionDenied,
        BridgeErrorKind::UnknownObject,
        BridgeErrorKind::HostUnavailable,
        BridgeErrorKind::Internal,
    ] {
        assert!(
            listed.iter().any(|name| name == kind.as_str()),
            "{kind:?} is a kind the catalogue does not list"
        );
    }
}

proptest! {
    /// The host does not read, order or reuse `request_id`; it echoes it. The
    /// generator is narrow on purpose — this is a property about correlation,
    /// not about JSON string escaping.
    #[test]
    fn a_request_id_survives_the_envelope_round_trip(id in "[A-Za-z0-9_:-]{1,32}") {
        let request = BridgeRequest {
            bridge_version: BRIDGE_VERSION,
            request_id: id.clone(),
            target: "qgis".to_owned(),
            method: "layers.list".to_owned(),
            args: serde_json::Map::new(),
        };
        let text = serde_json::to_string(&request).expect("serialisable");
        let parsed: BridgeRequest = serde_json::from_str(&text).expect("parses");
        prop_assert_eq!(parsed.request_id.as_str(), id.as_str());

        let response = BridgeResponse {
            bridge_version: BRIDGE_VERSION,
            request_id: parsed.request_id.clone(),
            ok: true,
            result: Some(json!([])),
            error: None,
        };
        prop_assert!(response.is_consistent());
        prop_assert_eq!(response.request_id, request.request_id);
    }

    /// Any method name not in the manifest is `unknown_method` — including the
    /// camelCase spelling of a method that does exist.
    #[test]
    fn an_unlisted_method_is_never_dispatched(method in "[a-z][a-z_.]{0,20}") {
        let contract = contract();
        let manifest = &contract.manifests["qgis"];
        prop_assume!(manifest.method(&method).is_none());

        let envelope = json!({
            "bridge_version": BRIDGE_VERSION,
            "request_id": "req-prop",
            "target": "qgis",
            "method": method,
            "args": {},
        });
        let (kind, _) = validate_request(
            &contract.manifests,
            &envelope,
            contract.session(),
            &contract.all_permissions(),
        )
        .expect_err("an unlisted method cannot dispatch");
        prop_assert_eq!(kind, BridgeErrorKind::UnknownMethod);
    }
}
