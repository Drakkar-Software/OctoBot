use std::sync::Arc;

use anyhow::{Context, Result};
use octobot_launcher_config::{LauncherConfig, LAUNCHER_PID_FILENAME, Store};
use octobot_launcher_service::{ENV_FOREGROUND, LauncherService, ServiceLevel, ServiceStatus, auto_level};

use crate::cli::{ServiceArgs, ServiceCommands};
use crate::supervisor::run_supervisor;

fn spawn_daemon(config: &LauncherConfig) -> Result<()> {
    use std::process::Stdio;

    let log_path = config.launcher.data_root.join("launcher.log");
    std::fs::create_dir_all(&config.launcher.data_root)
        .with_context(|| format!("create data root {}", config.launcher.data_root.display()))?;
    let log_file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .with_context(|| format!("open log file {}", log_path.display()))?;

    let exe = std::env::current_exe().context("resolve current exe")?;

    let mut child = std::process::Command::new(exe)
        .args(["service", "run"])
        .env(ENV_FOREGROUND, "1")
        .stdin(Stdio::null())
        .stdout(log_file.try_clone().context("clone log file handle")?)
        .stderr(log_file)
        .spawn()
        .context("spawn daemon process")?;

    std::thread::sleep(std::time::Duration::from_millis(700));

    match child.try_wait() {
        Ok(Some(status)) => {
            let tail = tail_log(&log_path, 30).unwrap_or_default();
            anyhow::bail!(
                "Launcher daemon exited immediately (status: {status}).\nLast log lines from {}:\n{tail}",
                log_path.display()
            );
        }
        Ok(None) => {
            println!("Launcher daemon started (pid {}).", child.id());
            println!("Logs: {}", log_path.display());
        }
        Err(e) => return Err(e).context("check daemon status"),
    }
    Ok(())
}

pub async fn handle_service(args: ServiceArgs, config: &LauncherConfig) -> Result<()> {
    match args.command {
        ServiceCommands::Install { user, system } => {
            let level = resolve_level(user, system);
            let svc = LauncherService::new(level).context("create service manager")?;
            svc.install().context("install service")?;
            println!("Service installed ({level:?}).");
            Ok(())
        }
        ServiceCommands::Uninstall => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            svc.uninstall().context("uninstall service")?;
            println!("Service uninstalled.");
            Ok(())
        }
        ServiceCommands::Start => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            svc.start().context("start service")?;
            println!("Service started.");
            Ok(())
        }
        ServiceCommands::Stop => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            let svc_running = matches!(svc.status(), Ok(ServiceStatus::Running));
            if svc_running {
                svc.stop().context("stop service")?;
            }
            stop_pid_file_daemon(&config.launcher.data_root.join(LAUNCHER_PID_FILENAME));
            println!("Service stopped.");
            Ok(())
        }
        ServiceCommands::Restart => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            let svc_running = matches!(svc.status(), Ok(ServiceStatus::Running));
            if svc_running {
                svc.stop().context("stop service")?;
            }
            stop_pid_file_daemon(&config.launcher.data_root.join(LAUNCHER_PID_FILENAME));
            spawn_daemon(config)?;
            println!("Service restarted.");
            Ok(())
        }
        ServiceCommands::Status => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            let status = svc.status().context("query service status")?;
            match status {
                ServiceStatus::Running => println!("Service is running."),
                ServiceStatus::Stopped => println!("Service is stopped."),
                ServiceStatus::NotInstalled => println!("Service is not installed."),
                ServiceStatus::Failed(reason) => println!("Service failed: {reason}"),
            }
            Ok(())
        }
        ServiceCommands::Run => {
            if std::env::var(ENV_FOREGROUND).is_err() {
                return spawn_daemon(config);
            }
            let store = Arc::new(
                Store::new(config.launcher.data_root.clone()).context("open store")?,
            );
            run_supervisor(config.clone(), store).await
        }
    }
}

fn resolve_level(user: bool, system: bool) -> ServiceLevel {
    if system {
        return ServiceLevel::System;
    }
    if user {
        return ServiceLevel::User;
    }
    auto_level()
}

fn tail_log(path: &std::path::Path, n: usize) -> Option<String> {
    let content = std::fs::read_to_string(path).ok()?;
    let lines: Vec<&str> = content.lines().collect();
    let start = lines.len().saturating_sub(n);
    Some(lines[start..].join("\n"))
}

fn stop_pid_file_daemon(pid_path: &std::path::Path) {
    let Ok(pid_str) = std::fs::read_to_string(pid_path) else { return };
    let Ok(pid) = pid_str.trim().parse::<u32>() else { return };

    #[cfg(unix)]
    {
        let pid_s = pid.to_string();
        let _ = std::process::Command::new("kill").args(["-TERM", &pid_s]).status();
        for _ in 0..30 {
            let alive = std::process::Command::new("kill")
                .args(["-0", &pid_s])
                .status()
                .map(|s| s.success())
                .unwrap_or(false);
            if !alive { break; }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
    }
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .status();
    }
}
