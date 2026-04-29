use thiserror::Error;

#[derive(Debug, Error)]
pub enum UpdateError {
    #[error("network error: {0}")]
    Network(String),
    #[error("bad signature")]
    BadSignature,
    #[error("missing signature")]
    MissingSignature,
    #[error("malformed signature")]
    MalformedSignature,
    #[error("sha256 mismatch")]
    Sha256Mismatch,
    #[error("no artifact for platform: {0}")]
    NoArtifactForPlatform(String),
    #[error("downgrade refused")]
    DowngradeRefused,
    #[error("update locked")]
    Locked,
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(String),
}

pub type Result<T> = std::result::Result<T, UpdateError>;
