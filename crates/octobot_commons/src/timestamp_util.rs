use std::sync::LazyLock;

use chrono::{DateTime, FixedOffset, Local, NaiveDateTime, TimeZone, Utc};

/// The local timezone, computed once at startup (mirrors Python's
/// `LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo`).
pub static LOCAL_TIMEZONE: LazyLock<FixedOffset> = LazyLock::new(|| {
    let local_now = Local::now();
    *local_now.offset()
});

const DEFAULT_DISPLAY_FORMAT: &str = "%d/%m/%y %H:%M";
const DEFAULT_NOW_FORMAT: &str = "%Y-%m-%d %H:%M:%S";

/// Convert a Unix timestamp (seconds) to a human-readable string.
///
/// * `timestamp`      – seconds since epoch (may contain fractional part)
/// * `time_format`    – `strftime`-compatible format (default `"%d/%m/%y %H:%M"`)
/// * `local_timezone` – when `true`, renders in the machine's local offset
pub fn convert_timestamp_to_datetime(
    timestamp: f64,
    time_format: Option<&str>,
    local_timezone: bool,
) -> String {
    let fmt = time_format.unwrap_or(DEFAULT_DISPLAY_FORMAT);
    let secs = timestamp as i64;
    let nanos = ((timestamp - secs as f64) * 1_000_000_000.0) as u32;

    if local_timezone {
        let dt: DateTime<FixedOffset> = LOCAL_TIMEZONE
            .timestamp_opt(secs, nanos)
            .single()
            .expect("invalid timestamp");
        dt.format(fmt).to_string()
    } else {
        let dt: DateTime<Utc> = Utc
            .timestamp_opt(secs, nanos)
            .single()
            .expect("invalid timestamp");
        dt.format(fmt).to_string()
    }
}

/// Convert multiple timestamps to human-readable strings.
pub fn convert_timestamps_to_datetime(
    timestamps: &[f64],
    time_format: Option<&str>,
    local_timezone: bool,
) -> Vec<String> {
    timestamps
        .iter()
        .map(|&ts| convert_timestamp_to_datetime(ts, time_format, local_timezone))
        .collect()
}

/// Return `true` when the timestamp can be converted to a valid datetime.
///
/// Mirrors the Python version which returns `True` for `0.0` (falsy)
/// and catches `OSError`/`ValueError`/`OverflowError` for everything else.
pub fn is_valid_timestamp(timestamp: f64) -> bool {
    if timestamp == 0.0 {
        // Python: `if timestamp:` is falsy for 0 → skips the try block → returns True
        return true;
    }
    let secs = timestamp as i64;
    let nanos = ((timestamp - secs as f64).abs() * 1_000_000_000.0) as u32;
    Utc.timestamp_opt(secs, nanos).single().is_some()
}

/// Return the current time as a formatted string.
///
/// * `time_format`    – defaults to `"%Y-%m-%d %H:%M:%S"`
/// * `local_timezone` – defaults to `true` (matches Python default)
pub fn get_now_time(time_format: Option<&str>, local_timezone: bool) -> String {
    let fmt = time_format.unwrap_or(DEFAULT_NOW_FORMAT);
    if local_timezone {
        let now = Utc::now().with_timezone(&*LOCAL_TIMEZONE);
        now.format(fmt).to_string()
    } else {
        Utc::now().format(fmt).to_string()
    }
}

/// Parse a datetime string and return its Unix timestamp (seconds).
///
/// The string is interpreted with the given `date_time_format` and pinned to
/// either the local timezone or UTC (no implicit timezone inference from the
/// string itself – mirrors the Python behaviour of `.replace(tzinfo=...)`).
pub fn datetime_to_timestamp(
    date_time_str: &str,
    date_time_format: &str,
    local_timezone: bool,
) -> f64 {
    create_datetime_from_string(date_time_str, date_time_format, local_timezone).timestamp() as f64
}

/// Parse a datetime string into a timezone-aware `DateTime<FixedOffset>`.
///
/// The parsed naive datetime is pinned to `LOCAL_TIMEZONE` when
/// `local_timezone` is `true`, otherwise to UTC.
pub fn create_datetime_from_string(
    date_time_str: &str,
    date_time_format: &str,
    local_timezone: bool,
) -> DateTime<FixedOffset> {
    let naive = NaiveDateTime::parse_from_str(date_time_str, date_time_format)
        .expect("failed to parse datetime string");
    if local_timezone {
        LOCAL_TIMEZONE
            .from_local_datetime(&naive)
            .single()
            .expect("ambiguous or invalid local datetime")
    } else {
        Utc.from_utc_datetime(&naive).fixed_offset()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_timestamp_utc() {
        // 2023-01-15 12:30:00 UTC  →  1673785800
        let s = convert_timestamp_to_datetime(1_673_785_800.0, None, false);
        assert_eq!(s, "15/01/23 12:30");
    }

    #[test]
    fn test_convert_timestamps() {
        let v = convert_timestamps_to_datetime(&[0.0, 1_673_785_800.0], None, false);
        assert_eq!(v.len(), 2);
        assert_eq!(v[0], "01/01/70 00:00");
    }

    #[test]
    fn test_is_valid_timestamp() {
        assert!(is_valid_timestamp(0.0));
        assert!(is_valid_timestamp(1_673_785_800.0));
        // Extremely large values are invalid
        assert!(!is_valid_timestamp(f64::MAX));
    }

    #[test]
    fn test_roundtrip_utc() {
        let ts = datetime_to_timestamp("15/01/23 12:30", "%d/%m/%y %H:%M", false);
        assert!((ts - 1_673_785_800.0).abs() < 1.0);
    }
}
