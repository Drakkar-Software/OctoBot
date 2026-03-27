pub mod channels;
pub mod matrix;
pub mod tree;

use pyo3::prelude::*;
use pyo3::types::PyModule;

use octobot_evaluators::constants;

#[pymodule]
#[pyo3(name = "_core")]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    // ── Constants ──────────────────────────────────────────────────────
    m.add("START_EVAL_PERTINENCE", constants::START_EVAL_PERTINENCE)?;
    m.add("MAX_TA_EVAL_TIME_SECONDS", constants::MAX_TA_EVAL_TIME_SECONDS)?;
    m.add("EVALUATION_ALLOWED_TIME_DELTA", constants::EVALUATION_ALLOWED_TIME_DELTA)?;
    m.add("EVALUATOR_CLASS_TYPE_MRO_INDEX", constants::EVALUATOR_CLASS_TYPE_MRO_INDEX)?;
    // EVALUATOR_EVAL_DEFAULT_TYPE: the Python side stores the actual `float` type
    m.add("EVALUATOR_EVAL_DEFAULT_TYPE", py.eval(pyo3::ffi::c_str!("float"), None, None)?)?;
    m.add("STRATEGIES_REQUIRED_TIME_FRAME", constants::STRATEGIES_REQUIRED_TIME_FRAME)?;
    m.add("STRATEGIES_REQUIRED_EVALUATORS", constants::STRATEGIES_REQUIRED_EVALUATORS)?;
    m.add("STRATEGIES_COMPATIBLE_EVALUATOR_TYPES", constants::STRATEGIES_COMPATIBLE_EVALUATOR_TYPES)?;
    m.add("CONFIG_FORCED_TIME_FRAME", constants::CONFIG_FORCED_TIME_FRAME)?;
    m.add("TENTACLE_DEFAULT_CONFIG", constants::TENTACLE_DEFAULT_CONFIG)?;
    m.add("EVALUATORS_CHANNEL", constants::EVALUATORS_CHANNEL)?;
    m.add("MATRIX_CHANNEL", constants::MATRIX_CHANNEL)?;
    m.add("MATRIX_CHANNELS", constants::MATRIX_CHANNELS)?;
    m.add("TA_RE_EVALUATION_TRIGGER_UPDATED_DATA", constants::TA_RE_EVALUATION_TRIGGER_UPDATED_DATA)?;
    m.add("RESET_EVALUATION", constants::RESET_EVALUATION)?;
    m.add("EVALUATOR_CHANNEL_DATA_ACTION", constants::EVALUATOR_CHANNEL_DATA_ACTION)?;
    m.add("EVALUATOR_CHANNEL_DATA_EXCHANGE_ID", constants::EVALUATOR_CHANNEL_DATA_EXCHANGE_ID)?;
    m.add("EVALUATOR_CHANNEL_DATA_TIME_FRAMES", constants::EVALUATOR_CHANNEL_DATA_TIME_FRAMES)?;

    // ── Python enum ───────────────────────────────────────────────────
    let enums_mod = py.import("octobot_evaluators_rs._enums")?;
    let emt = enums_mod.getattr("EvaluatorMatrixTypes")?;
    m.add("EvaluatorMatrixTypes", &emt)?;

    // ── Tree module ───────────────────────────────────────────────────
    tree::base_tree_node::register(m)?;
    tree::base_tree::register(m)?;

    // ── Matrix module ─────────────────────────────────────────────────
    matrix::matrix::register(m)?;
    matrix::matrices::register(m)?;
    matrix::matrix_manager::register(m)?;

    // ── Channels module ───────────────────────────────────────────────
    channels::evaluator_channel::register(m)?;
    channels::evaluators_channel::register(m)?;
    channels::matrix_channel::register(m)?;

    // ── Submodules for import path compatibility ──────────────────────

    // constants submodule
    let cm = PyModule::new(py, "constants")?;
    cm.add("START_EVAL_PERTINENCE", constants::START_EVAL_PERTINENCE)?;
    cm.add("MAX_TA_EVAL_TIME_SECONDS", constants::MAX_TA_EVAL_TIME_SECONDS)?;
    cm.add("EVALUATION_ALLOWED_TIME_DELTA", constants::EVALUATION_ALLOWED_TIME_DELTA)?;
    cm.add("EVALUATOR_CLASS_TYPE_MRO_INDEX", constants::EVALUATOR_CLASS_TYPE_MRO_INDEX)?;
    cm.add("EVALUATOR_EVAL_DEFAULT_TYPE", py.eval(pyo3::ffi::c_str!("float"), None, None)?)?;
    cm.add("STRATEGIES_REQUIRED_TIME_FRAME", constants::STRATEGIES_REQUIRED_TIME_FRAME)?;
    cm.add("STRATEGIES_REQUIRED_EVALUATORS", constants::STRATEGIES_REQUIRED_EVALUATORS)?;
    cm.add("STRATEGIES_COMPATIBLE_EVALUATOR_TYPES", constants::STRATEGIES_COMPATIBLE_EVALUATOR_TYPES)?;
    cm.add("CONFIG_FORCED_TIME_FRAME", constants::CONFIG_FORCED_TIME_FRAME)?;
    cm.add("TENTACLE_DEFAULT_CONFIG", constants::TENTACLE_DEFAULT_CONFIG)?;
    cm.add("EVALUATORS_CHANNEL", constants::EVALUATORS_CHANNEL)?;
    cm.add("MATRIX_CHANNEL", constants::MATRIX_CHANNEL)?;
    cm.add("MATRIX_CHANNELS", constants::MATRIX_CHANNELS)?;
    cm.add("TA_RE_EVALUATION_TRIGGER_UPDATED_DATA", constants::TA_RE_EVALUATION_TRIGGER_UPDATED_DATA)?;
    cm.add("RESET_EVALUATION", constants::RESET_EVALUATION)?;
    cm.add("EVALUATOR_CHANNEL_DATA_ACTION", constants::EVALUATOR_CHANNEL_DATA_ACTION)?;
    cm.add("EVALUATOR_CHANNEL_DATA_EXCHANGE_ID", constants::EVALUATOR_CHANNEL_DATA_EXCHANGE_ID)?;
    cm.add("EVALUATOR_CHANNEL_DATA_TIME_FRAMES", constants::EVALUATOR_CHANNEL_DATA_TIME_FRAMES)?;
    m.add_submodule(&cm)?;

    // enums submodule
    let em = PyModule::new(py, "enums")?;
    em.add("EvaluatorMatrixTypes", &emt)?;
    m.add_submodule(&em)?;

    // errors submodule
    let errm = PyModule::new(py, "errors")?;
    errm.add("NodeExistsError", py.get_type::<tree::base_tree::NodeExistsError>())?;
    m.add_submodule(&errm)?;

    Ok(())
}
