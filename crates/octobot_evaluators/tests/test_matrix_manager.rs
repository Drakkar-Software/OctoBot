//! Tests mirroring `packages/evaluators/tests/matrix/test_matrix_manager.py`.

use std::time::{SystemTime, UNIX_EPOCH};

use octobot_evaluators::matrix::matrices;
use octobot_evaluators::matrix::matrix::Matrix;
use octobot_evaluators::matrix::matrix_manager::*;
use octobot_evaluators::tree::node_value::NodeValue;

fn path(segments: &[&str]) -> Vec<String> {
    segments.iter().map(|s| s.to_string()).collect()
}

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

/// Helper: create a matrix, add to singleton, return its id.
fn setup_matrix() -> String {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();
    let lock = matrices::instance();
    let mut guard = lock.lock().unwrap();
    guard.add_matrix(m);
    id
}

fn teardown(matrix_id: &str) {
    let lock = matrices::instance();
    let mut guard = lock.lock().unwrap();
    guard.del_matrix(matrix_id);
}

// ---------------------------------------------------------------------------
// Path builder tests (mirrors test_get_tentacle_path, test_get_tentacle_value_path,
// test_get_matrix_default_value_path)
// ---------------------------------------------------------------------------

#[test]
fn test_get_tentacle_path() {
    assert_eq!(
        get_tentacle_path(Some("binance"), Some("TA"), Some("Test-TA")),
        vec!["binance", "TA", "Test-TA"]
    );
    assert_eq!(
        get_tentacle_path(None, Some("TA"), Some("Test-TA")),
        vec!["TA", "Test-TA"]
    );
    assert_eq!(
        get_tentacle_path(Some("binance"), None, Some("Test-TA")),
        vec!["binance", "Test-TA"]
    );
    assert_eq!(
        get_tentacle_path(None, None, Some("Test-TA")),
        vec!["Test-TA"]
    );
}

#[test]
fn test_get_tentacle_value_path() {
    assert!(get_tentacle_value_path(None, None, None).is_empty());
    assert_eq!(
        get_tentacle_value_path(None, Some("BTC"), None),
        vec!["BTC"]
    );
    assert_eq!(
        get_tentacle_value_path(None, None, Some("1m")),
        vec!["1m"]
    );
    assert_eq!(
        get_tentacle_value_path(None, Some("ETH"), Some("1h")),
        vec!["ETH", "1h"]
    );
}

#[test]
fn test_get_matrix_default_value_path() {
    assert_eq!(
        get_matrix_default_value_path("Test-TA", "TA", Some("binance"), None, None, None),
        get_tentacle_path(Some("binance"), Some("TA"), Some("Test-TA"))
    );
    let mut expected = get_tentacle_path(None, Some("TA"), Some("Test-TA"));
    expected.extend(get_tentacle_value_path(None, Some("ETH"), Some("1h")));
    assert_eq!(
        get_matrix_default_value_path("Test-TA", "TA", None, None, Some("ETH"), Some("1h")),
        expected
    );
    let mut expected2 = get_tentacle_path(Some("bitmex"), Some("TA"), Some("Test-TA"));
    expected2.extend(get_tentacle_value_path(None, Some("ETH"), None));
    assert_eq!(
        get_matrix_default_value_path("Test-TA", "TA", Some("bitmex"), None, Some("ETH"), None),
        expected2
    );
}

// ---------------------------------------------------------------------------
// set_tentacle_value / get_tentacle_value
// ---------------------------------------------------------------------------

#[test]
fn test_set_tentacle_value() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &path(&["test-path"]),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(0)),
        0.0,
        None,
        None,
    );
    assert_eq!(
        get_tentacle_value(&id, &path(&["test-path"])),
        Some(NodeValue::Int(0))
    );

    let tp = get_tentacle_path(Some("binance"), Some("TA"), Some("Test-TA"));
    set_tentacle_value(
        &id,
        &tp,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Str("value".into())),
        0.0,
        None,
        None,
    );
    assert_eq!(
        get_tentacle_value(&id, &tp),
        Some(NodeValue::Str("value".into()))
    );
    teardown(&id);
}

#[test]
fn test_get_tentacle_value() {
    let id = setup_matrix();

    // Non-existent path returns None
    assert!(get_tentacle_value(&id, &path(&["Test-TA"])).is_none());

    // Create node and set value
    set_tentacle_value(
        &id,
        &path(&["Test-TA"]),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(0)),
        0.0,
        None,
        None,
    );
    assert_eq!(
        get_tentacle_value(&id, &path(&["Test-TA"])),
        Some(NodeValue::Int(0))
    );

    let tp = get_tentacle_path(None, Some("TA"), Some("Test-TA"));
    set_tentacle_value(
        &id,
        &tp,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Str("test".into())),
        0.0,
        None,
        None,
    );
    assert_eq!(
        get_tentacle_value(&id, &tp),
        Some(NodeValue::Str("test".into()))
    );
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_tentacle_nodes (mirrors test_get_tentacle_nodes_*)
// ---------------------------------------------------------------------------

#[test]
fn test_get_tentacle_nodes_on_root() {
    let id = setup_matrix();
    // Create: ["NO_TYPE", "Test-TA"], ["binance", "Test-TA-2"], ["Test-TA-3"]
    set_tentacle_value(&id, &path(&["NO_TYPE", "Test-TA"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["binance", "Test-TA-2"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["Test-TA-3"]), None, None, 0.0, None, None);

    // Root children: NO_TYPE, binance, Test-TA-3
    assert_eq!(get_tentacle_nodes(&id, None, None, None).len(), 3);
    assert_eq!(get_tentacle_nodes(&id, None, Some("TA"), None).len(), 0);
    assert_eq!(get_tentacle_nodes(&id, Some("bitfinex"), None, None).len(), 0);
    assert_eq!(get_tentacle_nodes(&id, None, Some("NO_TYPE"), None).len(), 1);
    assert_eq!(get_tentacle_nodes(&id, Some("binance"), None, None).len(), 1);
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_on_tentacle_type() {
    let id = setup_matrix();
    set_tentacle_value(&id, &path(&["NO_TYPE", "Test-TA"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TEST_TYPE", "Test-TA-2"]), None, None, 0.0, None, None);

    assert_eq!(get_tentacle_nodes(&id, None, Some("TA"), None).len(), 0);
    assert_eq!(get_tentacle_nodes(&id, None, Some("NO_TYPE"), None).len(), 1);
    assert_eq!(get_tentacle_nodes(&id, None, Some("TEST_TYPE"), None).len(), 1);
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_on_exchange_name_and_tentacle_type() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &path(&["binance", "NO_TYPE", "Test-TA"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["binance", "TEST_TYPE", "Test-TA-2"]),
        None, None, 0.0, None, None,
    );

    // Children of ["binance"]: NO_TYPE, TEST_TYPE
    let nodes = get_tentacle_nodes(&id, Some("binance"), None, None);
    assert_eq!(nodes.len(), 2);

    // Children of ["binance", "NO_TYPE"]: Test-TA
    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), Some("NO_TYPE"), None).len(),
        1
    );
    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), Some("TEST_TYPE"), None).len(),
        1
    );
    assert_eq!(
        get_tentacle_nodes(&id, Some("bitfinex"), None, None).len(),
        0
    );
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_on_exchange_name() {
    let id = setup_matrix();
    set_tentacle_value(&id, &path(&["binance", "Test-TA"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["binance", "Test-TA-2"]), None, None, 0.0, None, None);

    assert_eq!(
        get_tentacle_nodes(&id, Some("bitfinex"), None, None).len(),
        0
    );
    assert_eq!(get_tentacle_nodes(&id, None, Some("NO_TYPE"), None).len(), 0);
    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), None, None).len(),
        2
    );
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_on_multiple_tentacle_type() {
    let id = setup_matrix();
    set_tentacle_value(&id, &path(&["TA", "Test-TA"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA-2"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA-3"]), None, None, 0.0, None, None);

    assert_eq!(get_tentacle_nodes(&id, None, Some("TA"), None).len(), 3);
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_on_multiple_tentacle_type_and_exchange_name() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &path(&["binance", "TA", "Test-TA"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["binance", "TA", "Test-TA-2"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["binance", "TA", "Test-TA-3"]),
        None, None, 0.0, None, None,
    );

    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), Some("TA"), None).len(),
        3
    );
    teardown(&id);
}

#[test]
fn test_get_tentacle_nodes_mixed() {
    let id = setup_matrix();
    // 9 nodes with various combinations
    set_tentacle_value(&id, &path(&["binance", "TA", "Test-TA"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["bitfinex", "TA", "Test-TA-2"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["binance", "TA", "Test-TA-3"]), None, None, 0.0, None, None);
    set_tentacle_value(
        &id,
        &path(&["binance", "TEST-TYPE", "Test-TA-4"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["bitfinex", "TEST-TYPE", "Test-TA-5"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(&id, &path(&["TEST-TYPE", "Test-TA-6"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["bitfinex", "Test-TA-7"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["Test-TA-8"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["binance", "Test-TA-9"]), None, None, 0.0, None, None);

    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), Some("TA"), None).len(),
        2
    ); // Test-TA, Test-TA-3
    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), Some("TEST-TYPE"), None).len(),
        1
    ); // Test-TA-4
    assert_eq!(
        get_tentacle_nodes(&id, Some("bitfinex"), Some("TEST-TYPE"), None).len(),
        1
    ); // Test-TA-5
    // bitfinex children: TA node, TEST-TYPE node, Test-TA-7
    assert_eq!(
        get_tentacle_nodes(&id, Some("bitfinex"), None, None).len(),
        3
    );
    // Root-level TEST-TYPE children: Test-TA-6
    assert_eq!(get_tentacle_nodes(&id, None, Some("TEST-TYPE"), None).len(), 1);
    // binance children: TA node, TEST-TYPE node, Test-TA-9
    assert_eq!(
        get_tentacle_nodes(&id, Some("binance"), None, None).len(),
        3
    );
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_tentacles_value_nodes (mirrors test_get_tentacles_value_nodes_*)
// ---------------------------------------------------------------------------

#[test]
fn test_get_tentacles_value_nodes_with_symbol() {
    let id = setup_matrix();
    // Create tentacle nodes with value sub-paths
    set_tentacle_value(&id, &path(&["TA", "Test-TA", "BTC"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA", "ETH"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA-2", "BTC"]), None, None, 0.0, None, None);

    let node1 = path(&["TA", "Test-TA"]);
    let node2 = path(&["TA", "Test-TA-2"]);

    assert_eq!(
        get_tentacles_value_nodes(&id, &[node1.clone(), node2.clone()], None, Some("BTC"), None)
            .len(),
        2
    );
    assert_eq!(
        get_tentacles_value_nodes(&id, &[node1.clone(), node2.clone()], None, Some("ETH"), None)
            .len(),
        1
    );
    teardown(&id);
}

#[test]
fn test_get_tentacles_value_nodes_with_time_frame() {
    let id = setup_matrix();
    set_tentacle_value(&id, &path(&["TA", "Test-TA", "1m"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA", "1h"]), None, None, 0.0, None, None);
    set_tentacle_value(&id, &path(&["TA", "Test-TA-2", "1h"]), None, None, 0.0, None, None);

    let node1 = path(&["TA", "Test-TA"]);
    let node2 = path(&["TA", "Test-TA-2"]);

    assert_eq!(
        get_tentacles_value_nodes(&id, &[node1.clone(), node2.clone()], None, None, Some("1h"))
            .len(),
        2
    );
    // "1m" as symbol (matches Python test behavior — path is ["1m"] either way)
    assert_eq!(
        get_tentacles_value_nodes(&id, &[node1.clone(), node2.clone()], None, Some("1m"), None)
            .len(),
        1
    );
    teardown(&id);
}

#[test]
fn test_get_tentacles_value_nodes_with_symbol_and_time_frame() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA", "BTC", "1h"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "BTC", "1m"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-3", "ETH", "1h"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "ETH", "1m"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA", "ETH", "1d"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "LTC", "1h"]),
        None, None, 0.0, None, None,
    );

    let node1 = path(&["TA", "Test-TA"]);
    let node2 = path(&["TA", "Test-TA-2"]);
    let node3 = path(&["TA", "Test-TA-3"]);
    let all = vec![node1.clone(), node2.clone(), node3.clone()];

    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("BTC"), Some("1h")).len(),
        1
    );
    // BTC without time_frame: finds BTC children nodes
    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("BTC"), None).len(),
        2
    );
    assert_eq!(
        get_tentacles_value_nodes(
            &id,
            &[node1.clone(), node3.clone()],
            None,
            Some("BTC"),
            None
        )
        .len(),
        1
    );
    assert_eq!(
        get_tentacles_value_nodes(
            &id,
            &[node1.clone(), node3.clone()],
            None,
            Some("BTC"),
            Some("1m")
        )
        .len(),
        0
    );
    assert_eq!(
        get_tentacles_value_nodes(&id, std::slice::from_ref(&node3), None, Some("BTC"), None).len(),
        0
    );
    // ETH from all three nodes
    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("ETH"), None).len(),
        3
    );
    teardown(&id);
}

#[test]
fn test_get_tentacles_value_nodes_mixed() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA", "BTC", "1h"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "BTC"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-3", "ETH"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "ETH", "1m"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA", "ETH", "1d"]),
        None, None, 0.0, None, None,
    );
    set_tentacle_value(
        &id,
        &path(&["TA", "Test-TA-2", "LTC", "1h"]),
        None, None, 0.0, None, None,
    );

    let node1 = path(&["TA", "Test-TA"]);
    let node2 = path(&["TA", "Test-TA-2"]);
    let node3 = path(&["TA", "Test-TA-3"]);
    let all = vec![node1.clone(), node2.clone(), node3.clone()];

    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("BTC"), Some("1h")).len(),
        1
    );
    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("BTC"), None).len(),
        2
    );
    assert_eq!(
        get_tentacles_value_nodes(
            &id,
            &[node1.clone(), node3.clone()],
            None,
            Some("BTC"),
            None
        )
        .len(),
        1
    );
    assert_eq!(
        get_tentacles_value_nodes(
            &id,
            &[node1.clone(), node3.clone()],
            None,
            Some("BTC"),
            Some("1m")
        )
        .len(),
        0
    );
    assert_eq!(
        get_tentacles_value_nodes(&id, std::slice::from_ref(&node3), None, Some("BTC"), None).len(),
        0
    );
    assert_eq!(
        get_tentacles_value_nodes(&id, &all, None, Some("ETH"), None).len(),
        3
    );
    teardown(&id);
}

// ---------------------------------------------------------------------------
// delete_tentacle_node
// ---------------------------------------------------------------------------

#[test]
fn test_delete_tentacle_node() {
    let id = setup_matrix();
    let eval1_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval2_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );

    set_tentacle_value(&id, &eval1_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);
    set_tentacle_value(&id, &eval2_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);

    // Non-existing path
    assert!(!delete_tentacle_node(&id, &path(&["non_existing"])));
    // Delete existing
    assert!(delete_tentacle_node(&id, &eval2_path));
    // Already deleted
    assert!(!delete_tentacle_node(&id, &eval2_path));
    teardown(&id);
}

// ---------------------------------------------------------------------------
// is_tentacle_value_valid / is_tentacles_values_valid
// ---------------------------------------------------------------------------

#[test]
fn test_is_tentacle_value_valid() {
    let id = setup_matrix();
    let eval1_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval2_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );

    // Initialize nodes
    set_tentacle_value(&id, &eval1_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);
    set_tentacle_value(&id, &eval2_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);

    // Set eval1 timestamp to now — should be valid (1m = 1 minute)
    set_tentacle_value(&id, &eval1_path, None, None, now(), None, None);
    assert!(is_tentacle_value_valid(&id, &eval1_path, 1.0, 0.0, None));
    // eval2 still has timestamp 0 — not valid
    assert!(!is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // Set eval2 to old timestamp (100s)
    set_tentacle_value(&id, &eval2_path, None, None, 100.0, None, None);
    assert!(!is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // Set eval2 to now - 2*60*60 (2 hours ago) — for 1h timeframe, not valid
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 2.0 * 60.0,
        None,
        None,
    );
    assert!(!is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // Set eval2 to now - 60*60 (1 hour ago) — for 1h timeframe with 10s delta, valid
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0,
        None,
        None,
    );
    assert!(is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // Non-existing node
    assert!(!is_tentacle_value_valid(
        &id,
        &path(&["nonexistent"]),
        60.0,
        0.0,
        None
    ));

    // Test delta: set to now - 60*60 - 10 (just outside default delta)
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0 - 10.0,
        None,
        None,
    );
    assert!(!is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // now - 60*60 - 9 (just inside default delta=10)
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0 - 9.0,
        None,
        None,
    );
    assert!(is_tentacle_value_valid(&id, &eval2_path, 60.0, 0.0, None));

    // Custom delta=30: now - 60*60 - 29
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0 - 29.0,
        None,
        None,
    );
    assert!(is_tentacle_value_valid(
        &id,
        &eval2_path,
        60.0,
        0.0,
        Some(30.0)
    ));

    // Custom delta=30: now - 60*60 - 31 (outside)
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0 - 31.0,
        None,
        None,
    );
    assert!(!is_tentacle_value_valid(
        &id,
        &eval2_path,
        60.0,
        0.0,
        Some(30.0)
    ));
    teardown(&id);
}

#[test]
fn test_is_tentacles_values_valid() {
    let id = setup_matrix();
    let eval1_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval2_path = get_matrix_default_value_path(
        "Test-TA",
        "TA",
        None,
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );

    // Initialize with no timestamp — both invalid
    set_tentacle_value(&id, &eval1_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);
    set_tentacle_value(&id, &eval2_path, Some(NodeValue::Str("TA".into())), None, 0.0, None, None);

    // Both paths have different time frames: 1m (1.0) and 1h (60.0)
    // For simplicity, test with a single time frame value since Rust API requires one
    // Check both invalid (timestamp 0)
    assert!(!is_tentacles_values_valid(
        &id,
        &[&eval1_path, &eval2_path],
        60.0,
        0.0,
        None
    ));

    // Set both to very old timestamps — still invalid
    set_tentacle_value(
        &id,
        &eval1_path,
        None,
        None,
        now() - 1.0 * 2.0 * 60.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 2.0 * 60.0,
        None,
        None,
    );
    assert!(!is_tentacles_values_valid(
        &id,
        &[&eval1_path, &eval2_path],
        60.0,
        0.0,
        None
    ));

    // Set both to recent timestamps — valid
    set_tentacle_value(
        &id,
        &eval1_path,
        None,
        None,
        now() - 60.0 * 60.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        None,
        now() - 60.0 * 60.0,
        None,
        None,
    );
    assert!(is_tentacles_values_valid(
        &id,
        &[&eval1_path, &eval2_path],
        60.0,
        0.0,
        None
    ));
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_evaluations_by_evaluator
// ---------------------------------------------------------------------------

#[test]
#[allow(clippy::needless_borrows_for_generic_args)]
fn test_get_evaluations_by_evaluator() {
    let id = setup_matrix();
    let eval1_path = get_matrix_default_value_path(
        "RSI",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval2_path = get_matrix_default_value_path(
        "ADX",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let _eval3_path = get_matrix_default_value_path(
        "ADX",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );

    // Set values
    set_tentacle_value(
        &id,
        &eval1_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(1)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval2_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Float(-0.5)),
        0.0,
        None,
        None,
    );

    let is_valid = |v: &NodeValue| v.is_some() && v.as_f64() != Some(0.0);

    let result = get_evaluations_by_evaluator(
        &id,
        Some("kraken"),
        Some("TA"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
        true,
        &is_valid,
    )
    .unwrap();
    assert_eq!(result.len(), 2);
    assert!(result.contains_key("RSI"));
    assert!(result.contains_key("ADX"));

    // Set ADX to invalid value (NodeValue::Str("0") simulates START_PENDING_EVAL_NOTE)
    set_tentacle_value(
        &id,
        &eval2_path,
        None,
        Some(NodeValue::Str("0".into())),
        0.0,
        None,
        None,
    );

    // With allow_missing=false, should error
    let is_valid_strict =
        |v: &NodeValue| v.is_some() && v.as_f64() != Some(0.0) && *v != NodeValue::Str("0".into());

    let result = get_evaluations_by_evaluator(
        &id,
        Some("kraken"),
        Some("TA"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
        false,
        &is_valid_strict,
    );
    assert!(result.is_err());

    // With allow_missing=true, ADX should be excluded
    let result = get_evaluations_by_evaluator(
        &id,
        Some("kraken"),
        Some("TA"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
        true,
        &is_valid_strict,
    )
    .unwrap();
    assert_eq!(result.len(), 1);
    assert!(result.contains_key("RSI"));

    // With a closure that accepts "0" string, both should be included
    let is_valid_allow_pending = |v: &NodeValue| v.is_some();
    let result = get_evaluations_by_evaluator(
        &id,
        Some("kraken"),
        Some("TA"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
        true,
        &is_valid_allow_pending,
    )
    .unwrap();
    assert_eq!(result.len(), 2);

    // Invalid path returns empty
    let result = get_evaluations_by_evaluator(
        &id,
        Some("kraken"),
        Some("TA_invalid"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
        true,
        &is_valid,
    )
    .unwrap();
    assert!(result.is_empty());
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_available_time_frames
// ---------------------------------------------------------------------------

#[test]
fn test_get_available_time_frames() {
    let id = setup_matrix();
    // Create multiple evaluator paths with different time frames
    let eval1_path = get_matrix_default_value_path(
        "RSI",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval2_path = get_matrix_default_value_path(
        "ADX",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1m"),
    );
    let eval3_path = get_matrix_default_value_path(
        "ADX",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );
    let eval4_path = get_matrix_default_value_path(
        "RSI",
        "TA",
        Some("kraken"),
        Some("BTC"),
        Some("BTC/USD"),
        Some("1h"),
    );

    set_tentacle_value(
        &id,
        &eval1_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(1)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval2_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Float(-0.5)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval3_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(0)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &eval4_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(-1)),
        0.0,
        None,
        None,
    );

    let mut tfs = get_available_time_frames(&id, "kraken", "TA", "BTC", "BTC/USD");
    tfs.sort();
    assert_eq!(tfs, vec!["1h", "1m"]);

    // Invalid path returns empty
    let tfs = get_available_time_frames(&id, "kraken", "TA_invalid", "BTC", "BTC/USD");
    assert!(tfs.is_empty());
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_available_symbols
// ---------------------------------------------------------------------------

#[test]
fn test_get_available_symbols() {
    let id = setup_matrix();
    set_tentacle_value(
        &id,
        &get_matrix_default_value_path(
            "RSI",
            "TA",
            Some("kraken"),
            Some("BTC"),
            Some("BTC/USD"),
            Some("1m"),
        ),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(1)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &get_matrix_default_value_path(
            "RSI",
            "TA",
            Some("kraken"),
            Some("BTC"),
            Some("BTCX/USDC"),
            Some("1m"),
        ),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Float(-0.5)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &get_matrix_default_value_path(
            "RSI",
            "TA",
            Some("kraken"),
            Some("BTC"),
            Some("BTCX/USDC"),
            Some("1h"),
        ),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(0)),
        0.0,
        None,
        None,
    );
    set_tentacle_value(
        &id,
        &get_matrix_default_value_path(
            "RSI",
            "TA",
            Some("kraken"),
            Some("BTC"),
            Some("BTC/USD"),
            Some("1h"),
        ),
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Int(-1)),
        0.0,
        None,
        None,
    );

    let mut syms = get_available_symbols(&id, "kraken", "BTC", Some("TA"), None);
    syms.sort();
    assert_eq!(syms, vec!["BTC/USD", "BTCX/USDC"]);

    // Invalid paths
    assert!(get_available_symbols(&id, "invalid_exchange", "BTC", Some("TA"), None).is_empty());
    assert!(get_available_symbols(&id, "kraken", "BTCX", Some("TA"), None).is_empty());

    // Real-time type fallback
    set_tentacle_value(
        &id,
        &get_matrix_default_value_path(
            "RSI",
            "REAL_TIME",
            Some("kraken"),
            Some("BTCX"),
            Some("BTCX/USD"),
            Some("1h"),
        ),
        Some(NodeValue::Str("REAL_TIME".into())),
        Some(NodeValue::Int(-1)),
        0.0,
        None,
        None,
    );
    assert_eq!(
        get_available_symbols(&id, "kraken", "BTCX", None, None),
        vec!["BTCX/USD"]
    );
    teardown(&id);
}

// ---------------------------------------------------------------------------
// get_latest_eval_time
// ---------------------------------------------------------------------------

#[test]
fn test_get_latest_eval_time() {
    let id = setup_matrix();
    let eval_path = get_matrix_default_value_path(
        "RSI",
        "TA",
        Some("binance"),
        Some("BTC"),
        Some("BTC/USDT"),
        Some("1h"),
    );
    set_tentacle_value(
        &id,
        &eval_path,
        Some(NodeValue::Str("TA".into())),
        Some(NodeValue::Float(0.5)),
        1000.0,
        None,
        None,
    );
    assert_eq!(
        get_latest_eval_time(
            &id,
            Some("binance"),
            Some("TA"),
            Some("BTC"),
            Some("BTC/USDT"),
            Some("1h")
        ),
        Some(1000.0)
    );
    teardown(&id);
}
