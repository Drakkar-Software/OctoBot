use thiserror::Error;

#[derive(Debug, Error)]
pub enum LauncherError {
    #[error("backend unavailable: {0}")]
    BackendUnavailable(String),
    #[error("instance not found: {0}")]
    InstanceNotFound(String),
    #[error("instance already running")]
    AlreadyRunning,
    #[error("instance not running")]
    NotRunning,
    #[error("operation timed out")]
    Timeout,
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("backend error: {0}")]
    Backend(String),
    #[error("config error: {0}")]
    Config(String),
    #[error("other error: {0}")]
    Other(#[from] anyhow::Error),
}

pub type Result<T> = std::result::Result<T, LauncherError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn variants_implement_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<LauncherError>();
    }

    #[test]
    fn io_error_conversion() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
        let launcher_err: LauncherError = io_err.into();
        assert!(matches!(launcher_err, LauncherError::Io(_)));
    }
}
