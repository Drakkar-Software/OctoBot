use std::collections::HashMap;

use bollard::models::{HostConfig, PortBinding, RestartPolicy, RestartPolicyNameEnum};
use octobot_launcher_core::model::{InstanceId, InstanceSpec};

use crate::constants::{
    CONTAINER_PREFIX, DEFAULT_IMAGE, LABEL_INSTANCE_ID, LABEL_LAUNCHER, LABEL_VERSION,
    MOUNT_CONFIG, MOUNT_USER_DATA, RUNTIME_OPT_IMAGE, RUNTIME_OPT_IMAGE_DIGEST,
};

pub(crate) fn container_name(id: InstanceId) -> String {
    format!("{CONTAINER_PREFIX}{}", id.short())
}

pub(crate) fn build_labels(spec: &InstanceSpec) -> HashMap<String, String> {
    let mut labels = HashMap::new();
    labels.insert(LABEL_LAUNCHER.to_string(), "1".to_string());
    labels.insert(LABEL_INSTANCE_ID.to_string(), spec.id.0.to_string());
    labels.insert(LABEL_VERSION.to_string(), spec.version.clone());
    labels
}

pub(crate) fn build_binds(spec: &InstanceSpec) -> Vec<String> {
    vec![
        format!("{}:{MOUNT_USER_DATA}", spec.data_dir.display()),
        format!("{}:{MOUNT_CONFIG}", spec.config_dir.display()),
    ]
}

pub(crate) fn resolve_image(spec: &InstanceSpec) -> String {
    let base_image = if let Some(serde_json::Value::String(img)) = spec.runtime_options.get(RUNTIME_OPT_IMAGE) {
        img.clone()
    } else {
        format!("{DEFAULT_IMAGE}:{}", spec.version)
    };

    if let Some(serde_json::Value::String(digest)) = spec.runtime_options.get(RUNTIME_OPT_IMAGE_DIGEST) {
        format!("{base_image}@sha256:{digest}")
    } else {
        base_image
    }
}

pub(crate) fn build_restart_policy(auto_restart: bool) -> RestartPolicy {
    if auto_restart {
        RestartPolicy {
            name: Some(RestartPolicyNameEnum::UNLESS_STOPPED),
            maximum_retry_count: None,
        }
    } else {
        RestartPolicy {
            name: Some(RestartPolicyNameEnum::EMPTY),
            maximum_retry_count: None,
        }
    }
}

pub(crate) fn build_port_bindings(
    spec: &InstanceSpec,
) -> HashMap<String, Option<Vec<PortBinding>>> {
    let mut port_bindings: HashMap<String, Option<Vec<PortBinding>>> = HashMap::new();
    for pm in &spec.ports {
        let key = format!("{}/tcp", pm.container_or_internal);
        let binding = PortBinding {
            host_ip: Some(pm.bind_addr.to_string()),
            host_port: Some(pm.host.to_string()),
        };
        port_bindings.insert(key, Some(vec![binding]));
    }
    port_bindings
}

pub(crate) fn build_host_config(spec: &InstanceSpec) -> HostConfig {
    HostConfig {
        binds: Some(build_binds(spec)),
        port_bindings: Some(build_port_bindings(spec)),
        restart_policy: Some(build_restart_policy(spec.auto_restart)),
        ..Default::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use octobot_launcher_core::model::{PortMapping, RuntimeKind};
    use std::collections::BTreeMap;
    use std::net::IpAddr;
    use std::path::PathBuf;

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
    fn naming_container_name_from_instance_id() {
        let id = InstanceId::new();
        let name = container_name(id);
        assert!(name.starts_with(CONTAINER_PREFIX));
        assert_eq!(name.len(), CONTAINER_PREFIX.len() + 8);
        assert_eq!(&name[CONTAINER_PREFIX.len()..], id.short());
    }

    #[test]
    fn naming_label_set_includes_required_keys() {
        let spec = sample_spec();
        let labels = build_labels(&spec);
        assert!(labels.contains_key(LABEL_LAUNCHER));
        assert!(labels.contains_key(LABEL_INSTANCE_ID));
        assert!(labels.contains_key(LABEL_VERSION));
        assert_eq!(labels[LABEL_LAUNCHER], "1");
        assert_eq!(labels[LABEL_INSTANCE_ID], spec.id.0.to_string());
        assert_eq!(labels[LABEL_VERSION], spec.version);
    }

    #[test]
    fn mounts_volume_paths_are_canonicalized() {
        let spec = sample_spec();
        let binds = build_binds(&spec);
        assert_eq!(binds[0], format!("/data:{MOUNT_USER_DATA}"));
        assert_eq!(binds[1], format!("/config:{MOUNT_CONFIG}"));
    }

    #[test]
    fn mounts_container_paths_are_constants() {
        let spec = sample_spec();
        let binds = build_binds(&spec);
        assert!(binds[0].ends_with(MOUNT_USER_DATA));
        assert!(binds[1].ends_with(MOUNT_CONFIG));
    }

    #[test]
    fn ports_bind_addr_default_is_loopback() {
        let pm = PortMapping::default();
        assert_eq!(pm.bind_addr, "127.0.0.1".parse::<IpAddr>().unwrap());
    }

    #[test]
    fn restart_auto_restart_maps_to_unless_stopped() {
        let policy = build_restart_policy(true);
        assert_eq!(policy.name, Some(RestartPolicyNameEnum::UNLESS_STOPPED));
    }

    #[test]
    fn restart_no_auto_restart_maps_to_empty() {
        let policy = build_restart_policy(false);
        assert_eq!(policy.name, Some(RestartPolicyNameEnum::EMPTY));
    }

    #[test]
    fn image_digest_pin_uses_at_form() {
        let mut spec = sample_spec();
        spec.version = "2.4.42".into();
        spec.runtime_options = serde_json::json!({
            RUNTIME_OPT_IMAGE_DIGEST: "abc123"
        });
        let image = resolve_image(&spec);
        assert_eq!(image, format!("{DEFAULT_IMAGE}:2.4.42@sha256:abc123"));
    }

    #[test]
    fn image_custom_image_override() {
        let mut spec = sample_spec();
        spec.runtime_options = serde_json::json!({
            RUNTIME_OPT_IMAGE: "custom/octobot:latest"
        });
        let image = resolve_image(&spec);
        assert_eq!(image, "custom/octobot:latest");
    }

    #[test]
    fn image_default_uses_version() {
        let spec = sample_spec();
        let image = resolve_image(&spec);
        assert_eq!(image, format!("{DEFAULT_IMAGE}:2.4.42"));
    }
}
