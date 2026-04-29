pub mod error;
mod service;

pub use error::{Result, ServiceError};
pub use service::{
    auto_level, service_label, ENV_FOREGROUND, LauncherService, ServiceLevel, ServiceStatus,
};
