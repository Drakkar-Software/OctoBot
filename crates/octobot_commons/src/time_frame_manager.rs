use std::sync::LazyLock;

use crate::constants::MINUTE_TO_SECONDS;
use crate::enums::{time_frames_minutes, TimeFrames};

/// All `TimeFrames` variants sorted from shortest to longest (by minutes).
///
/// Equivalent to the Python module-level `TimeFramesRank`.
pub static TIME_FRAMES_RANK: LazyLock<Vec<TimeFrames>> = LazyLock::new(|| {
    let mut v = TimeFrames::variants().to_vec();
    v.sort_by_key(|tf| time_frames_minutes(*tf));
    v
});

/// Sort a slice of time frames from shortest to longest (by minutes).
///
/// When `reverse` is `true` the order is longest-first.
pub fn sort_time_frames(time_frames: &[TimeFrames], reverse: bool) -> Vec<TimeFrames> {
    let mut v = time_frames.to_vec();
    v.sort_by_key(|tf| time_frames_minutes(*tf));
    if reverse {
        v.reverse();
    }
    v
}

/// Find the minimum time frame that appears in `time_frames` and is at least
/// as large as `min_time_frame` (if supplied).
///
/// Returns `None` only when `time_frames` is empty **and** no `min_time_frame`
/// fallback was given.  Otherwise the semantics match the Python version:
///
/// * Empty `time_frames` → first element of `TIME_FRAMES_RANK`.
/// * `min_time_frame` provided → skip all ranked frames below it.
/// * No match → return `min_time_frame` itself.
pub fn find_min_time_frame(
    time_frames: &[TimeFrames],
    min_time_frame: Option<TimeFrames>,
) -> Option<TimeFrames> {
    if time_frames.is_empty() {
        // If exchange has no time frame list, return the smallest known frame
        // (same as Python: `return TimeFramesRank[0]`).
        return Some(TIME_FRAMES_RANK[0]);
    }

    // Build a set of string values for fast lookup (mirrors
    // `time_frame_list = [t.value for t in time_frames]` then `tf_val in time_frame_list`).
    let tf_values: Vec<&str> = time_frames.iter().map(|tf| tf.value()).collect();

    let min_index = min_time_frame
        .and_then(|mtf| TIME_FRAMES_RANK.iter().position(|&r| r == mtf))
        .unwrap_or(0);

    for (index, &ranked_tf) in TIME_FRAMES_RANK.iter().enumerate() {
        if index >= min_index && tf_values.contains(&ranked_tf.value()) {
            return Some(ranked_tf);
        }
    }

    // Fallback – return the min_time_frame itself (Python: `return min_time_frame`).
    min_time_frame
}

/// Walk backwards through `TIME_FRAMES_RANK` from `time_frame` until a frame
/// present in `time_frames` is found.  If none is found, return `origin`.
pub fn get_previous_time_frame(
    time_frames: &[TimeFrames],
    time_frame: TimeFrames,
    origin: TimeFrames,
) -> TimeFrames {
    get_previous_time_frame_inner(time_frames, time_frame, origin)
}

fn get_previous_time_frame_inner(
    time_frames: &[TimeFrames],
    time_frame: TimeFrames,
    origin: TimeFrames,
) -> TimeFrames {
    let current_index = TIME_FRAMES_RANK
        .iter()
        .position(|&tf| tf == time_frame)
        .expect("time_frame not found in TIME_FRAMES_RANK");

    if current_index > 0 {
        let previous = TIME_FRAMES_RANK[current_index - 1];
        if time_frames.contains(&previous) {
            return previous;
        }
        return get_previous_time_frame_inner(time_frames, previous, origin);
    }

    // Reached the beginning of the rank.
    if time_frames.contains(&time_frame) {
        time_frame
    } else {
        origin
    }
}

/// Parse a list of time-frame strings into `(valid, invalid)` vectors.
///
/// Unlike the Python version this does **not** log; the caller can decide what
/// to do with the `invalid` entries.
pub fn parse_time_frames(time_frame_strings: &[&str]) -> (Vec<TimeFrames>, Vec<String>) {
    let mut valid = Vec::new();
    let mut invalid = Vec::new();

    for &s in time_frame_strings {
        match TimeFrames::from_value(s) {
            Some(tf) => valid.push(tf),
            None => invalid.push(s.to_owned()),
        }
    }

    (valid, invalid)
}

/// Return `true` when the string corresponds to a known `TimeFrames` variant.
pub fn is_time_frame(time_frame_str: &str) -> bool {
    TimeFrames::from_value(time_frame_str).is_some()
}

/// Return the exact timestamp of the last completed `time_frame` tick
/// relative to `base_timestamp`.
///
/// ```text
/// tf_seconds = minutes(time_frame) * MINUTE_TO_SECONDS
/// result     = base_timestamp - (base_timestamp % tf_seconds)
/// ```
pub fn get_last_timeframe_time(time_frame: TimeFrames, base_timestamp: f64) -> f64 {
    let tf_seconds = time_frames_minutes(time_frame) as f64 * MINUTE_TO_SECONDS as f64;
    base_timestamp - (base_timestamp % tf_seconds)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_time_frames_rank_order() {
        let rank = &*TIME_FRAMES_RANK;
        for pair in rank.windows(2) {
            assert!(
                time_frames_minutes(pair[0]) <= time_frames_minutes(pair[1]),
                "{:?} should come before {:?}",
                pair[0],
                pair[1]
            );
        }
    }

    #[test]
    fn test_sort_time_frames() {
        let input = [TimeFrames::OneDay, TimeFrames::OneMinute, TimeFrames::OneHour];
        let sorted = sort_time_frames(&input, false);
        assert_eq!(sorted, vec![TimeFrames::OneMinute, TimeFrames::OneHour, TimeFrames::OneDay]);

        let rev = sort_time_frames(&input, true);
        assert_eq!(rev, vec![TimeFrames::OneDay, TimeFrames::OneHour, TimeFrames::OneMinute]);
    }

    #[test]
    fn test_find_min_time_frame_empty() {
        let result = find_min_time_frame(&[], None);
        assert_eq!(result, Some(TIME_FRAMES_RANK[0]));
    }

    #[test]
    fn test_find_min_time_frame_basic() {
        let frames = [TimeFrames::OneHour, TimeFrames::OneDay];
        let result = find_min_time_frame(&frames, None);
        assert_eq!(result, Some(TimeFrames::OneHour));
    }

    #[test]
    fn test_find_min_time_frame_with_floor() {
        let frames = [TimeFrames::OneMinute, TimeFrames::OneHour, TimeFrames::OneDay];
        let result = find_min_time_frame(&frames, Some(TimeFrames::OneHour));
        assert_eq!(result, Some(TimeFrames::OneHour));
    }

    #[test]
    fn test_get_previous_time_frame() {
        let config = [TimeFrames::OneMinute, TimeFrames::FiveMinutes, TimeFrames::OneHour];
        let prev = get_previous_time_frame(&config, TimeFrames::OneHour, TimeFrames::OneMinute);
        assert_eq!(prev, TimeFrames::FiveMinutes);
    }

    #[test]
    fn test_get_previous_time_frame_skips_gaps() {
        // FifteenMinutes is not in config, so it should skip past it.
        let config = [TimeFrames::FiveMinutes, TimeFrames::OneHour];
        let prev = get_previous_time_frame(&config, TimeFrames::OneHour, TimeFrames::FiveMinutes);
        assert_eq!(prev, TimeFrames::FiveMinutes);
    }

    #[test]
    fn test_parse_time_frames() {
        let (valid, invalid) = parse_time_frames(&["1m", "5m", "bogus", "1d"]);
        assert_eq!(valid, vec![TimeFrames::OneMinute, TimeFrames::FiveMinutes, TimeFrames::OneDay]);
        assert_eq!(invalid, vec!["bogus".to_owned()]);
    }

    #[test]
    fn test_is_time_frame() {
        assert!(is_time_frame("1h"));
        assert!(!is_time_frame("2x"));
    }

    #[test]
    fn test_get_last_timeframe_time() {
        // 1h = 3600s.  base = 7300.0 → 7300 - (7300 % 3600) = 7300 - 100 = 7200
        let result = get_last_timeframe_time(TimeFrames::OneHour, 7300.0);
        assert!((result - 7200.0).abs() < f64::EPSILON);
    }
}
