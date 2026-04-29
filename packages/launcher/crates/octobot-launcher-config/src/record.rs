use octobot_launcher_core::{InstanceSpec, InstanceState};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DesiredState {
    Running,
    Stopped,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceRecord {
    pub spec: InstanceSpec,
    pub desired_state: DesiredState,
    pub last_known_state: InstanceState,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}
