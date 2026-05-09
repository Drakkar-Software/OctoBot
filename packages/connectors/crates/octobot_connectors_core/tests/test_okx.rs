mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::{ExchangeTestRunner, FuturesExchangeTestRunner};

mod spot {
    use super::*;

    fn tester() -> SimpleExchangeTester {
        SimpleExchangeTester::spot("okx", "BTC/USDT", "BTC", "USDT", 50.0, 10.0)
    }

    crate::gen_spot_tests!();
}

mod futures_basic {
    use super::*;

    fn tester() -> SimpleExchangeTester {
        SimpleExchangeTester::future("okx", "DOT/USDT:USDT", "DOT", "USDT", 50.0, 10.0)
    }

    #[tokio::test]
    async fn test_get_symbol_prices() {
        tester().run_test_get_symbol_prices().await;
    }

    #[tokio::test]
    #[ignore = "requires live credentials"]
    async fn test_get_positions() {
        tester().run_test_get_positions().await;
    }

    #[tokio::test]
    #[ignore = "requires live credentials"]
    async fn test_get_funding_rate() {
        tester().run_test_get_funding_rate().await;
    }
}
