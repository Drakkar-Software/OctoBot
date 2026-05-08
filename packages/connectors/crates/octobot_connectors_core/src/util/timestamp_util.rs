// Timestamp utilities.
// Mirrors octobot_commons.timestamp_util and the timestamp uniformisation
// logic in CCXTAdapter.get_uniformized_timestamp.

/// OctoBot uses second-precision timestamps internally.
/// Exchange APIs return millisecond timestamps (>= 1e12).
/// This function converts ms → s when necessary.
pub fn uniformize_timestamp(ts: i64) -> i64 {
    if is_ms_timestamp(ts) {
        ts / 1000
    } else {
        ts
    }
}

/// Returns true if the timestamp is in milliseconds (>= 10^12).
pub fn is_ms_timestamp(ts: i64) -> bool {
    ts >= 1_000_000_000_000
}

/// Returns true if the timestamp is in seconds (< 10^12 and > 0).
pub fn is_valid_timestamp(ts: i64) -> bool {
    ts > 0 && ts < 10_000_000_000_000
}

/// Returns the current Unix timestamp in seconds.
pub fn current_timestamp() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// Returns the current Unix timestamp in milliseconds.
pub fn current_timestamp_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_uniformize_ms() {
        // 1700000000000 ms → 1700000000 s
        assert_eq!(uniformize_timestamp(1_700_000_000_000), 1_700_000_000);
    }

    #[test]
    fn test_uniformize_seconds_unchanged() {
        assert_eq!(uniformize_timestamp(1_700_000_000), 1_700_000_000);
    }

    #[test]
    fn test_is_ms_timestamp() {
        assert!(is_ms_timestamp(1_700_000_000_000));
        assert!(!is_ms_timestamp(1_700_000_000));
    }
}
