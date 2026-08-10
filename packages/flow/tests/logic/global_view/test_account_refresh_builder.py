#  Drakkar-Software OctoBot-Flow

import datetime

import mock

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.enums as trading_enums

import octobot_flow.entities
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module
import octobot_flow.logic.global_view.account_refresh_builder as account_refresh_builder_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _context() -> octobot_flow.entities.GlobalViewAccountContext:
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="account-1",
        exchange_config_ids=["exchange-config-1"],
    )
    account = protocol_models.Account(
        id="account-1",
        name="Test account",
        is_simulated=False,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
    )
    return octobot_flow.entities.GlobalViewAccountContext(
        account=account,
        exchange_account=exchange_account,
        exchange_config=protocol_models.ExchangeConfig(
            id="exchange-config-1",
            name="binance-main",
            exchange="binanceus",
            sandboxed=False,
        ),
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=exchange_data_module.ExchangeAuthDetails(
            exchange_type=trading_enums.ExchangeTypes.SPOT.value,
            sandboxed=False,
            exchange_account_id="account-1",
        ),
    )


class TestBuildGlobalViewAccountRefreshResult:
    def test_builds_refresh_result_with_history_state(self):
        context = _context()
        exchange_refresh_result = octobot_flow.entities.ExchangeAccountRefreshResult(
            assets=[],
            portfolio_snapshot=protocol_models.PortfolioHistoricalValue(
                timestamp=_TEST_TIMESTAMP,
                total=1000.0,
            ),
            valuation_unit="USDC",
            open_orders=[],
            trades=[],
            positions=[],
            changed_order_ids={"gone-order"},
        )
        expected_history_state = protocol_models.PortfolioHistoricalValuesState(
            version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
            history=protocol_models.PortfolioHistoricalValues(
                unit="USDC",
                values=[exchange_refresh_result.portfolio_snapshot],
            ),
        )
        with mock.patch.object(
            account_state_persistence_module,
            "build_portfolio_history_state",
            return_value=expected_history_state,
        ) as build_history_mock:
            refresh_result = account_refresh_builder_module.build_global_view_account_refresh_result(
                "wallet-1",
                context,
                exchange_refresh_result,
            )
        build_history_mock.assert_called_once_with(
            "wallet-1",
            "account-1",
            exchange_refresh_result.portfolio_snapshot,
            "USDC",
            _TEST_TIMESTAMP,
        )
        assert refresh_result.updated_account.id == "account-1"
        assert refresh_result.changed_order_ids == {"gone-order"}
        assert refresh_result.portfolio_history_state == expected_history_state
