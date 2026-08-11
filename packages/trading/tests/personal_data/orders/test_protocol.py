#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.

import datetime

import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.orders.protocol as orders_protocol


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


class TestToProtocolOrder:
    def test_defaults_optional_fields_when_missing_from_ccxt_order(self):
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

        protocol_order = orders_protocol.to_protocol_order(ccxt_like_order)

        assert protocol_order.id == "order-1"
        assert protocol_order.exchange_id == "order-1"
        assert protocol_order.trigger_above is None
        assert protocol_order.reduce_only is False
        assert protocol_order.is_active is True
