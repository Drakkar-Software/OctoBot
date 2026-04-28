use anyhow::{Context, Result};
use octobot_launcher_config::{InstanceRecord, LauncherConfig};

use crate::cli::{InstanceArgs, InstanceCommands};
use crate::client::{ApiClient, ApiResponse};
use crate::paths;
use crate::spinner::{with_spinner, with_streaming_spinner};

pub async fn handle_instance(args: InstanceArgs, config: &LauncherConfig, token: Option<String>) -> Result<()> {
    match args.command {
        InstanceCommands::List { json } => {
            let client = ApiClient::from_config(config, token);
            let resp = client.get(paths::INSTANCES).await?;
            if !resp.is_success() {
                let s = resp.status;
                anyhow::bail!("failed to list instances: HTTP {s}: {}", resp.text());
            }
            let records: Vec<InstanceRecord> = resp.json().context("parse instances")?;
            if json {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else {
                print_instances_table(&records);
            }
            Ok(())
        }
        InstanceCommands::Add { name, runtime, version, data_dir, binary_path, source_dir } => {
            let runtime_kind = parse_runtime(&runtime)?;
            let client = ApiClient::from_config(config, token);
            let mut body = serde_json::json!({
                "name": name,
                "runtime": runtime_kind,
                "version": version,
                "runtime_options": build_runtime_options(binary_path, source_dir),
            });
            if let Some(dir) = data_dir {
                body["data_dir"] = serde_json::json!(dir);
                body["config_dir"] = serde_json::json!(dir.join("config"));
            }
            let resp = client.post(paths::INSTANCES, body).await?;
            if resp.is_success() {
                let record: serde_json::Value = resp.json().context("parse response")?;
                let id = record["spec"]["id"].as_str().unwrap_or("unknown");
                println!("{id}");
                Ok(())
            } else {
                let s = resp.status;
                anyhow::bail!("failed to add instance: HTTP {s}: {}", resp.text())
            }
        }
        InstanceCommands::Remove { id } => {
            let client = ApiClient::from_config(config, token);
            let resp = client.delete(&paths::instance(&id)).await?;
            if resp.is_success() || resp.status == 204 {
                println!("Instance {id} removed.");
                Ok(())
            } else {
                let s = resp.status;
                anyhow::bail!("failed to remove instance: HTTP {s}: {}", resp.text())
            }
        }
        InstanceCommands::Start { id } => {
            let client = ApiClient::from_config(config, token);
            let (label_tx, label_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
            let record = with_streaming_spinner(
                "Starting...",
                label_rx,
                client.post_sse(&paths::instance_start(&id), serde_json::json!({}), move |step| {
                    let _ = label_tx.send(step.to_string());
                }),
            ).await?;
            print_sse_start_result(&record);
            Ok(())
        }
        InstanceCommands::Stop { id } => {
            let client = ApiClient::from_config(config, token);
            let resp = with_spinner(
                "Stopping...",
                client.post(&paths::instance_stop(&id), serde_json::json!({})),
            ).await?;
            check_status(resp, "stop instance")
        }
        InstanceCommands::StopAll => {
            let client = ApiClient::from_config(config, token.clone());
            let resp = client.get(paths::INSTANCES).await?;
            if !resp.is_success() {
                let s = resp.status;
                anyhow::bail!("failed to list instances: HTTP {s}: {}", resp.text());
            }
            let records: Vec<octobot_launcher_config::InstanceRecord> = resp.json().context("parse instances")?;
            if records.is_empty() {
                println!("No instances to stop.");
                return Ok(());
            }
            for record in &records {
                let id = record.spec.id.0.to_string();
                let name = &record.spec.name;
                let client2 = ApiClient::from_config(config, token.clone());
                let resp = with_spinner(
                    &format!("Stopping {name}..."),
                    client2.post(&paths::instance_stop(&id), serde_json::json!({})),
                ).await?;
                if resp.is_success() {
                    println!("{name}: stopped");
                } else {
                    let s = resp.status;
                    println!("{name}: error HTTP {s}: {}", resp.text());
                }
            }
            Ok(())
        }
        InstanceCommands::Restart { id } => {
            let client = ApiClient::from_config(config, token);
            let (label_tx, label_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
            with_streaming_spinner(
                "Restarting...",
                label_rx,
                client.post_sse(&paths::instance_restart(&id), serde_json::json!({}), move |step| {
                    let _ = label_tx.send(step.to_string());
                }),
            ).await?;
            println!("OK");
            Ok(())
        }
        InstanceCommands::Update { id, version } => {
            let client = ApiClient::from_config(config, token);
            let body = match version {
                Some(v) => serde_json::json!({ "version": v }),
                None => serde_json::json!({}),
            };
            let (label_tx, label_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
            with_streaming_spinner(
                "Updating...",
                label_rx,
                client.post_sse(&paths::instance_update(&id), body, move |step| {
                    let _ = label_tx.send(step.to_string());
                }),
            ).await?;
            println!("OK");
            Ok(())
        }
        InstanceCommands::Run { name, runtime, version, data_dir, binary_path, source_dir } => {
            let client = ApiClient::from_config(config, token);

            let resp = client.get(paths::INSTANCES).await?;
            if !resp.is_success() {
                let s = resp.status;
                anyhow::bail!("failed to list instances: HTTP {s}: {}", resp.text());
            }
            let records: Vec<InstanceRecord> = resp.json().context("parse instances")?;

            let id = if let Some(existing) = records.iter().find(|r| r.spec.name == name) {
                existing.spec.id.0.to_string()
            } else {
                let runtime_kind = parse_runtime(&runtime)?;
                let mut body = serde_json::json!({
                    "name": name,
                    "runtime": runtime_kind,
                    "version": version,
                    "runtime_options": build_runtime_options(binary_path, source_dir),
                });
                if let Some(dir) = data_dir {
                    body["data_dir"] = serde_json::json!(dir);
                    body["config_dir"] = serde_json::json!(dir.join("config"));
                }
                let resp = client.post(paths::INSTANCES, body).await?;
                if !resp.is_success() {
                    let s = resp.status;
                    anyhow::bail!("failed to create instance: HTTP {s}: {}", resp.text());
                }
                let record: serde_json::Value = resp.json().context("parse create response")?;
                let id = record["spec"]["id"].as_str().unwrap_or("unknown").to_string();
                println!("Created {id}");
                id
            };

            let (label_tx, label_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
            let record = with_streaming_spinner(
                "Starting...",
                label_rx,
                client.post_sse(&paths::instance_start(&id), serde_json::json!({}), move |step| {
                    let _ = label_tx.send(step.to_string());
                }),
            ).await?;
            print_sse_start_result(&record);
            Ok(())
        }
        InstanceCommands::Status { id } => {
            let client = ApiClient::from_config(config, token);
            let resp = client.get(&paths::instance_status(&id)).await?;
            let status: serde_json::Value = resp.json().context("parse status")?;
            println!("{}", serde_json::to_string_pretty(&status)?);
            Ok(())
        }
    }
}

fn build_runtime_options(binary_path: Option<std::path::PathBuf>, source_dir: Option<std::path::PathBuf>) -> serde_json::Value {
    let mut opts = serde_json::Map::new();
    if let Some(p) = binary_path {
        opts.insert("binary_path".to_string(), serde_json::json!(p));
    }
    if let Some(d) = source_dir {
        opts.insert("source_dir".to_string(), serde_json::json!(d));
    }
    serde_json::Value::Object(opts)
}

fn parse_runtime(s: &str) -> Result<octobot_launcher_core::RuntimeKind> {
    match s.to_lowercase().as_str() {
        "docker" => Ok(octobot_launcher_core::RuntimeKind::Docker),
        "binary" => Ok(octobot_launcher_core::RuntimeKind::Binary),
        "python" => Ok(octobot_launcher_core::RuntimeKind::Python),
        other => anyhow::bail!("unknown runtime '{other}': must be docker, binary, or python"),
    }
}

fn print_instances_table(records: &[InstanceRecord]) {
    if records.is_empty() {
        println!("No instances configured.");
        return;
    }
    println!(
        "{:<10} {:<20} {:<8} {:<10} {:<12} State",
        "ID", "Name", "Runtime", "Version", "Desired"
    );
    println!("{}", "-".repeat(80));
    for r in records {
        println!(
            "{:<10} {:<20} {:<8} {:<10} {:<12} {:?}",
            r.spec.id.short(),
            r.spec.name,
            format!("{:?}", r.spec.runtime),
            r.spec.version,
            format!("{:?}", r.desired_state),
            r.last_known_state,
        );
    }
}

fn check_status(resp: ApiResponse, action: &str) -> Result<()> {
    if resp.is_success() {
        println!("OK");
        Ok(())
    } else {
        let s = resp.status;
        anyhow::bail!("failed to {action}: HTTP {s}: {}", resp.text())
    }
}

fn print_sse_start_result(record: &serde_json::Value) {
    if record["spec"]["runtime"].as_str() == Some("Python") {
        if let Some(data_dir) = record["spec"]["data_dir"].as_str() {
            let log = std::path::Path::new(data_dir)
                .join("logs")
                .join("launcher-stdio.log");
            println!("OK (logs: {})", log.display());
            return;
        }
    }
    println!("OK");
}
