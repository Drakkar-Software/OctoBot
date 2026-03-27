//! Tests mirroring `packages/evaluators/tests/matrix/test_matrices.py`.

use octobot_evaluators::matrix::matrices;
use octobot_evaluators::matrix::matrix::Matrix;
use octobot_evaluators::tree::node_value::NodeValue;

#[test]
fn test_default_matrices() {
    let lock = matrices::instance();
    let guard = lock.lock().unwrap();
    // Getting a non-existent matrix returns None.
    assert!(guard.get_matrix("non-existent-id-matrices").is_none());
}

#[test]
fn test_add_matrix() {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();

    let lock = matrices::instance();
    let mut guard = lock.lock().unwrap();
    // Initially empty for this ID
    assert!(guard.get_matrix(&id).is_none());

    guard.add_matrix(m);

    assert!(guard.get_matrix(&id).is_some());
    assert_eq!(guard.get_matrix(&id).unwrap().matrix_id, id);

    // Cleanup
    guard.del_matrix(&id);
}

#[test]
fn test_get_matrix() {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();

    let lock = matrices::instance();
    let mut guard = lock.lock().unwrap();
    guard.add_matrix(m);

    assert!(guard.get_matrix(&id).is_some());
    // Non-existent suffix
    assert!(guard.get_matrix(&format!("{}t", id)).is_none());

    guard.del_matrix(&id);
}

#[test]
fn test_del_matrix() {
    let m: Matrix<NodeValue> = Matrix::new();
    let id = m.matrix_id.clone();

    let lock = matrices::instance();
    let mut guard = lock.lock().unwrap();
    guard.add_matrix(m);

    assert!(guard.get_matrix(&id).is_some());
    guard.del_matrix(&id);
    assert!(guard.get_matrix(&id).is_none());
}
