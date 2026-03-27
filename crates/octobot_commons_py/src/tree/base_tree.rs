use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::tree::base_tree_node::PyBaseTreeNode;

pyo3::create_exception!(octobot_commons_rs, NodeExistsError, pyo3::exceptions::PyException);

#[pyclass(name = "BaseTree", dict, subclass, module = "octobot_commons_rs")]
pub struct PyBaseTree {
    #[pyo3(get)]
    pub root: Py<PyBaseTreeNode>,
}

#[pymethods]
impl PyBaseTree {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        let root = Py::new(py, PyBaseTreeNode::new(py, None, None))?;
        Ok(Self { root })
    }

    #[staticmethod]
    #[pyo3(signature = (value, node_type, node, timestamp=0.0))]
    fn set_node(
        value: Option<Py<PyAny>>,
        node_type: Option<Py<PyAny>>,
        node: &Bound<'_, PyBaseTreeNode>,
        timestamp: f64,
    ) -> PyResult<()> {
        let mut n = node.borrow_mut();
        if let Some(v) = value {
            n.node_value = v;
        }
        if let Some(t) = node_type {
            n.node_type = t;
        }
        n.node_value_time = timestamp;
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (value, node_type, path, timestamp=0.0, description=None, metadata=None))]
    fn set_node_at_path(
        &self,
        py: Python<'_>,
        value: Option<Py<PyAny>>,
        node_type: Option<Py<PyAny>>,
        path: &Bound<'_, PyList>,
        timestamp: f64,
        description: Option<Py<PyAny>>,
        metadata: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let keys = list_to_strings(path)?;
        let node = self.get_or_create_node_inner(py, &keys)?;
        let node_bound = node.bind(py);
        let mut n = node_bound.borrow_mut();
        if let Some(v) = value {
            n.node_value = v;
        }
        if let Some(t) = node_type {
            n.node_type = t;
        }
        n.node_value_time = timestamp;
        if let Some(d) = description {
            n.node_description = d;
        }
        if let Some(m) = metadata {
            n.node_metadata = m.clone().unbind();
        }
        Ok(())
    }

    #[pyo3(signature = (path, starting_node=None))]
    fn get_node(
        &self,
        py: Python<'_>,
        path: &Bound<'_, PyList>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let keys = list_to_strings(path)?;
        let start = starting_node.unwrap_or_else(|| self.root.clone_ref(py));
        self.traverse(py, &keys, start)
    }

    #[pyo3(signature = (path, starting_node=None, **_kwargs))]
    fn get_or_create_node(
        &self,
        py: Python<'_>,
        path: &Bound<'_, PyList>,
        starting_node: Option<Py<PyBaseTreeNode>>,
        _kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let keys = list_to_strings(path)?;
        if let Some(start) = starting_node {
            self.get_or_create_node_from(py, &keys, start)
        } else {
            self.get_or_create_node_inner(py, &keys)
        }
    }

    #[pyo3(signature = (path, starting_node=None))]
    fn delete_node(
        &self,
        py: Python<'_>,
        path: &Bound<'_, PyList>,
        starting_node: Option<Py<PyBaseTreeNode>>,
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let keys = list_to_strings(path)?;
        if keys.is_empty() {
            return Err(NodeExistsError::new_err("Cannot delete root"));
        }
        let parent_keys = &keys[..keys.len() - 1];
        let child_key = &keys[keys.len() - 1];
        let start = starting_node.unwrap_or_else(|| self.root.clone_ref(py));
        let parent = self.traverse(py, parent_keys, start)?;
        let children = parent.bind(py).borrow().children.clone_ref(py);
        let children_bound = children.bind(py);
        match children_bound.get_item(child_key)? {
            Some(child) => {
                children_bound.del_item(child_key)?;
                Ok(child.cast::<PyBaseTreeNode>()?.clone().unbind())
            }
            None => Err(NodeExistsError::new_err(
                "NodeExistsError: node does not exist at the given path",
            )),
        }
    }

    fn get_children_keys(
        &self,
        py: Python<'_>,
        path: &Bound<'_, PyList>,
    ) -> PyResult<Vec<String>> {
        let keys = list_to_strings(path)?;
        let start = self.root.clone_ref(py);
        let node = self.traverse(py, &keys, start)?;
        let children = node.bind(py).borrow().children.clone_ref(py);
        let result: Vec<String> = children
            .bind(py)
            .keys()
            .iter()
            .filter_map(|k| k.extract().ok())
            .collect();
        Ok(result)
    }

    #[pyo3(signature = (path=None, select_leaves_only=true))]
    fn get_nested_children_with_path(
        &self,
        py: Python<'_>,
        path: Option<&Bound<'_, PyList>>,
        select_leaves_only: bool,
    ) -> PyResult<Py<PyList>> {
        let keys = match path {
            Some(p) => list_to_strings(p)?,
            None => Vec::new(),
        };
        let start = self.root.clone_ref(py);
        let node = self.traverse(py, &keys, start)?;
        let results = PyList::empty(py);
        self.collect_nested(py, &node, &keys, select_leaves_only, &results)?;
        Ok(results.unbind())
    }

    fn clear(&self, py: Python<'_>) -> PyResult<()> {
        let mut root = self.root.bind(py).borrow_mut();
        root.node_value = py.None();
        root.node_value_time = 0.0;
        root.node_type = py.None();
        root.node_description = py.None();
        root.node_metadata = PyDict::new(py).unbind();
        root.children = PyDict::new(py).unbind();
        Ok(())
    }
}

impl PyBaseTree {
    fn traverse(
        &self,
        py: Python<'_>,
        keys: &[String],
        start: Py<PyBaseTreeNode>,
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let mut current = start;
        for key in keys {
            let children = current.bind(py).borrow().children.clone_ref(py);
            match children.bind(py).get_item(key)? {
                Some(child) => {
                    current = child.cast::<PyBaseTreeNode>()?.clone().unbind();
                }
                None => {
                    return Err(NodeExistsError::new_err(
                        "NodeExistsError: node does not exist at the given path",
                    ));
                }
            }
        }
        Ok(current)
    }

    fn get_or_create_node_inner(
        &self,
        py: Python<'_>,
        keys: &[String],
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let mut current = self.root.clone_ref(py);
        for key in keys {
            let children = current.bind(py).borrow().children.clone_ref(py);
            let children_bound = children.bind(py);
            match children_bound.get_item(key)? {
                Some(child) => {
                    current = child.cast::<PyBaseTreeNode>()?.clone().unbind();
                }
                None => {
                    let new_node = Py::new(py, PyBaseTreeNode::new(py, None, None))?;
                    children_bound.set_item(key, &new_node)?;
                    current = new_node;
                }
            }
        }
        Ok(current)
    }

    fn get_or_create_node_from(
        &self,
        py: Python<'_>,
        keys: &[String],
        start: Py<PyBaseTreeNode>,
    ) -> PyResult<Py<PyBaseTreeNode>> {
        let mut current = start;
        for key in keys {
            let children = current.bind(py).borrow().children.clone_ref(py);
            let children_bound = children.bind(py);
            match children_bound.get_item(key)? {
                Some(child) => {
                    current = child.cast::<PyBaseTreeNode>()?.clone().unbind();
                }
                None => {
                    let new_node = Py::new(py, PyBaseTreeNode::new(py, None, None))?;
                    children_bound.set_item(key, &new_node)?;
                    current = new_node;
                }
            }
        }
        Ok(current)
    }

    fn collect_nested(
        &self,
        py: Python<'_>,
        node: &Py<PyBaseTreeNode>,
        current_path: &[String],
        select_leaves_only: bool,
        results: &Bound<'_, PyList>,
    ) -> PyResult<()> {
        let children = node.bind(py).borrow().children.clone_ref(py);
        let children_bound = children.bind(py);
        let child_keys: Vec<String> = children_bound
            .keys()
            .iter()
            .filter_map(|k| k.extract().ok())
            .collect();

        if child_keys.is_empty() || !select_leaves_only {
            let path_list = PyList::new(py, current_path)?;
            let tuple = pyo3::types::PyTuple::new(py, [node.bind(py).as_any(), path_list.as_any()])?;
            results.append(tuple)?;
        }

        for key in child_keys {
            let child_obj = children_bound.get_item(&key)?.unwrap();
            let child: Py<PyBaseTreeNode> = child_obj.cast::<PyBaseTreeNode>()?.clone().unbind();
            let mut child_path = current_path.to_vec();
            child_path.push(key);
            self.collect_nested(py, &child, &child_path, select_leaves_only, results)?;
        }
        Ok(())
    }
}

fn list_to_strings(list: &Bound<'_, PyList>) -> PyResult<Vec<String>> {
    list.iter()
        .map(|item| item.str().and_then(|s| s.extract::<String>()))
        .collect()
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyBaseTree>()?;
    m.add("NodeExistsError", m.py().get_type::<NodeExistsError>())?;
    Ok(())
}
