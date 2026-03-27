use std::fmt;
use std::sync::LazyLock;

use regex::Regex;

use crate::constants::{MARKET_SEPARATOR, OPTION_SEPARATOR, SETTLEMENT_ASSET_SEPARATOR};
use crate::enums::OptionTypes;

static FULL_SYMBOL_GROUPS_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"([^//]*)\/([^:]*):?([^-]*)-?([^-]*)-?([^-]*)-?([^-]*)").unwrap()
});

/// Represents a trading symbol parsed into its constituent parts.
///
/// Inspired from CCXT <https://docs.ccxt.com/en/latest/manual.html#option>:
///
/// ```text
///   base / quote : settlement - identifier - strike price - type
///   BTC  / USDT  : BTC        - 211225     - 60000        - P
/// ```
#[derive(Debug, Clone)]
pub struct Symbol {
    pub symbol_str: String,
    pub base: Option<String>,
    pub quote: Option<String>,
    pub settlement_asset: Option<String>,
    pub identifier: Option<String>,
    pub strike_price: Option<String>,
    pub option_type: Option<String>,
    pub market_separator: String,
    pub settlement_separator: String,
    pub option_separator: String,
}

impl Symbol {
    pub fn new(symbol_str: &str) -> Self {
        Self::with_separators(
            symbol_str,
            MARKET_SEPARATOR,
            SETTLEMENT_ASSET_SEPARATOR,
            OPTION_SEPARATOR,
        )
    }

    pub fn with_separators(
        symbol_str: &str,
        market_separator: &str,
        settlement_separator: &str,
        option_separator: &str,
    ) -> Self {
        let mut s = Self {
            symbol_str: symbol_str.to_string(),
            base: None,
            quote: None,
            settlement_asset: None,
            identifier: None,
            strike_price: None,
            option_type: None,
            market_separator: market_separator.to_string(),
            settlement_separator: settlement_separator.to_string(),
            option_separator: option_separator.to_string(),
        };
        s.parse_symbol(symbol_str);
        s
    }

    /// Parse the specified symbol string and populate all fields.
    pub fn parse_symbol(&mut self, symbol_str: &str) {
        if symbol_str.contains(&self.settlement_separator) {
            let (base, quote, settlement, identifier, strike, opt_type) =
                _parse_symbol_full(&FULL_SYMBOL_GROUPS_REGEX, symbol_str);
            self.base = Some(base);
            self.quote = Some(quote);
            self.settlement_asset = Some(settlement);
            self.identifier = Some(identifier);
            self.strike_price = Some(strike);
            self.option_type = _parse_option_type(opt_type.as_str());
        } else {
            // simple (probably spot) pair, use split as it is much faster
            let (base, quote) = _parse_spot_symbol(&self.market_separator, symbol_str);
            self.base = Some(base);
            self.quote = quote;
            self.settlement_asset = Some(String::new());
            self.identifier = Some(String::new());
            self.strike_price = Some(String::new());
            self.option_type = None;
        }
    }

    /// Return a tuple of (base, quote) for this symbol.
    pub fn base_and_quote(&self) -> (Option<&str>, Option<&str>) {
        (self.base.as_deref(), self.quote.as_deref())
    }

    /// Return the full merged string representation of this symbol, including settlement
    /// asset and option details when present.
    pub fn merged_str_symbol(
        &self,
        market_separator: Option<&str>,
        settlement_separator: Option<&str>,
        option_separator: Option<&str>,
    ) -> String {
        let ms = market_separator.unwrap_or(MARKET_SEPARATOR);
        let ss = settlement_separator.unwrap_or(SETTLEMENT_ASSET_SEPARATOR);
        let os = option_separator.unwrap_or(OPTION_SEPARATOR);

        let base = self.base.as_deref().unwrap_or("");
        let quote = self.quote.as_deref().unwrap_or("");
        let mut merged = format!("{base}{ms}{quote}");

        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        if !settlement.is_empty() {
            merged = format!("{merged}{ss}{settlement}");

            let strike = self.strike_price.as_deref().unwrap_or("");
            let ident = self.identifier.as_deref().unwrap_or("");
            let opt_type = self.option_type.as_deref().unwrap_or("");
            if !strike.is_empty() && !ident.is_empty() && !opt_type.is_empty() {
                let parsed_type = _parse_option_type(opt_type).unwrap_or_default();
                let details = ["", ident, strike, &parsed_type];
                merged = format!("{merged}{}", details.join(os));
            }
        }
        merged
    }

    /// Return the base/quote representation of this symbol without settlement details.
    pub fn merged_str_base_and_quote_only_symbol(
        &self,
        market_separator: Option<&str>,
    ) -> String {
        let ms = market_separator.unwrap_or(MARKET_SEPARATOR);
        let base = self.base.as_deref().unwrap_or("");
        let quote = self.quote.as_deref().unwrap_or("");
        format!("{base}{ms}{quote}")
    }

    /// Return `true` when this symbol represents a perpetual future contract.
    pub fn is_perpetual_future(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        let identifier = self.identifier.as_deref().unwrap_or("");
        let strike = self.strike_price.as_deref().unwrap_or("");
        let opt_type = self.option_type.as_deref().unwrap_or("");
        !settlement.is_empty()
            && identifier.is_empty()
            && strike.is_empty()
            && opt_type.is_empty()
    }

    /// Return `true` when this symbol represents a spot asset.
    pub fn is_spot(&self) -> bool {
        let base = self.base.as_deref().unwrap_or("");
        let quote = self.quote.as_deref().unwrap_or("");
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        !base.is_empty() && !quote.is_empty() && settlement.is_empty()
    }

    /// Return `true` when this symbol represents a non-perpetual future contract.
    pub fn is_future(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        let strike = self.strike_price.as_deref().unwrap_or("");
        let opt_type = self.option_type.as_deref().unwrap_or("");
        !settlement.is_empty() && strike.is_empty() && opt_type.is_empty()
    }

    /// Return `true` when this symbol has an expiration date.
    pub fn does_expire(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        let identifier = self.identifier.as_deref().unwrap_or("");
        !settlement.is_empty() && !identifier.is_empty()
    }

    /// Return `true` when this symbol represents a put option.
    pub fn is_put_option(&self) -> bool {
        self.option_type.as_deref() == Some(OptionTypes::Put.value())
    }

    /// Return `true` when this symbol represents a call option.
    pub fn is_call_option(&self) -> bool {
        self.option_type.as_deref() == Some(OptionTypes::Call.value())
    }

    /// Return `true` when this symbol represents an option contract.
    pub fn is_option(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        let identifier = self.identifier.as_deref().unwrap_or("");
        let strike = self.strike_price.as_deref().unwrap_or("");
        let opt_type = self.option_type.as_deref().unwrap_or("");
        !settlement.is_empty()
            && !identifier.is_empty()
            && !strike.is_empty()
            && !opt_type.is_empty()
    }

    /// Return `true` when this symbol represents a linear contract
    /// (settlement_asset == quote), or when there is no settlement asset.
    pub fn is_linear(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        if settlement.is_empty() {
            true
        } else {
            self.quote.as_deref() == Some(settlement)
        }
    }

    /// Return `true` when this symbol represents an inverse contract
    /// (settlement_asset == base).
    pub fn is_inverse(&self) -> bool {
        let settlement = self.settlement_asset.as_deref().unwrap_or("");
        if settlement.is_empty() {
            false
        } else {
            self.base.as_deref() == Some(settlement)
        }
    }

    /// Return `true` if the given symbol has the same base and quote as self.
    pub fn is_same_base_and_quote(&self, other: &Symbol) -> bool {
        self.base == other.base && self.quote == other.quote
    }
}

impl PartialEq for Symbol {
    fn eq(&self, other: &Self) -> bool {
        std::ptr::eq(self, other)
            || (self.symbol_str == other.symbol_str
                && self.base == other.base
                && self.quote == other.quote
                && self.settlement_asset == other.settlement_asset
                && self.identifier == other.identifier
                && self.strike_price == other.strike_price
                && self.option_type == other.option_type)
    }
}

impl Eq for Symbol {}

impl fmt::Display for Symbol {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.symbol_str)
    }
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

fn _parse_symbol_full(
    regex: &Regex,
    symbol_str: &str,
) -> (String, String, String, String, String, String) {
    let caps = regex.captures(symbol_str).expect("symbol regex must match");
    let get = |i: usize| {
        caps.get(i)
            .map(|m| m.as_str().to_string())
            .unwrap_or_default()
    };
    (get(1), get(2), get(3), get(4), get(5), get(6))
}

fn _parse_spot_symbol(separator: &str, symbol_str: &str) -> (String, Option<String>) {
    let parts: Vec<&str> = symbol_str.splitn(3, separator).collect();
    if parts.len() < 2 {
        (symbol_str.to_string(), None)
    } else {
        (parts[0].to_string(), Some(parts[1].to_string()))
    }
}

fn _parse_option_type(option_type_str: &str) -> Option<String> {
    if option_type_str.is_empty() {
        None
    } else {
        Some(option_type_str.to_uppercase())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_spot_symbol() {
        let s = Symbol::new("BTC/USDT");
        assert_eq!(s.base.as_deref(), Some("BTC"));
        assert_eq!(s.quote.as_deref(), Some("USDT"));
        assert!(s.is_spot());
        assert!(!s.is_future());
        assert!(!s.is_option());
    }

    #[test]
    fn test_perpetual_future() {
        let s = Symbol::new("BTC/USDT:USDT");
        assert_eq!(s.base.as_deref(), Some("BTC"));
        assert_eq!(s.quote.as_deref(), Some("USDT"));
        assert_eq!(s.settlement_asset.as_deref(), Some("USDT"));
        assert!(s.is_perpetual_future());
        assert!(s.is_future());
        assert!(s.is_linear());
        assert!(!s.is_inverse());
        assert!(!s.is_spot());
    }

    #[test]
    fn test_inverse_perpetual() {
        let s = Symbol::new("BTC/USDT:BTC");
        assert!(s.is_perpetual_future());
        assert!(s.is_inverse());
        assert!(!s.is_linear());
    }

    #[test]
    fn test_option_put() {
        let s = Symbol::new("BTC/USDT:BTC-211225-60000-P");
        assert!(s.is_option());
        assert!(s.is_put_option());
        assert!(!s.is_call_option());
        assert_eq!(s.option_type.as_deref(), Some("P"));
        assert_eq!(s.strike_price.as_deref(), Some("60000"));
        assert_eq!(s.identifier.as_deref(), Some("211225"));
    }

    #[test]
    fn test_option_call() {
        let s = Symbol::new("ETH/USDT:USDT-210625-5000-C");
        assert!(s.is_option());
        assert!(s.is_call_option());
        assert!(!s.is_put_option());
    }

    #[test]
    fn test_display() {
        let s = Symbol::new("BTC/USDT");
        assert_eq!(format!("{s}"), "BTC/USDT");
    }

    #[test]
    fn test_equality() {
        let a = Symbol::new("BTC/USDT");
        let b = Symbol::new("BTC/USDT");
        assert_eq!(a, b);
    }

    #[test]
    fn test_merged_str_symbol_spot() {
        let s = Symbol::new("BTC/USDT");
        assert_eq!(s.merged_str_symbol(None, None, None), "BTC/USDT");
    }

    #[test]
    fn test_merged_str_symbol_option() {
        let s = Symbol::new("BTC/USDT:BTC-211225-60000-P");
        assert_eq!(
            s.merged_str_symbol(None, None, None),
            "BTC/USDT:BTC-211225-60000-P"
        );
    }

    #[test]
    fn test_no_separator_single_coin() {
        let s = Symbol::new("BTC");
        assert_eq!(s.base.as_deref(), Some("BTC"));
        assert_eq!(s.quote, None);
    }
}
