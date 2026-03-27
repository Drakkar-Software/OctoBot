use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (time_format=None, local_timezone=true))]
pub fn get_now_time(time_format: Option<&str>, local_timezone: bool) -> String {
    octobot_commons::timestamp_util::get_now_time(time_format, local_timezone)
}

#[pyfunction]
#[pyo3(signature = (timestamp, time_format=None, local_timezone=false))]
pub fn convert_timestamp_to_datetime(
    timestamp: f64,
    time_format: Option<&str>,
    local_timezone: bool,
) -> String {
    octobot_commons::timestamp_util::convert_timestamp_to_datetime(
        timestamp,
        time_format,
        local_timezone,
    )
}

#[pyfunction]
#[pyo3(signature = (timestamps, time_format=None, local_timezone=false))]
pub fn convert_timestamps_to_datetime(
    timestamps: Vec<f64>,
    time_format: Option<&str>,
    local_timezone: bool,
) -> Vec<String> {
    octobot_commons::timestamp_util::convert_timestamps_to_datetime(
        &timestamps,
        time_format,
        local_timezone,
    )
}

#[pyfunction]
pub fn is_valid_timestamp(timestamp: f64) -> bool {
    octobot_commons::timestamp_util::is_valid_timestamp(timestamp)
}

#[pyfunction]
#[pyo3(signature = (date_time_str, date_time_format, local_timezone=true))]
pub fn datetime_to_timestamp(
    date_time_str: &str,
    date_time_format: &str,
    local_timezone: bool,
) -> f64 {
    octobot_commons::timestamp_util::datetime_to_timestamp(
        date_time_str,
        date_time_format,
        local_timezone,
    )
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_now_time, m)?)?;
    m.add_function(wrap_pyfunction!(convert_timestamp_to_datetime, m)?)?;
    m.add_function(wrap_pyfunction!(convert_timestamps_to_datetime, m)?)?;
    m.add_function(wrap_pyfunction!(is_valid_timestamp, m)?)?;
    m.add_function(wrap_pyfunction!(datetime_to_timestamp, m)?)?;
    Ok(())
}
