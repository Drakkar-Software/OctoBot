use std::collections::HashMap;
use std::fmt;

#[derive(Debug)]
pub struct NodeExistsError;

impl fmt::Display for NodeExistsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("NodeExistsError: node does not exist at the given path")
    }
}

impl std::error::Error for NodeExistsError {}

/// Node element of a BaseTree. Generic over value type `T`.
///
/// In the pure Rust crate, `T` is typically `NodeValue`.
/// In the PyO3 bridge, `T` is `Py<PyAny>` for arbitrary Python objects.
pub struct BaseTreeNode<T> {
    pub node_value: Option<T>,
    pub node_value_time: f64,
    pub node_type: Option<T>,
    pub node_description: Option<T>,
    pub node_metadata: HashMap<String, T>,
    pub children: HashMap<String, BaseTreeNode<T>>,
}

impl<T> BaseTreeNode<T> {
    pub fn new(node_value: Option<T>, node_type: Option<T>) -> Self {
        Self {
            node_value,
            node_value_time: 0.0,
            node_type,
            node_description: None,
            node_metadata: HashMap::new(),
            children: HashMap::new(),
        }
    }

    pub fn set_child(&mut self, key: String, child: BaseTreeNode<T>) {
        self.children.insert(key, child);
    }

    pub fn pop_child(&mut self, key: &str) -> Option<BaseTreeNode<T>> {
        self.children.remove(key)
    }
}

impl<T> Default for BaseTreeNode<T> {
    fn default() -> Self {
        Self::new(None, None)
    }
}

/// Tree based on BaseTreeNode.
pub struct BaseTree<T> {
    pub root: BaseTreeNode<T>,
}

impl<T> BaseTree<T> {
    pub fn new() -> Self {
        Self {
            root: BaseTreeNode::default(),
        }
    }

    /// Set attributes on an existing node.
    pub fn set_node(
        node: &mut BaseTreeNode<T>,
        value: Option<T>,
        node_type: Option<T>,
        timestamp: f64,
    ) {
        Self::apply_values(node, value, node_type, timestamp, None, None);
    }

    /// Set node at path, creating intermediate nodes as needed.
    pub fn set_node_at_path(
        &mut self,
        value: Option<T>,
        node_type: Option<T>,
        path: &[String],
        timestamp: f64,
        description: Option<T>,
        metadata: Option<HashMap<String, T>>,
    ) {
        let node = self.get_or_create_node(path);
        Self::apply_values(node, value, node_type, timestamp, description, metadata);
    }

    /// Get immutable node at path. Returns error if path does not exist.
    pub fn get_node<'a>(
        &'a self,
        path: &[String],
        starting_node: Option<&'a BaseTreeNode<T>>,
    ) -> Result<&'a BaseTreeNode<T>, NodeExistsError> {
        let start = starting_node.unwrap_or(&self.root);
        Self::traverse(path, start)
    }

    /// Get mutable node at path, creating it if it does not exist.
    pub fn get_or_create_node(&mut self, path: &[String]) -> &mut BaseTreeNode<T> {
        let mut current = &mut self.root;
        for key in path {
            if !current.children.contains_key(key) {
                current
                    .children
                    .insert(key.clone(), BaseTreeNode::default());
            }
            current = current.children.get_mut(key).unwrap();
        }
        current
    }

    /// Get mutable node at path relative to a starting node index path.
    /// Use when you need a mutable reference from a known sub-path.
    pub fn get_or_create_node_from(
        &mut self,
        base_path: &[String],
        sub_path: &[String],
    ) -> &mut BaseTreeNode<T> {
        let full: Vec<String> = base_path
            .iter()
            .chain(sub_path.iter())
            .cloned()
            .collect();
        self.get_or_create_node(&full)
    }

    /// Delete node at path. Returns the deleted node or error.
    pub fn delete_node(
        &mut self,
        path: &[String],
    ) -> Result<BaseTreeNode<T>, NodeExistsError> {
        if path.is_empty() {
            return Err(NodeExistsError);
        }
        let parent_path = &path[..path.len() - 1];
        let key = &path[path.len() - 1];

        let parent = Self::traverse_mut(parent_path, &mut self.root)?;
        parent.pop_child(key).ok_or(NodeExistsError)
    }

    /// Get children keys of node at path.
    pub fn get_children_keys(
        &self,
        path: &[String],
    ) -> Result<Vec<String>, NodeExistsError> {
        let node = self.get_node(path, None)?;
        Ok(node.children.keys().cloned().collect())
    }

    /// Depth-first traversal yielding (node_ref, path) pairs.
    pub fn get_nested_children_with_path<'a>(
        &'a self,
        path: &[String],
        select_leaves_only: bool,
    ) -> Result<Vec<(&'a BaseTreeNode<T>, Vec<String>)>, NodeExistsError> {
        #![allow(clippy::type_complexity)]
        let mut results = Vec::new();
        self.collect_nested(path, select_leaves_only, &mut results)?;
        Ok(results)
    }

    /// Clear the tree.
    pub fn clear(&mut self) {
        self.root = BaseTreeNode::default();
    }

    // --- Private helpers ---

    fn traverse<'a>(
        path: &[String],
        start: &'a BaseTreeNode<T>,
    ) -> Result<&'a BaseTreeNode<T>, NodeExistsError> {
        let mut current = start;
        for key in path {
            current = current.children.get(key).ok_or(NodeExistsError)?;
        }
        Ok(current)
    }

    fn traverse_mut<'a>(
        path: &[String],
        start: &'a mut BaseTreeNode<T>,
    ) -> Result<&'a mut BaseTreeNode<T>, NodeExistsError> {
        let mut current = start;
        for key in path {
            current = current.children.get_mut(key).ok_or(NodeExistsError)?;
        }
        Ok(current)
    }

    fn apply_values(
        node: &mut BaseTreeNode<T>,
        value: Option<T>,
        node_type: Option<T>,
        timestamp: f64,
        description: Option<T>,
        metadata: Option<HashMap<String, T>>,
    ) {
        if value.is_some() {
            node.node_value = value;
        }
        if node_type.is_some() {
            node.node_type = node_type;
        }
        node.node_value_time = timestamp;
        if description.is_some() {
            node.node_description = description;
        }
        if let Some(meta) = metadata {
            node.node_metadata = meta;
        }
    }

    fn collect_nested<'a>(
        &'a self,
        parent_path: &[String],
        select_leaves_only: bool,
        results: &mut Vec<(&'a BaseTreeNode<T>, Vec<String>)>,
    ) -> Result<(), NodeExistsError> {
        let node = self.get_node(parent_path, None)?;
        let children_keys: Vec<String> = node.children.keys().cloned().collect();

        if children_keys.is_empty() || !select_leaves_only {
            results.push((node, parent_path.to_vec()));
        }

        for key in children_keys {
            let mut child_path = parent_path.to_vec();
            child_path.push(key);
            self.collect_nested(&child_path, select_leaves_only, results)?;
        }
        Ok(())
    }
}

impl<T> Default for BaseTree<T> {
    fn default() -> Self {
        Self::new()
    }
}
