// Futures contracts data layer.
// Mirrors octobot_trading.exchange_data.contracts (Contract / MarginContract /
// FutureContract / OptionContract). Implemented as a single FutureContract
// struct here since the Python distinction is mostly cosmetic.

use rust_decimal::Decimal;
use std::collections::HashMap;

use crate::enums::{FutureContractType, MarginType, PositionMode};

/// Future contract details for a single trading pair.
/// Combines Contract + MarginContract + FutureContract from Python into one struct.
#[derive(Debug, Clone)]
pub struct FutureContract {
    pub pair: String,
    pub margin_type: Option<MarginType>,
    pub contract_size: Decimal,
    pub maximum_leverage: Decimal,
    pub current_leverage: Decimal,
    pub contract_type: FutureContractType,
    pub minimum_tick_size: Option<Decimal>,
    pub position_mode: Option<PositionMode>,
    pub maintenance_margin_rate: Option<Decimal>,
    pub risk_limit: HashMap<String, serde_json::Value>,
}

impl FutureContract {
    pub fn new(pair: String, contract_type: FutureContractType) -> Self {
        Self {
            pair,
            margin_type: None,
            contract_size: Decimal::ONE,
            maximum_leverage: Decimal::ONE,
            current_leverage: Decimal::ONE,
            contract_type,
            minimum_tick_size: None,
            position_mode: None,
            maintenance_margin_rate: None,
            risk_limit: HashMap::new(),
        }
    }

    pub fn is_linear(&self) -> bool {
        matches!(
            self.contract_type,
            FutureContractType::LinearPerpetual | FutureContractType::LinearExpirable
        )
    }

    pub fn is_inverse(&self) -> bool {
        matches!(
            self.contract_type,
            FutureContractType::InversePerpetual | FutureContractType::InverseExpirable
        )
    }

    pub fn is_expirable(&self) -> bool {
        matches!(
            self.contract_type,
            FutureContractType::LinearExpirable | FutureContractType::InverseExpirable
        )
    }
}

/// Single leverage tier (mirrors LeverageTier from Python).
#[derive(Debug, Clone, Default)]
pub struct LeverageTier {
    pub tier: u32,
    pub currency: Option<String>,
    pub min_notional: Option<Decimal>,
    pub max_notional: Option<Decimal>,
    pub maintenance_margin_rate: Option<Decimal>,
    pub max_leverage: Option<Decimal>,
    pub info: HashMap<String, serde_json::Value>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_future_contract_new() {
        let c = FutureContract::new("BTC/USDT:USDT".into(), FutureContractType::LinearPerpetual);
        assert_eq!(c.pair, "BTC/USDT:USDT");
        assert!(c.is_linear());
        assert!(!c.is_inverse());
        assert!(!c.is_expirable());
    }

    #[test]
    fn test_inverse_expirable() {
        let c = FutureContract::new("BTC/USD:BTC-251225".into(), FutureContractType::InverseExpirable);
        assert!(c.is_inverse());
        assert!(c.is_expirable());
        assert!(!c.is_linear());
    }
}
