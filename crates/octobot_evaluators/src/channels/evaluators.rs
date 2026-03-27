use std::collections::HashMap;

use async_channel::constants::CHANNEL_WILDCARD;

use crate::channels::evaluator_channel::EvaluatorChannel;

// ---------------------------------------------------------------------------
// Filter key constants – mirror EvaluatorsChannel class attributes
// ---------------------------------------------------------------------------

pub const MATRIX_ID_KEY: &str = "matrix_id";
pub const EVALUATOR_NAME_KEY: &str = "evaluator_name";
pub const EVALUATOR_TYPE_KEY: &str = "evaluator_type";
pub const EXCHANGE_NAME_KEY: &str = "exchange_name";
pub const CRYPTOCURRENCY_KEY: &str = "cryptocurrency";
pub const SYMBOL_KEY: &str = "symbol";
pub const TIME_FRAME_KEY: &str = "time_frame";

// ---------------------------------------------------------------------------
// EvaluatorMessage
// ---------------------------------------------------------------------------

/// Typed message payload produced / consumed on an `EvaluatorsChannel`.
pub struct EvaluatorMessage {
    pub matrix_id: String,
    pub evaluator_name: String,
    pub evaluator_type: String,
    pub exchange_name: String,
    pub cryptocurrency: String,
    pub symbol: String,
    pub time_frame: String,
    pub data: HashMap<String, String>,
}

// ---------------------------------------------------------------------------
// EvaluatorsChannel
// ---------------------------------------------------------------------------

/// Channel dedicated to evaluator events. Wraps an `EvaluatorChannel` and
/// defines the set of filter keys used for routing.
/// Mirrors `evaluators/channel/evaluators.py`.
pub struct EvaluatorsChannel {
    pub inner: EvaluatorChannel,
}

impl EvaluatorsChannel {
    pub fn new(matrix_id: String) -> Self {
        Self {
            inner: EvaluatorChannel::new(matrix_id),
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Build a filter map from the standard evaluator keyword arguments.
/// Any `None` value is replaced by `CHANNEL_WILDCARD`.
pub fn build_filter_map(
    matrix_id: Option<&str>,
    evaluator_name: Option<&str>,
    evaluator_type: Option<&str>,
    exchange_name: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> HashMap<String, String> {
    let resolve = |v: Option<&str>| v.unwrap_or(CHANNEL_WILDCARD).to_string();
    let mut m = HashMap::with_capacity(7);
    m.insert(MATRIX_ID_KEY.to_string(), resolve(matrix_id));
    m.insert(EVALUATOR_NAME_KEY.to_string(), resolve(evaluator_name));
    m.insert(EVALUATOR_TYPE_KEY.to_string(), resolve(evaluator_type));
    m.insert(EXCHANGE_NAME_KEY.to_string(), resolve(exchange_name));
    m.insert(CRYPTOCURRENCY_KEY.to_string(), resolve(cryptocurrency));
    m.insert(SYMBOL_KEY.to_string(), resolve(symbol));
    m.insert(TIME_FRAME_KEY.to_string(), resolve(time_frame));
    m
}
