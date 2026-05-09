// Shared helpers for exchange integration tests.

use async_trait::async_trait;
use octobot_connectors_core::config::{ExchangeConfig, ExchangeCredentials};
use octobot_connectors_core::connector::ccxt::CcxtConnector;
use octobot_connectors_core::connector::Exchange;
use octobot_connectors_core::enums::ExchangeTypes;
use octobot_connectors_core::tests::exchange_test_framework::{
    ExchangeTestConfig, ExchangeTestRunner, FuturesExchangeTestRunner,
};

pub struct SimpleExchangeTester {
    pub config: ExchangeTestConfig,
    api_key_env: String,
    secret_env: String,
    password_env: Option<String>,
}

impl SimpleExchangeTester {
    pub fn spot(
        exchange: &str,
        symbol: &str,
        order_currency: &str,
        settlement_currency: &str,
        order_size_pct: f64,
        order_price_diff_pct: f64,
    ) -> Self {
        Self {
            config: ExchangeTestConfig {
                exchange_name: exchange.into(),
                exchange_type: ExchangeTypes::Spot,
                symbol: symbol.into(),
                order_currency: order_currency.into(),
                settlement_currency: settlement_currency.into(),
                order_size_pct,
                order_price_diff_pct,
                ..Default::default()
            },
            api_key_env: format!("{}_API_KEY", exchange.to_uppercase()),
            secret_env: format!("{}_API_SECRET", exchange.to_uppercase()),
            password_env: None,
        }
    }

    pub fn future(
        exchange: &str,
        symbol: &str,
        order_currency: &str,
        settlement_currency: &str,
        order_size_pct: f64,
        order_price_diff_pct: f64,
    ) -> Self {
        Self {
            config: ExchangeTestConfig {
                exchange_name: exchange.into(),
                exchange_type: ExchangeTypes::Future,
                symbol: symbol.into(),
                order_currency: order_currency.into(),
                settlement_currency: settlement_currency.into(),
                order_size_pct,
                order_price_diff_pct,
                ..Default::default()
            },
            api_key_env: format!("{}_API_KEY", exchange.to_uppercase()),
            secret_env: format!("{}_API_SECRET", exchange.to_uppercase()),
            password_env: None,
        }
    }

    pub fn with_api_key_env(mut self, env: &str) -> Self {
        self.api_key_env = env.into();
        self
    }

    pub fn with_secret_env(mut self, env: &str) -> Self {
        self.secret_env = env.into();
        self
    }

    pub fn with_password_env(mut self, env: &str) -> Self {
        self.password_env = Some(env.into());
        self
    }
}

#[async_trait(?Send)]
impl ExchangeTestRunner for SimpleExchangeTester {
    fn config(&self) -> &ExchangeTestConfig {
        &self.config
    }

    async fn create_exchange(&self) -> Box<dyn Exchange> {
        let creds = ExchangeCredentials {
            api_key: std::env::var(&self.api_key_env).ok(),
            secret: std::env::var(&self.secret_env).ok(),
            password: self
                .password_env
                .as_ref()
                .and_then(|e| std::env::var(e).ok()),
            ..Default::default()
        };
        let is_future = self.config.exchange_type == ExchangeTypes::Future;
        let cfg = ExchangeConfig {
            exchange_name: self.config.exchange_name.clone(),
            credentials: creds,
            is_future,
            ..ExchangeConfig::new(&self.config.exchange_name)
        };
        let mut connector = CcxtConnector::new(cfg);
        connector
            .initialize()
            .await
            .expect("Failed to initialize exchange");
        Box::new(connector)
    }
}

impl FuturesExchangeTestRunner for SimpleExchangeTester {}

// Macro to generate standard spot test functions.
// Expects `fn tester() -> SimpleExchangeTester` to exist in the calling module.
#[macro_export]
macro_rules! gen_spot_tests {
    () => {
        #[tokio::test]
        async fn test_get_symbol_prices() {
            tester().run_test_get_symbol_prices().await;
        }

        #[tokio::test]
        async fn test_get_order_book() {
            tester().run_test_get_order_book().await;
        }

        #[tokio::test]
        async fn test_get_recent_trades() {
            tester().run_test_get_recent_trades().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_portfolio() {
            tester().run_test_get_portfolio().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_open_orders() {
            tester().run_test_get_open_orders().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_create_and_cancel_limit_order() {
            tester().run_test_create_and_cancel_limit_order().await;
        }
    };
}

// Macro for futures-specific tests (positions, leverage, funding rate).
// Expects `fn tester() -> SimpleExchangeTester` to exist in the calling module.
#[macro_export]
macro_rules! gen_futures_only_tests {
    () => {
        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_positions() {
            tester().run_test_get_positions().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_and_set_leverage() {
            tester().run_test_get_and_set_leverage().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_set_margin_type() {
            tester().run_test_set_margin_type().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_funding_rate() {
            tester().run_test_get_funding_rate().await;
        }

        #[tokio::test]
        #[ignore = "requires live credentials"]
        async fn test_get_mark_price() {
            tester().run_test_get_mark_price().await;
        }
    };
}
