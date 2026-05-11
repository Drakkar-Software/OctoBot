import contextlib
import mock
import pytest
import types

import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors

import octobot_node.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module


class TestAccountStateUpdaterCheckExchangeAccountState:
    @pytest.mark.asyncio
    async def test_encrypts_clear_credentials_before_exchange_manager_context(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            exchange="binanceus",
            remote_account_id="remote-1",
            api_key="plain-key",
            api_secret="plain-secret",
        )
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        dummy_exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())

        @contextlib.asynccontextmanager
        async def fake_exchange_manager_from_exchange_data(*args, **kwargs):
            yield dummy_exchange_manager

        with (
            mock.patch.object(
                account_state_updater_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
            mock.patch.object(
                account_state_updater_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager_from_exchange_data,
            ),
            mock.patch.object(
                account_state_updater_module.tentacles_manager_api,
                "get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch.object(
                account_state_updater_module.tentacles_manager_api,
                "set_tentacle_config_proxy",
                new=mock.Mock(),
            ),
            mock.patch.object(
                account_state_updater_module,
                "_check_exchange_manager_state",
                new=mock.AsyncMock(
                    return_value=protocol_models.AccountState(
                        status=protocol_models.AccountStatus.VALID,
                        message=protocol_models.AccountStatusMessage.VALID,
                    )
                ),
            ),
        ):
            account_state = await account_state_updater_module._check_exchange_account_state(
                exchange_account
            )
        assert account_state.status == protocol_models.AccountStatus.VALID
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        assert encrypt_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_encrypts_passphrase_when_present(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            exchange="binanceus",
            remote_account_id="remote-1",
            api_key="plain-key",
            api_secret="plain-secret",
            api_passphrase="plain-pass",
        )
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        dummy_exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())

        @contextlib.asynccontextmanager
        async def fake_exchange_manager_from_exchange_data(*args, **kwargs):
            yield dummy_exchange_manager

        with (
            mock.patch.object(
                account_state_updater_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
            mock.patch.object(
                account_state_updater_module.trading_exchanges,
                "exchange_manager_from_exchange_data",
                fake_exchange_manager_from_exchange_data,
            ),
            mock.patch.object(
                account_state_updater_module.tentacles_manager_api,
                "get_full_tentacles_setup_config",
                return_value=mock.Mock(),
            ),
            mock.patch.object(
                account_state_updater_module.tentacles_manager_api,
                "set_tentacle_config_proxy",
                new=mock.Mock(),
            ),
            mock.patch.object(
                account_state_updater_module,
                "_check_exchange_manager_state",
                new=mock.AsyncMock(
                    return_value=protocol_models.AccountState(
                        status=protocol_models.AccountStatus.VALID,
                        message=protocol_models.AccountStatusMessage.VALID,
                    )
                ),
            ),
        ):
            await account_state_updater_module._check_exchange_account_state(exchange_account)
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        encrypt_mock.assert_any_call("plain-pass")
        assert encrypt_mock.call_count == 3


class TestAccountStateUpdaterCheckExchangeManagerState:
    @pytest.mark.asyncio
    async def test_returns_valid_state_when_exchange_checks_succeed(self):
        exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())
        with (
            mock.patch.object(
                account_state_updater_module,
                "_request_exchange_to_ensure_authentication",
                new=mock.AsyncMock(return_value=None),
            ),
            mock.patch.object(
                account_state_updater_module,
                "_ensure_api_key_permissions",
                new=mock.AsyncMock(return_value=None),
            ),
        ):
            account_state = await account_state_updater_module._check_exchange_manager_state(exchange_manager)
        assert account_state.status == protocol_models.AccountStatus.VALID
        assert account_state.message == protocol_models.AccountStatusMessage.VALID

    @pytest.mark.asyncio
    async def test_maps_ip_whitelist_error(self):
        exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())
        with mock.patch.object(
            account_state_updater_module,
            "_request_exchange_to_ensure_authentication",
            new=mock.AsyncMock(side_effect=trading_errors.InvalidAPIKeyIPWhitelistError("ip")),
        ):
            account_state = await account_state_updater_module._check_exchange_manager_state(exchange_manager)
        assert account_state.status == protocol_models.AccountStatus.INVALID
        assert account_state.message == protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST

    @pytest.mark.asyncio
    async def test_maps_withdrawal_permissions_error(self):
        exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())
        with mock.patch.object(
            account_state_updater_module,
            "_request_exchange_to_ensure_authentication",
            new=mock.AsyncMock(
                side_effect=trading_errors.AuthenticationError("Missing withdrawal permission")
            ),
        ):
            account_state = await account_state_updater_module._check_exchange_manager_state(exchange_manager)
        assert account_state.status == protocol_models.AccountStatus.INVALID
        assert account_state.message == protocol_models.AccountStatusMessage.REVOKE_API_WITHDRAWAL_RIGHTS
