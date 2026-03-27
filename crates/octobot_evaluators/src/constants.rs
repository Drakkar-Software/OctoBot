// Numeric constants
pub const START_EVAL_PERTINENCE: i64 = 1;
pub const MAX_TA_EVAL_TIME_SECONDS: f64 = 0.1;
pub const EVALUATION_ALLOWED_TIME_DELTA: f64 = 10.0;
pub const EVALUATOR_CLASS_TYPE_MRO_INDEX: i64 = -4;

// EVALUATOR_EVAL_DEFAULT_TYPE is `float` (the Python type object) in Python.
// In Rust we store the string tag; the PyO3 bridge converts to the actual type.
pub const EVALUATOR_EVAL_DEFAULT_TYPE: &str = "float";

// Strategy config keys
pub const STRATEGIES_REQUIRED_TIME_FRAME: &str = "required_time_frames";
pub const STRATEGIES_REQUIRED_EVALUATORS: &str = "required_evaluators";
pub const STRATEGIES_COMPATIBLE_EVALUATOR_TYPES: &str = "compatible_evaluator_types";
pub const CONFIG_FORCED_TIME_FRAME: &str = "forced_time_frame";
pub const TENTACLE_DEFAULT_CONFIG: &str = "default_config";

// Channel names
pub const EVALUATORS_CHANNEL: &str = "Evaluators";
pub const MATRIX_CHANNEL: &str = "Matrix";
pub const MATRIX_CHANNELS: &str = "MatrixChannels";

// Channel data keys
pub const TA_RE_EVALUATION_TRIGGER_UPDATED_DATA: &str = "TA_re_evaluation_trigger_updated_data";
pub const RESET_EVALUATION: &str = "reset_evaluation";
pub const EVALUATOR_CHANNEL_DATA_ACTION: &str = "action";
pub const EVALUATOR_CHANNEL_DATA_EXCHANGE_ID: &str = "exchange_id";
pub const EVALUATOR_CHANNEL_DATA_TIME_FRAMES: &str = "time_frames";
