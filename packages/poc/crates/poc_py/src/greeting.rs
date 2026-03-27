use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyfunction]
fn greet(name: &str) -> String {
    poc_core::greeting::greet(name)
}

#[pyfunction]
fn add(a: i64, b: i64) -> i64 {
    poc_core::greeting::add(a, b)
}

#[pyfunction]
fn fibonacci(n: u32) -> u64 {
    poc_core::greeting::fibonacci(n)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(greet, m)?)?;
    m.add_function(wrap_pyfunction!(add, m)?)?;
    m.add_function(wrap_pyfunction!(fibonacci, m)?)?;
    Ok(())
}
