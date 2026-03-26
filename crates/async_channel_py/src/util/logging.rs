use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (name=None))]
pub fn get_logger(py: Python<'_>, name: Option<&str>) -> PyResult<Py<PyAny>> {
    let name = name.unwrap_or("");
    if let Ok(m) = py.import("octobot_commons.logging") {
        if let Ok(l) = m.call_method1("get_logger", (name,)) {
            return Ok(l.unbind());
        }
    }
    Ok(py.import("logging")?.call_method1("getLogger", (name,))?.unbind())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_logger, m)?)?;
    Ok(())
}
