use std::collections::HashMap;

use crate::constants::{MARKET_SEPARATOR, OPTION_SEPARATOR, SETTLEMENT_ASSET_SEPARATOR, USD_LIKE_COINS};
use crate::symbols::symbol::Symbol;

/// Parse the specified symbol string into a [`Symbol`] object.
pub fn parse_symbol(symbol: &str) -> Symbol {
    Symbol::new(symbol)
}

/// Return merged currency and market without `/`, replacing `:` with `_`.
pub fn merge_symbol(symbol: &str) -> String {
    symbol
        .replace(MARKET_SEPARATOR, "")
        .replace(SETTLEMENT_ASSET_SEPARATOR, "_")
}

/// Check if the given string is a symbol (contains the separator) rather than a single coin.
pub fn is_symbol(value: &str, separator: Option<&str>) -> bool {
    let sep = separator.unwrap_or(MARKET_SEPARATOR);
    value.contains(sep)
}

/// Merge individual currency components into a full symbol string.
#[allow(clippy::too_many_arguments)]
pub fn merge_currencies(
    currency: &str,
    market: &str,
    settlement_asset: Option<&str>,
    identifier: Option<&str>,
    strike_price: Option<&str>,
    option_type: Option<&str>,
    market_separator: Option<&str>,
    settlement_separator: Option<&str>,
    option_separator: Option<&str>,
) -> String {
    let ms = market_separator.unwrap_or(MARKET_SEPARATOR);
    let ss = settlement_separator.unwrap_or(SETTLEMENT_ASSET_SEPARATOR);
    let os = option_separator.unwrap_or(OPTION_SEPARATOR);

    let raw = format!("{currency}{ms}{market}");
    let mut symbol = Symbol::with_separators(&raw, ms, ss, os);

    if let Some(sa) = settlement_asset {
        symbol.settlement_asset = Some(sa.to_string());
    }
    if let Some(sp) = strike_price {
        if !sp.is_empty() {
            symbol.strike_price = Some(sp.to_string());
        }
    }
    if let Some(id) = identifier {
        if !id.is_empty() {
            symbol.identifier = Some(id.to_string());
        }
    }
    if let Some(ot) = option_type {
        if !ot.is_empty() {
            symbol.option_type = Some(ot.to_string());
        }
    }

    symbol.merged_str_symbol(Some(ms), Some(ss), Some(os))
}

/// Convert a symbol string according to the provided parameters.
pub fn convert_symbol(
    symbol: &str,
    symbol_separator: &str,
    new_symbol_separator: Option<&str>,
    should_uppercase: bool,
    should_lowercase: bool,
    base_and_quote_only: bool,
) -> String {
    let new_sep = new_symbol_separator.unwrap_or(MARKET_SEPARATOR);
    let working = if base_and_quote_only {
        symbol
            .split(SETTLEMENT_ASSET_SEPARATOR)
            .next()
            .unwrap_or(symbol)
    } else {
        symbol
    };

    let replaced = working.replace(symbol_separator, new_sep);
    if should_uppercase {
        replaced.to_uppercase()
    } else if should_lowercase {
        replaced.to_lowercase()
    } else {
        replaced
    }
}

/// Return `true` if the given coin is a USD-like coin.
pub fn is_usd_like_coin(coin: &str) -> bool {
    USD_LIKE_COINS.contains(&coin)
}

/// Return the most common USD-like symbol found among the given pairs.
///
/// # Errors
///
/// Returns an error if `pairs` is empty or no USD-like symbol is found.
pub fn get_most_common_usd_like_symbol(pairs: &[&str]) -> Result<String, String> {
    if pairs.is_empty() {
        return Err("Pairs cannot be empty".to_string());
    }

    let mut counts: HashMap<String, usize> = HashMap::new();
    for pair in pairs {
        let parsed = Symbol::new(pair);
        if let Some(ref q) = parsed.quote {
            *counts.entry(q.clone()).or_insert(0) += 1;
        }
        if let Some(ref b) = parsed.base {
            *counts.entry(b.clone()).or_insert(0) += 1;
        }
    }

    // Sort by count descending (stable-sort preserves insertion order for ties,
    // matching Python's Counter.most_common behaviour when items have equal counts).
    let mut entries: Vec<(String, usize)> = counts.into_iter().collect();
    entries.sort_by_key(|e| std::cmp::Reverse(e.1));

    for (symbol, _) in &entries {
        if is_usd_like_coin(symbol) {
            return Ok(symbol.clone());
        }
    }

    Err("Pairs cannot be empty".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_symbol() {
        let s = parse_symbol("BTC/USDT");
        assert_eq!(s.base.as_deref(), Some("BTC"));
        assert_eq!(s.quote.as_deref(), Some("USDT"));
    }

    #[test]
    fn test_merge_symbol() {
        assert_eq!(merge_symbol("BTC/USDT"), "BTCUSDT");
        assert_eq!(merge_symbol("BTC/USDT:USDT"), "BTCUSDT_USDT");
    }

    #[test]
    fn test_is_symbol() {
        assert!(is_symbol("BTC/USDT", None));
        assert!(!is_symbol("BTC", None));
    }

    #[test]
    fn test_merge_currencies_spot() {
        assert_eq!(
            merge_currencies("BTC", "USDT", None, None, None, None, None, None, None),
            "BTC/USDT"
        );
    }

    #[test]
    fn test_merge_currencies_future() {
        assert_eq!(
            merge_currencies(
                "BTC",
                "USDT",
                Some("USDT"),
                None,
                None,
                None,
                None,
                None,
                None
            ),
            "BTC/USDT:USDT"
        );
    }

    #[test]
    fn test_convert_symbol_uppercase() {
        assert_eq!(
            convert_symbol("btc/usdt", "/", Some("-"), true, false, false),
            "BTC-USDT"
        );
    }

    #[test]
    fn test_convert_symbol_lowercase() {
        assert_eq!(
            convert_symbol("BTC/USDT", "/", Some("-"), false, true, false),
            "btc-usdt"
        );
    }

    #[test]
    fn test_convert_symbol_base_and_quote_only() {
        assert_eq!(
            convert_symbol("BTC/USDT:USDT", "/", Some("/"), false, false, true),
            "BTC/USDT"
        );
    }

    #[test]
    fn test_is_usd_like_coin() {
        assert!(is_usd_like_coin("USDT"));
        assert!(is_usd_like_coin("USDC"));
        assert!(!is_usd_like_coin("BTC"));
    }

    #[test]
    fn test_get_most_common_usd_like_symbol() {
        let pairs = vec!["BTC/USDT", "ETH/USDT", "SOL/USDC"];
        assert_eq!(
            get_most_common_usd_like_symbol(&pairs).unwrap(),
            "USDT"
        );
    }

    #[test]
    fn test_get_most_common_usd_like_symbol_empty() {
        let pairs: Vec<&str> = vec![];
        assert!(get_most_common_usd_like_symbol(&pairs).is_err());
    }

    #[test]
    fn test_get_most_common_usd_like_symbol_no_usd() {
        let pairs = vec!["BTC/ETH"];
        assert!(get_most_common_usd_like_symbol(&pairs).is_err());
    }
}
