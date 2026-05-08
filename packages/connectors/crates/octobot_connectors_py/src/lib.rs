// PyO3 bridge: exposes octobot_connectors_core to Python.
// Built as a cdylib by maturin; imported as `octobot_connectors_rs._core`.
//
// Each Python-visible type is a thin #[pyclass] wrapper around the Rust type.
// Async methods use pyo3-asyncio (tokio runtime) so Python can `await` them.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use rust_decimal::prelude::ToPrimitive;
use std::collections::HashMap;

use octobot_connectors_core::{
    config::{ExchangeConfig, ExchangeCredentials, ProxyConfig},
    connector::{ccxt::CcxtConnector, Exchange},
    enums::{ExchangeTypes, MarginType, OrderStatus, PositionSide, TimeFrame, TradeOrderSide, TraderOrderType},
    error::OctoBotExchangeError,
    types::{Balance, Candle, CurrencyBalance, Order, OrderBook, Position, Ticker},
};

// ---- Helper: convert OctoBotExchangeError → PyErr ----

fn to_py_err(e: OctoBotExchangeError) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

// ============================================================
// Enums
// ============================================================

/// Python wrapper for TradeOrderSide
#[pyclass(name = "TradeOrderSide")]
#[derive(Clone)]
pub struct PyTradeOrderSide(pub TradeOrderSide);

#[pymethods]
impl PyTradeOrderSide {
    #[classattr]
    const BUY: &'static str = "buy";
    #[classattr]
    const SELL: &'static str = "sell";

    #[new]
    fn new(value: &str) -> PyResult<Self> {
        TradeOrderSide::from_str(value)
            .map(Self)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown TradeOrderSide: {value}")))
    }

    fn value(&self) -> &'static str { self.0.value() }
    fn __repr__(&self) -> String { format!("TradeOrderSide.{:?}", self.0) }
    fn __str__(&self) -> &'static str { self.0.value() }
    fn __eq__(&self, other: &Self) -> bool { self.0 == other.0 }
}

#[pyclass(name = "TraderOrderType")]
#[derive(Clone)]
pub struct PyTraderOrderType(pub TraderOrderType);

#[pymethods]
impl PyTraderOrderType {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        let t = match value {
            "buy_market" => TraderOrderType::BuyMarket,
            "buy_limit" => TraderOrderType::BuyLimit,
            "stop_loss" => TraderOrderType::StopLoss,
            "stop_limit" => TraderOrderType::StopLossLimit,
            "sell_market" => TraderOrderType::SellMarket,
            "sell_limit" => TraderOrderType::SellLimit,
            "trailing_stop" => TraderOrderType::TrailingStop,
            "trailing_stop_limit" => TraderOrderType::TrailingStopLimit,
            "take_profit" => TraderOrderType::TakeProfit,
            "take_profit_limit" => TraderOrderType::TakeProfitLimit,
            "unsupported" => TraderOrderType::Unsupported,
            _ => TraderOrderType::Unknown,
        };
        Ok(Self(t))
    }
    fn value(&self) -> &'static str { self.0.value() }
    fn __repr__(&self) -> String { format!("TraderOrderType({:?})", self.0) }
    fn __str__(&self) -> &'static str { self.0.value() }
}

#[pyclass(name = "OrderStatus")]
#[derive(Clone)]
pub struct PyOrderStatus(pub OrderStatus);

#[pymethods]
impl PyOrderStatus {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        let s = match value {
            "pending_creation" => OrderStatus::PendingCreation,
            "open" => OrderStatus::Open,
            "partially_filled" => OrderStatus::PartiallyFilled,
            "filled" => OrderStatus::Filled,
            "canceled" => OrderStatus::Canceled,
            "canceling" => OrderStatus::PendingCancel,
            "closed" => OrderStatus::Closed,
            "expired" => OrderStatus::Expired,
            "rejected" => OrderStatus::Rejected,
            _ => OrderStatus::Unknown,
        };
        Ok(Self(s))
    }
    fn value(&self) -> &'static str { self.0.value() }
    fn is_closed(&self) -> bool { self.0.is_closed() }
    fn __repr__(&self) -> String { format!("OrderStatus({:?})", self.0) }
    fn __str__(&self) -> &'static str { self.0.value() }
    fn __eq__(&self, other: &Self) -> bool { self.0 == other.0 }
}

#[pyclass(name = "ExchangeTypes")]
#[derive(Clone)]
pub struct PyExchangeTypes(pub ExchangeTypes);

#[pymethods]
impl PyExchangeTypes {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        let t = match value {
            "spot" => ExchangeTypes::Spot,
            "future" => ExchangeTypes::Future,
            "margin" => ExchangeTypes::Margin,
            "option" => ExchangeTypes::Option,
            _ => ExchangeTypes::Unknown,
        };
        Ok(Self(t))
    }
    fn value(&self) -> &'static str { self.0.value() }
    fn __repr__(&self) -> String { format!("ExchangeTypes({:?})", self.0) }
    fn __str__(&self) -> &'static str { self.0.value() }
}

#[pyclass(name = "TimeFrame")]
#[derive(Clone)]
pub struct PyTimeFrame(pub TimeFrame);

#[pymethods]
impl PyTimeFrame {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        TimeFrame::from_ccxt_value(value)
            .map(Self)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown TimeFrame: {value}")))
    }
    fn to_ccxt_value(&self) -> &'static str { self.0.to_ccxt_value() }
    fn to_seconds(&self) -> i64 { self.0.to_seconds() }
    fn __repr__(&self) -> String { format!("TimeFrame({:?})", self.0) }
    fn __str__(&self) -> &'static str { self.0.to_ccxt_value() }
}

#[pyclass(name = "MarginType")]
#[derive(Clone)]
pub struct PyMarginType(pub MarginType);

#[pymethods]
impl PyMarginType {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        MarginType::from_str(value)
            .map(Self)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown MarginType: {value}")))
    }
    fn value(&self) -> &'static str { self.0.value() }
    fn __repr__(&self) -> String { format!("MarginType({:?})", self.0) }
    fn __str__(&self) -> &'static str { self.0.value() }
}

#[pyclass(name = "PositionSide")]
#[derive(Clone)]
pub struct PyPositionSide(pub PositionSide);

#[pymethods]
impl PyPositionSide {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        let s = match value {
            "long" => PositionSide::Long,
            "short" => PositionSide::Short,
            "both" => PositionSide::Both,
            _ => PositionSide::Unknown,
        };
        Ok(Self(s))
    }
    fn value(&self) -> &'static str { self.0.value() }
    fn __repr__(&self) -> String { format!("PositionSide({:?})", self.0) }
}

// ============================================================
// Config
// ============================================================

#[pyclass(name = "ExchangeCredentials")]
#[derive(Clone, Default)]
pub struct PyExchangeCredentials(pub ExchangeCredentials);

#[pymethods]
impl PyExchangeCredentials {
    #[new]
    #[pyo3(signature = (api_key=None, secret=None, password=None, wallet_address=None, private_key=None))]
    fn new(
        api_key: Option<String>,
        secret: Option<String>,
        password: Option<String>,
        wallet_address: Option<String>,
        private_key: Option<String>,
    ) -> Self {
        Self(ExchangeCredentials {
            api_key,
            secret,
            password,
            wallet_address,
            private_key,
            ..Default::default()
        })
    }

    #[getter] fn api_key(&self) -> Option<String> { self.0.api_key.clone() }
    #[getter] fn secret(&self) -> Option<String> { self.0.secret.clone() }
    fn has_credentials(&self) -> bool { self.0.has_credentials() }
    fn __repr__(&self) -> String {
        format!("ExchangeCredentials(key={})", self.0.sanitized_api_key().unwrap_or("None".into()))
    }
}

#[pyclass(name = "ProxyConfig")]
#[derive(Clone, Default)]
pub struct PyProxyConfig(pub ProxyConfig);

#[pymethods]
impl PyProxyConfig {
    #[new]
    #[pyo3(signature = (http_proxy=None, https_proxy=None, socks_proxy=None))]
    fn new(
        http_proxy: Option<String>,
        https_proxy: Option<String>,
        socks_proxy: Option<String>,
    ) -> Self {
        Self(ProxyConfig {
            http_proxy,
            https_proxy,
            socks_proxy,
            ..Default::default()
        })
    }
    fn has_proxy(&self) -> bool { self.0.has_proxy() }
}

#[pyclass(name = "ExchangeConfig")]
#[derive(Clone)]
pub struct PyExchangeConfig(pub ExchangeConfig);

#[pymethods]
impl PyExchangeConfig {
    #[new]
    #[pyo3(signature = (
        exchange_name,
        credentials=None,
        proxy=None,
        is_sandboxed=false,
        is_future=false,
        is_spot_only=true,
    ))]
    fn new(
        exchange_name: String,
        credentials: Option<PyExchangeCredentials>,
        proxy: Option<PyProxyConfig>,
        is_sandboxed: bool,
        is_future: bool,
        is_spot_only: bool,
    ) -> Self {
        let mut cfg = ExchangeConfig::new(exchange_name);
        if let Some(c) = credentials { cfg.credentials = c.0; }
        if let Some(p) = proxy { cfg.proxy = Some(p.0); }
        cfg.is_sandboxed = is_sandboxed;
        cfg.is_future = is_future;
        cfg.is_spot_only = is_spot_only;
        Self(cfg)
    }

    #[getter]
    fn exchange_name(&self) -> &str { &self.0.exchange_name }

    #[getter]
    fn is_future(&self) -> bool { self.0.is_future }

    fn __repr__(&self) -> String {
        format!("ExchangeConfig(exchange={})", self.0.exchange_name)
    }
}

// ============================================================
// Data types (returned from Exchange methods)
// ============================================================

#[pyclass(name = "Candle")]
#[derive(Clone)]
pub struct PyCandle(pub Candle);

#[pymethods]
impl PyCandle {
    #[getter] fn timestamp(&self) -> i64 { self.0.timestamp }
    #[getter] fn open(&self) -> f64 { self.0.open }
    #[getter] fn high(&self) -> f64 { self.0.high }
    #[getter] fn low(&self) -> f64 { self.0.low }
    #[getter] fn close(&self) -> f64 { self.0.close }
    #[getter] fn volume(&self) -> f64 { self.0.volume }
    fn __repr__(&self) -> String {
        format!("Candle(ts={}, close={})", self.0.timestamp, self.0.close)
    }
}

#[pyclass(name = "Ticker")]
#[derive(Clone)]
pub struct PyTicker(pub Ticker);

#[pymethods]
impl PyTicker {
    #[getter] fn symbol(&self) -> &str { &self.0.symbol }
    #[getter] fn timestamp(&self) -> i64 { self.0.timestamp }
    #[getter] fn last(&self) -> Option<f64> { self.0.last }
    #[getter] fn bid(&self) -> Option<f64> { self.0.bid }
    #[getter] fn ask(&self) -> Option<f64> { self.0.ask }
    #[getter] fn close(&self) -> Option<f64> { self.0.close }
    #[getter] fn volume(&self) -> Option<f64> { self.0.base_volume }
    fn last_price(&self) -> Option<f64> { self.0.last_price() }
    fn __repr__(&self) -> String { format!("Ticker({})", self.0.symbol) }
}

#[pyclass(name = "OrderBook")]
#[derive(Clone)]
pub struct PyOrderBook(pub OrderBook);

#[pymethods]
impl PyOrderBook {
    #[getter] fn symbol(&self) -> &str { &self.0.symbol }
    #[getter] fn timestamp(&self) -> i64 { self.0.timestamp }
    #[getter] fn bids(&self) -> Vec<[f64; 2]> { self.0.bids.clone() }
    #[getter] fn asks(&self) -> Vec<[f64; 2]> { self.0.asks.clone() }
    fn best_bid(&self) -> Option<f64> { self.0.best_bid() }
    fn best_ask(&self) -> Option<f64> { self.0.best_ask() }
}

#[pyclass(name = "CurrencyBalance")]
#[derive(Clone)]
pub struct PyCurrencyBalance(pub CurrencyBalance);

#[pymethods]
impl PyCurrencyBalance {
    #[getter] fn free(&self) -> f64 { self.0.free.to_f64().unwrap_or(0.0) }
    #[getter] fn used(&self) -> f64 { self.0.used.to_f64().unwrap_or(0.0) }
    #[getter] fn total(&self) -> f64 { self.0.total.to_f64().unwrap_or(0.0) }
    fn __repr__(&self) -> String {
        format!("Balance(free={}, total={})", self.free(), self.total())
    }
}

#[pyclass(name = "Order")]
#[derive(Clone)]
pub struct PyOrder(pub Order);

#[pymethods]
impl PyOrder {
    #[getter] fn id(&self) -> &str { &self.0.id }
    #[getter] fn symbol(&self) -> &str { &self.0.symbol }
    #[getter] fn timestamp(&self) -> i64 { self.0.timestamp }
    #[getter] fn price(&self) -> Option<f64> { self.0.price }
    #[getter] fn amount(&self) -> f64 { self.0.amount }
    #[getter] fn filled(&self) -> f64 { self.0.filled }
    #[getter] fn remaining(&self) -> f64 { self.0.remaining }
    #[getter] fn status(&self) -> String { self.0.status.value().to_string() }
    #[getter] fn reduce_only(&self) -> bool { self.0.reduce_only }
    fn is_open(&self) -> bool { self.0.is_open() }
    fn is_closed(&self) -> bool { self.0.is_closed() }
    fn __repr__(&self) -> String { format!("Order(id={}, symbol={})", self.0.id, self.0.symbol) }
}

#[pyclass(name = "Position")]
#[derive(Clone)]
pub struct PyPosition(pub Position);

#[pymethods]
impl PyPosition {
    #[getter] fn symbol(&self) -> &str { &self.0.symbol }
    #[getter] fn contracts(&self) -> Option<f64> { self.0.contracts }
    #[getter] fn entry_price(&self) -> Option<f64> { self.0.entry_price }
    #[getter] fn mark_price(&self) -> Option<f64> { self.0.mark_price }
    #[getter] fn unrealized_pnl(&self) -> Option<f64> { self.0.unrealized_pnl }
    fn is_empty(&self) -> bool { self.0.is_empty() }
    fn __repr__(&self) -> String { format!("Position({})", self.0.symbol) }
}

// ============================================================
// CcxtConnector Python wrapper
// ============================================================

#[pyclass(name = "CcxtConnector")]
pub struct PyCcxtConnector {
    inner: CcxtConnector,
}

#[pymethods]
impl PyCcxtConnector {
    #[new]
    fn new(config: &PyExchangeConfig) -> PyResult<Self> {
        Ok(Self { inner: CcxtConnector::new(config.0.clone()) })
    }

    fn get_name(&self) -> &str {
        self.inner.get_name()
    }

    #[getter]
    fn exchange_name(&self) -> &str {
        self.inner.get_name()
    }

    fn is_authenticated(&self) -> bool {
        self.inner.is_authenticated()
    }

    fn get_exchange_type(&self) -> String {
        self.inner.get_exchange_type().value().to_string()
    }

    fn get_available_symbols(&self, active_only: bool) -> Vec<String> {
        self.inner.get_available_symbols(active_only)
    }

    fn get_exchange_current_time(&self) -> i64 {
        self.inner.get_exchange_current_time()
    }

    // ---- Async methods via pyo3-asyncio ----
    // NOTE: pyo3-asyncio 0.21 requires the connector to be cloneable or wrapped in Arc.
    // The pattern here uses tokio's block_in_place for simplicity; production code
    // should use `pyo3_asyncio_0_21::tokio::future_into_py` for true async.

    fn initialize<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        // Synchronous init using tokio::runtime::Handle
        // A full async bridge would use: pyo3_asyncio_0_21::tokio::future_into_py(py, async { ... })
        py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
                .block_on(self.inner.initialize())
                .map_err(to_py_err)
        })?;
        Ok(py.None().into_bound(py))
    }

    fn get_balance<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_balance(HashMap::new()))
                .map_err(to_py_err)
        })?;
        // Convert Balance to Python dict
        let dict = pyo3::types::PyDict::new(py);
        for (currency, balance) in result {
            let bal = PyCurrencyBalance(balance).into_pyobject(py)?.into_any().unbind();
            dict.set_item(currency, bal)?;
        }
        Ok(dict.into_any())
    }

    fn get_price_ticker<'py>(&self, py: Python<'py>, symbol: String) -> PyResult<Bound<'py, PyAny>> {
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_price_ticker(&symbol))
                .map_err(to_py_err)
        })?;
        PyTicker(result).into_pyobject(py).map(|b| b.into_any())
    }

    fn get_symbol_prices<'py>(
        &self,
        py: Python<'py>,
        symbol: String,
        time_frame: String,
        limit: Option<usize>,
        since: Option<i64>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let tf = TimeFrame::from_ccxt_value(&time_frame)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown time frame: {time_frame}")))?;
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_symbol_prices(&symbol, tf, limit, since, HashMap::new()))
                .map_err(to_py_err)
        })?;
        let list = pyo3::types::PyList::new(
            py,
            result.into_iter().map(|c| PyCandle(c).into_pyobject(py).unwrap().into_any().unbind()),
        )?;
        Ok(list.into_any())
    }

    fn get_order_book<'py>(
        &self,
        py: Python<'py>,
        symbol: String,
        limit: usize,
    ) -> PyResult<Bound<'py, PyAny>> {
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_order_book(&symbol, limit))
                .map_err(to_py_err)
        })?;
        PyOrderBook(result).into_pyobject(py).map(|b| b.into_any())
    }

    fn get_open_orders<'py>(
        &self,
        py: Python<'py>,
        symbol: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let sym = symbol.as_deref();
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_open_orders(sym, None, None))
                .map_err(to_py_err)
        })?;
        let list = pyo3::types::PyList::new(
            py,
            result.into_iter().map(|o| PyOrder(o).into_pyobject(py).unwrap().into_any().unbind()),
        )?;
        Ok(list.into_any())
    }

    fn cancel_order<'py>(
        &self,
        py: Python<'py>,
        order_id: String,
        symbol: String,
        order_type: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let ot = PyTraderOrderType::new(&order_type)?.0;
        let status = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.cancel_order(&order_id, &symbol, ot))
                .map_err(to_py_err)
        })?;
        PyOrderStatus(status).into_pyobject(py).map(|b| b.into_any())
    }

    fn get_positions<'py>(
        &self,
        py: Python<'py>,
        symbols: Option<Vec<String>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let result = py.allow_threads(|| {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(self.inner.get_positions(symbols))
                .map_err(to_py_err)
        })?;
        let list = pyo3::types::PyList::new(
            py,
            result.into_iter().map(|p| PyPosition(p).into_pyobject(py).unwrap().into_any().unbind()),
        )?;
        Ok(list.into_any())
    }

    fn __repr__(&self) -> String {
        format!("CcxtConnector(exchange={})", self.inner.get_name())
    }
}

// ============================================================
// Module registration
// ============================================================

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Enums
    m.add_class::<PyTradeOrderSide>()?;
    m.add_class::<PyTraderOrderType>()?;
    m.add_class::<PyOrderStatus>()?;
    m.add_class::<PyExchangeTypes>()?;
    m.add_class::<PyTimeFrame>()?;
    m.add_class::<PyMarginType>()?;
    m.add_class::<PyPositionSide>()?;

    // Config
    m.add_class::<PyExchangeCredentials>()?;
    m.add_class::<PyProxyConfig>()?;
    m.add_class::<PyExchangeConfig>()?;

    // Data types
    m.add_class::<PyCandle>()?;
    m.add_class::<PyTicker>()?;
    m.add_class::<PyOrderBook>()?;
    m.add_class::<PyCurrencyBalance>()?;
    m.add_class::<PyOrder>()?;
    m.add_class::<PyPosition>()?;

    // Connector
    m.add_class::<PyCcxtConnector>()?;

    Ok(())
}
