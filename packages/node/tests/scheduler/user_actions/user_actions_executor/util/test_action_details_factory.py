#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import datetime

import mock
import octobot_flow.entities as flow_entities
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config

from ..account import account_executor_test_utils
from . import trading_tentacles_test_utils


_WALLET_ADDRESS = account_executor_test_utils.WALLET_ADDRESS
_ACCOUNT_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _live_exchange_account() -> protocol_models.Account:
    return protocol_models.Account(
        id="acc-1",
        name="Test exchange account",
        is_simulated=False,
        created_at=_ACCOUNT_TIMESTAMP,
        updated_at=_ACCOUNT_TIMESTAMP,
        authentication_id="wallet-auth-id",
        assets=account_executor_test_utils.assets_payload(),
        specifics=protocol_models.AccountSpecifics(
            actual_instance=account_executor_test_utils.exchange_account_payload(),
        ),
    )


def _authentication(
    *,
    api_passphrase: str | None = None,
) -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id="wallet-auth-id",
        api_key="plain-key",
        api_secret="plain-secret",
        api_passphrase=api_passphrase,
    )


def _auth_details_from_result(result: dict) -> exchange_data_module.ExchangeAuthDetails:
    exchange_account_details_dict = result["exchange_account_details"]
    return exchange_data_module.ExchangeAuthDetails.from_dict(
        exchange_account_details_dict["auth_details"],
    )


class TestExchangeProtocolAccountToApplyConfigurationDictEncryptsCredentials:
    def test_encrypts_api_key_and_api_secret(self):
        account = _live_exchange_account()
        authentication = _authentication()
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        with (
            mock.patch.object(
                action_details_factory_module.exchange_account_resolver,
                "get_exchange_config",
                return_value=account_executor_test_utils.exchange_config_payload(),
            ),
            mock.patch.object(
                action_details_factory_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
            mock.patch.object(
                action_details_factory_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
        ):
            result = action_details_factory_module.exchange_protocol_account_to_apply_configuration_dict(
                account,
                user_id=_WALLET_ADDRESS,
            )
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        assert encrypt_mock.call_count == 2
        auth_details = _auth_details_from_result(result)
        assert auth_details.api_key == "enc:plain-key"
        assert auth_details.api_secret == "enc:plain-secret"
        assert auth_details.api_password == ""

    def test_encrypts_passphrase_when_present(self):
        account = _live_exchange_account()
        authentication = _authentication(api_passphrase="plain-pass")
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        with (
            mock.patch.object(
                action_details_factory_module.exchange_account_resolver,
                "get_exchange_config",
                return_value=account_executor_test_utils.exchange_config_payload(),
            ),
            mock.patch.object(
                action_details_factory_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
            mock.patch.object(
                action_details_factory_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
        ):
            result = action_details_factory_module.exchange_protocol_account_to_apply_configuration_dict(
                account,
                user_id=_WALLET_ADDRESS,
            )
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        encrypt_mock.assert_any_call("plain-pass")
        assert encrypt_mock.call_count == 3
        auth_details = _auth_details_from_result(result)
        assert auth_details.api_password == "enc:plain-pass"


class TestExchangeProtocolAccountToApplyConfigurationDictExchangeUrl:
    def test_maps_exchange_config_url_to_exchange_details(self):
        account = account_executor_test_utils.minimal_exchange_account(
            account_id="acc-hollaex-earncurve",
            is_simulated=True,
        )
        earn_curve_api_url = "https://www.earncurve.com.au/api"
        with mock.patch.object(
            action_details_factory_module.exchange_account_resolver,
            "get_exchange_config",
            return_value=protocol_models.ExchangeConfig(
                id="functional-hollaex-exchange-config-id",
                name="earncurve-main",
                exchange="hollaex",
                sandboxed=False,
                url=earn_curve_api_url,
            ),
        ):
            result = action_details_factory_module.exchange_protocol_account_to_apply_configuration_dict(
                account,
                user_id=_WALLET_ADDRESS,
            )
        exchange_details = result["exchange_account_details"]["exchange_details"]
        assert exchange_details["url"] == earn_curve_api_url


def _init_action() -> flow_entities.ConfiguredActionDetails:
    return flow_entities.ConfiguredActionDetails(
        id="action_init",
        action=flow_enums.ActionType.APPLY_CONFIGURATION.value,
        config={},
    )


class TestNormalizeTentacleName:
    def test_camel_case_trading_mode(self):
        assert trading_tentacles_config.normalize_tentacle_name("GridTradingMode") == "grid_trading_mode"

    def test_acronym_camel_case_trading_mode(self):
        assert trading_tentacles_config.normalize_tentacle_name("DCATradingMode") == "d_c_a_trading_mode"

    def test_snake_case_unchanged(self):
        assert trading_tentacles_config.normalize_tentacle_name("grid_trading_mode") == "grid_trading_mode"


class TestNextActionIdForTentacleName:
    def test_camel_case_and_snake_case_produce_same_action_id(self):
        tentacle_name_counters: dict[str, int] = {}
        camel_case_action_id = action_details_factory_module._next_action_id_for_tentacle_name(
            "GridTradingMode",
            tentacle_name_counters,
        )
        snake_case_action_id = action_details_factory_module._next_action_id_for_tentacle_name(
            "grid_trading_mode",
            tentacle_name_counters,
        )
        assert camel_case_action_id == "grid_trading_mode_1"
        assert snake_case_action_id == "grid_trading_mode_2"

    def test_mixed_conventions_share_counter(self):
        tentacle_name_counters: dict[str, int] = {}
        action_details_factory_module._next_action_id_for_tentacle_name(
            "GridTradingMode",
            tentacle_name_counters,
        )
        second_action_id = action_details_factory_module._next_action_id_for_tentacle_name(
            "grid_trading_mode",
            tentacle_name_counters,
        )
        assert second_action_id == "grid_trading_mode_2"


class TestTradingTentaclesActionFactory:
    def test_same_dsl_and_action_id_for_camel_case_and_snake_case_names(self):
        init_action = _init_action()
        camel_case_configuration = trading_tentacles_test_utils.grid_trading_configuration(
            symbol="BTC/USDT",
        )
        snake_case_configuration = camel_case_configuration.model_copy(
            update={"name": "grid_trading_mode"},
        )

        camel_case_action = action_details_factory_module.trading_tentacles_action_factory(
            init_action,
            camel_case_configuration,
        )
        snake_case_action = action_details_factory_module.trading_tentacles_action_factory(
            init_action,
            snake_case_configuration,
        )

        assert camel_case_action.id == trading_tentacles_test_utils.tentacle_action_id(
            grid_trading.GridTradingMode.get_name()
        )
        assert snake_case_action.id == camel_case_action.id
        assert snake_case_action.dsl_script == camel_case_action.dsl_script
        assert camel_case_action.dsl_script.startswith("grid_trading_mode(")


class TestTradingTentaclesWithEvaluatorsActionsFactory:
    def test_same_action_ids_for_camel_case_and_snake_case_names(self):
        init_action = _init_action()
        camel_case_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration()
        snake_case_configuration = camel_case_configuration.model_copy(
            update={
                "name": trading_tentacles_config.normalize_tentacle_name(camel_case_configuration.name),
                "evaluators": [
                    evaluator.model_copy(
                        update={"name": trading_tentacles_config.normalize_tentacle_name(evaluator.name)}
                    )
                    for evaluator in (camel_case_configuration.evaluators or [])
                ],
                "strategies": [
                    strategy.model_copy(
                        update={"name": trading_tentacles_config.normalize_tentacle_name(strategy.name)}
                    )
                    for strategy in (camel_case_configuration.strategies or [])
                ],
            }
        )

        camel_case_actions = action_details_factory_module.trading_tentacles_with_evaluators_actions_factory(
            init_action,
            camel_case_configuration,
        )
        snake_case_actions = action_details_factory_module.trading_tentacles_with_evaluators_actions_factory(
            init_action,
            snake_case_configuration,
        )

        assert {action.id for action in camel_case_actions} == {
            action.id for action in snake_case_actions
        }
        assert trading_tentacles_test_utils.tentacle_action_id(
            momentum_evaluator.RSIMomentumEvaluator.get_name()
        ) in {action.id for action in camel_case_actions}
        assert trading_tentacles_test_utils.tentacle_action_id(
            mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name()
        ) in {action.id for action in camel_case_actions}
        assert trading_tentacles_test_utils.tentacle_action_id(
            dca_trading.DCATradingMode.get_name()
        ) in {action.id for action in camel_case_actions}


class TestCopyActionFactory:
    def test_passes_reference_market_argument_to_dsl(self):
        copy_configuration = protocol_models.CopyConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.COPY,
            strategy_id="copied-strategy",
        )
        copy_action = action_details_factory_module.copy_action_factory(
            _init_action(),
            copy_configuration,
            reference_market="USDT",
        )
        assert copy_action.dsl_script == (
            'copy_exchange_account(strategy_id="copied-strategy", '
            'reference_market="USDT", reference_account=\'\', account_copy_settings=\'{}\')'
        )

    def test_passes_different_reference_market_to_dsl(self):
        copy_configuration = protocol_models.CopyConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.COPY,
            strategy_id="copied-strategy",
        )
        copy_action = action_details_factory_module.copy_action_factory(
            _init_action(),
            copy_configuration,
            reference_market="USDC",
        )
        assert copy_action.dsl_script == (
            'copy_exchange_account(strategy_id="copied-strategy", '
            'reference_market="USDC", reference_account=\'\', account_copy_settings=\'{}\')'
        )


class TestGenericProcessMetadataInitActionFactory:
    def test_builds_metadata_only_apply_configuration(self):
        strategy_reference = protocol_models.StrategyReference(
            id="strategy-1",
            version="1.0.0",
            emit_signals=True,
        )
        init_action = action_details_factory_module.generic_process_metadata_init_action_factory(
            automation_id="automation-1",
            strategy_reference=strategy_reference,
        )
        assert init_action.id == "action_init"
        assert init_action.action == flow_enums.ActionType.APPLY_CONFIGURATION.value
        metadata = init_action.config["automation"]["metadata"]
        assert metadata["automation_id"] == "automation-1"
        assert metadata["strategy_id"] == "strategy-1"
        assert metadata["strategy_version"] == "1.0.0"
        assert metadata["emit_signals"] is True
        assert "exchange_account_details" not in init_action.config


class TestGenericProcessActionFactoryWithoutAccount:
    def test_omits_exchange_auth_data_when_protocol_account_is_none(self):
        generic_process_configuration = protocol_models.GenericProcessConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
        )
        process_action = action_details_factory_module.generic_process_action_factory(
            _init_action(),
            generic_process_configuration,
            None,
            _WALLET_ADDRESS,
            automation_id="automation-1",
            strategy_id="strategy-1",
        )
        assert "exchange_auth_data" not in process_action.dsl_script
        assert "user_id=" in process_action.dsl_script
        assert "sync_profile_id=" in process_action.dsl_script


class TestGenericProcessActionFactoryWithEmbeddedProfileData:
    def test_uses_profile_data_keyword_when_strategy_id_is_omitted(self):
        embedded_profile_data = {"profile_details": {"id": "embedded-profile"}}
        generic_process_configuration = protocol_models.GenericProcessConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
            profile_data=embedded_profile_data,
        )
        process_action = action_details_factory_module.generic_process_action_factory(
            _init_action(),
            generic_process_configuration,
            None,
            _WALLET_ADDRESS,
            automation_id="automation-1",
        )
        assert "profile_data=" in process_action.dsl_script
        assert "sync_profile_id=" not in process_action.dsl_script
        assert process_action.dsl_script.startswith("run_octobot_process('automation-1', user_id=")
