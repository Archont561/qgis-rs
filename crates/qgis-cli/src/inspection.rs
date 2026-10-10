//! Read-only filesystem inspection; neither XML nor QGIS semantics are evaluated.
use crate::cli::InspectArgs;
use anyhow::Result;
use qgis_render::ProjectFormat;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

/// Inspection failures are scoped so legacy command exits remain unchanged.
#[derive(Debug)]
pub(crate) enum Failure {
    MissingInput(PathBuf),
    InvalidInput(String),
    Filesystem(String),
}

impl Failure {
    fn code(&self) -> &'static str {
        match self {
            Self::MissingInput(_) => "missing_input",
            Self::InvalidInput(_) => "invalid_input",
            Self::Filesystem(_) => "filesystem_failure",
        }
    }

    pub(crate) fn exit_code(&self) -> u8 {
        match self {
            Self::MissingInput(_) => 11,
            Self::InvalidInput(_) => 10,
            Self::Filesystem(_) => 14,
        }
    }
}

impl std::fmt::Display for Failure {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidInput(message) | Self::Filesystem(message) => formatter.write_str(message),
            Self::MissingInput(path) => {
                write!(formatter, "project file not found: {}", path.display())
            }
        }
    }
}

impl std::error::Error for Failure {}

pub(crate) fn run(args: InspectArgs) -> Result<()> {
    let result = metadata(&args.project);
    if args.json {
        let error = result.as_ref().err().map(|error| {
            json!({
                "code": error.code(),
                "message": error.to_string(),
            })
        });
        println!(
            "{}",
            json!({
                "inspection": "file_metadata",
                "qgis_validation": "not_performed",
                "value": result.as_ref().ok(),
                "error": error,
            })
        );
    } else if let Ok(value) = &result {
        println!("inspection: file_metadata");
        println!("path: {}", args.project.display());
        println!(
            "format: {} (extension-derived)",
            value["format"].as_str().unwrap_or_default()
        );
        println!("size: {} bytes", value["size_bytes"]);
        println!("contents: not read or validated");
        println!("qgis_validation: not_performed");
    }
    result.map(|_| ()).map_err(Into::into)
}

fn metadata(path: &Path) -> Result<Value, Failure> {
    let metadata = std::fs::metadata(path).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            Failure::MissingInput(path.to_path_buf())
        } else {
            Failure::Filesystem(format!(
                "cannot inspect filesystem metadata for {}: {error}",
                path.display()
            ))
        }
    })?;
    if !metadata.is_file() {
        return Err(Failure::InvalidInput(format!(
            "not a regular file: {}",
            path.display()
        )));
    }
    let format = path
        .extension()
        .and_then(|ext| ext.to_str())
        .and_then(ProjectFormat::from_extension)
        .ok_or_else(|| {
            Failure::InvalidInput(format!(
                "expected a .qgs or .qgz extension: {}",
                path.display()
            ))
        })?;
    let path = path
        .to_str()
        .ok_or_else(|| Failure::InvalidInput("project path must be valid UTF-8".to_string()))?;
    Ok(json!({"path": path, "format": format, "size_bytes": metadata.len()}))
}
