use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

use crate::matrix::matrix::Matrix;
use crate::tree::node_value::NodeValue;

/// Singleton container for named Matrix instances.
///
/// Port of `packages/evaluators/octobot_evaluators/matrix/matrices.py`.
pub struct Matrices {
    pub matrices: HashMap<String, Matrix<NodeValue>>,
}

impl Matrices {
    pub fn new() -> Self {
        Matrices {
            matrices: HashMap::new(),
        }
    }

    /// Register a matrix. The matrix is stored under its own `matrix_id`.
    pub fn add_matrix(&mut self, matrix: Matrix<NodeValue>) {
        self.matrices.insert(matrix.matrix_id.clone(), matrix);
    }

    /// Get an immutable reference to a matrix by id.
    pub fn get_matrix(&self, matrix_id: &str) -> Option<&Matrix<NodeValue>> {
        self.matrices.get(matrix_id)
    }

    /// Get a mutable reference to a matrix by id.
    pub fn get_matrix_mut(&mut self, matrix_id: &str) -> Option<&mut Matrix<NodeValue>> {
        self.matrices.get_mut(matrix_id)
    }

    /// Remove a matrix by id.
    pub fn del_matrix(&mut self, matrix_id: &str) {
        self.matrices.remove(matrix_id);
    }
}

impl Default for Matrices {
    fn default() -> Self {
        Self::new()
    }
}

/// Global singleton instance.
static INSTANCE: OnceLock<Arc<Mutex<Matrices>>> = OnceLock::new();

pub fn instance() -> Arc<Mutex<Matrices>> {
    INSTANCE
        .get_or_init(|| Arc::new(Mutex::new(Matrices::new())))
        .clone()
}
