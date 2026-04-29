use std::path::PathBuf;

#[cfg(not(windows))]
const DOCKER_SOCKET_UNIX: &str = "/var/run/docker.sock";
#[cfg(windows)]
const DOCKER_SOCKET_WINDOWS: &str = "npipe:////./pipe/docker_engine";

use figment::{
    providers::{Env, Format, Toml},
    Figment,
};
use serde::{Deserialize, Serialize};

use crate::error::{ConfigError, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LauncherSection {
    pub api_bind: String,
    pub log_level: String,
    pub data_root: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateSection {
    pub channel: String,
    pub auto_update_launcher: bool,
    pub auto_update_instances: bool,
    pub check_interval_hours: u32,
    pub manifest_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DockerBackendConfig {
    pub enabled: bool,
    pub socket: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BinaryBackendConfig {
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonBackendConfig {
    pub enabled: bool,
    pub default_python_dist: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendsSection {
    pub docker: DockerBackendConfig,
    pub binary: BinaryBackendConfig,
    pub python: PythonBackendConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LauncherConfig {
    pub launcher: LauncherSection,
    pub update: UpdateSection,
    pub backends: BackendsSection,
}

fn default_launcher_section() -> LauncherSection {
    LauncherSection {
        api_bind: "127.0.0.1:7531".to_string(),
        log_level: "info".to_string(),
        data_root: default_data_root(false),
    }
}

fn default_update_section() -> UpdateSection {
    UpdateSection {
        channel: "stable".to_string(),
        auto_update_launcher: true,
        auto_update_instances: false,
        check_interval_hours: 6,
        manifest_url: "https://updates.drakkar.software/octobot-launcher/v1/manifest.json"
            .to_string(),
    }
}

fn default_backends_section() -> BackendsSection {
    BackendsSection {
        docker: DockerBackendConfig {
            enabled: true,
            #[cfg(unix)]
            socket: DOCKER_SOCKET_UNIX.to_string(),
            #[cfg(windows)]
            socket: DOCKER_SOCKET_WINDOWS.to_string(),
            #[cfg(not(any(unix, windows)))]
            socket: DOCKER_SOCKET_UNIX.to_string(),
        },
        binary: BinaryBackendConfig { enabled: true },
        python: PythonBackendConfig {
            enabled: true,
            default_python_dist: "auto".to_string(),
        },
    }
}

impl Default for LauncherConfig {
    fn default() -> Self {
        Self {
            launcher: default_launcher_section(),
            update: default_update_section(),
            backends: default_backends_section(),
        }
    }
}

fn default_toml_string() -> String {
    let defaults = LauncherConfig::default();
    let launcher = &defaults.launcher;
    let update = &defaults.update;
    let backends = &defaults.backends;

    let data_root = launcher.data_root.display().to_string().replace('\\', "/");
    let docker_socket = backends.docker.socket.replace('\\', "/");

    format!(
        r#"[launcher]
api_bind = "{api_bind}"
log_level = "{log_level}"
data_root = "{data_root}"

[update]
channel = "{channel}"
auto_update_launcher = {auto_update_launcher}
auto_update_instances = {auto_update_instances}
check_interval_hours = {check_interval_hours}
manifest_url = "{manifest_url}"

[backends.docker]
enabled = {docker_enabled}
socket = "{docker_socket}"

[backends.binary]
enabled = {binary_enabled}

[backends.python]
enabled = {python_enabled}
default_python_dist = "{default_python_dist}"
"#,
        api_bind = launcher.api_bind,
        log_level = launcher.log_level,
        data_root = data_root,
        channel = update.channel,
        auto_update_launcher = update.auto_update_launcher,
        auto_update_instances = update.auto_update_instances,
        check_interval_hours = update.check_interval_hours,
        manifest_url = update.manifest_url,
        docker_enabled = backends.docker.enabled,
        docker_socket = docker_socket,
        binary_enabled = backends.binary.enabled,
        python_enabled = backends.python.enabled,
        default_python_dist = backends.python.default_python_dist,
    )
}

pub fn load_config(config_path: Option<&std::path::Path>) -> Result<LauncherConfig> {
    let defaults_toml = default_toml_string();

    let mut figment = Figment::new().merge(Toml::string(&defaults_toml));

    if let Some(path) = config_path {
        if path.exists() {
            figment = figment.merge(Toml::file(path));
        }
    } else {
        let default_path = default_config_path(false);
        if default_path.exists() {
            figment = figment.merge(Toml::file(&default_path));
        }
    }

    figment = figment.merge(Env::prefixed("OCTOBOT_LAUNCHER__").split("__"));

    let config: LauncherConfig = figment.extract().map_err(|e| ConfigError::Load(e.to_string()))?;

    validate_config(&config)?;

    Ok(config)
}

fn validate_config(config: &LauncherConfig) -> Result<()> {
    let valid_levels = ["trace", "debug", "info", "warn", "error"];
    if !valid_levels.contains(&config.launcher.log_level.as_str()) {
        return Err(ConfigError::Validation(format!(
            "invalid log_level '{}': must be one of trace, debug, info, warn, error",
            config.launcher.log_level
        )));
    }
    Ok(())
}

pub fn default_config_path(system: bool) -> PathBuf {
    if system {
        #[cfg(target_os = "linux")]
        return PathBuf::from("/etc/octobot-launcher/config.toml");
        #[cfg(target_os = "macos")]
        return PathBuf::from("/Library/Application Support/OctoBotLauncher/config.toml");
        #[cfg(target_os = "windows")]
        {
            let programdata =
                std::env::var("PROGRAMDATA").unwrap_or_else(|_| "C:\\ProgramData".to_string());
            return PathBuf::from(programdata).join("OctoBotLauncher").join("config.toml");
        }
        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        return PathBuf::from("/etc/octobot-launcher/config.toml");
    }

    if let Some(proj_dirs) =
        directories::ProjectDirs::from("software", "Drakkar", "OctoBotLauncher")
    {
        proj_dirs.config_dir().join("config.toml")
    } else {
        PathBuf::from("config.toml")
    }
}

pub fn default_data_root(system: bool) -> PathBuf {
    if system || is_root_user() {
        #[cfg(target_os = "linux")]
        return PathBuf::from("/var/lib/octobot-launcher");
        #[cfg(target_os = "macos")]
        return PathBuf::from("/Library/Application Support/OctoBotLauncher");
        #[cfg(target_os = "windows")]
        {
            let programdata =
                std::env::var("PROGRAMDATA").unwrap_or_else(|_| "C:\\ProgramData".to_string());
            return PathBuf::from(programdata).join("OctoBotLauncher");
        }
        #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
        return PathBuf::from("/var/lib/octobot-launcher");
    }

    if let Some(proj_dirs) =
        directories::ProjectDirs::from("software", "Drakkar", "OctoBotLauncher")
    {
        proj_dirs.data_dir().to_path_buf()
    } else {
        PathBuf::from("data")
    }
}

#[cfg(unix)]
fn is_root_user() -> bool {
    std::process::Command::new("id")
        .arg("-u")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| s.trim().parse::<u32>().ok())
        == Some(0)
}

#[cfg(not(unix))]
fn is_root_user() -> bool {
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write as IoWrite;

    fn env_lock() -> std::sync::MutexGuard<'static, ()> {
        crate::TEST_ENV_LOCK.get_or_init(|| std::sync::Mutex::new(())).lock().unwrap()
    }

    fn write_toml(dir: &tempfile::TempDir, content: &str) -> PathBuf {
        let path = dir.path().join("config.toml");
        let mut f = std::fs::File::create(&path).expect("create config file");
        f.write_all(content.as_bytes()).expect("write config file");
        path
    }

    #[test]
    fn default_values_loaded() {
        let _g = env_lock();
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "");
        let config = load_config(Some(&path)).expect("load config");
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
        assert!(config.backends.binary.enabled);
        assert!(config.backends.python.enabled);
        assert_eq!(config.backends.python.default_python_dist, "auto");
    }

    #[test]
    fn env_var_override() {
        let _g = env_lock();
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "");
        std::env::set_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND", "0.0.0.0:9000");
        let config = load_config(Some(&path)).expect("load config");
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        assert_eq!(config.launcher.api_bind, "0.0.0.0:9000");
    }

    #[test]
    fn missing_file_uses_defaults() {
        let _g = env_lock();
        std::env::remove_var("OCTOBOT_LAUNCHER__LAUNCHER__API_BIND");
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = dir.path().join("nonexistent.toml");
        let config = load_config(Some(&path)).expect("load config");
        assert_eq!(config.launcher.api_bind, "127.0.0.1:7531");
        assert_eq!(config.update.channel, "stable");
    }

    #[test]
    fn malformed_toml_returns_error() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "[[[ broken toml");
        let result = load_config(Some(&path));
        assert!(matches!(result, Err(ConfigError::Load(_))));
    }

    #[test]
    fn invalid_log_level_rejected() {
        let dir = tempfile::TempDir::new().expect("tempdir");
        let path = write_toml(&dir, "[launcher]\nlog_level = \"blarg\"");
        let result = load_config(Some(&path));
        assert!(matches!(result, Err(ConfigError::Validation(_))));
    }

    #[test]
    fn path_locations_per_platform() {
        let system_path = default_config_path(true);
        let user_path = default_config_path(false);
        assert!(!system_path.as_os_str().is_empty());
        assert!(!user_path.as_os_str().is_empty());
    }
}
