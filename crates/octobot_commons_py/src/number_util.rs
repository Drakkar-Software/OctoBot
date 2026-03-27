use pyo3::prelude::*;

#[pyfunction]
pub fn round_into_str_with_max_digits(number: f64, digits_count: usize) -> String {
    octobot_commons::number_util::round_into_str_with_max_digits(number, digits_count)
}

#[pyfunction]
pub fn round_into_float_with_max_digits(number: f64, digits_count: usize) -> f64 {
    octobot_commons::number_util::round_into_float_with_max_digits(number, digits_count)
}

#[pyfunction]
pub fn get_digits_count(value: f64) -> i64 {
    octobot_commons::number_util::get_digits_count(value)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(round_into_str_with_max_digits, m)?)?;
    m.add_function(wrap_pyfunction!(round_into_float_with_max_digits, m)?)?;
    m.add_function(wrap_pyfunction!(get_digits_count, m)?)?;
    Ok(())
}
