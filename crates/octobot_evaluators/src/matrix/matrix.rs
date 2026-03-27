use std::collections::HashMap;

use uuid::Uuid;

use crate::tree::base_tree::{BaseTree, BaseTreeNode};

/// Matrix wraps a `BaseTree<T>` with a unique identifier.
///
/// Port of `packages/evaluators/octobot_evaluators/matrix/matrix.py`.
pub struct Matrix<T> {
    pub matrix_id: String,
    pub matrix: BaseTree<T>,
}

impl<T> Matrix<T> {
    pub fn new() -> Self {
        Self {
            matrix_id: Uuid::new_v4().to_string(),
            matrix: BaseTree::new(),
        }
    }

    /// Set a node value at the given path, creating intermediate nodes as needed.
    pub fn set_node_value(
        &mut self,
        value: Option<T>,
        value_type: Option<T>,
        value_path: &[String],
        timestamp: f64,
        description: Option<T>,
        metadata: Option<HashMap<String, T>>,
    ) {
        self.matrix
            .set_node_at_path(value, value_type, value_path, timestamp, description, metadata);
    }

    /// Get children of the node at `node_path` as a `Vec` of references.
    ///
    /// Returns an empty `Vec` if the path does not exist.
    pub fn get_node_children_at_path<'a>(
        &'a self,
        node_path: &[String],
        starting_node: Option<&'a BaseTreeNode<T>>,
    ) -> Vec<&'a BaseTreeNode<T>> {
        match self.matrix.get_node(node_path, starting_node) {
            Ok(node) => node.children.values().collect(),
            Err(_) => Vec::new(),
        }
    }

    /// Get children of the node at `node_path` as a `HashMap` keyed by child name.
    ///
    /// Returns an empty `HashMap` if the path does not exist.
    pub fn get_node_children_by_names_at_path<'a>(
        &'a self,
        node_path: &[String],
        starting_node: Option<&'a BaseTreeNode<T>>,
    ) -> HashMap<String, &'a BaseTreeNode<T>> {
        match self.matrix.get_node(node_path, starting_node) {
            Ok(node) => node
                .children
                .iter()
                .map(|(k, v)| (k.clone(), v))
                .collect(),
            Err(_) => HashMap::new(),
        }
    }

    /// Get an immutable reference to the node at `node_path`.
    ///
    /// Returns `None` if the path does not exist.
    pub fn get_node_at_path<'a>(
        &'a self,
        node_path: &[String],
        starting_node: Option<&'a BaseTreeNode<T>>,
    ) -> Option<&'a BaseTreeNode<T>> {
        self.matrix.get_node(node_path, starting_node).ok()
    }

    /// Delete the node at `node_path`, returning it if it existed.
    ///
    /// Returns `None` if the path does not exist.
    pub fn delete_node_at_path(
        &mut self,
        node_path: &[String],
    ) -> Option<BaseTreeNode<T>> {
        self.matrix.delete_node(node_path).ok()
    }
}

impl<T> Default for Matrix<T> {
    fn default() -> Self {
        Self::new()
    }
}
