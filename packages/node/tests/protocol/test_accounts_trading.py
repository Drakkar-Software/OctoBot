#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import datetime

import mock
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot_node.protocol.accounts_trading as accounts_trading_module

_ORDER_COLUMNS = trading_enums.ExchangeConstantsOrderColumns
_POSITION_COLUMNS = trading_enums.ExchangeConstantsPositionColumns

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
_TEST_ACCOUNT_ID = "acc-trading-1"
_SAMPLE_ENCRYPTED_BLOB = {
    sync_constants.BLOB_IV_KEY: "sample-iv",
    sync_constants.BLOB_DATA_KEY: "sample-data",
}


class TestGetAccountTradingStateEncrypted:
    """Checks :func:`octobot_node.protocol.accounts_trading.get_account_trading_state_encrypted`."""

    def test_passes_address_and_account_id_to_provider_and_returns_blob(self):
        provider_stub = mock.Mock()
        provider_stub.load_state_encrypted = mock.Mock(return_value=_SAMPLE_ENCRYPTED_BLOB)
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            encrypted_state = accounts_trading_module.get_account_trading_state_encrypted(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
            )

        provider_stub.load_state_encrypted.assert_called_once_with(
            _TEST_WALLET_ADDRESS,
            _TEST_ACCOUNT_ID,
        )
        assert encrypted_state == _SAMPLE_ENCRYPTED_BLOB

    def test_returns_none_when_provider_raises_collection_no_data_error(self):
        provider_stub = mock.Mock()
        provider_stub.load_state_encrypted = mock.Mock(
            side_effect=collection_errors.CollectionNoDataError("missing trading state"),
        )
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            encrypted_state = accounts_trading_module.get_account_trading_state_encrypted(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
            )

        assert encrypted_state is None


def _sample_order(order_id: str) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol="BTC/USDT",
        price=1.0,
        quantity=1.0,
        filled=0.0,
        exchange_id="ex-1",
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        status=protocol_models.OrderStatus.OPEN,
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )


class TestGetAccountTradingSummaries:
    """Checks :func:`octobot_node.protocol.accounts_trading.get_account_trading_summaries`."""

    def test_returns_summaries_for_loaded_accounts(self):
        fixture_time = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
        trading_state = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=fixture_time,
                orders=[_sample_order("ord-1")],
            ),
        )
        with mock.patch.object(
            accounts_trading_module,
            "get_account_trading_state",
            return_value=trading_state,
        ) as load_state_mock:
            summaries = accounts_trading_module.get_account_trading_summaries(
                _TEST_WALLET_ADDRESS,
                [_TEST_ACCOUNT_ID],
            )
        load_state_mock.assert_called_once_with(_TEST_WALLET_ADDRESS, _TEST_ACCOUNT_ID)
        assert len(summaries) == 1
        assert summaries[0].account_id == _TEST_ACCOUNT_ID
        assert summaries[0].account_trading is not None
        assert summaries[0].account_trading.orders is not None
        assert summaries[0].account_trading.orders[0].id == "ord-1"

    def test_omits_accounts_when_trading_state_is_missing(self):
        def load_state_side_effect(address: str, account_id: str):
            if account_id == "acc-missing":
                raise collection_errors.CollectionNoDataError("missing trading state")
            return protocol_models.AccountTradingState(
                version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
                account_trading=protocol_models.AccountTrading(
                    updated_at=datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC),
                ),
            )

        with mock.patch.object(
            accounts_trading_module,
            "get_account_trading_state",
            side_effect=load_state_side_effect,
        ):
            summaries = accounts_trading_module.get_account_trading_summaries(
                _TEST_WALLET_ADDRESS,
                ["acc-present", "acc-missing"],
            )
        assert len(summaries) == 1
        assert summaries[0].account_id == "acc-present"


def _exchange_order_dict(order_id: str) -> dict:
    return {
        _ORDER_COLUMNS.ID.value: order_id,
        _ORDER_COLUMNS.SYMBOL.value: "BTC/USDT",
        _ORDER_COLUMNS.PRICE.value: 1.0,
        _ORDER_COLUMNS.AMOUNT.value: 1.0,
        _ORDER_COLUMNS.FILLED.value: 0.0,
        _ORDER_COLUMNS.EXCHANGE_ID.value: "ex-1",
        _ORDER_COLUMNS.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
        _ORDER_COLUMNS.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
        _ORDER_COLUMNS.TRIGGER_ABOVE.value: False,
        _ORDER_COLUMNS.REDUCE_ONLY.value: False,
        _ORDER_COLUMNS.IS_ACTIVE.value: True,
        _ORDER_COLUMNS.STATUS.value: trading_enums.OrderStatus.OPEN.value,
        _ORDER_COLUMNS.TIMESTAMP.value: 1735689600.0,
    }


def _exchange_trade_dict(trade_id: str) -> dict:
    return {
        _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: trade_id,
        _ORDER_COLUMNS.ID.value: trade_id,
        _ORDER_COLUMNS.SYMBOL.value: "BTC/USDT",
        _ORDER_COLUMNS.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
        _ORDER_COLUMNS.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
        _ORDER_COLUMNS.AMOUNT.value: 1.0,
        _ORDER_COLUMNS.PRICE.value: 1.0,
        _ORDER_COLUMNS.STATUS.value: trading_enums.OrderStatus.FILLED.value,
        _ORDER_COLUMNS.TIMESTAMP.value: 1735689600.0,
    }


def _exchange_position_dict(position_id: str) -> dict:
    return {
        _POSITION_COLUMNS.ID.value: position_id,
        _POSITION_COLUMNS.SYMBOL.value: "BTC/USDT",
        _POSITION_COLUMNS.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
        _POSITION_COLUMNS.QUANTITY.value: 1.0,
        _POSITION_COLUMNS.ENTRY_PRICE.value: 1.0,
        _POSITION_COLUMNS.MARK_PRICE.value: 1.0,
        _POSITION_COLUMNS.LIQUIDATION_PRICE.value: 0.5,
        _POSITION_COLUMNS.STATUS.value: trading_enums.PositionStatus.OPEN.value,
    }


class TestUpdateAccountTrading:
    """Checks :func:`octobot_node.protocol.accounts_trading.update_account_trading`."""

    def test_creates_state_when_trading_file_is_missing(self):
        provider_stub = mock.Mock()
        provider_stub.load_state = mock.Mock(
            side_effect=collection_errors.CollectionNoDataError("missing trading state"),
        )
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_trading_module.update_account_trading(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
                [_exchange_order_dict("ord-new")],
                [_exchange_trade_dict("trade-new")],
                [_exchange_position_dict("pos-new")],
            )
        provider_stub.save_state.assert_called_once()
        saved_state = provider_stub.save_state.call_args[0][2]
        assert saved_state.account_trading.orders is not None
        assert saved_state.account_trading.orders[0].id == "ord-new"
        assert saved_state.account_trading.trades is not None
        assert saved_state.account_trading.trades[0].trade_id == "trade-new"

    def test_replaces_orders_and_upserts_trades(self):
        fixture_time = datetime.datetime(2026, 1, 10, tzinfo=datetime.UTC)
        existing_state = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=fixture_time,
                orders=[_sample_order("ord-old")],
                trades=[
                    accounts_trading_module.trades_protocol.to_protocol_trade(
                        _exchange_trade_dict("trade-existing"),
                    ),
                ],
            ),
        )
        provider_stub = mock.Mock()
        provider_stub.load_state = mock.Mock(return_value=existing_state)
        with mock.patch.object(
            accounts_trading_module.trading_provider.AccountTradingProvider,
            "instance",
            return_value=provider_stub,
        ):
            accounts_trading_module.update_account_trading(
                _TEST_WALLET_ADDRESS,
                _TEST_ACCOUNT_ID,
                [_exchange_order_dict("ord-new")],
                [_exchange_trade_dict("trade-existing"), _exchange_trade_dict("trade-new")],
                [_exchange_position_dict("pos-new")],
            )
        saved_state = provider_stub.save_state.call_args[0][2]
        assert saved_state.account_trading.orders is not None
        assert saved_state.account_trading.orders[0].id == "ord-new"
        assert saved_state.account_trading.positions is not None
        assert saved_state.account_trading.positions[0].id == "pos-new"
        assert saved_state.account_trading.trades is not None
        trade_ids = {trade.trade_id for trade in saved_state.account_trading.trades}
        assert trade_ids == {"trade-existing", "trade-new"}
