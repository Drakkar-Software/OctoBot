use pyo3::prelude::*;
use pyo3::types::PyDict;

use async_channel::producer::{Producer, SyncConsumerHandle};
use pyo3_bridge::futures::py_none_future;
use pyo3_bridge::async_methods::{await_py_method0, await_py_method1};
use pyo3_bridge::event_loop::try_get_event_loop;
use crate::util::logging::get_logger;

#[pyclass(name = "Producer", dict, subclass, module = "async_channel_rs")]
pub struct PyProducer {
    #[pyo3(get, set)] pub logger: Py<PyAny>,
    #[pyo3(get, set)] pub channel: Py<PyAny>,
    #[pyo3(get, set)] pub produce_task: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub should_stop: bool,
    #[pyo3(get, set)] pub is_running: bool,
    inner: Producer,
    /// Cached event loop reference. May be None if created from tokio thread.
    event_loop: Option<Py<PyAny>>,
}

#[pymethods]
impl PyProducer {
    #[new]
    fn new(py: Python<'_>, channel: Py<PyAny>) -> PyResult<Self> {
        let inner = Producer::new();
        let event_loop = try_get_event_loop(py);
        Ok(Self {
            logger: get_logger(py, Some("Producer"))?,
            channel, produce_task: None,
            should_stop: inner.should_stop,
            is_running: inner.is_running,
            inner,
            event_loop,
        })
    }

    fn send<'py>(slf: &Bound<'py, Self>, data: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        let data: Py<PyAny> = data.clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumers: Vec<Py<PyAny>> = Python::attach(|py| {
                let ch = producer.bind(py).getattr("channel")?;
                let list = ch.call_method0("get_consumers")?;
                list.try_iter()?.map(|c| -> PyResult<Py<PyAny>> { Ok(c?.unbind()) }).collect::<PyResult<Vec<_>>>()
            })?;
            for c in consumers {
                let fut = Python::attach(|py| {
                    let q = c.bind(py).getattr("queue")?;
                    let coro = q.call_method1("put", (data.bind(py),))?;
                    pyo3_async_runtimes::tokio::into_future(coro)
                })?;
                fut.await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }

    #[pyo3(signature = (**_kw))]
    fn push<'py>(_slf: &Bound<'py, Self>, _kw: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }
    fn start<'py>(_slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }

    fn pause<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let mut b = slf.borrow_mut();
        let _ = b.logger.bind(py).call_method1("debug", ("Pausing...",));
        b.inner.pause();
        b.is_running = b.inner.is_running;
        if !b.channel.bind(py).getattr("is_paused")?.extract::<bool>()? {
            b.channel.bind(py).setattr("is_paused", true)?;
        }
        py_none_future(py)
    }

    fn resume<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let inner = slf.borrow();
        let _ = inner.logger.bind(py).call_method1("debug", ("Resuming...",));
        if inner.channel.bind(py).getattr("is_paused")?.extract::<bool>()? {
            inner.channel.bind(py).setattr("is_paused", false)?;
        }
        py_none_future(py)
    }

    #[pyo3(signature = (**_kw))]
    fn perform<'py>(_slf: &Bound<'py, Self>, _kw: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }
    #[pyo3(signature = (**_kw))]
    fn modify<'py>(_slf: &Bound<'py, Self>, _kw: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
        py_none_future(_slf.py())
    }

    fn wait_for_processing<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumers: Vec<Py<PyAny>> = Python::attach(|py| {
                let ch = producer.bind(py).getattr("channel")?;
                ch.call_method0("get_consumers")?.try_iter()?.map(|c| -> PyResult<Py<PyAny>> { Ok(c?.unbind()) }).collect::<PyResult<Vec<_>>>()
            })?;
            for c in consumers {
                await_py_method0(&c, "join_queue").await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn synchronized_perform_consumers_queue<'py>(
        slf: &Bound<'py, Self>, priority_level: i64, join_consumers: bool, timeout: f64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // 1. Collect consumer handles from Python
            let consumers: Vec<Py<PyAny>> = Python::attach(|py| {
                let ch = producer.bind(py).getattr("channel")?;
                ch.call_method1("get_prioritized_consumers", (priority_level,))?
                    .try_iter()?.map(|c| -> PyResult<Py<PyAny>> { Ok(c?.unbind()) }).collect::<PyResult<Vec<_>>>()
            })?;
            let handles: Vec<SyncConsumerHandle> = consumers
                .iter()
                .enumerate()
                .map(|(i, _)| SyncConsumerHandle { index: i })
                .collect();

            // 2. drain_and_perform closure: drains Python queue and calls perform
            let drain_and_perform = |idx: usize| {
                let c: Py<PyAny> = Python::attach(|py| consumers[idx].clone_ref(py));
                async move {
                    Producer::drain_queue(
                        || {
                            let c = Python::attach(|py| c.clone_ref(py));
                            async move {
                                Python::attach(|py| {
                                    c.bind(py).getattr("queue")?.call_method0("empty")?.extract::<bool>()
                                }).unwrap_or(true)
                            }
                        },
                        || {
                            let c = Python::attach(|py| c.clone_ref(py));
                            async move {
                                let fut = Python::attach(|py| {
                                    let coro = c.bind(py).getattr("queue")?.call_method0("get")?;
                                    pyo3_async_runtimes::tokio::into_future(coro)
                                });
                                match fut {
                                    Ok(f) => f.await.ok(),
                                    Err(_) => None,
                                }
                            }
                        },
                        |data: Py<PyAny>| {
                            let c = Python::attach(|py| c.clone_ref(py));
                            async move {
                                let res = Python::attach(|py| {
                                    let coro = c.bind(py).call_method1("perform", (data.bind(py),))?;
                                    pyo3_async_runtimes::tokio::into_future(coro)
                                });
                                if let Ok(f) = res { let _ = f.await; }
                            }
                        },
                    ).await;
                }
            };

            // 3. join_fn closure: bridges Python consumer.join calls
            let join_fn = |idx: usize, timeout: f64| {
                let c = Python::attach(|py| consumers[idx].clone_ref(py));
                async move {
                    let res = Python::attach(|py| {
                        let coro = c.bind(py).call_method1("join", (timeout,))?;
                        pyo3_async_runtimes::tokio::into_future(coro)
                    });
                    if let Ok(f) = res {
                        let _ = f.await;
                    }
                }
            };

            // 4. Delegate to Rust Producer::synchronized_perform
            Producer::synchronized_perform(
                &handles,
                join_consumers,
                timeout,
                drain_and_perform,
                join_fn,
            ).await;

            Ok(Python::attach(|py| py.None()))
        })
    }

    fn stop<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let mut b = slf.borrow_mut();
        b.inner.stop();
        b.should_stop = b.inner.should_stop;
        b.is_running = b.inner.is_running;
        if let Some(ref t) = b.produce_task { let _ = t.bind(py).call_method0("cancel"); }
        py_none_future(py)
    }

    fn create_task(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        {
            let mut b = slf.borrow_mut();
            b.inner.create_task();
            b.is_running = b.inner.is_running;
        }
        let coro = slf.call_method0("start")?;
        let asyncio = py.import("asyncio")?;
        let loop_obj = match &slf.borrow().event_loop {
            Some(l) => l.clone_ref(py),
            None => asyncio.call_method0("get_running_loop")?.unbind(),
        };
        // Temporarily set the event loop for this thread so ensure_future works
        asyncio.call_method1("set_event_loop", (loop_obj.bind(py),))?;
        let task = asyncio.call_method1("ensure_future", (coro,))?;
        let mut b = slf.borrow_mut();
        b.produce_task = Some(task.unbind());
        if b.event_loop.is_none() { b.event_loop = Some(loop_obj); }
        Ok(())
    }

    fn run<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producer: Py<PyAny> = slf.as_any().clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let channel = Python::attach(|py| -> PyResult<Py<PyAny>> {
                Ok(producer.bind(py).getattr("channel")?.unbind())
            })?;
            await_py_method1(&channel, "register_producer", &producer).await?;
            Python::attach(|py| -> PyResult<()> {
                if !producer.bind(py).getattr("channel")?.getattr("is_synchronized")?.extract::<bool>()? {
                    producer.bind(py).call_method0("create_task")?;
                }
                Ok(())
            })?;
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn is_consumers_queue_empty(slf: &Bound<'_, Self>, priority_level: i64) -> PyResult<bool> {
        let py = slf.py();
        let data: Vec<(i64, bool)> = slf.borrow().channel.bind(py)
            .call_method0("get_consumers")?.try_iter()?
            .map(|c| {
                let c = c.unwrap();
                let prio = c.getattr("priority_level").and_then(|p| p.extract()).unwrap_or(0);
                let empty = c.getattr("queue")
                    .and_then(|q| q.call_method0("empty"))
                    .and_then(|e| e.extract())
                    .unwrap_or(true);
                (prio, empty)
            }).collect();
        Ok(Producer::is_consumers_queue_empty(&data, priority_level))
    }
}

// Public Rust-accessible constructor for cross-crate use.
impl PyProducer {
    pub fn create(py: Python<'_>, channel: Py<PyAny>) -> PyResult<Self> {
        Self::new(py, channel)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyProducer>()?;
    Ok(())
}
