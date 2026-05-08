// Unified data types normalised to OctoBot's internal format.
// Translated from packages/trading/octobot_trading/enums.py column enums
// and the ccxt adapter output format.

use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::enums::{MarginType, OrderStatus, PositionSide, PositionStatus, TradeOrderSide, TraderOrderType};

/// OHLCV candle. Timestamp in seconds (uniformised from exchange ms timestamps).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candle {
    pub timestamp: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

impl Candle {
    pub fn is_valid(&self) -> bool {
        self.open > 0.0 && self.high >= self.low && self.volume >= 0.0
    }
}

/// Unified ticker (matches ExchangeConstantsTickersColumns)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Ticker {
    pub symbol: String,
    pub timestamp: i64,
    pub high: Option<f64>,
    pub low: Option<f64>,
    pub bid: Option<f64>,
    pub bid_volume: Option<f64>,
    pub ask: Option<f64>,
    pub ask_volume: Option<f64>,
    pub vwap: Option<f64>,
    pub open: Option<f64>,
    pub close: Option<f64>,
    pub last: Option<f64>,
    pub change: Option<f64>,
    pub percentage: Option<f64>,
    pub base_volume: Option<f64>,
    pub quote_volume: Option<f64>,
    /// Mark price (futures)
    pub mark_price: Option<f64>,
}

impl Ticker {
    pub fn last_price(&self) -> Option<f64> {
        self.last.or(self.close)
    }
}

/// Order book snapshot (matches ExchangeConstantsOrderBookInfoColumns)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct OrderBook {
    pub symbol: String,
    pub timestamp: i64,
    /// [price, quantity] pairs, best bid first
    pub bids: Vec<[f64; 2]>,
    /// [price, quantity] pairs, best ask first
    pub asks: Vec<[f64; 2]>,
}

impl OrderBook {
    pub fn best_bid(&self) -> Option<f64> {
        self.bids.first().map(|b| b[0])
    }

    pub fn best_ask(&self) -> Option<f64> {
        self.asks.first().map(|a| a[0])
    }
}

/// Fee details (matches FeePropertyColumns)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Fee {
    pub cost: Decimal,
    pub currency: Option<String>,
    pub rate: Option<f64>,
    pub fee_type: Option<String>,
    /// True when fee was fetched from exchange (not estimated)
    pub is_from_exchange: bool,
    pub exchange_original_cost: Option<Decimal>,
}

/// Unified order (matches ExchangeConstantsOrderColumns)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub id: String,
    pub exchange_id: Option<String>,
    pub timestamp: i64,
    pub symbol: String,
    pub order_type: TraderOrderType,
    pub side: TradeOrderSide,
    pub price: Option<f64>,
    pub amount: f64,
    pub filled: f64,
    pub remaining: f64,
    pub cost: Option<f64>,
    pub average: Option<f64>,
    pub status: OrderStatus,
    pub fee: Option<Fee>,
    pub stop_price: Option<f64>,
    pub stop_loss_price: Option<f64>,
    pub take_profit_price: Option<f64>,
    pub reduce_only: bool,
    pub trigger_above: Option<bool>,
    pub tag: Option<String>,
    pub quantity_currency: Option<String>,
    /// Raw extra fields from the exchange info dict
    pub extra: HashMap<String, serde_json::Value>,
}

impl Order {
    pub fn is_open(&self) -> bool {
        matches!(self.status, OrderStatus::Open | OrderStatus::PartiallyFilled | OrderStatus::PendingCreation)
    }

    pub fn is_closed(&self) -> bool {
        self.status.is_closed()
    }
}

/// A single trade (filled or public)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub id: Option<String>,
    /// Exchange-native trade ID
    pub exchange_trade_id: Option<String>,
    pub order_id: Option<String>,
    pub timestamp: i64,
    pub symbol: String,
    pub side: TradeOrderSide,
    pub price: f64,
    pub amount: f64,
    pub cost: Option<f64>,
    pub fee: Option<Fee>,
    pub taker_or_maker: Option<String>,
}

/// Position (futures / margin) — matches ExchangeConstantsPositionColumns
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub symbol: String,
    pub timestamp: i64,
    pub side: PositionSide,
    pub status: PositionStatus,
    pub margin_type: Option<MarginType>,
    pub leverage: Option<f64>,
    pub contracts: Option<f64>,
    pub contract_size: Option<f64>,
    pub entry_price: Option<f64>,
    pub mark_price: Option<f64>,
    pub liquidation_price: Option<f64>,
    pub unrealized_pnl: Option<f64>,
    pub realized_pnl: Option<f64>,
    pub closing_fee: Option<f64>,
    pub notional: Option<f64>,
    pub initial_margin: Option<f64>,
    pub maintenance_margin: Option<f64>,
    pub margin_ratio: Option<f64>,
    pub collateral: Option<f64>,
    pub position_mode: Option<String>,
    pub maintenance_margin_rate: Option<f64>,
}

impl Position {
    pub fn is_empty(&self) -> bool {
        self.contracts.map_or(true, |c| c == 0.0)
    }
}

/// Balance for a single currency (matches CONFIG_PORTFOLIO_FREE/USED/TOTAL)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CurrencyBalance {
    pub free: Decimal,
    pub used: Decimal,
    pub total: Decimal,
}

/// Full portfolio balance keyed by currency symbol
pub type Balance = HashMap<String, CurrencyBalance>;

/// Market status precision (matches ExchangeConstantsMarketStatusColumns.PRECISION_*)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MarketPrecision {
    pub price: Option<f64>,
    pub amount: Option<f64>,
    pub cost: Option<f64>,
}

/// Market status limits (min/max for amount, price, cost)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MarketLimits {
    pub amount_min: Option<f64>,
    pub amount_max: Option<f64>,
    pub price_min: Option<f64>,
    pub price_max: Option<f64>,
    pub cost_min: Option<f64>,
    pub cost_max: Option<f64>,
}

/// Market status (matches ExchangeConstantsMarketStatusColumns)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketStatus {
    pub symbol: String,
    pub id: Option<String>,
    pub currency: Option<String>,
    pub market: Option<String>,
    pub active: bool,
    pub precision: MarketPrecision,
    pub limits: MarketLimits,
    pub contract_size: Option<f64>,
    pub market_type: Option<String>,
    pub taker_fee: Option<f64>,
    pub maker_fee: Option<f64>,
    /// Raw ccxt market info dict
    pub raw: HashMap<String, serde_json::Value>,
}

/// Funding rate (futures)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FundingRate {
    pub symbol: String,
    pub funding_rate: Option<f64>,
    pub last_funding_time: Option<i64>,
    pub next_funding_time: Option<i64>,
    pub predicted_funding_rate: Option<f64>,
}

/// Leverage info (futures)
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LeverageInfo {
    pub symbol: String,
    pub leverage: Option<f64>,
    pub margin_mode: Option<String>,
    pub long_leverage: Option<f64>,
    pub short_leverage: Option<f64>,
}

/// Transaction / withdrawal / deposit
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub id: Option<String>,
    pub txid: Option<String>,
    pub timestamp: Option<i64>,
    pub address_to: Option<String>,
    pub address_from: Option<String>,
    pub tag: Option<String>,
    pub tx_type: Option<String>,
    pub amount: Option<f64>,
    pub currency: Option<String>,
    pub status: Option<String>,
    pub fee: Option<Fee>,
    pub network: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_candle_validity() {
        let c = Candle { timestamp: 1000, open: 100.0, high: 110.0, low: 90.0, close: 105.0, volume: 1000.0 };
        assert!(c.is_valid());
        let bad = Candle { timestamp: 1000, open: 0.0, high: 0.0, low: 0.0, close: 0.0, volume: 0.0 };
        assert!(!bad.is_valid());
    }

    #[test]
    fn test_order_book_best_prices() {
        let ob = OrderBook {
            symbol: "BTC/USDT".into(),
            timestamp: 0,
            bids: vec![[50000.0, 1.0], [49999.0, 2.0]],
            asks: vec![[50001.0, 0.5], [50002.0, 1.0]],
        };
        assert_eq!(ob.best_bid(), Some(50000.0));
        assert_eq!(ob.best_ask(), Some(50001.0));
    }

    #[test]
    fn test_position_empty() {
        let mut p = Position {
            symbol: "BTC/USDT".into(),
            timestamp: 0,
            side: crate::enums::PositionSide::Long,
            status: PositionStatus::Open,
            margin_type: None,
            leverage: None,
            contracts: Some(0.0),
            contract_size: None,
            entry_price: None,
            mark_price: None,
            liquidation_price: None,
            unrealized_pnl: None,
            realized_pnl: None,
            closing_fee: None,
            notional: None,
            initial_margin: None,
            maintenance_margin: None,
            margin_ratio: None,
            collateral: None,
            position_mode: None,
            maintenance_margin_rate: None,
        };
        assert!(p.is_empty());
        p.contracts = Some(1.5);
        assert!(!p.is_empty());
    }
}
