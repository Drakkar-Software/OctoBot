use std::path::{Path, PathBuf};

use octobot_launcher_core::error::{LauncherError, Result};

pub(crate) async fn create_venv(python: &Path, venv_dir: &Path) -> std::io::Result<()> {
    let status = tokio::process::Command::new(python)
        .args(["-m", "venv"])
        .arg(venv_dir)
        .status()
        .await?;

    if !status.success() {
        return Err(std::io::Error::other(format!(
            "python -m venv exited with status {}",
            status.code().unwrap_or(-1)
        )));
    }
    Ok(())
}

pub(crate) fn venv_python(venv_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv_dir.join("Scripts").join("python.exe");
    #[cfg(not(windows))]
    return venv_dir.join("bin").join("python");
}

pub(crate) fn venv_pip(venv_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv_dir.join("Scripts").join("pip.exe");
    #[cfg(not(windows))]
    return venv_dir.join("bin").join("pip");
}

pub(crate) fn venv_octobot(venv_dir: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv_dir.join("Scripts").join("OctoBot.exe");
    #[cfg(not(windows))]
    return venv_dir.join("bin").join("OctoBot");
}

pub(crate) async fn pip_install(pip: &Path, package_spec: &str) -> Result<()> {
    let status = tokio::process::Command::new(pip)
        .args(["install", "--upgrade", package_spec])
        .status()
        .await
        .map_err(|e| LauncherError::Backend(format!("pip install failed to spawn: {e}")))?;

    if !status.success() {
        return Err(LauncherError::Backend(format!(
            "pip install failed: exit code {}",
            status.code().unwrap_or(-1)
        )));
    }
    Ok(())
}

pub(crate) async fn pip_install_editable(pip: &Path, source_dir: &Path) -> Result<()> {
    let status = tokio::process::Command::new(pip)
        .args(["install", "-e"])
        .arg(source_dir)
        .status()
        .await
        .map_err(|e| LauncherError::Backend(format!("pip install -e failed to spawn: {e}")))?;

    if !status.success() {
        return Err(LauncherError::Backend(format!(
            "pip install -e failed: exit code {}",
            status.code().unwrap_or(-1)
        )));
    }
    Ok(())
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    async fn require_python() -> Option<PathBuf> {
        which::which("python3")
            .ok()
            .or_else(|| which::which("python").ok())
    }

    #[tokio::test]
    async fn create_venv_creates_pip() {
        let python = match require_python().await {
            Some(p) => p,
            None => return,
        };
        let tmp = tempfile::tempdir().unwrap();
        create_venv(&python, tmp.path()).await.unwrap();
        let pip = venv_pip(tmp.path());
        assert!(pip.exists(), "pip not found at {}", pip.display());
    }

    #[tokio::test]
    async fn idempotent_prepare() {
        let python = match require_python().await {
            Some(p) => p,
            None => return,
        };
        let tmp = tempfile::tempdir().unwrap();
        create_venv(&python, tmp.path()).await.unwrap();
        create_venv(&python, tmp.path()).await.unwrap();
        let pip = venv_pip(tmp.path());
        assert!(pip.exists());
    }

    #[tokio::test]
    async fn pip_install_failure_preserves_old_state() {
        let python = match require_python().await {
            Some(p) => p,
            None => return,
        };
        let tmp = tempfile::tempdir().unwrap();
        create_venv(&python, tmp.path()).await.unwrap();
        let pip = venv_pip(tmp.path());
        let result = pip_install(&pip, "OctoBot==999.0.0").await;
        assert!(result.is_err());
        assert!(pip.exists(), "venv pip still intact after failed install");
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn editable_install() {
        let python = match require_python().await {
            Some(p) => p,
            None => return,
        };
        let tmp = tempfile::tempdir().unwrap();
        let venv_dir = tmp.path().join("venv");
        create_venv(&python, &venv_dir).await.unwrap();
        let pip = venv_pip(&venv_dir);

        let src_dir = tmp.path().join("mypackage");
        std::fs::create_dir_all(&src_dir).unwrap();
        std::fs::write(
            src_dir.join("setup.py"),
            b"from setuptools import setup\nsetup(name='mypackage', version='0.1.0')\n",
        )
        .unwrap();

        let result = pip_install_editable(&pip, &src_dir).await;
        assert!(result.is_ok(), "editable install failed: {result:?}");
        assert!(venv_python(&venv_dir).exists());
    }
}
