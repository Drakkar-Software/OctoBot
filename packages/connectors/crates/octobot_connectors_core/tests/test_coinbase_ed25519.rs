mod common;
use common::SimpleExchangeTester;
use octobot_connectors_core::tests::exchange_test_framework::ExchangeTestRunner;

fn tester() -> SimpleExchangeTester {
    SimpleExchangeTester::spot("coinbase", "ADA/USDC", "ADA", "USDC", 70.0, 10.0)
        .with_api_key_env("COINBASE_ED25519_API_KEY")
        .with_secret_env("COINBASE_ED25519_API_SECRET")
}

crate::gen_spot_tests!();
