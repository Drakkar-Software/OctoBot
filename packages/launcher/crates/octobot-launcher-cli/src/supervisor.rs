use std::fs::File;
use std::sync::Arc;

use anyhow::{Context, Result};
use fs2::FileExt;
use octobot_launcher_api::{ApiServer, ApiState, ListenerConfig};
use octobot_launcher_api::token_store::TokenStore;
use octobot_launcher_binary::{BinaryBackend, BinaryBackendConfig};
use octobot_launcher_config::{
    DesiredState, LauncherConfig, LOCK_FILENAME, SOCKET_FILENAME, Store, BOOTSTRAP_TOKEN_FILENAME,
};
use octobot_launcher_core::Backend;
use octobot_launcher_docker::DockerBackend;
use octobot_launcher_python::{PythonBackend, PythonBackendConfig, PythonDistMode};
use octobot_launcher_update::{BAKED_PUBKEY_HEX, Updater};

use crate::write_bootstrap_token;

pub async fn run_supervisor(config: LauncherConfig, store: Arc<Store>) -> Result<()> {
    let lock_path = config.launcher.data_root.join(LOCK_FILENAME);
    std::fs::create_dir_all(&config.launcher.data_root)
        .with_context(|| format!("create data root {}", config.launcher.data_root.display()))?;
    let lock_file = File::create(&lock_path)
        .with_context(|| format!("open lock file {}", lock_path.display()))?;
    lock_file.try_lock_exclusive().map_err(|_| {
        anyhow::anyhow!("Another launcher instance is running")
    })?;

    let token_store = Arc::new(TokenStore::load(store.tokens_path()));

    if let Some(raw) = token_store.bootstrap_if_empty().context("bootstrap token")? {
        let bootstrap_path = config.launcher.data_root.join(BOOTSTRAP_TOKEN_FILENAME);
        write_bootstrap_token(&bootstrap_path, &raw)?;
        println!("Bootstrap admin token (saved to {}):", bootstrap_path.display());
        println!("  {raw}");
        println!();
    }

    let mut backends: Vec<Box<dyn Backend>> = Vec::new();

    if config.backends.docker.enabled {
        match DockerBackend::new() {
            Ok(b) => backends.push(Box::new(b)),
            Err(e) => tracing::warn!("docker backend disabled: {e}"),
        }
    }

    if config.backends.binary.enabled {
        let mut binary_backend = BinaryBackend::new(BinaryBackendConfig::default());
        if let Some(updater) = build_updater(&config, &store) {
            binary_backend = binary_backend.with_updater(Arc::new(updater));
        }
        backends.push(Box::new(binary_backend));
    }

    if config.backends.python.enabled {
        let dist_mode = match config.backends.python.default_python_dist.as_str() {
            "always" => PythonDistMode::Always,
            "never" => PythonDistMode::Never,
            _ => PythonDistMode::Auto,
        };
        backends.push(Box::new(PythonBackend::new(PythonBackendConfig {
            python_dist: dist_mode,
        })));
    }

    let tcp_bind: std::net::SocketAddr = config
        .launcher
        .api_bind
        .parse()
        .with_context(|| format!("parse api_bind '{}'", config.launcher.api_bind))?;

    let unix_socket_path = {
        #[cfg(unix)]
        {
            Some(config.launcher.data_root.join(SOCKET_FILENAME))
        }
        #[cfg(not(unix))]
        {
            None
        }
    };

    let backends = Arc::new(backends);

    let lockout = Arc::new(octobot_launcher_api::lockout::Lockout::new());
    let api_state = ApiState {
        store: Arc::clone(&store),
        token_store: Arc::clone(&token_store),
        lockout,
        backends: Arc::clone(&backends),
    };
    let listener_config = ListenerConfig {
        tcp_bind,
        unix_socket_path,
    };
    let api_server = ApiServer::new(api_state, listener_config);

    let records = store.list_instance_records()?;
    for record in records {
        if record.desired_state == DesiredState::Running {
            let spec = record.spec.clone();
            let runtime = spec.runtime;
            let backends_ref = Arc::clone(&backends);
            tokio::spawn(async move {
                if let Some(backend) = backends_ref.iter().find(|b| b.kind() == runtime) {
                    if let Err(e) = backend.start(&spec, None).await {
                        tracing::warn!("failed to start instance {}: {e}", spec.id);
                    }
                }
            });
        }
    }

    let pending_restart = config.launcher.data_root.join("pending_restart");
    if pending_restart.exists() {
        let _ = std::fs::remove_file(&pending_restart);
    }

    #[cfg(unix)]
    {
        use tokio::signal::unix::{SignalKind, signal};
        let mut sigterm = signal(SignalKind::terminate())?;
        let mut sigint = signal(SignalKind::interrupt())?;

        tokio::select! {
            result = api_server.serve() => {
                result.with_context(|| "API server error")?;
            }
            _ = sigterm.recv() => {
                tracing::info!("received SIGTERM, shutting down");
            }
            _ = sigint.recv() => {
                tracing::info!("received SIGINT, shutting down");
            }
        }
    }

    #[cfg(not(unix))]
    {
        tokio::select! {
            result = api_server.serve() => {
                result.with_context(|| "API server error")?;
            }
            result = tokio::signal::ctrl_c() => {
                result.with_context(|| "signal error")?;
                tracing::info!("received Ctrl-C, shutting down");
            }
        }
    }

    Ok(())
}

fn build_updater(config: &LauncherConfig, store: &Store) -> Option<Updater> {
    Updater::from_baked_config(
        config.update.manifest_url.clone(),
        config.update.channel.clone(),
        BAKED_PUBKEY_HEX,
        store.data_root().join("update-state"),
        store.data_root().join("update-cache"),
    )
}
