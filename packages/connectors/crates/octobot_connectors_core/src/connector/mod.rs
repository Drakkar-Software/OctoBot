// Exchange connector trait and implementations.
// The connector layer wraps the ccxt Rust crate and normalises its output
// to OctoBot unified types via CcxtAdapter.
//
// Mirrors the Python hierarchy:
//   connectors/ccxt/ccxt_connector.py  →  ccxt module
//   connectors/ccxt/ccxt_adapter.py    →  adapter module
//   abstract_exchange.py (connector portion) → this mod

pub mod adapter;
pub mod ccxt;

use async_trait::async_trait;
use std::collections::HashMap;

use crate::enums::{ExchangeTypes, FutureContractType, MarginType, OrderStatus, PositionMode, TimeFrame, TradeOrderSide, TraderOrderType};
use crate::error::ExchangeResult;
use crate::types::{Balance, Candle, FundingRate, LeverageInfo, MarketStatus, Order, OrderBook, Position, Ticker, Trade, Transaction};
use rust_decimal::Decimal;

/// Central exchange abstraction.
/// Mirrors Python AbstractExchange and RestExchange combined into one trait.
/// Concrete implementations are CcxtConnector for live trading and a
/// simulator connector for backtesting.
#[async_trait(?Send)]
pub trait Exchange: Send + Sync {
    // ---- Lifecycle ----

    async fn initialize(&mut self) -> ExchangeResult<()>;
    async fn stop(&mut self) -> ExchangeResult<()>;

    // ---- Identity ----

    fn get_name(&self) -> &str;
    fn get_exchange_type(&self) -> ExchangeTypes;
    fn is_authenticated(&self) -> bool;
    fn is_supporting_sandbox(&self) -> bool { false }

    // ---- Market data (public) ----

    async fn load_markets(&mut self, reload: bool) -> ExchangeResult<HashMap<String, MarketStatus>>;
    async fn get_market_status(
        &self, symbol: &str,
        price_example: Option<f64>,
        with_fixer: bool,
    ) -> ExchangeResult<MarketStatus>;

    async fn get_symbol_prices(
        &self,
        symbol: &str,
        time_frame: TimeFrame,
        limit: Option<usize>,
        since: Option<i64>,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Vec<Candle>>;

    async fn get_kline_price(
        &self,
        symbol: &str,
        time_frame: TimeFrame,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Vec<Candle>>;

    async fn get_order_book(&self, symbol: &str, limit: usize) -> ExchangeResult<OrderBook>;

    async fn get_recent_trades(
        &self,
        symbol: &str,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Trade>>;

    async fn get_price_ticker(&self, symbol: &str) -> ExchangeResult<Ticker>;

    async fn get_all_currencies_price_ticker(
        &self,
        symbols: Option<Vec<String>>,
    ) -> ExchangeResult<HashMap<String, Ticker>>;

    // ---- Orders (authenticated) ----

    async fn get_order(
        &self,
        exchange_order_id: &str,
        symbol: Option<&str>,
    ) -> ExchangeResult<Option<Order>>;

    async fn get_all_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>>;

    async fn get_open_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>>;

    async fn get_closed_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>>;

    async fn get_cancelled_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>>;

    async fn get_my_recent_trades(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Trade>>;

    async fn create_order(
        &self,
        order_type: TraderOrderType,
        symbol: &str,
        quantity: Decimal,
        price: Option<Decimal>,
        stop_price: Option<Decimal>,
        side: Option<TradeOrderSide>,
        current_price: Option<Decimal>,
        reduce_only: bool,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<Option<Order>>;

    async fn cancel_order(
        &self,
        exchange_order_id: &str,
        symbol: &str,
        order_type: TraderOrderType,
    ) -> ExchangeResult<OrderStatus>;

    async fn cancel_all_orders(&self, symbol: Option<&str>) -> ExchangeResult<()>;

    async fn edit_order(
        &self,
        exchange_order_id: &str,
        order_type: TraderOrderType,
        symbol: &str,
        quantity: f64,
        price: f64,
        stop_price: Option<f64>,
        side: Option<TradeOrderSide>,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<Order>;

    // ---- Account (authenticated) ----

    async fn get_balance(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Balance>;

    // ---- Futures-specific (authenticated) ----

    async fn get_position(&self, symbol: &str) -> ExchangeResult<Option<Position>>;
    async fn get_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>>;
    async fn get_closed_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>>;
    async fn get_funding_rate(&self, symbol: &str) -> ExchangeResult<FundingRate>;
    async fn get_mark_price(&self, symbol: &str) -> ExchangeResult<f64>;

    async fn get_symbol_leverage(&self, symbol: &str) -> ExchangeResult<LeverageInfo>;
    async fn set_symbol_leverage(
        &self,
        symbol: &str,
        leverage: f64,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<LeverageInfo>;
    async fn set_symbol_margin_type(
        &self,
        symbol: &str,
        isolated: bool,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<()>;
    async fn set_position_mode(&self, one_way: bool, symbol: Option<&str>) -> ExchangeResult<()>;

    // ---- Transactions ----

    async fn get_deposit_address(
        &self,
        currency: &str,
        network: Option<&str>,
    ) -> ExchangeResult<Option<String>>;

    async fn withdraw(
        &self,
        currency: &str,
        amount: Decimal,
        address: &str,
        tag: Option<&str>,
        network: Option<&str>,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<Transaction>;

    // ---- Market info helpers ----

    fn get_fees(&self, symbol: &str) -> ExchangeResult<HashMap<String, f64>>;
    fn get_exchange_current_time(&self) -> i64;
    fn get_uniform_timestamp(&self, timestamp: i64) -> i64 { timestamp }
    fn get_pair_from_exchange(&self, pair: &str) -> Option<String>;
    fn get_exchange_pair(&self, pair: &str) -> ExchangeResult<String>;
    fn get_split_pair_from_exchange(&self, pair: &str) -> (String, String);
    fn get_pair_cryptocurrency(&self, pair: &str) -> String;
    fn get_available_symbols(&self, active_only: bool) -> Vec<String>;
    fn get_all_tradable_symbols(&self) -> Vec<String> { self.get_available_symbols(true) }
    fn get_alias_symbols(&self) -> Vec<String> { vec![] }
    fn get_available_time_frames(&self) -> Vec<String>;
    fn get_rate_limit(&self) -> f64;
    fn get_default_balance(&self) -> Balance { Balance::new() }
    fn get_supported_exchange_types(&self) -> Vec<ExchangeTypes>;
    fn uses_demo_trading_instead_of_sandbox(&self) -> bool { false }
    fn supports_fetching_balance(&self) -> bool { true }
    fn supports_native_edit_order(&self, order_type: &TraderOrderType) -> bool;
    fn supports_api_leverage_update(&self, _symbol: &str) -> bool { true }

    // ---- Futures contract helpers ----

    async fn get_funding_rate_history(
        &self,
        symbol: &str,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<FundingRate>>;

    async fn get_margin_type(&self, symbol: &str) -> ExchangeResult<MarginType>;
    async fn get_position_mode(&self, symbol: &str) -> ExchangeResult<PositionMode>;
    async fn get_maintenance_margin_rate(&self, symbol: &str) -> ExchangeResult<Decimal>;
    async fn get_leverage_tiers(&self, symbols: Option<Vec<String>>) -> ExchangeResult<serde_json::Value>;

    fn get_contract_type(&self, symbol: &str) -> Option<FutureContractType>;
    fn get_contract_size(&self, symbol: &str) -> Option<f64>;
    fn is_linear_symbol(&self, symbol: &str) -> bool;
    fn is_inverse_symbol(&self, symbol: &str) -> bool;
    fn is_expirable_symbol(&self, symbol: &str) -> bool;
    fn supports_trading_type(&self, _symbol: &str) -> bool { true }

    // ---- Authentication helpers ----

    async fn get_account_id(&self) -> ExchangeResult<String>;
    fn is_authenticated_request(&self, url: &str, method: &str, headers: &HashMap<String, String>, body: &str) -> bool;
    fn is_successfully_authenticated(&self) -> bool { self.is_authenticated() }
    fn get_max_orders_count(&self, _symbol: &str, _order_type: &TraderOrderType) -> usize { 0 }

    // ---- Error classification ----

    fn is_order_not_found_error(&self, _error_str: &str) -> bool { false }
    fn is_api_permission_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_rules_compliancy_error(&self, _error_str: &str) -> bool { false }
    fn is_missing_funds_error(&self, _error_str: &str) -> bool { false }
    fn is_authentication_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_closed_position_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_order_would_immediately_trigger_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_order_uncancellable(&self, _error_str: &str) -> bool { false }
    fn is_exchange_max_orders_for_market_reached_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_internal_sync_error(&self, _error_str: &str) -> bool { false }
    fn is_exchange_account_traded_symbol_permission_error(&self, _error_str: &str) -> bool { false }
    fn is_ip_whitelist_error(&self, _error_str: &str) -> bool { false }
}
