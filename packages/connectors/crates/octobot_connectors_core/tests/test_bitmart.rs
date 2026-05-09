mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::ExchangeTestRunner;

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::spot("bitmart", "BTC/USDT", "BTC", "USDT", 80.0, 10.0)
}

crate::gen_spot_tests!();
