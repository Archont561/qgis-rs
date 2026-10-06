//! Validate the shared Python/TypeScript bridge contract fixture tree.
//!
//! `cases.json` is the sole catalogue. This module checks its own schema and
//! every valid description/envelope it names; deliberately malformed request
//! vectors only need to exist and contain valid JSON because their invalidity
//! is the behavior under test in the language suites.

use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::path::Path;

use anyhow::{bail, Context, Result};
use serde::Deserialize;
use serde_json::Value;

const BRIDGE_VERSION: u64 = 1;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Catalogue {
    bridge_version: u64,
    doc: String,
    session_id: String,
    descriptions: Vec<DescriptionCase>,
    requests: Vec<RequestCase>,
    malformed: Vec<MalformedCase>,
    responses: Vec<ResponseCase>,
    events: Vec<EventCase>,
    error_kinds: Vec<String>,
    call_kinds: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct DescriptionCase {
    target: String,
    kind: String,
    file: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RequestCase {
    file: String,
    target: String,
    method: String,
    expect: String,
    response: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct MalformedCase {
    file: String,
    error_kind: String,
    why: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ResponseCase {
    file: String,
    ok: bool,
    request_id: String,
    #[serde(default)]
    error_kind: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EventCase {
    file: String,
    target: String,
    event: String,
    correlated: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Description {
    bridge_version: u64,
    namespace: String,
    kind: String,
    version: String,
    doc: String,
    methods: Vec<Method>,
    events: Vec<EventSpec>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Method {
    name: String,
    call_kind: String,
    permissions: Vec<String>,
    args: Schema,
    result: Schema,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EventSpec {
    name: String,
    payload: Schema,
}

#[derive(Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Schema {
    #[serde(default)]
    r#type: Option<String>,
    #[serde(default)]
    properties: BTreeMap<String, Schema>,
    #[serde(default)]
    required: Vec<String>,
    #[serde(default)]
    items: Option<Box<Schema>>,
    #[serde(default)]
    r#enum: Vec<Value>,
    #[serde(default)]
    additional_properties: Option<bool>,
    #[serde(default, rename = "$handle")]
    handle: Option<String>,
}

impl Schema {
    fn validate(&self, label: &str) -> Result<()> {
        if let Some(type_name) = &self.r#type {
            const TYPES: &[&str] = &["string", "boolean", "integer", "number", "object", "array"];
            if !TYPES.contains(&type_name.as_str()) {
                bail!("{label} has unknown schema type {type_name:?}");
            }
        }
        for required in &self.required {
            if !self.properties.contains_key(required) {
                bail!("{label} requires undeclared property {required:?}");
            }
        }
        for (name, property) in &self.properties {
            require_name(name, "schema property")?;
            property.validate(label)?;
        }
        if let Some(items) = &self.items {
            items.validate(label)?;
        }
        let _ = (&self.r#enum, self.additional_properties, &self.handle);
        Ok(())
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    bridge_version: u64,
    request_id: String,
    target: String,
    method: String,
    args: BTreeMap<String, Value>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Response {
    bridge_version: u64,
    request_id: String,
    ok: bool,
    #[serde(default)]
    result: Option<Value>,
    #[serde(default)]
    error: Option<BridgeError>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct BridgeError {
    kind: String,
    message: String,
    #[serde(default)]
    details: Option<Value>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Event {
    bridge_version: u64,
    #[serde(default)]
    request_id: Option<String>,
    target: String,
    event: String,
    payload: Value,
}

fn read<T: for<'de> Deserialize<'de>>(root: &Path, relative: &str) -> Result<T> {
    let path = root.join(relative);
    let text = fs::read_to_string(&path)
        .with_context(|| format!("cannot read bridge fixture {}", path.display()))?;
    serde_json::from_str(&text)
        .with_context(|| format!("invalid bridge fixture {}", path.display()))
}

fn read_value(root: &Path, relative: &str) -> Result<Value> {
    read(root, relative)
}

fn require_version(version: u64, file: &str) -> Result<()> {
    if version != BRIDGE_VERSION {
        bail!("{file} has incompatible bridge_version {version}; expected {BRIDGE_VERSION}");
    }
    Ok(())
}

fn require_name(name: &str, label: &str) -> Result<()> {
    let valid = !name.is_empty()
        && name.split('.').all(|part| {
            !part.is_empty()
                && part
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
        });
    if !valid {
        bail!("{label} must be a dotted snake_case wire name: {name:?}");
    }
    Ok(())
}

/// Validate the catalogue and every canonical fixture it names.
///
/// Returns a stable summary suitable for local and CI output.
///
/// # Errors
///
/// Fails when a listed file is absent or invalid JSON, when a canonical object
/// contains unknown fields, or when IDs, names, versions, and catalogue links
/// disagree.
pub fn validate_tree(root: &Path) -> Result<String> {
    let catalogue: Catalogue = read(root, "cases.json")?;
    require_version(catalogue.bridge_version, "cases.json")?;
    if catalogue.doc.trim().is_empty() || catalogue.session_id.trim().is_empty() {
        bail!("cases.json requires non-empty doc and session_id");
    }

    let call_kinds: HashSet<&str> = catalogue.call_kinds.iter().map(String::as_str).collect();
    let error_kinds: HashSet<&str> = catalogue.error_kinds.iter().map(String::as_str).collect();
    let mut methods = HashSet::new();
    let mut events = HashSet::new();
    let mut targets = HashSet::new();

    for case in &catalogue.descriptions {
        require_name(&case.target, "description target")?;
        let description: Description = read(root, &case.file)?;
        require_version(description.bridge_version, &case.file)?;
        if description.namespace != case.target || description.kind != case.kind {
            bail!("{} disagrees with its catalogue target or kind", case.file);
        }
        if !targets.insert(case.target.as_str()) {
            bail!("duplicate description target {}", case.target);
        }
        if !call_kinds.contains(case.kind.as_str()) {
            bail!("{} uses unknown call kind {}", case.file, case.kind);
        }
        if description.version.trim().is_empty() || description.doc.trim().is_empty() {
            bail!("{} requires non-empty version and doc", case.file);
        }
        for method in description.methods {
            require_name(&method.name, "method")?;
            if method.call_kind != case.kind || !call_kinds.contains(method.call_kind.as_str()) {
                bail!(
                    "{}.{} has an incompatible call_kind",
                    case.target,
                    method.name
                );
            }
            method
                .args
                .validate(&format!("{}.{} args", case.target, method.name))?;
            method
                .result
                .validate(&format!("{}.{} result", case.target, method.name))?;
            if !methods.insert((case.target.as_str(), method.name)) {
                bail!("{} lists a duplicate method", case.file);
            }
            let _ = method.permissions;
        }
        for event in description.events {
            require_name(&event.name, "event")?;
            event
                .payload
                .validate(&format!("{}.{} payload", case.target, event.name))?;
            if !events.insert((case.target.as_str(), event.name)) {
                bail!("{} lists a duplicate event", case.file);
            }
        }
    }

    for case in &catalogue.requests {
        let request: Request = read(root, &case.file)?;
        require_version(request.bridge_version, &case.file)?;
        require_name(&request.target, "request target")?;
        require_name(&request.method, "request method")?;
        if request.request_id.is_empty() {
            bail!("{} requires a non-empty request_id", case.file);
        }
        if request.target != case.target || request.method != case.method {
            bail!(
                "{} disagrees with its catalogue target or method",
                case.file
            );
        }
        if case.expect != "valid" {
            bail!(
                "{} has unsupported expectation {:?}",
                case.file,
                case.expect
            );
        }
        if !methods.contains(&(case.target.as_str(), case.method.clone())) {
            bail!("{} names a method absent from its description", case.file);
        }
        if let Some(response) = &case.response {
            let _: Value = read_value(root, response)?;
        }
        let _ = request.args;
    }

    for case in &catalogue.responses {
        let response: Response = read(root, &case.file)?;
        require_version(response.bridge_version, &case.file)?;
        if response.request_id.is_empty() || response.request_id != case.request_id {
            bail!("{} has a missing or mismatched request_id", case.file);
        }
        if response.ok != case.ok {
            bail!("{} disagrees with its catalogue ok value", case.file);
        }
        match (response.ok, response.result, response.error) {
            (true, Some(_), None) => {}
            (false, None, Some(error)) => {
                if error.message.trim().is_empty()
                    || !error_kinds.contains(error.kind.as_str())
                    || case.error_kind.as_deref() != Some(error.kind.as_str())
                {
                    bail!("{} has an invalid structured error", case.file);
                }
                let _ = error.details;
            }
            _ => bail!(
                "{} must contain exactly result or error according to ok",
                case.file
            ),
        }
    }

    for case in &catalogue.events {
        let event: Event = read(root, &case.file)?;
        require_version(event.bridge_version, &case.file)?;
        require_name(&event.target, "event target")?;
        require_name(&event.event, "event name")?;
        if event.target != case.target
            || event.event != case.event
            || event.request_id.is_some() != case.correlated
            || !events.contains(&(case.target.as_str(), case.event.clone()))
        {
            bail!("{} disagrees with its catalogue or description", case.file);
        }
        let _ = event.payload;
    }

    for case in &catalogue.malformed {
        let _: Value = read_value(root, &case.file)?;
        if !error_kinds.contains(case.error_kind.as_str()) || case.why.trim().is_empty() {
            bail!("{} has an unknown error kind or no reason", case.file);
        }
    }

    Ok(format!(
        "bridge-fixtures: {} descriptions, {} requests, {} responses, {} malformed cases, {} events",
        catalogue.descriptions.len(),
        catalogue.requests.len(),
        catalogue.responses.len(),
        catalogue.malformed.len(),
        catalogue.events.len()
    ))
}

/// Validate the repository's checked-in bridge fixture tree and print a summary.
pub fn run(root: &Path) -> Result<()> {
    println!("{}", validate_tree(root)?);
    Ok(())
}
