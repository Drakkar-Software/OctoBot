#![allow(clippy::unwrap_used, clippy::expect_used)]

use assert_cmd::Command;
use predicates::prelude::*;

fn cmd() -> Command {
    Command::cargo_bin("octobot-launcher").unwrap()
}

mod clap {
    use super::*;

    #[test]
    fn help_renders() {
        cmd().arg("--help").assert().success();
    }

    #[test]
    fn version_subcommand() {
        let output = cmd().arg("version").assert().success();
        let stdout = String::from_utf8(output.get_output().stdout.clone()).unwrap();
        assert!(!stdout.trim().is_empty(), "version should print something");
    }

    #[test]
    fn unknown_subcommand_exits_2() {
        cmd()
            .arg("totally-unknown-subcommand")
            .assert()
            .failure()
            .code(2);
    }

    #[test]
    fn missing_required_arg_instance_add() {
        cmd()
            .args(["instance", "add", "--runtime", "docker"])
            .assert()
            .failure()
            .code(2)
            .stderr(predicate::str::contains("--name"));
    }
}

mod token_tests {
    use super::*;
    use tempfile::TempDir;

    fn config_toml(dir: &TempDir) -> std::path::PathBuf {
        let data_root = dir.path().to_str().unwrap().replace('\\', "/");
        let config = format!(
            "[launcher]\napi_bind = \"127.0.0.1:7531\"\nlog_level = \"info\"\ndata_root = \"{data_root}\"\n\
            [update]\nchannel = \"stable\"\nauto_update_launcher = true\nauto_update_instances = false\n\
            check_interval_hours = 6\nmanifest_url = \"https://updates.drakkar.software/octobot-launcher/v1/manifest.json\"\n\
            [backends.docker]\nenabled = false\nsocket = \"/var/run/docker.sock\"\n\
            [backends.binary]\nenabled = false\n\
            [backends.python]\nenabled = false\ndefault_python_dist = \"auto\"\n"
        );
        let path = dir.path().join("config.toml");
        std::fs::write(&path, config).unwrap();
        path
    }

    #[test]
    fn create_prints_raw_once() {
        let dir = TempDir::new().unwrap();
        std::fs::create_dir_all(dir.path().join("state")).unwrap();
        let config_path = config_toml(&dir);
        let output = cmd()
            .args([
                "--config",
                config_path.to_str().unwrap(),
                "token",
                "create",
                "--label",
                "test-token",
            ])
            .assert()
            .success();
        let stdout = String::from_utf8(output.get_output().stdout.clone()).unwrap();
        assert!(
            stdout.contains("oblch_"),
            "expected oblch_ prefix in output, got: {stdout}"
        );
    }
}

mod instance_tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;
    use tempfile::TempDir;

    use octobot_launcher_api::{ApiServer, ApiState, ListenerConfig};
    use octobot_launcher_api::lockout::Lockout;
    use octobot_launcher_api::token_store::TokenStore;
    use octobot_launcher_config::Store;
    use octobot_launcher_core::backend::Backend;
    use octobot_launcher_core::backend::mock::MockBackend;

    struct TestServer {
        port: u16,
        token: String,
        _dir: TempDir,
    }

    fn start_test_server() -> TestServer {
        let dir = TempDir::new().unwrap();
        let store = Arc::new(Store::new(dir.path().to_path_buf()).unwrap());
        let token_store = Arc::new(TokenStore::load(dir.path().join("tokens.json")));
        let (_, raw) = token_store.create("admin".into(), vec!["*".to_string()], None).unwrap();
        let lockout = Arc::new(Lockout::new());

        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        drop(listener);

        let backends: Arc<Vec<Box<dyn Backend>>> = Arc::new(vec![
            Box::new(MockBackend::default()),
        ]);
        let state = ApiState { store, token_store, lockout, backends };
        let server_config = ListenerConfig {
            tcp_bind: format!("127.0.0.1:{port}").parse().unwrap(),
            unix_socket_path: None,
        };
        let api_server = ApiServer::new(state, server_config);

        thread::spawn(move || {
            tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap()
                .block_on(async { let _ = api_server.serve().await; });
        });

        thread::sleep(std::time::Duration::from_millis(100));
        TestServer { port, token: raw, _dir: dir }
    }

    fn config_toml(dir: &TempDir, port: u16) -> std::path::PathBuf {
        let data_root = dir.path().to_str().unwrap().replace('\\', "/");
        let config = format!(
            "[launcher]\napi_bind = \"127.0.0.1:{port}\"\nlog_level = \"info\"\ndata_root = \"{data_root}\"\n\
            [update]\nchannel = \"stable\"\nauto_update_launcher = true\nauto_update_instances = false\n\
            check_interval_hours = 6\nmanifest_url = \"https://updates.drakkar.software/octobot-launcher/v1/manifest.json\"\n\
            [backends.docker]\nenabled = false\nsocket = \"/var/run/docker.sock\"\n\
            [backends.binary]\nenabled = false\n\
            [backends.python]\nenabled = false\ndefault_python_dist = \"auto\"\n"
        );
        let path = dir.path().join("config.toml");
        std::fs::write(&path, config).unwrap();
        path
    }

    #[test]
    fn add_then_list_json_format() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        let add_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "add", "--name", "test-bot", "--runtime", "docker"])
            .assert().success();
        let id = String::from_utf8(add_out.get_output().stdout.clone()).unwrap();
        assert!(!id.trim().is_empty(), "add should print instance id");

        let list_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "list", "--json"])
            .assert().success();
        let stdout = String::from_utf8(list_out.get_output().stdout.clone()).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&stdout)
            .unwrap_or_else(|e| panic!("not valid JSON: {e}\noutput: {stdout}"));
        let arr = parsed.as_array().expect("expected JSON array");
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["spec"]["name"], "test-bot");
    }

    #[test]
    fn add_then_start_returns_ok() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        let add_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "add", "--name", "bot", "--runtime", "binary"])
            .assert().success();
        let id = String::from_utf8(add_out.get_output().stdout.clone()).unwrap();
        let id = id.trim();

        cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "start", id])
            .assert().success();
    }

    #[test]
    fn add_then_remove_then_list_empty() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        let add_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "add", "--name", "bot", "--runtime", "binary"])
            .assert().success();
        let id = String::from_utf8(add_out.get_output().stdout.clone()).unwrap();
        let id = id.trim();

        cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "remove", id])
            .assert().success();

        let list_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "list", "--json"])
            .assert().success();
        let stdout = String::from_utf8(list_out.get_output().stdout.clone()).unwrap();
        let arr: Vec<serde_json::Value> = serde_json::from_str(&stdout).unwrap();
        assert!(arr.is_empty(), "list should be empty after remove");
    }

    #[test]
    fn missing_token_returns_error() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "instance", "list"])
            .assert()
            .failure()
            .stderr(predicate::str::contains("401"));
    }

    #[test]
    fn stop_all_no_instances_prints_message() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        let out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "stop-all"])
            .assert().success();
        let stdout = String::from_utf8(out.get_output().stdout.clone()).unwrap();
        assert!(stdout.contains("No instances"), "expected no-instances message, got: {stdout}");
    }

    #[test]
    fn stop_all_stops_all_running_instances() {
        let srv = start_test_server();
        let cfg_dir = TempDir::new().unwrap();
        let config_path = config_toml(&cfg_dir, srv.port);

        for name in &["bot-a", "bot-b"] {
            let add_out = cmd()
                .args(["--config", config_path.to_str().unwrap(),
                       "--token", &srv.token,
                       "instance", "add", "--name", name, "--runtime", "binary"])
                .assert().success();
            let id = String::from_utf8(add_out.get_output().stdout.clone()).unwrap();
            let id = id.trim();
            cmd()
                .args(["--config", config_path.to_str().unwrap(),
                       "--token", &srv.token,
                       "instance", "start", id])
                .assert().success();
        }

        let stop_out = cmd()
            .args(["--config", config_path.to_str().unwrap(),
                   "--token", &srv.token,
                   "instance", "stop-all"])
            .assert().success();
        let stdout = String::from_utf8(stop_out.get_output().stdout.clone()).unwrap();
        assert!(stdout.contains("bot-a"), "expected bot-a in output: {stdout}");
        assert!(stdout.contains("bot-b"), "expected bot-b in output: {stdout}");
        assert!(stdout.contains("stopped"), "expected 'stopped' in output: {stdout}");
    }
}

mod doctor_tests {
    use super::*;
    use tempfile::TempDir;

    fn config_toml(dir: &TempDir) -> std::path::PathBuf {
        let data_root = dir.path().to_str().unwrap().replace('\\', "/");
        let config = format!(
            "[launcher]\napi_bind = \"127.0.0.1:7531\"\nlog_level = \"info\"\ndata_root = \"{data_root}\"\n\
            [update]\nchannel = \"stable\"\nauto_update_launcher = true\nauto_update_instances = false\n\
            check_interval_hours = 6\nmanifest_url = \"https://updates.drakkar.software/octobot-launcher/v1/manifest.json\"\n\
            [backends.docker]\nenabled = true\nsocket = \"/var/run/docker.sock\"\n\
            [backends.binary]\nenabled = true\n\
            [backends.python]\nenabled = true\ndefault_python_dist = \"auto\"\n"
        );
        let path = dir.path().join("config.toml");
        std::fs::write(&path, config).unwrap();
        path
    }

    #[test]
    fn reports_each_backend() {
        let dir = TempDir::new().unwrap();
        let config_path = config_toml(&dir);

        let output = cmd()
            .args(["--config", config_path.to_str().unwrap(), "doctor"])
            .output()
            .unwrap();

        let stdout = String::from_utf8(output.stdout.clone()).unwrap();
        assert!(
            stdout.contains("Docker"),
            "expected Docker in doctor output\n{stdout}"
        );
        assert!(
            stdout.contains("Binary"),
            "expected Binary in doctor output\n{stdout}"
        );
        assert!(
            stdout.contains("Python"),
            "expected Python in doctor output\n{stdout}"
        );
    }

    #[test]
    fn nonzero_exit_on_failure() {
        let dir = TempDir::new().unwrap();
        let config_path = config_toml(&dir);

        let output = cmd()
            .args(["--config", config_path.to_str().unwrap(), "doctor"])
            .output()
            .unwrap();

        if !output.status.success() {
            return;
        }

        let stdout = String::from_utf8(output.stdout.clone()).unwrap();
        if stdout.contains("[FAIL]") {
            panic!("doctor reported failures but exited 0\n{stdout}");
        }
    }
}
