use octobot_commons::enums::OptionTypes;
use octobot_commons::symbols::symbol::Symbol;
use octobot_commons::symbols::symbol_util::*;

#[test]
fn test_parse_symbol() {
    assert_eq!(parse_symbol("BTC/USDT"), Symbol::new("BTC/USDT"));
}

#[test]
fn test_merge_symbol() {
    assert_eq!(merge_symbol("BTC/USDT"), "BTCUSDT");
    assert_eq!(merge_symbol("BTC/USDT:USDT"), "BTCUSDT_USDT");
}

#[test]
fn test_merge_currencies_simple() {
    assert_eq!(
        merge_currencies("BTC", "USDT", None, None, None, None, None, None, None),
        "BTC/USDT"
    );
}

#[test]
fn test_merge_currencies_with_settlement() {
    assert_eq!(
        merge_currencies("BTC", "USDT", Some("BTC"), None, None, None, None, None, None),
        "BTC/USDT:BTC"
    );
}

#[test]
fn test_merge_currencies_custom_separators() {
    assert_eq!(
        merge_currencies(
            "BTC", "USDT", Some("XXX"), None, None, None, Some("g"), Some("d"), None
        ),
        "BTCgUSDTdXXX"
    );
}

#[test]
fn test_merge_currencies_option_put() {
    assert_eq!(
        merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            Some("USDC"),
            Some("261231"),
            Some("0"),
            Some(OptionTypes::Put.value()),
            None,
            None,
            None,
        ),
        "will-bitcoin-replace-sha-256-before-2027/USDC:USDC-261231-0-P"
    );
}

#[test]
fn test_merge_currencies_option_custom_type() {
    assert_eq!(
        merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            Some("USDC"),
            Some("261231"),
            Some("0"),
            Some("test"),
            None,
            None,
            None,
        ),
        "will-bitcoin-replace-sha-256-before-2027/USDC:USDC-261231-0-TEST"
    );
}

#[test]
fn test_merge_currencies_option_none_type() {
    assert_eq!(
        merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            Some("USDC"),
            Some("261231"),
            Some("0"),
            None,
            None,
            None,
            None,
        ),
        "will-bitcoin-replace-sha-256-before-2027/USDC:USDC"
    );
}

#[test]
fn test_convert_symbol() {
    assert_eq!(
        convert_symbol("BTC-USDT", "-", None, false, false, false),
        "BTC/USDT"
    );
}

#[test]
fn test_is_symbol_default_separator() {
    assert!(is_symbol("BTC/USDT", None));
    assert!(is_symbol("ETH/USDT", None));
    assert!(is_symbol("BTC/USDT:USDT", None));
    assert!(!is_symbol("BTC", None));
    assert!(!is_symbol("USDT", None));
}

#[test]
fn test_is_symbol_dash_separator() {
    assert!(is_symbol("BTC-USDT", Some("-")));
    assert!(!is_symbol("BTC", Some("-")));
}

#[test]
fn test_is_symbol_colon_separator() {
    assert!(is_symbol("BTC/USDT:USDT", Some(":")));
    assert!(!is_symbol("BTC/USDT", Some(":")));
}

#[test]
fn test_is_symbol_pipe_separator() {
    assert!(is_symbol("BTC|USDT", Some("|")));
    assert!(!is_symbol("BTC", Some("|")));
}

#[test]
fn test_is_symbol_edge_cases() {
    assert!(!is_symbol("", Some("/")));
    assert!(is_symbol("/", Some("/")));
    assert!(is_symbol("BTC/USDT/ETH", Some("/")));
}

#[test]
fn test_is_usd_like_coin() {
    assert!(is_usd_like_coin("USDT"));
    assert!(is_usd_like_coin("USDC"));
    assert!(is_usd_like_coin("USD"));
    assert!(is_usd_like_coin("BUSD"));
    assert!(!is_usd_like_coin("BTC"));
    assert!(!is_usd_like_coin("ETH"));
    assert!(!is_usd_like_coin(""));
}

#[test]
fn test_get_most_common_usd_like_symbol() {
    let pairs = vec!["BTC/USDT", "ETH/USDT", "SOL/USDC"];
    let result = get_most_common_usd_like_symbol(&pairs);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "USDT");

    let pairs = vec!["BTC/USDC", "ETH/USDC", "SOL/USDT"];
    let result = get_most_common_usd_like_symbol(&pairs);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "USDC");

    let empty: Vec<&str> = vec![];
    let result = get_most_common_usd_like_symbol(&empty);
    assert!(result.is_err());

    let no_usd = vec!["BTC/ETH", "SOL/BTC"];
    let result = get_most_common_usd_like_symbol(&no_usd);
    assert!(result.is_err());
}
