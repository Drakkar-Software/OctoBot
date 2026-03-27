//  Drakkar-Software OctoBot-Evaluators
//  Copyright (c) Drakkar-Software, All rights reserved.
//
//  This library is free software; you can redistribute it and/or
//  modify it under the terms of the GNU Lesser General Public
//  License as published by the Free Software Foundation; either
//  version 3.0 of the License, or (at your option) any later version.
//
//  This library is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//  Lesser General Public License for more details.
//
//  You should have received a copy of the GNU Lesser General Public
//  License along with this library.

//! Port of `packages/evaluators/octobot_evaluators/matrix/matrix_manager.py`.
//!
//! Pure functions that operate on the [`Matrices`] singleton via
//! [`matrices::instance()`].

use std::collections::HashMap;

use crate::constants::EVALUATION_ALLOWED_TIME_DELTA;
use crate::enums::EvaluatorMatrixTypes;
use crate::errors::UnsetTentacleEvaluation;
use crate::matrix::matrices;
use crate::tree::base_tree::BaseTreeNode;
use crate::tree::node_value::NodeValue;

const MINUTE_TO_SECONDS: f64 = 60.0;

// ---------------------------------------------------------------------------
// EvaluationResult – returned by `get_evaluations_by_evaluator`
// ---------------------------------------------------------------------------

/// A single evaluation result extracted from the matrix.
#[derive(Clone, Debug)]
pub struct EvaluationResult {
    pub node_value: Option<NodeValue>,
    pub node_value_time: f64,
}

// ---------------------------------------------------------------------------
// Pure path builders (no state access)
// ---------------------------------------------------------------------------

/// Build a tentacle path from optional exchange name, tentacle type and
/// tentacle name.  `None` segments are omitted.
pub fn get_tentacle_path(
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    tentacle_name: Option<&str>,
) -> Vec<String> {
    let mut path = Vec::new();
    if let Some(v) = exchange_name {
        path.push(v.to_string());
    }
    if let Some(v) = tentacle_type {
        path.push(v.to_string());
    }
    if let Some(v) = tentacle_name {
        path.push(v.to_string());
    }
    path
}

/// Build a tentacle value path from optional cryptocurrency, symbol and
/// time frame.  `None` segments are omitted.
pub fn get_tentacle_value_path(
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Vec<String> {
    let mut path = Vec::new();
    if let Some(v) = cryptocurrency {
        path.push(v.to_string());
    }
    if let Some(v) = symbol {
        path.push(v.to_string());
    }
    if let Some(v) = time_frame {
        path.push(v.to_string());
    }
    path
}

/// Build the full default value path for a tentacle.
///
/// Equivalent to `get_tentacle_path(...) + get_tentacle_value_path(...)`.
pub fn get_matrix_default_value_path(
    tentacle_name: &str,
    tentacle_type: &str,
    exchange_name: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Vec<String> {
    let mut path = get_tentacle_path(exchange_name, Some(tentacle_type), Some(tentacle_name));
    path.extend(get_tentacle_value_path(cryptocurrency, symbol, time_frame));
    path
}

// ---------------------------------------------------------------------------
// Matrix accessors
// ---------------------------------------------------------------------------

/// Set a tentacle's node value at the given path, creating intermediate nodes
/// as needed.
pub fn set_tentacle_value(
    matrix_id: &str,
    tentacle_path: &[String],
    tentacle_type: Option<NodeValue>,
    tentacle_value: Option<NodeValue>,
    timestamp: f64,
    description: Option<NodeValue>,
    metadata: Option<HashMap<String, NodeValue>>,
) {
    let lock = matrices::instance();
    let mut matrices = lock.lock().unwrap();
    if let Some(matrix) = matrices.get_matrix_mut(matrix_id) {
        matrix.set_node_value(
            tentacle_value,
            tentacle_type,
            tentacle_path,
            timestamp,
            description,
            metadata,
        );
    }
}

/// Return a clone of the node at `tentacle_path`, or `None` if it does not
/// exist.
pub fn get_tentacle_node(
    matrix_id: &str,
    tentacle_path: &[String],
) -> Option<(Option<NodeValue>, f64)> {
    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let matrix = matrices.get_matrix(matrix_id)?;
    let node = matrix.get_node_at_path(tentacle_path, None)?;
    Some((node.node_value.clone(), node.node_value_time))
}

/// Delete the node at `tentacle_path`. Returns `true` if a node was deleted.
pub fn delete_tentacle_node(matrix_id: &str, tentacle_path: &[String]) -> bool {
    let lock = matrices::instance();
    let mut matrices = lock.lock().unwrap();
    if let Some(matrix) = matrices.get_matrix_mut(matrix_id) {
        matrix.delete_node_at_path(tentacle_path).is_some()
    } else {
        false
    }
}

/// Get the value of the node at `tentacle_path`, or `None` if it does not
/// exist.
pub fn get_tentacle_value(matrix_id: &str, tentacle_path: &[String]) -> Option<NodeValue> {
    get_tentacle_node(matrix_id, tentacle_path)
        .and_then(|(val, _)| val)
}

/// Get the evaluation time of the node at `tentacle_path`, or `None` if it
/// does not exist.
pub fn get_tentacle_eval_time(matrix_id: &str, tentacle_path: &[String]) -> Option<f64> {
    get_tentacle_node(matrix_id, tentacle_path).map(|(_, t)| t)
}

/// Return the children of the node at the tentacle path built from
/// `exchange_name`, `tentacle_type` and `tentacle_name`.
///
/// Because the Matrices singleton is behind a Mutex, we cannot return borrowed
/// references.  Instead we collect the children's `(name, node_value,
/// node_value_time)` triples.
pub fn get_tentacle_nodes(
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    tentacle_name: Option<&str>,
) -> Vec<TentacleNodeSnapshot> {
    let path = get_tentacle_path(exchange_name, tentacle_type, tentacle_name);
    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return Vec::new();
    };
    snapshot_children(matrix.get_node_children_at_path(&path, None))
}

/// Return the children of the node at `node_path` as a map keyed by child
/// name.
pub fn get_node_children_by_names_at_path(
    matrix_id: &str,
    node_path: &[String],
) -> HashMap<String, TentacleNodeSnapshot> {
    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return HashMap::new();
    };
    let children = matrix.get_node_children_by_names_at_path(node_path, None);
    children
        .into_iter()
        .map(|(name, node)| (name, snapshot_node(node)))
        .collect()
}

/// Return nodes at the value sub-path for each of the given tentacle nodes.
///
/// Filters out paths that do not resolve to a node. Operates under a single
/// lock acquisition.
pub fn get_tentacles_value_nodes(
    matrix_id: &str,
    tentacle_node_paths: &[Vec<String>],
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Vec<TentacleNodeSnapshot> {
    let value_path = get_tentacle_value_path(cryptocurrency, symbol, time_frame);
    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return Vec::new();
    };
    let mut results = Vec::new();
    for tentacle_path in tentacle_node_paths {
        // Navigate to the tentacle node first, then resolve the value sub-path.
        if let Some(tentacle_node) = matrix.get_node_at_path(tentacle_path, None) {
            if let Some(value_node) = matrix.get_node_at_path(&value_path, Some(tentacle_node)) {
                results.push(snapshot_node(value_node));
            }
        }
    }
    results
}

/// Return the latest evaluation time across all matching value nodes.
pub fn get_latest_eval_time(
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
) -> Option<f64> {
    let tentacle_path = get_tentacle_path(exchange_name, tentacle_type, None);
    let value_path = get_tentacle_value_path(cryptocurrency, symbol, time_frame);

    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let matrix = matrices.get_matrix(matrix_id)?;

    // Get the tentacle-level children (one per evaluator).
    let tentacle_children = matrix.get_node_children_at_path(&tentacle_path, None);

    let mut latest: Option<f64> = None;
    for tentacle_node in &tentacle_children {
        if let Some(value_node) = matrix.get_node_at_path(&value_path, Some(tentacle_node)) {
            let t = value_node.node_value_time;
            if t != 0.0 {
                latest = Some(match latest {
                    Some(prev) => prev.max(t),
                    None => t,
                });
            }
        }
    }
    latest
}

/// Return evaluations keyed by evaluator name.
///
/// The `is_valid` closure replaces the Python
/// `evaluators_util.check_valid_eval_note` call, keeping this crate free of
/// external dependencies.  Callers that want the original behaviour should pass
/// a closure equivalent to:
///
/// ```ignore
/// |v: &NodeValue| v.is_some() && v.as_f64() != Some(0.0)
/// ```
#[allow(clippy::too_many_arguments)]
pub fn get_evaluations_by_evaluator(
    matrix_id: &str,
    exchange_name: Option<&str>,
    tentacle_type: Option<&str>,
    cryptocurrency: Option<&str>,
    symbol: Option<&str>,
    time_frame: Option<&str>,
    allow_missing: bool,
    is_valid: impl Fn(&NodeValue) -> bool,
) -> Result<HashMap<String, EvaluationResult>, UnsetTentacleEvaluation> {
    let tentacle_path = get_tentacle_path(exchange_name, tentacle_type, None);
    let value_path = get_tentacle_value_path(cryptocurrency, symbol, time_frame);

    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return Ok(HashMap::new());
    };

    let evaluator_nodes = matrix.get_node_children_by_names_at_path(&tentacle_path, None);
    let mut evaluations: HashMap<String, EvaluationResult> = HashMap::new();

    for (evaluator_name, node) in &evaluator_nodes {
        // Resolve value sub-path from evaluator node.
        let evaluation = matrix.get_node_at_path(&value_path, Some(node));

        if let Some(eval_node) = evaluation {
            let eval_value = eval_node.node_value.clone().unwrap_or(NodeValue::None);
            if is_valid(&eval_value) {
                evaluations.insert(
                    evaluator_name.clone(),
                    EvaluationResult {
                        node_value: eval_node.node_value.clone(),
                        node_value_time: eval_node.node_value_time,
                    },
                );
            } else if !allow_missing {
                let tf_display = time_frame.unwrap_or("evaluation");
                let sym_display = symbol.unwrap_or("unknown");
                return Err(UnsetTentacleEvaluation {
                    message: format!(
                        "Missing {} for {} on {}, evaluation is {:?}).",
                        tf_display, evaluator_name, sym_display, eval_value
                    ),
                });
            }
        }
    }
    Ok(evaluations)
}

/// Return evaluation descriptions by evaluator name.
///
/// Currently unimplemented (mirrors the Python TODO).
pub fn get_evaluation_descriptions_by_evaluator(
    _matrix_id: &str,
    _exchange_name: Option<&str>,
    _tentacle_type: Option<&str>,
    _cryptocurrency: Option<&str>,
    _symbol: Option<&str>,
    _time_frame: Option<&str>,
    _allow_missing: bool,
) -> Option<HashMap<String, String>> {
    None // TODO
}

/// Return the list of available time frames for the given tentacle.
pub fn get_available_time_frames(
    matrix_id: &str,
    exchange_name: &str,
    tentacle_type: &str,
    cryptocurrency: &str,
    symbol: &str,
) -> Vec<String> {
    let tentacle_path = get_tentacle_path(Some(exchange_name), Some(tentacle_type), None);
    let value_path = get_tentacle_value_path(Some(cryptocurrency), Some(symbol), None);

    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return Vec::new();
    };

    let evaluator_nodes = matrix.get_node_children_by_names_at_path(&tentacle_path, None);
    let first_node = match evaluator_nodes.values().next() {
        Some(node) => *node,
        None => return Vec::new(),
    };
    let children = matrix.get_node_children_by_names_at_path(&value_path, Some(first_node));
    children.into_keys().collect()
}

/// Return the list of available symbols for the given cryptocurrency.
///
/// Looks up `tentacle_type` first; if no symbols are found and
/// `second_tentacle_type` differs, retries with the second type.
///
/// Defaults mirror Python:
/// - `tentacle_type` = `EvaluatorMatrixTypes::TA`
/// - `second_tentacle_type` = `EvaluatorMatrixTypes::RealTime`
pub fn get_available_symbols(
    matrix_id: &str,
    exchange_name: &str,
    cryptocurrency: &str,
    tentacle_type: Option<&str>,
    second_tentacle_type: Option<&str>,
) -> Vec<String> {
    let tt = tentacle_type.unwrap_or(EvaluatorMatrixTypes::TA.as_str());
    let stt = second_tentacle_type.unwrap_or(EvaluatorMatrixTypes::RealTime.as_str());

    get_available_symbols_inner(matrix_id, exchange_name, cryptocurrency, tt, stt)
}

fn get_available_symbols_inner(
    matrix_id: &str,
    exchange_name: &str,
    cryptocurrency: &str,
    tentacle_type: &str,
    second_tentacle_type: &str,
) -> Vec<String> {
    let tentacle_path = get_tentacle_path(Some(exchange_name), Some(tentacle_type), None);
    let value_path = get_tentacle_value_path(Some(cryptocurrency), None, None);

    let lock = matrices::instance();
    let matrices = lock.lock().unwrap();
    let Some(matrix) = matrices.get_matrix(matrix_id) else {
        return Vec::new();
    };

    let evaluator_nodes = matrix.get_node_children_by_names_at_path(&tentacle_path, None);
    let first_node = match evaluator_nodes.values().next() {
        Some(node) => *node,
        None => return Vec::new(),
    };

    let possible_symbols: Vec<String> = matrix
        .get_node_children_by_names_at_path(&value_path, Some(first_node))
        .into_keys()
        .collect();

    if !possible_symbols.is_empty() {
        return possible_symbols;
    }

    // Retry with the second tentacle type if it differs.
    if tentacle_type != second_tentacle_type {
        // Drop the current lock before recursing.
        drop(matrices);
        drop(lock);
        return get_available_symbols_inner(
            matrix_id,
            exchange_name,
            cryptocurrency,
            second_tentacle_type,
            second_tentacle_type,
        );
    }

    Vec::new()
}

// ---------------------------------------------------------------------------
// Time-validity checks
// ---------------------------------------------------------------------------

/// Check whether a tentacle's evaluation is still valid in time.
///
/// `time_frame_minutes` is the number of minutes for the evaluation's time
/// frame.  The caller must resolve the `TimeFrames` enum to minutes before
/// calling this function (keeps this crate free of the `octobot_commons`
/// dependency on `TimeFrames`).
pub fn is_tentacle_value_valid(
    matrix_id: &str,
    tentacle_path: &[String],
    time_frame_minutes: f64,
    timestamp: f64,
    delta: Option<f64>,
) -> bool {
    let ts = if timestamp == 0.0 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    } else {
        timestamp
    };
    let allowed = delta.unwrap_or(EVALUATION_ALLOWED_TIME_DELTA);

    match get_tentacle_node(matrix_id, tentacle_path) {
        Some((_, eval_time)) => is_evaluation_valid_in_time(ts, eval_time, time_frame_minutes, allowed),
        None => false,
    }
}

/// Check whether an evaluation timestamp is still valid relative to the
/// current time, the time frame duration and an allowed delta.
///
/// `time_frame_minutes` is the number of minutes for the evaluation's time
/// frame.  The formula matches the Python original:
///
/// ```text
/// current_time - (evaluation_time + time_frame_minutes * 60 + allowed_delta) < 0
/// ```
pub fn is_evaluation_valid_in_time(
    current_time: f64,
    evaluation_time: f64,
    time_frame_minutes: f64,
    allowed_delta: f64,
) -> bool {
    current_time - (evaluation_time + time_frame_minutes * MINUTE_TO_SECONDS + allowed_delta) < 0.0
}

/// Check whether all tentacle values in the list are valid.
pub fn is_tentacles_values_valid(
    matrix_id: &str,
    tentacle_path_list: &[&[String]],
    time_frame_minutes: f64,
    timestamp: f64,
    delta: Option<f64>,
) -> bool {
    tentacle_path_list.iter().all(|path| {
        is_tentacle_value_valid(matrix_id, path, time_frame_minutes, timestamp, delta)
    })
}

// ---------------------------------------------------------------------------
// Snapshot helpers – extract owned data from borrowed tree nodes
// ---------------------------------------------------------------------------

/// Owned snapshot of a tree node, safe to return outside a Mutex guard scope.
#[derive(Clone, Debug)]
pub struct TentacleNodeSnapshot {
    pub node_value: Option<NodeValue>,
    pub node_value_time: f64,
    pub children_names: Vec<String>,
}

fn snapshot_node(node: &BaseTreeNode<NodeValue>) -> TentacleNodeSnapshot {
    TentacleNodeSnapshot {
        node_value: node.node_value.clone(),
        node_value_time: node.node_value_time,
        children_names: node.children.keys().cloned().collect(),
    }
}

fn snapshot_children(nodes: Vec<&BaseTreeNode<NodeValue>>) -> Vec<TentacleNodeSnapshot> {
    nodes.into_iter().map(snapshot_node).collect()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::matrix::matrices;
    use crate::matrix::matrix::Matrix;
    use crate::tree::node_value::NodeValue;

    /// Helper: create a matrix, register it in the singleton, return its id.
    fn setup_matrix() -> String {
        let mut m = Matrix::<NodeValue>::new();
        let id = m.matrix_id.clone();
        // Populate a small tree:
        //   binance -> TA -> rsi -> BTC -> BTC/USDT -> 1h
        let path: Vec<String> = vec![
            "binance".into(),
            "TA".into(),
            "rsi".into(),
            "BTC".into(),
            "BTC/USDT".into(),
            "1h".into(),
        ];
        m.set_node_value(
            Some(NodeValue::Float(0.5)),
            Some(NodeValue::Str("float".into())),
            &path,
            1000.0,
            None,
            None,
        );
        let lock = matrices::instance();
        let mut matrices = lock.lock().unwrap();
        matrices.add_matrix(m);
        id
    }

    fn teardown(matrix_id: &str) {
        let lock = matrices::instance();
        let mut matrices = lock.lock().unwrap();
        matrices.del_matrix(matrix_id);
    }

    #[test]
    fn test_get_tentacle_path() {
        assert_eq!(
            get_tentacle_path(Some("binance"), Some("TA"), Some("rsi")),
            vec!["binance", "TA", "rsi"]
        );
        assert_eq!(
            get_tentacle_path(None, Some("TA"), None),
            vec!["TA"]
        );
        assert!(get_tentacle_path(None, None, None).is_empty());
    }

    #[test]
    fn test_get_tentacle_value_path() {
        assert_eq!(
            get_tentacle_value_path(Some("BTC"), Some("BTC/USDT"), Some("1h")),
            vec!["BTC", "BTC/USDT", "1h"]
        );
        assert_eq!(
            get_tentacle_value_path(None, Some("BTC/USDT"), None),
            vec!["BTC/USDT"]
        );
    }

    #[test]
    fn test_get_matrix_default_value_path() {
        let path = get_matrix_default_value_path(
            "rsi",
            "TA",
            Some("binance"),
            Some("BTC"),
            Some("BTC/USDT"),
            Some("1h"),
        );
        assert_eq!(
            path,
            vec!["binance", "TA", "rsi", "BTC", "BTC/USDT", "1h"]
        );
    }

    #[test]
    fn test_set_and_get_tentacle_value() {
        let id = setup_matrix();
        let path: Vec<String> = vec![
            "binance".into(),
            "TA".into(),
            "rsi".into(),
            "BTC".into(),
            "BTC/USDT".into(),
            "1h".into(),
        ];
        let val = get_tentacle_value(&id, &path);
        assert_eq!(val, Some(NodeValue::Float(0.5)));
        teardown(&id);
    }

    #[test]
    fn test_get_tentacle_eval_time() {
        let id = setup_matrix();
        let path: Vec<String> = vec![
            "binance".into(),
            "TA".into(),
            "rsi".into(),
            "BTC".into(),
            "BTC/USDT".into(),
            "1h".into(),
        ];
        let t = get_tentacle_eval_time(&id, &path);
        assert_eq!(t, Some(1000.0));
        teardown(&id);
    }

    #[test]
    fn test_get_tentacle_value_nonexistent() {
        let id = setup_matrix();
        let path: Vec<String> = vec!["nope".into()];
        assert!(get_tentacle_value(&id, &path).is_none());
        teardown(&id);
    }

    #[test]
    fn test_delete_tentacle_node() {
        let id = setup_matrix();
        let path: Vec<String> = vec![
            "binance".into(),
            "TA".into(),
            "rsi".into(),
            "BTC".into(),
            "BTC/USDT".into(),
            "1h".into(),
        ];
        assert!(delete_tentacle_node(&id, &path));
        assert!(get_tentacle_value(&id, &path).is_none());
        teardown(&id);
    }

    #[test]
    fn test_is_evaluation_valid_in_time() {
        // evaluation_time=1000, tf_minutes=60 => covers up to 1000+3600+10 = 4610
        assert!(is_evaluation_valid_in_time(4609.0, 1000.0, 60.0, 10.0));
        assert!(!is_evaluation_valid_in_time(4611.0, 1000.0, 60.0, 10.0));
    }

    #[test]
    fn test_get_evaluations_by_evaluator() {
        let id = setup_matrix();
        let result = get_evaluations_by_evaluator(
            &id,
            Some("binance"),
            Some("TA"),
            Some("BTC"),
            Some("BTC/USDT"),
            Some("1h"),
            true,
            |v| v.is_some() && v.as_f64() != Some(0.0),
        )
        .unwrap();
        assert_eq!(result.len(), 1);
        assert!(result.contains_key("rsi"));
        let eval = result.get("rsi").unwrap();
        assert_eq!(eval.node_value, Some(NodeValue::Float(0.5)));
        assert_eq!(eval.node_value_time, 1000.0);
        teardown(&id);
    }

    #[test]
    fn test_get_evaluations_by_evaluator_not_allow_missing() {
        let id = setup_matrix();
        // Set the rsi value to 0 so check_valid_eval_note would fail.
        let path: Vec<String> = vec![
            "binance".into(),
            "TA".into(),
            "rsi".into(),
            "BTC".into(),
            "BTC/USDT".into(),
            "1h".into(),
        ];
        set_tentacle_value(
            &id,
            &path,
            None,
            Some(NodeValue::Float(0.0)),
            100.0,
            None,
            None,
        );
        let result = get_evaluations_by_evaluator(
            &id,
            Some("binance"),
            Some("TA"),
            Some("BTC"),
            Some("BTC/USDT"),
            Some("1h"),
            false,
            |v| v.is_some() && v.as_f64() != Some(0.0),
        );
        assert!(result.is_err());
        teardown(&id);
    }

    #[test]
    fn test_get_available_time_frames() {
        let id = setup_matrix();
        let tfs = get_available_time_frames(&id, "binance", "TA", "BTC", "BTC/USDT");
        assert_eq!(tfs, vec!["1h"]);
        teardown(&id);
    }

    #[test]
    fn test_get_available_symbols() {
        let id = setup_matrix();
        let syms = get_available_symbols(&id, "binance", "BTC", Some("TA"), None);
        assert_eq!(syms, vec!["BTC/USDT"]);
        teardown(&id);
    }

    #[test]
    fn test_get_latest_eval_time() {
        let id = setup_matrix();
        let t = get_latest_eval_time(&id, Some("binance"), Some("TA"), Some("BTC"), Some("BTC/USDT"), Some("1h"));
        assert_eq!(t, Some(1000.0));
        teardown(&id);
    }
}
