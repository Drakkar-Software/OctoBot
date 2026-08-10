#  Drakkar-Software OctoBot-Flow

import datetime

import mock

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

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
        trading_provider.load_state.side_effect = collection_errors.CollectionNoDataError()
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
