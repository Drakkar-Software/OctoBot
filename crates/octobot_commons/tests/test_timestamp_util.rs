use std::time::{SystemTime, UNIX_EPOCH};

use octobot_commons::timestamp_util::*;

// -- is_valid_timestamp -------------------------------------------------------

#[test]
fn test_is_valid_timestamp_with_current_time() {
    // In Python the test calls `is_valid_timestamp(get_now_time())`, but
    // get_now_time() returns a String in both Python and Rust. In Rust we
    // can't pass a String where f64 is expected, so instead we verify that a
    // real "current" timestamp is valid.
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64();
    assert!(is_valid_timestamp(now));
}

#[test]
fn test_is_valid_timestamp_with_known_value() {
    assert!(is_valid_timestamp(1_577_836_800.0));
}

#[test]
fn test_is_valid_timestamp_zero() {
    // Python: 0.0 is falsy so the try block is skipped -> returns True.
    assert!(is_valid_timestamp(0.0));
}

#[test]
fn test_is_valid_timestamp_max_is_invalid() {
    assert!(!is_valid_timestamp(f64::MAX));
}

// -- datetime_to_timestamp (round-trip) ---------------------------------------

#[test]
fn test_datetime_to_timestamp() {
    // Mirror the Python test: format a known UTC timestamp with local_timezone,
    // then parse it back. We use UTC (local_timezone=false) for determinism.
    let date_str = convert_timestamp_to_datetime(
        1_737_331_200.0,
        Some("%d/%m/%y %H:%M"),
        false, // UTC – we cannot mock LOCAL_TIMEZONE in Rust
    );
    let roundtripped = datetime_to_timestamp(&date_str, "%d/%m/%y %H:%M", false);
    assert_eq!(roundtripped, 1_737_331_200.0);
}

// -- convert_timestamp_to_datetime -------------------------------------------

#[test]
fn test_convert_timestamp_to_datetime_default() {
    let ts: f64 = 1_577_836_800.0; // 1 Jan 2020 00:00 UTC
    assert_eq!(
        convert_timestamp_to_datetime(ts, None, false),
        "01/01/20 00:00"
    );
}

#[test]
fn test_convert_timestamp_to_datetime_custom_format() {
    let ts: f64 = 1_577_836_800.0;
    assert_eq!(
        convert_timestamp_to_datetime(ts, Some("%Y-%m-%d"), false),
        "2020-01-01"
    );
}

#[test]
fn test_convert_timestamp_to_datetime_utc_instead_of_local() {
    // We cannot mock LOCAL_TIMEZONE (LazyLock) in Rust, so we verify the UTC
    // path produces the expected result instead of the local-timezone test.
    let ts: f64 = 1_577_836_800.0; // 1 Jan 2020 00:00 UTC
    assert_eq!(
        convert_timestamp_to_datetime(ts, None, false),
        "01/01/20 00:00"
    );
}

#[test]
fn test_convert_timestamp_to_datetime_epoch() {
    assert_eq!(
        convert_timestamp_to_datetime(0.0, None, false),
        "01/01/70 00:00"
    );
}

#[test]
fn test_convert_timestamp_to_datetime_far_future() {
    let ts: f64 = 32_503_680_000.0; // year 3000
    assert_eq!(
        convert_timestamp_to_datetime(ts, Some("%Y"), false),
        "3000"
    );
}

#[test]
fn test_convert_timestamp_to_datetime_negative() {
    // Python test: `assert isinstance(result, str)`.
    // chrono handles -1 (one second before epoch) without panicking,
    // so we verify the result is a non-empty string, mirroring the Python
    // assertion that the return type is str.
    let result = convert_timestamp_to_datetime(-1.0, None, false);
    assert!(!result.is_empty());
}

// -- convert_timestamps_to_datetime ------------------------------------------

#[test]
fn test_convert_timestamps_to_datetime() {
    let timestamps = vec![0.0, 1_577_836_800.0];
    let results = convert_timestamps_to_datetime(&timestamps, None, false);
    assert_eq!(results.len(), 2);
    assert_eq!(results[0], "01/01/70 00:00");
    assert_eq!(results[1], "01/01/20 00:00");
}

// -- get_now_time -------------------------------------------------------------

#[test]
fn test_get_now_time_returns_non_empty_string() {
    let now = get_now_time(None, false);
    assert!(!now.is_empty());
}

#[test]
fn test_get_now_time_custom_format() {
    let now = get_now_time(Some("%Y"), false);
    // The year should be a 4-digit number.
    assert_eq!(now.len(), 4);
    assert!(now.parse::<u32>().is_ok());
}

// -- create_datetime_from_string ---------------------------------------------

#[test]
fn test_create_datetime_from_string_utc() {
    let dt = create_datetime_from_string("01/01/20 00:00", "%d/%m/%y %H:%M", false);
    assert_eq!(dt.timestamp(), 1_577_836_800);
}
