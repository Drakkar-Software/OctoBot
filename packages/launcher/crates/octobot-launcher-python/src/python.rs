use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use octobot_launcher_core::backend::{send_progress, ProgressSender};
use octobot_launcher_core::error::{LauncherError, Result};
use octobot_launcher_core::model::{HealthStatus, InstanceId, InstanceSpec, InstanceState, RuntimeKind};
use octobot_launcher_core::Backend;
use tokio::process::Child;
use tokio::sync::Mutex;
use tracing::{info, warn};

use crate::discovery::discover_python;
use crate::venv::{create_venv, pip_install, pip_install_editable, venv_octobot, venv_pip, venv_python};

fn venv_dir(data_dir: &Path) -> PathBuf {
    data_dir.join("venv")
}

fn pid_file_path(data_dir: &Path) -> PathBuf {
    data_dir.join("octobot.pid")
}

fn stdio_log_path(data_dir: &Path) -> PathBuf {
    data_dir.join("logs").join("launcher-stdio.log")
}

fn write_pid_file(path: &Path, pid: u32) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, pid.to_string())
}

fn remove_pid_file(path: &Path) {
    if path.exists() {
        let _ = std::fs::remove_file(path);
    }
}

struct Inner {
    child: Option<Child>,
    started_at: Option<DateTime<Utc>>,
    pid: Option<u32>,
    data_dir: Option<PathBuf>,
    runtime_options: Option<serde_json::Value>,
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
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PythonDistMode {
    Auto,
    Always,
    Never,
}

#[derive(Debug)]
pub struct PythonBackendConfig {
    pub python_dist: PythonDistMode,
}

impl Default for PythonBackendConfig {
    fn default() -> Self {
        Self {
            python_dist: PythonDistMode::Auto,
        }
    }
}

#[derive(Debug)]
pub struct PythonBackend {
    #[allow(dead_code)]
    config: PythonBackendConfig,
    inner: Arc<Mutex<Inner>>,
    start_lock: Arc<Mutex<()>>,
}

impl PythonBackend {
    pub fn new(config: PythonBackendConfig) -> Self {
        Self {
            config,
            inner: Arc::new(Mutex::new(Inner::new())),
            start_lock: Arc::new(Mutex::new(())),
        }
    }
}

impl Default for PythonBackend {
    fn default() -> Self {
        Self::new(PythonBackendConfig::default())
    }
}

#[async_trait]
impl Backend for PythonBackend {
    fn kind(&self) -> RuntimeKind {
        RuntimeKind::Python
    }

    async fn probe(&self) -> Result<()> {
        let python = discover_python(Path::new("."), &serde_json::Value::Null).await;
        match python {
            Some(_) => Ok(()),
            None => Err(LauncherError::BackendUnavailable(
                "no Python ≥ 3.10 found".into(),
            )),
        }
    }

    async fn prepare(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        let venv = venv_dir(&spec.data_dir);
        let logs_dir = spec.data_dir.join("logs");
        std::fs::create_dir_all(&venv)?;
        std::fs::create_dir_all(&logs_dir)?;

        send_progress(progress, "Discovering Python interpreter");
        let python = discover_python(&spec.data_dir, &spec.runtime_options)
            .await
            .ok_or_else(|| LauncherError::BackendUnavailable("no Python ≥ 3.10 found".into()))?;

        let venv_py = venv_python(&venv);
        if !venv_py.exists() {
            send_progress(progress, "Creating virtual environment");
            create_venv(&python, &venv)
                .await
                .map_err(|e| LauncherError::Backend(format!("create_venv failed: {e}")))?;
        }

        let pip = venv_pip(&venv);
        send_progress(progress, "Upgrading pip");
        pip_install(&pip, "pip").await?;

        let source_dir = spec
            .runtime_options
            .get("source_dir")
            .and_then(|v| v.as_str())
            .map(PathBuf::from);

        if let Some(src) = source_dir {
            send_progress(progress, format!("Installing OctoBot from {}", src.display()));
            pip_install_editable(&pip, &src).await?;
        } else {
            let pkg = if spec.version == "latest" {
                "OctoBot".to_string()
            } else {
                format!("OctoBot=={}", spec.version)
            };
            send_progress(progress, format!("Installing {pkg}"));
            pip_install(&pip, &pkg).await?;
        }

        Ok(())
    }

    async fn start(&self, spec: &InstanceSpec, progress: Option<&ProgressSender>) -> Result<()> {
        let _start_guard = self
            .start_lock
            .try_lock()
            .map_err(|_| LauncherError::AlreadyRunning)?;
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

        self.prepare(spec, progress).await?;

        let venv = venv_dir(&spec.data_dir);
        let bin = venv_octobot(&venv);

        let mut cmd = tokio::process::Command::new(&bin);
        cmd.current_dir(&spec.data_dir);

        for (k, v) in &spec.env {
            cmd.env(k, v);
        }

        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
            cmd.creation_flags(CREATE_NEW_PROCESS_GROUP);
        }

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

        cmd.kill_on_drop(false);

        send_progress(progress, "Starting OctoBot");
        let mut child = cmd.spawn()?;
        let pid = child.id().ok_or_else(|| {
            LauncherError::Backend("failed to get child PID after spawn".to_string())
        })?;

        write_pid_file(&pid_file_path(&spec.data_dir), pid)?;

        tokio::time::sleep(Duration::from_millis(300)).await;
        if let Ok(Some(exit_status)) = child.try_wait() {
            return Err(LauncherError::Backend(format!(
                "OctoBot exited immediately ({exit_status}), check: {}",
                log_path.display()
            )));
        }

        let mut inner = self.inner.lock().await;
        inner.pid = Some(pid);
        inner.started_at = Some(Utc::now());
        inner.data_dir = Some(spec.data_dir.clone());
        inner.runtime_options = Some(spec.runtime_options.clone());
        inner.child = Some(child);

        info!(pid, bin = %bin.display(), "octobot python started");
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
            (child, data_dir)
        };

        if let Some(ref dir) = data_dir {
            remove_pid_file(&pid_file_path(dir));
        }

        let wait_result = tokio::time::timeout(timeout, child.wait()).await;

        match wait_result {
            Ok(Ok(status)) => {
                info!(pid, ?status, "octobot python stopped gracefully");
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
        remove_pid_file(&pid_file_path(&spec.data_dir));
        self.start(spec, progress).await
    }

    async fn status(&self, _id: InstanceId) -> Result<HealthStatus> {
        let mut inner = self.inner.lock().await;

        if let Some(ref mut child) = inner.child {
            if let Ok(Some(_)) = child.try_wait() {
                inner.child = None;
                inner.started_at = None;
                inner.pid = None;
            }
        }

        match (inner.child.as_ref(), inner.started_at) {
            (Some(_), Some(started_at)) => {
                let pid = inner.pid.unwrap_or(0);
                let uptime = Utc::now()
                    .signed_duration_since(started_at)
                    .num_seconds()
                    .max(0);
                let uptime = u64::try_from(uptime).unwrap_or(0);
                Ok(HealthStatus {
                    state: InstanceState::Running {
                        pid_or_container: pid.to_string(),
                        started_at,
                    },
                    uptime_seconds: Some(uptime),
                    last_http_check: None,
                })
            }
            _ => Ok(HealthStatus {
                state: InstanceState::Stopped,
                uptime_seconds: None,
                last_http_check: None,
            }),
        }
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

        let venv = venv_dir(&spec.data_dir);
        let pip = venv_pip(&venv);

        send_progress(progress, format!("Installing OctoBot=={target_version}"));
        pip_install(&pip, &format!("OctoBot=={target_version}")).await?;

        self.start(spec, progress).await
    }

    async fn remove(&self, id: InstanceId, purge: bool) -> Result<()> {
        let data_dir = {
            let inner = self.inner.lock().await;
            inner.data_dir.clone()
        };

        match self.stop(id, Duration::from_secs(10)).await {
            Ok(()) | Err(LauncherError::NotRunning) => {}
            Err(e) => return Err(e),
        }

        if let Some(dir) = data_dir {
            remove_pid_file(&pid_file_path(&dir));

            if purge {
                let venv = venv_dir(&dir);
                let log_dir = dir.join("logs");
                if venv.exists() {
                    std::fs::remove_dir_all(&venv)?;
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
            runtime: RuntimeKind::Python,
            version: "2.4.0".into(),
            data_dir: data_dir.to_path_buf(),
            config_dir: data_dir.to_path_buf(),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        }
    }

    #[tokio::test]
    async fn stop_when_not_running_returns_error() {
        let tmp = tempfile::tempdir().unwrap();
        let backend = PythonBackend::default();
        let spec = make_spec(tmp.path());
        let result = backend.stop(spec.id, Duration::from_secs(5)).await;
        assert!(matches!(result, Err(LauncherError::NotRunning)));
    }

    #[test]
    fn default_config_is_auto_dist() {
        let backend = PythonBackend::default();
        assert_eq!(backend.config.python_dist, PythonDistMode::Auto);
    }

    #[tokio::test]
    async fn prepare_emits_progress_messages() {
        let python = match which::which("python3")
            .ok()
            .or_else(|| which::which("python").ok())
        {
            Some(p) => p,
            None => return,
        };

        let tmp = tempfile::tempdir().unwrap();
        let venv_dir = tmp.path().join("venv");
        crate::venv::create_venv(&python, &venv_dir).await.unwrap();

        let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel::<String>();
        let backend = PythonBackend::default();
        let mut spec = make_spec(tmp.path());
        spec.version = "latest".into();

        let _ = backend.prepare(&spec, Some(&tx)).await;
        drop(tx);

        let mut messages = vec![];
        while let Ok(msg) = rx.try_recv() {
            messages.push(msg);
        }
        assert!(
            messages.iter().any(|m| m.contains("Discovering")),
            "expected 'Discovering' in progress messages: {messages:?}"
        );
    }

    mod update {
        use super::*;

        #[cfg(unix)]
        #[tokio::test]
        async fn version_change_reflected() {
            use crate::venv::{create_venv, pip_install};

            let python = match which::which("python3")
                .ok()
                .or_else(|| which::which("python").ok())
            {
                Some(p) => p,
                None => return,
            };

            let tmp = tempfile::tempdir().unwrap();
            let venv = tmp.path().join("venv");
            create_venv(&python, &venv).await.unwrap();
            let pip = crate::venv::venv_pip(&venv);

            let result = pip_install(&pip, "OctoBot==2.4.0").await;
            if result.is_err() {
                return;
            }

            let output = tokio::process::Command::new(&pip)
                .args(["show", "OctoBot"])
                .output()
                .await
                .unwrap();
            let text = String::from_utf8_lossy(&output.stdout);
            assert!(text.contains("2.4.0"), "expected version 2.4.0 in: {text}");
        }
    }
}
