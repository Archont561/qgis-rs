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
}

/// A manager operation and its handler strategy.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OperationDefinition {
    pub name: String,
    pub handler: String,
    pub requires_initialization: bool,
}

/// Parse and validate one manifest at the public generator seam.
pub fn validate_manifest(contents: &str) -> Result<ApiManifest> {
    let manifest: ApiManifest = serde_json::from_str(contents).context("parse API manifest JSON")?;
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
            bail!("declaration IDs must be non-empty and unique: {}", declaration.id);
        }
        if declaration.kind.is_empty() || declaration.module.is_empty() {
            bail!("declaration {} must include kind and module", declaration.id);
        }
        if !STATUSES.contains(&declaration.status.as_str()) {
            bail!(
                "declaration {} has unsupported status {:?}",
                declaration.id,
                declaration.status
            );
        }
        if declaration.since.is_empty() || declaration.version_range.is_empty() {
            bail!("declaration {} must include its version range", declaration.id);
        }
        if declaration.reason.trim().is_empty() {
            bail!("declaration {} must include a support reason", declaration.id);
        }
        if declaration.status.starts_with("supported")
            && (declaration.operation.as_deref().unwrap_or_default().is_empty()
                || declaration.handler.as_deref().unwrap_or_default().is_empty())
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
        if !operation_names.insert(&operation.name) {
            bail!("duplicate operation: {}", operation.name);
        }
    }
    if manifest.operations.is_empty() {
        bail!("API manifest must generate at least one operation");
    }

    let supported_operations: HashSet<&str> = manifest
        .declarations
        .iter()
        .filter(|declaration| declaration.status.starts_with("supported"))
        .filter_map(|declaration| declaration.operation.as_deref())
        .collect();
    for operation in &manifest.operations {
        if !supported_operations.contains(operation.name.as_str()) {
            bail!(
                "operation {} has no supported declaration in the manifest",
                operation.name
            );
        }
    }

    for exclusion in &manifest.exclusions {
        if !STATUSES.contains(&exclusion.status.as_str()) {
            bail!("exclusion {} has unsupported status {:?}", exclusion.scope, exclusion.status);
        }
        if exclusion.reason.trim().is_empty() {
            bail!("exclusion {} must include a reason", exclusion.scope);
        }
    }

    Ok(manifest)
}

/// Render the generated C++ operation registration fragment.
pub fn render_operation_table(manifest: &ApiManifest) -> Result<String> {
    let mut output = String::new();
    for operation in &manifest.operations {
        output.push_str(&format!(
            "QGIS_NATIVE_OPERATION(\"{}\", {}, {});\n",
            operation.name, operation.handler, operation.requires_initialization
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
        manifest.manifest_version,
        manifest.qgis.min_version,
        manifest.qgis.tested_version,
    )
}

/// Run the repository command against the checked-in manifest.
pub fn run(check: bool) -> Result<()> {
    let root = crate::util::repo_root();
    generate(
        &root.join("crates/qgis-sys/native_manager/generated/api_manifest.json"),
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
        return Ok(());
    }

    fs::create_dir_all(output_dir)
        .with_context(|| format!("create generated API directory {}", output_dir.display()))?;
    fs::write(&table_path, operation_table)
        .with_context(|| format!("write {}", table_path.display()))?;
    fs::write(&header_path, header)
        .with_context(|| format!("write {}", header_path.display()))?;
    println!("generated native-manager API fragments in {}", output_dir.display());
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
        && value
            .chars()
            .enumerate()
            .all(|(index, character)| {
                character == '_'
                    || character.is_ascii_lowercase()
                    || (index > 0 && character.is_ascii_digit())
            })
}

fn valid_cpp_identifier(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .enumerate()
            .all(|(index, character)| {
                character == '_'
                    || character.is_ascii_alphabetic()
                    || (index > 0 && character.is_ascii_digit())
            })
}
