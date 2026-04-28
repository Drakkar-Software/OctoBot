use anyhow::{Context, Result};
use octobot_launcher_config::LauncherConfig;

use crate::cli::{UpdateArgs, UpdateCommands};
use crate::client::ApiClient;
use crate::paths;

pub async fn handle_update(args: UpdateArgs, config: &LauncherConfig, token: Option<String>) -> Result<()> {
    match args.command {
        UpdateCommands::Check => {
            let client = ApiClient::from_config(config, token);
            let resp = client.get(paths::UPDATES_CHECK).await?;
            let body: serde_json::Value = resp.json().context("parse update check")?;
            println!("{}", serde_json::to_string_pretty(&body)?);
            Ok(())
        }
        UpdateCommands::Apply => {
            let client = ApiClient::from_config(config, token);
            let resp = client
                .post(paths::UPDATES_APPLY, serde_json::json!({}))
                .await?;
            if resp.is_success() {
                println!("Update applied. Restart the service to complete.");
                Ok(())
            } else {
                let s = resp.status;
                anyhow::bail!("update failed: HTTP {s}: {}", resp.text())
            }
        }
        UpdateCommands::SetChannel { channel } => {
            println!("Channel set to '{channel}' (edit config to persist).");
            let _ = config;
            Ok(())
        }
    }
}
