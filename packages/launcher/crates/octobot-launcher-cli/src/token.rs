use anyhow::{Context, Result};
use octobot_launcher_api::token_store::TokenStore;
use octobot_launcher_config::{LauncherConfig, STATE_DIR, TOKENS_FILENAME};

use crate::cli::{TokenArgs, TokenCommands};
use crate::print_qr;

pub fn handle_token(args: TokenArgs, config: &LauncherConfig) -> Result<()> {
    let store_path = config.launcher.data_root.join(STATE_DIR).join(TOKENS_FILENAME);
    let token_store = TokenStore::load(store_path);

    match args.command {
        TokenCommands::List => {
            let records = token_store.list();
            if records.is_empty() {
                println!("No tokens configured.");
                return Ok(());
            }
            println!(
                "{:<14} {:<20} {:<30} {:<24} {:<24} Revoked",
                "ID", "Label", "Scopes", "Created", "Expires"
            );
            println!("{}", "-".repeat(120));
            for r in &records {
                let scopes = r.scopes.join(",");
                let expires = r
                    .expires_at
                    .map_or_else(|| "never".to_string(), |t| t.to_rfc3339());
                println!(
                    "{:<14} {:<20} {:<30} {:<24} {:<24} {}",
                    r.id,
                    r.label,
                    scopes,
                    r.created_at.to_rfc3339(),
                    expires,
                    r.revoked,
                );
            }
            Ok(())
        }
        TokenCommands::Create {
            label,
            scope,
            expires_in,
        } => {
            let scopes = if scope.is_empty() {
                octobot_launcher_api::default_scopes()
            } else {
                scope
            };
            let expires_at = expires_in
                .as_deref()
                .map(parse_expires_in)
                .transpose()
                .context("parse --expires-in")?;
            let (_record, raw) = token_store.create(label, scopes, expires_at).context("create token")?;
            println!("Token created. Save this now — it will not be shown again:\n");
            println!("  {raw}\n");
            let pairing_url = format!(
                "octobot://pair?host={}&token={}",
                config.launcher.api_bind, raw
            );
            println!("QR code for mobile pairing:");
            print_qr(&pairing_url);
            println!("URL: {pairing_url}");
            Ok(())
        }
        TokenCommands::Revoke { id } => {
            if token_store.revoke(&id).context("revoke token")? {
                println!("Token {id} revoked.");
            } else {
                anyhow::bail!("token '{id}' not found");
            }
            Ok(())
        }
        TokenCommands::Rotate { id } => {
            let records = token_store.list();
            let existing = records
                .iter()
                .find(|r| r.id == id)
                .ok_or_else(|| anyhow::anyhow!("token '{id}' not found"))?
                .clone();
            token_store.revoke(&id).context("revoke token")?;
            let (_new_record, new_raw) = token_store.create(
                existing.label.clone(),
                existing.scopes.clone(),
                existing.expires_at,
            ).context("create token")?;
            println!("Token rotated. New token (save now — will not be shown again):\n");
            println!("  {new_raw}\n");
            Ok(())
        }
        TokenCommands::ShowPairing { id } => {
            let records = token_store.list();
            let found = records.iter().any(|r| r.id == id && !r.revoked);
            if !found {
                anyhow::bail!("token '{id}' not found or revoked");
            }
            let pairing_url = format!(
                "octobot://pair?host={}&token={}",
                config.launcher.api_bind, id
            );
            println!("Pairing URL (uses token ID — raw token not recoverable after creation):");
            println!("URL: {pairing_url}");
            print_qr(&pairing_url);
            Ok(())
        }
    }
}

fn parse_expires_in(s: &str) -> Result<chrono::DateTime<chrono::Utc>> {
    let (num_str, unit) = if let Some(n) = s.strip_suffix('d') {
        (n, "d")
    } else if let Some(n) = s.strip_suffix('h') {
        (n, "h")
    } else if let Some(n) = s.strip_suffix('m') {
        (n, "m")
    } else {
        anyhow::bail!("unknown duration format '{s}': use 30d, 7d, 24h, etc.")
    };

    let n: i64 = num_str
        .parse()
        .with_context(|| format!("parse number in '{s}'"))?;

    let duration = match unit {
        "d" => chrono::Duration::days(n),
        "h" => chrono::Duration::hours(n),
        "m" => chrono::Duration::minutes(n),
        _ => unreachable!(),
    };

    Ok(chrono::Utc::now() + duration)
}
