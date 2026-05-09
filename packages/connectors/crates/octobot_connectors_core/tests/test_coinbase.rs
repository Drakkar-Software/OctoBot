mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::ExchangeTestRunner;

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::spot("coinbase", "ADA/USDC", "ADA", "USDC", 70.0, 10.0)
}

crate::gen_spot_tests!();
