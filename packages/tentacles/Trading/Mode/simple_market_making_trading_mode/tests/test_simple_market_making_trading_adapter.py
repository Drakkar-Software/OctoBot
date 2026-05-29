# Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import mock
import pytest

import octobot.automation.automation as automation_module
import octobot_commons.constants as commons_constants
import octobot_commons.profiles
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter as simple_market_making_profile_data_adapter
from tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading import SimpleMarketMakingTradingMode
import tentacles.Automation.trigger_events.volatility_threshold_event.volatility_threshold as volatility_threshold_module
import tentacles.Automation.trigger_events.holding_threshold_event.holding_threshold as holding_threshold_module
import tentacles.Automation.conditions.no_condition_condition.no_condition as no_condition_module
import tentacles.Automation.actions.stop_strategies_and_pause_trader_action.stop_strategies_and_pause_trader as stop_action_module


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def authenticator():
    return mock.Mock()

@pytest.fixture
def adapter(authenticator):
    tentacles_data = []
    additional_data = {}
    authenticator = authenticator
    auth_key = None
    return simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter(
        tentacles_data, additional_data, authenticator, auth_key
    )

@pytest.fixture
def auth_data():
    return [
        octobot_commons.profiles.exchange_auth_data.ExchangeAuthData(
            internal_name="binance",
            exchange_credential_id="1234567890",
            exchange_type="spot",
        )
    ]

@pytest.fixture
def profile_data():
    return octobot_commons.profiles.profile_data.ProfileData(
        profile_details=octobot_commons.profiles.profile_data.ProfileDetailsData(
            bot_id="1234567890",
        ),
        exchanges=[
            octobot_commons.profiles.ExchangeData(
                internal_name="binance",
                exchange_account_id="1234567890",
            )
        ],
    )


class TestAdapt:
    @staticmethod
    def _build_exchange_configs():
        return [
            {
                simple_market_making_profile_data_adapter.NAME: "binance",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: "cred-1",
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: "acc-1",
                simple_market_making_profile_data_adapter.SANDBOXED: False,
                simple_market_making_profile_data_adapter.EXCHANGE_TYPE: commons_constants.DEFAULT_EXCHANGE_TYPE,
                simple_market_making_profile_data_adapter.URL: "https://api.binance.com",
            },
            {
                simple_market_making_profile_data_adapter.NAME: "kucoin",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: None,
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: None,
                simple_market_making_profile_data_adapter.SANDBOXED: False,
                simple_market_making_profile_data_adapter.EXCHANGE_TYPE: commons_constants.DEFAULT_EXCHANGE_TYPE,
                simple_market_making_profile_data_adapter.URL: None,
            },
        ]

    @staticmethod
    def _build_pair_configs(pair: str = "BTC/USDT", reference_exchange: str = "kucoin"):
        return [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: pair,
                SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        SimpleMarketMakingTradingMode.EXCHANGE: reference_exchange,
                        SimpleMarketMakingTradingMode.PAIR: pair,
                        SimpleMarketMakingTradingMode.WEIGHT: 1,
                    }
                ],
                SimpleMarketMakingTradingMode.MAX_BASE_BUDGET: 0.1,
                SimpleMarketMakingTradingMode.MAX_QUOTE_BUDGET: 3000,
            }
        ]

    async def test_adapt_uses_direct_exchange_configs_and_registers_helpers(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs()
        mm_tentacle_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}

        adapter.tentacles_data.append(octobot_commons.profiles.profile_data.TentaclesData(
            name=SimpleMarketMakingTradingMode.get_name(),
            config=mm_tentacle_config,
        ))
        register_exchange_configs_mock = mock.Mock()
        register_automations_config_mock = mock.Mock()
        should_fill_exchange_auth_mock = mock.Mock(return_value=False)

        adapter._register_exchange_configs = register_exchange_configs_mock  # type: ignore
        adapter._register_automations_config = register_automations_config_mock  # type: ignore
        adapter._should_fill_exchange_auth = should_fill_exchange_auth_mock  # type: ignore

        # ensure usd-like symbol selection is deterministic
        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            await adapter.adapt(profile_data, auth_data)

        assert profile_data.trading.paused is False
        assert profile_data.trader.enabled is True
        assert profile_data.trader_simulator.enabled is False

        traded_pairs = {c.name for c in profile_data.crypto_currencies}
        assert traded_pairs == {"BTC/USDT"}

        assert ["binance", "kucoin"] == sorted([e.internal_name for e in profile_data.exchanges])

        register_exchange_configs_mock.assert_called_once_with(profile_data, exchange_configs)
        register_automations_config_mock.assert_called_once_with(profile_data, pair_configs)
        should_fill_exchange_auth_mock.assert_called_once_with()

    async def test_adapt_uses_legacy_exchange_configs_when_exchanges_missing(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            # exchange configs are stored in options
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.OPTIONS.value
        ] = {simple_market_making_profile_data_adapter.EXCHANGE_CONFIGS: exchange_configs}

        pair_configs = self._build_pair_configs()
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}

        get_config_mock = mock.Mock(return_value=mm_config)
        register_exchange_configs_mock = mock.Mock()
        register_automations_config_mock = mock.Mock()

        adapter._get_simple_market_making_tentacle_config = get_config_mock  # type: ignore
        adapter._register_exchange_configs = register_exchange_configs_mock  # type: ignore
        adapter._register_automations_config = register_automations_config_mock  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            await adapter.adapt(profile_data, auth_data)

        register_exchange_configs_mock.assert_called_once_with(profile_data, exchange_configs)
        register_automations_config_mock.assert_called_once_with(profile_data, pair_configs)

    async def test_adapt_with_empty_additional_data_uses_profile_exchanges(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        adapter.additional_data.clear()
        pair_configs = self._build_pair_configs(reference_exchange="binance")
        mm_tentacle_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}
        adapter.tentacles_data = [
            octobot_commons.profiles.profile_data.TentaclesData(
                name=SimpleMarketMakingTradingMode.get_name(),
                config=mm_tentacle_config,
            )
        ]
        register_exchange_configs_mock = mock.Mock()
        register_automations_config_mock = mock.Mock()
        adapter._register_exchange_configs = register_exchange_configs_mock  # type: ignore
        adapter._register_automations_config = register_automations_config_mock  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        expected_exchange_names = [exchange.internal_name for exchange in profile_data.exchanges]

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            await adapter.adapt(profile_data, auth_data)

        assert [exchange.internal_name for exchange in profile_data.exchanges] == expected_exchange_names
        traded_pairs = {currency.name for currency in profile_data.crypto_currencies}
        assert traded_pairs == {"BTC/USDT"}
        register_exchange_configs_mock.assert_not_called()
        register_automations_config_mock.assert_called_once_with(profile_data, pair_configs)

        mm_tentacle_configs = [
            tentacle.config
            for tentacle in profile_data.tentacles
            if tentacle.name == SimpleMarketMakingTradingMode.get_name()
        ]
        assert len(mm_tentacle_configs) == 1
        for pair_setting in mm_tentacle_configs[0][SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS]:
            for ref in pair_setting[SimpleMarketMakingTradingMode.REFERENCE_PRICE]:
                assert (
                    ref[SimpleMarketMakingTradingMode.EXCHANGE]
                    in expected_exchange_names
                )

    async def test_adapt_with_empty_additional_data_raises_when_profile_has_no_exchanges(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        profile_data.exchanges = []
        adapter.additional_data.clear()
        pair_configs = self._build_pair_configs(reference_exchange="binance")
        mm_tentacle_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}
        adapter.tentacles_data = [
            octobot_commons.profiles.profile_data.TentaclesData(
                name=SimpleMarketMakingTradingMode.get_name(),
                config=mm_tentacle_config,
            )
        ]
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            with pytest.raises(
                ValueError,
                match="No exchanges found in profile data and no exchange",
            ):
                await adapter.adapt(profile_data, auth_data)

    async def test_adapt_sets_reference_market_from_usd_like_symbol(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs(pair="ETH/USDT")
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}
        adapter._get_simple_market_making_tentacle_config = mock.Mock(return_value=mm_config)  # type: ignore
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        usd_like_mock = mock.Mock(return_value="USDT")
        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            usd_like_mock,
        ):
            await adapter.adapt(profile_data, auth_data)

        usd_like_mock.assert_called_once_with(["ETH/USDT"])
        assert profile_data.trading.reference_market == "USDT"

    async def test_adapt_sets_reference_market_from_first_pair_quote_on_value_error(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs(pair="XRP/USDT")
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}
        adapter._get_simple_market_making_tentacle_config = mock.Mock(return_value=mm_config)  # type: ignore
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        def _raise_value_error(_):
            raise ValueError("no usd like")

        class ParsedSymbol:
            def __init__(self, quote):
                self.quote = quote

        parse_symbol_mock = mock.Mock(return_value=ParsedSymbol("USDT"))

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(side_effect=_raise_value_error),
        ), mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.parse_symbol",
            parse_symbol_mock,
        ):
            await adapter.adapt(profile_data, auth_data)

        parse_symbol_mock.assert_called_once_with("XRP/USDT")
        assert profile_data.trading.reference_market == "USDT"

    async def test_adapt_pauses_trading_when_bot_should_not_trade(self, adapter, profile_data, auth_data):
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs()
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}

        adapter._get_simple_market_making_tentacle_config = mock.Mock(return_value=mm_config)  # type: ignore
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        adapter.authenticator.user_account.bot_id = "different"
        adapter.authenticator.select_bot = mock.AsyncMock()
        community_bot = mock.Mock()
        community_bot.should_trade_according_to_products_subscription_and_deployment_error_status = mock.AsyncMock(
            return_value=False
        )
        adapter.authenticator.community_bot = community_bot

        profile_data.crypto_currencies = []

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            await adapter.adapt(profile_data, auth_data)

        adapter.authenticator.select_bot.assert_awaited_once_with(profile_data.profile_details.bot_id)
        community_bot.should_trade_according_to_products_subscription_and_deployment_error_status.assert_awaited_once_with()
        assert profile_data.trading.paused is True
        assert profile_data.crypto_currencies == []

    async def test_adapt_adds_exchange_auth_when_required(self, adapter, profile_data, auth_data):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs()
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}

        adapter._get_simple_market_making_tentacle_config = mock.Mock(return_value=mm_config)  # type: ignore
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=True)  # type: ignore
        adapter._add_exchange_auth = mock.AsyncMock()  # type: ignore

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.get_most_common_usd_like_symbol",
            mock.Mock(return_value="USDT"),
        ):
            await adapter.adapt(profile_data, auth_data)

        adapter._add_exchange_auth.assert_awaited_once()  # type: ignore
        call_args = adapter._add_exchange_auth.await_args  # type: ignore
        assert call_args.args[0] is profile_data
        assert call_args.args[1] is auth_data
        base_exchange_auth_datas = call_args.args[2]
        assert {a.internal_name for a in base_exchange_auth_datas} == {
            cfg[simple_market_making_profile_data_adapter.NAME] for cfg in exchange_configs
        }

    async def test_adapt_simulated_trading_fills_simulator_portfolio(
        self, adapter, profile_data, auth_data
    ):
        profile_data.profile_details.bot_id = None
        exchange_configs = self._build_exchange_configs()
        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.EXCHANGES.value
        ] = exchange_configs

        pair_configs = self._build_pair_configs(pair="BTC/USDT")
        mm_config = {SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: pair_configs}

        adapter._get_simple_market_making_tentacle_config = mock.Mock(return_value=mm_config)  # type: ignore
        adapter._register_exchange_configs = mock.Mock()  # type: ignore
        adapter._register_automations_config = mock.Mock()  # type: ignore
        adapter._should_fill_exchange_auth = mock.Mock(return_value=False)  # type: ignore

        adapter.additional_data[
            simple_market_making_profile_data_adapter.community_enums.BotConfigKeys.IS_SIMULATED.value
        ] = True

        with mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.commons_logging.get_logger",
            mock.Mock(return_value=mock.Mock()),
        ), mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.symbols_util.parse_symbol",
            mock.Mock(return_value=type("Parsed", (), {"base": "BTC", "quote": "USDT"})()),
        ), mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.octobot_commons.constants.IS_DEV_MODE_ENABLED",
            True,
        ):
            await adapter.adapt(profile_data, auth_data)

        assert profile_data.trader.enabled is False
        assert profile_data.trader_simulator.enabled is True
        assert profile_data.trader_simulator.starting_portfolio["BTC"] == 0.1
        assert profile_data.trader_simulator.starting_portfolio["USDT"] == 3000


class TestRegisterExchangeConfigs:
    def test_register_exchange_configs_adds_hollaex_autofilled_with_auth_and_url(self, adapter, profile_data):
        exchange_url = "https://api.binance.com"
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "binance",
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: "acc-1",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: "cred-1",
                simple_market_making_profile_data_adapter.URL: exchange_url,
            }
        ]

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=True,
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]

        # force auth flag is set
        assert tentacle.config[commons_constants.CONFIG_FORCE_AUTHENTICATION] is True

        # there should be exactly one other key containing auto-filled config
        other_keys = [k for k in tentacle.config.keys() if k != commons_constants.CONFIG_FORCE_AUTHENTICATION]
        assert len(other_keys) == 1
        auto_filled = tentacle.config[other_keys[0]]

        # auto-filled mapping must target the first exchange internal name
        assert list(auto_filled.keys()) == [profile_data.exchanges[0].internal_name]
        url_mapping = auto_filled[profile_data.exchanges[0].internal_name]
        # url_mapping should contain exactly the exchange URL
        assert list(url_mapping.values()) == [exchange_url]

    def test_register_exchange_configs_adds_hollaex_autofilled_without_force_auth_when_not_required(
        self, adapter, profile_data
    ):
        exchange_url = "https://api.binance.com"
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "binance",
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: "acc-1",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: "cred-1",
                simple_market_making_profile_data_adapter.URL: exchange_url,
            }
        ]

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=False,
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]

        # no forced authentication flag
        assert commons_constants.CONFIG_FORCE_AUTHENTICATION not in tentacle.config

        # config must still contain auto-filled URL mapping
        assert len(tentacle.config) == 1
        (auto_key,) = tentacle.config.keys()
        auto_filled = tentacle.config[auto_key]
        assert list(auto_filled.keys()) == [profile_data.exchanges[0].internal_name]
        url_mapping = auto_filled[profile_data.exchanges[0].internal_name]
        assert list(url_mapping.values()) == [exchange_url]

    def test_register_exchange_configs_adds_script_tentacle_when_requires_auth_without_url(
        self, adapter, profile_data
    ):
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "binance",
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: "acc-1",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: "cred-1",
            }
        ]

        class DummyExchangeTentacle:
            pass

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=True,
        ), mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.scripting_library.get_exchange_tentacle_from_name",
            mock.Mock(return_value=DummyExchangeTentacle),
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        assert tentacle.name == DummyExchangeTentacle.__name__
        assert tentacle.config == {commons_constants.CONFIG_FORCE_AUTHENTICATION: True}

    def test_register_exchange_configs_ignores_config_without_url_or_auth(self, adapter, profile_data):
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "binance",
                # no URL, no account id, no credential id
            }
        ]

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=False,
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        # no tentacle added
        assert profile_data.tentacles == []

    def test_register_exchange_configs_adds_force_auth_tentacle(self, adapter, profile_data):
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "dexscreener",
                simple_market_making_profile_data_adapter.EXCHANGE_ACCOUNT_ID: "acc-1",
                simple_market_making_profile_data_adapter.EXCHANGE_CREDENTIAL_ID: "cred-1",
            }
        ]

        class DummyExchangeTentacle:
            pass

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=True,
        ), mock.patch(
            "tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_profile_data_adapter.scripting_library.get_exchange_tentacle_from_name",
            mock.Mock(return_value=DummyExchangeTentacle),
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        assert tentacle.name == DummyExchangeTentacle.__name__
        assert tentacle.config == {commons_constants.CONFIG_FORCE_AUTHENTICATION: True}

    def test_register_exchange_configs_with_hollaex_url(self, adapter, profile_data):
        exchange_url = "https://api.dexscreener.com"
        exchange_configs = [
            {
                simple_market_making_profile_data_adapter.NAME: "dexscreener",
                simple_market_making_profile_data_adapter.URL: exchange_url,
            }
        ]

        with mock.patch.object(
            simple_market_making_profile_data_adapter.SimpleMarketMakingProfileDataAdapter,
            "exchange_config_requires_exchange_auth",
            return_value=False,
        ):
            adapter._register_exchange_configs(profile_data, exchange_configs)  # type: ignore

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]

        auto_filled_keys = list(tentacle.config.keys())
        assert len(auto_filled_keys) == 1
        auto_filled = tentacle.config[auto_filled_keys[0]]
        assert list(auto_filled.keys()) == [profile_data.exchanges[0].internal_name]
        url_mapping = auto_filled[profile_data.exchanges[0].internal_name]
        assert list(url_mapping.values()) == [exchange_url]


class TestRegisterAutomationsConfig:
    def test_register_automations_config_adds_volatility_automation(self, adapter, profile_data):
        pair_configs = [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                SimpleMarketMakingTradingMode.EXCHANGE: "",
                "stop_conditions": {
                    "max_positive_percent_price_change": 10,
                    "max_negative_percent_price_change": 5,
                    "average_price_counted_minutes": 30,
                },
            }
        ]

        adapter._register_automations_config(profile_data, pair_configs)

        # one automation tentacle added
        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        assert tentacle.name == automation_module.Automation.get_name()

        config = tentacle.config
        automations = config[automation_module.Automation.AUTOMATIONS]
        assert config[automation_module.Automation.AUTOMATIONS_COUNT] == len(automations) == 1
        assert automations == {
            "1": {
                "trigger_event": volatility_threshold_module.VolatilityThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                volatility_threshold_module.VolatilityThreshold.get_name(): {
                    volatility_threshold_module.VolatilityThreshold.EXCHANGE: "binance",
                    volatility_threshold_module.VolatilityThreshold.SYMBOL: "BTC/USDT",
                    volatility_threshold_module.VolatilityThreshold.PERIOD_IN_MINUTES: 30,
                    volatility_threshold_module.VolatilityThreshold.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE: 10,
                    volatility_threshold_module.VolatilityThreshold.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE: 5,
                },
            }
        }

    def test_register_automations_config_volatility_still_parses_legacy_average_prive_key(
        self, adapter, profile_data
    ):
        pair_configs = [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                SimpleMarketMakingTradingMode.EXCHANGE: "",
                "stop_conditions": {
                    "max_positive_percent_price_change": 10,
                    "max_negative_percent_price_change": 5,
                    "average_prive_counted_minutes": 30,
                },
            }
        ]

        adapter._register_automations_config(profile_data, pair_configs)

        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        automations = tentacle.config[automation_module.Automation.AUTOMATIONS]
        volatility_cfg = automations["1"][volatility_threshold_module.VolatilityThreshold.get_name()]
        assert volatility_cfg[volatility_threshold_module.VolatilityThreshold.PERIOD_IN_MINUTES] == 30

    def test_register_automations_config_adds_holding_threshold_automations_for_base_and_quote(
        self, adapter, profile_data
    ):
        pair_configs = [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                SimpleMarketMakingTradingMode.EXCHANGE: "",
                "stop_conditions": {
                    "min_base_holding": 1,
                    "min_quote_holding": 2,
                },
            }
        ]

        adapter._register_automations_config(profile_data, pair_configs)

        # expecting a single automations tentacle
        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        assert tentacle.name == automation_module.Automation.get_name()

        automations = tentacle.config[automation_module.Automation.AUTOMATIONS]
        # both base and quote thresholds should have created entries
        assert len(automations) == 2
        assert automations == {
            "1": {
                "trigger_event": holding_threshold_module.HoldingThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                holding_threshold_module.HoldingThreshold.get_name(): {
                    holding_threshold_module.HoldingThreshold.AMOUNT: 1,
                    holding_threshold_module.HoldingThreshold.ASSET_NAME: "BTC",
                    holding_threshold_module.HoldingThreshold.EXCHANGE: "binance",
                    holding_threshold_module.HoldingThreshold.STOP_ON_INFERIOR: True,
                },
            },
            "2": {
                "trigger_event": holding_threshold_module.HoldingThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                holding_threshold_module.HoldingThreshold.get_name(): {
                    holding_threshold_module.HoldingThreshold.AMOUNT: 2,
                    holding_threshold_module.HoldingThreshold.ASSET_NAME: "USDT",
                    holding_threshold_module.HoldingThreshold.EXCHANGE: "binance",
                    holding_threshold_module.HoldingThreshold.STOP_ON_INFERIOR: True,
                },
            }
        }

    def test_register_automations_config_adds_holding_threshold_automations_for_base_and_quote_and_volatility_threshold(self, adapter, profile_data):
        pair_configs = [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                SimpleMarketMakingTradingMode.EXCHANGE: "",
                "stop_conditions": {
                    "min_base_holding": 1,
                    "min_quote_holding": 2,
                    "max_positive_percent_price_change": 10,
                    "max_negative_percent_price_change": 5,
                    "average_price_counted_minutes": 30,
                },
            }
        ]

        adapter._register_automations_config(profile_data, pair_configs)

        # expecting a single automations tentacle
        assert len(profile_data.tentacles) == 1
        tentacle = profile_data.tentacles[0]
        assert tentacle.name == automation_module.Automation.get_name()

        automations = tentacle.config[automation_module.Automation.AUTOMATIONS]
        assert len(automations) == 3
        assert automations == {
            "1": {
                "trigger_event": volatility_threshold_module.VolatilityThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                volatility_threshold_module.VolatilityThreshold.get_name(): {
                    volatility_threshold_module.VolatilityThreshold.EXCHANGE: "binance",
                    volatility_threshold_module.VolatilityThreshold.SYMBOL: "BTC/USDT",
                    volatility_threshold_module.VolatilityThreshold.PERIOD_IN_MINUTES: 30,
                    volatility_threshold_module.VolatilityThreshold.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE: 10,
                    volatility_threshold_module.VolatilityThreshold.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE: 5,
                },
            },
            "2": {
                "trigger_event": holding_threshold_module.HoldingThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                holding_threshold_module.HoldingThreshold.get_name(): {
                    holding_threshold_module.HoldingThreshold.AMOUNT: 1,
                    holding_threshold_module.HoldingThreshold.ASSET_NAME: "BTC",
                    holding_threshold_module.HoldingThreshold.EXCHANGE: "binance",
                    holding_threshold_module.HoldingThreshold.STOP_ON_INFERIOR: True,
                },
            },
            "3": {
                "trigger_event": holding_threshold_module.HoldingThreshold.get_name(),
                "conditions": [no_condition_module.NoCondition.get_name()],
                "actions": [stop_action_module.StopStrategiesAndPauseTrader.get_name()],
                no_condition_module.NoCondition.get_name(): {},
                stop_action_module.StopStrategiesAndPauseTrader.get_name(): {},
                holding_threshold_module.HoldingThreshold.get_name(): {
                    holding_threshold_module.HoldingThreshold.AMOUNT: 2,
                    holding_threshold_module.HoldingThreshold.ASSET_NAME: "USDT",
                    holding_threshold_module.HoldingThreshold.EXCHANGE: "binance",
                    holding_threshold_module.HoldingThreshold.STOP_ON_INFERIOR: True,
                },
            },
        }

    def test_register_automations_config_ignores_pairs_without_stop_conditions(self, adapter, profile_data):
        pair_configs = [
            {
                SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                SimpleMarketMakingTradingMode.EXCHANGE: "",
                # no "stop_conditions" key
            }
        ]

        adapter._register_automations_config(profile_data, pair_configs)

        # no automations => no tentacles added
        assert profile_data.tentacles == []
