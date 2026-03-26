use pyo3::prelude::*;
use pyo3::types::PyDict;
use crate::util::logging::get_logger;

#[pyclass(name = "ChannelInstances", subclass, module = "async_channel_rs")]
pub struct PyChannelInstances {
    #[pyo3(get, set)] pub channels: Py<PyAny>,
}

#[pymethods]
impl PyChannelInstances {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        Ok(Self { channels: PyDict::new(py).unbind().into_any() })
    }
    #[classmethod]
    fn instance(cls: &Bound<'_, pyo3::types::PyType>) -> PyResult<Py<PyAny>> {
        let py = cls.py();
        let has: bool = cls.getattr("_instances")
            .and_then(|d| d.call_method1("__contains__", (cls,)))
            .and_then(|r| r.extract()).unwrap_or(false);
        if has { return Ok(cls.getattr("_instances")?.get_item(cls)?.unbind()); }
        let inst = cls.call0()?;
        if cls.getattr("_instances").is_err() { cls.setattr("_instances", PyDict::new(py))?; }
        cls.getattr("_instances")?.set_item(cls, &inst)?;
        Ok(inst.unbind())
    }
    #[classattr] fn _instances(py: Python<'_>) -> Py<PyAny> { PyDict::new(py).unbind().into_any() }
}

fn ci(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    py.import("async_channel_rs._core")?.getattr("ChannelInstances")?.call_method0("instance")
}

#[pyfunction]
pub fn set_chan_at_id(py: Python<'_>, chan: &Bound<'_, PyAny>, name: String) -> PyResult<Py<PyAny>> {
    let chs = ci(py)?.getattr("channels")?;
    let cn: String = if !name.is_empty() { chan.call_method0("get_name")?.extract()? } else { name };
    let cid = chan.getattr("chan_id")?;
    if !chs.call_method1("__contains__", (&cid,))?.extract::<bool>()? { chs.set_item(&cid, PyDict::new(py))?; }
    let d = chs.get_item(&cid)?;
    if !d.call_method1("__contains__", (&cn,))?.extract::<bool>()? { d.set_item(&cn, chan)?; Ok(chan.clone().unbind()) }
    else { Err(pyo3::exceptions::PyValueError::new_err(format!("Channel {} already exists.", cn))) }
}

#[pyfunction]
pub fn get_channels(py: Python<'_>, chan_id: &str) -> PyResult<Py<PyAny>> {
    let chs = ci(py)?.getattr("channels")?;
    if chs.call_method1("__contains__", (chan_id,))?.extract::<bool>()? { Ok(chs.get_item(chan_id)?.unbind()) }
    else { Err(pyo3::exceptions::PyKeyError::new_err(format!("Channels not found with chan_id: {}", chan_id))) }
}

#[pyfunction]
pub fn del_channel_container(py: Python<'_>, chan_id: &str) -> PyResult<()> {
    ci(py)?.getattr("channels")?.call_method1("pop", (chan_id, py.None()))?; Ok(())
}

#[pyfunction]
pub fn get_chan_at_id(py: Python<'_>, chan_name: &str, chan_id: &str) -> PyResult<Py<PyAny>> {
    let msg = format!("Channel {} not found with chan_id: {}", chan_name, chan_id);
    let d = ci(py)?.getattr("channels")?.get_item(chan_id).map_err(|_| pyo3::exceptions::PyKeyError::new_err(msg.clone()))?;
    d.get_item(chan_name).map(|v| v.unbind()).map_err(|_| pyo3::exceptions::PyKeyError::new_err(msg))
}

#[pyfunction]
pub fn del_chan_at_id(py: Python<'_>, chan_name: &str, chan_id: &str) -> PyResult<()> {
    let chs = ci(py)?.getattr("channels")?;
    if chs.call_method1("__contains__", (chan_id,))?.extract::<bool>()? {
        chs.get_item(chan_id)?.call_method1("pop", (chan_name, py.None()))?;
    } else {
        get_logger(py, Some("ChannelInstances"))?.bind(py)
            .call_method1("warning", (format!("Can't del chan {} with chan_id: {}", chan_name, chan_id),))?;
    }
    Ok(())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyChannelInstances>()?;
    m.add_function(wrap_pyfunction!(set_chan_at_id, m)?)?;
    m.add_function(wrap_pyfunction!(get_channels, m)?)?;
    m.add_function(wrap_pyfunction!(del_channel_container, m)?)?;
    m.add_function(wrap_pyfunction!(get_chan_at_id, m)?)?;
    m.add_function(wrap_pyfunction!(del_chan_at_id, m)?)?;
    Ok(())
}
