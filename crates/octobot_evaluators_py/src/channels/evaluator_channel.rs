use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::PyClassInitializer;

use async_channel::enums::ChannelConsumerPriorityLevels;
use async_channel_py::channels::channel::PyChannel;
use async_channel_py::consumer::{PyConsumer, PySupervisedConsumer};
use async_channel_py::producer::PyProducer;

// ---------------------------------------------------------------------------
// Consumer / Producer marker subclasses
// ---------------------------------------------------------------------------

#[pyclass(
    name = "EvaluatorChannelConsumer",
    extends = PyConsumer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorChannelConsumer;

#[pymethods]
impl PyEvaluatorChannelConsumer {
    #[new]
    #[pyo3(signature = (callback=None, size=None, priority_level=None))]
    fn new(
        py: Python<'_>,
        callback: Option<Py<PyAny>>,
        size: Option<i64>,
        priority_level: Option<i64>,
    ) -> PyResult<(Self, PyConsumer)> {
        Ok((Self, PyConsumer::create(py, callback, size, priority_level)?))
    }
}

impl PyEvaluatorChannelConsumer {
    pub fn create(
        py: Python<'_>,
        callback: Option<Py<PyAny>>,
        size: Option<i64>,
        priority_level: Option<i64>,
    ) -> PyResult<(Self, PyConsumer)> {
        Self::new(py, callback, size, priority_level)
    }
}

#[pyclass(
    name = "EvaluatorChannelSupervisedConsumer",
    extends = PySupervisedConsumer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorChannelSupervisedConsumer;

#[pymethods]
impl PyEvaluatorChannelSupervisedConsumer {
    #[new]
    #[pyo3(signature = (callback=None, size=None, priority_level=None))]
    fn new(
        py: Python<'_>,
        callback: Option<Py<PyAny>>,
        size: Option<i64>,
        priority_level: Option<i64>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let base = PyConsumer::create(py, callback, size, priority_level)?;
        let sup = PySupervisedConsumer::create_part(py)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(sup)
            .add_subclass(Self))
    }
}

impl PyEvaluatorChannelSupervisedConsumer {
    pub fn create(
        py: Python<'_>,
        callback: Option<Py<PyAny>>,
        size: Option<i64>,
        priority_level: Option<i64>,
    ) -> PyResult<PyClassInitializer<Self>> {
        Self::new(py, callback, size, priority_level)
    }
}

#[pyclass(
    name = "EvaluatorChannelProducer",
    extends = PyProducer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorChannelProducer;

#[pymethods]
impl PyEvaluatorChannelProducer {
    #[new]
    fn new(py: Python<'_>, channel: Py<PyAny>) -> PyResult<(Self, PyProducer)> {
        Ok((Self, PyProducer::create(py, channel)?))
    }
}

impl PyEvaluatorChannelProducer {
    pub fn create(py: Python<'_>, channel: Py<PyAny>) -> PyResult<(Self, PyProducer)> {
        Self::new(py, channel)
    }
}

// ---------------------------------------------------------------------------
// EvaluatorChannel
// ---------------------------------------------------------------------------

#[pyclass(
    name = "EvaluatorChannel",
    extends = PyChannel,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorChannel {
    #[pyo3(get, set)]
    pub matrix_id: String,
}

#[pymethods]
impl PyEvaluatorChannel {
    #[classattr]
    const DEFAULT_PRIORITY_LEVEL: i64 = ChannelConsumerPriorityLevels::Medium as i64;

    #[new]
    fn new(py: Python<'_>, matrix_id: String) -> PyResult<(Self, PyChannel)> {
        let base = PyChannel::create(py)?;
        Ok((Self { matrix_id }, base))
    }

    /// Override: exclude `origin_consumer` from the filtered list.
    #[pyo3(signature = (consumer_filters, origin_consumer=None))]
    fn get_consumer_from_filters(
        slf: &Bound<'_, Self>,
        consumer_filters: &Bound<'_, PyDict>,
        origin_consumer: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        // Call parent filter_consumers (public wrapper)
        let base_results: Vec<Py<PyAny>> =
            PyChannel::filter_consumers(slf.as_any().cast()?, consumer_filters)?;
        match origin_consumer {
            Some(origin) => {
                let py = slf.py();
                Ok(base_results
                    .into_iter()
                    .filter(|c| !c.bind(py).is(origin))
                    .collect())
            }
            None => Ok(base_results),
        }
    }
}

impl PyEvaluatorChannel {
    pub fn create(py: Python<'_>, matrix_id: String) -> PyResult<(Self, PyChannel)> {
        Self::new(py, matrix_id)
    }
}

// ---------------------------------------------------------------------------
// Module-level functions
// ---------------------------------------------------------------------------

/// Register a channel under `name` in the ChannelInstances singleton,
/// keyed by `chan.matrix_id`.
#[pyfunction]
#[pyo3(signature = (chan, name))]
pub fn set_chan(py: Python<'_>, chan: &Bound<'_, PyAny>, name: String) -> PyResult<()> {
    let ci = py
        .import("async_channel_rs._core")?
        .getattr("ChannelInstances")?
        .call_method0("instance")?;
    let chs = ci.getattr("channels")?;
    let matrix_id = chan.getattr("matrix_id")?;
    let chan_name: String = if name.is_empty() {
        chan.call_method0("get_name")?.extract()?
    } else {
        name
    };

    if !chs
        .call_method1("__contains__", (&matrix_id,))?
        .extract::<bool>()?
    {
        chs.set_item(&matrix_id, PyDict::new(py))?;
    }
    let d = chs.get_item(&matrix_id)?;
    if !d
        .call_method1("__contains__", (&chan_name,))?
        .extract::<bool>()?
    {
        d.set_item(&chan_name, chan)?;
    } else {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Channel {} already exists.",
            chan_name
        )));
    }
    Ok(())
}

/// Return the channels dict for the given `matrix_id`.
#[pyfunction]
pub fn get_evaluator_channels(py: Python<'_>, matrix_id: &str) -> PyResult<Py<PyAny>> {
    let ci = py
        .import("async_channel_rs._core")?
        .getattr("ChannelInstances")?
        .call_method0("instance")?;
    let chs = ci.getattr("channels")?;
    if chs
        .call_method1("__contains__", (matrix_id,))?
        .extract::<bool>()?
    {
        Ok(chs.get_item(matrix_id)?.unbind())
    } else {
        Err(pyo3::exceptions::PyKeyError::new_err(format!(
            "Channels not found with matrix_id: {}",
            matrix_id
        )))
    }
}

/// Remove the channel container for `matrix_id`.
#[pyfunction]
pub fn del_evaluator_channel_container(py: Python<'_>, matrix_id: &str) -> PyResult<()> {
    let ci = py
        .import("async_channel_rs._core")?
        .getattr("ChannelInstances")?
        .call_method0("instance")?;
    ci.getattr("channels")?
        .call_method1("pop", (matrix_id, py.None()))?;
    Ok(())
}

/// Get a single channel by name within `matrix_id`.
#[pyfunction]
pub fn get_chan(py: Python<'_>, chan_name: &str, matrix_id: &str) -> PyResult<Py<PyAny>> {
    let ci = py
        .import("async_channel_rs._core")?
        .getattr("ChannelInstances")?
        .call_method0("instance")?;
    let msg = format!(
        "Channel {} not found with matrix_id: {}",
        chan_name, matrix_id
    );
    let d = ci
        .getattr("channels")?
        .get_item(matrix_id)
        .map_err(|_| pyo3::exceptions::PyKeyError::new_err(msg.clone()))?;
    d.get_item(chan_name)
        .map(|v| v.unbind())
        .map_err(|_| pyo3::exceptions::PyKeyError::new_err(msg))
}

/// Remove a single channel by name within `matrix_id`.
#[pyfunction]
pub fn del_chan(py: Python<'_>, chan_name: &str, matrix_id: &str) -> PyResult<()> {
    let ci = py
        .import("async_channel_rs._core")?
        .getattr("ChannelInstances")?
        .call_method0("instance")?;
    let chs = ci.getattr("channels")?;
    if chs
        .call_method1("__contains__", (matrix_id,))?
        .extract::<bool>()?
    {
        chs.get_item(matrix_id)?
            .call_method1("pop", (chan_name, py.None()))?;
    } else {
        let logger = py
            .import("octobot_commons.logging")?
            .call_method1("get_logger", ("EvaluatorChannel",))?;
        logger.call_method1(
            "warning",
            (format!(
                "Can't del chan {} with matrix_id: {}",
                chan_name, matrix_id
            ),),
        )?;
    }
    Ok(())
}

/// Async helper: trigger TA re-evaluation with updated data.
#[allow(clippy::too_many_arguments)]
#[pyfunction]
#[pyo3(signature = (matrix_id, evaluator_name, evaluator_type, exchange_name, cryptocurrency, symbol, exchange_id, time_frames))]
fn trigger_technical_evaluators_re_evaluation_with_updated_data<'py>(
    py: Python<'py>,
    matrix_id: String,
    evaluator_name: String,
    evaluator_type: String,
    exchange_name: String,
    cryptocurrency: String,
    symbol: String,
    exchange_id: String,
    time_frames: Py<PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let wc = async_channel::constants::CHANNEL_WILDCARD.to_string();
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        // First: send RESET_EVALUATION
        let chan: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
            let m = py.import("octobot_evaluators_rs._core")?;
            let c = m.call_method1(
                "get_chan",
                (
                    octobot_evaluators::constants::EVALUATORS_CHANNEL,
                    &matrix_id,
                ),
            )?;
            Ok(c.unbind())
        })?;
        let producer: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
            let p = chan.bind(py).call_method0("get_internal_producer")?;
            Ok(p.unbind())
        })?;

        // Build reset data dict
        let fut = Python::attach(|py| -> PyResult<_> {
            let data = PyDict::new(py);
            data.set_item(
                octobot_evaluators::constants::EVALUATOR_CHANNEL_DATA_ACTION,
                octobot_evaluators::constants::RESET_EVALUATION,
            )?;
            data.set_item(
                octobot_evaluators::constants::EVALUATOR_CHANNEL_DATA_TIME_FRAMES,
                time_frames.bind(py),
            )?;
            let kwargs = PyDict::new(py);
            kwargs.set_item("matrix_id", &matrix_id)?;
            kwargs.set_item("data", data)?;
            kwargs.set_item("evaluator_name", &evaluator_name)?;
            kwargs.set_item("evaluator_type", &evaluator_type)?;
            kwargs.set_item("exchange_name", &exchange_name)?;
            kwargs.set_item("cryptocurrency", &cryptocurrency)?;
            kwargs.set_item("symbol", &symbol)?;
            kwargs.set_item("time_frame", &wc)?;
            let coro = producer.bind(py).call_method("send", (), Some(&kwargs))?;
            pyo3_async_runtimes::tokio::into_future(coro)
        })?;
        fut.await?;

        // Second: send TA_RE_EVALUATION_TRIGGER_UPDATED_DATA
        let fut2 = Python::attach(|py| -> PyResult<_> {
            let data = PyDict::new(py);
            data.set_item(
                octobot_evaluators::constants::EVALUATOR_CHANNEL_DATA_ACTION,
                octobot_evaluators::constants::TA_RE_EVALUATION_TRIGGER_UPDATED_DATA,
            )?;
            data.set_item(
                octobot_evaluators::constants::EVALUATOR_CHANNEL_DATA_EXCHANGE_ID,
                &exchange_id,
            )?;
            data.set_item(
                octobot_evaluators::constants::EVALUATOR_CHANNEL_DATA_TIME_FRAMES,
                time_frames.bind(py),
            )?;
            let kwargs = PyDict::new(py);
            kwargs.set_item("matrix_id", &matrix_id)?;
            kwargs.set_item("data", data)?;
            kwargs.set_item("evaluator_name", &evaluator_name)?;
            kwargs.set_item("evaluator_type", &evaluator_type)?;
            kwargs.set_item("exchange_name", &exchange_name)?;
            kwargs.set_item("cryptocurrency", &cryptocurrency)?;
            kwargs.set_item("symbol", &symbol)?;
            kwargs.set_item("time_frame", &wc)?;
            let coro = producer.bind(py).call_method("send", (), Some(&kwargs))?;
            pyo3_async_runtimes::tokio::into_future(coro)
        })?;
        fut2.await?;

        Ok(Python::attach(|py| py.None()))
    })
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyEvaluatorChannelConsumer>()?;
    m.add_class::<PyEvaluatorChannelSupervisedConsumer>()?;
    m.add_class::<PyEvaluatorChannelProducer>()?;
    m.add_class::<PyEvaluatorChannel>()?;
    // Set PRODUCER_CLASS and CONSUMER_CLASS on EvaluatorChannel
    let ec = m.getattr("EvaluatorChannel")?;
    ec.setattr(
        "PRODUCER_CLASS",
        m.getattr("EvaluatorChannelProducer")?,
    )?;
    ec.setattr(
        "CONSUMER_CLASS",
        m.getattr("EvaluatorChannelConsumer")?,
    )?;
    m.add_function(wrap_pyfunction!(set_chan, m)?)?;
    m.add_function(wrap_pyfunction!(get_evaluator_channels, m)?)?;
    m.add_function(wrap_pyfunction!(del_evaluator_channel_container, m)?)?;
    m.add_function(wrap_pyfunction!(get_chan, m)?)?;
    m.add_function(wrap_pyfunction!(del_chan, m)?)?;
    m.add_function(wrap_pyfunction!(
        trigger_technical_evaluators_re_evaluation_with_updated_data,
        m
    )?)?;
    Ok(())
}
