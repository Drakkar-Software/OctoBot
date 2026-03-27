//! External integration tests for `octobot_commons::time_frame_manager`.
//!
//! Mirrors the pure-logic tests from the Python
//! `test_time_frame_manager.py`, plus Rust-only tests for `is_time_frame`,
//! `get_last_timeframe_time`, and `TIME_FRAMES_RANK` ordering.

use octobot_commons::enums::{time_frames_minutes, TimeFrames};
use octobot_commons::time_frame_manager::*;

// ---------------------------------------------------------------------------
// Python-mirrored tests
// ---------------------------------------------------------------------------

/// Python: test_parse_time_frames
/// parse_time_frames(["3d", "5d", "1m", "6h"]) == [ThreeDays, OneMinute, SixHours]
/// "5d" is not a valid TimeFrames variant, so it lands in the invalid list.
#[test]
fn test_parse_time_frames() {
    let (valid, invalid) = parse_time_frames(&["3d", "5d", "1m", "6h"]);
    assert_eq!(
        valid,
        vec![TimeFrames::ThreeDays, TimeFrames::OneMinute, TimeFrames::SixHours],
    );
    assert_eq!(invalid, vec!["5d".to_string()]);
}

/// Python: test_sort_time_frames (first assertion)
/// sort([3d, 1m, 6h]) == [1m, 6h, 3d]
#[test]
fn test_sort_time_frames_basic() {
    let input = [TimeFrames::ThreeDays, TimeFrames::OneMinute, TimeFrames::SixHours];
    let sorted = sort_time_frames(&input, false);
    assert_eq!(
        sorted,
        vec![TimeFrames::OneMinute, TimeFrames::SixHours, TimeFrames::ThreeDays],
    );
}

/// Python: test_sort_time_frames (second assertion)
/// sort([1M, 3d, 12h, 1h, 1m, 6h]) == [1m, 1h, 6h, 12h, 3d, 1M]
#[test]
fn test_sort_time_frames_full() {
    let input = [
        TimeFrames::OneMonth,
        TimeFrames::ThreeDays,
        TimeFrames::TwelveHours,
        TimeFrames::OneHour,
        TimeFrames::OneMinute,
        TimeFrames::SixHours,
    ];
    let sorted = sort_time_frames(&input, false);
    assert_eq!(
        sorted,
        vec![
            TimeFrames::OneMinute,
            TimeFrames::OneHour,
            TimeFrames::SixHours,
            TimeFrames::TwelveHours,
            TimeFrames::ThreeDays,
            TimeFrames::OneMonth,
        ],
    );
}

/// Python: test_find_min_time_frame
/// find_min([4h, 1d, 1M, 15m]) == 15m
/// find_min([1M, 1w])           == 1w
/// find_min([1m])               == 1m
#[test]
fn test_find_min_time_frame() {
    assert_eq!(
        find_min_time_frame(
            &[
                TimeFrames::FourHours,
                TimeFrames::OneDay,
                TimeFrames::OneMonth,
                TimeFrames::FifteenMinutes,
            ],
            None,
        ),
        Some(TimeFrames::FifteenMinutes),
    );
    assert_eq!(
        find_min_time_frame(&[TimeFrames::OneMonth, TimeFrames::OneWeek], None),
        Some(TimeFrames::OneWeek),
    );
    assert_eq!(
        find_min_time_frame(&[TimeFrames::OneMinute], None),
        Some(TimeFrames::OneMinute),
    );
}

/// Python: test_get_previous_time_frame
/// config = [1h, 4h, 1d]
///
/// get_previous(config, 1d, 1d) == 4h   (walks back from 1d, finds 4h in config)
/// get_previous(config, 1m, 1m) == 1m   (1m not in config; walks to start, returns origin)
/// get_previous(config, 1h, 1h) == 1h   (1h is at index 0 in config; returns itself)
/// get_previous(config, 1M, 1M) == 1d   (walks back from 1M, finds 1d in config)
#[test]
fn test_get_previous_time_frame() {
    let config = [TimeFrames::OneHour, TimeFrames::FourHours, TimeFrames::OneDay];

    assert_eq!(
        get_previous_time_frame(&config, TimeFrames::OneDay, TimeFrames::OneDay),
        TimeFrames::FourHours,
    );
    assert_eq!(
        get_previous_time_frame(&config, TimeFrames::OneMinute, TimeFrames::OneMinute),
        TimeFrames::OneMinute,
    );
    assert_eq!(
        get_previous_time_frame(&config, TimeFrames::OneHour, TimeFrames::OneHour),
        TimeFrames::OneHour,
    );
    assert_eq!(
        get_previous_time_frame(&config, TimeFrames::OneMonth, TimeFrames::OneMonth),
        TimeFrames::OneDay,
    );
}

// ---------------------------------------------------------------------------
// Rust-only tests
// ---------------------------------------------------------------------------

/// Verify `is_time_frame` returns true for every known variant string value
/// and false for invalid strings.
#[test]
fn test_is_time_frame() {
    // Valid variant strings.
    assert!(is_time_frame("1m"));
    assert!(is_time_frame("3m"));
    assert!(is_time_frame("5m"));
    assert!(is_time_frame("15m"));
    assert!(is_time_frame("30m"));
    assert!(is_time_frame("1h"));
    assert!(is_time_frame("2h"));
    assert!(is_time_frame("3h"));
    assert!(is_time_frame("4h"));
    assert!(is_time_frame("6h"));
    assert!(is_time_frame("8h"));
    assert!(is_time_frame("12h"));
    assert!(is_time_frame("1d"));
    assert!(is_time_frame("3d"));
    assert!(is_time_frame("1w"));
    assert!(is_time_frame("1M"));
    assert!(is_time_frame("1y"));

    // Invalid strings.
    assert!(!is_time_frame("5d"));
    assert!(!is_time_frame(""));
    assert!(!is_time_frame("2d"));
    assert!(!is_time_frame("abc"));
    assert!(!is_time_frame("1H")); // case-sensitive: "1H" is not "1h"
}

/// Verify `get_last_timeframe_time` aligns a timestamp to the start of its
/// enclosing time-frame window.
#[test]
fn test_get_last_timeframe_time() {
    // OneHour = 60 minutes = 3600 seconds.
    // A timestamp partway through an hour should snap back to the hour start.
    let base = 1_700_000_123.0; // arbitrary timestamp
    let result = get_last_timeframe_time(TimeFrames::OneHour, base);
    let tf_seconds = 60.0 * 60.0; // 3600
    let expected = base - (base % tf_seconds);
    assert!(
        (result - expected).abs() < f64::EPSILON,
        "OneHour: expected {expected}, got {result}",
    );

    // OneDay = 1440 minutes = 86400 seconds.
    let result_day = get_last_timeframe_time(TimeFrames::OneDay, base);
    let tf_seconds_day = 1440.0 * 60.0;
    let expected_day = base - (base % tf_seconds_day);
    assert!(
        (result_day - expected_day).abs() < f64::EPSILON,
        "OneDay: expected {expected_day}, got {result_day}",
    );

    // OneMinute = 1 minute = 60 seconds.
    let result_min = get_last_timeframe_time(TimeFrames::OneMinute, base);
    let tf_seconds_min = 60.0;
    let expected_min = base - (base % tf_seconds_min);
    assert!(
        (result_min - expected_min).abs() < f64::EPSILON,
        "OneMinute: expected {expected_min}, got {result_min}",
    );

    // Exact alignment: if the timestamp is already aligned, result == base.
    let aligned = 1_699_999_200.0; // 1700000000 - 800 => divisible by 3600
    assert!(
        (get_last_timeframe_time(TimeFrames::OneHour, aligned) - aligned).abs() < f64::EPSILON,
        "An aligned timestamp should be returned unchanged",
    );
}

/// Verify that `TIME_FRAMES_RANK` is sorted from shortest to longest.
#[test]
fn test_time_frames_rank_ordering() {
    let rank = &*TIME_FRAMES_RANK;
    assert!(!rank.is_empty(), "TIME_FRAMES_RANK should not be empty");

    for pair in rank.windows(2) {
        assert!(
            time_frames_minutes(pair[0]) <= time_frames_minutes(pair[1]),
            "TIME_FRAMES_RANK is not sorted: {:?} ({} min) should come before {:?} ({} min)",
            pair[0],
            time_frames_minutes(pair[0]),
            pair[1],
            time_frames_minutes(pair[1]),
        );
    }
}

/// Verify that `TIME_FRAMES_RANK` contains all `TimeFrames` variants.
#[test]
fn test_time_frames_rank_completeness() {
    let rank = &*TIME_FRAMES_RANK;
    for variant in TimeFrames::variants() {
        assert!(
            rank.contains(variant),
            "TIME_FRAMES_RANK is missing variant {:?}",
            variant,
        );
    }
    assert_eq!(
        rank.len(),
        TimeFrames::variants().len(),
        "TIME_FRAMES_RANK length should match the number of TimeFrames variants",
    );
}

/// `sort_time_frames` with `reverse = true` should produce longest-first order.
#[test]
fn test_sort_time_frames_reverse() {
    let input = [
        TimeFrames::OneMinute,
        TimeFrames::OneDay,
        TimeFrames::SixHours,
    ];
    let sorted = sort_time_frames(&input, true);
    assert_eq!(
        sorted,
        vec![TimeFrames::OneDay, TimeFrames::SixHours, TimeFrames::OneMinute],
    );
}
