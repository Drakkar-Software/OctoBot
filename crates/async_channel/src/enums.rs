#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ChannelConsumerPriorityLevels {
    High = 0,
    Medium = 1,
    Optional = 2,
}

impl ChannelConsumerPriorityLevels {
    pub fn value(self) -> i64 {
        self as i64
    }

    pub fn from_value(v: i64) -> Option<Self> {
        match v {
            0 => Some(Self::High),
            1 => Some(Self::Medium),
            2 => Some(Self::Optional),
            _ => None,
        }
    }
}
