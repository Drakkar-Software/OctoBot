mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::ExchangeTestRunner;

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::spot("hyperliquid", "ETH/USDC", "ETH", "USDC", 25.0, 10.0)
}

crate::gen_spot_tests!();
