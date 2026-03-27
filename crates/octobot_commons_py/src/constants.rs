use pyo3::prelude::*;

use octobot_commons::constants;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // From __init__.py
    m.add("PROJECT_NAME", constants::PROJECT_NAME)?;
    m.add("VERSION", constants::VERSION)?;
    m.add("MARKET_SEPARATOR", constants::MARKET_SEPARATOR)?;
    m.add("SETTLEMENT_ASSET_SEPARATOR", constants::SETTLEMENT_ASSET_SEPARATOR)?;
    m.add("OPTION_SEPARATOR", constants::OPTION_SEPARATOR)?;
    m.add("DICT_BULLET_TOKEN_STR", constants::DICT_BULLET_TOKEN_STR)?;

    // Time
    m.add("MSECONDS_TO_SECONDS", constants::MSECONDS_TO_SECONDS)?;
    m.add("MINUTE_TO_SECONDS", constants::MINUTE_TO_SECONDS)?;
    m.add("MSECONDS_TO_MINUTE", constants::MSECONDS_TO_MINUTE)?;
    m.add("HOURS_TO_SECONDS", constants::HOURS_TO_SECONDS)?;
    m.add("HOURS_TO_MSECONDS", constants::HOURS_TO_MSECONDS)?;
    m.add("DAYS_TO_SECONDS", constants::DAYS_TO_SECONDS)?;

    // Strings
    m.add("CONFIG_WILDCARD", constants::CONFIG_WILDCARD)?;
    m.add("CONFIG_SYMBOLS_WILDCARD", constants::CONFIG_SYMBOLS_WILDCARD.to_vec())?;
    m.add("PORTFOLIO_AVAILABLE", constants::PORTFOLIO_AVAILABLE)?;
    m.add("MARGIN_PORTFOLIO", constants::MARGIN_PORTFOLIO)?;
    m.add("PORTFOLIO_TOTAL", constants::PORTFOLIO_TOTAL)?;

    // Config
    m.add("CONFIG_ENABLED_OPTION", constants::CONFIG_ENABLED_OPTION)?;
    m.add("CONFIG_DEBUG_OPTION", constants::CONFIG_DEBUG_OPTION)?;
    m.add("CONFIG_TIME_FRAME", constants::CONFIG_TIME_FRAME)?;
    m.add("USER_FOLDER", constants::USER_FOLDER)?;
    m.add("CONFIG_FOLDER", constants::CONFIG_FOLDER)?;
    m.add("CONFIG_FILE", constants::CONFIG_FILE)?;
    m.add("SAFE_DUMP_SUFFIX", constants::SAFE_DUMP_SUFFIX)?;
    m.add("DEFAULT_CONFIG_FILE", constants::DEFAULT_CONFIG_FILE)?;
    m.add("SCHEMA", constants::SCHEMA)?;
    m.add("CONFIG_FILE_EXT", constants::CONFIG_FILE_EXT)?;
    m.add("CONFIG_REFRESH_RATE", constants::CONFIG_REFRESH_RATE)?;
    m.add("CONFIG_SAVED_HISTORICAL_TIMEFRAMES", constants::CONFIG_SAVED_HISTORICAL_TIMEFRAMES)?;
    m.add("CONFIG_OPTIMIZER_ID", constants::CONFIG_OPTIMIZER_ID)?;
    m.add("CONFIG_BACKTESTING_ID", constants::CONFIG_BACKTESTING_ID)?;
    m.add("CONFIG_CURRENT_LIVE_ID", constants::CONFIG_CURRENT_LIVE_ID)?;
    m.add("DEFAULT_CURRENT_LIVE_ID", constants::DEFAULT_CURRENT_LIVE_ID)?;
    m.add("DEFAULT_CONFIG_FILE_PATH", constants::DEFAULT_CONFIG_FILE_PATH.as_str())?;
    m.add("CONFIG_FILE_SCHEMA", constants::CONFIG_FILE_SCHEMA.as_str())?;

    // Profiles
    m.add("PROFILES_FOLDER", constants::PROFILES_FOLDER)?;
    m.add("PROFILE_CONFIG_FILE", constants::PROFILE_CONFIG_FILE)?;
    m.add("CONFIG_PROFILE", constants::CONFIG_PROFILE)?;
    m.add("CONFIG_BACKTESTING_PROFILE", constants::CONFIG_BACKTESTING_PROFILE)?;
    m.add("DEFAULT_PROFILE", constants::DEFAULT_PROFILE)?;
    m.add("CONFIG_NAME", constants::CONFIG_NAME)?;
    m.add("CONFIG_SLUG", constants::CONFIG_SLUG)?;
    m.add("CONFIG_DESCRIPTION", constants::CONFIG_DESCRIPTION)?;
    m.add("CONFIG_AVATAR", constants::CONFIG_AVATAR)?;
    m.add("CONFIG_ORIGIN_URL", constants::CONFIG_ORIGIN_URL)?;
    m.add("CONFIG_AUTO_UPDATE", constants::CONFIG_AUTO_UPDATE)?;
    m.add("CONFIG_READ_ONLY", constants::CONFIG_READ_ONLY)?;
    m.add("CONFIG_HIDDEN", constants::CONFIG_HIDDEN)?;
    m.add("CONFIG_IMPORTED", constants::CONFIG_IMPORTED)?;
    m.add("CONFIG_EXTRA_BACKTESTING_TIME_FRAMES", constants::CONFIG_EXTRA_BACKTESTING_TIME_FRAMES)?;
    m.add("CONFIG_COMPLEXITY", constants::CONFIG_COMPLEXITY)?;
    m.add("CONFIG_RISK", constants::CONFIG_RISK)?;
    m.add("CONFIG_TYPE", constants::CONFIG_TYPE)?;
    m.add("PROFILE_CONFIG", constants::PROFILE_CONFIG)?;
    m.add("CONFIG_ID", constants::CONFIG_ID)?;
    m.add("PROFILE_EXPORT_FORMAT", constants::PROFILE_EXPORT_FORMAT)?;
    m.add("IMPORTED_PROFILE_PREFIX", constants::IMPORTED_PROFILE_PREFIX)?;
    m.add("USE_CURRENT_PROFILE", constants::USE_CURRENT_PROFILE)?;
    m.add("USER_PROFILES_FOLDER", constants::USER_PROFILES_FOLDER.as_str())?;
    m.add("PROFILE_FILE_SCHEMA", constants::PROFILE_FILE_SCHEMA.as_str())?;
    m.add("DEFAULT_PROFILE_FILE", constants::DEFAULT_PROFILE_FILE.as_str())?;

    // Crypto currencies
    m.add("CONFIG_CRYPTO_CURRENCIES", constants::CONFIG_CRYPTO_CURRENCIES)?;
    m.add("CONFIG_CRYPTO_CURRENCY", constants::CONFIG_CRYPTO_CURRENCY)?;
    m.add("CONFIG_CRYPTO_PAIRS", constants::CONFIG_CRYPTO_PAIRS)?;
    m.add("CONFIG_CRYPTO_QUOTE", constants::CONFIG_CRYPTO_QUOTE)?;
    m.add("CONFIG_CRYPTO_ADD", constants::CONFIG_CRYPTO_ADD)?;
    m.add("TRADING_SYMBOL_REGEX", constants::TRADING_SYMBOL_REGEX)?;

    // Exchange
    m.add("CONFIG_EXCHANGES", constants::CONFIG_EXCHANGES)?;
    m.add("CONFIG_EXCHANGE_KEY", constants::CONFIG_EXCHANGE_KEY)?;
    m.add("CONFIG_EXCHANGE_SECRET", constants::CONFIG_EXCHANGE_SECRET)?;
    m.add("CONFIG_EXCHANGE_PASSWORD", constants::CONFIG_EXCHANGE_PASSWORD)?;
    m.add("CONFIG_EXCHANGE_UID", constants::CONFIG_EXCHANGE_UID)?;
    m.add("CONFIG_EXCHANGE_ACCESS_TOKEN", constants::CONFIG_EXCHANGE_ACCESS_TOKEN)?;
    m.add("CONFIG_EXCHANGE_TYPE", constants::CONFIG_EXCHANGE_TYPE)?;
    m.add("CONFIG_FORCE_AUTHENTICATION", constants::CONFIG_FORCE_AUTHENTICATION)?;
    m.add("CONFIG_CONTRACT_TYPE", constants::CONFIG_CONTRACT_TYPE)?;
    m.add("CONFIG_REQUIRED_EXTRA_TIMEFRAMES", constants::CONFIG_REQUIRED_EXTRA_TIMEFRAMES)?;
    m.add("CONFIG_EXCHANGE_SANDBOXED", constants::CONFIG_EXCHANGE_SANDBOXED)?;
    m.add("CONFIG_EXCHANGE_FUTURE", constants::CONFIG_EXCHANGE_FUTURE)?;
    m.add("CONFIG_EXCHANGE_MARGIN", constants::CONFIG_EXCHANGE_MARGIN)?;
    m.add("CONFIG_EXCHANGE_OPTION", constants::CONFIG_EXCHANGE_OPTION)?;
    m.add("CONFIG_EXCHANGE_SPOT", constants::CONFIG_EXCHANGE_SPOT)?;
    m.add("CONFIG_EXCHANGE_REST_ONLY", constants::CONFIG_EXCHANGE_REST_ONLY)?;
    m.add("CONFIG_EXCHANGE_WEB_SOCKET", constants::CONFIG_EXCHANGE_WEB_SOCKET)?;
    m.add("CONFIG_EXCHANGE_SUB_ACCOUNT", constants::CONFIG_EXCHANGE_SUB_ACCOUNT)?;
    m.add("CONFIG_EXCHANGE_ENCRYPTED_VALUES", constants::CONFIG_EXCHANGE_ENCRYPTED_VALUES.to_vec())?;

    // Trader
    m.add("CONFIG_TRADING", constants::CONFIG_TRADING)?;
    m.add("CONFIG_TRADER", constants::CONFIG_TRADER)?;
    m.add("CONFIG_LOAD_TRADE_HISTORY", constants::CONFIG_LOAD_TRADE_HISTORY)?;
    m.add("CONFIG_TRADER_RISK", constants::CONFIG_TRADER_RISK)?;
    m.add("CONFIG_TRADER_PAUSED", constants::CONFIG_TRADER_PAUSED)?;
    m.add("CONFIG_TRADER_ALLOW_ARTIFICIAL_ORDERS", constants::CONFIG_TRADER_ALLOW_ARTIFICIAL_ORDERS)?;
    m.add("CONFIG_TRADER_RISK_MIN", constants::CONFIG_TRADER_RISK_MIN)?;
    m.add("CONFIG_TRADER_RISK_MAX", constants::CONFIG_TRADER_RISK_MAX)?;
    m.add("CONFIG_TRADER_REFERENCE_MARKET", constants::CONFIG_TRADER_REFERENCE_MARKET)?;
    m.add("DEFAULT_STORAGE_TRADING_MODE", constants::DEFAULT_STORAGE_TRADING_MODE)?;

    // Simulator
    m.add("CONFIG_SIMULATOR", constants::CONFIG_SIMULATOR)?;
    m.add("CONFIG_STARTING_PORTFOLIO", constants::CONFIG_STARTING_PORTFOLIO)?;
    m.add("SIMULATOR_CURRENT_PORTFOLIO", constants::SIMULATOR_CURRENT_PORTFOLIO)?;
    m.add("CONFIG_SIMULATOR_FEES", constants::CONFIG_SIMULATOR_FEES)?;
    m.add("CONFIG_SIMULATOR_FEES_MAKER", constants::CONFIG_SIMULATOR_FEES_MAKER)?;
    m.add("CONFIG_SIMULATOR_FEES_TAKER", constants::CONFIG_SIMULATOR_FEES_TAKER)?;
    m.add("CONFIG_SIMULATOR_FEES_WITHDRAW", constants::CONFIG_SIMULATOR_FEES_WITHDRAW)?;

    // Optimization campaigns
    m.add("DEFAULT_CAMPAIGN", constants::DEFAULT_CAMPAIGN)?;

    // Optimizer
    m.add("OPTIMIZER_RUNS_FOLDER", constants::OPTIMIZER_RUNS_FOLDER)?;

    // OS
    m.add("PLATFORM_DATA_SEPARATOR", constants::PLATFORM_DATA_SEPARATOR)?;
    m.add("BYTES_BY_GB", constants::BYTES_BY_GB)?;

    // Evaluators
    m.add("INIT_EVAL_NOTE", constants::INIT_EVAL_NOTE)?;
    m.add("START_PENDING_EVAL_NOTE", constants::START_PENDING_EVAL_NOTE)?;

    // Tentacles
    m.add("TENTACLE_DEFAULT_CONFIG", constants::TENTACLE_DEFAULT_CONFIG)?;
    m.add("CONFIG_TENTACLES_FILE", constants::CONFIG_TENTACLES_FILE)?;
    m.add("EVALUATOR_PRIORITY", constants::EVALUATOR_PRIORITY)?;
    m.add("DEFAULT_EVALUATOR_PRIORITY", constants::DEFAULT_EVALUATOR_PRIORITY)?;
    m.add("CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT", constants::CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT)?;
    m.add("CONFIG_HISTORICAL_CONFIGURATION", constants::CONFIG_HISTORICAL_CONFIGURATION)?;
    m.add("NESTED_TENTACLE_CONFIG", constants::NESTED_TENTACLE_CONFIG)?;
    m.add("CONFIG_ACTIVATION_TOPICS", constants::CONFIG_ACTIVATION_TOPICS)?;
    m.add("CONFIG_TRIGGER_TIMEFRAMES", constants::CONFIG_TRIGGER_TIMEFRAMES)?;
    m.add("CONFIG_EMIT_TRADING_SIGNALS", constants::CONFIG_EMIT_TRADING_SIGNALS)?;
    m.add("CONFIG_TRADING_SIGNALS_STRATEGY", constants::CONFIG_TRADING_SIGNALS_STRATEGY)?;
    m.add("ALLOW_DEFAULT_CONFIG", constants::ALLOW_DEFAULT_CONFIG)?;

    // Terms of service
    m.add("CONFIG_ACCEPTED_TERMS", constants::CONFIG_ACCEPTED_TERMS)?;

    // Distribution
    m.add("DEFAULT_DISTRIBUTION", constants::DEFAULT_DISTRIBUTION)?;
    m.add("CONFIG_DISTRIBUTION", constants::CONFIG_DISTRIBUTION)?;

    // Metrics
    m.add("CONFIG_METRICS", constants::CONFIG_METRICS)?;
    m.add("CONFIG_METRICS_BOT_ID", constants::CONFIG_METRICS_BOT_ID)?;
    m.add("TIMER_BEFORE_METRICS_REGISTRATION_SECONDS", constants::TIMER_BEFORE_METRICS_REGISTRATION_SECONDS)?;
    m.add("METRICS_ROUTE_GEN_BOT_ID", constants::METRICS_ROUTE_GEN_BOT_ID)?;
    m.add("METRICS_ROUTE", constants::METRICS_ROUTE)?;
    m.add("COMMUNITY_TOPS_COUNT", constants::COMMUNITY_TOPS_COUNT)?;
    m.add("METRICS_ROUTE_COMMUNITY", constants::METRICS_ROUTE_COMMUNITY.as_str())?;
    m.add("METRICS_ROUTE_UPTIME", constants::METRICS_ROUTE_UPTIME.as_str())?;
    m.add("METRICS_ROUTE_REGISTER", constants::METRICS_ROUTE_REGISTER.as_str())?;

    // Default values
    m.add("DEFAULT_API_KEY", constants::DEFAULT_API_KEY)?;
    m.add("DEFAULT_API_SECRET", constants::DEFAULT_API_SECRET)?;
    m.add("DEFAULT_API_PASSWORD", constants::DEFAULT_API_PASSWORD)?;
    m.add("DEFAULT_EXCHANGE_TYPE", constants::DEFAULT_EXCHANGE_TYPE)?;
    m.add("NO_KEY_VALUE", constants::NO_KEY_VALUE)?;
    m.add("DEFAULT_CONFIG_VALUES", constants::DEFAULT_CONFIG_VALUES.to_vec())?;

    // Cache
    m.add("CACHE_FOLDER", constants::CACHE_FOLDER)?;
    m.add("CACHE_FILE", constants::CACHE_FILE)?;
    m.add("CACHE_HASH_SIZE", constants::CACHE_HASH_SIZE)?;
    m.add("CACHE_RELATED_DATA_SEPARATOR", constants::CACHE_RELATED_DATA_SEPARATOR)?;
    m.add("LOCAL_BOT_DATA", constants::LOCAL_BOT_DATA)?;
    m.add("DO_NOT_CACHE", constants::DO_NOT_CACHE)?;
    m.add("DO_NOT_OVERRIDE_CACHE", constants::DO_NOT_OVERRIDE_CACHE)?;
    m.add("DEFAULT_IGNORED_VALUE", constants::DEFAULT_IGNORED_VALUE)?;
    m.add("UNPROVIDED_CACHE_IDENTIFIER", constants::UNPROVIDED_CACHE_IDENTIFIER)?;

    // Async settings
    m.add("DEFAULT_FUTURE_TIMEOUT", constants::DEFAULT_FUTURE_TIMEOUT)?;

    // Github
    m.add("GITHUB_RAW_CONTENT_URL", constants::GITHUB_RAW_CONTENT_URL)?;
    m.add("GITHUB_API_CONTENT_URL", constants::GITHUB_API_CONTENT_URL)?;
    m.add("GITHUB_BASE_URL", constants::GITHUB_BASE_URL)?;
    m.add("GITHUB_ORGANISATION", constants::GITHUB_ORGANISATION)?;

    // External resources
    m.add("EXTERNAL_RESOURCE_URL", constants::EXTERNAL_RESOURCE_URL)?;

    // Run databases
    m.add("DATA_FOLDER", constants::DATA_FOLDER)?;
    m.add("DB_SEPARATOR", constants::DB_SEPARATOR)?;
    m.add("TINYDB_EXT", constants::TINYDB_EXT)?;
    m.add("MAX_BACKTESTING_RUNS", constants::MAX_BACKTESTING_RUNS)?;
    m.add("MAX_OPTIMIZER_RUNS", constants::MAX_OPTIMIZER_RUNS)?;

    // DSL
    m.add("BASE_OPERATORS_LIBRARY", constants::BASE_OPERATORS_LIBRARY)?;
    m.add("CONTEXTUAL_OPERATORS_LIBRARY", constants::CONTEXTUAL_OPERATORS_LIBRARY)?;
    m.add("UNRESOLVED_PARAMETER_PLACEHOLDER", constants::UNRESOLVED_PARAMETER_PLACEHOLDER)?;

    // Logging
    m.add("EXCEPTION_DESC", constants::EXCEPTION_DESC)?;
    m.add("IS_EXCEPTION_DESC", constants::IS_EXCEPTION_DESC)?;

    // Coins
    m.add("USD_LIKE_COINS", constants::USD_LIKE_COINS.to_vec())?;
    m.add("DEFAULT_REFERENCE_MARKET", constants::DEFAULT_REFERENCE_MARKET)?;
    m.add("USUAL_REFERENCE_MARKET_USD_LIKE_COINS", constants::USUAL_REFERENCE_MARKET_USD_LIKE_COINS.to_vec())?;
    m.add("FIAT_NON_USD_LIKE_COINS", constants::FIAT_NON_USD_LIKE_COINS.to_vec())?;
    m.add("USD_LIKE_AND_FIAT_COINS", constants::USD_LIKE_AND_FIAT_COINS.clone())?;

    // SSL
    m.add("KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL", constants::KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL)?;

    // Environment-variable constants
    m.add("PROFILE_REFRESH_HOURS_INTERVAL", *constants::PROFILE_REFRESH_HOURS_INTERVAL)?;
    m.add("CLOCK_REFRESH_HOURS_INTERVAL", *constants::CLOCK_REFRESH_HOURS_INTERVAL)?;
    m.add("RESOURCES_WATCHER_MINUTES_INTERVAL", *constants::RESOURCES_WATCHER_MINUTES_INTERVAL)?;
    m.add("TIMER_BETWEEN_METRICS_UPTIME_UPDATE", *constants::TIMER_BETWEEN_METRICS_UPTIME_UPDATE)?;
    m.add("METRICS_URL", constants::METRICS_URL.as_str())?;
    m.add("FORCE_BACKTESTING_LOGS", *constants::FORCE_BACKTESTING_LOGS)?;
    m.add("ENABLE_CERTIFI_SSL_CERTIFICATES", *constants::ENABLE_CERTIFI_SSL_CERTIFICATES)?;
    m.add("IS_DEV_MODE_ENABLED", *constants::IS_DEV_MODE_ENABLED)?;
    m.add("USE_MINIMAL_LIBS", *constants::USE_MINIMAL_LIBS)?;

    Ok(())
}
