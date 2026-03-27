use std::sync::LazyLock;

use crate::enums::TimeFrames;

// ---------------------------------------------------------------------------
// From __init__.py
// ---------------------------------------------------------------------------

pub const PROJECT_NAME: &str = "OctoBot-Commons";
pub const VERSION: &str = "1.10.6";
pub const MARKET_SEPARATOR: &str = "/";
pub const SETTLEMENT_ASSET_SEPARATOR: &str = ":";
pub const OPTION_SEPARATOR: &str = "-";
pub const DICT_BULLET_TOKEN_STR: &str = "\n ";

// ---------------------------------------------------------------------------
// Time
// ---------------------------------------------------------------------------

pub const MSECONDS_TO_SECONDS: u64 = 1000;
pub const MINUTE_TO_SECONDS: u64 = 60;
pub const MSECONDS_TO_MINUTE: u64 = MSECONDS_TO_SECONDS * MINUTE_TO_SECONDS;
pub const HOURS_TO_SECONDS: u64 = MINUTE_TO_SECONDS * 60;
pub const HOURS_TO_MSECONDS: u64 = MSECONDS_TO_SECONDS * MINUTE_TO_SECONDS * MINUTE_TO_SECONDS;
pub const DAYS_TO_SECONDS: u64 = HOURS_TO_SECONDS * 24;

// ---------------------------------------------------------------------------
// Strings
// ---------------------------------------------------------------------------

pub const CONFIG_WILDCARD: &str = "*";
pub const CONFIG_SYMBOLS_WILDCARD: &[&str] = &["*"];
pub const PORTFOLIO_AVAILABLE: &str = "available";
pub const MARGIN_PORTFOLIO: &str = "margin";
pub const PORTFOLIO_TOTAL: &str = "total";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

pub const CONFIG_ENABLED_OPTION: &str = "enabled";
pub const CONFIG_DEBUG_OPTION: &str = "DEV-MODE";
pub const CONFIG_TIME_FRAME: &str = "time_frame";
pub const USER_FOLDER: &str = "user";
pub const CONFIG_FOLDER: &str = "config";
pub const CONFIG_FILE: &str = "config.json";
pub const SAFE_DUMP_SUFFIX: &str = ".back";
pub const DEFAULT_CONFIG_FILE: &str = "default_config.json";
pub const SCHEMA: &str = "schema";
pub const CONFIG_FILE_EXT: &str = ".json";
pub const CONFIG_REFRESH_RATE: &str = "refresh_rate_seconds";
pub const CONFIG_SAVED_HISTORICAL_TIMEFRAMES: &str = "saved_historical_timeframes";
pub const CONFIG_OPTIMIZER_ID: &str = "optimizer_id";
pub const CONFIG_BACKTESTING_ID: &str = "backtesting_id";
pub const CONFIG_CURRENT_LIVE_ID: &str = "current-live-id";
pub const DEFAULT_CURRENT_LIVE_ID: i64 = 1;

// Computed path constants
pub static DEFAULT_CONFIG_FILE_PATH: LazyLock<String> =
    LazyLock::new(|| format!("{CONFIG_FOLDER}/{DEFAULT_CONFIG_FILE}"));
pub static CONFIG_FILE_SCHEMA: LazyLock<String> =
    LazyLock::new(|| format!("{CONFIG_FOLDER}/config_{SCHEMA}.json"));

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

pub const PROFILES_FOLDER: &str = "profiles";
pub const PROFILE_CONFIG_FILE: &str = "profile.json";
pub const CONFIG_PROFILE: &str = "profile";
pub const CONFIG_BACKTESTING_PROFILE: &str = "backtesting_profile";
pub const DEFAULT_PROFILE: &str = "default";
pub const CONFIG_NAME: &str = "name";
pub const CONFIG_SLUG: &str = "slug";
pub const CONFIG_DESCRIPTION: &str = "description";
pub const CONFIG_AVATAR: &str = "avatar";
pub const CONFIG_ORIGIN_URL: &str = "origin_url";
pub const CONFIG_AUTO_UPDATE: &str = "auto_update";
pub const CONFIG_READ_ONLY: &str = "read_only";
pub const CONFIG_HIDDEN: &str = "hidden";
pub const CONFIG_IMPORTED: &str = "imported";
pub const CONFIG_EXTRA_BACKTESTING_TIME_FRAMES: &str = "extra_backtesting_time_frames";
pub const CONFIG_COMPLEXITY: &str = "complexity";
pub const CONFIG_RISK: &str = "risk";
pub const CONFIG_TYPE: &str = "type";
pub const PROFILE_CONFIG: &str = "config";
pub const CONFIG_ID: &str = "id";
pub const PROFILE_EXPORT_FORMAT: &str = "zip";
pub const IMPORTED_PROFILE_PREFIX: &str = "imported";
pub const USE_CURRENT_PROFILE: &str = "use_current_profile";

pub static USER_PROFILES_FOLDER: LazyLock<String> =
    LazyLock::new(|| format!("{USER_FOLDER}/{PROFILES_FOLDER}"));
pub static PROFILE_FILE_SCHEMA: LazyLock<String> =
    LazyLock::new(|| format!("{CONFIG_FOLDER}/profile_{SCHEMA}.json"));
pub static DEFAULT_PROFILE_FILE: LazyLock<String> =
    LazyLock::new(|| format!("{CONFIG_PROFILE}.json"));

// ---------------------------------------------------------------------------
// Crypto currencies
// ---------------------------------------------------------------------------

pub const CONFIG_CRYPTO_CURRENCIES: &str = "crypto-currencies";
pub const CONFIG_CRYPTO_CURRENCY: &str = "crypto-currency";
pub const CONFIG_CRYPTO_PAIRS: &str = "pairs";
pub const CONFIG_CRYPTO_QUOTE: &str = "quote";
pub const CONFIG_CRYPTO_ADD: &str = "add";
pub const TRADING_SYMBOL_REGEX: &str = r"([a-zA-Z]|\d){1,}/([a-zA-Z]|\d){1,}";

// ---------------------------------------------------------------------------
// Exchange
// ---------------------------------------------------------------------------

pub const CONFIG_EXCHANGES: &str = "exchanges";
pub const CONFIG_EXCHANGE_KEY: &str = "api-key";
pub const CONFIG_EXCHANGE_SECRET: &str = "api-secret";
pub const CONFIG_EXCHANGE_PASSWORD: &str = "api-password";
pub const CONFIG_EXCHANGE_UID: &str = "api-uid";
pub const CONFIG_EXCHANGE_ACCESS_TOKEN: &str = "access_token";
pub const CONFIG_EXCHANGE_TYPE: &str = "exchange-type";
pub const CONFIG_FORCE_AUTHENTICATION: &str = "force-authentication";
pub const CONFIG_CONTRACT_TYPE: &str = "contract-type";
pub const CONFIG_REQUIRED_EXTRA_TIMEFRAMES: &str = "required_extra_timeframes";
pub const CONFIG_EXCHANGE_SANDBOXED: &str = "sandboxed";
pub const CONFIG_EXCHANGE_FUTURE: &str = "future";
pub const CONFIG_EXCHANGE_MARGIN: &str = "margin";
pub const CONFIG_EXCHANGE_OPTION: &str = "option";
pub const CONFIG_EXCHANGE_SPOT: &str = "spot";
pub const CONFIG_EXCHANGE_REST_ONLY: &str = "rest_only";
pub const CONFIG_EXCHANGE_WEB_SOCKET: &str = "web-socket";
pub const CONFIG_EXCHANGE_SUB_ACCOUNT: &str = "sub_account";
pub const CONFIG_EXCHANGE_ENCRYPTED_VALUES: &[&str] = &[
    CONFIG_EXCHANGE_KEY,
    CONFIG_EXCHANGE_SECRET,
    CONFIG_EXCHANGE_PASSWORD,
];

// ---------------------------------------------------------------------------
// Trader
// ---------------------------------------------------------------------------

pub const CONFIG_TRADING: &str = "trading";
pub const CONFIG_TRADER: &str = "trader";
pub const CONFIG_LOAD_TRADE_HISTORY: &str = "load-trade-history";
pub const CONFIG_TRADER_RISK: &str = "risk";
pub const CONFIG_TRADER_PAUSED: &str = "paused";
pub const CONFIG_TRADER_ALLOW_ARTIFICIAL_ORDERS: &str = "allow-artificial-orders";
pub const CONFIG_TRADER_RISK_MIN: f64 = 0.05;
pub const CONFIG_TRADER_RISK_MAX: f64 = 1.0;
pub const CONFIG_TRADER_REFERENCE_MARKET: &str = "reference-market";
pub const DEFAULT_STORAGE_TRADING_MODE: &str = "default";

// ---------------------------------------------------------------------------
// Simulator
// ---------------------------------------------------------------------------

pub const CONFIG_SIMULATOR: &str = "trader-simulator";
pub const CONFIG_STARTING_PORTFOLIO: &str = "starting-portfolio";
pub const SIMULATOR_CURRENT_PORTFOLIO: &str = "simulator_current_portfolio";
pub const CONFIG_SIMULATOR_FEES: &str = "fees";
pub const CONFIG_SIMULATOR_FEES_MAKER: &str = "maker";
pub const CONFIG_SIMULATOR_FEES_TAKER: &str = "taker";
pub const CONFIG_SIMULATOR_FEES_WITHDRAW: &str = "withdraw";

// ---------------------------------------------------------------------------
// Optimization campaigns
// ---------------------------------------------------------------------------

pub const DEFAULT_CAMPAIGN: &str = "default_campaign";

// ---------------------------------------------------------------------------
// Optimizer
// ---------------------------------------------------------------------------

pub const OPTIMIZER_RUNS_FOLDER: &str = "optimizer";

// ---------------------------------------------------------------------------
// OS
// ---------------------------------------------------------------------------

pub const PLATFORM_DATA_SEPARATOR: &str = ":";
pub const BYTES_BY_GB: u64 = 1_000_000_000;

// ---------------------------------------------------------------------------
// Evaluators
// ---------------------------------------------------------------------------

pub const MIN_EVAL_TIME_FRAME: TimeFrames = TimeFrames::OneMinute;
pub const INIT_EVAL_NOTE: i64 = 0;
pub const START_PENDING_EVAL_NOTE: &str = "0";

// ---------------------------------------------------------------------------
// Tentacles
// ---------------------------------------------------------------------------

pub const TENTACLE_DEFAULT_CONFIG: &str = "default_config";
pub const CONFIG_TENTACLES_FILE: &str = "tentacles_config.json";
pub const EVALUATOR_PRIORITY: &str = "priority";
pub const DEFAULT_EVALUATOR_PRIORITY: i64 = 0;
pub const CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT: &str = "required_candles_count";
pub const CONFIG_HISTORICAL_CONFIGURATION: &str = "_historical_configuration";
pub const NESTED_TENTACLE_CONFIG: &str = "nested_tentacle_configuration";
pub const CONFIG_ACTIVATION_TOPICS: &str = "activation method";
pub const CONFIG_TRIGGER_TIMEFRAMES: &str = "Trigger_timeframes";
pub const CONFIG_EMIT_TRADING_SIGNALS: &str = "emit_trading_signals";
pub const CONFIG_TRADING_SIGNALS_STRATEGY: &str = "trading_strategy";
pub const ALLOW_DEFAULT_CONFIG: &str = "allow_default_config";

// ---------------------------------------------------------------------------
// Terms of service
// ---------------------------------------------------------------------------

pub const CONFIG_ACCEPTED_TERMS: &str = "accepted_terms";

// ---------------------------------------------------------------------------
// Distribution
// ---------------------------------------------------------------------------

pub const DEFAULT_DISTRIBUTION: &str = "default";
pub const CONFIG_DISTRIBUTION: &str = "distribution";

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

pub const CONFIG_METRICS: &str = "metrics";
pub const CONFIG_METRICS_BOT_ID: &str = "metrics-bot-id";
pub const TIMER_BEFORE_METRICS_REGISTRATION_SECONDS: u64 = 600;
pub const METRICS_ROUTE_GEN_BOT_ID: &str = "gen-bot-id";
pub const METRICS_ROUTE: &str = "metrics";
pub const COMMUNITY_TOPS_COUNT: u64 = 1000;

pub static METRICS_ROUTE_COMMUNITY: LazyLock<String> =
    LazyLock::new(|| format!("{METRICS_ROUTE}/community"));
pub static METRICS_ROUTE_UPTIME: LazyLock<String> =
    LazyLock::new(|| format!("{METRICS_ROUTE}/uptime"));
pub static METRICS_ROUTE_REGISTER: LazyLock<String> =
    LazyLock::new(|| format!("{METRICS_ROUTE}/register"));

// ---------------------------------------------------------------------------
// Default values
// ---------------------------------------------------------------------------

pub const DEFAULT_API_KEY: &str = "your-api-key-here";
pub const DEFAULT_API_SECRET: &str = "your-api-secret-here";
pub const DEFAULT_API_PASSWORD: &str = "your-api-password-here";
pub const DEFAULT_EXCHANGE_TYPE: &str = CONFIG_EXCHANGE_SPOT;
pub const NO_KEY_VALUE: &str = "NO KEY";
pub const DEFAULT_CONFIG_VALUES: &[&str] = &[
    DEFAULT_API_KEY,
    DEFAULT_API_SECRET,
    DEFAULT_API_PASSWORD,
    "NOKEY",
    NO_KEY_VALUE,
    "Empty",
];

pub fn is_default_config_value(val: &str) -> bool {
    DEFAULT_CONFIG_VALUES.contains(&val)
}

// ---------------------------------------------------------------------------
// Cache
// ---------------------------------------------------------------------------

pub const CACHE_FOLDER: &str = "cache";
pub const CACHE_FILE: &str = "cache.json";
pub const CACHE_HASH_SIZE: usize = 15;
pub const CACHE_RELATED_DATA_SEPARATOR: &str = "##";
pub const LOCAL_BOT_DATA: &str = "local_bot_data";
pub const DO_NOT_CACHE: &str = "do_not_cache";
pub const DO_NOT_OVERRIDE_CACHE: &str = "do_not_override_cache";
pub const DEFAULT_IGNORED_VALUE: i64 = -1;
pub const UNPROVIDED_CACHE_IDENTIFIER: &str = "_unprovided";

// ---------------------------------------------------------------------------
// Async settings
// ---------------------------------------------------------------------------

pub const DEFAULT_FUTURE_TIMEOUT: u64 = 120;

// ---------------------------------------------------------------------------
// Github urls
// ---------------------------------------------------------------------------

pub const GITHUB_RAW_CONTENT_URL: &str = "https://raw.githubusercontent.com";
pub const GITHUB_API_CONTENT_URL: &str = "https://api.github.com";
pub const GITHUB_BASE_URL: &str = "https://github.com";
pub const GITHUB_ORGANISATION: &str = "Drakkar-Software";

// ---------------------------------------------------------------------------
// External resources
// ---------------------------------------------------------------------------

pub const EXTERNAL_RESOURCE_URL: &str = "https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/external_resources.json";

// ---------------------------------------------------------------------------
// Run databases
// ---------------------------------------------------------------------------

pub const DATA_FOLDER: &str = "data";
pub const DB_SEPARATOR: &str = "_";
pub const TINYDB_EXT: &str = ".json";
pub const MAX_BACKTESTING_RUNS: u64 = 500_000;
pub const MAX_OPTIMIZER_RUNS: u64 = 50_000;

// ---------------------------------------------------------------------------
// DSL interpreter
// ---------------------------------------------------------------------------

pub const BASE_OPERATORS_LIBRARY: &str = "base";
pub const CONTEXTUAL_OPERATORS_LIBRARY: &str = "contextual";
pub const UNRESOLVED_PARAMETER_PLACEHOLDER: &str = "UNRESOLVED_PARAMETER";

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

pub const EXCEPTION_DESC: &str = "exception_desc";
pub const IS_EXCEPTION_DESC: &str = "is_exception_desc";

// ---------------------------------------------------------------------------
// Coins
// ---------------------------------------------------------------------------

pub const USD_LIKE_COINS: &[&str] = &[
    "USDT", "USDC", "TUSD", "USDE", "USDS", "BUSD", "DAI", "USD", "USDD", "USDP", "GUSD",
    "LUSD", "FDUSD",
];
pub const DEFAULT_REFERENCE_MARKET: &str = "USDT";
pub const USUAL_REFERENCE_MARKET_USD_LIKE_COINS: &[&str] = &["USDT", "USDC"];
pub const FIAT_NON_USD_LIKE_COINS: &[&str] = &["EUR", "GBP", "TRY", "BRL", "ARS"];

pub static USD_LIKE_AND_FIAT_COINS: LazyLock<Vec<&'static str>> = LazyLock::new(|| {
    let mut v = USD_LIKE_COINS.to_vec();
    v.extend_from_slice(FIAT_NON_USD_LIKE_COINS);
    v
});

// ---------------------------------------------------------------------------
// SSL
// ---------------------------------------------------------------------------

pub const KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL: &str =
    "https://tentacles.octobot.online/officials/packages/full/base/1.0.9/metadata.yaml";

// ---------------------------------------------------------------------------
// Environment-variable constants
// ---------------------------------------------------------------------------

pub fn parse_boolean_environment_var(env_key: &str, default_value: &str) -> bool {
    std::env::var(env_key)
        .unwrap_or_else(|_| default_value.to_string())
        .to_lowercase()
        == "true"
}

pub static PROFILE_REFRESH_HOURS_INTERVAL: LazyLock<i64> = LazyLock::new(|| {
    std::env::var("PROFILE_REFRESH_HOURS_INTERVAL")
        .unwrap_or_else(|_| "24".to_string())
        .parse()
        .unwrap_or(24)
});

pub static CLOCK_REFRESH_HOURS_INTERVAL: LazyLock<i64> = LazyLock::new(|| {
    std::env::var("CLOCK_REFRESH_HOURS_INTERVAL")
        .unwrap_or_else(|_| "4".to_string())
        .parse()
        .unwrap_or(4)
});

pub static RESOURCES_WATCHER_MINUTES_INTERVAL: LazyLock<f64> = LazyLock::new(|| {
    std::env::var("RESOURCES_WATCHER_MINUTES_INTERVAL")
        .unwrap_or_else(|_| "10".to_string())
        .parse()
        .unwrap_or(10.0)
});

pub static TIMER_BETWEEN_METRICS_UPTIME_UPDATE: LazyLock<f64> = LazyLock::new(|| {
    std::env::var("TIMER_BETWEEN_METRICS_UPTIME_UPDATE")
        .unwrap_or_else(|_| (3600.0 * 4.0).to_string())
        .parse()
        .unwrap_or(3600.0 * 4.0)
});

pub static METRICS_URL: LazyLock<String> = LazyLock::new(|| {
    std::env::var("METRICS_OCTOBOT_ONLINE_URL")
        .unwrap_or_else(|_| "https://metrics.octobot.online/".to_string())
});

pub static FORCE_BACKTESTING_LOGS: LazyLock<bool> =
    LazyLock::new(|| parse_boolean_environment_var("FORCE_BACKTESTING_LOGS", "false"));

pub static ENABLE_CERTIFI_SSL_CERTIFICATES: LazyLock<bool> =
    LazyLock::new(|| parse_boolean_environment_var("ENABLE_CERTIFI_SSL_CERTIFICATES", "true"));

pub static IS_DEV_MODE_ENABLED: LazyLock<bool> =
    LazyLock::new(|| parse_boolean_environment_var(CONFIG_DEBUG_OPTION, "False"));

pub static USE_MINIMAL_LIBS: LazyLock<bool> =
    LazyLock::new(|| parse_boolean_environment_var("USE_MINIMAL_LIBS", "false"));
