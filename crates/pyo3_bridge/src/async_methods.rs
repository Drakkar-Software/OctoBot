use pyo3::prelude::*;

/// Acquire the GIL, call a no-arg async method on a Python object, and await it.
pub async fn await_py_method0(obj: &Py<PyAny>, method: &str) -> PyResult<Py<PyAny>> {
    let fut = Python::attach(|py| {
        pyo3_async_runtimes::tokio::into_future(obj.bind(py).call_method0(method)?)
    })?;
    fut.await
}

/// Acquire the GIL, call a 1-arg async method on a Python object, and await it.
pub async fn await_py_method1(obj: &Py<PyAny>, method: &str, arg: &Py<PyAny>) -> PyResult<Py<PyAny>> {
    let fut = Python::attach(|py| {
        pyo3_async_runtimes::tokio::into_future(
            obj.bind(py).call_method1(method, (arg.bind(py),))?
        )
    })?;
    fut.await
}

/// Call a no-arg async method on each item in a slice, awaiting sequentially.
pub async fn for_each_await(items: &[Py<PyAny>], method: &str) -> PyResult<()> {
    for item in items {
        await_py_method0(item, method).await?;
    }
    Ok(())
}
