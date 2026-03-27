use std::fmt;

#[derive(Debug)]
pub struct NodeExistsError;

impl fmt::Display for NodeExistsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("NodeExistsError: node does not exist at the given path")
    }
}

impl std::error::Error for NodeExistsError {}

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
