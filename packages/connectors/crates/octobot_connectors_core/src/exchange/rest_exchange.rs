// RestExchange: high-level wrapper around CcxtConnector with per-exchange config flags.
// Translated from packages/trading/octobot_trading/exchanges/types/rest_exchange.py (1406 lines).
//
// In the Python code, RestExchange is a class that exchange tentacles inherit from
// to override class-level constants. Here, RestExchangeConfig is a struct of those constants
// and RestExchange wraps any Exchange implementation plus the config.
//
// Exchange tentacle implementors should:
//   1. Create a RestExchangeConfig with the appropriate flags
//   2. Override error-detection string lists
//   3. Wrap a CcxtConnector

use std::collections::HashMap;
use async_trait::async_trait;
use rust_decimal::Decimal;

use crate::config::ExchangeConfig;
use crate::connector::{Exchange, ccxt::CcxtConnector};
use crate::enums::{ExchangeTypes, OrderStatus, TimeFrame, TradeOrderSide, TraderOrderType};
use crate::error::{ExchangeResult, OctoBotExchangeError};
use crate::types::{
    Balance, Candle, FundingRate, LeverageInfo, MarketStatus, Order, OrderBook,
    Position, Ticker, Trade, Transaction,
};

/// All per-exchange configuration flags extracted from Python RestExchange class constants.
/// Mirrors the class-level bool/int constants in rest_exchange.py.
#[derive(Debug, Clone)]
pub struct RestExchangeConfig {
    // ---- Market status ----
    /// Set True when get_fixed_market_status should be called (mirrors FIX_MARKET_STATUS)
    pub fix_market_status: bool,
    /// Remove invalid price limits when fixing market status
    pub remove_market_status_price_limits: bool,
    /// Adapt amounts for contract size
    pub adapt_market_status_for_contract_size: bool,
    /// Include disabled symbols in available symbols list
    pub include_disabled_symbols_in_available_symbols: bool,

    // ---- Orders ----
    /// Use create_market_buy_order_with_cost for market buy orders
    pub enable_spot_buy_market_with_cost: bool,
    /// Fetch fees from recent trades (get_order doesn't include fees)
    pub require_order_fees_from_trades: bool,
    /// get_closed_orders not supported; use recent trades instead
    pub require_closed_orders_from_recent_trades: bool,
    /// get_my_recent_trades should use get_closed_orders
    pub allow_trades_from_closed_orders: bool,
    /// Exchange may return incomplete last candle
    pub dump_incomplete_last_candle: bool,
    /// Empty position returns None; use mocked empty position
    pub requires_mocked_empty_position: bool,
    /// get_positions() returns no empty positions; use get_position()
    pub requires_symbol_for_empty_position: bool,
    /// get_order() can return None during order creation
    pub expect_possible_order_not_found_during_order_creation: bool,

    // ---- Authentication ----
    /// Even public APIs require auth
    pub always_requires_authentication: bool,
    /// Loading markets can trigger auth calls when creds are set
    pub can_make_authenticated_requests_when_loading_markets: bool,
    /// Exchange details must be fetched before starting
    pub has_fetched_details: bool,

    // ---- Futures ----
    pub supports_set_margin_type: bool,
    pub supports_set_margin_type_on_open_positions: bool,
    pub mark_price_in_position: bool,
    pub mark_price_in_ticker: bool,
    pub funding_with_mark_price: bool,
    pub funding_in_ticker: bool,

    // ---- OHLCV ----
    /// Exchange skips candles when no trades occurred
    pub is_skipping_empty_candles_in_ohlcv_fetch: bool,
    pub max_fetched_ohlcv_count: Option<usize>,

    // ---- Stop loss price parameter names for ccxt ----
    pub stop_loss_edit_price_param: String,
    pub stop_loss_create_price_param: String,

    // ---- Withdrawal ----
    pub withdraw_network_param_key: String,

    // ---- Error detection substrings (mirrors EXCHANGE_*_ERRORS lists) ----
    pub order_not_found_errors: Vec<String>,
    pub permission_errors: Vec<String>,
    pub missing_funds_errors: Vec<String>,
    pub compliancy_errors: Vec<String>,
}

impl Default for RestExchangeConfig {
    fn default() -> Self {
        Self {
            fix_market_status: false,
            remove_market_status_price_limits: false,
            adapt_market_status_for_contract_size: false,
            include_disabled_symbols_in_available_symbols: false,
            enable_spot_buy_market_with_cost: false,
            require_order_fees_from_trades: false,
            require_closed_orders_from_recent_trades: false,
            allow_trades_from_closed_orders: false,
            dump_incomplete_last_candle: false,
            requires_mocked_empty_position: false,
            requires_symbol_for_empty_position: false,
            expect_possible_order_not_found_during_order_creation: false,
            always_requires_authentication: false,
            can_make_authenticated_requests_when_loading_markets: false,
            has_fetched_details: false,
            supports_set_margin_type: true,
            supports_set_margin_type_on_open_positions: true,
            mark_price_in_position: false,
            mark_price_in_ticker: false,
            funding_with_mark_price: false,
            funding_in_ticker: false,
            is_skipping_empty_candles_in_ohlcv_fetch: false,
            max_fetched_ohlcv_count: None,
            stop_loss_edit_price_param: "stopLossPrice".to_string(),
            stop_loss_create_price_param: "stopLossPrice".to_string(),
            withdraw_network_param_key: "network".to_string(),
            order_not_found_errors: vec![],
            permission_errors: vec![],
            missing_funds_errors: vec![],
            compliancy_errors: vec![],
        }
    }
}

/// RestExchange: wraps a CcxtConnector with exchange-specific configuration flags.
/// This is what exchange tentacle implementations instantiate.
pub struct RestExchange {
    pub rest_config: RestExchangeConfig,
    pub connector: CcxtConnector,
}

impl RestExchange {
    pub fn new(exchange_config: ExchangeConfig, rest_config: RestExchangeConfig) -> Self {
        let mut connector = CcxtConnector::new(exchange_config);
        // Propagate config flags to the connector
        connector.fix_market_status = rest_config.fix_market_status;
        connector.remove_market_status_price_limits = rest_config.remove_market_status_price_limits;
        connector.adapt_market_status_for_contract_size = rest_config.adapt_market_status_for_contract_size;
        connector.require_order_fees_from_trades = rest_config.require_order_fees_from_trades;
        connector.require_closed_orders_from_recent_trades = rest_config.require_closed_orders_from_recent_trades;
        connector.dump_incomplete_last_candle = rest_config.dump_incomplete_last_candle;
        connector.supports_set_margin_type = rest_config.supports_set_margin_type;
        connector.mark_price_in_position = rest_config.mark_price_in_position;
        connector.mark_price_in_ticker = rest_config.mark_price_in_ticker;
        connector.funding_in_ticker = rest_config.funding_in_ticker;
        connector.max_fetched_ohlcv_count = rest_config.max_fetched_ohlcv_count;
        connector.is_skipping_empty_candles = rest_config.is_skipping_empty_candles_in_ohlcv_fetch;
        connector.order_not_found_errors = rest_config.order_not_found_errors.clone();
        connector.permission_errors = rest_config.permission_errors.clone();
        connector.missing_funds_errors = rest_config.missing_funds_errors.clone();
        connector.compliancy_errors = rest_config.compliancy_errors.clone();

        Self { rest_config, connector }
    }

    /// Returns a reference to the inner connector.
    pub fn connector(&self) -> &CcxtConnector {
        &self.connector
    }

    /// Mutable reference to the inner connector.
    pub fn connector_mut(&mut self) -> &mut CcxtConnector {
        &mut self.connector
    }

    // ---- Error detection (mirrors RestExchange.is_*_error methods) ----

    pub fn is_order_not_found_error(&self, error: &OctoBotExchangeError) -> bool {
        self.connector.is_order_not_found_error(&error.to_string())
    }

    pub fn is_api_permission_error(&self, error: &OctoBotExchangeError) -> bool {
        self.connector.is_api_permission_error(&error.to_string())
    }

    pub fn is_exchange_rules_compliancy_error(&self, error: &OctoBotExchangeError) -> bool {
        self.connector.is_exchange_rules_compliancy_error(&error.to_string())
    }

    pub fn is_missing_funds_error(&self, error: &OctoBotExchangeError) -> bool {
        self.connector.is_missing_funds_error(&error.to_string())
    }

    pub fn is_authentication_error(&self, error: &OctoBotExchangeError) -> bool {
        error.is_auth_error()
    }
}

/// Delegate all Exchange trait methods to the inner CcxtConnector.
#[async_trait]
impl Exchange for RestExchange {
    async fn initialize(&mut self) -> ExchangeResult<()> {
        self.connector.initialize().await
    }
    async fn stop(&mut self) -> ExchangeResult<()> {
        self.connector.stop().await
    }
    fn get_name(&self) -> &str { self.connector.get_name() }
    fn get_exchange_type(&self) -> ExchangeTypes { self.connector.get_exchange_type() }
    fn is_authenticated(&self) -> bool { self.connector.is_authenticated() }
    fn is_supporting_sandbox(&self) -> bool { self.connector.is_supporting_sandbox() }

    async fn load_markets(&mut self, reload: bool) -> ExchangeResult<HashMap<String, MarketStatus>> {
        self.connector.load_markets(reload).await
    }
    async fn get_market_status(&self, symbol: &str, price_example: Option<f64>, with_fixer: bool) -> ExchangeResult<MarketStatus> {
        self.connector.get_market_status(symbol, price_example, with_fixer).await
    }
    async fn get_symbol_prices(&self, symbol: &str, time_frame: TimeFrame, limit: Option<usize>, since: Option<i64>, params: HashMap<String, serde_json::Value>) -> ExchangeResult<Vec<Candle>> {
        self.connector.get_symbol_prices(symbol, time_frame, limit, since, params).await
    }
    async fn get_kline_price(&self, symbol: &str, time_frame: TimeFrame, params: HashMap<String, serde_json::Value>) -> ExchangeResult<Vec<Candle>> {
        self.connector.get_kline_price(symbol, time_frame, params).await
    }
    async fn get_order_book(&self, symbol: &str, limit: usize) -> ExchangeResult<OrderBook> {
        self.connector.get_order_book(symbol, limit).await
    }
    async fn get_recent_trades(&self, symbol: &str, limit: Option<usize>) -> ExchangeResult<Vec<Trade>> {
        self.connector.get_recent_trades(symbol, limit).await
    }
    async fn get_price_ticker(&self, symbol: &str) -> ExchangeResult<Ticker> {
        self.connector.get_price_ticker(symbol).await
    }
    async fn get_all_currencies_price_ticker(&self, symbols: Option<Vec<String>>) -> ExchangeResult<HashMap<String, Ticker>> {
        self.connector.get_all_currencies_price_ticker(symbols).await
    }
    async fn get_order(&self, exchange_order_id: &str, symbol: Option<&str>) -> ExchangeResult<Option<Order>> {
        self.connector.get_order(exchange_order_id, symbol).await
    }
    async fn get_all_orders(&self, symbol: Option<&str>, since: Option<i64>, limit: Option<usize>) -> ExchangeResult<Vec<Order>> {
        self.connector.get_all_orders(symbol, since, limit).await
    }
    async fn get_open_orders(&self, symbol: Option<&str>, since: Option<i64>, limit: Option<usize>) -> ExchangeResult<Vec<Order>> {
        self.connector.get_open_orders(symbol, since, limit).await
    }
    async fn get_closed_orders(&self, symbol: Option<&str>, since: Option<i64>, limit: Option<usize>) -> ExchangeResult<Vec<Order>> {
        self.connector.get_closed_orders(symbol, since, limit).await
    }
    async fn get_cancelled_orders(&self, symbol: Option<&str>, since: Option<i64>, limit: Option<usize>) -> ExchangeResult<Vec<Order>> {
        self.connector.get_cancelled_orders(symbol, since, limit).await
    }
    async fn get_my_recent_trades(&self, symbol: Option<&str>, since: Option<i64>, limit: Option<usize>) -> ExchangeResult<Vec<Trade>> {
        self.connector.get_my_recent_trades(symbol, since, limit).await
    }
    async fn create_order(&self, order_type: TraderOrderType, symbol: &str, quantity: Decimal, price: Option<Decimal>, stop_price: Option<Decimal>, side: Option<TradeOrderSide>, current_price: Option<Decimal>, reduce_only: bool, params: Option<HashMap<String, serde_json::Value>>) -> ExchangeResult<Option<Order>> {
        self.connector.create_order(order_type, symbol, quantity, price, stop_price, side, current_price, reduce_only, params).await
    }
    async fn cancel_order(&self, exchange_order_id: &str, symbol: &str, order_type: TraderOrderType) -> ExchangeResult<OrderStatus> {
        self.connector.cancel_order(exchange_order_id, symbol, order_type).await
    }
    async fn cancel_all_orders(&self, symbol: Option<&str>) -> ExchangeResult<()> {
        self.connector.cancel_all_orders(symbol).await
    }
    async fn edit_order(&self, exchange_order_id: &str, order_type: TraderOrderType, symbol: &str, quantity: f64, price: f64, stop_price: Option<f64>, side: Option<TradeOrderSide>, params: Option<HashMap<String, serde_json::Value>>) -> ExchangeResult<Order> {
        self.connector.edit_order(exchange_order_id, order_type, symbol, quantity, price, stop_price, side, params).await
    }
    async fn get_balance(&self, params: HashMap<String, serde_json::Value>) -> ExchangeResult<Balance> {
        self.connector.get_balance(params).await
    }
    async fn get_position(&self, symbol: &str) -> ExchangeResult<Option<Position>> {
        self.connector.get_position(symbol).await
    }
    async fn get_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>> {
        self.connector.get_positions(symbols).await
    }
    async fn get_closed_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>> {
        self.connector.get_closed_positions(symbols).await
    }
    async fn get_funding_rate(&self, symbol: &str) -> ExchangeResult<FundingRate> {
        self.connector.get_funding_rate(symbol).await
    }
    async fn get_mark_price(&self, symbol: &str) -> ExchangeResult<f64> {
        self.connector.get_mark_price(symbol).await
    }
    async fn get_symbol_leverage(&self, symbol: &str) -> ExchangeResult<LeverageInfo> {
        self.connector.get_symbol_leverage(symbol).await
    }
    async fn set_symbol_leverage(&self, symbol: &str, leverage: f64, params: Option<HashMap<String, serde_json::Value>>) -> ExchangeResult<LeverageInfo> {
        self.connector.set_symbol_leverage(symbol, leverage, params).await
    }
    async fn set_symbol_margin_type(&self, symbol: &str, isolated: bool, params: Option<HashMap<String, serde_json::Value>>) -> ExchangeResult<()> {
        self.connector.set_symbol_margin_type(symbol, isolated, params).await
    }
    async fn set_position_mode(&self, one_way: bool, symbol: Option<&str>) -> ExchangeResult<()> {
        self.connector.set_position_mode(one_way, symbol).await
    }
    async fn get_deposit_address(&self, currency: &str, network: Option<&str>) -> ExchangeResult<Option<String>> {
        self.connector.get_deposit_address(currency, network).await
    }
    async fn withdraw(&self, currency: &str, amount: Decimal, address: &str, tag: Option<&str>, network: Option<&str>, params: Option<HashMap<String, serde_json::Value>>) -> ExchangeResult<Transaction> {
        self.connector.withdraw(currency, amount, address, tag, network, params).await
    }
    fn get_fees(&self, symbol: &str) -> ExchangeResult<HashMap<String, f64>> {
        self.connector.get_fees(symbol)
    }
    fn get_exchange_current_time(&self) -> i64 { self.connector.get_exchange_current_time() }
    fn get_pair_from_exchange(&self, pair: &str) -> Option<String> { self.connector.get_pair_from_exchange(pair) }
    fn get_exchange_pair(&self, pair: &str) -> ExchangeResult<String> { self.connector.get_exchange_pair(pair) }
    fn get_available_symbols(&self, active_only: bool) -> Vec<String> { self.connector.get_available_symbols(active_only) }
    fn get_available_time_frames(&self) -> Vec<String> { self.connector.get_available_time_frames() }
    fn get_rate_limit(&self) -> f64 { self.connector.get_rate_limit() }
    fn is_order_not_found_error(&self, error_str: &str) -> bool { self.connector.is_order_not_found_error(error_str) }
    fn is_api_permission_error(&self, error_str: &str) -> bool { self.connector.is_api_permission_error(error_str) }
    fn is_exchange_rules_compliancy_error(&self, error_str: &str) -> bool { self.connector.is_exchange_rules_compliancy_error(error_str) }
    fn is_missing_funds_error(&self, error_str: &str) -> bool { self.connector.is_missing_funds_error(error_str) }
    fn is_authentication_error(&self, error_str: &str) -> bool {
        let lower = error_str.to_lowercase();
        lower.contains("auth") || lower.contains("apikey") || lower.contains("invalid key")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rest_exchange_config_defaults() {
        let cfg = RestExchangeConfig::default();
        assert!(!cfg.fix_market_status);
        assert!(cfg.supports_set_margin_type);
        assert!(cfg.order_not_found_errors.is_empty());
    }

    #[test]
    fn test_rest_exchange_creation() {
        let exchange_config = ExchangeConfig::new("bybit");
        let rest_config = RestExchangeConfig {
            fix_market_status: true,
            mark_price_in_ticker: true,
            order_not_found_errors: vec!["order not found".into()],
            ..Default::default()
        };
        let exchange = RestExchange::new(exchange_config, rest_config);
        assert_eq!(exchange.get_name(), "bybit");
        assert!(exchange.rest_config.fix_market_status);
        assert!(exchange.connector.fix_market_status);
    }
}
