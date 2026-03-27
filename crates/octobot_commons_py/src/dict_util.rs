use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;

fn pyany_to_value(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        Ok(Value::Null)
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(Value::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(Value::Number(i.into()))
    } else if let Ok(f) = obj.extract::<f64>() {
        Ok(serde_json::Number::from_f64(f)
            .map(Value::Number)
            .unwrap_or(Value::Null))
    } else if let Ok(s) = obj.extract::<String>() {
        Ok(Value::String(s))
    } else if let Ok(list) = obj.cast::<PyList>() {
        let mut arr = Vec::new();
        for item in list.iter() {
            arr.push(pyany_to_value(&item)?);
        }
        Ok(Value::Array(arr))
    } else if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in dict.iter() {
            let key: String = k.extract()?;
            map.insert(key, pyany_to_value(&v)?);
        }
        Ok(Value::Object(map))
    } else {
        Ok(Value::Null)
    }
}

fn value_to_pyany(py: Python<'_>, val: &Value) -> PyResult<Py<PyAny>> {
    match val {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => Ok(b.into_pyobject(py)?.to_owned().into_any().unbind()),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_pyobject(py)?.into_any().unbind())
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_pyobject(py)?.into_any().unbind())
            } else {
                Ok(py.None())
            }
        }
        Value::String(s) => Ok(s.into_pyobject(py)?.into_any().unbind()),
        Value::Array(arr) => {
            let list = PyList::empty(py);
            for item in arr {
                list.append(value_to_pyany(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        Value::Object(map) => {
            let dict = PyDict::new(py);
            for (k, v) in map {
                dict.set_item(k, value_to_pyany(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
    }
}

#[pyfunction]
#[pyo3(signature = (dict, key, list_indexes=None))]
pub fn find_nested_value(
    py: Python<'_>,
    dict: &Bound<'_, PyAny>,
    key: &str,
    list_indexes: Option<Vec<usize>>,
) -> PyResult<(bool, Py<PyAny>)> {
    let val = pyany_to_value(dict)?;
    let indexes = list_indexes.unwrap_or_default();
    // Release GIL for pure Rust search over serde_json::Value
    let result = py.detach(|| {
        octobot_commons::dict_util::find_nested_value(&val, key, &indexes)
    });
    match result {
        Some(found) => Ok((true, value_to_pyany(py, &found)?)),
        None => Ok((false, key.into_pyobject(py)?.into_any().unbind())),
    }
}

#[pyfunction]
#[pyo3(signature = (base, update, exception_list=None, logger=None))]
pub fn check_and_merge_values_from_reference(
    base: &Bound<'_, PyDict>,
    update: &Bound<'_, PyDict>,
    exception_list: Option<Vec<String>>,
    logger: Option<&Bound<'_, PyAny>>,
) -> PyResult<()> {
    let py = base.py();
    let mut base_val = pyany_to_value(base.as_any())?;
    let update_val = pyany_to_value(update.as_any())?;
    let exc_refs: Vec<&str> = exception_list
        .as_ref()
        .map(|e| e.iter().map(String::as_str).collect())
        .unwrap_or_default();
    let _ = logger; // logger wiring deferred; no-op for now
    // Release GIL for pure Rust merge work
    py.detach(|| {
        octobot_commons::dict_util::check_and_merge_values_from_reference(
            &mut base_val,
            &update_val,
            &exc_refs,
            None,
        );
    });
    // Write back merged values into base dict
    if let Value::Object(map) = &base_val {
        base.clear();
        for (k, v) in map {
            base.set_item(k, value_to_pyany(py, v)?)?;
        }
    }
    Ok(())
}

#[pyfunction]
pub fn contains_each_element(
    py: Python<'_>,
    dict: &Bound<'_, PyAny>,
    expected: &Bound<'_, PyAny>,
) -> PyResult<bool> {
    let dict_val = pyany_to_value(dict)?;
    let expected_val = pyany_to_value(expected)?;
    // Release GIL for pure Rust comparison
    Ok(py.detach(|| {
        octobot_commons::dict_util::contains_each_element(&dict_val, &expected_val)
    }))
}

#[pyfunction]
#[pyo3(signature = (base, update, list_indexes=None, ignore_lists=false))]
pub fn nested_update_dict<'py>(
    base: &Bound<'py, PyDict>,
    update: &Bound<'_, PyAny>,
    list_indexes: Option<Vec<usize>>,
    ignore_lists: bool,
) -> PyResult<Bound<'py, PyDict>> {
    let py = base.py();
    let mut base_val = pyany_to_value(base.as_any())?;
    let update_val = pyany_to_value(update)?;
    let indexes = list_indexes.unwrap_or_default();
    // Release GIL for pure Rust dict merge
    py.detach(|| {
        octobot_commons::dict_util::nested_update_dict(
            &mut base_val,
            &update_val,
            &indexes,
            ignore_lists,
        );
    });
    if let Value::Object(map) = &base_val {
        base.clear();
        for (k, v) in map {
            base.set_item(k, value_to_pyany(py, v)?)?;
        }
    }
    Ok(base.clone())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_nested_value, m)?)?;
    m.add_function(wrap_pyfunction!(check_and_merge_values_from_reference, m)?)?;
    m.add_function(wrap_pyfunction!(contains_each_element, m)?)?;
    m.add_function(wrap_pyfunction!(nested_update_dict, m)?)?;
    Ok(())
}
