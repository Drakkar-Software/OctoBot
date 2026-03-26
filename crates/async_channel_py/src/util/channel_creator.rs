use pyo3::prelude::*;
use pyo3::types::PyDict;

use async_channel::util::channel_creator as rust_creator;
use pyo3_bridge::async_methods::await_py_method0;

#[pyfunction]
#[pyo3(signature = (channel_class, set_chan_method, *, is_synchronized=false, channel_name=None, **kwargs))]
pub fn create_channel_instance<'py>(
    py: Python<'py>,
    channel_class: &Bound<'py, PyAny>,
    set_chan_method: &Bound<'py, PyAny>,
    is_synchronized: bool,
    channel_name: Option<String>,
    kwargs: Option<&Bound<'py, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    // Sync setup
    let created = match kwargs {
        Some(kw) => channel_class.call((), Some(kw))?,
        None => channel_class.call0()?,
    };
    let name: String = match channel_name {
        Some(n) => n,
        None => channel_class.call_method0("get_name")?.extract()?,
    };
    let kw = PyDict::new(py);
    kw.set_item("name", &name)?;
    set_chan_method.call((&created,), Some(&kw))?;
    created.setattr("is_synchronized", is_synchronized)?;

    let channel: Py<PyAny> = created.clone().unbind();
    // Async: delegate start to Rust orchestrator
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let channel_for_start = Python::attach(|py| channel.clone_ref(py));
        rust_creator::create_channel_instance(
            || Python::attach(|py| channel.clone_ref(py)),
            |_| {}, // set_chan already done above
            is_synchronized,
            |_| {}, // is_synchronized already set above
            || async move {
                let _ = await_py_method0(&channel_for_start, "start").await;
            },
        ).await;
        Ok(channel)
    })
}

#[pyfunction]
#[pyo3(signature = (channel_class, set_chan_method, *, is_synchronized=false, **kwargs))]
pub fn create_all_subclasses_channel<'py>(
    py: Python<'py>,
    channel_class: &Bound<'py, PyAny>,
    set_chan_method: &Bound<'py, PyAny>,
    is_synchronized: bool,
    kwargs: Option<&Bound<'py, PyDict>>,
) -> PyResult<Bound<'py, PyAny>> {
    type SubEntry = (Py<PyAny>, Py<PyAny>, Option<Py<PyDict>>);
    let mut sub_data: Vec<SubEntry> = Vec::new();
    for sub in channel_class.call_method0("__subclasses__")?.try_iter()? {
        sub_data.push((sub?.unbind(), set_chan_method.clone().unbind(), kwargs.map(|k| k.clone().unbind())));
    }
    let count = sub_data.len();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        // Delegate iteration to Rust orchestrator
        rust_creator::create_all_subclasses_channel(count, |i| {
            let (sub_cls, set_method, kw) = Python::attach(|py| {
                (
                    sub_data[i].0.clone_ref(py),
                    sub_data[i].1.clone_ref(py),
                    sub_data[i].2.as_ref().map(|k| k.clone_ref(py)),
                )
            });
            async move {
                let channel: Py<PyAny> = Python::attach(|py| -> PyResult<Py<PyAny>> {
                    let sub_cls_bound: &Bound<'_, PyAny> = sub_cls.bind(py);
                    let created = match &kw {
                        Some(k) => { let k_bound: &Bound<'_, PyDict> = k.bind(py); sub_cls_bound.call((), Some(k_bound))? },
                        None => sub_cls_bound.call0()?,
                    };
                    let name: String = sub_cls_bound.call_method0("get_name")?.extract()?;
                    let skw = PyDict::new(py); skw.set_item("name", &name)?;
                    let set_method_bound: &Bound<'_, PyAny> = set_method.bind(py);
                    set_method_bound.call((&created,), Some(&skw))?;
                    created.setattr("is_synchronized", is_synchronized)?;
                    Ok(created.unbind())
                }).unwrap();
                let _ = await_py_method0(&channel, "start").await;
            }
        }).await;
        Ok(Python::attach(|py| py.None()))
    })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_channel_instance, m)?)?;
    m.add_function(wrap_pyfunction!(create_all_subclasses_channel, m)?)?;
    Ok(())
}
