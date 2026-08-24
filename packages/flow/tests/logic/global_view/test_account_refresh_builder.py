#  Drakkar-Software OctoBot-Flow

import datetime

import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.enums as trading_enums

import octobot_flow.entities
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
            historical_trade_symbols=["BTC/USDT"],
        ),
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=exchange_data_module.ExchangeAuthDetails(
            exchange_type=trading_enums.ExchangeTypes.SPOT.value,
            sandboxed=False,
            exchange_account_id="account-1",
        ),
    )


class TestBuildGlobalViewAccountRefreshResult:
    def test_builds_refresh_result_without_history(self):
        context = _context()
        exchange_refresh_result = octobot_flow.entities.ExchangeAccountRefreshResult(
            assets=[],
            ticker_closes={"BTC/USDT": 65000.0},
            valuation_unit="USDC",
            open_orders=[],
            trades=[],
            positions=[],
            changed_order_ids={"gone-order"},
        )
        refresh_result = account_refresh_builder_module.build_global_view_account_refresh_result(
            "wallet-1",
            context,
            exchange_refresh_result,
        )
        assert refresh_result.updated_account.id == "account-1"
        assert refresh_result.changed_order_ids == {"gone-order"}
        assert not hasattr(refresh_result, "portfolio_history_state") or refresh_result.__dict__.get("portfolio_history_state") is None
