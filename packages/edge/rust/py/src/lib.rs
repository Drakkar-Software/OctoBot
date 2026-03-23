use pyo3::prelude::*;
use octobot_edge_core as core;

#[pyfunction]
fn hmac_sha256<'py>(py: Python<'py>, key: &[u8], message: &[u8]) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
    let result = core::hmac_sha256(key, message)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(pyo3::types::PyBytes::new_bound(py, &result))
}

#[pyfunction]
fn hmac_sha512<'py>(py: Python<'py>, key: &[u8], message: &[u8]) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
    let result = core::hmac_sha512(key, message)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(pyo3::types::PyBytes::new_bound(py, &result))
}

#[pyfunction]
fn hash(algorithm: &str, data: &str, encoding: &str) -> PyResult<String> {
    core::hash(algorithm, data, encoding)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Generic HMAC — matches WASM/NAPI API surface
#[pyfunction]
fn hmac(algorithm: &str, secret: &str, data: &str, encoding: &str) -> PyResult<String> {
    core::hmac(algorithm, secret, data, encoding)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Keep backward compatibility alias
#[pyfunction]
fn hash_digest(algorithm: &str, data: &str, encoding: &str) -> PyResult<String> {
    hash(algorithm, data, encoding)
}

#[pymodule]
fn octobot_edge_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hmac_sha256, m)?)?;
    m.add_function(wrap_pyfunction!(hmac_sha512, m)?)?;
    m.add_function(wrap_pyfunction!(hmac, m)?)?;
    m.add_function(wrap_pyfunction!(hash, m)?)?;
    m.add_function(wrap_pyfunction!(hash_digest, m)?)?;
    Ok(())
}
