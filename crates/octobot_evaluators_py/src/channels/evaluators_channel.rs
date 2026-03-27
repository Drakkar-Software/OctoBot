use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::PyClassInitializer;

use async_channel::constants::CHANNEL_WILDCARD;
use async_channel::enums::ChannelConsumerPriorityLevels;
use pyo3_bridge::async_methods::await_py_method0;

use crate::channels::evaluator_channel::{
    PyEvaluatorChannel, PyEvaluatorChannelConsumer, PyEvaluatorChannelProducer,
};
use async_channel_py::channels::channel::PyChannel;
use async_channel_py::consumer::PyConsumer;
use async_channel_py::producer::PyProducer;

// ---------------------------------------------------------------------------
// Consumer / Producer subclasses
// ---------------------------------------------------------------------------

#[pyclass(
    name = "EvaluatorsChannelConsumer",
    extends = PyEvaluatorChannelConsumer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorsChannelConsumer;

#[pymethods]
impl PyEvaluatorsChannelConsumer {
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
    name = "EvaluatorsChannelProducer",
    extends = PyEvaluatorChannelProducer,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorsChannelProducer;

#[pymethods]
impl PyEvaluatorsChannelProducer {
    #[new]
    fn new(py: Python<'_>, channel: Py<PyAny>) -> PyResult<PyClassInitializer<Self>> {
        let base = PyProducer::create(py, channel)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(PyEvaluatorChannelProducer)
            .add_subclass(Self))
    }

    /// Send an evaluator message to filtered consumers.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        matrix_id,
        data,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None,
        origin_consumer = None
    ))]
    fn send<'py>(
        slf: &Bound<'py, Self>,
        matrix_id: String,
        data: Py<PyAny>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<String>,
        origin_consumer: Option<Py<PyAny>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let evaluator_name = evaluator_name.unwrap_or_else(|| wc.clone());
        let evaluator_type = evaluator_type.unwrap_or_else(|| wc.clone());
        let exchange_name = exchange_name.unwrap_or_else(|| wc.clone());
        let cryptocurrency = cryptocurrency.unwrap_or_else(|| wc.clone());
        let symbol = symbol.unwrap_or_else(|| wc.clone());
        let time_frame = time_frame.unwrap_or_else(|| wc.clone());

        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumers: Vec<Py<PyAny>> = Python::attach(|py| -> PyResult<Vec<Py<PyAny>>> {
                let ch = producer.bind(py).getattr("channel")?;
                let kwargs = PyDict::new(py);
                kwargs.set_item("matrix_id", &matrix_id)?;
                kwargs.set_item("evaluator_name", &evaluator_name)?;
                kwargs.set_item("evaluator_type", &evaluator_type)?;
                kwargs.set_item("exchange_name", &exchange_name)?;
                kwargs.set_item("cryptocurrency", &cryptocurrency)?;
                kwargs.set_item("symbol", &symbol)?;
                kwargs.set_item("time_frame", &time_frame)?;
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
                    msg.set_item("evaluator_type", &evaluator_type)?;
                    msg.set_item("exchange_name", &exchange_name)?;
                    msg.set_item("cryptocurrency", &cryptocurrency)?;
                    msg.set_item("symbol", &symbol)?;
                    msg.set_item("time_frame", &time_frame)?;
                    msg.set_item("data", data.bind(py))?;
                    let q = consumer.bind(py).getattr("queue")?;
                    let coro = q.call_method1("put", (msg,))?;
                    pyo3_async_runtimes::tokio::into_future(coro)
                })?;
                fut.await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }
}

// ---------------------------------------------------------------------------
// EvaluatorsChannel
// ---------------------------------------------------------------------------

#[pyclass(
    name = "EvaluatorsChannel",
    extends = PyEvaluatorChannel,
    dict,
    subclass,
    module = "octobot_evaluators_rs"
)]
pub struct PyEvaluatorsChannel;

#[pymethods]
impl PyEvaluatorsChannel {
    #[classattr]
    const MATRIX_ID_KEY: &'static str = "matrix_id";
    #[classattr]
    const EVALUATOR_NAME_KEY: &'static str = "evaluator_name";
    #[classattr]
    const EVALUATOR_TYPE_KEY: &'static str = "evaluator_type";
    #[classattr]
    const EXCHANGE_NAME_KEY: &'static str = "exchange_name";
    #[classattr]
    const CRYPTOCURRENCY_KEY: &'static str = "cryptocurrency";
    #[classattr]
    const SYMBOL_KEY: &'static str = "symbol";
    #[classattr]
    const TIME_FRAME_KEY: &'static str = "time_frame";

    #[new]
    fn new(py: Python<'_>, matrix_id: String) -> PyResult<PyClassInitializer<Self>> {
        let base = PyChannel::create(py)?;
        Ok(PyClassInitializer::from(base)
            .add_subclass(PyEvaluatorChannel { matrix_id })
            .add_subclass(Self))
    }

    /// Create a new consumer with filter keyword arguments.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        callback,
        size = 0,
        priority_level = None,
        matrix_id = None,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None
    ))]
    fn new_consumer<'py>(
        slf: &Bound<'py, Self>,
        callback: Py<PyAny>,
        size: i64,
        priority_level: Option<i64>,
        matrix_id: Option<String>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let priority = priority_level
            .unwrap_or(ChannelConsumerPriorityLevels::Medium as i64);
        let matrix_id = matrix_id.unwrap_or_else(|| wc.clone());
        let evaluator_name = evaluator_name.unwrap_or_else(|| wc.clone());
        let evaluator_type = evaluator_type.unwrap_or_else(|| wc.clone());
        let exchange_name = exchange_name.unwrap_or_else(|| wc.clone());
        let cryptocurrency = cryptocurrency.unwrap_or_else(|| wc.clone());
        let symbol = symbol.unwrap_or_else(|| wc.clone());
        let time_frame = time_frame.unwrap_or_else(|| wc.clone());

        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumer: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
                let c = Py::new(
                    py,
                    PyEvaluatorsChannelConsumer::new(py, Some(callback), Some(size), Some(priority))?,
                )?;
                Ok(c.into_any())
            })?;
            let fut = Python::attach(|py| -> PyResult<_> {
                let kwargs = PyDict::new(py);
                kwargs.set_item("matrix_id", &matrix_id)?;
                kwargs.set_item("evaluator_name", &evaluator_name)?;
                kwargs.set_item("evaluator_type", &evaluator_type)?;
                kwargs.set_item("exchange_name", &exchange_name)?;
                kwargs.set_item("cryptocurrency", &cryptocurrency)?;
                kwargs.set_item("symbol", &symbol)?;
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

    /// Return filtered consumers using the evaluator filter keys.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        matrix_id = None,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None,
        origin_consumer = None
    ))]
    fn get_filtered_consumers(
        slf: &Bound<'_, Self>,
        matrix_id: Option<String>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<String>,
        origin_consumer: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let filters = PyDict::new(py);
        filters.set_item("matrix_id", matrix_id.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_name", evaluator_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_type", evaluator_type.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("exchange_name", exchange_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("cryptocurrency", cryptocurrency.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("symbol", symbol.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("time_frame", time_frame.unwrap_or_else(|| wc.clone()))?;
        let result = slf.as_any().call_method1(
            "get_consumer_from_filters",
            (filters, origin_consumer),
        )?;
        result
            .try_iter()?
            .map(|c| Ok(c?.unbind()))
            .collect::<PyResult<Vec<_>>>()
    }

    /// Override _add_new_consumer_and_run with evaluator filter keys.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        consumer,
        matrix_id = None,
        evaluator_name = None,
        evaluator_type = None,
        exchange_name = None,
        cryptocurrency = None,
        symbol = None,
        time_frame = None
    ))]
    fn _add_new_consumer_and_run<'py>(
        slf: &Bound<'py, Self>,
        consumer: &Bound<'py, PyAny>,
        matrix_id: Option<String>,
        evaluator_name: Option<String>,
        evaluator_type: Option<String>,
        exchange_name: Option<String>,
        cryptocurrency: Option<String>,
        symbol: Option<String>,
        time_frame: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let wc = CHANNEL_WILDCARD.to_string();
        let filters = PyDict::new(py);
        filters.set_item("matrix_id", matrix_id.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_name", evaluator_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("evaluator_type", evaluator_type.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("exchange_name", exchange_name.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("cryptocurrency", cryptocurrency.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("symbol", symbol.unwrap_or_else(|| wc.clone()))?;
        filters.set_item("time_frame", time_frame.unwrap_or_else(|| wc.clone()))?;

        // add_new_consumer via Python dispatch + consumer.run()
        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        let consumer_ref: Py<PyAny> = consumer.clone().unbind();
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
            Ok(Python::attach(|py| py.None()))
        })
    }
}

pub fn register(m: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {
    m.add_class::<PyEvaluatorsChannelConsumer>()?;
    m.add_class::<PyEvaluatorsChannelProducer>()?;
    m.add_class::<PyEvaluatorsChannel>()?;
    let ec = m.getattr("EvaluatorsChannel")?;
    ec.setattr(
        "PRODUCER_CLASS",
        m.getattr("EvaluatorsChannelProducer")?,
    )?;
    ec.setattr(
        "CONSUMER_CLASS",
        m.getattr("EvaluatorsChannelConsumer")?,
    )?;
    Ok(())
}
