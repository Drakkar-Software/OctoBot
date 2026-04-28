#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::collections::BTreeMap;
use std::path::PathBuf;
use std::sync::Arc;

use octobot_launcher_config::{DesiredState, InstanceRecord, Store, load_config};
use octobot_launcher_core::{InstanceId, InstanceSpec, InstanceState, RuntimeKind};
use tempfile::TempDir;

fn sample_record() -> InstanceRecord {
    let id = InstanceId::new();
    InstanceRecord {
        spec: InstanceSpec {
            id,
            name: "test-bot".to_string(),
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
fn store_write_read_delete_round_trip() {
    let dir = TempDir::new().unwrap();
    let store = Store::new(dir.path().to_path_buf()).unwrap();
    let record = sample_record();
    let id = record.spec.id.clone();

    let path = store.instances_dir().join(format!("{}.json", id.0));
    store.write_atomic(&path, &record).unwrap();

    let records = store.list_instance_records().unwrap();
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].spec.id.0, id.0);
    assert_eq!(records[0].spec.name, "test-bot");
    assert_eq!(records[0].desired_state, DesiredState::Running);

    store.delete(&path).unwrap();

    let records_after = store.list_instance_records().unwrap();
    assert!(records_after.is_empty());
}

#[test]
fn corrupt_instance_file_skipped_not_panicked() {
    let dir = TempDir::new().unwrap();
    let store = Store::new(dir.path().to_path_buf()).unwrap();
    let instances_dir = store.instances_dir();

    for _ in 0..3 {
        let record = sample_record();
        let path = instances_dir.join(format!("{}.json", record.spec.id.0));
        store.write_atomic(&path, &record).unwrap();
    }

    std::fs::write(instances_dir.join("corrupt.json"), b"{bad json").unwrap();

    let records = store.list_instance_records().unwrap();
    assert_eq!(records.len(), 3);
}

#[test]
fn config_loads_from_file() {
    let dir = TempDir::new().unwrap();
    let config_path = dir.path().join("config.toml");
    std::fs::write(
        &config_path,
        format!(
            "[launcher]\ndata_root = {:?}\napi_bind = \"127.0.0.1:9999\"\n",
            dir.path()
        ),
    )
    .unwrap();

    let config = load_config(Some(&config_path)).unwrap();
    assert_eq!(config.launcher.api_bind, "127.0.0.1:9999");
    assert_eq!(config.launcher.data_root, dir.path());
}

#[tokio::test]
async fn store_concurrent_writes_no_corruption() {
    let dir = TempDir::new().unwrap();
    let store = Arc::new(Store::new(dir.path().to_path_buf()).unwrap());
    let record = sample_record();
    let path = store
        .instances_dir()
        .join(format!("{}.json", record.spec.id.0));

    let mut handles = vec![];
    for _ in 0..10 {
        let store_clone = Arc::clone(&store);
        let record_clone = record.clone();
        let path_clone = path.clone();
        handles.push(tokio::spawn(async move {
            store_clone.write_atomic(&path_clone, &record_clone).unwrap();
        }));
    }

    for handle in handles {
        handle.await.unwrap();
    }

    let content = std::fs::read_to_string(&path).unwrap();
    let parsed: serde_json::Value = serde_json::from_str(&content).expect("valid JSON after concurrent writes");
    assert!(parsed.is_object());
}
