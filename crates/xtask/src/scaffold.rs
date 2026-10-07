//! Add one reviewable operation to the native-manager API manifest.
//!
//! D12 replaced the per-concept CXX bridge tree with one native manager and a
//! generated operation registry. Scaffolding therefore changes only the JSON
//! source of truth; `api-manifest` owns its generated C++ fragments.
//!
//! Usage: `pixi run xtask scaffold project_save project_save`

use std::fs;
use std::path::Path;

use anyhow::{bail, Context, Result};

use crate::api_manifest::{validate_manifest, Declaration, OperationDefinition};

/// Add a supported native-manager operation and its review declaration.
///
/// Public for `tests/scaffold.rs`, which exercises the generator against an
/// isolated manifest instead of modifying the repository.
pub fn operation(manifest_path: &Path, name: &str, handler: &str) -> Result<()> {
    let contents = fs::read_to_string(manifest_path)
        .with_context(|| format!("read API manifest {}", manifest_path.display()))?;
    let mut manifest = validate_manifest(&contents)?;
    if manifest
        .operations
        .iter()
        .any(|operation| operation.name == name)
    {
        bail!("API-manifest operation already exists: {name}");
    }

    manifest.declarations.push(Declaration {
        id: format!("NativeManager::{name}"),
        kind: "operation".to_string(),
        module: "native_manager".to_string(),
        status: "supported_manual".to_string(),
        since: manifest.qgis.min_version.clone(),
        version_range: format!(">={},<4", manifest.qgis.min_version),
        reason: "Scaffolded native-manager operation; review semantics before implementation."
            .to_string(),
        ownership: None,
        operation: Some(name.to_string()),
        handler: Some(handler.to_string()),
    });
    manifest.operations.push(OperationDefinition {
        name: name.to_string(),
        handler: handler.to_string(),
        codec: "json_object".to_string(),
        requires_initialization: true,
    });

    // Validate the complete result before replacing the source of truth.
    let mut updated = serde_json::to_string_pretty(&manifest).context("serialize API manifest")?;
    updated.push('\n');
    validate_manifest(&updated)?;
    fs::write(manifest_path, updated)
        .with_context(|| format!("write API manifest {}", manifest_path.display()))?;
    Ok(())
}

/// Scaffold an operation in the repository manifest and regenerate fragments.
pub fn repository_operation(name: &str, handler: &str) -> Result<()> {
    let root = crate::util::repo_root();
    let manifest = root.join(crate::api_manifest::MANIFEST_PATH);
    operation(&manifest, name, handler)?;
    crate::api_manifest::run(false, None)?;
    println!(
        "scaffold: added native-manager operation {name} with handler {handler}; review its declaration, implement the handler, and add the matching `Operation` variant to qgis-protocol — `xtask check-api-operations` fails until both sides spell it, and `check-api-manifest` fails until the pinned baseline is promoted with `cp {} {}`",
        crate::api_manifest::MANIFEST_PATH,
        crate::api_manifest::BASELINE_PATH
    );
    Ok(())
}
