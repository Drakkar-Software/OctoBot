use octobot_commons::data_util::*;

#[test]
fn test_mean_integers() {
    assert_eq!(mean(&[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]), 4.0);
}

#[test]
fn test_mean_floats() {
    assert_eq!(mean(&[0.684, 1.0, 2.0, 3.0, 4.0, 5.5, 6.0, 7.5]), 3.7105);
}

#[test]
fn test_mean_empty() {
    assert_eq!(mean(&[]), 0.0);
}

#[test]
fn test_mean_single_element() {
    assert_eq!(mean(&[42.0]), 42.0);
}

#[test]
fn test_mean_negative_values() {
    assert_eq!(mean(&[-2.0, -1.0, 0.0, 1.0, 2.0]), 0.0);
}
