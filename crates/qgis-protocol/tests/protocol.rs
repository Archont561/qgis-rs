//! The envelope, exercised the way a binding sees it: as JSON.
//!
//! What these cover is the transport's two promises — a request round-trips
//! without losing a field, and the operation set is *closed*, so an unknown
//! verb is a parse error here rather than a surprise inside the engine.

use qgis_protocol::*;
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

#[test]
fn error_kinds_spell_themselves_the_way_serde_does() {
    let kinds = [
        ErrorKind::InvalidRequest,
        ErrorKind::UnsupportedTransport,
        ErrorKind::InvalidPayload,
        ErrorKind::Io,
        ErrorKind::ProjectNotFound,
        ErrorKind::UnsupportedProject,
        ErrorKind::InvalidExtent,
        ErrorKind::InvalidZoomRange,
        ErrorKind::UnknownCrs,
        ErrorKind::UnknownImageFormat,
        ErrorKind::Unimplemented,
        ErrorKind::InvalidOperation,
        ErrorKind::InvalidObjectId,
        ErrorKind::NotInitialized,
        ErrorKind::Qgis,
        ErrorKind::Internal,
    ];
    for kind in kinds {
        let encoded = serde_json::to_value(kind).expect("serialisable");
        assert_eq!(encoded, json!(kind.as_str()));
    }
}

#[test]
fn responses_carry_this_builds_transport_version() {
    assert_eq!(
        EngineResponse::success(json!({})).transport_version,
        TRANSPORT_VERSION
    );
    assert!(!EngineResponse::failure(json!({})).ok);
}
