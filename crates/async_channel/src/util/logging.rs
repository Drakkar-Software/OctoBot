/// Get a logger name for a given component.
/// In pure Rust, this returns the name for use with the `log` crate.
pub fn get_logger_name(name: &str) -> String {
    if name.is_empty() {
        "async_channel".to_string()
    } else {
        format!("async_channel::{}", name)
    }
}

/// Alias for `get_logger_name`. Returns a logger identifier string for the
/// given component name. Mirrors the Python `get_logger(name)` function.
pub fn get_logger(name: &str) -> String {
    get_logger_name(name)
}
