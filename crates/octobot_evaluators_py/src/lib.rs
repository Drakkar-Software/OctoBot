pub mod channels;
pub mod matrix;

use pyo3::prelude::*;
use pyo3::types::PyModule;

use octobot_evaluators::constants;

pyo3::create_exception!(octobot_evaluators_rs, UnsetTentacleEvaluation, pyo3::exceptions::PyException);

/// create_matrix() -> str
/// Creates a new Matrix, adds it to the Matrices singleton, returns the matrix_id.
#[pyfunction]
fn create_matrix(py: Python<'_>) -> PyResult<String> {
    let core = py.import("octobot_evaluators_rs._core")?;
    let matrix_cls = core.getattr("Matrix")?;
    let matrices_cls = core.getattr("Matrices")?;
    let mat = matrix_cls.call0()?;
    let matrix_id: String = mat.getattr("matrix_id")?.extract()?;
    let inst = matrices_cls.call_method0("instance")?;
    inst.call_method1("add_matrix", (&mat,))?;
    Ok(matrix_id)
}

/// Register all evaluator constants on a module.
fn register_constants(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add("START_EVAL_PERTINENCE", constants::START_EVAL_PERTINENCE)?;
    m.add("MAX_TA_EVAL_TIME_SECONDS", constants::MAX_TA_EVAL_TIME_SECONDS)?;
    m.add("EVALUATION_ALLOWED_TIME_DELTA", constants::EVALUATION_ALLOWED_TIME_DELTA)?;
    m.add("EVALUATOR_CLASS_TYPE_MRO_INDEX", constants::EVALUATOR_CLASS_TYPE_MRO_INDEX)?;
    m.add("EVALUATOR_EVAL_DEFAULT_TYPE", py.get_type::<pyo3::types::PyFloat>())?;
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
    Ok(())
}

#[pymodule]
#[pyo3(name = "_core")]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();

    // ── Constants ──────────────────────────────────────────────────────
    register_constants(m)?;

    // ── Python enum ───────────────────────────────────────────────────
    let enums_mod = py.import("octobot_evaluators_rs._enums")?;
    let emt = enums_mod.getattr("EvaluatorMatrixTypes")?;
    m.add("EvaluatorMatrixTypes", &emt)?;

    // ── Tree module (from octobot_commons_py) ─────────────────────────
    octobot_commons_py::tree::base_tree_node::register(m)?;
    octobot_commons_py::tree::base_tree::register(m)?;

    // ── Matrix module ─────────────────────────────────────────────────
    matrix::matrix::register(m)?;
    matrix::matrices::register(m)?;
    matrix::matrix_manager::register(m)?;

    // ── Channels module ───────────────────────────────────────────────
    channels::evaluator_channel::register(m)?;
    channels::evaluators_channel::register(m)?;
    channels::matrix_channel::register(m)?;

    // ── API helpers ─────────────────────────────────────────────────────
    m.add_function(wrap_pyfunction!(create_matrix, m)?)?;

    // ── Errors ──────────────────────────────────────────────────────────
    m.add("UnsetTentacleEvaluation", py.get_type::<UnsetTentacleEvaluation>())?;

    // ── Submodules for import path compatibility ──────────────────────

    // constants submodule
    let cm = PyModule::new(py, "constants")?;
    register_constants(&cm)?;
    m.add_submodule(&cm)?;

    // enums submodule
    let em = PyModule::new(py, "enums")?;
    em.add("EvaluatorMatrixTypes", &emt)?;
    m.add_submodule(&em)?;

    // errors submodule
    let errm = PyModule::new(py, "errors")?;
    errm.add("NodeExistsError", py.get_type::<octobot_commons_py::tree::base_tree::NodeExistsError>())?;
    errm.add("UnsetTentacleEvaluation", py.get_type::<UnsetTentacleEvaluation>())?;
    m.add_submodule(&errm)?;

    Ok(())
}
