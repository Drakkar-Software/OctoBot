use std::collections::HashMap;

use octobot_evaluators::matrix::matrix::Matrix;
use octobot_evaluators::matrix::matrices;
use octobot_evaluators::tree::node_value::NodeValue;

fn path(segments: &[&str]) -> Vec<String> {
    segments.iter().map(|s| s.to_string()).collect()
}

// ---------------------------------------------------------------------------
// Matrix basics
// ---------------------------------------------------------------------------

#[test]
fn test_matrix_new_has_uuid_format_id() {
    let m: Matrix<NodeValue> = Matrix::new();
    // UUID v4 string: 8-4-4-4-12 hex chars
    assert_eq!(m.matrix_id.len(), 36);
    let parts: Vec<&str> = m.matrix_id.split('-').collect();
    assert_eq!(parts.len(), 5);
    assert_eq!(parts[0].len(), 8);
    assert_eq!(parts[1].len(), 4);
    assert_eq!(parts[2].len(), 4);
    assert_eq!(parts[3].len(), 4);
    assert_eq!(parts[4].len(), 12);
}

#[test]
fn test_two_matrices_have_different_ids() {
    let m1: Matrix<NodeValue> = Matrix::new();
    let m2: Matrix<NodeValue> = Matrix::new();
    assert_ne!(m1.matrix_id, m2.matrix_id);
}

// ---------------------------------------------------------------------------
// set_node_value / get_node_at_path
// ---------------------------------------------------------------------------

#[test]
fn test_set_and_get_node_value() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    let p = path(&["exchange", "BTC", "price"]);
    m.set_node_value(
        Some(NodeValue::Float(50000.0)),
        Some(NodeValue::Str("float".into())),
        &p,
        1234.0,
        None,
        None,
    );

    let node = m.get_node_at_path(&p, None).expect("node should exist");
    assert_eq!(node.node_value, Some(NodeValue::Float(50000.0)));
    assert_eq!(node.node_type, Some(NodeValue::Str("float".into())));
    assert!((node.node_value_time - 1234.0).abs() < f64::EPSILON);
}

#[test]
fn test_get_node_at_path_returns_none_for_missing() {
    let m: Matrix<NodeValue> = Matrix::new();
    assert!(m.get_node_at_path(&path(&["no", "such"]), None).is_none());
}

// ---------------------------------------------------------------------------
// set_node_value with description and metadata
// ---------------------------------------------------------------------------

#[test]
fn test_set_node_value_with_description_and_metadata() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    let p = path(&["eval", "rsi"]);
    let mut meta = HashMap::new();
    meta.insert("source".to_string(), NodeValue::Str("binance".into()));

    m.set_node_value(
        Some(NodeValue::Float(70.0)),
        None,
        &p,
        99.0,
        Some(NodeValue::Str("RSI indicator".into())),
        Some(meta),
    );

    let node = m.get_node_at_path(&p, None).unwrap();
    assert_eq!(
        node.node_description,
        Some(NodeValue::Str("RSI indicator".into()))
    );
    assert_eq!(
        node.node_metadata.get("source"),
        Some(&NodeValue::Str("binance".into()))
    );
}

// ---------------------------------------------------------------------------
// get_node_children_at_path
// ---------------------------------------------------------------------------

#[test]
fn test_get_node_children_at_path() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    m.set_node_value(
        Some(NodeValue::Int(1)),
        None,
        &path(&["data", "child_a"]),
        0.0,
        None,
        None,
    );
    m.set_node_value(
        Some(NodeValue::Int(2)),
        None,
        &path(&["data", "child_b"]),
        0.0,
        None,
        None,
    );

    let children = m.get_node_children_at_path(&path(&["data"]), None);
    assert_eq!(children.len(), 2);

    // Collect values for an order-independent check
    let mut values: Vec<Option<&NodeValue>> = children.iter().map(|c| c.node_value.as_ref()).collect();
    values.sort_by(|a, b| format!("{:?}", a).cmp(&format!("{:?}", b)));
    assert!(values.contains(&Some(&NodeValue::Int(1))));
    assert!(values.contains(&Some(&NodeValue::Int(2))));
}

#[test]
fn test_get_node_children_at_path_returns_empty_for_missing() {
    let m: Matrix<NodeValue> = Matrix::new();
    let children = m.get_node_children_at_path(&path(&["nope"]), None);
    assert!(children.is_empty());
}

// ---------------------------------------------------------------------------
// get_node_children_by_names_at_path
// ---------------------------------------------------------------------------

#[test]
fn test_get_node_children_by_names_at_path() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    m.set_node_value(
        Some(NodeValue::Str("alpha".into())),
        None,
        &path(&["parent", "x"]),
        0.0,
        None,
        None,
    );
    m.set_node_value(
        Some(NodeValue::Str("beta".into())),
        None,
        &path(&["parent", "y"]),
        0.0,
        None,
        None,
    );

    let by_name = m.get_node_children_by_names_at_path(&path(&["parent"]), None);
    assert_eq!(by_name.len(), 2);
    assert!(by_name.contains_key("x"));
    assert!(by_name.contains_key("y"));
    assert_eq!(
        by_name["x"].node_value,
        Some(NodeValue::Str("alpha".into()))
    );
    assert_eq!(
        by_name["y"].node_value,
        Some(NodeValue::Str("beta".into()))
    );
}

#[test]
fn test_get_node_children_by_names_at_path_returns_empty_for_missing() {
    let m: Matrix<NodeValue> = Matrix::new();
    let by_name = m.get_node_children_by_names_at_path(&path(&["nope"]), None);
    assert!(by_name.is_empty());
}

// ---------------------------------------------------------------------------
// delete_node_at_path
// ---------------------------------------------------------------------------

#[test]
fn test_delete_node_at_path_removes_node() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    m.set_node_value(
        Some(NodeValue::Bool(true)),
        None,
        &path(&["del", "me"]),
        0.0,
        None,
        None,
    );

    let deleted = m
        .delete_node_at_path(&path(&["del", "me"]))
        .expect("should return deleted node");
    assert_eq!(deleted.node_value, Some(NodeValue::Bool(true)));

    // Node is gone
    assert!(m.get_node_at_path(&path(&["del", "me"]), None).is_none());
}

#[test]
fn test_delete_node_at_path_returns_none_for_missing() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    assert!(m.delete_node_at_path(&path(&["nothing"])).is_none());
}

// ---------------------------------------------------------------------------
// Matrices singleton: add, get, del
// ---------------------------------------------------------------------------

#[test]
fn test_matrices_add_and_get_matrix() {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();

    let singleton = matrices::instance();
    let mut guard = singleton.lock().unwrap();
    guard.add_matrix(m);

    assert!(guard.get_matrix(&id).is_some());
    assert_eq!(guard.get_matrix(&id).unwrap().matrix_id, id);

    // Cleanup
    guard.del_matrix(&id);
}

#[test]
fn test_matrices_del_matrix() {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();

    let singleton = matrices::instance();
    let mut guard = singleton.lock().unwrap();
    guard.add_matrix(m);
    assert!(guard.get_matrix(&id).is_some());

    guard.del_matrix(&id);
    assert!(guard.get_matrix(&id).is_none());
}

#[test]
fn test_matrices_get_missing_returns_none() {
    let singleton = matrices::instance();
    let guard = singleton.lock().unwrap();
    assert!(guard.get_matrix("does-not-exist").is_none());
}

#[test]
fn test_matrices_get_matrix_mut() {
    let mut m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();
    m.set_node_value(
        Some(NodeValue::Int(100)),
        None,
        &path(&["val"]),
        0.0,
        None,
        None,
    );

    let singleton = matrices::instance();
    let mut guard = singleton.lock().unwrap();
    guard.add_matrix(m);

    // Mutate through the singleton
    let matrix_mut = guard.get_matrix_mut(&id).unwrap();
    matrix_mut.set_node_value(
        Some(NodeValue::Int(200)),
        None,
        &path(&["val"]),
        1.0,
        None,
        None,
    );

    let node = guard
        .get_matrix(&id)
        .unwrap()
        .get_node_at_path(&path(&["val"]), None)
        .unwrap();
    assert_eq!(node.node_value, Some(NodeValue::Int(200)));

    // Cleanup
    guard.del_matrix(&id);
}

#[test]
fn test_matrices_multiple_matrices_independent() {
    let m1: Matrix<NodeValue> = Matrix::new();
    let m2: Matrix<NodeValue> = Matrix::new();
    let id1 = m1.matrix_id.clone();
    let id2 = m2.matrix_id.clone();

    let singleton = matrices::instance();
    let mut guard = singleton.lock().unwrap();
    guard.add_matrix(m1);
    guard.add_matrix(m2);

    assert!(guard.get_matrix(&id1).is_some());
    assert!(guard.get_matrix(&id2).is_some());
    assert_ne!(
        guard.get_matrix(&id1).unwrap().matrix_id,
        guard.get_matrix(&id2).unwrap().matrix_id
    );

    // Cleanup
    guard.del_matrix(&id1);
    guard.del_matrix(&id2);
}
