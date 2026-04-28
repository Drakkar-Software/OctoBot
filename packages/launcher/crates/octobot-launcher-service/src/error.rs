use thiserror::Error;

#[derive(Debug, Error)]
pub enum ServiceError {
    #[error("service manager error: {0}")]
    Manager(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("not supported on this platform")]
    Unsupported,
}

pub type Result<T> = std::result::Result<T, ServiceError>;
