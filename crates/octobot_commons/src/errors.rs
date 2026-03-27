use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("{0}")]
    Config(String),
    #[error("{0}")]
    Remote(String),
}

#[derive(Debug, Error)]
pub enum InvalidParametersError {
    #[error("{0}")]
    Base(String),
    #[error("{0}")]
    MissingDefaultValue(String),
    #[error("{0}")]
    InvalidFormat(String),
}

#[derive(Debug, Error)]
pub enum DSLInterpreterError {
    #[error("{0}")]
    Base(String),
    #[error("{0}")]
    UnsupportedOperator(String),
    #[error("{0}")]
    InvalidParameters(#[from] InvalidParametersError),
    #[error("{0}")]
    ResolvedParameterNotFound(String),
    #[error("{0}")]
    ErrorStatement(String),
}

#[derive(Debug, Error)]
pub enum CommonsError {
    #[error("{0}")]
    Config(#[from] ConfigError),
    #[error("{0}")]
    NoProfile(String),
    #[error("{0}")]
    ProfileConflict(String),
    #[error("{0}")]
    ProfileRemoval(String),
    #[error("{0}")]
    ProfileImport(String),
    #[error("{0}")]
    ConfigEvaluator(String),
    #[error("{0}")]
    ConfigTrading(String),
    #[error("{0}")]
    TentacleNotFound(String),
    #[error("{0}")]
    UninitializedCache(String),
    #[error("{0}")]
    NoCacheValue(String),
    #[error("{0}")]
    UncachableValue(String),
    #[error("{0}")]
    DatabaseNotFound(String),
    #[error("{0}")]
    MissingData(String),
    #[error("{0}")]
    MissingExchangeData(String),
    #[error("{0}")]
    ExecutionAborted(String),
    #[error("{0}")]
    LogicalOperator(String),
    #[error("{0}")]
    Unsupported(String),
    #[error("{0}")]
    InvalidUserInput(String),
    #[error("{0}")]
    MissingSignalBuilder(String),
    #[error("{0}")]
    DSLInterpreter(#[from] DSLInterpreterError),
}
