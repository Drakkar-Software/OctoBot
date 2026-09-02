#  Drakkar-Software OctoBot-Flow
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Flow consumer smoke for protocol wire fixtures: committed wire JSON must parse and
# feed real flow code paths (profile_data_factory, trade_fetch_cursors), not only
# generated octobot_protocol.models.

import json

import octobot_protocol.models as protocol_models
import scripts.lib.openapi_compat_lib as openapi_compat_lib

import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module
import octobot_flow.logic.portfolio_history.trade_fetch_cursors as trade_fetch_cursors_module


class TestProtocolWireCompat:
    def test_accounts_state_fixture_supports_profile_data_factory_inputs(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        with open(version_dir / "accounts_state.json", encoding="utf-8") as handle:
            accounts_state_payload = json.load(handle)
        accounts_state = protocol_models.AccountsState.from_json(json.dumps(accounts_state_payload))
        assert accounts_state is not None
        if accounts_state.accounts and accounts_state.exchange_configs:
            account = accounts_state.accounts[0]
            exchange_config = accounts_state.exchange_configs[0]
            profile_data = profile_data_factory_module.profile_data_for_account(
                account,
                protocol_models.ExchangeAccount(
                    id="exchange-account-1",
                    account_id=account.id,
                    exchange=exchange_config.exchange,
                ),
                exchange_config,
                protocol_models.TradingType.SPOT,
                is_simulated=False,
            )
            assert profile_data.exchanges[0].internal_name == exchange_config.exchange

    def test_account_trading_state_fixture_supports_trade_fetch_cursors(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        with open(version_dir / "account_trading_state.json", encoding="utf-8") as handle:
            trading_state_payload = json.load(handle)
        trading_state = protocol_models.AccountTradingState.from_json(json.dumps(trading_state_payload))
        assert trading_state is not None
        persisted_symbols = trade_fetch_cursors_module.symbols_with_persisted_trades(
            trading_state.account_trading,
        )
        assert persisted_symbols == set()

    def test_user_action_fixtures_parse(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        user_actions_dir = version_dir / "user_actions"
        for fixture_path in sorted(user_actions_dir.glob("*.json")):
            with open(fixture_path, encoding="utf-8") as handle:
                fixture_payload = json.load(handle)
            parsed_action = protocol_models.UserAction.from_json(json.dumps(fixture_payload))
            assert parsed_action is not None
