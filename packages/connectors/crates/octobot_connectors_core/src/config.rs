// Translated from:
//   packages/trading/octobot_trading/exchanges/config/exchange_credentials_data.py
//   packages/trading/octobot_trading/exchanges/config/proxy_config.py
//   packages/trading/octobot_trading/exchanges/config/exchange_config_data.py

use std::collections::HashMap;

/// API credentials for an exchange — matches ExchangeCredentialsData
#[derive(Debug, Clone, Default)]
pub struct ExchangeCredentials {
    /// CEX REST / WS API key
    pub api_key: Option<String>,
    pub secret: Option<String>,
    /// Some exchanges require a passphrase (e.g., OKX, KuCoin)
    pub password: Option<String>,
    /// UID (some exchanges use this instead of key)
    pub uid: Option<String>,
    /// OAuth bearer token (alternative auth)
    pub auth_token: Option<String>,
    pub auth_token_header_prefix: Option<String>,
    /// DEX wallet credentials
    pub wallet_address: Option<String>,
    pub private_key: Option<String>,
}

impl ExchangeCredentials {
    pub fn has_credentials(&self) -> bool {
        (self.api_key.is_some() && self.secret.is_some())
            || (self.wallet_address.is_some() && self.private_key.is_some())
            || self.auth_token.is_some()
    }

    pub fn is_empty(&self) -> bool {
        !self.has_credentials()
    }

    pub fn sanitized_api_key(&self) -> Option<String> {
        self.api_key.as_ref().map(|k| {
            if k.len() > 8 {
                format!("{}...{}", &k[..4], &k[k.len()-4..])
            } else {
                "****".to_string()
            }
        })
    }
}

/// Proxy configuration — matches ProxyConfig in proxy_config.py
#[derive(Debug, Clone, Default)]
pub struct ProxyConfig {
    pub http_proxy: Option<String>,
    pub https_proxy: Option<String>,
    pub socks_proxy: Option<String>,
    pub ws_proxy: Option<String>,
    pub wss_proxy: Option<String>,
    pub ws_socks_proxy: Option<String>,
    pub aiohttp_trust_env: bool,
    pub proxy_host: Option<String>,
    /// When true, only authenticated requests go through the proxy
    pub use_authenticated_exchange_requests_only_proxy: bool,
}

impl ProxyConfig {
    pub fn has_rest_proxy(&self) -> bool {
        self.http_proxy.is_some() || self.https_proxy.is_some() || self.socks_proxy.is_some()
    }

    pub fn has_websocket_proxy(&self) -> bool {
        self.ws_proxy.is_some() || self.wss_proxy.is_some() || self.ws_socks_proxy.is_some()
    }

    pub fn has_proxy(&self) -> bool {
        self.has_rest_proxy() || self.has_websocket_proxy()
    }
}

/// Exchange-level configuration (mode flags, credentials, traded symbols)
/// Encompasses ExchangeManager-level settings from the Python side.
#[derive(Debug, Clone)]
pub struct ExchangeConfig {
    /// Exchange name as recognised by ccxt (e.g., "binanceus", "bybit")
    pub exchange_name: String,
    pub credentials: ExchangeCredentials,
    pub proxy: Option<ProxyConfig>,
    /// Whether to use the exchange sandbox / testnet
    pub is_sandboxed: bool,
    /// Whether this is a simulated (backtesting) exchange
    pub is_simulated: bool,
    /// Whether running in backtesting mode
    pub is_backtesting: bool,
    /// Futures trading
    pub is_future: bool,
    /// Options trading
    pub is_option: bool,
    /// Spot-only mode
    pub is_spot_only: bool,
    /// When true, the connector is created for a one-off query (exchange_only mode)
    pub exchange_only: bool,
    /// Re-use already loaded market status cache
    pub use_cached_markets: bool,
    /// Extra ccxt client options
    pub options: HashMap<String, serde_json::Value>,
    /// Extra HTTP headers
    pub headers: HashMap<String, String>,
    /// Symbols to monitor / trade (if empty, all available symbols are used)
    pub traded_symbol_pairs: Vec<String>,
    /// Time frames to watch
    pub traded_time_frames: Vec<String>,
}

impl ExchangeConfig {
    pub fn new(exchange_name: impl Into<String>) -> Self {
        Self {
            exchange_name: exchange_name.into(),
            credentials: ExchangeCredentials::default(),
            proxy: None,
            is_sandboxed: false,
            is_simulated: false,
            is_backtesting: false,
            is_future: false,
            is_option: false,
            is_spot_only: true,
            exchange_only: false,
            use_cached_markets: false,
            options: HashMap::new(),
            headers: HashMap::new(),
            traded_symbol_pairs: vec![],
            traded_time_frames: vec![],
        }
    }

    pub fn with_credentials(mut self, creds: ExchangeCredentials) -> Self {
        self.credentials = creds;
        self
    }

    pub fn with_sandbox(mut self, sandboxed: bool) -> Self {
        self.is_sandboxed = sandboxed;
        self
    }

    pub fn should_authenticate(&self) -> bool {
        self.credentials.has_credentials() && !self.is_simulated && !self.is_backtesting
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_credentials_empty() {
        assert!(ExchangeCredentials::default().is_empty());
    }

    #[test]
    fn test_credentials_with_keys() {
        let creds = ExchangeCredentials {
            api_key: Some("mykey1234abcd".into()),
            secret: Some("mysecret".into()),
            ..Default::default()
        };
        assert!(creds.has_credentials());
        let sanitized = creds.sanitized_api_key().unwrap();
        assert!(sanitized.contains("..."));
    }

    #[test]
    fn test_proxy_has_proxy() {
        let proxy = ProxyConfig {
            http_proxy: Some("http://proxy:8080".into()),
            ..Default::default()
        };
        assert!(proxy.has_proxy());
        assert!(proxy.has_rest_proxy());
        assert!(!proxy.has_websocket_proxy());
    }

    #[test]
    fn test_exchange_config_defaults() {
        let cfg = ExchangeConfig::new("binance");
        assert_eq!(cfg.exchange_name, "binance");
        assert!(!cfg.is_future);
        assert!(!cfg.should_authenticate());
    }
}
