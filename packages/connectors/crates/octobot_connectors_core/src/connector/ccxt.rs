// CcxtConnector: wraps the ccxt Rust crate and exposes the Exchange trait.
// Translated from packages/trading/octobot_trading/exchanges/connectors/ccxt/ccxt_connector.py
// and packages/trading/octobot_trading/exchanges/connectors/ccxt/ccxt_client_util.py

use async_trait::async_trait;
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use rust_decimal::Decimal;
use tokio::sync::Mutex;

use ccxt::exchange::{Exchange as CcxtExchange, Value as CcxtValue};

use crate::config::ExchangeConfig;
use crate::connector::{adapter::CcxtAdapter, Exchange};
use crate::enums::{ExchangeTypes, OrderStatus, TimeFrame, TradeOrderSide, TraderOrderType};
use crate::error::{ExchangeResult, OctoBotExchangeError};
use crate::types::{
    Balance, Candle, FundingRate, LeverageInfo, MarketStatus, Order, OrderBook, Position,
    Ticker, Trade, Transaction,
};

// Boxed ccxt exchange client protected by Mutex for &mut self access
type CcxtClient = Arc<Mutex<Box<dyn CcxtExchange + Send>>>;

/// Convert a ccxt Value response to serde_json::Value (None if Undefined)
fn ccxt_to_json(v: CcxtValue) -> Option<serde_json::Value> {
    match v {
        CcxtValue::Json(j) => Some(j),
        CcxtValue::Undefined => None,
    }
}

/// Convert a ccxt Value response, returning an error if Undefined
fn ccxt_to_json_required(v: CcxtValue, context: &str) -> ExchangeResult<serde_json::Value> {
    ccxt_to_json(v).ok_or_else(|| {
        OctoBotExchangeError::FailedRequest(format!("{context}: empty response from ccxt"))
    })
}

/// Build the initial config Value passed to a ccxt exchange constructor.
fn build_ccxt_config(config: &ExchangeConfig) -> serde_json::Value {
    let mut obj = json!({});
    let creds = &config.credentials;
    if let Some(k) = &creds.api_key {
        obj["apiKey"] = json!(k);
    }
    if let Some(s) = &creds.secret {
        obj["secret"] = json!(s);
    }
    if let Some(p) = &creds.password {
        obj["password"] = json!(p);
    }
    if let Some(uid) = &creds.uid {
        obj["uid"] = json!(uid);
    }
    if config.is_sandboxed {
        obj["options"] = json!({ "sandboxMode": true });
    }
    for (k, v) in &config.options {
        obj[k] = v.clone();
    }
    obj
}

/// Create a boxed ccxt exchange instance for the given exchange name.
fn make_ccxt_client(name: &str, config: &ExchangeConfig) -> Option<Box<dyn CcxtExchange + Send>> {
    let params = build_ccxt_config(config);
    let v = CcxtValue::Json(params);

    macro_rules! make {
        ($mod:ident, $impl:ident) => {
            Some(Box::new(ccxt::exchanges::$mod::$impl::new(v)) as Box<dyn CcxtExchange + Send>)
        };
    }

    match name.to_lowercase().as_str() {
        "binance"          => make!(binance, BinanceImpl),
        "binanceusdm"      => make!(binanceusdm, BinanceusdmImpl),
        "binancecoinm"     => make!(binancecoinm, BinancecoinmImpl),
        "binanceus"        => make!(binanceus, BinanceusImpl),
        "bybit"            => make!(bybit, BybitImpl),
        "coinbase"         => make!(coinbase, CoinbaseImpl),
        "coinbaseadvanced" => make!(coinbaseadvanced, CoinbaseadvancedImpl),
        "gate" | "gateio"  => make!(gate, GateImpl),
        "huobi"            => make!(huobi, HuobiImpl),
        "htx"              => make!(htx, HtxImpl),
        "kucoin"           => make!(kucoin, KucoinImpl),
        "kucoinfutures"    => make!(kucoinfutures, KucoinfuturesImpl),
        "kraken"           => make!(kraken, KrakenImpl),
        "krakenfutures"    => make!(krakenfutures, KrakenfuturesImpl),
        "okx"              => make!(okx, OkxImpl),
        "okxus"            => make!(okxus, OkxusImpl),
        "bitfinex"         => make!(bitfinex, BitfinexImpl),
        "bitmex"           => make!(bitmex, BitmexImpl),
        "deribit"          => make!(deribit, DeribitImpl),
        "mexc"             => make!(mexc, MexcImpl),
        "bitget"           => make!(bitget, BitgetImpl),
        "poloniex"         => make!(poloniex, PoloniexImpl),
        "ascendex"         => make!(ascendex, AscendexImpl),
        "bingx"            => make!(bingx, BingxImpl),
        "bitmart"          => make!(bitmart, BitmartImpl),
        "coinex"           => make!(coinex, CoinexImpl),
        "cryptocom"        => make!(cryptocom, CryptocomImpl),
        "hollaex"          => make!(hollaex, HollaexImpl),
        "hyperliquid"      => make!(hyperliquid, HyperliquidImpl),
        "lbank"            => make!(lbank, LbankImpl),
        "phemex"           => make!(phemex, PhemexImpl),
        _                  => None,
    }
}

/// CcxtConnector wraps the ccxt Rust crate and normalises its data via CcxtAdapter.
pub struct CcxtConnector {
    pub config: ExchangeConfig,
    pub rest_name: String,
    pub is_authenticated: bool,
    pub force_authentication: bool,
    adapter: CcxtAdapter,

    pub fix_market_status: bool,
    pub remove_market_status_price_limits: bool,
    pub adapt_market_status_for_contract_size: bool,
    pub require_order_fees_from_trades: bool,
    pub require_closed_orders_from_recent_trades: bool,
    pub dump_incomplete_last_candle: bool,
    pub supports_set_margin_type: bool,
    pub mark_price_in_position: bool,
    pub mark_price_in_ticker: bool,
    pub funding_in_ticker: bool,
    pub max_fetched_ohlcv_count: Option<usize>,
    pub is_skipping_empty_candles: bool,

    pub order_not_found_errors: Vec<String>,
    pub permission_errors: Vec<String>,
    pub missing_funds_errors: Vec<String>,
    pub compliancy_errors: Vec<String>,

    markets: HashMap<String, MarketStatus>,
    all_currencies_price_ticker: HashMap<String, Ticker>,
    pub saved_data: HashMap<String, serde_json::Value>,

    /// Live ccxt exchange client (None before initialize() is called)
    client: Option<CcxtClient>,
}

impl CcxtConnector {
    pub fn new(config: ExchangeConfig) -> Self {
        let rest_name = config.exchange_name.clone();
        let is_authenticated = config.credentials.has_credentials();
        Self {
            config,
            rest_name,
            is_authenticated,
            force_authentication: false,
            adapter: CcxtAdapter::new(),
            fix_market_status: false,
            remove_market_status_price_limits: false,
            adapt_market_status_for_contract_size: false,
            require_order_fees_from_trades: false,
            require_closed_orders_from_recent_trades: false,
            dump_incomplete_last_candle: false,
            supports_set_margin_type: true,
            mark_price_in_position: false,
            mark_price_in_ticker: false,
            funding_in_ticker: false,
            max_fetched_ohlcv_count: None,
            is_skipping_empty_candles: false,
            order_not_found_errors: vec![],
            permission_errors: vec![],
            missing_funds_errors: vec![],
            compliancy_errors: vec![],
            markets: HashMap::new(),
            all_currencies_price_ticker: HashMap::new(),
            saved_data: HashMap::new(),
            client: None,
        }
    }

    fn ccxt_client(&self) -> ExchangeResult<&CcxtClient> {
        self.client.as_ref().ok_or_else(|| {
            OctoBotExchangeError::FailedRequest(
                "ccxt client not initialised — call initialize() first".into(),
            )
        })
    }

    pub fn translate_error(&self, error: &str) -> OctoBotExchangeError {
        let lower = error.to_lowercase();
        if self.order_not_found_errors.iter().any(|e| lower.contains(e.as_str())) {
            return OctoBotExchangeError::OrderNotFound(error.to_string());
        }
        if self.permission_errors.iter().any(|e| lower.contains(e.as_str())) {
            return OctoBotExchangeError::PermissionError(error.to_string());
        }
        if self.missing_funds_errors.iter().any(|e| lower.contains(e.as_str())) {
            return OctoBotExchangeError::MissingFunds(error.to_string());
        }
        if self.compliancy_errors.iter().any(|e| lower.contains(e.as_str())) {
            return OctoBotExchangeError::ExchangeCompliancyError(error.to_string());
        }
        if lower.contains("auth") || lower.contains("apikey") || lower.contains("invalid key") {
            return OctoBotExchangeError::AuthenticationError(error.to_string());
        }
        if lower.contains("rate limit") || lower.contains("ddos") {
            return OctoBotExchangeError::RateLimitExceeded(error.to_string());
        }
        OctoBotExchangeError::FailedRequest(error.to_string())
    }

    pub fn fetch_stop_order_in_different_request(&self, _symbol: Option<&str>) -> bool {
        false
    }

    fn current_timestamp() -> i64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0)
    }
}

#[async_trait]
impl Exchange for CcxtConnector {
    async fn initialize(&mut self) -> ExchangeResult<()> {
        let ccxt_client = make_ccxt_client(&self.rest_name, &self.config)
            .ok_or_else(|| {
                OctoBotExchangeError::NotSupported(format!(
                    "Exchange '{}' is not supported by the ccxt Rust crate",
                    self.rest_name
                ))
            })?;

        let client: CcxtClient = Arc::new(Mutex::new(ccxt_client));

        {
            let mut guard = client.lock().await;
            let raw = guard.load_markets(CcxtValue::Undefined, CcxtValue::Undefined).await;
            if let Some(serde_json::Value::Object(map)) = ccxt_to_json(raw) {
                for (symbol, market_raw) in map {
                    match self.adapter.adapt_market_status(&market_raw) {
                        Ok(ms) => { self.markets.insert(symbol, ms); }
                        Err(e) => { log::warn!("market status parse error for {symbol}: {e}"); }
                    }
                }
            }
        }

        self.client = Some(client);
        Ok(())
    }

    async fn stop(&mut self) -> ExchangeResult<()> {
        self.client = None;
        Ok(())
    }

    fn get_name(&self) -> &str {
        &self.rest_name
    }

    fn get_exchange_type(&self) -> ExchangeTypes {
        if self.config.is_future {
            ExchangeTypes::Future
        } else if self.config.is_option {
            ExchangeTypes::Option
        } else {
            ExchangeTypes::Spot
        }
    }

    fn is_authenticated(&self) -> bool {
        self.is_authenticated
    }

    fn is_supporting_sandbox(&self) -> bool {
        false
    }

    // ---- Market data ----

    async fn load_markets(&mut self, reload: bool) -> ExchangeResult<HashMap<String, MarketStatus>> {
        if !reload && !self.markets.is_empty() {
            return Ok(self.markets.clone());
        }
        let client_opt = self.client.clone();
        if let Some(client) = client_opt {
            let reload_val = CcxtValue::Json(json!(reload));
            let mut guard = client.lock().await;
            let raw = guard.load_markets(reload_val, CcxtValue::Undefined).await;
            drop(guard);
            if let Some(serde_json::Value::Object(map)) = ccxt_to_json(raw) {
                for (symbol, market_raw) in map {
                    match self.adapter.adapt_market_status(&market_raw) {
                        Ok(ms) => { self.markets.insert(symbol, ms); }
                        Err(e) => { log::warn!("market status parse error for {symbol}: {e}"); }
                    }
                }
            }
        }
        Ok(self.markets.clone())
    }

    async fn get_market_status(
        &self,
        symbol: &str,
        price_example: Option<f64>,
        with_fixer: bool,
    ) -> ExchangeResult<MarketStatus> {
        if let Some(ms) = self.markets.get(symbol) {
            let mut ms = ms.clone();
            if with_fixer && self.fix_market_status {
                crate::util::market_status_fixer::fix_market_status(&mut ms, price_example);
            }
            return Ok(ms);
        }
        Err(OctoBotExchangeError::FailedMarketStatusRequest(
            format!("Market status not found for {symbol}"),
        ))
    }

    async fn get_symbol_prices(
        &self,
        symbol: &str,
        time_frame: TimeFrame,
        limit: Option<usize>,
        since: Option<i64>,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Vec<Candle>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let params_val = if params.is_empty() {
            CcxtValue::Undefined
        } else {
            CcxtValue::Json(serde_json::Value::Object(params.into_iter().collect()))
        };

        let raw = guard.fetch_ohlcv(
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Json(json!(time_frame.to_ccxt_value())),
            since_val,
            limit_val,
            params_val,
        ).await;

        let json_val = ccxt_to_json_required(raw, "fetch_ohlcv")?;
        let candles = self.adapter.adapt_ohlcv(&json_val, &time_frame)?;

        if let Some(max) = self.max_fetched_ohlcv_count {
            Ok(candles.into_iter().take(max).collect())
        } else {
            Ok(candles)
        }
    }

    async fn get_kline_price(
        &self,
        symbol: &str,
        time_frame: TimeFrame,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Vec<Candle>> {
        self.get_symbol_prices(symbol, time_frame, Some(1), None, params).await
    }

    async fn get_order_book(&self, symbol: &str, limit: usize) -> ExchangeResult<OrderBook> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.fetch_order_book(
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Json(json!(limit)),
            CcxtValue::Undefined,
        ).await;

        let json_val = ccxt_to_json_required(raw, "fetch_order_book")?;
        self.adapter.adapt_order_book(&json_val)
    }

    async fn get_recent_trades(
        &self,
        symbol: &str,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Trade>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);
        let raw = guard.fetch_trades(
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Undefined,
            limit_val,
            CcxtValue::Undefined,
        ).await;

        let json_val = ccxt_to_json_required(raw, "fetch_trades")?;
        self.adapter.adapt_trades(&json_val, Some(symbol))
    }

    async fn get_price_ticker(&self, symbol: &str) -> ExchangeResult<Ticker> {
        if let Some(ticker) = self.all_currencies_price_ticker.get(symbol) {
            return Ok(ticker.clone());
        }
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.fetch_ticker(
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Undefined,
        ).await;

        let json_val = ccxt_to_json_required(raw, "fetch_ticker")?;
        self.adapter.adapt_ticker(&json_val)
    }

    async fn get_all_currencies_price_ticker(
        &self,
        symbols: Option<Vec<String>>,
    ) -> ExchangeResult<HashMap<String, Ticker>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbols_val = symbols
            .map(|s| CcxtValue::Json(json!(s)))
            .unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_tickers(symbols_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_tickers")?;

        let mut out = HashMap::new();
        if let serde_json::Value::Object(map) = json_val {
            for (sym, ticker_raw) in map {
                match self.adapter.adapt_ticker(&ticker_raw) {
                    Ok(t) => { out.insert(sym, t); }
                    Err(e) => { log::warn!("ticker parse error for {sym}: {e}"); }
                }
            }
        }
        Ok(out)
    }

    // ---- Orders ----

    async fn get_order(
        &self,
        exchange_order_id: &str,
        symbol: Option<&str>,
    ) -> ExchangeResult<Option<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let raw = guard.fetch_order(
            CcxtValue::Json(json!(exchange_order_id)),
            symbol_val,
            CcxtValue::Undefined,
        ).await;

        match ccxt_to_json(raw) {
            Some(json_val) => self.adapter.adapt_order(&json_val, symbol).map(Some),
            None => Ok(None),
        }
    }

    async fn get_all_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_orders(symbol_val, since_val, limit_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_orders")?;
        self.adapter.adapt_orders(&json_val, symbol, false)
    }

    async fn get_open_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_open_orders(symbol_val, since_val, limit_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_open_orders")?;
        self.adapter.adapt_orders(&json_val, symbol, false)
    }

    async fn get_closed_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_closed_orders(symbol_val, since_val, limit_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_closed_orders")?;
        self.adapter.adapt_orders(&json_val, symbol, false)
    }

    async fn get_cancelled_orders(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_canceled_orders(symbol_val, since_val, limit_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_canceled_orders")?;
        self.adapter.adapt_orders(&json_val, symbol, true)
    }

    async fn get_my_recent_trades(
        &self,
        symbol: Option<&str>,
        since: Option<i64>,
        limit: Option<usize>,
    ) -> ExchangeResult<Vec<Trade>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let since_val = since.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        let limit_val = limit.map(|l| CcxtValue::Json(json!(l))).unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_my_trades(symbol_val, since_val, limit_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_my_trades")?;
        self.adapter.adapt_trades(&json_val, symbol)
    }

    async fn create_order(
        &self,
        order_type: TraderOrderType,
        symbol: &str,
        quantity: Decimal,
        price: Option<Decimal>,
        stop_price: Option<Decimal>,
        side: Option<TradeOrderSide>,
        _current_price: Option<Decimal>,
        reduce_only: bool,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<Option<Order>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let side_str = side.as_ref().map(|s| s.value()).unwrap_or_else(|| order_type.ccxt_side());
        let type_str = order_type.ccxt_type();

        let mut extra_params = params.unwrap_or_default();
        if reduce_only {
            extra_params.insert("reduceOnly".into(), json!(true));
        }
        if let Some(sp) = stop_price {
            extra_params.insert("stopPrice".into(), json!(sp.to_string()));
            extra_params.insert("triggerPrice".into(), json!(sp.to_string()));
        }

        let params_val = if extra_params.is_empty() {
            CcxtValue::Undefined
        } else {
            CcxtValue::Json(serde_json::Value::Object(extra_params.into_iter().collect()))
        };

        let price_val = price
            .map(|p| CcxtValue::Json(json!(p.to_string())))
            .unwrap_or(CcxtValue::Undefined);

        let raw = guard.create_order(
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Json(json!(type_str)),
            CcxtValue::Json(json!(side_str)),
            CcxtValue::Json(json!(quantity.to_string())),
            price_val,
            params_val,
        ).await;

        match ccxt_to_json(raw) {
            Some(json_val) => self.adapter.adapt_order(&json_val, Some(symbol)).map(Some),
            None => Ok(None),
        }
    }

    async fn cancel_order(
        &self,
        exchange_order_id: &str,
        symbol: &str,
        _order_type: TraderOrderType,
    ) -> ExchangeResult<OrderStatus> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.cancel_order(
            CcxtValue::Json(json!(exchange_order_id)),
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Undefined,
        ).await;

        let json_val = ccxt_to_json_required(raw, "cancel_order")?;
        let order = self.adapter.adapt_order(&json_val, Some(symbol))?;
        Ok(order.status)
    }

    async fn cancel_all_orders(&self, symbol: Option<&str>) -> ExchangeResult<()> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        guard.cancel_all_orders(symbol_val, CcxtValue::Undefined).await;
        Ok(())
    }

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
    ) -> ExchangeResult<Order> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let side_str = side.as_ref().map(|s| s.value()).unwrap_or_else(|| order_type.ccxt_side());
        let type_str = order_type.ccxt_type();

        let mut extra_params = params.unwrap_or_default();
        if let Some(sp) = stop_price {
            extra_params.insert("stopPrice".into(), json!(sp));
            extra_params.insert("triggerPrice".into(), json!(sp));
        }

        let params_val = if extra_params.is_empty() {
            CcxtValue::Undefined
        } else {
            CcxtValue::Json(serde_json::Value::Object(extra_params.into_iter().collect()))
        };

        let raw = guard.edit_order(
            CcxtValue::Json(json!(exchange_order_id)),
            CcxtValue::Json(json!(symbol)),
            CcxtValue::Json(json!(type_str)),
            CcxtValue::Json(json!(side_str)),
            CcxtValue::Json(json!(quantity)),
            CcxtValue::Json(json!(price)),
            params_val,
        ).await;

        let json_val = ccxt_to_json_required(raw, "edit_order")?;
        self.adapter.adapt_order(&json_val, Some(symbol))
    }

    // ---- Account ----

    async fn get_balance(
        &self,
        params: HashMap<String, serde_json::Value>,
    ) -> ExchangeResult<Balance> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let params_val = if params.is_empty() {
            CcxtValue::Undefined
        } else {
            CcxtValue::Json(serde_json::Value::Object(params.into_iter().collect()))
        };

        let raw = guard.fetch_balance(params_val).await;
        let json_val = ccxt_to_json_required(raw, "fetch_balance")?;
        self.adapter.adapt_balance(&json_val)
    }

    // ---- Futures ----

    async fn get_position(&self, symbol: &str) -> ExchangeResult<Option<Position>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.fetch_position(CcxtValue::Json(json!(symbol)), CcxtValue::Undefined).await;
        match ccxt_to_json(raw) {
            Some(json_val) => self.adapter.adapt_position(&json_val).map(Some),
            None => Ok(None),
        }
    }

    async fn get_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let symbols_val = symbols
            .map(|s| CcxtValue::Json(json!(s)))
            .unwrap_or(CcxtValue::Undefined);

        let raw = guard.fetch_positions(symbols_val, CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_positions")?;
        self.adapter.adapt_positions(&json_val)
    }

    async fn get_closed_positions(&self, symbols: Option<Vec<String>>) -> ExchangeResult<Vec<Position>> {
        self.get_positions(symbols).await
    }

    async fn get_funding_rate(&self, symbol: &str) -> ExchangeResult<FundingRate> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.fetch_funding_rate(CcxtValue::Json(json!(symbol)), CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_funding_rate")?;
        self.adapter.adapt_funding_rate(&json_val)
    }

    async fn get_mark_price(&self, symbol: &str) -> ExchangeResult<f64> {
        let ticker = self.get_price_ticker(symbol).await?;
        ticker.mark_price.ok_or_else(|| {
            OctoBotExchangeError::FailedRequest(format!("no mark price for {symbol}"))
        })
    }

    async fn get_symbol_leverage(&self, symbol: &str) -> ExchangeResult<LeverageInfo> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let raw = guard.fetch_leverage(CcxtValue::Json(json!(symbol)), CcxtValue::Undefined).await;
        let json_val = ccxt_to_json_required(raw, "fetch_leverage")?;
        self.adapter.adapt_leverage(&json_val)
    }

    async fn set_symbol_leverage(
        &self,
        symbol: &str,
        leverage: f64,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<LeverageInfo> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let params_val = params
            .map(|p| CcxtValue::Json(serde_json::Value::Object(p.into_iter().collect())))
            .unwrap_or(CcxtValue::Undefined);

        let raw = guard.set_leverage(
            CcxtValue::Json(json!(leverage)),
            CcxtValue::Json(json!(symbol)),
            params_val,
        ).await;

        let json_val = ccxt_to_json_required(raw, "set_leverage")?;
        self.adapter.adapt_leverage(&json_val)
    }

    async fn set_symbol_margin_type(
        &self,
        symbol: &str,
        isolated: bool,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<()> {
        if !self.supports_set_margin_type {
            return Err(OctoBotExchangeError::NotSupported(format!(
                "{}: set_margin_type is not supported",
                self.rest_name
            )));
        }
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let margin_mode = if isolated { "isolated" } else { "cross" };
        let params_val = params
            .map(|p| CcxtValue::Json(serde_json::Value::Object(p.into_iter().collect())))
            .unwrap_or(CcxtValue::Undefined);

        guard.set_margin_mode(
            CcxtValue::Json(json!(margin_mode)),
            CcxtValue::Json(json!(symbol)),
            params_val,
        ).await;

        Ok(())
    }

    async fn set_position_mode(&self, one_way: bool, symbol: Option<&str>) -> ExchangeResult<()> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let mode = if one_way { "oneway" } else { "hedged" };
        let symbol_val = symbol.map(|s| CcxtValue::Json(json!(s))).unwrap_or(CcxtValue::Undefined);
        guard.set_position_mode(CcxtValue::Json(json!(mode)), symbol_val, CcxtValue::Undefined).await;
        Ok(())
    }

    // ---- Transactions ----

    async fn get_deposit_address(
        &self,
        currency: &str,
        network: Option<&str>,
    ) -> ExchangeResult<Option<String>> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let mut params = json!({});
        if let Some(net) = network {
            params["network"] = json!(net);
        }

        let raw = guard.fetch_deposit_address(
            CcxtValue::Json(json!(currency)),
            CcxtValue::Json(params),
        ).await;

        match ccxt_to_json(raw) {
            Some(v) => Ok(v.get("address").and_then(|a| a.as_str()).map(|s| s.to_string())),
            None => Ok(None),
        }
    }

    async fn withdraw(
        &self,
        currency: &str,
        amount: Decimal,
        address: &str,
        tag: Option<&str>,
        network: Option<&str>,
        params: Option<HashMap<String, serde_json::Value>>,
    ) -> ExchangeResult<Transaction> {
        let client = self.ccxt_client()?;
        let mut guard = client.lock().await;

        let mut extra = params.unwrap_or_default();
        if let Some(t) = tag {
            extra.insert("tag".into(), json!(t));
        }
        if let Some(net) = network {
            extra.insert("network".into(), json!(net));
        }

        let params_val = CcxtValue::Json(serde_json::Value::Object(extra.into_iter().collect()));

        let tag_val = tag.map(|t| CcxtValue::Json(json!(t))).unwrap_or(CcxtValue::Undefined);
        let raw = guard.withdraw(
            CcxtValue::Json(json!(currency)),
            CcxtValue::Json(json!(amount.to_string())),
            CcxtValue::Json(json!(address)),
            tag_val,
            params_val,
        ).await;

        let json_val = ccxt_to_json_required(raw, "withdraw")?;
        Ok(Transaction {
            id: json_val.get("id").and_then(|v| v.as_str()).map(|s| s.to_string()),
            txid: json_val.get("txid").and_then(|v| v.as_str()).map(|s| s.to_string()),
            timestamp: json_val.get("timestamp").and_then(|v| v.as_i64()),
            address_to: Some(address.to_string()),
            address_from: None,
            tag: tag.map(|t| t.to_string()),
            tx_type: Some("withdrawal".to_string()),
            amount: json_val.get("amount").and_then(|v| v.as_f64()),
            currency: Some(currency.to_string()),
            status: json_val.get("status").and_then(|v| v.as_str()).map(|s| s.to_string()),
            fee: None,
            network: network.map(|n| n.to_string()),
        })
    }

    // ---- Market info helpers ----

    fn get_fees(&self, _symbol: &str) -> ExchangeResult<HashMap<String, f64>> {
        Ok(HashMap::new())
    }

    fn get_exchange_current_time(&self) -> i64 {
        Self::current_timestamp()
    }

    fn get_pair_from_exchange(&self, pair: &str) -> Option<String> {
        if self.markets.contains_key(pair) {
            Some(pair.to_string())
        } else {
            None
        }
    }

    fn get_exchange_pair(&self, pair: &str) -> ExchangeResult<String> {
        self.markets
            .get(pair)
            .and_then(|m| m.id.clone())
            .ok_or_else(|| OctoBotExchangeError::UnsupportedSymbolError(pair.to_string()))
    }

    fn get_available_symbols(&self, active_only: bool) -> Vec<String> {
        self.markets
            .values()
            .filter(|m| !active_only || m.active)
            .map(|m| m.symbol.clone())
            .collect()
    }

    fn get_available_time_frames(&self) -> Vec<String> {
        ["1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d","3d","1w","1M"]
            .iter()
            .map(|s| s.to_string())
            .collect()
    }

    fn get_rate_limit(&self) -> f64 {
        0.5
    }

    fn is_order_not_found_error(&self, error_str: &str) -> bool {
        let lower = error_str.to_lowercase();
        self.order_not_found_errors.iter().any(|e| lower.contains(e.as_str()))
    }

    fn is_api_permission_error(&self, error_str: &str) -> bool {
        let lower = error_str.to_lowercase();
        self.permission_errors.iter().any(|e| lower.contains(e.as_str()))
    }

    fn is_exchange_rules_compliancy_error(&self, error_str: &str) -> bool {
        let lower = error_str.to_lowercase();
        self.compliancy_errors.iter().any(|e| lower.contains(e.as_str()))
    }

    fn is_missing_funds_error(&self, error_str: &str) -> bool {
        let lower = error_str.to_lowercase();
        self.missing_funds_errors.iter().any(|e| lower.contains(e.as_str()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_connector_defaults() {
        let config = ExchangeConfig::new("binance");
        let connector = CcxtConnector::new(config);
        assert_eq!(connector.get_name(), "binance");
        assert_eq!(connector.get_exchange_type(), ExchangeTypes::Spot);
        assert!(!connector.is_authenticated());
    }

    #[test]
    fn test_translate_error_auth() {
        let config = ExchangeConfig::new("binance");
        let connector = CcxtConnector::new(config);
        let err = connector.translate_error("Invalid API key");
        assert!(matches!(err, OctoBotExchangeError::AuthenticationError(_)));
    }

    #[test]
    fn test_translate_error_rate_limit() {
        let config = ExchangeConfig::new("binance");
        let connector = CcxtConnector::new(config);
        let err = connector.translate_error("rate limit exceeded");
        assert!(matches!(err, OctoBotExchangeError::RateLimitExceeded(_)));
    }

    #[test]
    fn test_make_ccxt_client_known_exchange() {
        let config = ExchangeConfig::new("binance");
        let client = make_ccxt_client("binance", &config);
        assert!(client.is_some(), "binance should be a known exchange");
    }

    #[test]
    fn test_make_ccxt_client_unknown_exchange() {
        let config = ExchangeConfig::new("unknown_exchange_xyz");
        let client = make_ccxt_client("unknown_exchange_xyz", &config);
        assert!(client.is_none(), "unknown exchange should return None");
    }
}
