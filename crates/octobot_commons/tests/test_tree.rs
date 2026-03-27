use octobot_commons::tree::base_tree::{BaseTree, BaseTreeNode, NodeExistsError};
use octobot_commons::tree::node_value::NodeValue;

fn p(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| s.to_string()).collect()
}

// --- BaseTreeNode tests ---

#[test]
fn test_base_tree_node_new() {
    let node: BaseTreeNode<NodeValue> = BaseTreeNode::new(
        Some(NodeValue::Int(42)),
        Some(NodeValue::Str("type".into())),
    );
    assert_eq!(node.node_value, Some(NodeValue::Int(42)));
    assert_eq!(node.node_type, Some(NodeValue::Str("type".into())));
    assert_eq!(node.node_value_time, 0.0);
    assert!(node.node_description.is_none());
    assert!(node.node_metadata.is_empty());
    assert!(node.children.is_empty());
}

#[test]
fn test_base_tree_node_default() {
    let node: BaseTreeNode<NodeValue> = BaseTreeNode::default();
    assert!(node.node_value.is_none());
    assert!(node.node_type.is_none());
}

#[test]
fn test_base_tree_node_set_child() {
    let mut node: BaseTreeNode<NodeValue> = BaseTreeNode::default();
    let child = BaseTreeNode::new(Some(NodeValue::Int(1)), None);
    node.set_child("child1".into(), child);
    assert!(node.children.contains_key("child1"));
    assert_eq!(
        node.children["child1"].node_value,
        Some(NodeValue::Int(1))
    );
}

#[test]
fn test_base_tree_node_pop_child() {
    let mut node: BaseTreeNode<NodeValue> = BaseTreeNode::default();
    node.set_child("child1".into(), BaseTreeNode::new(Some(NodeValue::Int(1)), None));
    let popped = node.pop_child("child1");
    assert!(popped.is_some());
    assert_eq!(popped.unwrap().node_value, Some(NodeValue::Int(1)));
    assert!(node.children.is_empty());

    // Pop non-existent child returns None
    assert!(node.pop_child("missing").is_none());
}

// --- BaseTree tests ---

#[test]
fn test_base_tree_init() {
    let tree: BaseTree<NodeValue> = BaseTree::new();
    assert!(tree.root.children.is_empty());
}

#[test]
fn test_base_tree_get_or_create_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let node = tree.get_or_create_node(&p(&["test"]));
    node.node_value = Some(NodeValue::Int(42));

    // Retrieve the same node
    let retrieved = tree.get_node(&p(&["test"]), None).unwrap();
    assert_eq!(retrieved.node_value, Some(NodeValue::Int(42)));
}

#[test]
fn test_base_tree_get_not_existing_node() {
    let tree: BaseTree<NodeValue> = BaseTree::new();
    let result = tree.get_node(&p(&["nonexistent"]), None);
    assert!(result.is_err());
}

#[test]
fn test_base_tree_delete_existing_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&p(&["test"])).node_value = Some(NodeValue::Int(1));

    let deleted = tree.delete_node(&p(&["test"]));
    assert!(deleted.is_ok());
    assert_eq!(deleted.unwrap().node_value, Some(NodeValue::Int(1)));

    // Node no longer exists
    assert!(tree.get_node(&p(&["test"]), None).is_err());
}

#[test]
fn test_base_tree_delete_not_existing_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    assert!(tree.delete_node(&p(&["nonexistent"])).is_err());
}

#[test]
fn test_base_tree_delete_empty_path() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    assert!(tree.delete_node(&p(&[])).is_err());
}

#[test]
fn test_base_tree_set_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    let node = tree.get_or_create_node(&p(&["test"]));
    BaseTree::set_node(node, Some(NodeValue::Int(1)), None, 5.0);
    assert_eq!(node.node_value, Some(NodeValue::Int(1)));
    assert!(node.node_type.is_none());
    assert_eq!(node.node_value_time, 5.0);

    // Update value
    BaseTree::set_node(node, Some(NodeValue::Int(5)), None, 10.0);
    assert_eq!(node.node_value, Some(NodeValue::Int(5)));
    assert_eq!(node.node_value_time, 10.0);
}

#[test]
fn test_base_tree_set_node_at_path() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Str("test-string".into())),
        Some(NodeValue::Str("test-type".into())),
        &p(&["a", "b", "c"]),
        1.0,
        None,
        None,
    );

    // Intermediate nodes created
    assert!(tree.get_node(&p(&["a"]), None).is_ok());
    assert!(tree.get_node(&p(&["a", "b"]), None).is_ok());

    // Leaf node has the values
    let leaf = tree.get_node(&p(&["a", "b", "c"]), None).unwrap();
    assert_eq!(leaf.node_value, Some(NodeValue::Str("test-string".into())));
    assert_eq!(leaf.node_type, Some(NodeValue::Str("test-type".into())));
    assert!(leaf.children.is_empty());
}

#[test]
fn test_base_tree_get_children_keys() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&p(&["test", "test2", "test3"]));
    tree.get_or_create_node(&p(&["test", "test2", "test3_2"]));
    tree.get_or_create_node(&p(&["test", "test3"]));

    let root_keys = tree.get_children_keys(&p(&[])).unwrap();
    assert_eq!(root_keys, vec!["test".to_string()]);

    let mut test_keys = tree.get_children_keys(&p(&["test"])).unwrap();
    test_keys.sort();
    assert_eq!(test_keys, vec!["test2".to_string(), "test3".to_string()]);

    let mut test2_keys = tree.get_children_keys(&p(&["test", "test2"])).unwrap();
    test2_keys.sort();
    assert_eq!(
        test2_keys,
        vec!["test3".to_string(), "test3_2".to_string()]
    );

    // Non-existent path raises error
    assert!(tree.get_children_keys(&p(&["nonexistent"])).is_err());
}

#[test]
fn test_base_tree_get_nested_children_leaves_only() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Int(1)),
        None,
        &p(&["a", "b", "c"]),
        0.0,
        None,
        None,
    );
    tree.set_node_at_path(
        Some(NodeValue::Int(2)),
        None,
        &p(&["a", "b", "d"]),
        0.0,
        None,
        None,
    );
    tree.set_node_at_path(
        Some(NodeValue::Int(3)),
        None,
        &p(&["a", "e"]),
        0.0,
        None,
        None,
    );

    let results = tree
        .get_nested_children_with_path(&p(&[]), true)
        .unwrap();
    let mut paths: Vec<Vec<String>> = results.iter().map(|(_, p)| p.clone()).collect();
    paths.sort();
    assert_eq!(
        paths,
        vec![
            p(&["a", "b", "c"]),
            p(&["a", "b", "d"]),
            p(&["a", "e"]),
        ]
    );
}

#[test]
fn test_base_tree_get_nested_children_all() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.set_node_at_path(
        Some(NodeValue::Int(1)),
        None,
        &p(&["a", "b"]),
        0.0,
        None,
        None,
    );

    let results = tree
        .get_nested_children_with_path(&p(&[]), false)
        .unwrap();
    let mut paths: Vec<Vec<String>> = results.iter().map(|(_, p)| p.clone()).collect();
    paths.sort();
    // Returns root, "a", and "a/b"
    assert_eq!(
        paths,
        vec![p(&[]), p(&["a"]), p(&["a", "b"])]
    );
}

#[test]
fn test_base_tree_clear() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&p(&["a", "b", "c"]));
    assert!(!tree.root.children.is_empty());
    tree.clear();
    assert!(tree.root.children.is_empty());
}

#[test]
fn test_base_tree_get_or_create_node_from() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&p(&["base", "path"]));
    let node = tree.get_or_create_node_from(&p(&["base", "path"]), &p(&["sub", "path"]));
    node.node_value = Some(NodeValue::Int(99));

    let retrieved = tree
        .get_node(&p(&["base", "path", "sub", "path"]), None)
        .unwrap();
    assert_eq!(retrieved.node_value, Some(NodeValue::Int(99)));
}

#[test]
fn test_base_tree_delete_nested_node() {
    let mut tree: BaseTree<NodeValue> = BaseTree::new();
    tree.get_or_create_node(&p(&["test", "child"]));

    // Delete child, parent remains
    let deleted = tree.delete_node(&p(&["test", "child"]));
    assert!(deleted.is_ok());
    assert!(tree.get_node(&p(&["test"]), None).is_ok());
    assert!(tree.get_node(&p(&["test", "child"]), None).is_err());
}

// --- NodeValue tests ---

#[test]
fn test_node_value_variants() {
    assert!(NodeValue::None.is_none());
    assert!(!NodeValue::None.is_some());

    let f = NodeValue::Float(3.14);
    assert!(f.is_some());
    assert_eq!(f.as_f64(), Some(3.14));

    let i = NodeValue::Int(42);
    assert_eq!(i.as_f64(), Some(42.0));

    let s = NodeValue::Str("hello".into());
    assert_eq!(s.as_str(), Some("hello"));

    let b = NodeValue::Bool(true);
    assert!(b.is_some());
    assert_eq!(b.as_f64(), None);
    assert_eq!(b.as_str(), None);
}

// --- NodeExistsError ---

#[test]
fn test_node_exists_error_display() {
    let err = NodeExistsError;
    let msg = format!("{err}");
    assert!(msg.contains("NodeExistsError"));
}
