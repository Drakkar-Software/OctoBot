use pyo3::prelude::*;

/// Try to cache the running asyncio event loop. Returns None if called from
/// a thread without an active loop (e.g. a tokio worker thread).
pub fn try_get_event_loop(py: Python<'_>) -> Option<Py<PyAny>> {
    let asyncio = py.import("asyncio").ok()?;
    asyncio.call_method0("get_running_loop")
        .or_else(|_| asyncio.call_method0("get_event_loop"))
        .ok()
        .map(|l| l.unbind())
}
