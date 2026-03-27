use pyo3::prelude::*;
use pyo3::types::PyList;

#[pyfunction]
pub fn flatten_list<'py>(list_to_flatten: &Bound<'py, PyList>) -> PyResult<Py<PyList>> {
    let py = list_to_flatten.py();
    let result = PyList::empty(py);
    for item in list_to_flatten.iter() {
        if let Ok(sublist) = item.cast::<PyList>() {
            for sub_item in sublist.iter() {
                result.append(sub_item)?;
            }
        } else {
            result.append(item)?;
        }
    }
    Ok(result.into())
}

#[pyfunction]
pub fn deduplicate<'py>(elements: &Bound<'py, PyList>) -> PyResult<Py<PyList>> {
    let py = elements.py();
    let result = PyList::empty(py);
    let seen = pyo3::types::PySet::empty(py)?;
    for item in elements.iter() {
        let hash_result = item.hash();
        if let Ok(h) = hash_result {
            if !seen.contains(h)? {
                seen.add(h)?;
                result.append(item)?;
            }
        } else {
            // unhashable — always include
            result.append(item)?;
        }
    }
    Ok(result.into())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(flatten_list, m)?)?;
    m.add_function(wrap_pyfunction!(deduplicate, m)?)?;
    Ok(())
}
