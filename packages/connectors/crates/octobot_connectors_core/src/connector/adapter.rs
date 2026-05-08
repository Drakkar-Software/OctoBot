// CcxtAdapter: transforms raw ccxt Rust crate responses into OctoBot unified types.
// Translated from:
//   packages/trading/octobot_trading/exchanges/adapters/abstract_adapter.py
//   packages/trading/octobot_trading/exchanges/connectors/ccxt/ccxt_adapter.py

use std::collections::HashMap;
use rust_decimal::prelude::*;

use crate::enums::{MarginType, OrderStatus, PositionSide, PositionStatus, TradeOrderSide, TraderOrderType};
use crate::error::{ExchangeResult, OctoBotExchangeError};
use crate::types::{
    Balance, Candle, CurrencyBalance, Fee, FundingRate, LeverageInfo, MarketLimits,
    MarketPrecision, MarketStatus, Order, OrderBook, Position, Ticker, Trade, Transaction,
};
use crate::enums::TimeFrame;
use crate::util::timestamp_util::uniformize_timestamp;

/// Adapter: translates ccxt raw JSON values into OctoBot normalised structs.
/// Every method mirrors the Python @_adapter-decorated methods in AbstractAdapter/CCXTAdapter.
pub struct CcxtAdapter;

impl CcxtAdapter {
    pub fn new() -> Self {
        Self
    }

    // ---- Timestamp ----

    /// Mirrors AbstractAdapter.get_uniformized_timestamp
    pub fn get_uniformized_timestamp(&self, ts: i64) -> i64 {
        uniformize_timestamp(ts)
    }

    // ---- Candles (OHLCV) ----

    /// Mirrors CCXTAdapter.adapt_ohlcv
    /// Each raw element is [timestamp_ms, open, high, low, close, volume]
    pub fn adapt_ohlcv(
        &self,
        raw: &serde_json::Value,
        time_frame: &TimeFrame,
    ) -> ExchangeResult<Vec<Candle>> {
        let arr = raw.as_array()
            .ok_or_else(|| OctoBotExchangeError::AdapterError("OHLCV is not an array".into()))?;
        let candle_secs = time_frame.to_seconds();
        arr.iter().map(|row| {
            let row = row.as_array()
                .ok_or_else(|| OctoBotExchangeError::AdapterError("OHLCV row is not an array".into()))?;
            let ts_ms = row.get(0).and_then(|v| v.as_i64()).unwrap_or(0);
            let ts = self.get_uniformized_timestamp(ts_ms);
            let aligned = ts - (ts % candle_secs);
            Ok(Candle {
                timestamp: aligned,
                open: row.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0),
                high: row.get(2).and_then(|v| v.as_f64()).unwrap_or(0.0),
                low:  row.get(3).and_then(|v| v.as_f64()).unwrap_or(0.0),
                close: row.get(4).and_then(|v| v.as_f64()).unwrap_or(0.0),
                volume: row.get(5).and_then(|v| v.as_f64()).unwrap_or(0.0),
            })
        }).collect()
    }

    // ---- Ticker ----

    pub fn adapt_ticker(&self, raw: &serde_json::Value) -> ExchangeResult<Ticker> {
        let ts_ms = raw["timestamp"].as_i64().unwrap_or(0);
        Ok(Ticker {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            timestamp: self.get_uniformized_timestamp(ts_ms),
            high: raw["high"].as_f64(),
            low: raw["low"].as_f64(),
            bid: raw["bid"].as_f64(),
            bid_volume: raw["bidVolume"].as_f64(),
            ask: raw["ask"].as_f64(),
            ask_volume: raw["askVolume"].as_f64(),
            vwap: raw["vwap"].as_f64(),
            open: raw["open"].as_f64(),
            close: raw["close"].as_f64(),
            last: raw["last"].as_f64(),
            change: raw["change"].as_f64(),
            percentage: raw["percentage"].as_f64(),
            base_volume: raw["baseVolume"].as_f64(),
            quote_volume: raw["quoteVolume"].as_f64(),
            mark_price: raw["markPrice"].as_f64(),
        })
    }

    // ---- Order book ----

    pub fn adapt_order_book(&self, raw: &serde_json::Value) -> ExchangeResult<OrderBook> {
        let ts_ms = raw["timestamp"].as_i64().unwrap_or_else(|| {
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as i64)
                .unwrap_or(0)
        });
        let coerce_f64 = |v: &serde_json::Value| -> Option<f64> {
            v.as_f64().or_else(|| v.as_str().and_then(|s| s.parse().ok()))
        };
        let parse_side = |key: &str| -> Vec<[f64; 2]> {
            raw[key].as_array().map(|arr| {
                arr.iter().filter_map(|entry| {
                    let row = entry.as_array()?;
                    let price = coerce_f64(row.get(0)?)?;
                    let qty = coerce_f64(row.get(1)?)?;
                    Some([price, qty])
                }).collect()
            }).unwrap_or_default()
        };
        Ok(OrderBook {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            timestamp: self.get_uniformized_timestamp(ts_ms),
            bids: parse_side("bids"),
            asks: parse_side("asks"),
        })
    }

    // ---- Orders ----

    /// Mirrors CCXTAdapter.adapt_orders
    pub fn adapt_orders(
        &self,
        raw: &serde_json::Value,
        symbol: Option<&str>,
        cancelled_only: bool,
    ) -> ExchangeResult<Vec<Order>> {
        let arr = raw.as_array()
            .ok_or_else(|| OctoBotExchangeError::AdapterError("orders is not an array".into()))?;
        let orders: ExchangeResult<Vec<Order>> = arr.iter()
            .map(|o| self.adapt_order(o, symbol))
            .collect();
        let orders = orders?;
        if cancelled_only {
            Ok(orders.into_iter()
                .filter(|o| o.status == OrderStatus::Canceled)
                .collect())
        } else {
            Ok(orders)
        }
    }

    /// Mirrors CCXTAdapter.adapt_order (fix_order + parse_order)
    pub fn adapt_order(&self, raw: &serde_json::Value, symbol: Option<&str>) -> ExchangeResult<Order> {
        let ts_ms = raw["timestamp"].as_i64().unwrap_or(0);
        let side_str = raw["side"].as_str().unwrap_or("buy");
        let side = TradeOrderSide::from_str(side_str).unwrap_or(TradeOrderSide::Buy);
        let type_str = raw["type"].as_str().unwrap_or("limit");

        let order_type = self.parse_order_type(type_str, &side, raw);

        let fee = raw.get("fee").filter(|v| !v.is_null()).map(|f| self.adapt_fee(f));

        let amount = raw["amount"].as_f64().unwrap_or(0.0);
        let filled = raw["filled"].as_f64().unwrap_or(0.0);
        let remaining = raw["remaining"].as_f64()
            .or_else(|| Some(amount - filled))
            .unwrap_or(0.0)
            .max(0.0);

        Ok(Order {
            id: raw["id"].as_str().unwrap_or("").to_string(),
            exchange_id: raw["id"].as_str().map(|s| s.to_string()),
            timestamp: self.get_uniformized_timestamp(ts_ms),
            symbol: raw["symbol"].as_str()
                .or(symbol)
                .unwrap_or("")
                .to_string(),
            order_type,
            side,
            price: raw["price"].as_f64(),
            amount,
            filled,
            remaining,
            cost: raw["cost"].as_f64(),
            average: raw["average"].as_f64(),
            status: self.parse_order_status(raw["status"].as_str()),
            fee,
            stop_price: raw["stopPrice"].as_f64(),
            stop_loss_price: raw["stopLossPrice"].as_f64(),
            take_profit_price: raw["takeProfitPrice"].as_f64(),
            reduce_only: raw["reduceOnly"].as_bool().unwrap_or(false),
            trigger_above: raw["triggerAbove"].as_bool(),
            tag: raw["tag"].as_str().map(|s| s.to_string()),
            quantity_currency: raw["quantityCurrency"].as_str().map(|s| s.to_string()),
            extra: raw["info"].as_object()
                .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
                .unwrap_or_default(),
        })
    }

    // ---- Trades ----

    pub fn adapt_trades(
        &self,
        raw: &serde_json::Value,
        symbol: Option<&str>,
    ) -> ExchangeResult<Vec<Trade>> {
        let arr = raw.as_array()
            .ok_or_else(|| OctoBotExchangeError::AdapterError("trades is not an array".into()))?;
        arr.iter().map(|t| self.adapt_trade(t, symbol)).collect()
    }

    pub fn adapt_trade(&self, raw: &serde_json::Value, symbol: Option<&str>) -> ExchangeResult<Trade> {
        let ts_ms = raw["timestamp"].as_i64().unwrap_or(0);
        let side_str = raw["side"].as_str().unwrap_or("buy");
        Ok(Trade {
            id: raw["id"].as_str().map(|s| s.to_string()),
            exchange_trade_id: raw["id"].as_str().map(|s| s.to_string()),
            order_id: raw["order"].as_str().map(|s| s.to_string()),
            timestamp: self.get_uniformized_timestamp(ts_ms),
            symbol: raw["symbol"].as_str().or(symbol).unwrap_or("").to_string(),
            side: TradeOrderSide::from_str(side_str).unwrap_or(TradeOrderSide::Buy),
            price: raw["price"].as_f64().unwrap_or(0.0),
            amount: raw["amount"].as_f64().unwrap_or(0.0),
            cost: raw["cost"].as_f64(),
            fee: raw.get("fee").filter(|v| !v.is_null()).map(|f| self.adapt_fee(f)),
            taker_or_maker: raw["takerOrMaker"].as_str().map(|s| s.to_string()),
        })
    }

    // ---- Balance ----

    /// Mirrors CCXTAdapter.adapt_balance
    pub fn adapt_balance(&self, raw: &serde_json::Value) -> ExchangeResult<Balance> {
        let mut result = Balance::new();
        if let Some(obj) = raw.as_object() {
            for (currency, account) in obj {
                // Skip meta-keys (total, free, used, info, timestamp, datetime)
                if matches!(
                    currency.as_str(),
                    "total" | "free" | "used" | "info" | "timestamp" | "datetime"
                ) {
                    continue;
                }
                if let Some(acct) = account.as_object() {
                    let free = Self::decimal_from_json(&acct.get("free").unwrap_or(&serde_json::Value::Null));
                    let used = Self::decimal_from_json(&acct.get("used").unwrap_or(&serde_json::Value::Null));
                    let total = Self::decimal_from_json(&acct.get("total").unwrap_or(&serde_json::Value::Null));
                    result.insert(currency.clone(), CurrencyBalance { free, used, total });
                }
            }
        }
        Ok(result)
    }

    // ---- Position ----

    pub fn adapt_position(&self, raw: &serde_json::Value) -> ExchangeResult<Position> {
        let ts_ms = raw["timestamp"].as_i64().unwrap_or(0);
        let side_str = raw["side"].as_str().unwrap_or("both");
        let side = match side_str {
            "long" => PositionSide::Long,
            "short" => PositionSide::Short,
            _ => PositionSide::Both,
        };
        let margin_type = raw["marginType"].as_str()
            .or_else(|| raw["marginMode"].as_str())
            .and_then(|m| MarginType::from_str(m));

        Ok(Position {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            timestamp: self.get_uniformized_timestamp(ts_ms),
            side,
            status: PositionStatus::Open,
            margin_type,
            leverage: raw["leverage"].as_f64(),
            contracts: raw["contracts"].as_f64(),
            contract_size: raw["contractSize"].as_f64(),
            entry_price: raw["entryPrice"].as_f64(),
            mark_price: raw["markPrice"].as_f64(),
            liquidation_price: raw["liquidationPrice"].as_f64(),
            unrealized_pnl: raw["unrealizedPnl"].as_f64(),
            realized_pnl: raw["realizedPnl"].as_f64(),
            closing_fee: None,
            notional: raw["notional"].as_f64(),
            initial_margin: raw["initialMargin"].as_f64(),
            maintenance_margin: raw["maintenanceMargin"].as_f64(),
            margin_ratio: raw["marginRatio"].as_f64(),
            collateral: raw["collateral"].as_f64(),
            position_mode: None,
            maintenance_margin_rate: raw["maintenanceMarginPercentage"].as_f64(),
        })
    }

    pub fn adapt_positions(
        &self,
        raw: &serde_json::Value,
    ) -> ExchangeResult<Vec<Position>> {
        let arr = raw.as_array()
            .ok_or_else(|| OctoBotExchangeError::AdapterError("positions is not an array".into()))?;
        arr.iter().map(|p| self.adapt_position(p)).collect()
    }

    // ---- Market status ----

    pub fn adapt_market_status(&self, raw: &serde_json::Value) -> ExchangeResult<MarketStatus> {
        let limits = {
            let lim = &raw["limits"];
            MarketLimits {
                amount_min: lim["amount"]["min"].as_f64(),
                amount_max: lim["amount"]["max"].as_f64(),
                price_min: lim["price"]["min"].as_f64(),
                price_max: lim["price"]["max"].as_f64(),
                cost_min: lim["cost"]["min"].as_f64(),
                cost_max: lim["cost"]["max"].as_f64(),
            }
        };
        let precision = {
            let prec = &raw["precision"];
            MarketPrecision {
                price: prec["price"].as_f64(),
                amount: prec["amount"].as_f64(),
                cost: prec["cost"].as_f64(),
            }
        };
        Ok(MarketStatus {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            id: raw["id"].as_str().map(|s| s.to_string()),
            currency: raw["base"].as_str().map(|s| s.to_string()),
            market: raw["quote"].as_str().map(|s| s.to_string()),
            active: raw["active"].as_bool().unwrap_or(true),
            precision,
            limits,
            contract_size: raw["contractSize"].as_f64(),
            market_type: raw["type"].as_str().map(|s| s.to_string()),
            taker_fee: raw["taker"].as_f64(),
            maker_fee: raw["maker"].as_f64(),
            raw: raw.as_object()
                .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
                .unwrap_or_default(),
        })
    }

    // ---- Funding rate ----

    pub fn adapt_funding_rate(&self, raw: &serde_json::Value) -> ExchangeResult<FundingRate> {
        Ok(FundingRate {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            funding_rate: raw["fundingRate"].as_f64(),
            last_funding_time: raw["lastFundingTime"].as_i64()
                .map(|ts| self.get_uniformized_timestamp(ts)),
            next_funding_time: raw["nextFundingTimestamp"].as_i64()
                .map(|ts| self.get_uniformized_timestamp(ts)),
            predicted_funding_rate: raw["predictedFundingRate"].as_f64(),
        })
    }

    // ---- Leverage ----

    pub fn adapt_leverage(&self, raw: &serde_json::Value) -> ExchangeResult<LeverageInfo> {
        Ok(LeverageInfo {
            symbol: raw["symbol"].as_str().unwrap_or("").to_string(),
            leverage: raw["leverage"].as_f64(),
            margin_mode: raw["marginMode"].as_str().map(|s| s.to_string()),
            long_leverage: raw["longLeverage"].as_f64(),
            short_leverage: raw["shortLeverage"].as_f64(),
        })
    }

    // ---- Helpers ----

    fn adapt_fee(&self, raw: &serde_json::Value) -> Fee {
        Fee {
            cost: Self::decimal_from_json(&raw["cost"]),
            currency: raw["currency"].as_str().map(|s| s.to_string()),
            rate: raw["rate"].as_f64(),
            fee_type: raw["type"].as_str().map(|s| s.to_string()),
            is_from_exchange: true,
            exchange_original_cost: {
                let v = &raw["cost"];
                if v.is_null() { None } else { Some(Self::decimal_from_json(v)) }
            },
        }
    }

    fn decimal_from_json(v: &serde_json::Value) -> Decimal {
        match v {
            serde_json::Value::Number(n) => {
                n.as_f64()
                    .and_then(|f| Decimal::from_f64(f))
                    .unwrap_or_default()
            }
            serde_json::Value::String(s) => {
                s.parse().unwrap_or_default()
            }
            _ => Decimal::ZERO,
        }
    }

    fn parse_order_status(&self, raw: Option<&str>) -> OrderStatus {
        match raw {
            Some("open") => OrderStatus::Open,
            Some("closed") => OrderStatus::Filled,
            Some("canceled") | Some("cancelled") => OrderStatus::Canceled,
            Some("expired") => OrderStatus::Expired,
            Some("rejected") => OrderStatus::Rejected,
            Some("partially_filled") => OrderStatus::PartiallyFilled,
            Some("canceling") => OrderStatus::PendingCancel,
            _ => OrderStatus::Unknown,
        }
    }

    fn parse_order_type(
        &self,
        type_str: &str,
        side: &TradeOrderSide,
        raw: &serde_json::Value,
    ) -> TraderOrderType {
        // Stop / take profit detection via extra fields
        if raw["stopPrice"].is_number() || raw["stopLossPrice"].is_number() {
            return match side {
                TradeOrderSide::Buy => TraderOrderType::StopLoss,
                TradeOrderSide::Sell => TraderOrderType::StopLoss,
            };
        }
        match (type_str, side) {
            ("limit", TradeOrderSide::Buy) => TraderOrderType::BuyLimit,
            ("limit", TradeOrderSide::Sell) => TraderOrderType::SellLimit,
            ("market", TradeOrderSide::Buy) => TraderOrderType::BuyMarket,
            ("market", TradeOrderSide::Sell) => TraderOrderType::SellMarket,
            ("stop_loss", _) | ("stop", _) => TraderOrderType::StopLoss,
            ("stop_loss_limit", _) | ("stop_limit", _) => TraderOrderType::StopLossLimit,
            ("take_profit", _) => TraderOrderType::TakeProfit,
            ("take_profit_limit", _) => TraderOrderType::TakeProfitLimit,
            ("trailing_stop", _) => TraderOrderType::TrailingStop,
            ("trailing_stop_limit", _) => TraderOrderType::TrailingStopLimit,
            _ => TraderOrderType::Unknown,
        }
    }

    // ---- Quantity adaptation for futures contract size ----

    /// Mirrors CCXTAdapter.adapt_quantities_with_contract_size
    /// Adjusts order amount when the exchange uses contracts instead of base currency units.
    pub fn adapt_quantities_with_contract_size(
        &self,
        order: &mut Order,
        contract_size: Option<f64>,
    ) {
        if let Some(size) = contract_size {
            if size > 0.0 && size != 1.0 {
                order.amount /= size;
                order.filled /= size;
                order.remaining /= size;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_adapt_ticker() {
        let adapter = CcxtAdapter::new();
        let raw = json!({
            "symbol": "BTC/USDT",
            "timestamp": 1_700_000_000_000i64,
            "last": 50000.0,
            "bid": 49999.0,
            "ask": 50001.0,
        });
        let ticker = adapter.adapt_ticker(&raw).unwrap();
        assert_eq!(ticker.symbol, "BTC/USDT");
        assert_eq!(ticker.last, Some(50000.0));
        // ms -> s
        assert_eq!(ticker.timestamp, 1_700_000_000);
    }

    #[test]
    fn test_adapt_order_book() {
        let adapter = CcxtAdapter::new();
        let raw = json!({
            "symbol": "BTC/USDT",
            "timestamp": 1_700_000_000_000i64,
            "bids": [[50000.0, 1.0], [49999.0, 2.0]],
            "asks": [[50001.0, 0.5]],
        });
        let ob = adapter.adapt_order_book(&raw).unwrap();
        assert_eq!(ob.bids.len(), 2);
        assert_eq!(ob.best_bid(), Some(50000.0));
    }

    #[test]
    fn test_adapt_ohlcv() {
        let adapter = CcxtAdapter::new();
        let raw = json!([
            [1_700_000_000_000i64, 49000.0, 51000.0, 48000.0, 50000.0, 1234.5],
        ]);
        let candles = adapter.adapt_ohlcv(&raw, &TimeFrame::OneHour).unwrap();
        assert_eq!(candles.len(), 1);
        assert_eq!(candles[0].close, 50000.0);
        // Aligned to hour boundary
        assert_eq!(candles[0].timestamp % 3600, 0);
    }

    #[test]
    fn test_adapt_order() {
        let adapter = CcxtAdapter::new();
        let raw = json!({
            "id": "order123",
            "timestamp": 1_700_000_000_000i64,
            "symbol": "BTC/USDT",
            "type": "limit",
            "side": "buy",
            "price": 49000.0,
            "amount": 0.1,
            "filled": 0.0,
            "remaining": 0.1,
            "status": "open",
            "fee": null,
            "info": {},
        });
        let order = adapter.adapt_order(&raw, None).unwrap();
        assert_eq!(order.id, "order123");
        assert_eq!(order.order_type, TraderOrderType::BuyLimit);
        assert!(order.is_open());
    }

    #[test]
    fn test_adapt_balance() {
        let adapter = CcxtAdapter::new();
        let raw = json!({
            "BTC": { "free": 1.5, "used": 0.5, "total": 2.0 },
            "USDT": { "free": 10000.0, "used": 0.0, "total": 10000.0 },
            "info": {},
            "free": {},
            "used": {},
            "total": {},
        });
        let balance = adapter.adapt_balance(&raw).unwrap();
        assert!(balance.contains_key("BTC"));
        assert!(!balance.contains_key("info"));
        assert_eq!(balance["BTC"].total, Decimal::from_f64(2.0).unwrap());
    }
}
