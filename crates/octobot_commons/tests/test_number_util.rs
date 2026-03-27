#![allow(clippy::excessive_precision)]
use octobot_commons::number_util::*;

#[test]
fn test_round_into_str_with_max_digits() {
    assert_eq!(
        round_into_str_with_max_digits(125.0256, 2),
        "125.03"
    );
}

#[test]
fn test_round_into_float_with_max_digits() {
    assert_eq!(round_into_float_with_max_digits(125.0210, 2), 125.02);
    assert_eq!(round_into_float_with_max_digits(1301.0, 5), 1301.00000);
    assert_eq!(round_into_float_with_max_digits(59866.0, 0), 59866.0);
    assert_eq!(
        round_into_float_with_max_digits(1.567824117582484154178, 15),
        1.567824117582484
    );
    assert_eq!(
        round_into_float_with_max_digits(0.000000059, 8),
        0.00000006
    );
}

#[test]
fn test_round_into_float_with_max_digits_large_integer_part() {
    // All of these f64 literals (8712661000.1273185, 8712661000.12731851, etc.)
    // represent the same f64 bit pattern, so a single comparison suffices.
    assert_ne!(
        round_into_float_with_max_digits(8712661000.1273185137283, 10),
        8712661000.127318
    );
    assert_eq!(
        round_into_float_with_max_digits(8712661000.1273185137283, 10),
        8712661000.1273185137
    );
}

#[test]
fn test_round_into_float_with_max_digits_very_small() {
    assert_eq!(
        round_into_float_with_max_digits(0.0000000000001, 5),
        0.0
    );
    assert_ne!(
        round_into_float_with_max_digits(0.0000000000001, 13),
        0.0
    );
}

#[test]
fn test_get_digits_count() {
    // get_digits_count returns value.log10().abs().round() as i64
    assert_eq!(get_digits_count(1.0), 0);     // log10(1) = 0
    assert_eq!(get_digits_count(9.0), 1);      // log10(9) ≈ 0.954 → 1
    assert_eq!(get_digits_count(10.0), 1);     // log10(10) = 1
    assert_eq!(get_digits_count(99.0), 2);     // log10(99) ≈ 1.996 → 2
    assert_eq!(get_digits_count(100.0), 2);    // log10(100) = 2
    assert_eq!(get_digits_count(999.0), 3);    // log10(999) ≈ 2.999 → 3
    assert_eq!(get_digits_count(1000.0), 3);   // log10(1000) = 3
    assert_eq!(get_digits_count(59866.0), 5);  // log10(59866) ≈ 4.777 → 5
    assert_eq!(get_digits_count(8712661000.0), 10); // log10(8712661000) ≈ 9.940 → 10
}

#[test]
fn test_get_digits_count_fractional_values() {
    assert_eq!(get_digits_count(125.0256), 2);            // log10(125) ≈ 2.097 → 2
    assert_eq!(get_digits_count(0.000000059), 7);         // log10(5.9e-8) ≈ -7.229, abs → 7
    assert_eq!(get_digits_count(1.567824117582484), 0);   // log10(1.567) ≈ 0.195 → 0
}
