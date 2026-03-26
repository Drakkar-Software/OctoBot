
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use async_channel::channels::channel::Channel;
use async_channel::constants;
use pyo3_bridge::futures::py_none_future;
use pyo3_bridge::async_methods::{await_py_method0, await_py_method1, for_each_await};
use crate::util::logging::get_logger;

#[pyclass(name = "Channel", dict, subclass, module = "async_channel_rs")]
pub struct PyChannel {
    #[pyo3(get, set)] pub logger: Py<PyAny>,
    #[pyo3(get, set)] pub chan_id: Option<String>,
    #[pyo3(get, set)] pub producers: Py<PyList>,
    #[pyo3(get, set)] pub consumers: Py<PyList>,
    #[pyo3(get, set)] pub internal_producer: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub is_paused: bool,
    #[pyo3(get, set)] pub is_synchronized: bool,
    #[allow(dead_code)] inner: Channel,
}

#[pymethods]
impl PyChannel {
    #[classattr] const INSTANCE_KEY: &'static str = "consumer_instance";
    #[classattr] const DEFAULT_PRIORITY_LEVEL: i64 = 0;

    #[new]
    #[pyo3(signature = (**_kw))]
    fn new(py: Python<'_>, _kw: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let inner = Channel::new("Channel");
        Ok(Self {
            logger: get_logger(py, Some("Channel"))?,
            chan_id: None, producers: PyList::empty(py).unbind(),
            consumers: PyList::empty(py).unbind(), internal_producer: None,
            is_paused: inner.is_paused,
            is_synchronized: inner.is_synchronized,
            inner,
        })
    }

    #[classmethod]
    fn get_name(cls: &Bound<'_, pyo3::types::PyType>) -> PyResult<String> {
        let n: String = cls.getattr("__name__")?.extract()?;
        Ok(Channel::derive_name(&n))
    }

    fn __deepcopy__(slf: &Bound<'_, Self>, _m: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> { Ok(slf.as_any().clone().unbind()) }
    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> { Ok(slf.as_any().clone().unbind()) }

    fn add_new_consumer(slf: &Bound<'_, Self>, consumer: &Bound<'_, PyAny>, filters: &Bound<'_, PyDict>) -> PyResult<()> {
        let py = slf.py();
        filters.set_item(slf.get_type().getattr("INSTANCE_KEY")?, consumer)?;
        slf.borrow().consumers.bind(py).append(filters)?;
        Ok(())
    }

    fn get_consumers(slf: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAny>>> {
        let py = slf.py();
        let key = slf.get_type().getattr("INSTANCE_KEY")?;
        slf.borrow().consumers.bind(py).iter().map(|c| Ok(c.get_item(&key)?.unbind())).collect()
    }

    fn get_prioritized_consumers(slf: &Bound<'_, Self>, priority_level: i64) -> PyResult<Vec<Py<PyAny>>> {
        let py = slf.py();
        let key = slf.get_type().getattr("INSTANCE_KEY")?;
        let mut out = Vec::new();
        for item in slf.borrow().consumers.bind(py).iter() {
            let c = item.get_item(&key)?;
            if c.getattr("priority_level")?.extract::<i64>()? <= priority_level { out.push(c.unbind()); }
        }
        Ok(out)
    }

    fn get_consumer_from_filters(slf: &Bound<'_, Self>, f: &Bound<'_, PyDict>) -> PyResult<Vec<Py<PyAny>>> {
        Self::_filter_consumers(slf, f)
    }

    fn _filter_consumers(slf: &Bound<'_, Self>, expected: &Bound<'_, PyDict>) -> PyResult<Vec<Py<PyAny>>> {
        let py = slf.py();
        let key = slf.get_type().getattr("INSTANCE_KEY")?;
        let wc = constants::CHANNEL_WILDCARD.into_pyobject(py)?;
        let mut out = Vec::new();
        for item in slf.borrow().consumers.bind(py).iter() {
            // Use Python eq() for filter matching so cross-type equality
            // (e.g. 1 == True) is preserved — core's check_filters operates
            // on strings and cannot handle this.
            let mut ok = true;
            for (k, v) in expected.iter() {
                if v.eq(&wc)? { continue; }
                match item.get_item(&k) {
                    Ok(cv) => {
                        if let Ok(list) = cv.cast::<PyList>() {
                            if !list.iter().any(|x| x.eq(&v).unwrap_or(false) || x.eq(&wc).unwrap_or(false)) { ok = false; break; }
                        } else if !cv.eq(&v)? && !cv.eq(&wc)? { ok = false; break; }
                    }
                    Err(_) => { ok = false; break; }
                }
            }
            if ok { out.push(item.get_item(&key)?.unbind()); }
        }
        Ok(out)
    }

    fn _should_pause_producers(slf: &Bound<'_, Self>) -> PyResult<bool> {
        let py = slf.py();
        let is_paused = slf.borrow().is_paused;
        let priorities: Vec<i64> = Self::get_consumers(slf)?
            .iter()
            .map(|c| c.bind(py).getattr("priority_level").and_then(|p| p.extract::<i64>()).unwrap_or(0))
            .collect();
        Ok(Channel::should_pause_with_priorities(is_paused, &priorities))
    }

    fn _should_resume_producers(slf: &Bound<'_, Self>) -> PyResult<bool> {
        let py = slf.py();
        let is_paused = slf.borrow().is_paused;
        let priorities: Vec<i64> = Self::get_consumers(slf)?
            .iter()
            .map(|c| c.bind(py).getattr("priority_level").and_then(|p| p.extract::<i64>()).unwrap_or(0))
            .collect();
        Ok(Channel::should_resume_with_priorities(is_paused, &priorities))
    }

    fn get_producers(slf: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAny>>> {
        Ok(slf.borrow().producers.bind(slf.py()).iter().map(|p| p.unbind()).collect())
    }

    fn unregister_producer(slf: &Bound<'_, Self>, producer: &Bound<'_, PyAny>) -> PyResult<()> {
        let l = slf.borrow().producers.bind(slf.py()).clone();
        for (i, p) in l.iter().enumerate() { if p.is(producer) { l.del_item(i)?; break; } }
        Ok(())
    }

    fn flush(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let inner = slf.borrow();
        if let Some(ref ip) = inner.internal_producer { ip.bind(py).setattr("channel", py.None())?; }
        for p in inner.producers.bind(py).iter() { p.setattr("channel", py.None())?; }
        Ok(())
    }

    #[pyo3(signature = (**kw))]
    fn get_internal_producer(slf: &Bound<'_, Self>, kw: Option<&Bound<'_, PyDict>>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        { let i = slf.borrow(); if let Some(ref ip) = i.internal_producer { return Ok(ip.clone_ref(py)); } }
        let cls = slf.get_type().getattr("PRODUCER_CLASS")?;
        if cls.is_none() { return Err(pyo3::exceptions::PyTypeError::new_err("PRODUCER_CLASS not defined")); }
        let p = match kw { Some(k) => cls.call((slf,), Some(k))?, None => cls.call1((slf,))? };
        slf.borrow_mut().internal_producer = Some(p.clone().unbind());
        Ok(p.unbind())
    }

    // ── async methods ──────────────────────────────────────────────────

    #[pyo3(signature = (callback=None, consumer_filters=None, internal_consumer=None, size=0, priority_level=0))]
    fn new_consumer<'py>(slf: &Bound<'py, Self>, callback: Option<Py<PyAny>>, consumer_filters: Option<Py<PyAny>>,
                         internal_consumer: Option<Py<PyAny>>, size: i64, priority_level: i64) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        let consumer_cls: Py<PyAny> = slf.get_type().getattr("CONSUMER_CLASS")?.unbind();
        // Capture the event loop NOW on the Python thread so that
        // Consumer.create_task() can use it from within the tokio thread.
        let event_loop: Py<PyAny> = py.import("asyncio")?.call_method0("get_running_loop")?.unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let consumer: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
                let c = match internal_consumer {
                    Some(ic) => ic,
                    None => consumer_cls.bind(py).call1((callback, size, priority_level))?.unbind(),
                };
                // Inject the event loop captured from the Python thread
                if let Ok(pyc) = c.bind(py).cast::<crate::consumer::PyConsumer>() {
                    pyc.borrow_mut().event_loop = Some(event_loop.clone_ref(py));
                }
                Ok(c)
            })?;
            let filters = consumer_filters.unwrap_or_else(|| Python::attach(|py| py.None()));
            // await self._add_new_consumer_and_run(consumer, filters)
            let fut = Python::attach(|py| {
                let coro = channel.bind(py).call_method1("_add_new_consumer_and_run", (consumer.bind(py), filters.bind(py)))?;
                pyo3_async_runtimes::tokio::into_future(coro)
            })?;
            fut.await?;
            // await self._check_producers_state()
            await_py_method0(&channel, "_check_producers_state").await?;
            Ok(consumer)
        })
    }

    #[pyo3(signature = (consumer, consumer_filters=None, **_kw))]
    fn _add_new_consumer_and_run<'py>(slf: &Bound<'py, Self>, consumer: &Bound<'py, PyAny>,
                                     consumer_filters: Option<Py<PyAny>>, _kw: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let f = match consumer_filters {
            Some(ref v) if !v.is_none(py) => v.bind(py).cast::<PyDict>()?.clone(),
            _ => PyDict::new(py).clone(),
        };
        Self::add_new_consumer(slf, consumer, &f)?;
        let is_sync = slf.borrow().is_synchronized;
        let consumer: Py<PyAny> = consumer.clone().unbind();
        let with_task: Py<PyAny> = (!is_sync).into_pyobject(py)?.to_owned().into_any().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            await_py_method1(&consumer, "run", &with_task).await
        })
    }

    fn remove_consumer<'py>(slf: &Bound<'py, Self>, consumer: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let key = slf.get_type().getattr("INSTANCE_KEY")?;
        let list = slf.borrow().consumers.bind(py).clone();
        for (i, item) in list.iter().enumerate() {
            if item.get_item(&key)?.is(consumer) { list.del_item(i)?; break; }
        }
        let channel: Py<PyAny> = slf.as_any().clone().unbind();
        let consumer: Py<PyAny> = consumer.clone().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            await_py_method0(&channel, "_check_producers_state").await?;
            await_py_method0(&consumer, "stop").await
        })
    }

    fn _check_producers_state<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let should_pause = Self::_should_pause_producers(slf)?;
        let should_resume = Self::_should_resume_producers(slf)?;
        let _channel: Py<PyAny> = slf.as_any().clone().unbind();

        if should_pause {
            slf.borrow_mut().is_paused = true;
            let producers: Vec<Py<PyAny>> = Self::get_producers(slf)?;
            return pyo3_async_runtimes::tokio::future_into_py(py, async move {
                for_each_await(&producers, "pause").await?;
                Ok(Python::attach(|py| py.None()))
            });
        }
        if should_resume {
            slf.borrow_mut().is_paused = false;
            let producers: Vec<Py<PyAny>> = Self::get_producers(slf)?;
            return pyo3_async_runtimes::tokio::future_into_py(py, async move {
                for_each_await(&producers, "resume").await?;
                Ok(Python::attach(|py| py.None()))
            });
        }
        py_none_future(py)
    }

    fn register_producer<'py>(slf: &Bound<'py, Self>, producer: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let list = slf.borrow().producers.bind(py).clone();
        if !list.iter().any(|p| p.is(producer)) { list.append(producer)?; }
        if slf.borrow().is_paused {
            let producer: Py<PyAny> = producer.clone().unbind();
            return pyo3_async_runtimes::tokio::future_into_py(py, async move {
                await_py_method0(&producer, "pause").await
            });
        }
        py_none_future(py)
    }

    fn start<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let consumers: Vec<Py<PyAny>> = Self::get_consumers(slf)?;
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            for_each_await(&consumers, "start").await?;
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn stop<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let mut all: Vec<Py<PyAny>> = Self::get_consumers(slf)?;
        all.extend(Self::get_producers(slf)?);
        if let Some(ref ip) = slf.borrow().internal_producer { all.push(ip.clone_ref(py)); }
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            for_each_await(&all, "stop").await?;
            Ok(Python::attach(|py| py.None()))
        })
    }

    fn run<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let is_sync = slf.borrow().is_synchronized;
        let consumers: Vec<Py<PyAny>> = Self::get_consumers(slf)?;
        let with_task: Py<PyAny> = (!is_sync).into_pyobject(py)?.to_owned().into_any().unbind();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            for c in &consumers {
                await_py_method1(c, "run", &with_task).await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }

    #[pyo3(signature = (**kw))]
    fn modify<'py>(slf: &Bound<'py, Self>, kw: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let producers: Vec<Py<PyAny>> = Self::get_producers(slf)?;
        let kw_obj: Option<Py<PyDict>> = kw.map(|k| k.clone().unbind());
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            for p in producers {
                let fut = Python::attach(|py| {
                    let coro = match &kw_obj {
                        Some(k) => p.bind(py).call_method("modify", (), Some(k.bind(py)))?,
                        None => p.bind(py).call_method0("modify")?,
                    };
                    pyo3_async_runtimes::tokio::into_future(coro)
                })?;
                fut.await?;
            }
            Ok(Python::attach(|py| py.None()))
        })
    }
}

// _filter_consumers, _should_pause_producers, _should_resume_producers
// are in the main #[pymethods] block above (bridged because Python
// calls them via self._ and subclasses may override them)

// ── Module-level functions ─────────────────────────────────────────────────

#[pyfunction] #[pyo3(signature = (chan, name=None))]
pub fn set_chan(py: Python<'_>, chan: &Bound<'_, PyAny>, name: Option<String>) -> PyResult<Py<PyAny>> {
    let ci = py.import("async_channel_rs._core")?.getattr("ChannelInstances")?.call_method0("instance")?;
    let chs = ci.getattr("channels")?;
    let n = match name { Some(ref s) if !s.is_empty() => s.clone(), _ => chan.call_method0("get_name")?.extract()? };
    if !chs.call_method1("__contains__", (&n,))?.extract::<bool>()? { chs.set_item(&n, chan)?; Ok(chan.clone().unbind()) }
    else { Err(pyo3::exceptions::PyValueError::new_err(format!("Channel {} already exists.", n))) }
}

#[pyfunction]
pub fn del_chan(py: Python<'_>, name: &str) -> PyResult<()> {
    let ci = py.import("async_channel_rs._core")?.getattr("ChannelInstances")?.call_method0("instance")?;
    ci.getattr("channels")?.call_method1("pop", (name, py.None()))?; Ok(())
}

#[pyfunction]
pub fn get_chan(py: Python<'_>, chan_name: &str) -> PyResult<Py<PyAny>> {
    let ci = py.import("async_channel_rs._core")?.getattr("ChannelInstances")?.call_method0("instance")?;
    Ok(ci.getattr("channels")?.get_item(chan_name)?.unbind())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyChannel>()?;
    m.getattr("Channel")?.setattr("PRODUCER_CLASS", m.py().None())?;
    m.getattr("Channel")?.setattr("CONSUMER_CLASS", m.py().None())?;
    m.add_function(wrap_pyfunction!(set_chan, m)?)?;
    m.add_function(wrap_pyfunction!(del_chan, m)?)?;
    m.add_function(wrap_pyfunction!(get_chan, m)?)?;
    Ok(())
}
