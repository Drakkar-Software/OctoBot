#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EvaluatorMatrixTypes {
    TA,
    Social,
    RealTime,
    Scripted,
    Strategies,
}

impl EvaluatorMatrixTypes {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::TA => "TA",
            Self::Social => "SOCIAL",
            Self::RealTime => "REAL_TIME",
            Self::Scripted => "SCRIPTED",
            Self::Strategies => "STRATEGIES",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "TA" => Some(Self::TA),
            "SOCIAL" => Some(Self::Social),
            "REAL_TIME" => Some(Self::RealTime),
            "SCRIPTED" => Some(Self::Scripted),
            "STRATEGIES" => Some(Self::Strategies),
            _ => None,
        }
    }
}

impl std::fmt::Display for EvaluatorMatrixTypes {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}
