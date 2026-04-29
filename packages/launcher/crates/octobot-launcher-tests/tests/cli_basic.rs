#![allow(clippy::unwrap_used, clippy::expect_used)]

use assert_cmd::Command;
use predicates::prelude::*;
use tempfile::TempDir;

#[test]
fn help_renders() {
    let mut cmd = Command::cargo_bin("octobot-launcher").unwrap();
    cmd.arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("instance"))
        .stdout(predicate::str::contains("service"))
        .stdout(predicate::str::contains("token"));
}

#[test]
fn version_subcommand() {
    let mut cmd = Command::cargo_bin("octobot-launcher").unwrap();
    let output = cmd.arg("version").output().unwrap();
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(!stdout.trim().is_empty());
}

#[test]
fn unknown_subcommand_exits_nonzero() {
    let mut cmd = Command::cargo_bin("octobot-launcher").unwrap();
    cmd.arg("foobarxyz").assert().failure();
}

#[test]
fn doctor_exits_nonzero_without_docker() {
    let dir = TempDir::new().unwrap();
    let config_path = dir.path().join("config.toml");
    std::fs::write(&config_path, "").unwrap();
    let output = Command::cargo_bin("octobot-launcher")
        .unwrap()
        .arg("--config")
        .arg(&config_path)
        .arg("doctor")
        .output()
        .unwrap();
    let combined = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr),
    );
    assert!(!combined.is_empty());
}

#[test]
fn instance_list_requires_daemon() {
    let dir = TempDir::new().unwrap();
    let config_path = dir.path().join("config.toml");
    std::fs::write(
        &config_path,
        format!("[launcher]\ndata_root = {:?}\napi_bind = \"127.0.0.1:19999\"", dir.path()),
    )
    .unwrap();
    let output = Command::cargo_bin("octobot-launcher")
        .unwrap()
        .arg("--config")
        .arg(&config_path)
        .arg("instance")
        .arg("list")
        .arg("--json")
        .output()
        .unwrap();
    assert!(!output.status.success(), "instance list should fail when daemon is not running");
}
