use pyo3::prelude::*;

/// Return a Python awaitable that immediately resolves to None.
pub fn py_none_future(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async {
        Ok(Python::attach(|py| py.None()))
    })
}
