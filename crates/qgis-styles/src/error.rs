//! Error types for style IR.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("invalid color {value:?}: expected #RRGGBB, #RRGGBBAA, or rgba()")]
    InvalidColor { value: String },

    #[error("invalid renderer {kind:?}: {reason}")]
    InvalidRenderer { kind: String, reason: String },

    #[error("invalid style: {reason}")]
    InvalidStyle { reason: String },

    #[error("JSON error: {source}")]
    Json {
        #[from]
        source: serde_json::Error,
    },

    #[error("I/O error: {source}")]
    Io {
        #[from]
        source: std::io::Error,
    },
}

pub type Result<T, E = Error> = std::result::Result<T, E>;
