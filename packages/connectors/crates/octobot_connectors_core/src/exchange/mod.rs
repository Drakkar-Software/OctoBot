// Exchange module: high-level exchange types built on top of the connector layer.
// Mirrors the Python types/ directory (rest_exchange.py, websocket_exchange.py).
// The Exchange trait lives in connector/mod.rs; this module provides
// the RestExchange wrapper with config flags and error-detection logic.

pub mod rest_exchange;
