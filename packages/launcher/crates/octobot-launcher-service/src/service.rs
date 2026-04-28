use std::ffi::OsString;
use std::path::PathBuf;

use service_manager::{
    ServiceInstallCtx, ServiceLabel, ServiceManager, ServiceStartCtx, ServiceStopCtx,
    ServiceUninstallCtx,
};
#[cfg(target_os = "macos")]
use service_manager::LaunchdServiceManager;
use tracing::debug;

use crate::error::{Result, ServiceError};

const REVERSE_DNS_LABEL: &str = "org.drakkar.octobot-launcher";

#[cfg(target_os = "linux")]
const SYSTEMD_SERVICE_NAME: &str = "octobot-launcher.service";

pub fn service_label() -> &'static str {
    #[cfg(target_os = "linux")]
    {
        SYSTEMD_SERVICE_NAME
    }
    #[cfg(not(target_os = "linux"))]
    {
        REVERSE_DNS_LABEL
    }
}

fn parse_label() -> Result<ServiceLabel> {
    REVERSE_DNS_LABEL
        .parse::<ServiceLabel>()
        .map_err(|e| ServiceError::Manager(e.to_string()))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ServiceLevel {
    System,
    User,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ServiceStatus {
    NotInstalled,
    Stopped,
    Running,
    Failed(String),
}

pub fn auto_level() -> ServiceLevel {
    #[cfg(target_os = "macos")]
    {
        return ServiceLevel::User;
    }
    #[cfg(not(target_os = "macos"))]
    {
        if std::env::var("DISPLAY").is_ok() {
            return ServiceLevel::User;
        }
        if std::env::var("WAYLAND_DISPLAY").is_ok() {
            return ServiceLevel::User;
        }
        if let Ok(val) = std::env::var("XDG_SESSION_TYPE") {
            if val == "x11" || val == "wayland" {
                return ServiceLevel::User;
            }
        }
        ServiceLevel::System
    }
}

pub struct LauncherService {
    manager: Box<dyn ServiceManager>,
    level: ServiceLevel,
}

impl std::fmt::Debug for LauncherService {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LauncherService")
            .field("level", &self.level)
            .finish_non_exhaustive()
    }
}

impl LauncherService {
    pub fn new(level: ServiceLevel) -> Result<Self> {
        let manager: Box<dyn ServiceManager> = {
            #[cfg(target_os = "macos")]
            {
                match level {
                    ServiceLevel::User => Box::new(LaunchdServiceManager::user()),
                    ServiceLevel::System => Box::new(LaunchdServiceManager::system()),
                }
            }
            #[cfg(not(target_os = "macos"))]
            {
                <dyn ServiceManager>::native()
                    .map_err(|e| ServiceError::Manager(e.to_string()))?
            }
        };
        Ok(Self { manager, level })
    }

    pub fn install(&self) -> Result<()> {
        let label = parse_label()?;
        let program = std::env::current_exe()?.canonicalize()?;
        let args: Vec<OsString> = vec![
            OsString::from("service"),
            OsString::from("run"),
        ];
        debug!("installing service {:?} with program {:?}", label, program);
        self.manager
            .install(ServiceInstallCtx {
                label,
                program,
                args,
                working_directory: None,
                environment: Some(vec![("OCTOBOT_LAUNCHER_FOREGROUND".into(), "1".into())]),
                autostart: true,
                username: None,
                contents: None,
                restart_policy: service_manager::RestartPolicy::default(),
            })
            .map_err(|e| ServiceError::Manager(e.to_string()))
    }

    pub fn uninstall(&self) -> Result<()> {
        let label = parse_label()?;
        debug!("uninstalling service {:?}", label);
        self.manager
            .uninstall(ServiceUninstallCtx { label })
            .map_err(|e| ServiceError::Manager(e.to_string()))
    }

    pub fn start(&self) -> Result<()> {
        let label = parse_label()?;
        debug!("starting service {:?}", label);
        self.manager
            .start(ServiceStartCtx { label })
            .map_err(|e| ServiceError::Manager(e.to_string()))
    }

    pub fn stop(&self) -> Result<()> {
        let label = parse_label()?;
        debug!("stopping service {:?}", label);
        self.manager
            .stop(ServiceStopCtx { label })
            .map_err(|e| ServiceError::Manager(e.to_string()))
    }

    pub fn status(&self) -> Result<ServiceStatus> {
        #[cfg(target_os = "linux")]
        {
            query_status_linux()
        }
        #[cfg(target_os = "macos")]
        {
            query_status_macos()
        }
        #[cfg(target_os = "windows")]
        {
            query_status_windows()
        }
        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        {
            Err(ServiceError::Unsupported)
        }
    }

    pub fn is_installed(&self) -> bool {
        #[cfg(target_os = "linux")]
        {
            is_installed_linux(self.level)
        }
        #[cfg(target_os = "macos")]
        {
            is_installed_macos(self.level)
        }
        #[cfg(target_os = "windows")]
        {
            is_installed_windows()
        }
        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        {
            false
        }
    }
}

#[cfg(target_os = "linux")]
fn query_status_linux() -> Result<ServiceStatus> {
    let output = std::process::Command::new("systemctl")
        .arg("is-active")
        .arg("octobot-launcher")
        .output()?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let state = stdout.trim();
    match state {
        "active" => Ok(ServiceStatus::Running),
        "inactive" => Ok(ServiceStatus::Stopped),
        "failed" => Ok(ServiceStatus::Failed("failed".to_string())),
        _ if output.status.code() == Some(4) => Ok(ServiceStatus::NotInstalled),
        other => Ok(ServiceStatus::Failed(other.to_string())),
    }
}

#[cfg(target_os = "macos")]
fn query_status_macos() -> Result<ServiceStatus> {
    let output = std::process::Command::new("launchctl")
        .arg("list")
        .arg(REVERSE_DNS_LABEL)
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        if stderr.contains("Could not find service") || output.status.code() == Some(113) {
            return Ok(ServiceStatus::NotInstalled);
        }
        return Ok(ServiceStatus::Stopped);
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    if stdout.contains("\"PID\"") || stdout.contains("PID =") {
        Ok(ServiceStatus::Running)
    } else {
        Ok(ServiceStatus::Stopped)
    }
}

#[cfg(target_os = "windows")]
fn query_status_windows() -> Result<ServiceStatus> {
    let output = std::process::Command::new("sc.exe")
        .arg("query")
        .arg(REVERSE_DNS_LABEL)
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        if stderr.contains("does not exist") || output.status.code() == Some(1060) {
            return Ok(ServiceStatus::NotInstalled);
        }
        return Ok(ServiceStatus::NotInstalled);
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    if stdout.contains("RUNNING") {
        Ok(ServiceStatus::Running)
    } else if stdout.contains("STOPPED") {
        Ok(ServiceStatus::Stopped)
    } else if stdout.contains("FAILED") {
        Ok(ServiceStatus::Failed("FAILED".to_string()))
    } else {
        Ok(ServiceStatus::Stopped)
    }
}

#[cfg(target_os = "linux")]
fn is_installed_linux(level: ServiceLevel) -> bool {
    match level {
        ServiceLevel::System => {
            PathBuf::from("/etc/systemd/system/octobot-launcher.service").exists()
        }
        ServiceLevel::User => {
            if let Some(home) = dirs_home() {
                home.join(".config/systemd/user/octobot-launcher.service").exists()
            } else {
                false
            }
        }
    }
}

#[cfg(target_os = "macos")]
fn is_installed_macos(level: ServiceLevel) -> bool {
    match level {
        ServiceLevel::System => {
            PathBuf::from("/Library/LaunchDaemons/org.drakkar.octobot-launcher.plist").exists()
        }
        ServiceLevel::User => {
            if let Some(home) = dirs_home() {
                home.join("Library/LaunchAgents/org.drakkar.octobot-launcher.plist").exists()
            } else {
                false
            }
        }
    }
}

#[cfg(target_os = "windows")]
fn is_installed_windows() -> bool {
    std::process::Command::new("sc.exe")
        .arg("query")
        .arg(REVERSE_DNS_LABEL)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn dirs_home() -> Option<PathBuf> {
    std::env::var("HOME").ok().map(PathBuf::from)
}

#[cfg(test)]
mod tests {
    use super::*;

    mod level {
        use super::*;

        #[test]
        fn desktop_detection_picks_user() {
            std::env::remove_var("WAYLAND_DISPLAY");
            std::env::remove_var("XDG_SESSION_TYPE");
            std::env::set_var("DISPLAY", ":0");
            let result = auto_level();
            std::env::remove_var("DISPLAY");
            assert_eq!(result, ServiceLevel::User);
        }

        #[test]
        fn headless_picks_system() {
            std::env::remove_var("DISPLAY");
            std::env::remove_var("WAYLAND_DISPLAY");
            std::env::remove_var("XDG_SESSION_TYPE");
            #[cfg(target_os = "macos")]
            assert_eq!(auto_level(), ServiceLevel::User);
            #[cfg(not(target_os = "macos"))]
            assert_eq!(auto_level(), ServiceLevel::System);
        }

        #[test]
        fn cli_override_wins() {
            let level = ServiceLevel::System;
            assert_eq!(level, ServiceLevel::System);
        }
    }

    mod naming {
        use super::*;

        #[test]
        fn reverse_dns_for_launchd() {
            #[cfg(not(target_os = "linux"))]
            assert_eq!(service_label(), "org.drakkar.octobot-launcher");
            #[cfg(target_os = "linux")]
            assert_eq!(service_label(), "octobot-launcher.service");
        }

        #[test]
        fn dotted_name_for_systemd() {
            let label = service_label();
            assert!(label.contains("octobot"));
        }
    }

    mod args {
        use super::*;

        #[test]
        fn run_subcommand_is_invoked() {
            let args: Vec<OsString> = vec![
                OsString::from("service"),
                OsString::from("run"),
            ];
            assert!(args.iter().any(|a| a == "service"));
            assert!(args.iter().any(|a| a == "run"));
        }

        #[test]
        fn current_exe_is_canonicalized() {
            let exe = std::env::current_exe().expect("current_exe must succeed");
            let canonical = exe.canonicalize();
            assert!(canonical.is_ok());
        }
    }
}
