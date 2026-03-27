use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

#[pyfunction]
pub fn evaluate_condition(left: f64, right: f64, operator: &str) -> PyResult<bool> {
    octobot_commons::logical_operators::evaluate_condition(left, right, operator)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate_condition, m)?)?;
    Ok(())
}
