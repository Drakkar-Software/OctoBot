use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

use octobot_commons::enums::TimeFrames;
use octobot_commons::time_frame_manager;

#[pyfunction]
#[pyo3(signature = (time_frames, reverse=false))]
pub fn sort_time_frames(time_frames: Vec<String>, reverse: bool) -> PyResult<Vec<String>> {
    let mut parsed: Vec<TimeFrames> = Vec::new();
    for s in &time_frames {
        parsed.push(
            TimeFrames::from_value(s)
                .ok_or_else(|| PyValueError::new_err(format!("Unknown time frame: {s}")))?,
        );
    }
    let sorted = time_frame_manager::sort_time_frames(&parsed, reverse);
    Ok(sorted.into_iter().map(|tf| tf.value().to_string()).collect())
}

#[pyfunction]
#[pyo3(signature = (time_frames, min_time_frame=None))]
pub fn find_min_time_frame(
    time_frames: Vec<String>,
    min_time_frame: Option<&str>,
) -> PyResult<Option<String>> {
    let mut parsed: Vec<TimeFrames> = Vec::new();
    for s in &time_frames {
        parsed.push(
            TimeFrames::from_value(s)
                .ok_or_else(|| PyValueError::new_err(format!("Unknown time frame: {s}")))?,
        );
    }
    let min_tf = min_time_frame
        .map(|s| {
            TimeFrames::from_value(s)
                .ok_or_else(|| PyValueError::new_err(format!("Unknown time frame: {s}")))
        })
        .transpose()?;
    Ok(time_frame_manager::find_min_time_frame(&parsed, min_tf)
        .map(|tf| tf.value().to_string()))
}

#[pyfunction]
pub fn is_time_frame(value: &str) -> bool {
    time_frame_manager::is_time_frame(value)
}

#[pyfunction]
pub fn parse_time_frames(strings: Vec<String>) -> (Vec<String>, Vec<String>) {
    let refs: Vec<&str> = strings.iter().map(String::as_str).collect();
    let (valid, invalid) = time_frame_manager::parse_time_frames(&refs);
    (
        valid.into_iter().map(|tf| tf.value().to_string()).collect(),
        invalid,
    )
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sort_time_frames, m)?)?;
    m.add_function(wrap_pyfunction!(find_min_time_frame, m)?)?;
    m.add_function(wrap_pyfunction!(is_time_frame, m)?)?;
    m.add_function(wrap_pyfunction!(parse_time_frames, m)?)?;
    Ok(())
}
