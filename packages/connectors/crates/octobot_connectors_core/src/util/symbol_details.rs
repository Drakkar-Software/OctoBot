// Symbol details.
// Translated from packages/trading/octobot_trading/exchanges/util/symbol_details.py

use std::collections::HashMap;

/// Stores CCXT-specific parsed and raw symbol details.
/// Mirrors Python SymbolDetails / CCXTDetails dataclasses.
#[derive(Debug, Clone, Default)]
pub struct CcxtDetails {
    pub info: HashMap<String, serde_json::Value>,
    pub parsed: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Default)]
pub struct SymbolDetails {
    pub ccxt: CcxtDetails,
}

impl SymbolDetails {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn update(&mut self, other: &SymbolDetails) {
        for (k, v) in &other.ccxt.info {
            self.ccxt.info.insert(k.clone(), v.clone());
        }
        for (k, v) in &other.ccxt.parsed {
            self.ccxt.parsed.insert(k.clone(), v.clone());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_symbol_details_default() {
        let sd = SymbolDetails::default();
        assert!(sd.ccxt.info.is_empty());
    }

    #[test]
    fn test_symbol_details_update() {
        let mut sd = SymbolDetails::new();
        let mut other = SymbolDetails::new();
        other.ccxt.info.insert("key".into(), serde_json::json!("value"));
        sd.update(&other);
        assert_eq!(sd.ccxt.info.get("key"), Some(&serde_json::json!("value")));
    }
}
