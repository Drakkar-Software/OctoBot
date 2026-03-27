use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use octobot_evaluators::constants::EVALUATION_ALLOWED_TIME_DELTA;
use octobot_evaluators::matrix::matrix_manager as rust_mm;

use octobot_commons_py::tree::base_tree_node::PyBaseTreeNode;

// ---------------------------------------------------------------------------
// Singleton access helpers
// ---------------------------------------------------------------------------

fn get_matrices_instance(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    py.import("octobot_evaluators_rs._core")?
        .getattr("Matrices")?
        .call_method0("instance")
}

fn get_matrix_from_singleton(py: Python<'_>, matrix_id: &str) -> PyResult<Py<PyAny>> {
    Ok(get_matrices_instance(py)?
        .call_method1("get_matrix", (matrix_id,))?
        .unbind())
}

// ---------------------------------------------------------------------------
// Exposed functions
// ---------------------------------------------------------------------------

#[pyfunction]
fn get_matrix(py: Python<'_>, matrix_id: &str) -> PyResult<Py<PyAny>> {
    get_matrix_from_singleton(py, matrix_id)
}

#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(signature = (matrix_id, tentacle_path, tentacle_type, tentacle_value, timestamp=0.0, description=None, metadata=None))]
fn set_tentacle_value(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
    tentacle_type: Py<PyAny>,
    tentacle_value: Py<PyAny>,
    timestamp: f64,
    description: Option<Py<PyAny>>,
    metadata: Option<&Bound<'_, PyDict>>,
) -> PyResult<()> {
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("timestamp", timestamp)?;
    if let Some(d) = description {
        kwargs.set_item("description", d)?;
    }
    if let Some(m) = metadata {
        kwargs.set_item("metadata", m)?;
    }
    matrix.bind(py).call_method(
        "set_node_value",
        (tentacle_value, tentacle_type, tentacle_path),
        Some(&kwargs),
    )?;
    Ok(())
}

#[pyfunction]
fn get_tentacle_node(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
) -> PyResult<Option<Py<PyBaseTreeNode>>> {
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let result = matrix
        .bind(py)
        .call_method1("get_node_at_path", (tentacle_path,))?;
    if result.is_none() {
        Ok(None)
    } else {
        let node: Py<PyBaseTreeNode> = result.extract()?;
        Ok(Some(node))
    }
}

#[pyfunction]
fn delete_tentacle_node(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
) -> PyResult<Option<Py<PyBaseTreeNode>>> {
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let result = matrix
        .bind(py)
        .call_method1("delete_node_at_path", (tentacle_path,))?;
    if result.is_none() {
        Ok(None)
    } else {
        let node: Py<PyBaseTreeNode> = result.extract()?;
        Ok(Some(node))
    }
}

#[pyfunction]
fn get_tentacle_value(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
) -> PyResult<Py<PyAny>> {
    match get_tentacle_node(py, matrix_id, tentacle_path)? {
        Some(node) => Ok(node.bind(py).borrow().node_value.clone_ref(py)),
        None => Ok(py.None()),
    }
}

#[pyfunction]
fn get_tentacle_eval_time(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
) -> PyResult<Option<f64>> {
    match get_tentacle_node(py, matrix_id, tentacle_path)? {
        Some(node) => {
            let t = node.bind(py).borrow().node_value_time;
            Ok(Some(t))
        }
        None => Ok(None),
    }
}

// ---------------------------------------------------------------------------
// Pure path builders -- delegate to Rust
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (exchange_name=None, tentacle_type=None, tentacle_name=None))]
fn get_tentacle_path(
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    tentacle_name: Option<&str>,
) -> Vec<String> {
    rust_mm::get_tentacle_path(exchange_name, tentacle_type, tentacle_name)
}

#[pyfunction]
#[pyo3(signature = (cryptocurrency=None, symbol=None, time_frame=None))]
fn get_tentacle_value_path(
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Vec<String> {
    rust_mm::get_tentacle_value_path(cryptocurrency, symbol, time_frame)
}

#[pyfunction]
#[pyo3(signature = (tentacle_name, tentacle_type, exchange_name=None, cryptocurrency=None, symbol=None, time_frame=None))]
fn get_matrix_default_value_path(
    tentacle_name: &str,
    tentacle_type: &str,
    exchange_name: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Vec<String> {
    rust_mm::get_matrix_default_value_path(
        tentacle_name,
        tentacle_type,
        exchange_name,
        cryptocurrency,
        symbol,
        time_frame,
    )
}

// ---------------------------------------------------------------------------
// Tentacle node queries
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (matrix_id, exchange_name=None, tentacle_type=None, tentacle_name=None))]
fn get_tentacle_nodes(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    tentacle_name: Option<&str>,
) -> PyResult<Vec<Py<PyAny>>> {
    let path = rust_mm::get_tentacle_path(exchange_name, tentacle_type, tentacle_name);
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let result = matrix
        .bind(py)
        .call_method1("get_node_children_at_path", (path,))?;
    let list: Vec<Py<PyAny>> = result
        .try_iter()?
        .map(|item| Ok(item?.unbind()))
        .collect::<PyResult<Vec<_>>>()?;
    Ok(list)
}

#[pyfunction]
#[pyo3(signature = (matrix_id, node_path, starting_node=None))]
fn get_node_children_by_names_at_path(
    py: Python<'_>,
    matrix_id: &str,
    node_path: Vec<String>,
    starting_node: Option<Py<PyBaseTreeNode>>,
) -> PyResult<Py<PyDict>> {
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let kwargs = PyDict::new(py);
    if let Some(sn) = starting_node {
        kwargs.set_item("starting_node", sn)?;
    }
    let result = matrix.bind(py).call_method(
        "get_node_children_by_names_at_path",
        (node_path,),
        Some(&kwargs),
    )?;
    Ok(result.cast_into::<PyDict>()?.unbind())
}

#[pyfunction]
#[pyo3(signature = (matrix_id, tentacle_nodes, cryptocurrency=None, symbol=None, time_frame=None))]
fn get_tentacles_value_nodes(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_nodes: Vec<Py<PyAny>>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> PyResult<Vec<Py<PyAny>>> {
    let value_path: Vec<String> = rust_mm::get_tentacle_value_path(cryptocurrency, symbol, time_frame);
    let path_list = PyList::new(py, &value_path)?;
    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let matrix_bound = matrix.bind(py);
    let mut results = Vec::with_capacity(tentacle_nodes.len());
    let kwargs = PyDict::new(py);

    for node in &tentacle_nodes {
        kwargs.set_item("starting_node", node)?;
        let value_result =
            matrix_bound.call_method("get_node_at_path", (&path_list,), Some(&kwargs))?;
        if !value_result.is_none() {
            results.push(value_result.unbind());
        }
    }
    Ok(results)
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(signature = (matrix_id, exchange_name=None, tentacle_type=None, cryptocurrency=None, symbol=None, time_frame=None, allow_missing=true, allowed_values=None))]
fn get_evaluations_by_evaluator(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
    allow_missing: bool,
    allowed_values: Option<Py<PyAny>>,
) -> PyResult<Py<PyDict>> {
    let tentacle_path = rust_mm::get_tentacle_path(exchange_name, tentacle_type, None);

    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let matrix_bound = matrix.bind(py);

    // Get evaluator children at tentacle path
    let evaluator_nodes = matrix_bound
        .call_method1("get_node_children_by_names_at_path", (tentacle_path,))?;
    let evaluator_dict = evaluator_nodes.cast::<PyDict>()?;

    let check_fn = py
        .import("octobot_commons.evaluators_util")?
        .getattr("check_valid_eval_note")?;

    let evaluations = PyDict::new(py);

    for (evaluator_name, node) in evaluator_dict.iter() {
        // Use get_tentacles_value_nodes with the node to resolve the value
        let nodes_list = pyo3::types::PyList::new(py, [&node])?;
        let value_nodes: Vec<Py<PyAny>> = get_tentacles_value_nodes(
            py, matrix_id,
            nodes_list.iter().map(|v| v.unbind()).collect(),
            cryptocurrency, symbol, time_frame,
        )?;

        if value_nodes.len() > 1 {
            // log warning -- more than one evaluation
        } else if let Some(eval_node) = value_nodes.first() {
            let en: Py<PyBaseTreeNode> = eval_node.bind(py).extract()?;
            let en_bound = en.bind(py);
            let en_ref = en_bound.borrow();
            let eval_value = en_ref.node_value.clone_ref(py);

            // Check allowed_values first, then check_valid_eval_note
            let in_allowed = if let Some(ref av) = allowed_values {
                av.bind(py).call_method1("__contains__", (&eval_value,))
                    .and_then(|r| r.extract::<bool>())
                    .unwrap_or(false)
            } else {
                false
            };
            let is_valid: bool = in_allowed || check_fn.call1((&eval_value,))?.extract()?;

            if is_valid {
                // Return the actual node object, matching Python behavior
                evaluations.set_item(&evaluator_name, eval_node)?;
            } else if !allow_missing {
                let tf_display = time_frame.unwrap_or("evaluation");
                let sym_display = symbol.unwrap_or("unknown");
                let eval_name_str: String = evaluator_name.extract()?;
                return Err(crate::UnsetTentacleEvaluation::new_err(format!(
                    "Missing {} for {} on {}, evaluation is {:?}).",
                    tf_display, eval_name_str, sym_display, eval_value
                )));
            }
        }
    }

    Ok(evaluations.unbind())
}

// ---------------------------------------------------------------------------
// Available time frames / symbols
// ---------------------------------------------------------------------------

#[pyfunction]
fn get_available_time_frames(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: &str,
    tentacle_type: &str,
    cryptocurrency: &str,
    symbol: &str,
) -> PyResult<Vec<String>> {
    let tentacle_path =
        rust_mm::get_tentacle_path(Some(exchange_name), Some(tentacle_type), None);
    let value_path =
        rust_mm::get_tentacle_value_path(Some(cryptocurrency), Some(symbol), None);

    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let matrix_bound = matrix.bind(py);

    // Get evaluator-level children
    let evaluator_nodes = matrix_bound
        .call_method1("get_node_children_by_names_at_path", (tentacle_path,))?;
    let evaluator_dict = evaluator_nodes.cast::<PyDict>()?;

    // Take the first evaluator node
    let first_item = evaluator_dict.iter().next();
    let first_node = match first_item {
        Some((_, node)) => node,
        None => return Ok(Vec::new()),
    };

    // Get time frame children from value path starting at that node
    let kwargs = PyDict::new(py);
    kwargs.set_item("starting_node", &first_node)?;
    let children = matrix_bound
        .call_method(
            "get_node_children_by_names_at_path",
            (value_path,),
            Some(&kwargs),
        )?;
    let children_dict = children.cast::<PyDict>()?;

    let keys: Vec<String> = children_dict
        .keys()
        .iter()
        .filter_map(|k| k.extract().ok())
        .collect();
    Ok(keys)
}

#[pyfunction]
#[pyo3(signature = (matrix_id, exchange_name, cryptocurrency, tentacle_type=None, second_tentacle_type=None))]
fn get_available_symbols(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: &str,
    cryptocurrency: &str,
    tentacle_type: Option<&str>,
    second_tentacle_type: Option<&str>,
) -> PyResult<Vec<String>> {
    let tt = tentacle_type.unwrap_or("TA");
    let stt = second_tentacle_type.unwrap_or("REAL_TIME");

    get_available_symbols_inner(py, matrix_id, exchange_name, cryptocurrency, tt, stt)
}

fn get_available_symbols_inner(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: &str,
    cryptocurrency: &str,
    tentacle_type: &str,
    second_tentacle_type: &str,
) -> PyResult<Vec<String>> {
    let tentacle_path =
        rust_mm::get_tentacle_path(Some(exchange_name), Some(tentacle_type), None);
    let value_path = rust_mm::get_tentacle_value_path(Some(cryptocurrency), None, None);

    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let matrix_bound = matrix.bind(py);

    let evaluator_nodes = matrix_bound
        .call_method1("get_node_children_by_names_at_path", (tentacle_path,))?;
    let evaluator_dict = evaluator_nodes.cast::<PyDict>()?;

    let first_item = evaluator_dict.iter().next();
    let first_node = match first_item {
        Some((_, node)) => node,
        None => return Ok(Vec::new()),
    };

    let kwargs = PyDict::new(py);
    kwargs.set_item("starting_node", &first_node)?;
    let children = matrix_bound
        .call_method(
            "get_node_children_by_names_at_path",
            (value_path,),
            Some(&kwargs),
        )?;
    let children_dict = children.cast::<PyDict>()?;

    let symbols: Vec<String> = children_dict
        .keys()
        .iter()
        .filter_map(|k| k.extract().ok())
        .collect();

    if !symbols.is_empty() {
        return Ok(symbols);
    }

    // Retry with second tentacle type if it differs
    if tentacle_type != second_tentacle_type {
        return get_available_symbols_inner(
            py,
            matrix_id,
            exchange_name,
            cryptocurrency,
            second_tentacle_type,
            second_tentacle_type,
        );
    }

    Ok(Vec::new())
}

// ---------------------------------------------------------------------------
// Time-validity checks
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (matrix_id, tentacle_path, timestamp=0.0, delta=None))]
fn is_tentacle_value_valid(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path: Vec<String>,
    timestamp: f64,
    delta: Option<f64>,
) -> PyResult<bool> {
    let ts = if timestamp == 0.0 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    } else {
        timestamp
    };
    let allowed = delta.unwrap_or(EVALUATION_ALLOWED_TIME_DELTA);

    // Extract time frame string before moving tentacle_path
    let tf_str = tentacle_path.last().cloned();

    // Check node existence first (Python raises KeyError if missing)
    let node = match get_tentacle_node(py, matrix_id, tentacle_path)? {
        Some(n) => n,
        None => {
            return Err(pyo3::exceptions::PyKeyError::new_err(
                "No node at given path",
            ));
        }
    };

    // Extract time frame from the last path element (matching Python's behavior)
    let tf_minutes: f64 = match tf_str.as_deref() {
        Some(tf_val) => {
            let tf_enum_cls = py.import("octobot_commons.enums")?;
            let tf_minutes_map = tf_enum_cls.getattr("TimeFramesMinutes")?;
            let tf_enum = tf_enum_cls.getattr("TimeFrames")?.call1((tf_val,));
            match tf_enum {
                Ok(tf) => tf_minutes_map.get_item(tf)?.extract().unwrap_or(0.0),
                Err(_) => return Ok(false),
            }
        }
        None => return Ok(false),
    };

    let eval_time = node.bind(py).borrow().node_value_time;
    Ok(rust_mm::is_evaluation_valid_in_time(
        ts, eval_time, tf_minutes, allowed,
    ))
}

/// Check whether an evaluation timestamp is still valid.
///
/// `time_frame` is a Python `TimeFrames` enum. The resolution to minutes
/// is done by `common_enums.TimeFramesMinutes[time_frame]`.
#[pyfunction]
#[pyo3(signature = (current_time, evaluation_time, time_frame, allowed_delta=None))]
fn is_evaluation_valid_in_time(
    py: Python<'_>,
    current_time: f64,
    evaluation_time: f64,
    time_frame: Py<PyAny>,
    allowed_delta: Option<f64>,
) -> PyResult<bool> {
    let delta = allowed_delta.unwrap_or(EVALUATION_ALLOWED_TIME_DELTA);
    let tf_minutes: f64 = py
        .import("octobot_commons.enums")?
        .getattr("TimeFramesMinutes")?
        .get_item(&time_frame)?
        .extract()?;
    Ok(rust_mm::is_evaluation_valid_in_time(
        current_time,
        evaluation_time,
        tf_minutes,
        delta,
    ))
}

#[pyfunction]
#[pyo3(signature = (matrix_id, tentacle_path_list, timestamp=0.0, delta=None))]
fn is_tentacles_values_valid(
    py: Python<'_>,
    matrix_id: &str,
    tentacle_path_list: Vec<Vec<String>>,
    timestamp: f64,
    delta: Option<f64>,
) -> PyResult<bool> {
    for path in tentacle_path_list {
        if !is_tentacle_value_valid(py, matrix_id, path, timestamp, delta)? {
            return Ok(false);
        }
    }
    Ok(true)
}

// ---------------------------------------------------------------------------
// Latest eval time
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (matrix_id, exchange_name=None, tentacle_type=None, cryptocurrency=None, symbol=None, time_frame=None))]
fn get_latest_eval_time(
    py: Python<'_>,
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> PyResult<Option<f64>> {
    let tentacle_path = rust_mm::get_tentacle_path(exchange_name, tentacle_type, None);
    let value_path = rust_mm::get_tentacle_value_path(cryptocurrency, symbol, time_frame);
    let path_list = PyList::new(py, &value_path)?;

    let matrix = get_matrix_from_singleton(py, matrix_id)?;
    let matrix_bound = matrix.bind(py);

    // Get tentacle-level children (one per evaluator)
    let evaluator_nodes = matrix_bound
        .call_method1("get_node_children_by_names_at_path", (tentacle_path,))?;
    let evaluator_dict = evaluator_nodes.cast::<PyDict>()?;

    let kwargs = PyDict::new(py);
    let mut latest: Option<f64> = None;
    for (_name, node) in evaluator_dict.iter() {
        kwargs.set_item("starting_node", &node)?;
        let value_result = matrix_bound
            .call_method("get_node_at_path", (&path_list,), Some(&kwargs))?;
        if value_result.is_none() {
            continue;
        }
        let vn: Py<PyBaseTreeNode> = value_result.extract()?;
        let t = vn.bind(py).borrow().node_value_time;
        if t != 0.0 {
            latest = Some(match latest {
                Some(prev) => prev.max(t),
                None => t,
            });
        }
    }

    Ok(latest)
}

// ---------------------------------------------------------------------------
// Register
// ---------------------------------------------------------------------------

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_matrix, m)?)?;
    m.add_function(wrap_pyfunction!(set_tentacle_value, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_node, m)?)?;
    m.add_function(wrap_pyfunction!(delete_tentacle_node, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_value, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_eval_time, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_path, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_value_path, m)?)?;
    m.add_function(wrap_pyfunction!(get_matrix_default_value_path, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacle_nodes, m)?)?;
    m.add_function(wrap_pyfunction!(get_node_children_by_names_at_path, m)?)?;
    m.add_function(wrap_pyfunction!(get_tentacles_value_nodes, m)?)?;
    m.add_function(wrap_pyfunction!(get_evaluations_by_evaluator, m)?)?;
    m.add_function(wrap_pyfunction!(get_available_time_frames, m)?)?;
    m.add_function(wrap_pyfunction!(get_available_symbols, m)?)?;
    m.add_function(wrap_pyfunction!(is_tentacle_value_valid, m)?)?;
    m.add_function(wrap_pyfunction!(is_evaluation_valid_in_time, m)?)?;
    m.add_function(wrap_pyfunction!(is_tentacles_values_valid, m)?)?;
    m.add_function(wrap_pyfunction!(get_latest_eval_time, m)?)?;
    Ok(())
}
