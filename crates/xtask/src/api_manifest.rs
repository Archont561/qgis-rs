//! Validate the versioned native-manager API manifest and render its generated
//! C++ registry/header fragments.
//!
//! The checked-in JSON is the reviewable source of truth. This module does not
//! attempt to parse C++ with regular expressions: header extraction and QGIS
//! binding metadata are inputs to the manifest, while this command enforces
//! that every recorded declaration has an explicit support decision and that
//! the generated manager table is deterministic.

use std::{collections::HashSet, fs, path::Path};

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};

const STATUSES: &[&str] = &[
    "supported",
    "supported_manual",
    "partial",
    "unsupported",
    "host_only",
    "provider_optional",
    "deprecated",
];

/// The checked-in native-manager manifest.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApiManifest {
    /// Schema/version of this manifest format.
    pub manifest_version: u32,
    /// QGIS compatibility pin.
    pub qgis: QgisVersion,
    /// Header and semantic metadata inputs.
    #[serde(default)]
    pub source: SourceMetadata,
    /// Every declaration discovered or explicitly reviewed by the extractor.
    pub declarations: Vec<Declaration>,
    /// Explicit mappings for ownership, codecs, and boundary policies.
    pub mappings: Vec<Mapping>,
    /// Native-manager operations generated from the reviewed declarations.
    pub operations: Vec<OperationDefinition>,
    /// Explicitly excluded API surfaces.
    #[serde(default)]
    pub exclusions: Vec<Exclusion>,
}

/// QGIS version range represented by the manifest.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct QgisVersion {
    pub min_version: String,
    pub tested_version: String,
}

/// Provenance of the declarations in the manifest.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceMetadata {
    pub extractor: String,
    #[serde(default)]
    pub headers: Vec<String>,
    #[serde(default)]
    pub metadata: Vec<String>,
}

/// One normalized public declaration and its support decision.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Declaration {
    pub id: String,
    pub kind: String,
    pub module: String,
    pub status: String,
    pub since: String,
    pub version_range: String,
    pub reason: String,
    #[serde(default)]
    pub ownership: Option<String>,
    #[serde(default)]
    pub operation: Option<String>,
    #[serde(default)]
    pub handler: Option<String>,
}

/// One explicit policy for mapping a QGIS/Qt concept to the transport.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Mapping {
    pub category: String,
    pub qgis_type: String,
    pub wire_type: String,
    pub rule: String,
}

/// An explicitly excluded public API scope.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Exclusion {
    pub scope: String,
    pub status: String,
    pub reason: String,
    /// Wire operations the transport serves that this scope accounts for.
    ///
    /// An operation `qgis-protocol` spells but the native manager never
    /// handles — the pure-Rust engine's own operations — is recorded here
    /// rather than left to be inferred from its absence. That is what lets
    /// [`check_wire_operations`] treat the manifest as a *partition* of the
    /// served names instead of a subset of them, so dropping an operation
    /// cannot look the same as never having had one.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub operations: Vec<String>,
}

/// A manager operation, serialization codec, and handler strategy.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OperationDefinition {
    pub name: String,
    pub handler: String,
    pub codec: String,
    pub requires_initialization: bool,
}

/// Parse and validate one manifest at the public generator seam.
pub fn validate_manifest(contents: &str) -> Result<ApiManifest> {
    let manifest: ApiManifest =
        serde_json::from_str(contents).context("parse API manifest JSON")?;
    if manifest.manifest_version != 1 {
        bail!(
            "unsupported API manifest version {}; expected 1",
            manifest.manifest_version
        );
    }
    if manifest.qgis.min_version.is_empty() || manifest.qgis.tested_version.is_empty() {
        bail!("QGIS manifest version pin must include min_version and tested_version");
    }
    if manifest.source.extractor.is_empty() {
        bail!("API manifest source.extractor must not be empty");
    }
    if manifest.declarations.is_empty() {
        bail!("API manifest must record at least one declaration");
    }

    let mut declaration_ids = HashSet::new();
    for declaration in &manifest.declarations {
        if declaration.id.is_empty() || !declaration_ids.insert(&declaration.id) {
            bail!(
                "declaration IDs must be non-empty and unique: {}",
                declaration.id
            );
        }
        if declaration.kind.is_empty() || declaration.module.is_empty() {
            bail!(
                "declaration {} must include kind and module",
                declaration.id
            );
        }
        if !STATUSES.contains(&declaration.status.as_str()) {
            bail!(
                "declaration {} has unsupported status {:?}",
                declaration.id,
                declaration.status
            );
        }
        if declaration.since.is_empty() || declaration.version_range.is_empty() {
            bail!(
                "declaration {} must include its version range",
                declaration.id
            );
        }
        if declaration.reason.trim().is_empty() {
            bail!(
                "declaration {} must include a support reason",
                declaration.id
            );
        }
        if declaration.status.starts_with("supported")
            && (declaration
                .operation
                .as_deref()
                .unwrap_or_default()
                .is_empty()
                || declaration
                    .handler
                    .as_deref()
                    .unwrap_or_default()
                    .is_empty())
        {
            bail!(
                "supported declaration {} must identify an operation and handler",
                declaration.id
            );
        }
    }

    let required_mapping_categories = [
        "ownership",
        "invalidation",
        "overload",
        "enum",
        "variant",
        "binary_artifact",
        "paging",
    ];
    for category in required_mapping_categories {
        if !manifest.mappings.iter().any(|mapping| {
            mapping.category == category
                && !mapping.qgis_type.is_empty()
                && !mapping.wire_type.is_empty()
                && !mapping.rule.trim().is_empty()
        }) {
            bail!("API manifest is missing an explicit {category} mapping");
        }
    }

    let mut operation_names = HashSet::new();
    for operation in &manifest.operations {
        if !valid_wire_name(&operation.name) {
            bail!("invalid operation name {:?}", operation.name);
        }
        if !valid_cpp_identifier(&operation.handler) {
            bail!("invalid C++ handler name {:?}", operation.handler);
        }
        if !valid_cpp_identifier(&operation.codec) {
            bail!("invalid codec name {:?}", operation.codec);
        }
        if !operation_names.insert(&operation.name) {
            bail!("duplicate operation: {}", operation.name);
        }
    }
    if manifest.operations.is_empty() {
        bail!("API manifest must generate at least one operation");
    }

    let supported_declarations: Vec<&Declaration> = manifest
        .declarations
        .iter()
        .filter(|declaration| declaration.status.starts_with("supported"))
        .collect();
    for operation in &manifest.operations {
        let Some(declaration) = supported_declarations
            .iter()
            .find(|declaration| declaration.operation.as_deref() == Some(operation.name.as_str()))
        else {
            bail!(
                "operation {} has no supported declaration in the manifest",
                operation.name
            );
        };
        if declaration.handler.as_deref() != Some(operation.handler.as_str()) {
            bail!(
                "operation {} handler {} disagrees with declaration {} handler {:?}",
                operation.name,
                operation.handler,
                declaration.id,
                declaration.handler
            );
        }
    }
    for declaration in supported_declarations {
        if let Some(operation) = declaration.operation.as_deref() {
            if !manifest
                .operations
                .iter()
                .any(|candidate| candidate.name == operation)
            {
                bail!(
                    "supported declaration {} has no generated operation {}",
                    declaration.id,
                    operation
                );
            }
        }
    }

    let mut excluded_operations = HashSet::new();
    for exclusion in &manifest.exclusions {
        if !STATUSES.contains(&exclusion.status.as_str()) {
            bail!(
                "exclusion {} has unsupported status {:?}",
                exclusion.scope,
                exclusion.status
            );
        }
        if exclusion.reason.trim().is_empty() {
            bail!("exclusion {} must include a reason", exclusion.scope);
        }
        if exclusion.status.starts_with("supported") && !exclusion.operations.is_empty() {
            bail!(
                "exclusion {} claims operations but has supported status {:?}",
                exclusion.scope,
                exclusion.status
            );
        }
        for operation in &exclusion.operations {
            if !valid_wire_name(operation) {
                bail!(
                    "exclusion {} lists invalid operation name {:?}",
                    exclusion.scope,
                    operation
                );
            }
            if !excluded_operations.insert(operation) {
                bail!("operation {operation} is excluded twice");
            }
            if operation_names.contains(operation) {
                bail!(
                    "operation {operation} is both generated and excluded by {}",
                    exclusion.scope
                );
            }
        }
    }

    Ok(manifest)
}

/// Reject an upgrade that silently drops declarations, operations, or ownership
/// metadata. Additions and explicit status changes remain reviewable output.
pub fn check_upgrade(previous: &ApiManifest, current: &ApiManifest) -> Result<()> {
    if current.manifest_version < previous.manifest_version {
        bail!(
            "API manifest version regressed from {} to {}",
            previous.manifest_version,
            current.manifest_version
        );
    }
    for declaration in &previous.declarations {
        let Some(next) = current
            .declarations
            .iter()
            .find(|candidate| candidate.id == declaration.id)
        else {
            bail!("declaration dropped from API manifest: {}", declaration.id);
        };
        if next.ownership != declaration.ownership {
            bail!(
                "ownership changed for declaration {}: {:?} -> {:?}",
                declaration.id,
                declaration.ownership,
                next.ownership
            );
        }
    }
    for operation in &previous.operations {
        if !current
            .operations
            .iter()
            .any(|candidate| candidate.name == operation.name)
        {
            bail!("operation dropped from API manifest: {}", operation.name);
        }
    }
    Ok(())
}

/// Require the manifest to account for every wire operation the transport
/// serves, in both directions.
///
/// `qgis-protocol`'s [`Operation::all`] is the list a client discovers through
/// `engine_info`; this manifest is the list the native manager generates. Two
/// hand-maintained lists of the same `snake_case` spellings are exactly the
/// duplication the native-manager strategy rules out, so the manifest has to
/// *partition* the served names: each one is either a generated operation or
/// is named by an exclusion with a status and a reason. A name on one side
/// only — added, renamed, or dropped — is reported here rather than
/// discovered later by a client that asked for an operation nobody handles.
///
/// Every violation is collected before failing, because a rename shows up as
/// two of them and fixing one at a time would need two runs of the gate.
///
/// # Errors
///
/// Fails when a generated operation is not served, when a served operation is
/// neither generated nor excluded, or when an exclusion names an operation the
/// transport does not serve.
pub fn check_wire_operations(manifest: &ApiManifest, served: &[&str]) -> Result<()> {
    let served: HashSet<&str> = served.iter().copied().collect();
    let generated: HashSet<&str> = manifest
        .operations
        .iter()
        .map(|operation| operation.name.as_str())
        .collect();

    let mut found = Vec::new();
    for operation in &manifest.operations {
        if !served.contains(operation.name.as_str()) {
            found.push(format!(
                "operation `{}` is generated by the API manifest but is not an Operation variant \
                 in qgis-protocol",
                operation.name
            ));
        }
    }
    for exclusion in &manifest.exclusions {
        for operation in &exclusion.operations {
            if !served.contains(operation.as_str()) {
                found.push(format!(
                    "exclusion `{}` accounts for operation `{operation}`, which qgis-protocol does \
                     not serve",
                    exclusion.scope
                ));
            }
        }
    }
    let excluded: HashSet<&str> = manifest
        .exclusions
        .iter()
        .flat_map(|exclusion| exclusion.operations.iter().map(String::as_str))
        .collect();
    let mut unaccounted: Vec<&str> = served
        .iter()
        .copied()
        .filter(|name| !generated.contains(name) && !excluded.contains(name))
        .collect();
    unaccounted.sort_unstable();
    for name in unaccounted {
        found.push(format!(
            "operation `{name}` is served by qgis-protocol but the API manifest neither generates \
             nor excludes it"
        ));
    }

    if found.is_empty() {
        return Ok(());
    }
    bail!(
        "the API manifest and qgis-protocol disagree about the served operations:\n  - {}",
        found.join("\n  - ")
    );
}

/// One-line result printed after the wire spellings have been reconciled.
///
/// Public for `tests/api_manifest.rs`, for the same reason
/// [`check_summary`] is: a check whose success prints nothing is
/// indistinguishable from a check that never ran.
#[must_use]
pub fn wire_check_summary(manifest: &ApiManifest, served: usize) -> String {
    let excluded: usize = manifest
        .exclusions
        .iter()
        .map(|exclusion| exclusion.operations.len())
        .sum();
    format!(
        "check-api-operations: {} generated plus {excluded} excluded operations account for all \
         {served} wire spellings",
        manifest.operations.len(),
    )
}

/// Run the reconciliation against the checked-in manifest and the linked
/// `qgis-protocol`.
///
/// # Errors
///
/// Propagates a manifest that does not parse, and any disagreement
/// [`check_wire_operations`] reports.
pub fn run_wire_operations_check() -> Result<()> {
    let manifest_path =
        crate::util::repo_root().join("crates/qgis-sys/native_manager/generated/api_manifest.json");
    let manifest = validate_manifest(
        &fs::read_to_string(&manifest_path)
            .with_context(|| format!("read API manifest {}", manifest_path.display()))?,
    )?;
    let served = qgis_protocol::Operation::all();
    check_wire_operations(&manifest, served)?;
    println!("{}", wire_check_summary(&manifest, served.len()));
    Ok(())
}

/// Render the generated C++ operation registration fragment.
pub fn render_operation_table(manifest: &ApiManifest) -> Result<String> {
    let mut output = String::new();
    for operation in &manifest.operations {
        output.push_str(&format!(
            "QGIS_NATIVE_OPERATION(\"{}\", {}, \"{}\", {});\n",
            operation.name, operation.handler, operation.codec, operation.requires_initialization
        ));
    }
    Ok(output)
}

/// Render the generated C++ constants consumed by `engine_info`.
#[must_use]
pub fn render_generated_header(manifest: &ApiManifest) -> String {
    format!(
        concat!(
            "#pragma once\n\n",
            "#define QGIS_API_MANIFEST_VERSION {}\n",
            "#define QGIS_API_MANIFEST_QGIS_MIN_VERSION \"{}\"\n",
            "#define QGIS_API_MANIFEST_QGIS_TESTED_VERSION \"{}\"\n",
        ),
        manifest.manifest_version, manifest.qgis.min_version, manifest.qgis.tested_version,
    )
}

/// One-line result printed after generated fragments have been verified.
///
/// Public for `tests/api_manifest.rs`: a silent successful drift check is easy
/// to mistake for a check that never ran.
#[must_use]
pub fn check_summary(manifest: &ApiManifest, fragment_count: usize) -> String {
    format!(
        "api-manifest: {} operations match {} generated fragments",
        manifest.operations.len(),
        fragment_count
    )
}

/// Run the repository command against the checked-in manifest.
pub fn run(check: bool, diff_against: Option<&str>) -> Result<()> {
    let root = crate::util::repo_root();
    let manifest_path = root.join("crates/qgis-sys/native_manager/generated/api_manifest.json");
    if let Some(previous_path) = diff_against {
        let current = validate_manifest(
            &fs::read_to_string(&manifest_path)
                .with_context(|| format!("read API manifest {}", manifest_path.display()))?,
        )?;
        let previous_path = root.join(previous_path);
        let previous =
            validate_manifest(&fs::read_to_string(&previous_path).with_context(|| {
                format!("read prior API manifest {}", previous_path.display())
            })?)?;
        check_upgrade(&previous, &current)?;
        println!(
            "API manifest upgrade is compatible with {}",
            previous_path.display()
        );
    }
    generate(
        &manifest_path,
        &root.join("crates/qgis-sys/include/native_manager/generated"),
        check,
    )
}

/// Validate the manifest and write its generated fragments, or check that the
/// checked-in fragments are current when `check` is true.
pub fn generate(manifest_path: &Path, output_dir: &Path, check: bool) -> Result<()> {
    let contents = fs::read_to_string(manifest_path)
        .with_context(|| format!("read API manifest {}", manifest_path.display()))?;
    let manifest = validate_manifest(&contents)?;
    let operation_table = render_operation_table(&manifest)?;
    let header = render_generated_header(&manifest);
    let table_path = output_dir.join("operation_table.inc");
    let header_path = output_dir.join("api_manifest.h");

    if check {
        assert_generated(&table_path, &operation_table)?;
        assert_generated(&header_path, &header)?;
        println!("{}", check_summary(&manifest, 2));
        return Ok(());
    }

    fs::create_dir_all(output_dir)
        .with_context(|| format!("create generated API directory {}", output_dir.display()))?;
    fs::write(&table_path, operation_table)
        .with_context(|| format!("write {}", table_path.display()))?;
    fs::write(&header_path, header).with_context(|| format!("write {}", header_path.display()))?;
    println!(
        "generated native-manager API fragments in {}",
        output_dir.display()
    );
    Ok(())
}

fn assert_generated(path: &Path, expected: &str) -> Result<()> {
    let actual = fs::read_to_string(path)
        .with_context(|| format!("read generated fragment {}", path.display()))?;
    if actual != expected {
        bail!(
            "generated fragment is stale: {}; run `pixi run xtask api-manifest`",
            path.display()
        );
    }
    Ok(())
}

fn valid_wire_name(value: &str) -> bool {
    !value.is_empty()
        && value.chars().enumerate().all(|(index, character)| {
            character == '_'
                || character.is_ascii_lowercase()
                || (index > 0 && character.is_ascii_digit())
        })
}

fn valid_cpp_identifier(value: &str) -> bool {
    !value.is_empty()
        && value.chars().enumerate().all(|(index, character)| {
            character == '_'
                || character.is_ascii_alphabetic()
                || (index > 0 && character.is_ascii_digit())
        })
}
