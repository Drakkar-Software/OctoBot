pub mod error;
mod service;

pub use error::{Result, ServiceError};
pub use service::{auto_level, service_label, LauncherService, ServiceLevel, ServiceStatus};
