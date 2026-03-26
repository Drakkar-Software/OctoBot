use pyo3::prelude::*;
use pyo3::types::PyDict;

use async_channel::consumer::{Consumer, ConsumeError, SupervisedState};
use async_channel::enums::ChannelConsumerPriorityLevels;
use pyo3_bridge::futures::py_none_future;
use pyo3_bridge::async_methods::await_py_method0;
use pyo3_bridge::event_loop::try_get_event_loop;
use crate::util::logging::get_logger;

fn is_cancelled_error(py: Python<'_>, e: &PyErr) -> bool {
    py.import("asyncio")
        .and_then(|m| m.getattr("CancelledError"))
        .map(|cls| e.is_instance(py, &cls))
        .unwrap_or(false)
}
#[pyclass(name = "Consumer", dict, subclass, module = "async_channel_rs")]
pub struct PyConsumer {
    #[pyo3(get, set)] pub logger: Py<PyAny>,
    #[pyo3(get, set)] pub queue: Py<PyAny>,
    pub callback: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub consume_task: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub should_stop: bool,
    #[pyo3(get, set)] pub priority_level: i64,
    inner: Consumer,
    /// Cached reference to the asyncio event loop. May be None if the
    /// consumer was created from a tokio thread (e.g. inside new_consumer).
    /// Set lazily in create_task if needed.
    pub event_loop: Option<Py<PyAny>>,
}

#[pymethods]
impl PyConsumer {
    #[new]
    #[pyo3(signature = (callback=None, size=None, priority_level=None))]
    fn new(py: Python<'_>, callback: Option<Py<PyAny>>, size: Option<i64>, priority_level: Option<i64>) -> PyResult<Self> {
        let prio = priority_level.unwrap_or(ChannelConsumerPriorityLevels::High.value());
        let asyncio = py.import("asyncio")?;
        let queue = asyncio.call_method1("Queue", (size.unwrap_or(0),))?;
        let event_loop = try_get_event_loop(py);
        Ok(Self {
            logger: get_logger(py, Some("Consumer"))?,
            queue: queue.unbind(), callback, consume_task: None,
            should_stop: false, priority_level: prio,
            inner: Consumer::new(prio),
            event_loop,
        })
    }

    #[getter]
    fn get_callback(&self, py: Python<'_>) -> Option<Py<PyAny>> { self.callback.as_ref().map(|c| c.clone_ref(py)) }
    #[setter]
    fn set_callback(&mut self, val: Option<Py<PyAny>>) { self.callback = val; }

    /// Route setattr to #[pyo3(get,set)] setters or __dict__.
    /// Needed because PyO3 with `dict` doesn't auto-route setattr to __dict__.
    fn __setattr__(slf: &Bound<'_, Self>, name: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        match name {
            "callback" => { slf.borrow_mut().callback = Some(value.clone().unbind()); Ok(()) },
            "consume_task" => { slf.borrow_mut().consume_task = Some(value.clone().unbind()); Ok(()) },
            "should_stop" => { slf.borrow_mut().should_stop = value.extract()?; Ok(()) },
            "priority_level" => { slf.borrow_mut().priority_level = value.extract()?; Ok(()) },
            "queue" => { slf.borrow_mut().queue = value.clone().unbind(); Ok(()) },
            "logger" => { slf.borrow_mut().logger = value.clone().unbind(); Ok(()) },
            _ => { slf.as_any().getattr("__dict__")?.set_item(name, value)?; Ok(()) },
        }
    }

    /// Route delattr to reset #[pyo3(get,set)] fields or remove from __dict__.
    fn __delattr__(slf: &Bound<'_, Self>, name: &str) -> PyResult<()> {
        match name {
            "callback" => { slf.borrow_mut().callback = None; Ok(()) },
            "consume_task" => { slf.borrow_mut().consume_task = None; Ok(()) },
            _ => {
                let dict = slf.as_any().getattr("__dict__")?;
                if dict.contains(name)? {
                    dict.del_item(name)?; Ok(())
                } else {
                    Err(pyo3::exceptions::PyAttributeError::new_err(
                        format!("cannot delete attribute '{name}'")
                    ))
                }
            },
        }
    }

    fn consume<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let c: Py<PyAny> = slf.as_any().clone().unbind();
        let inner = slf.borrow().inner.priority_level;
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let inner = Consumer::new(inner);
            inner.consume_loop(
                || { let c = Python::attach(|py| c.clone_ref(py)); async move {
                    if Python::attach(|py| c.bind(py).getattr("should_stop")?.extract::<bool>()).unwrap_or(true) {
                        return Err(ConsumeError::Closed);
                    }
                    let fut = Python::attach(|py| pyo3_async_runtimes::tokio::into_future(c.bind(py).getattr("queue")?.call_method0("get")?))
                        .map_err(|_: PyErr| ConsumeError::Closed)?;
                    fut.await.map_err(|e| Python::attach(|py| {
                        if is_cancelled_error(py, &e) { ConsumeError::Cancelled } else { ConsumeError::Other(e) }
                    }))
                }},
                |data: Py<PyAny>| { let c = Python::attach(|py| c.clone_ref(py)); async move {
                    let fut = Python::attach(|py| pyo3_async_runtimes::tokio::into_future(c.bind(py).call_method1("perform", (data.bind(py),))?))
                        .map_err(ConsumeError::Other)?;
                    fut.await.map_err(ConsumeError::Other).map(|_| ())
                }},
                || { let c = Python::attach(|py| c.clone_ref(py)); Python::attach(|py| { let _ = c.bind(py).getattr("logger").and_then(|l: Bound<'_, PyAny>| l.call_method1("debug", ("Cancelled task",))); }); },
                |e: PyErr| { let c = Python::attach(|py| c.clone_ref(py)); Python::attach(|py| {
                    if let Ok(logger) = c.bind(py).getattr("logger") {
                        let msg = format!("Exception when calling callback on {}: {}", c.bind(py), e);
                        let kw = PyDict::new(py); let _ = kw.set_item("publish_error_if_necessary", true); let _ = kw.set_item("error_message", &msg);
                        let _ = logger.call_method("exception", (e.clone_ref(py),), Some(&kw)).or_else(|_: PyErr| logger.call_method1("exception", (&msg,)));
                    }
                }); },
                || { let c = Python::attach(|py| c.clone_ref(py)); async move {
                    if let Ok(fut) = Python::attach(|py| pyo3_async_runtimes::tokio::into_future(c.bind(py).call_method0("consume_ends")?)) { let _ = fut.await; }
                }},
            ).await;
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn perform<'py>(slf: &Bound<'py, Self>, kwargs: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let cb = slf.borrow().callback.as_ref().map(|c| c.clone_ref(py));
        let kw: Py<PyAny> = kwargs.clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            if let Some(cb) = cb {
                let fut = Python::attach(|py| pyo3_async_runtimes::tokio::into_future(cb.bind(py).call((), Some(kw.bind(py).cast()?))?))?;
                return fut.await;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn consume_ends<'py>(_slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }

    fn start<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        { let mut b = slf.borrow_mut(); b.inner.start(); b.should_stop = false; }
        py_none_future(slf.py())
    }

    fn stop<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        { let mut b = slf.borrow_mut(); b.inner.stop(); b.should_stop = true; }
        { let b = slf.borrow(); if let Some(ref t) = b.consume_task { let _ = t.bind(py).call_method0("cancel"); } }
        py_none_future(py)
    }

    fn create_task(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let coro = slf.call_method0("consume")?;
        // Use asyncio.ensure_future which handles both coroutines and futures.
        // We must temporarily set the event loop for this thread because
        // create_task may be called from a tokio thread (via Python::attach)
        // where no asyncio loop is set as "current".
        let asyncio = py.import("asyncio")?;
        let loop_obj = match &slf.borrow().event_loop {
            Some(l) => l.clone_ref(py),
            None => asyncio.call_method0("get_running_loop")?.unbind(),
        };
        // Temporarily set the event loop for this thread so ensure_future works
        asyncio.call_method1("set_event_loop", (loop_obj.bind(py),))?;
        let task = asyncio.call_method1("ensure_future", (coro,))?;
        let mut b = slf.borrow_mut();
        b.consume_task = Some(task.unbind());
        if b.event_loop.is_none() { b.event_loop = Some(loop_obj); }
        Ok(())
    }

    #[pyo3(signature = (with_task=true))]
    fn run<'py>(slf: &Bound<'py, Self>, with_task: bool) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let c: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            await_py_method0(&c, "start").await?;
            if with_task { Python::attach(|py| -> PyResult<()> { c.bind(py).call_method0("create_task")?; Ok(()) })?; }
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn join<'py>(_slf: &Bound<'py, Self>, _t: f64) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }
    fn join_queue<'py>(_slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }
    fn __str__(slf: &Bound<'_, Self>) -> PyResult<String> {
        let py = slf.py();
        let cb: String = match &slf.borrow().callback { Some(cb) => cb.bind(py).getattr("__name__").and_then(|n| n.extract()).unwrap_or("None".into()), None => "None".into() };
        let cls: String = slf.get_type().getattr("__name__")?.extract()?;
        Ok(format!("{cls} with callback: {cb}"))
    }



}

#[pyclass(name = "InternalConsumer", extends = PyConsumer, subclass, module = "async_channel_rs")]
pub struct PyInternalConsumer;
#[pymethods]
impl PyInternalConsumer {
    #[new]
    fn new(py: Python<'_>) -> PyResult<(Self, PyConsumer)> { Ok((Self, PyConsumer::new(py, None, None, None)?)) }
    fn internal_callback(_s: &Bound<'_, Self>) -> PyResult<()> { Err(pyo3::exceptions::PyNotImplementedError::new_err("internal_callback is not implemented")) }
}

#[pyclass(name = "SupervisedConsumer", extends = PyConsumer, subclass, module = "async_channel_rs")]
pub struct PySupervisedConsumer { #[pyo3(get, set)] pub idle: Py<PyAny>, _supervised: SupervisedState }
#[pymethods]
impl PySupervisedConsumer {
    #[new]
    #[pyo3(signature = (callback=None, size=None, priority_level=None))]
    fn new(py: Python<'_>, callback: Option<Py<PyAny>>, size: Option<i64>, priority_level: Option<i64>) -> PyResult<(Self, PyConsumer)> {
        let base = PyConsumer::new(py, callback, size, priority_level)?;
        let idle = py.import("asyncio")?.call_method0("Event")?; idle.call_method0("set")?;
        Ok((Self { idle: idle.unbind(), _supervised: SupervisedState::new() }, base))
    }
    fn perform<'py>(slf: &Bound<'py, Self>, kwargs: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let c: Py<PyAny> = slf.as_any().clone().unbind();
        let kw: Py<PyAny> = kwargs.clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Uses SupervisedState pattern: clear idle, perform, set idle
            Python::attach(|py| -> PyResult<()> { c.bind(py).getattr("idle")?.call_method0("clear")?; Ok(()) })?;
            let result = { let fut = Python::attach(|py| { let cb = c.bind(py).getattr("callback")?; pyo3_async_runtimes::tokio::into_future(cb.call((), Some(kw.bind(py).cast()?))?) })?; fut.await };
            Python::attach(|py| -> PyResult<()> { c.bind(py).getattr("idle")?.call_method0("set")?; Ok(()) })?;
            result
        })
    }
    fn consume_ends<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        // Mirrors Python: try: self.queue.task_done() except ValueError: pass
        if let Err(e) = slf.as_any().getattr("queue")?.call_method0("task_done") {
            if !e.is_instance_of::<pyo3::exceptions::PyValueError>(py) {
                return Err(e);
            }
        }
        py_none_future(py)
    }
    fn join<'py>(slf: &Bound<'py, Self>, timeout: f64) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        if slf.borrow().idle.bind(py).call_method0("is_set")?.extract::<bool>()? {
            return py_none_future(py);
        }
        let fut = pyo3_async_runtimes::tokio::into_future(py.import("asyncio")?.call_method1("wait_for", (slf.borrow().idle.bind(py).call_method0("wait")?, timeout))?)?;
        pyo3_async_runtimes::tokio::future_into_py(py, fut)
    }
    fn join_queue<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let fut = pyo3_async_runtimes::tokio::into_future(slf.as_any().getattr("queue")?.call_method0("join")?)?;
        pyo3_async_runtimes::tokio::future_into_py(py, fut)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyConsumer>()?; m.add_class::<PyInternalConsumer>()?; m.add_class::<PySupervisedConsumer>()?; Ok(())
}
