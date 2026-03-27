use std::collections::HashMap;

/// Dynamic value stored in tree nodes.
/// Covers all types actually used by the evaluator matrix system.
#[derive(Clone, Debug, Default, PartialEq)]
pub enum NodeValue {
    #[default]
    None,
    Float(f64),
    Int(i64),
    Str(String),
    Bool(bool),
}

impl NodeValue {
    pub fn is_some(&self) -> bool {
        !matches!(self, NodeValue::None)
    }

    pub fn is_none(&self) -> bool {
        matches!(self, NodeValue::None)
    }

    pub fn as_f64(&self) -> Option<f64> {
        match self {
            NodeValue::Float(v) => Some(*v),
            NodeValue::Int(v) => Some(*v as f64),
            _ => Option::None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            NodeValue::Str(s) => Some(s),
            _ => Option::None,
        }
    }
}

/// Type tag for node values.
/// In Python this is a type object (e.g. `float`). In Rust we use an optional string tag.
pub type NodeType = Option<String>;

/// Metadata dict for tree nodes.
pub type NodeMetadata = HashMap<String, NodeValue>;
