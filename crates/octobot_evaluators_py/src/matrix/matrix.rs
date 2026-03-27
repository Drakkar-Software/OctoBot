use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use octobot_commons_py::tree::base_tree::PyBaseTree;
use octobot_commons_py::tree::base_tree_node::PyBaseTreeNode;

/// Convert a list of arbitrary Python objects to a PyList of their str() representations.
fn to_py_path_list<'py>(py: Python<'py>, path: Vec<Py<PyAny>>) -> PyResult<Bound<'py, PyList>> {
    let items: Vec<Bound<'py, PyAny>> = path
        .iter()
        .map(|p| p.bind(py).str().map(|s| s.into_any()))
        .collect::<PyResult<_>>()?;
    PyList::new(py, &items)
}

#[pyclass(name = "Matrix", dict, subclass, module = "octobot_evaluators_rs")]
pub struct PyMatrix {
    #[pyo3(get)]
    pub matrix_id: String,
    #[pyo3(get)]
    pub matrix: Py<PyBaseTree>,
}

#[pymethods]
impl PyMatrix {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        let id = uuid::Uuid::new_v4().to_string();
        let tree_cls = py.get_type::<PyBaseTree>();
        let tree: Py<PyBaseTree> = tree_cls.call0()?.extract()?;
        Ok(Self {
            matrix_id: id,
            matrix: tree,
        })
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (value, value_type, value_path, timestamp=0.0, description=None, metadata=None))]
    fn set_node_value(
        &self,
        py: Python<'_>,
        value: Py<PyAny>,
        value_type: Py<PyAny>,
        value_path: Vec<Py<PyAny>>,
        timestamp: f64,
        description: Option<Py<PyAny>>,
        metadata: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let tree = self.matrix.bind(py);
        let path_list = to_py_path_list(py, value_path)?;
        let kwargs = PyDict::new(py);
        kwargs.set_item("timestamp", timestamp)?;
        if let Some(d) = description {
            kwargs.set_item("description", d)?;
        }
        if let Some(m) = metadata {
            kwargs.set_item("metadata", m)?;
        }
        tree.call_method(
            "set_node_at_path",
            (value, value_type, path_list),
            Some(&kwargs),
        )?;
        Ok(())
    }

    #[pyo3(signature = (node_path, starting_node=None))]
    fn get_node_children_at_path(
        &self,
        py: Python<'_>,
        node_path: Vec<Py<PyAny>>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let tree = self.matrix.bind(py);
        let path_list = to_py_path_list(py, node_path)?;
        let kwargs = PyDict::new(py);
        if let Some(sn) = starting_node {
            kwargs.set_item("starting_node", sn)?;
        }
        let result = tree.call_method("get_node", (path_list,), Some(&kwargs));
        match result {
            Ok(node) => {
                let node_ref: Py<PyBaseTreeNode> = node.extract()?;
                let children = node_ref.bind(py).borrow().children.clone_ref(py);
                Ok(children
                    .bind(py)
                    .values()
                    .iter()
                    .map(|v| v.unbind())
                    .collect())
            }
            Err(_) => Ok(Vec::new()),
        }
    }

    #[pyo3(signature = (node_path, starting_node=None))]
    fn get_node_children_by_names_at_path(
        &self,
        py: Python<'_>,
        node_path: Vec<Py<PyAny>>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Py<PyDict>> {
        let tree = self.matrix.bind(py);
        let path_list = to_py_path_list(py, node_path)?;
        let kwargs = PyDict::new(py);
        if let Some(sn) = starting_node {
            kwargs.set_item("starting_node", sn)?;
        }
        let result = tree.call_method("get_node", (path_list,), Some(&kwargs));
        match result {
            Ok(node) => {
                let node_ref: Py<PyBaseTreeNode> = node.extract()?;
                let children = node_ref.bind(py).borrow().children.clone_ref(py);
                let out = PyDict::new(py);
                for (k, v) in children.bind(py).iter() {
                    out.set_item(k, v)?;
                }
                Ok(out.unbind())
            }
            Err(_) => Ok(PyDict::new(py).unbind()),
        }
    }

    #[pyo3(signature = (node_path, starting_node=None))]
    fn get_node_at_path(
        &self,
        py: Python<'_>,
        node_path: Vec<Py<PyAny>>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Option<Py<PyBaseTreeNode>>> {
        let tree = self.matrix.bind(py);
        let path_list = to_py_path_list(py, node_path)?;
        let kwargs = PyDict::new(py);
        if let Some(sn) = starting_node {
            kwargs.set_item("starting_node", sn)?;
        }
        match tree.call_method("get_node", (path_list,), Some(&kwargs)) {
            Ok(node) => {
                let n: Py<PyBaseTreeNode> = node.extract()?;
                Ok(Some(n))
            }
            Err(_) => Ok(None),
        }
    }

    #[pyo3(signature = (node_path, starting_node=None))]
    fn delete_node_at_path(
        &self,
        py: Python<'_>,
        node_path: Vec<Py<PyAny>>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Option<Py<PyBaseTreeNode>>> {
        let tree = self.matrix.bind(py);
        let path_list = to_py_path_list(py, node_path)?;
        let kwargs = PyDict::new(py);
        if let Some(sn) = starting_node {
            kwargs.set_item("starting_node", sn)?;
        }
        match tree.call_method("delete_node", (path_list,), Some(&kwargs)) {
            Ok(node) => {
                let n: Py<PyBaseTreeNode> = node.extract()?;
                Ok(Some(n))
            }
            Err(_) => Ok(None),
        }
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyMatrix>()?;
    Ok(())
}
