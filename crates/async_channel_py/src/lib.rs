pub mod channels;
pub mod consumer;
pub mod producer;
pub mod util;

#[cfg(feature = "pymodule")]
use pyo3::types::PyModule;
#[cfg(feature = "pymodule")]
use pyo3::prelude::*;

#[cfg(feature = "pymodule")]
#[pymodule]
#[pyo3(name = "_core")]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    m.add("CHANNEL_WILDCARD", async_channel::constants::CHANNEL_WILDCARD)?;
    m.add("DEFAULT_QUEUE_SIZE", async_channel::constants::DEFAULT_QUEUE_SIZE as i64)?;
    m.add("PROJECT_NAME", "async-channel")?;
    m.add("VERSION", "2.2.2")?;

    // Import the Python-defined enum (no embedded Python strings in Rust)
    let enums_mod = py.import("async_channel_rs._enums")?;
    let ecls = enums_mod.getattr("ChannelConsumerPriorityLevels")?;
    m.add("ChannelConsumerPriorityLevels", &ecls)?;

    consumer::register(m)?;
    producer::register(m)?;
    channels::channel::register(m)?;
    channels::channel_instances::register(m)?;
    util::channel_creator::register(m)?;
    util::logging::register(m)?;

    // Submodules for import path compatibility
    let cm = PyModule::new(py, "constants")?;
    cm.add("CHANNEL_WILDCARD", async_channel::constants::CHANNEL_WILDCARD)?;
    cm.add("DEFAULT_QUEUE_SIZE", async_channel::constants::DEFAULT_QUEUE_SIZE as i64)?;
    m.add_submodule(&cm)?;

    let em = PyModule::new(py, "enums")?;
    em.add("ChannelConsumerPriorityLevels", &ecls)?;
    m.add_submodule(&em)?;

    Ok(())
}
