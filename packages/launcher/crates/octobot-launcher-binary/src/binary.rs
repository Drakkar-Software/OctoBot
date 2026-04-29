use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use octobot_launcher_core::backend::{send_progress, ProgressSender};
use octobot_launcher_core::error::{LauncherError, Result};
use octobot_launcher_core::model::{
    HealthStatus, InstanceId, InstanceSpec, InstanceState, RuntimeKind,
};
use octobot_launcher_core::Backend;
use octobot_launcher_update::{ArtifactKind, Updater, fetch_latest_octobot_binary};
use tokio::process::Child;
use tokio::sync::Mutex;
use tracing::{info, warn};

use crate::pidfile::{is_orphaned_pid, read_pid_file, remove_pid_file, write_pid_file};
use crate::probe::run_http_probe;

pub(crate) fn binary_path(data_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    return data_dir.join("bin").join("octobot.exe");
    #[cfg(not(windows))]
    return data_dir.join("bin").join("octobot");
}

pub(crate) fn resolve_binary(data_dir: &Path, runtime_options: &serde_json::Value) -> PathBuf {
    if let Some(serde_json::Value::String(p)) = runtime_options.get("binary_path") {
        return PathBuf::from(p);
    }
    binary_path(data_dir)
}

pub(crate) fn new_binary_path(data_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    return data_dir.join("bin").join("octobot.new.exe");
    #[cfg(not(windows))]
    return data_dir.join("bin").join("octobot.new");
}

pub(crate) fn pid_file_path(data_dir: &Path) -> PathBuf {
    data_dir.join("octobot.pid")
}

pub(crate) fn stdio_log_path(data_dir: &Path) -> PathBuf {
    data_dir.join("logs").join("launcher-stdio.log")
}

struct Inner {
    child: Option<Child>,
    started_at: Option<DateTime<Utc>>,
    pid: Option<u32>,
    data_dir: Option<PathBuf>,
    runtime_options: Option<serde_json::Value>,
    last_http_check: Option<octobot_launcher_core::model::HttpProbe>,
}

impl std::fmt::Debug for Inner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Inner")
            .field("pid", &self.pid)
            .field("started_at", &self.started_at)
            .field("data_dir", &self.data_dir)
            .finish_non_exhaustive()
    }
}

impl Inner {
    fn new() -> Self {
        Self {
            child: None,
            started_at: None,
            pid: None,
            data_dir: None,
            runtime_options: None,
            last_http_check: None,
        }
    }
}

#[derive(Debug)]
pub struct BinaryBackendConfig {
    pub http_probe_interval_secs: u64,
}

impl Default for BinaryBackendConfig {
    fn default() -> Self {
        Self {
            http_probe_interval_secs: 30,
        }
    }
}

#[derive(Debug)]
pub struct BinaryBackend {
    #[allow(dead_code)]
    config: BinaryBackendConfig,
    updater: Option<Arc<Updater>>,
    inner: Arc<Mutex<Inner>>,
    start_lock: Arc<Mutex<()>>,
}

impl BinaryBackend {
    pub fn new(config: BinaryBackendConfig) -> Self {
        Self {
            config,
            updater: None,
            inner: Arc::new(Mutex::new(Inner::new())),
            start_lock: Arc::new(Mutex::new(())),
        }
    }

    #[must_use]
    pub fn with_updater(mut self, updater: Arc<Updater>) -> Self {
        self.updater = Some(updater);
        self
    }
}

impl Default for BinaryBackend {
    fn default() -> Self {
        Self::new(BinaryBackendConfig::default())
    }
}

#[async_trait]
impl Backend for BinaryBackend {
    fn kind(&self) -> RuntimeKind {
        RuntimeKind::Binary
    }

    async fn probe(&self) -> Result<()> {
        Ok(())
    }

    async fn prepare(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        send_progress(progress, "Preparing data directory");
        std::fs::create_dir_all(spec.data_dir.join("bin"))?;
        std::fs::create_dir_all(spec.data_dir.join("logs"))?;

        // If a custom binary_path is specified the caller manages the binary.
        if spec.runtime_options.get("binary_path").is_some() {
            return Ok(());
        }

        let bin = binary_path(&spec.data_dir);
        if !bin.exists() {
            let dest_dir = spec.data_dir.join("bin");
            send_progress(progress, format!("Downloading OctoBot {}", spec.version));

            let downloaded = if let Some(updater) = self.updater.as_ref() {
                // Use manifest-based updater when configured (production).
                // TODO: re-enable updates.drakkar.software manifest once server is live.
                updater
                    .fetch_artifact(ArtifactKind::OctoBotBinary, &dest_dir)
                    .await
                    .map_err(|e| LauncherError::Backend(e.to_string()))?
            } else {
                // Fallback: fetch latest release from GitHub.
                fetch_latest_octobot_binary(&dest_dir)
                    .await
                    .map_err(|e| LauncherError::Backend(e.to_string()))?
            };

            send_progress(progress, "Installing binary");
            let new_path = new_binary_path(&spec.data_dir);
            std::fs::rename(&downloaded, &new_path)?;
            std::fs::rename(&new_path, &bin)?;

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                std::fs::set_permissions(&bin, std::fs::Permissions::from_mode(0o755))?;
            }
        }

        Ok(())
    }

    async fn start(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        let _start_guard = self
            .start_lock
            .try_lock()
            .map_err(|_| LauncherError::AlreadyRunning)?;
        let pid_path = pid_file_path(&spec.data_dir);

        {
            let mut inner = self.inner.lock().await;
            if let Some(ref mut child) = inner.child {
                if let Ok(Some(_)) = child.try_wait() {
                    inner.child = None;
                    inner.started_at = None;
                    inner.pid = None;
                } else {
                    return Err(LauncherError::AlreadyRunning);
                }
            }
        }

        if let Ok(Some(pid)) = read_pid_file(&pid_path) {
            if !is_orphaned_pid(pid, "octobot") {
                return Err(LauncherError::AlreadyRunning);
            }
            remove_pid_file(&pid_path)?;
        }

        self.prepare(spec, progress).await?;

        let bin = resolve_binary(&spec.data_dir, &spec.runtime_options);
        let mut cmd = tokio::process::Command::new(&bin);

        for (k, v) in &spec.env {
            cmd.env(k, v);
        }

        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
            cmd.creation_flags(CREATE_NEW_PROCESS_GROUP);
        }

        let capture = spec
            .runtime_options
            .get("capture_stdio")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);

        if capture {
            let log_path = stdio_log_path(&spec.data_dir);
            if let Some(parent) = log_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let log_file = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_path)?;
            let log_file2 = log_file.try_clone()?;
            cmd.stdout(Stdio::from(log_file));
            cmd.stderr(Stdio::from(log_file2));
        } else {
            cmd.stdout(Stdio::null());
            cmd.stderr(Stdio::null());
        }

        cmd.kill_on_drop(false);

        send_progress(progress, "Starting OctoBot binary");
        let child = cmd.spawn()?;
        let pid = child.id().ok_or_else(|| {
            LauncherError::Backend("failed to get child PID after spawn".to_string())
        })?;

        write_pid_file(&pid_path, pid)?;

        let mut inner = self.inner.lock().await;
        inner.pid = Some(pid);
        inner.started_at = Some(Utc::now());
        inner.data_dir = Some(spec.data_dir.clone());
        inner.runtime_options = Some(spec.runtime_options.clone());
        inner.child = Some(child);

        info!(pid, binary = %bin.display(), "octobot binary started");
        Ok(())
    }

    async fn stop(&self, _id: InstanceId, timeout: Duration) -> Result<()> {
        let pid = {
            let inner = self.inner.lock().await;
            match inner.child.as_ref() {
                None => return Err(LauncherError::NotRunning),
                Some(_) => inner.pid.unwrap_or(0),
            }
        };

        send_graceful_signal(pid)?;

        let (mut child, data_dir) = {
            let mut inner = self.inner.lock().await;
            let child = match inner.child.take() {
                Some(c) => c,
                None => return Ok(()),
            };
            let data_dir = inner.data_dir.take();
            inner.started_at = None;
            inner.pid = None;
            inner.runtime_options = None;
            inner.last_http_check = None;
            (child, data_dir)
        };

        if let Some(ref dir) = data_dir {
            remove_pid_file(&pid_file_path(dir)).ok();
        }

        let wait_result = tokio::time::timeout(timeout, child.wait()).await;

        match wait_result {
            Ok(Ok(status)) => {
                info!(pid, ?status, "octobot binary stopped gracefully");
            }
            Ok(Err(e)) => {
                warn!(pid, error = %e, "error waiting for child process");
            }
            Err(_) => {
                warn!(pid, "graceful stop timed out, killing");
                let _ = child.kill().await;
                let _ = child.wait().await;
            }
        }

        Ok(())
    }

    async fn restart(
        &self,
        spec: &InstanceSpec,
        timeout: Duration,
        progress: Option<&ProgressSender>,
    ) -> Result<()> {
        match self.stop(spec.id, timeout).await {
            Ok(()) | Err(LauncherError::NotRunning) => {}
            Err(e) => return Err(e),
        }
        remove_pid_file(&pid_file_path(&spec.data_dir)).ok();
        self.start(spec, progress).await
    }

    async fn status(&self, _id: InstanceId) -> Result<HealthStatus> {
        let (state, uptime_seconds, probe_url) = {
            let inner = self.inner.lock().await;

            let probe_url = inner
                .runtime_options
                .as_ref()
                .and_then(|o| o.get("http_probe"))
                .and_then(|v| v.get("url"))
                .and_then(|v| v.as_str())
                .map(std::string::ToString::to_string);

            match (inner.child.as_ref(), inner.started_at) {
                (Some(_), Some(started_at)) => {
                    let pid = inner.pid.unwrap_or(0);
                    let uptime_secs = Utc::now()
                        .signed_duration_since(started_at)
                        .num_seconds()
                        .max(0);
                    let uptime = u64::try_from(uptime_secs).unwrap_or(0);
                    let state = InstanceState::Running {
                        pid_or_container: pid.to_string(),
                        started_at,
                    };
                    (state, Some(uptime), probe_url)
                }
                _ => (InstanceState::Stopped, None, probe_url),
            }
        };

        let last_http_check = if let Some(url) = probe_url {
            let probe = run_http_probe(&url).await;
            let mut inner = self.inner.lock().await;
            inner.last_http_check = Some(probe.clone());
            Some(probe)
        } else {
            self.inner.lock().await.last_http_check.clone()
        };

        Ok(HealthStatus {
            state,
            uptime_seconds,
            last_http_check,
        })
    }

    async fn update(
        &self,
        spec: &InstanceSpec,
        target_version: &str,
        progress: Option<&ProgressSender>,
    ) -> Result<()> {
        match self.stop(spec.id, Duration::from_secs(10)).await {
            Ok(()) | Err(LauncherError::NotRunning) => {}
            Err(e) => return Err(e),
        }

        let updater = self
            .updater
            .as_ref()
            .ok_or_else(|| LauncherError::Backend("no updater configured".to_string()))?;

        let dest_dir = spec.data_dir.join("bin");
        std::fs::create_dir_all(&dest_dir)?;

        send_progress(progress, format!("Downloading OctoBot {target_version}"));
        let downloaded = updater
            .fetch_artifact(ArtifactKind::OctoBotBinary, &dest_dir)
            .await
            .map_err(|e| LauncherError::Backend(e.to_string()))?;

        send_progress(progress, "Installing binary");
        let final_path = binary_path(&spec.data_dir);
        let new_path = new_binary_path(&spec.data_dir);
        std::fs::rename(&downloaded, &new_path)?;
        std::fs::rename(&new_path, &final_path)?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let perms = std::fs::Permissions::from_mode(0o755);
            std::fs::set_permissions(&final_path, perms)?;
        }

        self.start(spec, progress).await
    }

    async fn remove(&self, id: InstanceId, purge: bool) -> Result<()> {
        let data_dir = {
            let inner = self.inner.lock().await;
            inner.data_dir.clone()
        };

        match self.stop(id, Duration::from_secs(30)).await {
            Ok(()) | Err(LauncherError::NotRunning) => {}
            Err(e) => return Err(e),
        }

        if let Some(dir) = data_dir {
            remove_pid_file(&pid_file_path(&dir)).ok();

            if purge {
                let bin_dir = dir.join("bin");
                let log_dir = dir.join("logs");
                if bin_dir.exists() {
                    std::fs::remove_dir_all(&bin_dir)?;
                }
                if log_dir.exists() {
                    std::fs::remove_dir_all(&log_dir)?;
                }
            }
        }

        Ok(())
    }
}

fn send_graceful_signal(pid: u32) -> Result<()> {
    #[cfg(unix)]
    {
        match nix::sys::signal::kill(
            nix::unistd::Pid::from_raw(i32::try_from(pid).unwrap_or(i32::MAX)),
            nix::sys::signal::Signal::SIGTERM,
        ) {
            Ok(()) | Err(nix::errno::Errno::ESRCH) => {}
            Err(e) => return Err(LauncherError::Backend(format!("SIGTERM failed: {e}"))),
        }
    }
    #[cfg(windows)]
    {
        use windows::Win32::System::Console::GenerateConsoleCtrlEvent;
        unsafe {
            GenerateConsoleCtrlEvent(
                windows::Win32::System::Console::CTRL_BREAK_EVENT,
                pid,
            )
            .map_err(|e| LauncherError::Backend(format!("GenerateConsoleCtrlEvent failed: {e}")))?;
        }
    }
    #[cfg(not(any(unix, windows)))]
    let _ = pid;
    Ok(())
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    fn make_spec(data_dir: &Path) -> InstanceSpec {
        InstanceSpec {
            id: InstanceId::new(),
            name: "test-bot".into(),
            runtime: RuntimeKind::Binary,
            version: "1.0.0".into(),
            data_dir: data_dir.to_path_buf(),
            config_dir: data_dir.to_path_buf(),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        }
    }

    #[cfg(unix)]
    fn write_fake_octobot(data_dir: &Path) {
        use std::os::unix::fs::PermissionsExt;
        let bin_dir = data_dir.join("bin");
        std::fs::create_dir_all(&bin_dir).unwrap();
        let bin_path = binary_path(data_dir);
        std::fs::write(&bin_path, b"#!/bin/sh\nexec sleep 60\n").unwrap();
        let mut perms = std::fs::metadata(&bin_path).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&bin_path, perms).unwrap();
    }

    mod path {
        use super::*;

        #[test]
        fn binary_path_uses_correct_extension() {
            let p = binary_path(Path::new("/data"));
            if cfg!(windows) {
                assert!(p.to_string_lossy().ends_with(".exe"));
            } else {
                assert!(!p.to_string_lossy().ends_with(".exe"));
            }
        }
    }

    mod lifecycle {
        use super::*;

        #[cfg(unix)]
        #[tokio::test]
        async fn start_when_already_running_returns_error() {
            let tmp = tempfile::tempdir().unwrap();
            write_fake_octobot(tmp.path());
            let backend = BinaryBackend::default();
            let spec = make_spec(tmp.path());

            backend.prepare(&spec, None).await.unwrap();
            backend.start(&spec, None).await.unwrap();

            let result = backend.start(&spec, None).await;
            assert!(matches!(result, Err(LauncherError::AlreadyRunning)));

            backend.stop(spec.id, Duration::from_secs(5)).await.unwrap();
        }

        #[tokio::test]
        async fn stop_when_not_running_returns_error() {
            let tmp = tempfile::tempdir().unwrap();
            let backend = BinaryBackend::default();
            let spec = make_spec(tmp.path());

            let result = backend.stop(spec.id, Duration::from_secs(5)).await;
            assert!(matches!(result, Err(LauncherError::NotRunning)));
        }
    }

    #[cfg(unix)]
    mod signal {
        use super::*;

        #[tokio::test]
        async fn sigterm_then_sigkill() {
            let tmp = tempfile::tempdir().unwrap();
            write_fake_octobot(tmp.path());
            let backend = BinaryBackend::default();
            let spec = make_spec(tmp.path());

            backend.prepare(&spec, None).await.unwrap();
            backend.start(&spec, None).await.unwrap();

            let before = std::time::Instant::now();
            backend
                .stop(spec.id, Duration::from_millis(100))
                .await
                .unwrap();
            assert!(before.elapsed() < Duration::from_secs(5));
        }

        #[tokio::test]
        async fn graceful_exit_within_timeout() {
            use std::os::unix::fs::PermissionsExt;
            let tmp = tempfile::tempdir().unwrap();
            let bin_dir = tmp.path().join("bin");
            std::fs::create_dir_all(&bin_dir).unwrap();
            let bin_path = binary_path(tmp.path());
            std::fs::write(
                &bin_path,
                b"#!/bin/sh\ntrap 'exit 0' TERM\nsleep 60 & wait\n",
            )
            .unwrap();
            let mut perms = std::fs::metadata(&bin_path).unwrap().permissions();
            perms.set_mode(0o755);
            std::fs::set_permissions(&bin_path, perms).unwrap();

            let backend = BinaryBackend::default();
            let spec = make_spec(tmp.path());

            backend.prepare(&spec, None).await.unwrap();
            backend.start(&spec, None).await.unwrap();

            let before = std::time::Instant::now();
            backend
                .stop(spec.id, Duration::from_secs(5))
                .await
                .unwrap();
            assert!(before.elapsed() < Duration::from_secs(5));
        }
    }

    mod stdio {
        use super::*;

        #[cfg(unix)]
        #[tokio::test]
        async fn default_discards_output() {
            let tmp = tempfile::tempdir().unwrap();
            write_fake_octobot(tmp.path());
            let backend = BinaryBackend::default();
            let spec = make_spec(tmp.path());

            backend.prepare(&spec, None).await.unwrap();
            backend.start(&spec, None).await.unwrap();
            backend.stop(spec.id, Duration::from_secs(5)).await.unwrap();

            assert!(!stdio_log_path(tmp.path()).exists());
        }

        #[cfg(unix)]
        #[tokio::test]
        async fn capture_stdio_appends_to_log() {
            use std::os::unix::fs::PermissionsExt;
            let tmp = tempfile::tempdir().unwrap();
            let bin_dir = tmp.path().join("bin");
            std::fs::create_dir_all(&bin_dir).unwrap();
            let bin_path = binary_path(tmp.path());
            std::fs::write(&bin_path, b"#!/bin/sh\necho hello\nsleep 60\n").unwrap();
            let mut perms = std::fs::metadata(&bin_path).unwrap().permissions();
            perms.set_mode(0o755);
            std::fs::set_permissions(&bin_path, perms).unwrap();

            let backend = BinaryBackend::default();
            let mut spec = make_spec(tmp.path());
            spec.runtime_options = serde_json::json!({"capture_stdio": true});

            backend.prepare(&spec, None).await.unwrap();
            backend.start(&spec, None).await.unwrap();
            tokio::time::sleep(Duration::from_millis(200)).await;
            let _ = backend.stop(spec.id, Duration::from_secs(5)).await;

            assert!(stdio_log_path(tmp.path()).exists());
        }
    }

    mod update {
        use super::*;

        #[test]
        fn atomic_rename_replaces_binary() {
            let tmp = tempfile::tempdir().unwrap();
            let data_dir = tmp.path();
            let bin_dir = data_dir.join("bin");
            std::fs::create_dir_all(&bin_dir).unwrap();

            let bin_path = binary_path(data_dir);
            let new_path = new_binary_path(data_dir);

            std::fs::write(&bin_path, b"old").unwrap();
            std::fs::write(&new_path, b"new").unwrap();

            std::fs::rename(&new_path, &bin_path).unwrap();

            let contents = std::fs::read(&bin_path).unwrap();
            assert_eq!(contents, b"new");
        }
    }
}
