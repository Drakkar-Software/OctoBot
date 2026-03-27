use std::collections::HashMap;

use async_channel::constants::CHANNEL_WILDCARD;

use crate::channels::evaluator_channel::EvaluatorChannel;
use crate::tree::node_value::NodeValue;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

pub const FILTER_SIZE: usize = 1;

// Filter key constants – same keys as evaluators but listed in the order
// used by the Matrix channel Python source.
pub const MATRIX_ID_KEY: &str = "matrix_id";
pub const CRYPTOCURRENCY_KEY: &str = "cryptocurrency";
pub const SYMBOL_KEY: &str = "symbol";
pub const TIME_FRAME_KEY: &str = "time_frame";
pub const EVALUATOR_TYPE_KEY: &str = "evaluator_type";
pub const EXCHANGE_NAME_KEY: &str = "exchange_name";
pub const EVALUATOR_NAME_KEY: &str = "evaluator_name";

// ---------------------------------------------------------------------------
// MatrixMessage
// ---------------------------------------------------------------------------

/// Typed message payload produced / consumed on a `MatrixChannel`.
pub struct MatrixMessage {
    pub matrix_id: String,
    pub evaluator_name: String,
    pub evaluator_type: String,
    pub eval_note: Option<NodeValue>,
    pub eval_note_type: String,
    pub eval_note_description: Option<String>,
    pub eval_note_metadata: Option<HashMap<String, String>>,
    pub exchange_name: Option<String>,
    pub cryptocurrency: String,
    pub symbol: String,
    pub time_frame: Option<String>,
}

// ---------------------------------------------------------------------------
// MatrixChannel
// ---------------------------------------------------------------------------

/// Channel dedicated to matrix events. Wraps an `EvaluatorChannel` and
/// defines filter keys used for routing matrix updates.
/// Mirrors `matrix/channel/matrix.py`.
pub struct MatrixChannel {
    pub inner: EvaluatorChannel,
}

impl MatrixChannel {
    pub fn new(matrix_id: String) -> Self {
        Self {
            inner: EvaluatorChannel::new(matrix_id),
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Build a filter map from the standard matrix keyword arguments.
/// Any `None` value is replaced by `CHANNEL_WILDCARD`.
pub fn build_filter_map(
    matrix_id: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
    evaluator_type: Option<&str>,
    exchange_name: Option<&str>,
    evaluator_name: Option<&str>,
) -> HashMap<String, String> {
    let resolve = |v: Option<&str>| v.unwrap_or(CHANNEL_WILDCARD).to_string();
    let mut m = HashMap::with_capacity(7);
    m.insert(MATRIX_ID_KEY.to_string(), resolve(matrix_id));
    m.insert(CRYPTOCURRENCY_KEY.to_string(), resolve(cryptocurrency));
    m.insert(SYMBOL_KEY.to_string(), resolve(symbol));
    m.insert(TIME_FRAME_KEY.to_string(), resolve(time_frame));
    m.insert(EVALUATOR_TYPE_KEY.to_string(), resolve(evaluator_type));
    m.insert(EXCHANGE_NAME_KEY.to_string(), resolve(exchange_name));
    m.insert(EVALUATOR_NAME_KEY.to_string(), resolve(evaluator_name));
    m
}

/// Convenience constructor for a `MatrixMessage` with all fields specified.
#[allow(clippy::too_many_arguments)]
pub fn build_matrix_message(
    matrix_id: String,
    evaluator_name: String,
    evaluator_type: String,
    eval_note: Option<NodeValue>,
    eval_note_type: String,
    eval_note_description: Option<String>,
    eval_note_metadata: Option<HashMap<String, String>>,
    exchange_name: Option<String>,
    cryptocurrency: String,
    symbol: String,
    time_frame: Option<String>,
) -> MatrixMessage {
    MatrixMessage {
        matrix_id,
        evaluator_name,
        evaluator_type,
        eval_note,
        eval_note_type,
        eval_note_description,
        eval_note_metadata,
        exchange_name,
        cryptocurrency,
        symbol,
        time_frame,
    }
}
