use crate::error::Result;
use crate::model::{HealthStatus, InstanceId, InstanceSpec, RuntimeKind};

pub type ProgressSender = tokio::sync::mpsc::UnboundedSender<String>;

pub fn send_progress(tx: Option<&ProgressSender>, msg: impl Into<String>) {
    if let Some(tx) = tx {
        let _ = tx.send(msg.into());
    }
}

#[async_trait::async_trait]
pub trait Backend: Send + Sync + 'static {
    fn kind(&self) -> RuntimeKind;
    async fn probe(&self) -> Result<()>;
    async fn prepare(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()>;
    async fn start(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()>;
    async fn stop(&self, spec: &InstanceSpec, timeout: std::time::Duration) -> Result<()>;
    async fn restart(
        &self,
        spec: &InstanceSpec,
        timeout: std::time::Duration,
        progress: Option<&ProgressSender>,
    ) -> Result<()>;
    async fn status(&self, id: InstanceId) -> Result<HealthStatus>;
    async fn update(
        &self,
        spec: &InstanceSpec,
        target_version: &str,
        progress: Option<&ProgressSender>,
    ) -> Result<()>;
    async fn remove(&self, spec: &InstanceSpec, purge: bool) -> Result<()>;
}

#[cfg(feature = "testing")]
pub mod mock {
    use super::*;
    use crate::model::{InstanceState, RuntimeKind};
    use std::collections::HashMap;
    use std::sync::Arc;
    use tokio::sync::Mutex;

    #[derive(Debug, Default)]
    struct Inner {
        states: HashMap<InstanceId, InstanceState>,
        probe_result: Option<String>,
    }

    #[derive(Debug, Clone, Default)]
    pub struct MockBackend {
        inner: Arc<Mutex<Inner>>,
    }

    impl MockBackend {
        pub async fn set_probe_fail(&self, reason: &str) {
            self.inner.lock().await.probe_result = Some(reason.to_string());
        }

        pub async fn get_state(&self, id: InstanceId) -> Option<InstanceState> {
            self.inner.lock().await.states.get(&id).cloned()
        }
    }

    #[async_trait::async_trait]
    impl Backend for MockBackend {
        fn kind(&self) -> RuntimeKind {
            RuntimeKind::Binary
        }

        async fn probe(&self) -> Result<()> {
            let lock = self.inner.lock().await;
            if let Some(reason) = &lock.probe_result {
                return Err(crate::error::LauncherError::BackendUnavailable(reason.clone()));
            }
            Ok(())
        }

        async fn prepare(&self, spec: &InstanceSpec, _progress: Option<&ProgressSender>) -> Result<()> {
            self.inner
                .lock()
                .await
                .states
                .insert(spec.id, InstanceState::Stopped);
            Ok(())
        }

        async fn start(&self, spec: &InstanceSpec, _progress: Option<&ProgressSender>) -> Result<()> {
            let mut lock = self.inner.lock().await;
            if matches!(lock.states.get(&spec.id), Some(InstanceState::Running { .. })) {
                return Err(crate::error::LauncherError::AlreadyRunning);
            }
            lock.states.insert(
                spec.id,
                InstanceState::Running {
                    pid_or_container: "mock-pid".into(),
                    started_at: chrono::Utc::now(),
                },
            );
            Ok(())
        }

        async fn stop(&self, spec: &InstanceSpec, _timeout: std::time::Duration) -> Result<()> {
            let id = spec.id;
            let mut lock = self.inner.lock().await;
            if !matches!(lock.states.get(&id), Some(InstanceState::Running { .. })) {
                return Err(crate::error::LauncherError::NotRunning);
            }
            lock.states.insert(id, InstanceState::Stopped);
            Ok(())
        }

        async fn restart(
            &self,
            spec: &InstanceSpec,
            timeout: std::time::Duration,
            progress: Option<&ProgressSender>,
        ) -> Result<()> {
            self.stop(spec, timeout).await?;
            self.start(spec, progress).await
        }

        async fn status(&self, id: InstanceId) -> Result<HealthStatus> {
            let lock = self.inner.lock().await;
            let state = lock
                .states
                .get(&id)
                .cloned()
                .unwrap_or(InstanceState::Stopped);
            Ok(HealthStatus {
                state,
                uptime_seconds: None,
                last_http_check: None,
            })
        }

        async fn update(
            &self,
            spec: &InstanceSpec,
            _target_version: &str,
            _progress: Option<&ProgressSender>,
        ) -> Result<()> {
            self.inner
                .lock()
                .await
                .states
                .insert(spec.id, InstanceState::Stopped);
            Ok(())
        }

        async fn remove(&self, spec: &InstanceSpec, _purge: bool) -> Result<()> {
            self.inner.lock().await.states.remove(&spec.id);
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trait_object_is_object_safe() {
        fn accepts_backend(_: &dyn Backend) {}
        fn accepts_boxed(_: Box<dyn Backend>) {}
        let _ = accepts_backend;
        let _ = accepts_boxed;
    }

    #[cfg(feature = "testing")]
    #[tokio::test]
    async fn mock_backend_lifecycle() {
        use crate::model::InstanceState;
        use mock::MockBackend;
        use std::collections::BTreeMap;
        use std::path::PathBuf;

        let backend = MockBackend::default();
        let spec = InstanceSpec {
            id: InstanceId::new(),
            name: "test".into(),
            runtime: RuntimeKind::Binary,
            version: "1.0.0".into(),
            data_dir: PathBuf::from("/tmp/data"),
            config_dir: PathBuf::from("/tmp/config"),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        };

        backend.prepare(&spec, None).await.unwrap();
        assert!(matches!(
            backend.get_state(spec.id).await.unwrap(),
            InstanceState::Stopped
        ));

        backend.start(&spec, None).await.unwrap();
        assert!(matches!(
            backend.get_state(spec.id).await.unwrap(),
            InstanceState::Running { .. }
        ));

        let health = backend.status(spec.id).await.unwrap();
        assert!(matches!(health.state, InstanceState::Running { .. }));

        backend
            .stop(&spec, std::time::Duration::from_secs(5))
            .await
            .unwrap();
        assert!(matches!(
            backend.get_state(spec.id).await.unwrap(),
            InstanceState::Stopped
        ));

        backend.remove(&spec, false).await.unwrap();
        assert!(backend.get_state(spec.id).await.is_none());
    }
}
