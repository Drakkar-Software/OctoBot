use std::sync::Arc;

use anyhow::{Context, Result};
use octobot_launcher_config::{LauncherConfig, Store};
use octobot_launcher_service::{ENV_FOREGROUND, LauncherService, ServiceLevel, ServiceStatus, auto_level};

use crate::cli::{ServiceArgs, ServiceCommands};
use crate::supervisor::run_supervisor;

fn spawn_daemon(config: &LauncherConfig) -> Result<()> {
    use std::ffi::OsString;
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
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();

    let child = std::process::Command::new(exe)
        .args(&args)
        .env(ENV_FOREGROUND, "1")
        .stdin(Stdio::null())
        .stdout(log_file.try_clone().context("clone log file handle")?)
        .stderr(log_file)
        .spawn()
        .context("spawn daemon process")?;

    println!("Launcher daemon started (pid {})", child.id());
    println!("Logs: {}", log_path.display());
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
            svc.stop().context("stop service")?;
            println!("Service stopped.");
            Ok(())
        }
        ServiceCommands::Restart => {
            let level = auto_level();
            let svc = LauncherService::new(level).context("create service manager")?;
            svc.stop().context("stop service")?;
            svc.start().context("start service")?;
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
