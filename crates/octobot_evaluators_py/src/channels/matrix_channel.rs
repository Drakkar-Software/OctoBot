use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::PyClassInitializer;

use async_channel::enums::ChannelConsumerPriorityLevels;
use async_channel::constants::CHANNEL_WILDCARD;
use pyo3_bridge::async_methods::await_py_method0;

use crate::channels::evaluator_channel::{
    PyEvaluatorChannel, PyEvaluatorChannelConsumer,
    PyEvaluatorChannelProducer, PyEvaluatorChannelSupervisedConsumer,
};
use async_channel_py::channels::channel::PyChannel;
use async_channel_py::consumer::{PyConsumer, PySupervisedConsumer};
use async_channel_py::producer::PyProducer;

// ---------------------------------------------------------------------------
// Consumer / Producer marker subclasses
// ---------------------------------------------------------------------------

#[pyclass(
    name = "MatrixChannelConsumer",
    extends = PyEvaluatorChannelConsumer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyMatrixChannelConsumer;

#[pymethods]
impl PyMatrixChannelConsumer {
    #[new]
    #[pyo3(signature = (callback=None, size=None, priority_level=None))]
    fn new(
        py: Python<'_>,
        callback: Option<Py<PyAny>>,
        size: Option<i64>,
        priority_level: Option<i64>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let base = PyConsumer::create(py, callback, size, priority_level)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(PyEvaluatorChannelConsumer)
            .add_subclass(Self))
    }
}

#[pyclass(
    name = "MatrixChannelSupervisedConsumer",
    extends = PyEvaluatorChannelSupervisedConsumer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyMatrixChannelSupervisedConsumer;

#[pymethods]
impl PyMatrixChannelSupervisedConsumer {
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
            .add_subclass(PyEvaluatorChannelSupervisedConsumer)
            .add_subclass(Self))
    }
}

#[pyclass(
    name = "MatrixChannelProducer",
    extends = PyEvaluatorChannelProducer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyMatrixChannelProducer;

#[pymethods]
impl PyMatrixChannelProducer {
    #[new]
    fn new(py: Python<'_>, channel: Py<PyAny>) -> PyResult<PyClassInitializer<Self>> {
        let base = PyProducer::create(py, channel)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(PyEvaluatorChannelProducer)
            .add_subclass(Self))
    }

    /// Send a matrix message to filtered consumers.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        matrix_id,
        evaluator_name,
        evaluator_type,
        eval_note,
        eval_note_type = None,
        eval_note_description = None,
        eval_note_metadata = None,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None,
        origin_consumer = None
    ))]
    fn send<'py>(
        slf: &Bound<'py, Self>,
        matrix_id: String,
        evaluator_name: String,
        evaluator_type: Py<PyAny>,
        eval_note: Py<PyAny>,
        eval_note_type: Option<Py<PyAny>>,
        eval_note_description: Option<Py<PyAny>>,
        eval_note_metadata: Option<Py<PyAny>>,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<Py<PyAny>>,
        origin_consumer: Option<Py<PyAny>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let cryptocurrency = cryptocurrency.unwrap_or_else(|| wc.clone());
        let symbol = symbol.unwrap_or_else(|| wc.clone());

        // Resolve default eval_note_type to Python `float`
        let eval_note_type = eval_note_type.unwrap_or_else(|| {
            Python::attach(|py| {
                py.eval(pyo3::ffi::c_str!("float"), None, None)
                    .map(|v| v.unbind())
                    .unwrap_or_else(|_| py.None())
            })
        });

        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumers: Vec<Py<PyAny>> = Python::attach(|py| -> PyResult<Vec<Py<PyAny>>> {
                let ch = producer.bind(py).getattr("channel")?;
                let kwargs = PyDict::new(py);
                kwargs.set_item("matrix_id", &matrix_id)?;
                kwargs.set_item("cryptocurrency", &cryptocurrency)?;
                kwargs.set_item("symbol", &symbol)?;
                kwargs.set_item("time_frame", time_frame.as_ref().map(|t| t.bind(py)))?;
                kwargs.set_item("evaluator_type", evaluator_type.bind(py))?;
                kwargs.set_item("evaluator_name", &evaluator_name)?;
                kwargs.set_item("exchange_name", exchange_name.as_deref())?;
                kwargs.set_item("origin_consumer", origin_consumer.as_ref().map(|c| c.bind(py)))?;
                let list = ch.call_method("get_filtered_consumers", (), Some(&kwargs))?;
                list.try_iter()?
                    .map(|c| Ok(c?.unbind()))
                    .collect::<PyResult<Vec<_>>>()
            })?;

            for consumer in consumers {
                let fut = Python::attach(|py| -> PyResult<_> {
                    let msg = PyDict::new(py);
                    msg.set_item("matrix_id", &matrix_id)?;
                    msg.set_item("evaluator_name", &evaluator_name)?;
                    msg.set_item("evaluator_type", evaluator_type.bind(py))?;
                    msg.set_item("eval_note", eval_note.bind(py))?;
                    msg.set_item("eval_note_type", eval_note_type.bind(py))?;
                    msg.set_item("eval_note_description", eval_note_description.as_ref().map(|d| d.bind(py)))?;
                    msg.set_item("eval_note_metadata", eval_note_metadata.as_ref().map(|m| m.bind(py)))?;
                    msg.set_item("exchange_name", exchange_name.as_deref())?;
                    msg.set_item("cryptocurrency", &cryptocurrency)?;
                    msg.set_item("symbol", &symbol)?;
                    msg.set_item("time_frame", time_frame.as_ref().map(|t| t.bind(py)))?;
                    let q = consumer.bind(py).getattr("queue")?;
                    let coro = q.call_method1("put", (msg,))?;
                    pyo3_async_runtimes::tokio::into_future(coro)
                })?;
                fut.await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }

    /// Send an eval note: store in matrix then dispatch.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        matrix_id,
        evaluator_name,
        evaluator_type,
        eval_note,
        eval_note_type,
        eval_note_description = None,
        eval_note_metadata = None,
        eval_time = 0.0,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None,
        origin_consumer = None,
        notify = true
    ))]
    fn send_eval_note<'py>(
        slf: &Bound<'py, Self>,
        matrix_id: String,
        evaluator_name: String,
        evaluator_type: Py<PyAny>,
        eval_note: Py<PyAny>,
        eval_note_type: Py<PyAny>,
        eval_note_description: Option<Py<PyAny>>,
        eval_note_metadata: Option<Py<PyAny>>,
        eval_time: f64,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<Py<PyAny>>,
        origin_consumer: Option<Py<PyAny>>,
        notify: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producer: Py<PyAny> = slf.as_any().clone().unbind();

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // 1. Store in matrix via set_tentacle_value
            Python::attach(|py| -> PyResult<()> {
                let m = py.import("octobot_evaluators_rs._core")?;
                let path_kwargs = PyDict::new(py);
                path_kwargs.set_item("exchange_name", exchange_name.as_deref())?;
                path_kwargs.set_item("tentacle_type", evaluator_type.bind(py))?;
                path_kwargs.set_item("tentacle_name", &evaluator_name)?;
                path_kwargs.set_item("cryptocurrency", cryptocurrency.as_deref())?;
                path_kwargs.set_item("symbol", symbol.as_deref())?;
                path_kwargs.set_item("time_frame", time_frame.as_ref().map(|t| t.bind(py)))?;
                let path = m.call_method(
                    "get_matrix_default_value_path",
                    (),
                    Some(&path_kwargs),
                )?;
                let kwargs = PyDict::new(py);
                kwargs.set_item("matrix_id", &matrix_id)?;
                kwargs.set_item("tentacle_type", eval_note_type.bind(py))?;
                kwargs.set_item("tentacle_value", eval_note.bind(py))?;
                kwargs.set_item("timestamp", eval_time)?;
                kwargs.set_item("tentacle_path", path)?;
                kwargs.set_item("description", eval_note_description.as_ref().map(|d| d.bind(py)))?;
                kwargs.set_item("metadata", eval_note_metadata.as_ref().map(|m| m.bind(py)))?;
                m.call_method("set_tentacle_value", (), Some(&kwargs))?;
                Ok(())
            })?;

            // 2. Notify consumers if requested
            if notify {
                let fut = Python::attach(|py| -> PyResult<_> {
                    let kwargs = PyDict::new(py);
                    kwargs.set_item("matrix_id", &matrix_id)?;
                    kwargs.set_item("evaluator_name", &evaluator_name)?;
                    kwargs.set_item("evaluator_type", evaluator_type.bind(py))?;
                    kwargs.set_item("eval_note", eval_note.bind(py))?;
                    kwargs.set_item("eval_note_type", eval_note_type.bind(py))?;
                    kwargs.set_item("eval_note_description", eval_note_description.as_ref().map(|d| d.bind(py)))?;
                    kwargs.set_item("eval_note_metadata", eval_note_metadata.as_ref().map(|m| m.bind(py)))?;
                    kwargs.set_item("exchange_name", exchange_name.as_deref())?;
                    kwargs.set_item("cryptocurrency", cryptocurrency.as_deref())?;
                    kwargs.set_item("symbol", symbol.as_deref())?;
                    kwargs.set_item("time_frame", time_frame.as_ref().map(|t| t.bind(py)))?;
                    kwargs.set_item("origin_consumer", origin_consumer.as_ref().map(|c| c.bind(py)))?;
                    let coro = producer.bind(py).call_method("send", (), Some(&kwargs))?;
                    pyo3_async_runtimes::tokio::into_future(coro)
                })?;
                fut.await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }
}

// ---------------------------------------------------------------------------
// MatrixChannel
// ---------------------------------------------------------------------------

#[pyclass(
    name = "MatrixChannel",
    extends = PyEvaluatorChannel,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyMatrixChannel;

#[pymethods]
impl PyMatrixChannel {
    #[classattr]
    const FILTER_SIZE: usize = 1;
    #[classattr]
    const MATRIX_ID_KEY: &'static str = "matrix_id";
    #[classattr]
    const CRYPTOCURRENCY_KEY: &'static str = "cryptocurrency";
    #[classattr]
    const SYMBOL_KEY: &'static str = "symbol";
    #[classattr]
    const TIME_FRAME_KEY: &'static str = "time_frame";
    #[classattr]
    const EVALUATOR_TYPE_KEY: &'static str = "evaluator_type";
    #[classattr]
    const EXCHANGE_NAME_KEY: &'static str = "exchange_name";
    #[classattr]
    const EVALUATOR_NAME_KEY: &'static str = "evaluator_name";

    #[new]
    fn new(py: Python<'_>, matrix_id: String) -> PyResult<PyClassInitializer<Self>> {
        let base = PyChannel::create(py)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(PyEvaluatorChannel { matrix_id })
            .add_subclass(Self))
    }

    /// Create a new consumer with matrix filter keyword arguments.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        callback,
        size = 0,
        priority_level = None,
        matrix_id = None,
        cryptocurrency = None,
        symbol = None,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        time_frame = None,
        supervised = false
    ))]
    fn new_consumer<'py>(
        slf: &Bound<'py, Self>,
        callback: Py<PyAny>,
        size: i64,
        priority_level: Option<i64>,
        matrix_id: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        time_frame: Option<String>,
        supervised: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let priority = priority_level
            .unwrap_or(ChannelConsumerPriorityLevels::Medium as i64);
        let matrix_id = matrix_id.unwrap_or_else(|| wc.clone());
        let cryptocurrency = cryptocurrency.unwrap_or_else(|| wc.clone());
        let symbol = symbol.unwrap_or_else(|| wc.clone());
        let evaluator_name = evaluator_name.unwrap_or_else(|| wc.clone());
        let evaluator_type = evaluator_type.unwrap_or_else(|| wc.clone());
        let exchange_name = exchange_name.unwrap_or_else(|| wc.clone());
        let time_frame = time_frame.unwrap_or_else(|| wc.clone());

        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumer: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
                if supervised {
                    let c = Py::new(
                        py,
                        PyMatrixChannelSupervisedConsumer::new(py, Some(callback), Some(size), Some(priority))?,
                    )?;
                    Ok(c.into_any())
                } else {
                    let c = Py::new(
                        py,
                        PyMatrixChannelConsumer::new(py, Some(callback), Some(size), Some(priority))?,
                    )?;
                    Ok(c.into_any())
                }
            })?;
            let fut = Python::attach(|py| -> PyResult<_> {
                let kwargs = PyDict::new(py);
                kwargs.set_item("matrix_id", &matrix_id)?;
                kwargs.set_item("cryptocurrency", &cryptocurrency)?;
                kwargs.set_item("symbol", &symbol)?;
                kwargs.set_item("evaluator_name", &evaluator_name)?;
                kwargs.set_item("evaluator_type", &evaluator_type)?;
                kwargs.set_item("exchange_name", &exchange_name)?;
                kwargs.set_item("time_frame", &time_frame)?;
                let coro = channel
                    .bind(py)
                    .call_method("_add_new_consumer_and_run", (consumer.bind(py),), Some(&kwargs))?;
                pyo3_async_runtimes::tokio::into_future(coro)
            })?;
            fut.await?;
            Ok(consumer)
        })
    }

    /// Return filtered consumers using matrix filter keys.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        matrix_id = None,
        cryptocurrency = None,
        symbol = None,
        evaluator_type = None,
        time_frame = None,
        evaluator_name = None,
        exchange_name = None,
        origin_consumer = None
    ))]
    fn get_filtered_consumers(
        slf: &Bound<'_, Self>,
        matrix_id: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        evaluator_type: Option<String>,
        time_frame: Option<String>,
        evaluator_name: Option<String>,
        exchange_name: Option<String>,
        origin_consumer: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let filters = PyDict::new(py);
        filters.set_item("matrix_id", matrix_id.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("cryptocurrency", cryptocurrency.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("symbol", symbol.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("time_frame", time_frame.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_type", evaluator_type.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_name", evaluator_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("exchange_name", exchange_name.unwrap_or_else(|| wc.clone()))?;
        let result = slf.as_any().call_method1(
            "get_consumer_from_filters",
            (filters, origin_consumer),
        )?;
        result
            .try_iter()?
            .map(|c| Ok(c?.unbind()))
            .collect::<PyResult<Vec<_>>>()
    }

    /// Override _add_new_consumer_and_run with matrix filter keys.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        consumer,
        matrix_id = None,
        cryptocurrency = None,
        symbol = None,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        time_frame = None
    ))]
    fn _add_new_consumer_and_run<'py>(
        slf: &Bound<'py, Self>,
        consumer: &Bound<'py, PyAny>,
        matrix_id: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        time_frame: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let filters = PyDict::new(py);
        filters.set_item("matrix_id", matrix_id.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("cryptocurrency", cryptocurrency.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("symbol", symbol.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("time_frame", time_frame.as_deref().unwrap_or(&wc))?;
        filters.set_item("evaluator_name", evaluator_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("exchange_name", exchange_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_type", evaluator_type.unwrap_or_else(|| wc.clone()))?;

        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        let consumer_ref: Py<PyAny> = consumer.clone().unbind();
        let logger: Py<PyAny> = slf.as_any().getattr("logger")?.unbind();
        let filters_owned: Py<PyDict> = filters.clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            Python::attach(|py| -> PyResult<()> {
                channel.bind(py).call_method1(
                    "add_new_consumer",
                    (consumer_ref.bind(py), filters_owned.bind(py)),
                )?;
                Ok(())
            })?;
            await_py_method0(&consumer_ref, "run").await?;
            // Log consumer start
            Python::attach(|py| -> PyResult<()> {
                let filters_bound = filters_owned.bind(py);
                let get = |k: &str| -> String {
                    filters_bound
                        .get_item(k)
                        .ok()
                        .flatten()
                        .map(|v| v.to_string())
                        .unwrap_or_default()
                };
                let msg = format!(
                    "Consumer started for : [matrix_id={}, cryptocurrency={}, symbol={}, time_frame={}, evaluator_name={}, exchange_name={}, evaluator_type={}]",
                    get("matrix_id"), get("cryptocurrency"), get("symbol"),
                    get("time_frame"), get("evaluator_name"), get("exchange_name"),
                    get("evaluator_type"),
                );
                logger.bind(py).call_method1("debug", (msg,))?;
                Ok(())
            })?;
            Ok(Python::attach(|py| py.None()))
        })
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyMatrixChannelConsumer>()?;
    m.add_class::<PyMatrixChannelSupervisedConsumer>()?;
    m.add_class::<PyMatrixChannelProducer>()?;
    m.add_class::<PyMatrixChannel>()?;
    let mc = m.getattr("MatrixChannel")?;
    mc.setattr(
        "PRODUCER_CLASS",
        m.getattr("MatrixChannelProducer")?,
    )?;
    mc.setattr(
        "CONSUMER_CLASS",
        m.getattr("MatrixChannelConsumer")?,
    )?;
    Ok(())
}
