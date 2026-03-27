use std::fmt;

// NodeExistsError is now in octobot_commons::tree::base_tree
pub use octobot_commons::tree::base_tree::NodeExistsError;

#[derive(Debug)]
pub struct UnsetTentacleEvaluation {
    pub message: String,
}

impl fmt::Display for UnsetTentacleEvaluation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "UnsetTentacleEvaluation: {}", self.message)
    }
}

impl std::error::Error for UnsetTentacleEvaluation {}

#[derive(Debug)]
pub struct UnavailableEvaluatorError {
    pub message: String,
}

impl fmt::Display for UnavailableEvaluatorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "UnavailableEvaluatorError: {}", self.message)
    }
}

impl std::error::Error for UnavailableEvaluatorError {}
