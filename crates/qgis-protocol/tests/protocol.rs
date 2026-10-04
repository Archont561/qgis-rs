//! The envelope, exercised the way a binding sees it: as JSON.
//!
//! What these cover is the transport's two promises — a request round-trips
//! without losing a field, and the operation set is *closed*, so an unknown
//! verb is a parse error here rather than a surprise inside the engine.

use proptest::prelude::*;
use qgis_protocol::*;
use rstest::rstest;
use serde_json::{json, Value};

#[test]
fn a_request_round_trips_through_json() {
    let request = EngineRequest::new(Operation::DescribeExtent, json!({"extent": "14,50,15,51"}));
    let text = serde_json::to_string(&request).expect("serialisable");
    assert!(text.contains("\"operation\":\"describe_extent\""));
    assert_eq!(
        serde_json::from_str::<EngineRequest>(&text).expect("parses"),
        request
    );
}

#[test]
fn payload_is_optional() {
    let request: EngineRequest =
        serde_json::from_str(r#"{"transport_version":1,"operation":"ping"}"#)
            .expect("payload defaults");
    assert_eq!(request.payload, Value::Null);
}

#[test]
fn an_unknown_operation_is_a_parse_error_not_a_variant() {
    let error =
        serde_json::from_str::<EngineRequest>(r#"{"transport_version":1,"operation":"teleport"}"#);
    assert!(error.is_err(), "the operation set is closed");
}

#[test]
fn every_operation_is_listed_by_engine_info() {
    for name in Operation::all() {
        let request = format!(r#"{{"transport_version":1,"operation":"{name}"}}"#);
        serde_json::from_str::<EngineRequest>(&request)
            .unwrap_or_else(|_| panic!("{name} is advertised but does not parse"));
    }
}

/// `as_str` and the serde encoding are one wire name, per kind.
///
/// One case per variant: the list is the contract, and a case that goes red
/// names the kind that drifted instead of stopping the loop at the first one.
#[rstest]
#[case(ErrorKind::InvalidRequest)]
#[case(ErrorKind::UnsupportedTransport)]
#[case(ErrorKind::InvalidPayload)]
#[case(ErrorKind::Io)]
#[case(ErrorKind::ProjectNotFound)]
#[case(ErrorKind::UnsupportedProject)]
#[case(ErrorKind::InvalidExtent)]
#[case(ErrorKind::InvalidZoomRange)]
#[case(ErrorKind::UnknownCrs)]
#[case(ErrorKind::UnknownImageFormat)]
#[case(ErrorKind::Unimplemented)]
#[case(ErrorKind::InvalidOperation)]
#[case(ErrorKind::InvalidObjectId)]
#[case(ErrorKind::NotInitialized)]
#[case(ErrorKind::Qgis)]
#[case(ErrorKind::Internal)]
fn error_kinds_spell_themselves_the_way_serde_does(#[case] kind: ErrorKind) {
    let encoded = serde_json::to_value(kind).expect("serialisable");
    assert_eq!(encoded, json!(kind.as_str()));
}

#[test]
fn responses_carry_this_builds_transport_version() {
    assert_eq!(
        EngineResponse::success(json!({})).transport_version,
        TRANSPORT_VERSION
    );
    assert!(!EngineResponse::failure(json!({})).ok);
}

#[test]
fn layer_lifecycle_types_match_the_shared_golden_fixture() {
    let fixture: Value =
        serde_json::from_str(include_str!("../../../test-fixtures/layer-lifecycle.json"))
            .expect("shared layer fixture is valid JSON");

    let open_request: EngineRequest =
        serde_json::from_value(fixture["operations"]["layer_open"]["request"].clone())
            .expect("layer.open request uses the protocol");
    assert_eq!(open_request.operation, Operation::LayerOpen);
    let typed_open: LayerOpenRequest =
        serde_json::from_value(open_request.payload).expect("typed layer.open payload");
    assert_eq!(typed_open.provider, "ogr");
    assert_eq!(typed_open.name.as_deref(), Some("points"));
    let open_response: LayerOpenResponse =
        serde_json::from_value(fixture["operations"]["layer_open"]["result"].clone())
            .expect("typed layer.open result");
    assert_eq!(open_response.layer_id, 7);

    let info: LayerInfoResponse =
        serde_json::from_value(fixture["operations"]["layer_info"]["result"].clone())
            .expect("typed layer.info result");
    assert_eq!(
        serde_json::to_value(&info).expect("serialisable"),
        fixture["operations"]["layer_info"]["result"]
    );
    assert_eq!(info.fields[0].type_name, "Integer64");

    let info_request: LayerIdRequest =
        serde_json::from_value(fixture["operations"]["layer_info"]["request"]["payload"].clone())
            .expect("typed layer.info payload");
    assert_eq!(info_request.layer_id, 7);

    let feature_page: LayerFeaturesResponse =
        serde_json::from_value(fixture["operations"]["layer_features"]["result"].clone())
            .expect("typed layer.features result");
    assert_eq!(feature_page.features.len(), 2);
    assert_eq!(feature_page.next_offset, Some(2));
    assert_eq!(feature_page.features[0].attributes["name"], "alpha");

    let close: LayerCloseResponse =
        serde_json::from_value(fixture["operations"]["layer_close"]["result"].clone())
            .expect("typed layer.close result");
    assert!(close.closed);
}

#[test]
fn layer_feature_requests_apply_the_bounded_default() {
    let request: LayerFeaturesRequest =
        serde_json::from_value(json!({"layer_id": 7})).expect("defaults deserialize");
    assert_eq!(request.offset, 0);
    assert_eq!(request.limit, 100);
}

proptest! {
    #[test]
    fn requests_preserve_operation_and_payload_through_json(
        operation in prop::sample::select(vec![
            Operation::Ping,
            Operation::EngineInfo,
            Operation::ApiDescribe,
            Operation::DescribeExtent,
            Operation::DescribeCrs,
            Operation::DescribeZoomRange,
            Operation::PlanTiles,
        ]),
        value in any::<i64>(),
    ) {
        let request = EngineRequest::new(operation, json!({"value": value}));
        let encoded = serde_json::to_string(&request).expect("request serialises");
        let decoded: EngineRequest = serde_json::from_str(&encoded).expect("request parses");

        prop_assert_eq!(decoded, request);
    }

    #[test]
    fn response_envelopes_keep_the_transport_invariant(value in any::<i64>()) {
        let success = EngineResponse::success(json!({"value": value}));
        let failure = EngineResponse::failure(
            json!({"kind": ErrorKind::InvalidPayload.as_str()}),
        );

        prop_assert_eq!(success.transport_version, TRANSPORT_VERSION);
        prop_assert!(success.ok);
        prop_assert_eq!(failure.transport_version, TRANSPORT_VERSION);
        prop_assert!(!failure.ok);
    }
}

#[test]
fn native_artifact_contract_is_path_based() {
    let render = RenderMapResponse {
        path: "/tmp/map.png".to_string(),
        format: "png".to_string(),
        bytes: 42,
        width: 1024,
        height: 768,
    };
    let export = ExportFeaturesResponse {
        path: "/tmp/points.geojson".to_string(),
        format: "geojson".to_string(),
        bytes: 84,
        layer: "points".to_string(),
        feature_count: 3,
    };
    let render_json = serde_json::to_value(&render).expect("render response serialises");
    let export_json = serde_json::to_value(&export).expect("export response serialises");
    assert_eq!(render_json["path"], "/tmp/map.png");
    assert_eq!(render_json["bytes"], 42);
    assert_eq!(export_json["path"], "/tmp/points.geojson");
    assert_eq!(export_json["feature_count"], 3);
    assert!(render_json.get("data").is_none());
    assert!(export_json.get("features").is_none());
}
