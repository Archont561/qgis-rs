//! The plugin bridge contract: envelopes, manifests, handles, and the one
//! validator all three languages are checked against.
//!
//! This is **not** the engine transport in the parent module. The engine
//! transport is in-process Rust ↔ binding, request/response only, addressed by
//! a closed `operation` enum. The bridge is a plugin's web UI talking to its
//! Python host over QWebChannel: four targets, dotted method names, events,
//! permissions and object handles. Two wires, two version numbers —
//! [`BRIDGE_VERSION`] here, [`crate::TRANSPORT_VERSION`] there — so the engine
//! can rev its envelope without a plugin UI rebuild.
//!
//! The normative text is `.knowledge/bridge-test-contract.md`; the vectors are
//! `test-fixtures/bridge/`. What lives here is the *executable* half: the types
//! those fixtures must parse into, and [`validate_request`], the smallest
//! implementation of the dispatch rules that can tell the twelve malformed
//! vectors apart. A Python router and a TypeScript client are expected to reach
//! the same verdicts; this is the one that runs in CI.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

/// The shape version of the bridge envelope.
///
/// Bumped when a request, response or event field changes meaning. A host that
/// receives a version it does not know answers [`BridgeErrorKind::InvalidRequest`]
/// rather than guessing — a UI built against a future bridge fails loudly
/// against an old host instead of silently reading the wrong field.
pub const BRIDGE_VERSION: u32 = 1;

/// Which kind of thing a target — or one of its methods — is.
///
/// The distinction is the contract's, not a label: it decides what a test may
/// assume. `Engine` is answerable in a pure unit test; `QgisHost` needs a live
/// QGIS and must produce [`BridgeErrorKind::HostUnavailable`] rather than a
/// fake when there is none; `Plugin` is whatever a plugin declared; `Ui` is
/// stateful and answers an acknowledgement with the real news in an event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CallKind {
    /// Pure engine calls: geometry, tiles, CRS, project metadata.
    Engine,
    /// Calls that need a running QGIS.
    QgisHost,
    /// Methods a plugin exposes to its own web UI.
    Plugin,
    /// Stateful UI operations and the events they emit.
    Ui,
}

/// The machine-readable classification carried by every bridge failure.
///
/// A closed set, like the engine transport's [`crate::ErrorKind`] and for the
/// same reason: a client maps these onto its own language's exceptions, and
/// nothing anywhere matches on English prose.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BridgeErrorKind {
    /// The envelope is malformed: a missing field, a wrong type, an unknown
    /// `bridge_version`, positional `args`.
    InvalidRequest,
    /// No bridge object of that name is registered in this session.
    UnknownTarget,
    /// The target exists; the method is not in its manifest.
    UnknownMethod,
    /// The method exists; `args` does not satisfy its argument schema.
    InvalidArguments,
    /// The method is callable, but the plugin lacks the permission it declares.
    PermissionDenied,
    /// An object handle is unknown, expired, or belongs to another session.
    UnknownObject,
    /// The call needs QGIS, Qt or a WebEngine view, and it is not there.
    HostUnavailable,
    /// The handler raised. Spelled `internal_error` on the wire — `internal`
    /// alone reads like a flag rather than a failure.
    #[serde(rename = "internal_error")]
    Internal,
}

impl BridgeErrorKind {
    /// The wire spelling of this kind.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InvalidRequest => "invalid_request",
            Self::UnknownTarget => "unknown_target",
            Self::UnknownMethod => "unknown_method",
            Self::InvalidArguments => "invalid_arguments",
            Self::PermissionDenied => "permission_denied",
            Self::UnknownObject => "unknown_object",
            Self::HostUnavailable => "host_unavailable",
            Self::Internal => "internal_error",
        }
    }
}

/// A reference to something the host cannot serialise whole.
///
/// `object_id` is **opaque**: compare it, echo it, never parse or construct
/// one. The pair `(object_id, session_id)` is what identifies the object, which
/// is why presenting a handle to another session is
/// [`BridgeErrorKind::UnknownObject`] and not a miss.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ObjectHandle {
    /// Opaque id. No structure is promised and none may be relied on.
    pub object_id: String,
    /// The handle's manifest type, dotted and `snake_case` — `qgis.layer`.
    pub object_type: String,
    /// The session the handle is valid in.
    pub session_id: String,
}

/// One call from a plugin's web UI to its host.
///
/// `args` is a JSON **object**, always: a positional array does not parse, so
/// `malformed/positional-args.json` is an envelope error rather than an
/// argument error.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeRequest {
    /// The envelope shape the caller speaks. Checked against [`BRIDGE_VERSION`].
    pub bridge_version: u32,
    /// The caller's correlation string, opaque to the host and returned
    /// unchanged on success and on failure.
    pub request_id: String,
    /// Which bridge object to call: `engine`, `qgis`, `ui`, or a plugin's name.
    pub target: String,
    /// A dotted, `snake_case` method name from the target's manifest.
    pub method: String,
    /// Named arguments. Empty, never absent and never positional.
    #[serde(default)]
    pub args: Map<String, Value>,
}

/// One answer to a [`BridgeRequest`].
///
/// `ok` decides which field is present: `true` carries `result` and never
/// `error`, `false` carries `error` and never `result`. [`Self::is_consistent`]
/// is that rule, and the fixtures assert it.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeResponse {
    /// Always the host's [`BRIDGE_VERSION`].
    pub bridge_version: u32,
    /// The request's `request_id`, unchanged.
    pub request_id: String,
    /// Whether the call succeeded.
    pub ok: bool,
    /// The answer, when `ok`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    /// The failure, when not `ok`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<BridgeError>,
}

impl BridgeResponse {
    /// Whether exactly the field `ok` promises is present.
    #[must_use]
    pub const fn is_consistent(&self) -> bool {
        match self.ok {
            true => self.result.is_some() && self.error.is_none(),
            false => self.error.is_some() && self.result.is_none(),
        }
    }
}

/// The failure carried by a response whose `ok` is `false`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeError {
    /// What went wrong, machine-readably.
    pub kind: BridgeErrorKind,
    /// What went wrong, for a human reading a console.
    pub message: String,
    /// Anything structured worth attaching — the target, the method, the
    /// missing keys, the permission that was not granted.
    #[serde(default)]
    pub details: Value,
}

/// Something that happened, announced by the host without being asked.
///
/// An event is not a response: it has `event` and never `ok`. `request_id` is
/// present only when the event belongs to a call in flight (task progress) and
/// absent otherwise (a theme change).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeEvent {
    /// The envelope shape the host speaks.
    pub bridge_version: u32,
    /// A dotted, `snake_case` event name from the target's manifest.
    pub event: String,
    /// Which bridge object emitted it.
    pub target: String,
    /// The call this event belongs to, when it belongs to one.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub request_id: Option<String>,
    /// The event's payload, shaped by the manifest's event schema.
    pub payload: Value,
}

/// One target's manifest: the single source of its methods and events.
///
/// Nothing else may list them. A second spelling table in a binding, a doc page
/// or a test is exactly the duplication this type exists to prevent.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgeManifest {
    /// The envelope version this manifest describes.
    pub bridge_version: u32,
    /// The target's name, as it appears in a request's `target`.
    pub namespace: String,
    /// What kind of target it is.
    pub kind: CallKind,
    /// The manifest's own version, independent of [`BRIDGE_VERSION`].
    pub version: String,
    /// Prose for a human.
    #[serde(default)]
    pub doc: String,
    /// Every callable method.
    pub methods: Vec<MethodSpec>,
    /// Every event the target can emit.
    #[serde(default)]
    pub events: Vec<EventSpec>,
}

impl BridgeManifest {
    /// The named method, if this target has one.
    #[must_use]
    pub fn method(&self, name: &str) -> Option<&MethodSpec> {
        self.methods.iter().find(|method| method.name == name)
    }

    /// The named event, if this target can emit one.
    #[must_use]
    pub fn event(&self, name: &str) -> Option<&EventSpec> {
        self.events.iter().find(|event| event.name == name)
    }
}

/// One method: its arguments, its result, and what it is allowed to need.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MethodSpec {
    /// Dotted, `snake_case`.
    pub name: String,
    /// What answering it requires — see [`CallKind`].
    pub call_kind: CallKind,
    /// Permissions the plugin must have declared. Empty means unrestricted.
    #[serde(default)]
    pub permissions: Vec<String>,
    /// The shape of `args`.
    pub args: Schema,
    /// The shape of `result`.
    pub result: Schema,
}

/// One event: its name and the shape of its payload.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EventSpec {
    /// Dotted, `snake_case`.
    pub name: String,
    /// The shape of `payload`.
    pub payload: Schema,
}

/// A deliberately small JSON-Schema subset.
///
/// `type`, `properties`, `required`, `items`, `enum`, `additional_properties`
/// and `$handle`. Small because three languages have to agree on it offline,
/// and because a schema language rich enough to be interesting is one more
/// thing to test.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Schema {
    /// `object`, `array`, `string`, `number`, `integer`, `boolean`.
    #[serde(rename = "type", default, skip_serializing_if = "Option::is_none")]
    pub type_name: Option<String>,
    /// Member schemas, for an object.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub properties: Option<BTreeMap<String, Schema>>,
    /// Which members must be present.
    #[serde(default)]
    pub required: Vec<String>,
    /// The element schema, for an array.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub items: Option<Box<Schema>>,
    /// The closed set of allowed values.
    #[serde(rename = "enum", default, skip_serializing_if = "Option::is_none")]
    pub allowed: Option<Vec<Value>>,
    /// Whether members outside `properties` are tolerated. Defaults to tolerant
    /// so that a schema which says nothing stays permissive; the fixtures say
    /// `false` where a typo is likelier than an extension.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub additional_properties: Option<bool>,
    /// This value is an [`ObjectHandle`] of the named type.
    #[serde(rename = "$handle", default, skip_serializing_if = "Option::is_none")]
    pub handle: Option<String>,
}

impl Schema {
    /// Check one value against this schema, in the context of one session.
    ///
    /// The error kind is part of the contract, not an implementation detail: a
    /// handle that fails is [`BridgeErrorKind::UnknownObject`] — the caller's
    /// arguments were shaped correctly and the object was not there — while
    /// everything else is [`BridgeErrorKind::InvalidArguments`].
    ///
    /// # Errors
    ///
    /// Returns the kind and a human-readable reason for the first violation
    /// found.
    pub fn validate(
        &self,
        value: &Value,
        session_id: &str,
    ) -> Result<(), (BridgeErrorKind, String)> {
        if let Some(handle_type) = &self.handle {
            return validate_handle(value, handle_type, session_id);
        }

        if let Some(allowed) = &self.allowed {
            if !allowed.contains(value) {
                return Err((
                    BridgeErrorKind::InvalidArguments,
                    format!("{value} is not one of {allowed:?}"),
                ));
            }
        }

        let Some(type_name) = self.type_name.as_deref() else {
            return Ok(());
        };

        match (type_name, value) {
            ("object", Value::Object(members)) => self.validate_object(members, session_id),
            ("array", Value::Array(elements)) => {
                let Some(items) = &self.items else {
                    return Ok(());
                };
                elements
                    .iter()
                    .try_for_each(|element| items.validate(element, session_id))
            }
            ("string", Value::String(_))
            | ("boolean", Value::Bool(_))
            | ("number", Value::Number(_)) => Ok(()),
            ("integer", Value::Number(number)) if number.is_i64() || number.is_u64() => Ok(()),
            _ => Err((
                BridgeErrorKind::InvalidArguments,
                format!("expected {type_name}, got {value}"),
            )),
        }
    }

    fn validate_object(
        &self,
        members: &Map<String, Value>,
        session_id: &str,
    ) -> Result<(), (BridgeErrorKind, String)> {
        let properties = self.properties.clone().unwrap_or_default();

        for name in &self.required {
            if !members.contains_key(name) {
                return Err((
                    BridgeErrorKind::InvalidArguments,
                    format!("missing required member {name}"),
                ));
            }
        }

        for (name, member) in members {
            match properties.get(name) {
                Some(schema) => schema.validate(member, session_id)?,
                None if self.additional_properties == Some(false) => {
                    return Err((
                        BridgeErrorKind::InvalidArguments,
                        format!("unexpected member {name}"),
                    ))
                }
                None => {}
            }
        }

        Ok(())
    }
}

fn validate_handle(
    value: &Value,
    handle_type: &str,
    session_id: &str,
) -> Result<(), (BridgeErrorKind, String)> {
    let Ok(handle) = serde_json::from_value::<ObjectHandle>(value.clone()) else {
        return Err((
            BridgeErrorKind::InvalidArguments,
            format!("expected an object handle, got {value}"),
        ));
    };

    if handle.object_type != handle_type {
        return Err((
            BridgeErrorKind::UnknownObject,
            format!(
                "{} is a {}, not a {handle_type}",
                handle.object_id, handle.object_type
            ),
        ));
    }

    if handle.session_id != session_id {
        return Err((
            BridgeErrorKind::UnknownObject,
            format!(
                "{} belongs to {}, not to {session_id}",
                handle.object_id, handle.session_id
            ),
        ));
    }

    Ok(())
}

/// Dispatch one request against a session's manifests, without calling anything.
///
/// The smallest implementation of §2–§5 of the contract that can tell the
/// malformed vectors apart, in the order a host must check them: envelope,
/// version, target, method, permissions, then arguments. Order matters — a
/// typo'd method on an absent target is [`BridgeErrorKind::UnknownTarget`],
/// because the host cannot know what the method would have meant.
///
/// `granted` is the set of permissions the calling plugin declared.
///
/// # Errors
///
/// Returns the kind a host must answer with, and the reason to put in the
/// message.
pub fn validate_request(
    manifests: &BTreeMap<String, BridgeManifest>,
    envelope: &Value,
    session_id: &str,
    granted: &[String],
) -> Result<(), (BridgeErrorKind, String)> {
    let request: BridgeRequest = serde_json::from_value(envelope.clone())
        .map_err(|error| (BridgeErrorKind::InvalidRequest, error.to_string()))?;

    if request.bridge_version != BRIDGE_VERSION {
        return Err((
            BridgeErrorKind::InvalidRequest,
            format!(
                "bridge_version {} is not {BRIDGE_VERSION}",
                request.bridge_version
            ),
        ));
    }

    let manifest = manifests.get(&request.target).ok_or((
        BridgeErrorKind::UnknownTarget,
        format!("no bridge object named {}", request.target),
    ))?;

    let method = manifest.method(&request.method).ok_or_else(|| {
        (
            BridgeErrorKind::UnknownMethod,
            format!("{} has no method {}", request.target, request.method),
        )
    })?;

    if let Some(missing) = method
        .permissions
        .iter()
        .find(|permission| !granted.contains(permission))
    {
        return Err((
            BridgeErrorKind::PermissionDenied,
            format!("{} needs {missing}", method.name),
        ));
    }

    method
        .args
        .validate(&Value::Object(request.args), session_id)
}
