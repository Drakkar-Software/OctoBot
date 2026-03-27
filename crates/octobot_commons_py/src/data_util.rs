use pyo3::prelude::*;

#[pyfunction]
pub fn mean(number_list: Vec<f64>) -> f64 {
    octobot_commons::data_util::mean(&number_list)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(mean, m)?)?;
    Ok(())
}
