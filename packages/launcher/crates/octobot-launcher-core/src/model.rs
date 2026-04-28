use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::net::IpAddr;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct InstanceId(pub uuid::Uuid);

impl InstanceId {
    pub fn new() -> Self {
        Self(uuid::Uuid::new_v4())
    }

    pub fn short(&self) -> String {
        self.0.to_string()[..8].to_string()
    }
}

impl Default for InstanceId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for InstanceId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", &self.0.to_string()[..8])
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeKind {
    Docker,
    Binary,
    Python,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceSpec {
    pub id: InstanceId,
    pub name: String,
    pub runtime: RuntimeKind,
    pub version: String,
    pub data_dir: PathBuf,
    pub config_dir: PathBuf,
    pub env: BTreeMap<String, String>,
    pub ports: Vec<PortMapping>,
    pub auto_restart: bool,
    pub auto_update: bool,
    pub runtime_options: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PortMapping {
    pub host: u16,
    pub container_or_internal: u16,
    #[serde(default = "default_bind_addr")]
    pub bind_addr: IpAddr,
}

fn default_bind_addr() -> IpAddr {
    "127.0.0.1".parse().expect("loopback is valid")
}

impl Default for PortMapping {
    fn default() -> Self {
        Self {
            host: 0,
            container_or_internal: 0,
            bind_addr: default_bind_addr(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum InstanceState {
    Stopped,
    Starting,
    Running {
        pid_or_container: String,
        started_at: chrono::DateTime<chrono::Utc>,
    },
    Stopping,
    Failed {
        reason: String,
        at: chrono::DateTime<chrono::Utc>,
    },
    Updating,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub state: InstanceState,
    pub uptime_seconds: Option<u64>,
    pub last_http_check: Option<HttpProbe>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HttpProbe {
    pub url: String,
    pub status_code: Option<u16>,
    pub latency_ms: Option<u32>,
    pub at: chrono::DateTime<chrono::Utc>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_spec() -> InstanceSpec {
        InstanceSpec {
            id: InstanceId::new(),
            name: "test-bot".into(),
            runtime: RuntimeKind::Docker,
            version: "2.4.42".into(),
            data_dir: PathBuf::from("/data"),
            config_dir: PathBuf::from("/config"),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        }
    }

    #[test]
    fn serde_roundtrip_instance_spec() {
        for runtime in [RuntimeKind::Docker, RuntimeKind::Binary, RuntimeKind::Python] {
            let mut spec = sample_spec();
            spec.runtime = runtime;
            let json = serde_json::to_string(&spec).unwrap();
            let back: InstanceSpec = serde_json::from_str(&json).unwrap();
            assert_eq!(back.name, spec.name);
            assert_eq!(back.runtime, spec.runtime);
            assert_eq!(back.version, spec.version);
        }
    }

    #[test]
    fn serde_roundtrip_instance_state() {
        let states = vec![
            InstanceState::Stopped,
            InstanceState::Starting,
            InstanceState::Running {
                pid_or_container: "abc123".into(),
                started_at: chrono::Utc::now(),
            },
            InstanceState::Stopping,
            InstanceState::Failed {
                reason: "oom".into(),
                at: chrono::Utc::now(),
            },
            InstanceState::Updating,
        ];
        for state in states {
            let json = serde_json::to_string(&state).unwrap();
            let back: InstanceState = serde_json::from_str(&json).unwrap();
            assert_eq!(back, state);
        }
    }

    #[test]
    fn port_mapping_default_bind_addr() {
        let pm = PortMapping::default();
        assert_eq!(pm.bind_addr, "127.0.0.1".parse::<IpAddr>().unwrap());
    }

    #[test]
    fn instance_id_display() {
        let id = InstanceId::new();
        let display = format!("{id}");
        assert_eq!(display.len(), 8);
        let debug = format!("{id:?}");
        assert!(debug.contains("InstanceId"));
    }
}
