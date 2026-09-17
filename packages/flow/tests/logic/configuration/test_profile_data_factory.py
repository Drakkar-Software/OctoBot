#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import datetime

import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_flow.entities.accounts.exchange_account_details as exchange_account_details_module
import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module


class TestCreateProfileDataHollaexUrl:
    def test_builds_hollaex_tentacle_config_from_exchange_url(self):
        earn_curve_api_url = "https://www.earncurve.com.au/api"
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(
                internal_name="hollaex",
                url=earn_curve_api_url,
            ),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        profile_data = profile_data_factory_module.create_profile_data(
            exchange_account_details,
            automation_id="automation-hollaex-earncurve",
            symbols={"BTC/USDC"},
            as_simulator=True,
        )
        tentacle_config_by_name = profile_data.get_config_by_tentacle()
        assert "hollaex" in tentacle_config_by_name
        assert tentacle_config_by_name["hollaex"]["rest"] == earn_curve_api_url
        assert tentacle_config_by_name["hollaex"]["has_websockets"] is False

    def test_omits_hollaex_tentacle_when_url_missing(self):
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(
                internal_name="hollaex",
            ),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        profile_data = profile_data_factory_module.create_profile_data(
            exchange_account_details,
            automation_id="automation-hollaex-no-url",
            symbols={"BTC/USDC"},
            as_simulator=True,
        )
        assert profile_data.get_config_by_tentacle() == {}


class TestProfileDataForAccount:
    def test_enables_trader_for_real_account(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            remote_account_id="account-1",
            exchange_config_ids=["exchange-config-1"],
        )
        account = protocol_models.Account(
            id="account-1",
            name="Real account",
            is_simulated=False,
            created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        )
        exchange_config = protocol_models.ExchangeConfig(
            id="exchange-config-1",
            name="binance-main",
            exchange="binanceus",
            sandboxed=False,
        )
        profile_data = profile_data_factory_module.profile_data_for_account(
            account,
            exchange_account,
            exchange_config,
            protocol_models.TradingType.SPOT,
            is_simulated=False,
        )
        assert profile_data.trader.enabled is True
        assert profile_data.trader_simulator.enabled is False
        assert profile_data.exchanges[0].internal_name == "binanceus"

    def test_enables_simulator_for_simulated_account(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            remote_account_id="sim-account-1",
            exchange_config_ids=["exchange-config-1"],
        )
        account = protocol_models.Account(
            id="sim-account-1",
            name="Sim account",
            is_simulated=True,
            created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        )
        exchange_config = protocol_models.ExchangeConfig(
            id="exchange-config-1",
            name="binance-main",
            exchange="binanceus",
            sandboxed=False,
        )
        profile_data = profile_data_factory_module.profile_data_for_account(
            account,
            exchange_account,
            exchange_config,
            protocol_models.TradingType.SPOT,
            is_simulated=True,
        )
        assert profile_data.trader.enabled is False
        assert profile_data.trader_simulator.enabled is True


class TestGetCryptoCurrenciesFromSymbols:
    def test_groups_trading_pairs_under_parsed_base_currency(self):
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(internal_name="coinrabbit"),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        profile_data = profile_data_factory_module.create_profile_data(
            exchange_account_details,
            automation_id="automation-ticker-wise",
            symbols={
                "BTC@BTC/USDT@ETH",
                "ETH@ETH/USDT@ETH",
            },
            as_simulator=True,
        )
        crypto_by_name = {currency.name: currency.trading_pairs for currency in profile_data.crypto_currencies}
        assert crypto_by_name == {
            "BTC@BTC": ["BTC@BTC/USDT@ETH"],
            "ETH@ETH": ["ETH@ETH/USDT@ETH"],
        }


class TestInferReferenceMarket:
    def test_prefers_portfolio_unit_over_symbol_quote_for_ticker_wise_pairs(self):
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(internal_name="coinrabbit"),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
            portfolio=exchange_account_details_module.ExchangeAccountPortfolio(unit="USDT@ETH"),
        )
        crypto_currencies = [
            profile_data_module.CryptoCurrencyData(
                name="BTC@BTC",
                trading_pairs=["BTC@BTC/USDT@ETH"],
            )
        ]
        assert (
            profile_data_factory_module.infer_reference_market(exchange_account_details, crypto_currencies)
            == "USDT@ETH"
        )

    def test_returns_default_reference_market_when_internal_name_missing(self):
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        assert (
            profile_data_factory_module.infer_reference_market(exchange_account_details, [])
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )
