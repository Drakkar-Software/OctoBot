#  Drakkar-Software OctoBot-Flow

import datetime

import mock

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _portfolio_snapshot(total: float) -> protocol_models.PortfolioHistoricalValue:
    return protocol_models.PortfolioHistoricalValue(
        timestamp=_TEST_TIMESTAMP,
        total=total,
    )


def _protocol_order(exchange_id: str) -> protocol_models.Order:
    return protocol_models.Order(
        id=exchange_id,
        symbol="BTC/USDT",
        price=10000.0,
        quantity=0.01,
        filled=0.0,
        exchange_id=exchange_id,
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        status=protocol_models.OrderStatus.OPEN,
        created_at=_TEST_TIMESTAMP,
    )


class TestLoadPreviousOpenOrderExchangeIds:
    def test_returns_exchange_ids_from_persisted_orders(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
                orders=[
                    _protocol_order("order-1"),
                    _protocol_order("order-2"),
                ],
            ),
        )
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            exchange_ids = account_state_persistence_module.load_previous_open_order_exchange_ids(
                "wallet-1",
                "account-1",
            )
        assert exchange_ids == {"order-1", "order-2"}

    def test_returns_empty_set_when_no_trading_state(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            exchange_ids = account_state_persistence_module.load_previous_open_order_exchange_ids(
                "wallet-1",
                "account-1",
            )
        assert exchange_ids == set()

    def test_propagates_unexpected_load_state_errors(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = RuntimeError("disk failure")
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            try:
                account_state_persistence_module.load_previous_open_order_exchange_ids(
                    "wallet-1",
                    "account-1",
                )
                raise AssertionError("Expected RuntimeError")
            except RuntimeError as error:
                assert str(error) == "disk failure"


class TestLoadPreviousOpenOrders:
    def test_returns_storage_dicts_from_persisted_orders(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
                orders=[_protocol_order("order-1")],
            ),
        )
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            open_orders = account_state_persistence_module.load_previous_open_orders(
                "wallet-1",
                "account-1",
            )
        assert len(open_orders) == 1
        inner_order = open_orders[0][trading_constants.STORAGE_ORIGIN_VALUE]
        assert inner_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] == "order-1"
        assert inner_order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == "BTC/USDT"

    def test_returns_empty_list_when_no_trading_state(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            open_orders = account_state_persistence_module.load_previous_open_orders(
                "wallet-1",
                "account-1",
            )
        assert open_orders == []

    def test_propagates_unexpected_load_state_errors(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = RuntimeError("disk failure")
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            try:
                account_state_persistence_module.load_previous_open_orders(
                    "wallet-1",
                    "account-1",
                )
                raise AssertionError("Expected RuntimeError")
            except RuntimeError as error:
                assert str(error) == "disk failure"


class TestBuildPortfolioHistoryState:
    def test_merges_snapshot_into_history_state(self):
        history_provider = mock.Mock()
        history_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
        with mock.patch.object(
            collection_providers.AccountHistoryProvider,
            "instance",
            return_value=history_provider,
        ):
            history_state = account_state_persistence_module.build_portfolio_history_state(
                "wallet-1",
                "account-1",
                _portfolio_snapshot(1500.0),
                "USDC",
                _TEST_TIMESTAMP,
            )
        assert history_state.history is not None
        assert history_state.history.unit == "USDC"
        assert history_state.history.values[-1].total == 1500.0


class TestPersistAccountTrading:
    def test_saves_updated_trading_state(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
            ),
        )
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            account_state_persistence_module.persist_account_trading(
                "wallet-1",
                "account-1",
                orders=[],
                trades=[],
                positions=[],
            )
        trading_provider.save_state.assert_called_once()

    def test_raises_when_trading_state_missing(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            try:
                account_state_persistence_module.persist_account_trading(
                    "wallet-1",
                    "account-1",
                    orders=[],
                    trades=[],
                    positions=[],
                )
                raise AssertionError("Expected CollectionNoDataError")
            except collection_errors.CollectionNoDataError:
                pass
        trading_provider.save_state.assert_not_called()

    def test_fills_id_from_exchange_id_when_missing(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
            ),
        )
        order_without_id = {
            trading_constants.STORAGE_ORIGIN_VALUE: {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "exch-order-1",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 10000.0,
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 0.01,
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: protocol_models.Side.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: protocol_models.OrderType.LIMIT.value,
                trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: False,
                trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: False,
                trading_enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value: True,
                trading_enums.ExchangeConstantsOrderColumns.STATUS.value: protocol_models.OrderStatus.OPEN.value,
                trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: _TEST_TIMESTAMP.timestamp(),
            }
        }
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            account_state_persistence_module.persist_account_trading(
                "wallet-1",
                "account-1",
                orders=[order_without_id],
                trades=[],
                positions=[],
            )
        saved_state = trading_provider.save_state.call_args.args[2]
        saved_orders = saved_state.account_trading.orders
        assert len(saved_orders) == 1
        assert saved_orders[0].id == "exch-order-1"
        assert saved_orders[0].exchange_id == "exch-order-1"

    def test_persists_ccxt_order_missing_optional_fields(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
            ),
        )
        ccxt_like_order = {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: "order-1",
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order-1",
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 10000.0,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 0.01,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0.0,
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: protocol_models.Side.BUY.value,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: protocol_models.OrderType.LIMIT.value,
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value: protocol_models.OrderStatus.OPEN.value,
            trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: _TEST_TIMESTAMP.timestamp(),
        }
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            account_state_persistence_module.persist_account_trading(
                "wallet-1",
                "account-1",
                orders=[ccxt_like_order],
                trades=[],
                positions=[],
            )
        saved_state = trading_provider.save_state.call_args.args[2]
        saved_order = saved_state.account_trading.orders[0]
        assert saved_order.id == "order-1"
        assert saved_order.trigger_above is None
        assert saved_order.reduce_only is False
        assert saved_order.is_active is True

    def test_raises_when_order_missing_id_and_exchange_id(self):
        trading_provider = mock.Mock()
        trading_provider.load_state.return_value = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=_TEST_TIMESTAMP,
            ),
        )
        order_without_ids = {
            trading_constants.STORAGE_ORIGIN_VALUE: {
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
            }
        }
        with mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ):
            try:
                account_state_persistence_module.persist_account_trading(
                    "wallet-1",
                    "account-1",
                    orders=[order_without_ids],
                    trades=[],
                    positions=[],
                )
                raise AssertionError("Expected ValueError")
            except ValueError as error:
                assert "missing both id and exchange_id" in str(error)
        trading_provider.save_state.assert_not_called()


class TestPersistAccountTradingFromIterationState:
    def test_persists_trading_snapshot_from_automation_state(self):
        import octobot_flow.entities

        exchange_details = octobot_flow.entities.ExchangeAccountDetails()
        exchange_details.exchange_details.exchange_account_id = "acc-sync-1"
        elements = octobot_flow.entities.ExchangeAccountElements()
        elements.orders.open_orders = [{"exchange_id": "order-1"}]
        automation_state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation-1"),
            ),
            exchange_account_details=exchange_details,
        )
        automation_state.automation.exchange_account_elements = elements
        with mock.patch.object(
            account_state_persistence_module,
            "persist_account_trading",
        ) as persist_account_trading_mock:
            account_state_persistence_module.persist_account_trading_from_iteration_state(
                "wallet-1",
                automation_state.to_dict(include_default_values=False),
            )
        persist_account_trading_mock.assert_called_once_with(
            "wallet-1",
            "acc-sync-1",
            [{"exchange_id": "order-1"}],
            [],
            [],
        )

    def test_skips_when_wallet_not_registered(self):
        import octobot.community.wallet_backend.errors as wallet_backend_errors_module
        import octobot_flow.entities

        exchange_details = octobot_flow.entities.ExchangeAccountDetails()
        exchange_details.exchange_details.exchange_account_id = "acc-sync-1"
        elements = octobot_flow.entities.ExchangeAccountElements()
        elements.orders.open_orders = [{"exchange_id": "order-1"}]
        automation_state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation-1"),
            ),
            exchange_account_details=exchange_details,
        )
        automation_state.automation.exchange_account_elements = elements
        with mock.patch.object(
            account_state_persistence_module,
            "persist_account_trading",
            side_effect=wallet_backend_errors_module.WalletNotFoundError("Wallet not found"),
        ):
            account_state_persistence_module.persist_account_trading_from_iteration_state(
                "wallet-1",
                automation_state.to_dict(include_default_values=False),
            )
