pub mod constants;
pub mod data_util;
pub mod dict_util;
pub mod enums;
pub mod errors;
pub mod evaluators_util;
pub mod list_util;
pub mod logging;
pub mod logical_operators;
pub mod number_util;
pub mod symbols;
pub mod time_frame_manager;
pub mod timestamp_util;
pub mod tree;

#[cfg(feature = "pymodule")]
use pyo3::prelude::*;
#[cfg(feature = "pymodule")]
use pyo3::types::PyModule;

#[cfg(feature = "pymodule")]
#[pymodule]
#[pyo3(name = "_core")]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    // ── Top-level exports ────────────────────────────────────────────
    constants::register(m)?;
    enums::register(m)?;
    errors::register(m)?;
    number_util::register(m)?;
    data_util::register(m)?;
    list_util::register(m)?;
    dict_util::register(m)?;
    logical_operators::register(m)?;
    evaluators_util::register(m)?;
    timestamp_util::register(m)?;
    time_frame_manager::register(m)?;
    symbols::symbol::register(m)?;
    symbols::symbol_util::register(m)?;
    tree::base_tree_node::register(m)?;
    tree::base_tree::register(m)?;
    logging::register(m)?;

    // ── Submodules for import path compatibility ─────────────────────
    // These allow `from octobot_commons.X import Y` to work via conftest

    let cm = PyModule::new(py, "constants")?;
    constants::register(&cm)?;
    m.add_submodule(&cm)?;

    let em = PyModule::new(py, "enums")?;
    enums::register(&em)?;
    m.add_submodule(&em)?;

    let errm = PyModule::new(py, "errors")?;
    errors::register(&errm)?;
    m.add_submodule(&errm)?;

    let chm = PyModule::new(py, "channels_name")?;
    enums::register(&chm)?;
    m.add_submodule(&chm)?;

    let num = PyModule::new(py, "number_util")?;
    number_util::register(&num)?;
    m.add_submodule(&num)?;

    let ts = PyModule::new(py, "timestamp_util")?;
    timestamp_util::register(&ts)?;
    m.add_submodule(&ts)?;

    let tfm = PyModule::new(py, "time_frame_manager")?;
    time_frame_manager::register(&tfm)?;
    m.add_submodule(&tfm)?;

    let lu = PyModule::new(py, "list_util")?;
    list_util::register(&lu)?;
    m.add_submodule(&lu)?;

    let du = PyModule::new(py, "dict_util")?;
    dict_util::register(&du)?;
    m.add_submodule(&du)?;

    let dau = PyModule::new(py, "data_util")?;
    data_util::register(&dau)?;
    m.add_submodule(&dau)?;

    let lo = PyModule::new(py, "logical_operators")?;
    logical_operators::register(&lo)?;
    m.add_submodule(&lo)?;

    let eu = PyModule::new(py, "evaluators_util")?;
    evaluators_util::register(&eu)?;
    m.add_submodule(&eu)?;

    let sym = PyModule::new(py, "symbols")?;
    symbols::symbol::register(&sym)?;
    symbols::symbol_util::register(&sym)?;
    m.add_submodule(&sym)?;

    let sym_s = PyModule::new(py, "symbol")?;
    symbols::symbol::register(&sym_s)?;
    m.add_submodule(&sym_s)?;

    let sym_su = PyModule::new(py, "symbol_util")?;
    symbols::symbol_util::register(&sym_su)?;
    m.add_submodule(&sym_su)?;

    let tr = PyModule::new(py, "tree")?;
    tree::base_tree_node::register(&tr)?;
    tree::base_tree::register(&tr)?;
    m.add_submodule(&tr)?;

    let trbt = PyModule::new(py, "base_tree")?;
    tree::base_tree_node::register(&trbt)?;
    tree::base_tree::register(&trbt)?;
    m.add_submodule(&trbt)?;

    let log = PyModule::new(py, "logging")?;
    logging::register(&log)?;
    m.add_submodule(&log)?;

    let logutil = PyModule::new(py, "logging_util")?;
    logging::register(&logutil)?;
    m.add_submodule(&logutil)?;

    Ok(())
}
