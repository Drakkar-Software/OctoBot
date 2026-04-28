use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(name = "octobot-launcher", version, about = "OctoBot instance manager")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,

    #[arg(long, global = true, default_value = "info")]
    pub log_level: String,

    #[arg(long, global = true)]
    pub config: Option<PathBuf>,

    #[arg(long, global = true, env = "OCTOBOT_LAUNCHER_TOKEN")]
    pub token: Option<String>,
}

#[derive(Debug, Subcommand)]
pub enum Commands {
    Service(ServiceArgs),
    Instance(InstanceArgs),
    Token(TokenArgs),
    Update(UpdateArgs),
    Doctor,
    Version,
}

#[derive(Debug, Args)]
pub struct ServiceArgs {
    #[command(subcommand)]
    pub command: ServiceCommands,
}

#[derive(Debug, Subcommand)]
pub enum ServiceCommands {
    Install {
        #[arg(long)]
        user: bool,
        #[arg(long)]
        system: bool,
    },
    Uninstall,
    Start,
    Stop,
    Status,
    #[command(hide = true)]
    Run,
}

#[derive(Debug, Args)]
pub struct InstanceArgs {
    #[command(subcommand)]
    pub command: InstanceCommands,
}

#[derive(Debug, Subcommand)]
pub enum InstanceCommands {
    List {
        #[arg(long)]
        json: bool,
    },
    Add {
        #[arg(long)]
        name: String,
        #[arg(long)]
        runtime: String,
        #[arg(long, default_value = "latest")]
        version: String,
        #[arg(long)]
        data_dir: Option<PathBuf>,
        #[arg(long)]
        binary_path: Option<PathBuf>,
        #[arg(long)]
        source_dir: Option<PathBuf>,
    },
    Run {
        #[arg(long)]
        name: String,
        #[arg(long)]
        runtime: String,
        #[arg(long, default_value = "latest")]
        version: String,
        #[arg(long)]
        data_dir: Option<PathBuf>,
        #[arg(long)]
        binary_path: Option<PathBuf>,
        #[arg(long)]
        source_dir: Option<PathBuf>,
    },
    Remove {
        id: String,
    },
    Start {
        id: String,
    },
    Stop {
        id: String,
    },
    StopAll,
    Restart {
        id: String,
    },
    Update {
        id: String,
        #[arg(long)]
        version: Option<String>,
    },
    Status {
        id: String,
    },
}

#[derive(Debug, Args)]
pub struct TokenArgs {
    #[command(subcommand)]
    pub command: TokenCommands,
}

#[derive(Debug, Subcommand)]
pub enum TokenCommands {
    List,
    Create {
        #[arg(long)]
        label: String,
        #[arg(long, value_delimiter = ',')]
        scope: Vec<String>,
        #[arg(long)]
        expires_in: Option<String>,
    },
    Revoke {
        id: String,
    },
    Rotate {
        id: String,
    },
    ShowPairing {
        id: String,
    },
}

#[derive(Debug, Args)]
pub struct UpdateArgs {
    #[command(subcommand)]
    pub command: UpdateCommands,
}

#[derive(Debug, Subcommand)]
pub enum UpdateCommands {
    Check,
    Apply,
    SetChannel { channel: String },
}
