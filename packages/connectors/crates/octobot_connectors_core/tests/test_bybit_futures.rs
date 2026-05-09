mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::{ExchangeTestRunner, FuturesExchangeTestRunner};

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::future("bybit", "BTC/USDT:USDT", "BTC", "USDT", 5.0, 10.0)
}

crate::gen_futures_only_tests!();
