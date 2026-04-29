use anyhow::Result;
use octobot_launcher_api::token_store::TokenStore;
use octobot_launcher_binary::{BinaryBackend, BinaryBackendConfig};
use octobot_launcher_config::LauncherConfig;
use octobot_launcher_core::{Backend, LauncherError};
use octobot_launcher_docker::DockerBackend;
use octobot_launcher_python::{PythonBackend, PythonBackendConfig};

pub async fn run_doctor(config: &LauncherConfig) -> Result<()> {
    let mut all_ok = true;

    let docker_result = if config.backends.docker.enabled {
        match DockerBackend::new() {
            Ok(b) => b.probe().await,
            Err(e) => Err(e),
        }
    } else {
        Err(LauncherError::BackendUnavailable(
            "disabled in config".to_string(),
        ))
    };

    match &docker_result {
        Ok(()) => println!("[OK]  Docker backend: connected"),
        Err(e) => {
            println!("[FAIL] Docker backend: {e}");
            all_ok = false;
        }
    }

    let binary_result = if config.backends.binary.enabled {
        let b = BinaryBackend::new(BinaryBackendConfig::default());
        b.probe().await
    } else {
        Err(LauncherError::BackendUnavailable(
            "disabled in config".to_string(),
        ))
    };

    match binary_result {
        Ok(()) => println!("[OK]  Binary backend: available"),
        Err(e) => {
            println!("[FAIL] Binary backend: {e}");
            all_ok = false;
        }
    }

    let python_result = if config.backends.python.enabled {
        let b = PythonBackend::new(PythonBackendConfig::default());
        b.probe().await
    } else {
        Err(LauncherError::BackendUnavailable(
            "disabled in config".to_string(),
        ))
    };

    match python_result {
        Ok(()) => println!("[OK]  Python backend: available"),
        Err(e) => {
            println!("[FAIL] Python backend: {e}");
            all_ok = false;
        }
    }

    println!("[OK]  API: will bind to {}", config.launcher.api_bind);

    let data_root = &config.launcher.data_root;
    if data_root.exists() {
        let writable = std::fs::write(data_root.join(".write_test"), b"test")
            .and_then(|()| std::fs::remove_file(data_root.join(".write_test")))
            .is_ok();
        if writable {
            println!("[OK]  Data dir: {} (writable)", data_root.display());
        } else {
            println!("[FAIL] Data dir: {} (not writable)", data_root.display());
            all_ok = false;
        }
    } else {
        println!("[FAIL] Data dir: {} (does not exist)", data_root.display());
        all_ok = false;
    }

    let token_store_path = data_root.join("state").join("tokens.json");
    let token_store = TokenStore::load(token_store_path);
    let token_count = token_store.list().len();
    println!("[OK]  Tokens: {token_count} configured");

    if !all_ok {
        std::process::exit(1);
    }

    Ok(())
}
