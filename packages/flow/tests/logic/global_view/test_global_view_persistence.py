#  Drakkar-Software OctoBot-Flow

import datetime

import mock

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow.entities
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module
import octobot_flow.logic.global_view.global_view_persistence as global_view_persistence_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _refresh_result(*, open_orders: list[dict] | None = None) -> octobot_flow.entities.GlobalViewAccountRefreshResult:
    account = protocol_models.Account(
        id="account-1",
        name="Test",
        is_simulated=False,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
    )
    return octobot_flow.entities.GlobalViewAccountRefreshResult(
        updated_account=account,
        changed_order_ids=set(),
        open_orders=open_orders or [],
        portfolio_history_state=protocol_models.PortfolioHistoricalValuesState(
            version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
            history=protocol_models.PortfolioHistoricalValues(unit="USDC", values=[]),
        ),
    )


class TestPersistGlobalViewRefreshResult:
    def test_does_not_persist_trading_when_persist_open_orders_false(self):
        account_provider = mock.Mock()
        history_provider = mock.Mock()
        with (
            mock.patch.object(
                collection_providers.AccountProvider,
                "instance",
                return_value=account_provider,
            ),
            mock.patch.object(
                collection_providers.AccountHistoryProvider,
                "instance",
                return_value=history_provider,
            ),
            mock.patch.object(
                account_state_persistence_module,
                "persist_account_trading_orders",
            ) as persist_orders_mock,
        ):
            global_view_persistence_module.persist_global_view_refresh_result(
                "wallet-1",
                "account-1",
                _refresh_result(),
                persist_open_orders=False,
            )
        account_provider.update_item.assert_called_once()
        history_provider.save_state.assert_called_once()
        persist_orders_mock.assert_not_called()

    def test_persists_orders_only_when_persist_open_orders_true(self):
        account_provider = mock.Mock()
        history_provider = mock.Mock()
        open_orders = [
            {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order-1",
            }
        ]
        with (
            mock.patch.object(
                collection_providers.AccountProvider,
                "instance",
                return_value=account_provider,
            ),
            mock.patch.object(
                collection_providers.AccountHistoryProvider,
                "instance",
                return_value=history_provider,
            ),
            mock.patch.object(
                account_state_persistence_module,
                "persist_account_trading_orders",
            ) as persist_orders_mock,
        ):
            global_view_persistence_module.persist_global_view_refresh_result(
                "wallet-1",
                "account-1",
                _refresh_result(open_orders=open_orders),
                persist_open_orders=True,
            )
        persist_orders_mock.assert_called_once_with(
            "wallet-1",
            "account-1",
            open_orders,
        )


class TestPersistAccountTradingOrders:
    def test_replaces_orders_without_clearing_trades_or_positions(self):
        trading_provider = mock.Mock()
        sentinel_trade = protocol_models.Trade.model_construct(
            id="trade-1",
            trade_id="trade-1",
        )
        sentinel_position = protocol_models.Position.model_construct(
            id="pos-1",
            symbol="BTC/USDT",
        )
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
                orders=[
                    protocol_models.Order(
                        id="old-order",
                        symbol="BTC/USDT",
                        price=10000.0,
                        quantity=0.01,
                        filled=0.0,
                        exchange_id="old-order",
                        side=protocol_models.Side.BUY,
                        type=protocol_models.OrderType.LIMIT,
                        status=protocol_models.OrderStatus.OPEN,
                        created_at=_TEST_TIMESTAMP,
                    )
                ],
                trades=[sentinel_trade],
                positions=[sentinel_position],
            ),
        )
        order_payload = {
            trading_constants.STORAGE_ORIGIN_VALUE: {
                trading_enums.ExchangeConstantsOrderColumns.ID.value: "new-order",
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "new-order",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 2000.0,
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 0.5,
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: protocol_models.Side.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: protocol_models.OrderType.LIMIT.value,
                trading_enums.ExchangeConstantsOrderColumns.STATUS.value: protocol_models.OrderStatus.OPEN.value,
                trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: _TEST_TIMESTAMP.timestamp(),
            }
        }
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            account_state_persistence_module.persist_account_trading_orders(
                "wallet-1",
                "account-1",
                [order_payload],
            )
        saved_state = trading_provider.save_state.call_args.args[2]
        saved_trading = saved_state.account_trading
        assert len(saved_trading.orders) == 1
        assert saved_trading.orders[0].exchange_id == "new-order"
        assert saved_trading.positions == [sentinel_position]
        assert saved_trading.trades == [sentinel_trade]

    def test_raises_when_trading_state_missing(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            try:
                account_state_persistence_module.persist_account_trading_orders(
                    "wallet-1",
                    "account-1",
                    [],
                )
                raise AssertionError("Expected CollectionNoDataError")
            except collection_errors.CollectionNoDataError:
                pass
        trading_provider.save_state.assert_not_called()
