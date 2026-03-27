use pyo3::prelude::*;

pub const UNSET_EVAL_TYPE: &str = "unset_eval_type_param";

/// Bridge-only: uses Python `is not` identity semantics.
#[pyfunction]
#[pyo3(signature = (eval_note, eval_type=None, expected_eval_type=None, eval_time=None, expiry_delay=None, current_time=None))]
pub fn check_valid_eval_note(
    py: Python<'_>,
    eval_note: &Bound<'_, PyAny>,
    eval_type: Option<&Bound<'_, PyAny>>,
    expected_eval_type: Option<&Bound<'_, PyAny>>,
    eval_time: Option<f64>,
    expiry_delay: Option<f64>,
    current_time: Option<f64>,
) -> PyResult<bool> {
    let unset = UNSET_EVAL_TYPE.into_pyobject(py)?;

    // Default eval_type to UNSET_EVAL_TYPE
    let eval_type_obj = match eval_type {
        Some(et) => et.clone(),
        None => unset.clone().into_any(),
    };

    // If eval_type != UNSET and (eval_type != expected or expected is None)
    if !eval_type_obj.eq(&unset)? {
        match expected_eval_type {
            None => return Ok(false),
            Some(expected) => {
                if !eval_type_obj.eq(expected)? {
                    return Ok(false);
                }
            }
        }
    }

    // eval_note is not None
    if eval_note.is_none() {
        return Ok(false);
    }

    // eval_note is not START_PENDING_EVAL_NOTE (identity check)
    let start_pending = octobot_commons::constants::START_PENDING_EVAL_NOTE.into_pyobject(py)?;
    if eval_note.is(&start_pending) {
        return Ok(false);
    }

    // Time check
    if let (Some(et), Some(ed), Some(ct)) = (eval_time, expiry_delay, current_time) {
        if et + ed - ct <= 0.0 {
            return Ok(false);
        }
    }

    Ok(true)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("UNSET_EVAL_TYPE", UNSET_EVAL_TYPE)?;
    m.add_function(wrap_pyfunction!(check_valid_eval_note, m)?)?;
    Ok(())
}
