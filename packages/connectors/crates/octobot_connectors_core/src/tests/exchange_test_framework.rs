// Exchange integration test framework.
// Mirrors Python AbstractAuthenticatedExchangeTester.
// Each exchange implements ExchangeTestRunner and overrides config/assert methods.

use std::collections::HashMap;
use std::time::Duration;
use async_trait::async_trait;
use rust_decimal::Decimal;
use rust_decimal::prelude::*;

use crate::connector::Exchange;
use crate::enums::{ExchangeTypes, MarginType, OrderStatus, TimeFrame, TradeOrderSide, TraderOrderType};
use crate::error::{ExchangeResult, OctoBotExchangeError};
use crate::types::{Balance, Candle, Order, OrderBook, Position, Ticker, Trade};

// ---- Test configuration (mirrors class variables in AbstractAuthenticatedExchangeTester) ----

#[derive(Debug, Clone)]
pub struct ExchangeTestConfig {
    pub exchange_name: String,
    pub exchange_type: ExchangeTypes,
    pub order_currency: String,
    pub settlement_currency: String,
    pub symbol: String,
    pub time_frame: TimeFrame,
    /// % of portfolio to include in test orders
    pub order_size_pct: f64,
    /// % price difference from current price for limit/stop orders
    pub order_price_diff_pct: f64,
    pub allow_zero_maker_fees: bool,
    pub expect_missing_order_fees_due_to_recent_trades: bool,
    pub expect_missing_fee_in_cancelled_orders: bool,
    pub expect_possible_order_not_found_during_order_creation: bool,
    pub expect_not_supported_error_when_fetching_cancelled_orders: bool,
    pub converts_market_into_limit_orders: bool,
    pub open_orders_in_closed_orders: bool,
    pub cancelled_orders_in_closed_orders: bool,
    pub expect_fetch_order_to_be_available: bool,
    pub order_impacts_portfolio_free_balance: bool,
    pub market_fill_timeout: Duration,
    pub open_timeout: Duration,
    pub cancel_timeout: Duration,
    pub edit_timeout: Duration,
    pub recent_trades_update_timeout: Duration,
    pub order_in_open_and_cancelled_orders_timeout: Duration,
    pub min_portfolio_size: usize,
    pub expected_quote_min_order_size: f64,
    pub expect_balance_filter_by_market_status: bool,
    pub max_trade_usd_value: Decimal,
    pub min_trade_usd_value: Decimal,
    pub is_account_id_available: bool,
    pub is_broker_enabled_account: bool,
    pub supports_double_bundled_orders: bool,
    pub cancel_double_bundled_orders_together: bool,
    pub ignore_exchange_trade_id: bool,
    pub duplicate_trades_ratio: f64,
}

impl Default for ExchangeTestConfig {
    fn default() -> Self {
        Self {
            exchange_name: String::new(),
            exchange_type: ExchangeTypes::Spot,
            order_currency: "BTC".into(),
            settlement_currency: "USDT".into(),
            symbol: "BTC/USDT".into(),
            time_frame: TimeFrame::OneHour,
            order_size_pct: 10.0,
            order_price_diff_pct: 20.0,
            allow_zero_maker_fees: false,
            expect_missing_order_fees_due_to_recent_trades: false,
            expect_missing_fee_in_cancelled_orders: true,
            expect_possible_order_not_found_during_order_creation: false,
            expect_not_supported_error_when_fetching_cancelled_orders: false,
            converts_market_into_limit_orders: false,
            open_orders_in_closed_orders: false,
            cancelled_orders_in_closed_orders: false,
            expect_fetch_order_to_be_available: true,
            order_impacts_portfolio_free_balance: true,
            market_fill_timeout: Duration::from_secs(15),
            open_timeout: Duration::from_secs(15),
            cancel_timeout: Duration::from_secs(15),
            edit_timeout: Duration::from_secs(15),
            recent_trades_update_timeout: Duration::from_secs(15),
            order_in_open_and_cancelled_orders_timeout: Duration::from_secs(10),
            min_portfolio_size: 1,
            expected_quote_min_order_size: 1.0,
            expect_balance_filter_by_market_status: false,
            max_trade_usd_value: Decimal::from(8000),
            min_trade_usd_value: Decimal::from_str("0.1").unwrap(),
            is_account_id_available: true,
            is_broker_enabled_account: true,
            supports_double_bundled_orders: true,
            cancel_double_bundled_orders_together: true,
            ignore_exchange_trade_id: false,
            duplicate_trades_ratio: 0.0,
        }
    }
}

// ---- Test runner trait ----

/// Base trait for exchange integration tests.
/// Mirrors Python AbstractAuthenticatedExchangeTester.
///
/// To test an exchange:
///   1. Implement ExchangeTestRunner for a test struct
///   2. Call `run_*` methods from #[tokio::test] functions
///   3. Override config() to set exchange-specific expectations
#[async_trait(?Send)]
pub trait ExchangeTestRunner: Send + Sync {
    fn config(&self) -> &ExchangeTestConfig;
    async fn create_exchange(&self) -> Box<dyn Exchange>;

    // ---- Portfolio ----

    async fn run_test_get_portfolio(&self) {
        let exchange = self.create_exchange().await;
        let balance = exchange.get_balance(HashMap::new()).await
            .expect("get_balance failed");
        self.check_portfolio_content(&balance);
    }

    fn check_portfolio_content(&self, balance: &Balance) {
        let cfg = self.config();
        assert!(
            balance.len() >= cfg.min_portfolio_size,
            "Portfolio has {} assets, expected >= {}",
            balance.len(),
            cfg.min_portfolio_size,
        );
        let mut at_least_one_value = false;
        for (currency, values) in balance {
            assert!(values.free >= Decimal::ZERO, "{currency} free balance is negative");
            assert!(values.used >= Decimal::ZERO, "{currency} used balance is negative");
            assert!(
                values.total == values.free + values.used,
                "{currency} total != free + used"
            );
            if values.total > Decimal::ZERO {
                at_least_one_value = true;
            }
        }
        assert!(at_least_one_value, "No currency has any balance > 0");
        // No duplicate currencies
        assert_eq!(balance.len(), balance.keys().collect::<std::collections::HashSet<_>>().len());
    }

    // ---- Market data ----

    async fn run_test_get_symbol_prices(&self) {
        let exchange = self.create_exchange().await;
        let cfg = self.config();
        let candles = exchange
            .get_symbol_prices(&cfg.symbol, cfg.time_frame.clone(), Some(100), None, HashMap::new())
            .await
            .expect("get_symbol_prices failed");
        assert!(!candles.is_empty(), "Should return candles");
        self.check_candles_content(&candles);
    }

    fn check_candles_content(&self, candles: &[Candle]) {
        for candle in candles {
            assert!(candle.open > 0.0, "Candle open must be > 0");
            assert!(candle.high >= candle.low, "Candle high < low");
            assert!(candle.close > 0.0, "Candle close must be > 0");
            assert!(candle.volume >= 0.0, "Candle volume must be >= 0");
            assert!(candle.timestamp > 0, "Candle timestamp must be > 0");
        }
    }

    async fn run_test_get_order_book(&self) {
        let exchange = self.create_exchange().await;
        let ob = exchange
            .get_order_book(&self.config().symbol, 10)
            .await
            .expect("get_order_book failed");
        assert!(!ob.bids.is_empty(), "Order book has no bids");
        assert!(!ob.asks.is_empty(), "Order book has no asks");
        self.check_order_book_content(&ob);
    }

    fn check_order_book_content(&self, ob: &OrderBook) {
        assert!(ob.best_bid().is_some());
        assert!(ob.best_ask().is_some());
        let best_bid = ob.best_bid().unwrap();
        let best_ask = ob.best_ask().unwrap();
        assert!(best_bid < best_ask, "Best bid must be < best ask");
        for [price, qty] in &ob.bids {
            assert!(*price > 0.0, "Bid price must be > 0");
            assert!(*qty > 0.0, "Bid quantity must be > 0");
        }
        for [price, qty] in &ob.asks {
            assert!(*price > 0.0, "Ask price must be > 0");
            assert!(*qty > 0.0, "Ask quantity must be > 0");
        }
    }

    async fn run_test_get_recent_trades(&self) {
        let exchange = self.create_exchange().await;
        let trades = exchange
            .get_recent_trades(&self.config().symbol, Some(50))
            .await
            .expect("get_recent_trades failed");
        assert!(!trades.is_empty(), "Should return recent trades");
        for trade in &trades {
            assert!(trade.price > 0.0, "Trade price must be > 0");
            assert!(trade.amount > 0.0, "Trade amount must be > 0");
        }
    }

    // ---- Order management ----

    async fn run_test_create_and_cancel_limit_order(&self) {
        let exchange = self.create_exchange().await;
        let cfg = self.config();

        let ticker = exchange.get_price_ticker(&cfg.symbol).await
            .expect("get_price_ticker failed");
        let current_price = ticker.last_price().expect("No last price in ticker");
        let order_price = current_price * (1.0 - cfg.order_price_diff_pct / 100.0);
        let quantity = Decimal::from_f64(
            cfg.min_trade_usd_value.to_f64().unwrap_or(1.0) / order_price
        ).unwrap_or_default();

        let order = exchange.create_order(
            TraderOrderType::BuyLimit,
            &cfg.symbol,
            quantity,
            Some(Decimal::from_f64(order_price).unwrap_or_default()),
            None, None, None, false, None,
        ).await.expect("create_order failed");

        let order = order.expect("Created order should not be None");
        self.check_created_order(&order);
        assert!(order.is_open(), "Created order should be open");

        let status = exchange.cancel_order(&order.id, &cfg.symbol, TraderOrderType::BuyLimit)
            .await.expect("cancel_order failed");
        assert_eq!(status, OrderStatus::Canceled, "Order should be canceled");
    }

    fn check_created_order(&self, order: &Order) {
        assert!(!order.id.is_empty(), "Order ID must not be empty");
        assert!(!order.symbol.is_empty(), "Order symbol must not be empty");
        assert!(order.amount > 0.0, "Order amount must be > 0");
        assert!(order.timestamp > 0, "Order timestamp must be > 0");
    }

    async fn run_test_get_open_orders(&self) {
        let exchange = self.create_exchange().await;
        let orders = exchange.get_open_orders(Some(&self.config().symbol), None, None)
            .await.expect("get_open_orders failed");
        for order in &orders {
            assert!(order.is_open(), "All returned orders should be open");
        }
    }

    async fn run_test_get_closed_orders(&self) {
        let exchange = self.create_exchange().await;
        let orders = exchange.get_closed_orders(Some(&self.config().symbol), None, Some(50))
            .await.expect("get_closed_orders failed");
        for order in &orders {
            assert!(!matches!(order.status, crate::enums::OrderStatus::Open), "Closed orders must not be open");
        }
    }

    async fn run_test_get_my_recent_trades(&self) {
        let exchange = self.create_exchange().await;
        let trades = exchange.get_my_recent_trades(
            Some(&self.config().symbol), None, Some(50)
        ).await;
        // Accepting NotSupported gracefully
        match trades {
            Ok(trades) => {
                for trade in &trades {
                    assert!(trade.price > 0.0, "Trade price must be > 0");
                }
            }
            Err(OctoBotExchangeError::NotSupported(_)) => {}
            Err(e) => panic!("Unexpected error in get_my_recent_trades: {e}"),
        }
    }

    async fn run_test_get_cancelled_orders(&self) {
        let exchange = self.create_exchange().await;
        let cfg = self.config();
        let result = exchange.get_cancelled_orders(Some(&cfg.symbol), None, Some(50)).await;
        match result {
            Ok(_) => {}
            Err(OctoBotExchangeError::NotSupported(_))
            if cfg.expect_not_supported_error_when_fetching_cancelled_orders => {}
            Err(e) => panic!("Unexpected error in get_cancelled_orders: {e}"),
        }
    }

    async fn run_test_create_and_fill_market_order(&self) {
        let exchange = self.create_exchange().await;
        let cfg = self.config();

        let ticker = exchange.get_price_ticker(&cfg.symbol).await.unwrap();
        let price = ticker.last_price().unwrap();
        let quantity = Decimal::from_f64(
            cfg.min_trade_usd_value.to_f64().unwrap_or(1.0) / price
        ).unwrap_or_default();

        let order = exchange.create_order(
            TraderOrderType::BuyMarket,
            &cfg.symbol,
            quantity,
            None, None, None, None, false, None,
        ).await.expect("create_market_order failed");

        let order = order.expect("Market order should not be None");
        assert!(!order.id.is_empty());
    }

    async fn run_test_edit_order(&self) {
        // Only run if edit is expected to work on this exchange
        // Most exchanges require a specific order to edit; default is a no-op pass
    }
}

// ---- Futures test framework (extends ExchangeTestRunner) ----

/// Mirrors AbstractAuthenticatedFutureExchangeTester
#[async_trait(?Send)]
pub trait FuturesExchangeTestRunner: ExchangeTestRunner {
    fn inverse_symbol(&self) -> Option<&str> { None }
    fn supports_get_leverage(&self) -> bool { true }
    fn supports_get_position(&self) -> bool { true }
    fn supports_empty_position_set_margin_type(&self) -> bool { true }

    async fn run_test_get_positions(&self) {
        let exchange = self.create_exchange().await;
        let positions = exchange.get_positions(None).await
            .expect("get_positions failed");
        for position in &positions {
            self.check_position_content(position);
        }
    }

    fn check_position_content(&self, position: &Position) {
        assert!(!position.symbol.is_empty(), "Position symbol must not be empty");
        assert!(position.timestamp > 0, "Position timestamp must be > 0");
    }

    async fn run_test_get_and_set_leverage(&self) {
        let exchange = self.create_exchange().await;
        let symbol = &self.config().symbol;

        if self.supports_get_leverage() {
            let leverage = exchange.get_symbol_leverage(symbol).await;
            match leverage {
                Ok(lev) => {
                    assert_eq!(lev.symbol, *symbol);
                }
                Err(OctoBotExchangeError::NotSupported(_)) => {}
                Err(e) => panic!("Unexpected error in get_symbol_leverage: {e}"),
            }
        }

        // Set to 1x (safe default)
        let result = exchange.set_symbol_leverage(symbol, 1.0, None).await;
        match result {
            Ok(_) => {}
            Err(OctoBotExchangeError::NotSupported(_)) => {}
            Err(e) => panic!("Unexpected error in set_symbol_leverage: {e}"),
        }
    }

    async fn run_test_set_margin_type(&self) {
        let exchange = self.create_exchange().await;
        let symbol = &self.config().symbol;

        // Try both margin types
        for isolated in [false, true] {
            let result = exchange.set_symbol_margin_type(symbol, isolated, None).await;
            match result {
                Ok(_) => {}
                Err(OctoBotExchangeError::NotSupported(_)) => {}
                Err(e) => panic!("Unexpected error in set_symbol_margin_type(isolated={isolated}): {e}"),
            }
        }
    }

    async fn run_test_get_funding_rate(&self) {
        let exchange = self.create_exchange().await;
        let result = exchange.get_funding_rate(&self.config().symbol).await;
        match result {
            Ok(funding) => {
                assert!(!funding.symbol.is_empty());
            }
            Err(OctoBotExchangeError::NotSupported(_)) => {}
            Err(e) => panic!("Unexpected error in get_funding_rate: {e}"),
        }
    }

    async fn run_test_get_mark_price(&self) {
        let exchange = self.create_exchange().await;
        let result = exchange.get_mark_price(&self.config().symbol).await;
        match result {
            Ok(price) => assert!(price > 0.0, "Mark price must be > 0"),
            Err(OctoBotExchangeError::NotSupported(_)) => {}
            Err(e) => panic!("Unexpected error in get_mark_price: {e}"),
        }
    }
}

// ---- Options test framework ----

/// Mirrors AbstractAuthenticatedOptionExchangeTester
#[async_trait(?Send)]
pub trait OptionsExchangeTestRunner: FuturesExchangeTestRunner {
    async fn run_test_get_option_positions(&self) {
        let exchange = self.create_exchange().await;
        let positions = exchange.get_positions(None).await
            .expect("get_positions failed for options");
        for position in &positions {
            self.check_position_content(position);
        }
    }
}

// ---- Binance example implementation (shows the pattern for exchange testers) ----

#[cfg(test)]
mod example_tests {
    use super::*;
    use crate::config::{ExchangeConfig, ExchangeCredentials};
    use crate::connector::ccxt::CcxtConnector;

    struct BinanceSpotTester {
        config: ExchangeTestConfig,
    }

    impl BinanceSpotTester {
        fn new() -> Self {
            Self {
                config: ExchangeTestConfig {
                    exchange_name: "binanceus".into(),
                    exchange_type: ExchangeTypes::Spot,
                    symbol: "BTC/USDT".into(),
                    order_price_diff_pct: 20.0,
                    ..Default::default()
                },
            }
        }
    }

    #[async_trait(?Send)]
    impl ExchangeTestRunner for BinanceSpotTester {
        fn config(&self) -> &ExchangeTestConfig {
            &self.config
        }

        async fn create_exchange(&self) -> Box<dyn Exchange> {
            // In a real test: load credentials from env vars
            let api_key = std::env::var("BINANCE_API_KEY").ok();
            let secret = std::env::var("BINANCE_SECRET").ok();
            let creds = ExchangeCredentials {
                api_key,
                secret,
                ..Default::default()
            };
            let cfg = ExchangeConfig::new("binanceus").with_credentials(creds);
            Box::new(CcxtConnector::new(cfg))
        }
    }

    // Example test — skipped unless exchange credentials are available
    // #[tokio::test]
    // #[ignore = "requires live credentials"]
    // async fn test_binance_portfolio() {
    //     BinanceSpotTester::new().run_test_get_portfolio().await;
    // }
}
