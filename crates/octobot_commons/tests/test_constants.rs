use octobot_commons::constants::*;
use octobot_commons::enums::TimeFrames;

#[test]
fn test_market_separator() {
    assert_eq!(MARKET_SEPARATOR, "/");
}

#[test]
fn test_settlement_asset_separator() {
    assert_eq!(SETTLEMENT_ASSET_SEPARATOR, ":");
}

#[test]
fn test_option_separator() {
    assert_eq!(OPTION_SEPARATOR, "-");
}

#[test]
fn test_project_name() {
    assert_eq!(PROJECT_NAME, "OctoBot-Commons");
}

#[test]
fn test_minute_to_seconds() {
    assert_eq!(MINUTE_TO_SECONDS, 60);
}

#[test]
fn test_hours_to_seconds() {
    assert_eq!(HOURS_TO_SECONDS, 3600);
}

#[test]
fn test_days_to_seconds() {
    assert_eq!(DAYS_TO_SECONDS, 86400);
}

#[test]
fn test_min_eval_time_frame() {
    assert_eq!(MIN_EVAL_TIME_FRAME, TimeFrames::OneMinute);
}

#[test]
fn test_is_default_config_value_true() {
    assert!(is_default_config_value("your-api-key-here"));
}

#[test]
fn test_is_default_config_value_false() {
    assert!(!is_default_config_value("real-key"));
}

#[test]
fn test_usd_like_coins_contains_usdt_usdc() {
    assert!(USD_LIKE_COINS.contains(&"USDT"));
    assert!(USD_LIKE_COINS.contains(&"USDC"));
}

#[test]
fn test_usd_like_coins_does_not_contain_btc() {
    assert!(!USD_LIKE_COINS.contains(&"BTC"));
}

#[test]
fn test_parse_boolean_environment_var_nonexistent_default_false() {
    // Use a key that should not exist in the environment.
    assert!(!parse_boolean_environment_var(
        "OCTOBOT_TEST_NONEXISTENT_VAR_12345",
        "false"
    ));
}

#[test]
fn test_parse_boolean_environment_var_nonexistent_default_true() {
    assert!(parse_boolean_environment_var(
        "OCTOBOT_TEST_NONEXISTENT_VAR_12345",
        "true"
    ));
}
