use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::matrix::matrix::PyMatrix;

#[pyclass(name = "Matrices", dict, subclass, module = "octobot_evaluators_rs")]
pub struct PyMatrices {
    #[pyo3(get, set)]
    pub matrices: Py<PyDict>,
}

#[pymethods]
impl PyMatrices {
    #[new]
    fn new(py: Python<'_>) -> Self {
        Self {
            matrices: PyDict::new(py).unbind(),
        }
    }

    #[classmethod]
    fn instance(cls: &Bound<'_, pyo3::types::PyType>) -> PyResult<Py<PyAny>> {
        let py = cls.py();
        let has: bool = cls
            .getattr("_instances")
            .and_then(|d| d.call_method1("__contains__", (cls,)))
            .and_then(|r| r.extract())
            .unwrap_or(false);
        if has {
            return Ok(cls.getattr("_instances")?.get_item(cls)?.unbind());
        }
        let inst = cls.call0()?;
        if cls.getattr("_instances").is_err() {
            cls.setattr("_instances", PyDict::new(py))?;
        }
        cls.getattr("_instances")?.set_item(cls, &inst)?;
        Ok(inst.unbind())
    }

    fn add_matrix(&self, py: Python<'_>, matrix: &Bound<'_, PyMatrix>) -> PyResult<()> {
        let id = matrix.borrow().matrix_id.clone();
        let d = self.matrices.bind(py);
        if d.get_item(&id)?.is_none() {
            d.set_item(&id, matrix)?;
        }
        Ok(())
    }

    fn get_matrix(&self, py: Python<'_>, matrix_id: &str) -> PyResult<Py<PyAny>> {
        self.matrices
            .bind(py)
            .get_item(matrix_id)?
            .map(|v| v.unbind())
            .ok_or_else(|| {
                pyo3::exceptions::PyKeyError::new_err(format!("Matrix {} not found", matrix_id))
            })
    }

    fn del_matrix(&self, py: Python<'_>, matrix_id: &str) -> PyResult<()> {
        let d = self.matrices.bind(py);
        if d.get_item(matrix_id)?.is_some() {
            d.del_item(matrix_id)?;
        }
        Ok(())
    }

    #[classattr]
    fn _instances(py: Python<'_>) -> Py<PyAny> {
        PyDict::new(py).unbind().into_any()
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyMatrices>()?;
    Ok(())
}
