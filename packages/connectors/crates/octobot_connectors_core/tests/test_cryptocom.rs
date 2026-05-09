mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::ExchangeTestRunner;

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::spot("cryptocom", "BTC/USDT", "BTC", "USDT", 70.0, 10.0)
}

crate::gen_spot_tests!();
