use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass(name = "BaseTreeNode", dict, subclass, module = "octobot_commons_rs")]
pub struct PyBaseTreeNode {
    #[pyo3(get, set)]
    pub node_value: Py<PyAny>,
    #[pyo3(get, set)]
    pub node_value_time: f64,
    #[pyo3(get, set)]
    pub node_type: Py<PyAny>,
    #[pyo3(get, set)]
    pub node_description: Py<PyAny>,
    #[pyo3(get, set)]
    pub node_metadata: Py<PyDict>,
    #[pyo3(get, set)]
    pub children: Py<PyDict>,
}

#[pymethods]
impl PyBaseTreeNode {
    #[new]
    #[pyo3(signature = (node_value=None, node_type=None))]
    pub fn new(py: Python<'_>, node_value: Option<Py<PyAny>>, node_type: Option<Py<PyAny>>) -> Self {
        Self {
            node_value: node_value.unwrap_or_else(|| py.None()),
            node_value_time: 0.0,
            node_type: node_type.unwrap_or_else(|| py.None()),
            node_description: py.None(),
            node_metadata: PyDict::new(py).unbind(),
            children: PyDict::new(py).unbind(),
        }
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyBaseTreeNode>()?;
    Ok(())
}
