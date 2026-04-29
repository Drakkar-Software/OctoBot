use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("config load error: {0}")]
    Load(String),
    #[error("config validation error: {0}")]
    Validation(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialize error: {0}")]
    Serialize(String),
    #[error("deserialize error: {0}")]
    Deserialize(String),
}

pub type Result<T> = std::result::Result<T, ConfigError>;
