use std::path::{Path, PathBuf};

use parking_lot::Mutex;

pub const STATE_DIR: &str = "state";
pub const INSTANCES_SUBDIR: &str = "instances";
pub const TOKENS_FILENAME: &str = "tokens.json";
pub const BOOTSTRAP_TOKEN_FILENAME: &str = "bootstrap_token.txt";
pub const SOCKET_FILENAME: &str = "launcher.sock";
pub const LOCK_FILENAME: &str = "launcher.lock";
use serde::{de::DeserializeOwned, Serialize};
use tracing::warn;

use crate::{
    error::{ConfigError, Result},
    record::InstanceRecord,
};

#[derive(Debug)]
pub struct Store {
    data_root: PathBuf,
    write_lock: Mutex<()>,
}

impl Store {
    pub fn new(data_root: PathBuf) -> Result<Self> {
        let dirs = [
            data_root.join(STATE_DIR).join(INSTANCES_SUBDIR),
            data_root.clone(),
        ];
        for dir in &dirs {
            std::fs::create_dir_all(dir)?;
        }
        Ok(Self {
            data_root,
            write_lock: Mutex::new(()),
        })
    }

    pub fn write_atomic<T: Serialize>(&self, path: &Path, value: &T) -> Result<()> {
        let _guard = self.write_lock.lock();

        let content =
            serde_json::to_string_pretty(value).map_err(|e| ConfigError::Serialize(e.to_string()))?;

        let parent = path.parent().ok_or_else(|| {
            ConfigError::Io(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "path has no parent",
            ))
        })?;
        std::fs::create_dir_all(parent)?;

        let mut tmp = tempfile::Builder::new()
            .prefix(".tmp")
            .tempfile_in(parent)?;

        {
            use std::io::Write as IoWrite;
            let file = tmp.as_file_mut();
            file.write_all(content.as_bytes())?;
            file.flush()?;
            #[cfg(unix)]
            {
                sync_file(file)?;
                sync_dir(parent)?;
            }
        }

        tmp.persist(path).map_err(|e| ConfigError::Io(e.error))?;

        Ok(())
    }

    pub fn read<T: DeserializeOwned>(&self, path: &Path) -> Result<Option<T>> {
        match std::fs::read_to_string(path) {
            Ok(content) => {
                let value: T = serde_json::from_str(&content)
                    .map_err(|e| ConfigError::Deserialize(e.to_string()))?;
                Ok(Some(value))
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(ConfigError::Io(e)),
        }
    }

    pub fn delete(&self, path: &Path) -> Result<()> {
        match std::fs::remove_file(path) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(ConfigError::Io(e)),
        }
    }

    pub fn data_root(&self) -> &std::path::Path {
        &self.data_root
    }

    pub fn instances_dir(&self) -> PathBuf {
        self.data_root.join(STATE_DIR).join(INSTANCES_SUBDIR)
    }

    pub fn tokens_path(&self) -> PathBuf {
        self.data_root.join(STATE_DIR).join(TOKENS_FILENAME)
    }

    pub fn list_instance_records(&self) -> Result<Vec<InstanceRecord>> {
        let dir = self.instances_dir();
        let mut records = Vec::new();

        let read_dir = match std::fs::read_dir(&dir) {
            Ok(rd) => rd,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(records),
            Err(e) => return Err(ConfigError::Io(e)),
        };

        for entry in read_dir {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            match self.read::<InstanceRecord>(&path) {
                Ok(Some(record)) => records.push(record),
                Ok(None) => {}
                Err(e) => {
                    warn!("skipping corrupt instance record {:?}: {}", path, e);
                }
            }
        }

        Ok(records)
    }
}

#[cfg(unix)]
fn sync_file(file: &std::fs::File) -> Result<()> {
    file.sync_all()?;
    Ok(())
}

#[cfg(unix)]
fn sync_dir(path: &Path) -> Result<()> {
    let dir = std::fs::File::open(path)?;
    let _ = dir.sync_all();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::record::{DesiredState, InstanceRecord};
    use octobot_launcher_core::{InstanceId, InstanceSpec, InstanceState, RuntimeKind};
    use std::collections::BTreeMap;
    use std::sync::Arc;

    fn sample_record() -> InstanceRecord {
        let id = InstanceId::new();
        InstanceRecord {
            spec: InstanceSpec {
                id,
                name: "test-bot".to_string(),
                runtime: RuntimeKind::Binary,
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
    fn write_then_read_roundtrip() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let record = sample_record();
        let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
        store.write_atomic(&path, &record).expect("write");
        let back: Option<InstanceRecord> = store.read(&path).expect("read");
        let back = back.expect("should have value");
        assert_eq!(back.spec.name, record.spec.name);
        assert_eq!(back.spec.id, record.spec.id);
        assert_eq!(back.desired_state, record.desired_state);
    }

    #[test]
    fn partial_write_visibility() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let record = sample_record();
        let path = store.instances_dir().join("partial.json");
        store.write_atomic(&path, &record).expect("write");
        let result: Option<InstanceRecord> = store.read(&path).expect("read");
        assert!(result.is_some());
    }

    #[test]
    fn tempfile_cleanup_on_drop() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let record = sample_record();
        let path = store.instances_dir().join("cleanup_test.json");
        store.write_atomic(&path, &record).expect("write");
        let tmp_count = std::fs::read_dir(store.instances_dir())
            .expect("read dir")
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.file_name()
                    .to_string_lossy()
                    .starts_with(".tmp")
            })
            .count();
        assert_eq!(tmp_count, 0);
    }

    #[test]
    fn missing_file_returns_none() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let path = store.instances_dir().join("nonexistent.json");
        let result: Option<InstanceRecord> = store.read(&path).expect("read should succeed");
        assert!(result.is_none());
    }

    #[test]
    fn corrupt_file_returns_error_not_panic() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Store::new(dir.path().to_path_buf()).expect("store");
        let path = store.instances_dir().join("corrupt.json");
        std::fs::write(&path, b"{\"truncated\":").expect("write corrupt file");
        let result: crate::error::Result<Option<InstanceRecord>> = store.read(&path);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn concurrent_writes_serialized() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let store = Arc::new(Store::new(dir.path().to_path_buf()).expect("store"));
        let path = Arc::new(store.instances_dir().join("concurrent.json"));

        let handles: Vec<_> = (0..10)
            .map(|_| {
                let store = Arc::clone(&store);
                let path = Arc::clone(&path);
                let record = sample_record();
                tokio::spawn(async move {
                    store.write_atomic(&path, &record).expect("write");
                })
            })
            .collect();

        for h in handles {
            h.await.expect("task");
        }

        let result: Option<InstanceRecord> = store.read(&path).expect("final read");
        assert!(result.is_some());
    }
}
