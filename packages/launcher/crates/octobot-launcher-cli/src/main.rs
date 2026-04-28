#![deny(clippy::unwrap_used, clippy::expect_used)]

mod cli;
mod client;
mod doctor;
mod instance;
mod paths;
mod service;
mod spinner;
mod supervisor;
mod token;
mod update;

use anyhow::{Context, Result};
use clap::Parser;
use octobot_launcher_config::load_config;

use cli::{Cli, Commands};

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    tracing_subscriber::fmt()
        .with_env_filter(&cli.log_level)
        .init();

    let config = load_config(cli.config.as_deref()).context("load config")?;

    let token = cli.token.or_else(|| {
        let candidates = [
            config.launcher.data_root.join(octobot_launcher_config::BOOTSTRAP_TOKEN_FILENAME),
            octobot_launcher_config::default_data_root(true).join(octobot_launcher_config::BOOTSTRAP_TOKEN_FILENAME),
        ];
        candidates.iter()
            .filter_map(|p| std::fs::read_to_string(p).ok())
            .map(|s| s.trim().to_string())
            .next()
    });

    match cli.command {
        Commands::Service(args) => service::handle_service(args, &config).await,
        Commands::Instance(args) => instance::handle_instance(args, &config, token).await,
        Commands::Token(args) => token::handle_token(args, &config),
        Commands::Update(args) => update::handle_update(args, &config, token).await,
        Commands::Doctor => doctor::run_doctor(&config).await,
        Commands::Version => {
            println!("{}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
    }
}

pub fn print_qr(content: &str) {
    use qrcode::QrCode;
    use qrcode::render::unicode;
    match QrCode::new(content.as_bytes()) {
        Ok(code) => {
            let image = code
                .render::<unicode::Dense1x2>()
                .dark_color(unicode::Dense1x2::Dark)
                .light_color(unicode::Dense1x2::Light)
                .build();
            println!("{image}");
        }
        Err(e) => {
            tracing::warn!("failed to render QR code: {e}");
        }
    }
}

pub fn write_bootstrap_token(path: &std::path::Path, raw: &str) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).context("create bootstrap token parent dir")?;
    }
    std::fs::write(path, raw).context("write bootstrap token")?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let perms = std::fs::Permissions::from_mode(0o644);
        std::fs::set_permissions(path, perms).context("chmod bootstrap token")?;
    }
    Ok(())
}
