use octobot_commons::enums::LogicalOperators;
use octobot_commons::logical_operators::evaluate_condition;

#[test]
fn test_lower_than() {
    let op = LogicalOperators::LowerThan.value();
    assert!(evaluate_condition(1.0, 2.0, op).unwrap());
    assert!(!evaluate_condition(2.0, 1.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 1.0, op).unwrap());
}

#[test]
fn test_higher_than() {
    let op = LogicalOperators::HigherThan.value();
    assert!(evaluate_condition(2.0, 1.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 2.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 1.0, op).unwrap());
}

#[test]
fn test_lower_or_equal_to() {
    let op = LogicalOperators::LowerOrEqualTo.value();
    assert!(evaluate_condition(1.0, 2.0, op).unwrap());
    assert!(evaluate_condition(1.0, 1.0, op).unwrap());
    assert!(!evaluate_condition(2.0, 1.0, op).unwrap());
}

#[test]
fn test_higher_or_equal_to() {
    let op = LogicalOperators::HigherOrEqualTo.value();
    assert!(evaluate_condition(2.0, 1.0, op).unwrap());
    assert!(evaluate_condition(1.0, 1.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 2.0, op).unwrap());
}

#[test]
fn test_equal_to() {
    let op = LogicalOperators::EqualTo.value();
    assert!(evaluate_condition(1.0, 1.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 2.0, op).unwrap());
}

#[test]
fn test_different_from() {
    let op = LogicalOperators::DifferentFrom.value();
    assert!(evaluate_condition(1.0, 2.0, op).unwrap());
    assert!(!evaluate_condition(1.0, 1.0, op).unwrap());
}

#[test]
fn test_unknown_operator() {
    assert!(evaluate_condition(1.0, 2.0, "bogus").is_err());
}
