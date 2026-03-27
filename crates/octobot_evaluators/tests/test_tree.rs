use octobot_evaluators::tree::base_tree::{BaseTree, BaseTreeNode};
use octobot_evaluators::tree::node_value::NodeValue;

fn path(segments: &[&str]) -> Vec<String> {
    segments.iter().map(|s| s.to_string()).collect()
}

// ---------------------------------------------------------------------------
// BaseTree basics
// ---------------------------------------------------------------------------

#[test]
fn test_default_tree_root_has_no_children() {
    let tree: BaseTree<NodeValue> = BaseTree::new();
    assert!(tree.root.children.is_empty());
}

#[test]
fn test_get_or_create_node_creates_intermediate_nodes() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let p = path(&["a", "b", "c"]);
    let node = tree.get_or_create_node(&p);
    node.node_value = Some(NodeValue::Float(42.0));

    // Verify the full path is traversable via get_node
    let fetched = tree.get_node(&p, None).expect("node should exist");
    assert_eq!(fetched.node_value, Some(NodeValue::Float(42.0)));
}

#[test]
fn test_get_node_returns_error_for_missing_path() {
    let tree: BaseTree<NodeValue> = BaseTree::new();
    let result = tree.get_node(&path(&["nonexistent"]), None);
    assert!(result.is_err());
}

// ---------------------------------------------------------------------------
// set_node_at_path
// ---------------------------------------------------------------------------

#[test]
fn test_set_node_at_path_sets_value_type_and_timestamp() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let p = path(&["x", "y"]);
    tree.set_node_at_path(
        Some(NodeValue::Float(3.14)),
        Some(NodeValue::Str("float".into())),
        &p,
        1000.5,
        None,
        None,
    );

    let node = tree.get_node(&p, None).expect("node should exist");
    assert_eq!(node.node_value, Some(NodeValue::Float(3.14)));
    assert_eq!(node.node_type, Some(NodeValue::Str("float".into())));
    assert!((node.node_value_time - 1000.5).abs() < f64::EPSILON);
}

#[test]
fn test_set_node_at_path_preserves_existing_value_when_none_passed() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let p = path(&["keep"]);
    tree.set_node_at_path(Some(NodeValue::Int(7)), None, &p, 1.0, None, None);

    // Call again with value=None -- the original value should be preserved
    tree.set_node_at_path(None, None, &p, 2.0, None, None);

    let node = tree.get_node(&p, None).unwrap();
    assert_eq!(node.node_value, Some(NodeValue::Int(7)));
    // timestamp should be updated
    assert!((node.node_value_time - 2.0).abs() < f64::EPSILON);
}

// ---------------------------------------------------------------------------
// get_children_keys
// ---------------------------------------------------------------------------

#[test]
fn test_get_children_keys_returns_expected_keys() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&path(&["root_child", "a"]));
    tree.get_or_create_node(&path(&["root_child", "b"]));
    tree.get_or_create_node(&path(&["root_child", "c"]));

    let mut keys = tree
        .get_children_keys(&path(&["root_child"]))
        .expect("path should exist");
    keys.sort();
    assert_eq!(keys, vec!["a", "b", "c"]);
}

#[test]
fn test_get_children_keys_error_on_missing_path() {
    let tree: BaseTree<NodeValue> = BaseTree::new();
    let result = tree.get_children_keys(&path(&["missing"]));
    assert!(result.is_err());
}

// ---------------------------------------------------------------------------
// get_nested_children_with_path
// ---------------------------------------------------------------------------

#[test]
fn test_get_nested_children_with_path_leaves_only() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Int(1)),
        None,
        &path(&["a", "b", "leaf1"]),
        0.0,
        None,
        None,
    );
    tree.set_node_at_path(
        Some(NodeValue::Int(2)),
        None,
        &path(&["a", "b", "leaf2"]),
        0.0,
        None,
        None,
    );
    tree.set_node_at_path(
        Some(NodeValue::Int(3)),
        None,
        &path(&["a", "c"]),
        0.0,
        None,
        None,
    );

    let results = tree
        .get_nested_children_with_path(&path(&["a"]), true)
        .expect("path should exist");

    let mut paths: Vec<Vec<String>> = results.iter().map(|(_, p)| p.clone()).collect();
    paths.sort();
    // Leaves are: a > b > leaf1, a > b > leaf2, a > c
    assert_eq!(
        paths,
        vec![
            path(&["a", "b", "leaf1"]),
            path(&["a", "b", "leaf2"]),
            path(&["a", "c"]),
        ]
    );
}

#[test]
fn test_get_nested_children_with_path_all_nodes() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Int(1)),
        None,
        &path(&["a", "b"]),
        0.0,
        None,
        None,
    );

    let results = tree
        .get_nested_children_with_path(&path(&["a"]), false)
        .expect("path should exist");

    let mut paths: Vec<Vec<String>> = results.iter().map(|(_, p)| p.clone()).collect();
    paths.sort();
    // With leaves_only=false we get both the intermediate and the leaf
    assert_eq!(paths, vec![path(&["a"]), path(&["a", "b"]),]);
}

// ---------------------------------------------------------------------------
// delete_node
// ---------------------------------------------------------------------------

#[test]
fn test_delete_node_removes_and_returns_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Str("bye".into())),
        None,
        &path(&["d", "e"]),
        0.0,
        None,
        None,
    );

    let deleted = tree
        .delete_node(&path(&["d", "e"]))
        .expect("delete should succeed");
    assert_eq!(deleted.node_value, Some(NodeValue::Str("bye".into())));

    // The node should no longer be reachable
    assert!(tree.get_node(&path(&["d", "e"]), None).is_err());
    // Parent "d" should still exist but have no children
    let parent = tree.get_node(&path(&["d"]), None).unwrap();
    assert!(parent.children.is_empty());
}

#[test]
fn test_delete_node_error_on_missing_path() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let result = tree.delete_node(&path(&["nothing"]));
    assert!(result.is_err());
}

#[test]
fn test_delete_node_error_on_empty_path() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let result = tree.delete_node(&path(&[]));
    assert!(result.is_err());
}

// ---------------------------------------------------------------------------
// clear
// ---------------------------------------------------------------------------

#[test]
fn test_clear_empties_the_tree() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&path(&["a", "b"]));
    tree.get_or_create_node(&path(&["c"]));
    assert!(!tree.root.children.is_empty());

    tree.clear();
    assert!(tree.root.children.is_empty());
}

// ---------------------------------------------------------------------------
// NodeValue conversion / helper methods
// ---------------------------------------------------------------------------

#[test]
fn test_node_value_default_is_none() {
    let v: NodeValue = NodeValue::default();
    assert_eq!(v, NodeValue::None);
}

#[test]
fn test_node_value_is_some_and_is_none() {
    assert!(NodeValue::None.is_none());
    assert!(!NodeValue::None.is_some());

    assert!(NodeValue::Float(1.0).is_some());
    assert!(!NodeValue::Float(1.0).is_none());

    assert!(NodeValue::Int(0).is_some());
    assert!(NodeValue::Str("".into()).is_some());
    assert!(NodeValue::Bool(false).is_some());
}

#[test]
fn test_node_value_as_f64() {
    assert_eq!(NodeValue::Float(2.5).as_f64(), Some(2.5));
    assert_eq!(NodeValue::Int(10).as_f64(), Some(10.0));
    assert_eq!(NodeValue::Str("x".into()).as_f64(), None);
    assert_eq!(NodeValue::None.as_f64(), None);
    assert_eq!(NodeValue::Bool(true).as_f64(), None);
}

#[test]
fn test_node_value_as_str() {
    assert_eq!(NodeValue::Str("hello".into()).as_str(), Some("hello"));
    assert_eq!(NodeValue::Float(1.0).as_str(), None);
    assert_eq!(NodeValue::None.as_str(), None);
}

// ---------------------------------------------------------------------------
// BaseTreeNode direct usage
// ---------------------------------------------------------------------------

#[test]
fn test_base_tree_node_set_child_and_pop_child() {
    let mut parent: BaseTreeNode<NodeValue> = BaseTreeNode::default();
    let child = BaseTreeNode::new(Some(NodeValue::Bool(true)), None);
    parent.set_child("kid".to_string(), child);
    assert!(parent.children.contains_key("kid"));

    let popped = parent.pop_child("kid").expect("child should exist");
    assert_eq!(popped.node_value, Some(NodeValue::Bool(true)));
    assert!(!parent.children.contains_key("kid"));
}

#[test]
fn test_base_tree_node_pop_child_returns_none_for_missing_key() {
    let mut node: BaseTreeNode<NodeValue> = BaseTreeNode::default();
    assert!(node.pop_child("nope").is_none());
}
