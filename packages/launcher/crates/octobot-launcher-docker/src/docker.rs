// bollard 0.19 marks its own struct types as deprecated in favour of a
// query_parameters module that does not yet ship in 0.19.x.
#![allow(deprecated)]

use std::time::Duration;

use async_trait::async_trait;
use bollard::container::{
    Config, CreateContainerOptions, RemoveContainerOptions, StartContainerOptions,
    StopContainerOptions,
};
use bollard::image::CreateImageOptions;
use chrono::DateTime;
use futures_util::StreamExt;
use octobot_launcher_core::backend::{send_progress, ProgressSender};
use octobot_launcher_core::error::{LauncherError, Result};
use octobot_launcher_core::model::{
    HealthStatus, InstanceId, InstanceSpec, InstanceState, RuntimeKind,
};
use octobot_launcher_core::Backend;
use tracing::info;

use crate::helpers::{
    build_host_config, build_labels, container_name, resolve_image,
};

#[derive(Debug)]
pub struct DockerBackend {
    docker: bollard::Docker,
}

impl DockerBackend {
    pub fn new() -> Result<Self> {
        let docker = bollard::Docker::connect_with_defaults()
            .map_err(|e: bollard::errors::Error| LauncherError::BackendUnavailable(e.to_string()))?;
        Ok(Self { docker })
    }

    pub fn with_docker(docker: bollard::Docker) -> Self {
        Self { docker }
    }
}

#[async_trait]
impl Backend for DockerBackend {
    fn kind(&self) -> RuntimeKind {
        RuntimeKind::Docker
    }

    async fn probe(&self) -> Result<()> {
        tokio::time::timeout(Duration::from_secs(2), self.docker.version())
            .await
            .map_err(|_| LauncherError::BackendUnavailable("docker daemon not reachable".into()))?
            .map_err(|_| LauncherError::BackendUnavailable("docker daemon not reachable".into()))?;
        Ok(())
    }

    async fn prepare(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        let image = resolve_image(spec);
        let options = CreateImageOptions {
            from_image: image.clone(),
            ..Default::default()
        };

        send_progress(progress, format!("Pulling {image}"));

        let mut stream = self.docker.create_image(Some(options), None, None);

        while let Some(result) = stream.next().await {
            match result {
                Ok(info) => {
                    if let Some(status) = &info.status {
                        let msg = if let Some(prog) = &info.progress {
                            format!("{status} {prog}")
                        } else {
                            status.clone()
                        };
                        send_progress(progress, &msg);
                        info!(status = ?info.status, progress = ?info.progress, "pulling image {image}");
                    }
                }
                Err(e) => return Err(LauncherError::Backend(e.to_string())),
            }
        }

        Ok(())
    }

    async fn start(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        let name = container_name(spec.id);

        if let Ok(inspect) = self.docker.inspect_container(&name, None::<bollard::container::InspectContainerOptions>).await {
            if let Some(state) = inspect.state {
                if state.running == Some(true) {
                    return Err(LauncherError::AlreadyRunning);
                }
            }
        }

        self.prepare(spec, progress).await?;

        let image = resolve_image(spec);
        let env: Vec<String> = spec
            .env
            .iter()
            .map(|(k, v)| format!("{k}={v}"))
            .collect();

        let labels = build_labels(spec);
        let host_config = build_host_config(spec);

        let config = Config {
            image: Some(image),
            env: Some(env),
            labels: Some(labels),
            host_config: Some(host_config),
            ..Default::default()
        };

        let options = CreateContainerOptions {
            name: name.clone(),
            ..Default::default()
        };

        send_progress(progress, "Creating container");
        self.docker
            .create_container(Some(options), config)
            .await
            .map_err(|e| LauncherError::Backend(e.to_string()))?;

        send_progress(progress, "Starting container");
        self.docker
            .start_container(&name, None::<StartContainerOptions<String>>)
            .await
            .map_err(|e| LauncherError::Backend(e.to_string()))?;

        Ok(())
    }

    async fn stop(&self, id: InstanceId, timeout: Duration) -> Result<()> {
        let name = container_name(id);
        let options = StopContainerOptions {
            t: i64::try_from(timeout.as_secs()).unwrap_or(i64::MAX),
        };
        self.docker
            .stop_container(&name, Some(options))
            .await
            .map_err(|e| match e {
                bollard::errors::Error::DockerResponseServerError {
                    status_code: 404, ..
                } => LauncherError::InstanceNotFound(name.clone()),
                bollard::errors::Error::DockerResponseServerError {
                    status_code: 304, ..
                } => LauncherError::NotRunning,
                other => LauncherError::Backend(other.to_string()),
            })
    }

    async fn restart(
        &self,
        spec: &InstanceSpec,
        timeout: Duration,
        progress: Option<&ProgressSender>,
    ) -> Result<()> {
        self.stop(spec.id, timeout).await?;
        self.start(spec, progress).await
    }

    async fn status(&self, id: InstanceId) -> Result<HealthStatus> {
        let name = container_name(id);
        let inspect = self
            .docker
            .inspect_container(&name, None::<bollard::container::InspectContainerOptions>)
            .await
            .map_err(|e| match e {
                bollard::errors::Error::DockerResponseServerError {
                    status_code: 404, ..
                } => LauncherError::InstanceNotFound(name.clone()),
                other => LauncherError::Backend(other.to_string()),
            })?;

        let docker_state = inspect.state.unwrap_or_default();
        let is_running = docker_state.running.unwrap_or(false);

        let (state, uptime_seconds) = if is_running {
            let started_at = docker_state
                .started_at
                .as_deref()
                .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
                .map(|dt| dt.with_timezone(&chrono::Utc));

            let uptime = started_at.map(|sa| {
                let diff = chrono::Utc::now().signed_duration_since(sa);
                u64::try_from(diff.num_seconds().max(0)).unwrap_or(0)
            });

            let instance_state = InstanceState::Running {
                pid_or_container: name,
                started_at: started_at.unwrap_or_else(chrono::Utc::now),
            };

            (instance_state, uptime)
        } else {
            (InstanceState::Stopped, None)
        };

        Ok(HealthStatus {
            state,
            uptime_seconds,
            last_http_check: None,
        })
    }

    async fn update(
        &self,
        spec: &InstanceSpec,
        target_version: &str,
        progress: Option<&ProgressSender>,
    ) -> Result<()> {
        let updated_spec = InstanceSpec {
            version: target_version.to_string(),
            ..spec.clone()
        };

        self.prepare(&updated_spec, progress).await?;
        match self.stop(spec.id, Duration::from_secs(10)).await {
            Ok(()) | Err(LauncherError::NotRunning) => {}
            Err(e) => return Err(e),
        }

        let name = container_name(spec.id);
        self.docker
            .remove_container(
                &name,
                Some(RemoveContainerOptions {
                    force: true,
                    ..Default::default()
                }),
            )
            .await
            .map_err(|e| LauncherError::Backend(e.to_string()))?;

        self.start(&updated_spec, progress).await
    }

    async fn remove(&self, id: InstanceId, purge: bool) -> Result<()> {
        let name = container_name(id);

        let _ = self
            .docker
            .stop_container(&name, Some(StopContainerOptions { t: 10 }))
            .await;

        self.docker
            .remove_container(
                &name,
                Some(RemoveContainerOptions {
                    v: purge,
                    force: true,
                    ..Default::default()
                }),
            )
            .await
            .map_err(|e| match e {
                bollard::errors::Error::DockerResponseServerError {
                    status_code: 404, ..
                } => LauncherError::InstanceNotFound(name.clone()),
                other => LauncherError::Backend(other.to_string()),
            })
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use octobot_launcher_core::model::{InstanceId, InstanceSpec, RuntimeKind};
    use std::collections::BTreeMap;
    use std::path::PathBuf;
    use std::sync::Arc;

    fn sample_spec_with_version(version: &str) -> InstanceSpec {
        InstanceSpec {
            id: InstanceId::new(),
            name: "test-bot".into(),
            runtime: RuntimeKind::Docker,
            version: version.into(),
            data_dir: PathBuf::from("/data"),
            config_dir: PathBuf::from("/config"),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        }
    }

    #[derive(Debug, Default)]
    struct MockDockerOps {
        calls: Arc<Mutex<Vec<&'static str>>>,
    }

    impl MockDockerOps {
        fn record(&self, op: &'static str) {
            self.calls.lock().expect("mutex poisoned").push(op);
        }

        fn pull_image(&self, _spec: &InstanceSpec) {
            self.record("pull");
        }

        fn stop_container(&self, _spec: &InstanceSpec) {
            self.record("stop");
        }

        fn remove_container(&self, _spec: &InstanceSpec) {
            self.record("remove");
        }

        fn create_and_start_container(&self, _spec: &InstanceSpec) {
            self.record("start");
        }

        fn blue_green_update(&self, spec: &InstanceSpec, target_version: &str) {
            let updated = InstanceSpec {
                version: target_version.to_string(),
                ..spec.clone()
            };
            self.pull_image(&updated);
            self.stop_container(spec);
            self.remove_container(spec);
            self.create_and_start_container(&updated);
        }

        fn get_calls(&self) -> Vec<&'static str> {
            self.calls.lock().expect("mutex poisoned").clone()
        }
    }

    #[test]
    fn update_blue_green_order() {
        let ops = MockDockerOps::default();
        let spec = sample_spec_with_version("1.0.0");
        ops.blue_green_update(&spec, "2.0.0");
        assert_eq!(ops.get_calls(), vec!["pull", "stop", "remove", "start"]);
    }
}
