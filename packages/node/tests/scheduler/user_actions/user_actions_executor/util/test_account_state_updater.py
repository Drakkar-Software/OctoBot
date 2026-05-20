import contextlib
import datetime
import mock
import pytest
import types

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums

import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater_module


_WALLET_ADDRESS = "0xwallet"
_ACCOUNT_TS = datetime.datetime(2026, 3, 12, 9, 0, tzinfo=datetime.UTC)


def _sample_account(*, is_simulated: bool = False) -> protocol_models.Account:
    return protocol_models.Account(
        id="acc-1",
        name="Test account",
        is_simulated=is_simulated,
        created_at=_ACCOUNT_TS,
        updated_at=_ACCOUNT_TS,
        assets=[],
        specifics=protocol_models.AccountSpecifics(
            actual_instance=protocol_models.ExchangeAccount(
                account_type=protocol_models.AccountType.EXCHANGE,
                trading_type=protocol_models.TradingType.SPOT,
                exchange="binanceus",
                remote_account_id="remote-1",
            ),
        ),
    )


def _authentication() -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        api_key="plain-key",
        api_secret="plain-secret",
    )


class TestAccountStateUpdaterCheckExchangeAccountState:
    @pytest.mark.asyncio
    async def test_encrypts_clear_credentials_before_exchange_manager_context(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            trading_type=protocol_models.TradingType.SPOT,
            exchange="binanceus",
            remote_account_id="remote-1",
        )
        account = _sample_account()
        authentication = _authentication()
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        dummy_exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())

        @contextlib.asynccontextmanager
        async def fake_exchange_manager_from_exchange_data(*args, **kwargs):
            yield dummy_exchange_manager

        with (
            mock.patch.object(
                account_state_updater_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
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
                    return_value=(
                        protocol_models.AccountState(
                            status=protocol_models.AccountStatus.VALID,
                            message=protocol_models.AccountStatusMessage.VALID,
                        ),
                        None,
                    )
                ),
            ),
        ):
            account_state, _ = await account_state_updater_module._check_exchange_account_state(
                exchange_account,
                account,
                _WALLET_ADDRESS,
            )
        assert account_state.status == protocol_models.AccountStatus.VALID
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        assert encrypt_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_encrypts_passphrase_when_present(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            trading_type=protocol_models.TradingType.SPOT,
            exchange="binanceus",
            remote_account_id="remote-1",
        )
        account = _sample_account()
        authentication = protocol_models.AccountAuthentication(
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
                account_state_updater_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
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
                    return_value=(
                        protocol_models.AccountState(
                            status=protocol_models.AccountStatus.VALID,
                            message=protocol_models.AccountStatusMessage.VALID,
                        ),
                        None,
                    )
                ),
            ),
        ):
            await account_state_updater_module._check_exchange_account_state(
                exchange_account,
                account,
                _WALLET_ADDRESS,
            )
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        encrypt_mock.assert_any_call("plain-pass")
        assert encrypt_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_passes_futures_trading_type_as_future_exchange_type(self):
        exchange_account = protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            trading_type=protocol_models.TradingType.FUTURES,
            exchange="binanceus",
            remote_account_id="remote-1",
        )
        account = _sample_account()
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        dummy_exchange_manager = types.SimpleNamespace(exchange=types.SimpleNamespace())
        captured_exchange_data_args = {}

        @contextlib.asynccontextmanager
        async def fake_exchange_manager_from_exchange_data(*args, **kwargs):
            captured_exchange_data_args["exchange_data"] = args[0]
            captured_exchange_data_args["profile_data"] = args[1]
            yield dummy_exchange_manager

        with (
            mock.patch.object(
                account_state_updater_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=_authentication(),
            ),
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
                    return_value=(
                        protocol_models.AccountState(
                            status=protocol_models.AccountStatus.VALID,
                            message=protocol_models.AccountStatusMessage.VALID,
                        ),
                        None,
                    )
                ),
            ),
        ):
            await account_state_updater_module._check_exchange_account_state(
                exchange_account,
                account,
                _WALLET_ADDRESS,
            )
        expected_exchange_type = trading_enums.ExchangeTypes.FUTURE.value
        exchange_data = captured_exchange_data_args["exchange_data"]
        assert exchange_data.auth_details.exchange_type == expected_exchange_type
        profile_data = captured_exchange_data_args["profile_data"]
        assert profile_data.exchanges[0].exchange_type == expected_exchange_type


class TestAccountStateUpdaterCheckExchangeManagerState:
    @pytest.mark.asyncio
    async def test_returns_valid_state_when_exchange_checks_succeed(self):
        account = _sample_account()
        exchange = types.SimpleNamespace(
            get_balance=mock.AsyncMock(
                return_value={
                    "USDT": {
                        commons_constants.PORTFOLIO_TOTAL: 1000.0,
                        commons_constants.PORTFOLIO_AVAILABLE: 1000.0,
                    }
                }
            ),
            ensure_api_key_permissions=mock.AsyncMock(return_value=None),
        )
        exchange_manager = types.SimpleNamespace(exchange=exchange)
        account_state, assets = await account_state_updater_module._check_exchange_manager_state(
            exchange_manager,
            account,
        )
        assert account_state.status == protocol_models.AccountStatus.VALID
        assert account_state.message == protocol_models.AccountStatusMessage.VALID
        assert assets is not None
        assert len(assets) == 1
        assert assets[0].symbol == "USDT"
        assert assets[0].total == 1000.0
        assert assets[0].available == 1000.0
        exchange.get_balance.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_maps_ip_whitelist_error(self):
        account = _sample_account()
        exchange = types.SimpleNamespace(
            get_balance=mock.AsyncMock(side_effect=trading_errors.InvalidAPIKeyIPWhitelistError("ip")),
        )
        exchange_manager = types.SimpleNamespace(exchange=exchange)
        account_state, assets = await account_state_updater_module._check_exchange_manager_state(
            exchange_manager,
            account,
        )
        assert account_state.status == protocol_models.AccountStatus.INVALID
        assert account_state.message == protocol_models.AccountStatusMessage.INVALID_API_IP_WHITELIST
        assert assets is None

    @pytest.mark.asyncio
    async def test_maps_withdrawal_permissions_error(self):
        account = _sample_account()
        exchange = types.SimpleNamespace(
            get_balance=mock.AsyncMock(
                side_effect=trading_errors.AuthenticationError("Missing withdrawal permission")
            ),
        )
        exchange_manager = types.SimpleNamespace(exchange=exchange)
        account_state, assets = await account_state_updater_module._check_exchange_manager_state(
            exchange_manager,
            account,
        )
        assert account_state.status == protocol_models.AccountStatus.INVALID
        assert account_state.message == protocol_models.AccountStatusMessage.REVOKE_API_WITHDRAWAL_RIGHTS
        assert assets is None


class TestAccountStateUpdaterAssetsFromBalance:
    def test_maps_non_zero_holdings_to_detailed_assets(self):
        balance = {
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: 1000.0,
                commons_constants.PORTFOLIO_AVAILABLE: 900.0,
            },
            "BTC": {
                commons_constants.PORTFOLIO_TOTAL: 0.5,
                commons_constants.PORTFOLIO_AVAILABLE: 0.5,
            },
            "ETH": {
                commons_constants.PORTFOLIO_TOTAL: 0.0,
                commons_constants.PORTFOLIO_AVAILABLE: 0.0,
            },
        }
        assets = account_state_updater_module._assets_from_balance(balance)
        assets_by_symbol = {asset.symbol: asset for asset in assets}
        assert set(assets_by_symbol) == {"USDT", "BTC"}
        assert assets_by_symbol["USDT"].total == 1000.0
        assert assets_by_symbol["USDT"].available == 900.0
        assert assets_by_symbol["BTC"].total == 0.5
