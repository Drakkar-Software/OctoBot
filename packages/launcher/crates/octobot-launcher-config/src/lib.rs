pub mod config;
pub mod error;
pub mod record;
pub mod store;

#[cfg(test)]
pub(crate) static TEST_ENV_LOCK: std::sync::OnceLock<std::sync::Mutex<()>> =
    std::sync::OnceLock::new();

pub use config::{
    BackendsSection, BinaryBackendConfig, DockerBackendConfig, LauncherConfig, LauncherSection,
    PythonBackendConfig, UpdateSection, default_config_path, default_data_root, load_config,
};
pub use error::{ConfigError, Result};
pub use record::{DesiredState, InstanceRecord};
pub use store::{
    Store, BOOTSTRAP_TOKEN_FILENAME, INSTANCES_SUBDIR, STATE_DIR, TOKENS_FILENAME,
};

#[cfg(test)]
mod tests {
    use super::*;
    use crate::record::InstanceRecord;
    use octobot_launcher_core::{InstanceId, InstanceSpec, InstanceState, RuntimeKind};
    use std::collections::BTreeMap;
    use std::io::Write as IoWrite;
    use std::path::PathBuf;
    fn env_lock() -> std::sync::MutexGuard<'static, ()> {
        crate::TEST_ENV_LOCK.get_or_init(|| std::sync::Mutex::new(())).lock().unwrap()
    }

    fn write_toml(dir: &tempfile::TempDir, content: &str) -> PathBuf {
        let path = dir.path().join("config.toml");
        let mut f = std::fs::File::create(&path).expect("create");
        f.write_all(content.as_bytes()).expect("write");
        path
    }

    fn sample_record() -> InstanceRecord {
        let id = InstanceId::new();
        InstanceRecord {
            spec: InstanceSpec {
                id,
                name: "bot".to_string(),
                runtime: RuntimeKind::Docker,
                version: "1.0.0".to_string(),
                data_dir: PathBuf::from("/data"),
                config_dir: PathBuf::from("/config"),
                env: BTreeMap::new(),
                ports: vec![],
                auto_restart: false,
                auto_update: false,
                runtime_options: serde_json::Value::Null,
            },
            desired_state: DesiredState::Running,
            last_known_state: InstanceState::Stopped,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        }
    }

    #[test]
    fn instance_records_list_skips_invalid_files() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let instances_dir = store.instances_dir();

        for i in 0..3 {
            let record = sample_record();
            let path = instances_dir.join(format!("valid_{i}.json"));
            store.write_atomic(&path, &record).expect("write");
        }

        std::fs::write(instances_dir.join("corrupt.json"), b"{bad json").expect("write corrupt");

        let records = store.list_instance_records().expect("list");
        assert_eq!(records.len(), 3);
    }

    #[test]
    fn instance_records_create_then_remove() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let record = sample_record();
        let path = store
            .instances_dir()
            .join(format!("{}.json", record.spec.id.0));

        store.write_atomic(&path, &record).expect("write");
        let records = store.list_instance_records().expect("list after write");
        assert_eq!(records.len(), 1);

        store.delete(&path).expect("delete");
        let records = store.list_instance_records().expect("list after delete");
        assert!(records.is_empty());
    }

    #[test]
    fn config_default_values_loaded() {
        let _g = env_lock();
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "");
        let config = load_config(Some(&path)).expect("load");
        assert_eq!(config.launcher.api_bind, "127.0.0.1:7531");
        assert_eq!(config.launcher.log_level, "info");
        assert_eq!(config.update.channel, "stable");
        assert!(config.update.auto_update_launcher);
        assert!(!config.update.auto_update_instances);
        assert_eq!(config.update.check_interval_hours, 6);
        assert_eq!(
            config.update.manifest_url,
            "https://updates.drakkar.software/octobot-launcher/v1/manifest.json"
        );
    }

    #[test]
    fn config_env_var_override() {
        let _g = env_lock();
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "");
        std::env::set_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND", "0.0.0.0:9000");
        let config = load_config(Some(&path)).expect("load");
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        assert_eq!(config.launcher.api_bind, "0.0.0.0:9000");
    }

    #[test]
    fn config_missing_file_uses_defaults() {
        let _g = env_lock();
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = dir.path().join("nonexistent.toml");
        let config = load_config(Some(&path)).expect("load");
        assert_eq!(config.launcher.api_bind, "127.0.0.1:7531");
    }

    #[test]
    fn config_malformed_toml_returns_error() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "[[[ broken");
        let result = load_config(Some(&path));
        assert!(matches!(result, Err(ConfigError::Load(_))));
    }

    #[test]
    fn config_invalid_log_level_rejected() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "[launcher]\nlog_level = \"blarg\"");
        let result = load_config(Some(&path));
        assert!(matches!(result, Err(ConfigError::Validation(_))));
    }

    #[test]
    fn config_path_locations_per_platform() {
        let system = default_config_path(true);
        let user = default_config_path(false);
        assert!(!system.as_os_str().is_empty());
        assert!(!user.as_os_str().is_empty());
    }
}
