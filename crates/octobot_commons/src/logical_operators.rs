use crate::enums::LogicalOperators;
use crate::errors::CommonsError;

pub fn evaluate_condition(left: f64, right: f64, operator: &str) -> Result<bool, CommonsError> {
    if operator == LogicalOperators::LowerThan.value() {
        Ok(left < right)
    } else if operator == LogicalOperators::HigherThan.value() {
        Ok(left > right)
    } else if operator == LogicalOperators::LowerOrEqualTo.value() {
        Ok(left <= right)
    } else if operator == LogicalOperators::HigherOrEqualTo.value() {
        Ok(left >= right)
    } else if operator == LogicalOperators::EqualTo.value() {
        Ok((left - right).abs() < f64::EPSILON)
    } else if operator == LogicalOperators::DifferentFrom.value() {
        Ok((left - right).abs() >= f64::EPSILON)
    } else {
        Err(CommonsError::LogicalOperator(format!(
            "Unknown operator: {operator}"
        )))
    }
}
