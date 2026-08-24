import datetime

import octobot_protocol.models as protocol_models
import octobot_trading.enums as enums
import octobot_trading.personal_data.trades.protocol as trades_protocol


def _exchange_trade_dict(
    *,
    fee: dict | None = None,
) -> dict:
    order_columns = enums.ExchangeConstantsOrderColumns
    trade_dict = {
        order_columns.ID.value: "local-1",
        order_columns.EXCHANGE_TRADE_ID.value: "exchange-1",
        order_columns.SYMBOL.value: "BTC/USDT",
        order_columns.TYPE.value: enums.TradeOrderType.LIMIT,
        order_columns.SIDE.value: enums.TradeOrderSide.BUY,
        order_columns.AMOUNT.value: 1.0,
        order_columns.PRICE.value: 40000.0,
        order_columns.STATUS.value: enums.OrderStatus.FILLED,
        order_columns.TIMESTAMP.value: 1700000000.0,
    }
    if fee is not None:
        trade_dict[order_columns.FEE.value] = fee
    return trade_dict


class TestToProtocolTradeFee:
    def test_fee_absent(self):
        trade = trades_protocol.to_protocol_trade(_exchange_trade_dict())
        assert trade.fee is None

    def test_fee_present(self):
        fee_dict = {
            enums.FeePropertyColumns.CURRENCY.value: "BTC",
            enums.FeePropertyColumns.COST.value: 0.001,
        }
        trade = trades_protocol.to_protocol_trade(_exchange_trade_dict(fee=fee_dict))
        assert trade.fee is not None
        assert trade.fee.currency == "BTC"
        assert trade.fee.amount == 0.001

    def test_fee_round_trip(self):
        fee_dict = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.COST.value: 10,
        }
        trade = trades_protocol.to_protocol_trade(_exchange_trade_dict(fee=fee_dict))
        trade_dict = trades_protocol.exchange_columns_dict_from_protocol_trade(trade)
        assert trade_dict[enums.ExchangeConstantsOrderColumns.FEE.value] == fee_dict

    def test_exchange_columns_dict_without_fee(self):
        trade = protocol_models.Trade(
            id="local-1",
            trade_id="exchange-1",
            type=protocol_models.OrderType.LIMIT,
            symbol="BTC/USDT",
            side=protocol_models.Side.BUY,
            quantity=1.0,
            price=40000.0,
            status=protocol_models.OrderStatus.FILLED,
            executed_at=datetime.datetime.fromtimestamp(1700000000.0, tz=datetime.timezone.utc),
        )
        trade_dict = trades_protocol.exchange_columns_dict_from_protocol_trade(trade)
        assert enums.ExchangeConstantsOrderColumns.FEE.value not in trade_dict
