pub mod greeting;

#[cfg(feature = "pymodule")]
use pyo3::prelude::*;
#[cfg(feature = "pymodule")]
use pyo3::types::PyModule;

#[cfg(feature = "pymodule")]
#[pymodule]
#[pyo3(name = "_core")]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("VERSION", poc_core::greeting::VERSION)?;
    greeting::register(m)?;
    Ok(())
}
