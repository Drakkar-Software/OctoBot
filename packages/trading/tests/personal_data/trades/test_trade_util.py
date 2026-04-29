#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import time
import mock

from tests import event_loop
import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums

from octobot_trading.api.exchange import cancel_ccxt_throttle_task

from tests.exchanges import simulated_exchange_manager, simulated_trader
from tests.personal_data.trades import create_executed_trade


SYMBOL = "BTC/USDT"


def test_aggregate_trades_by_exchange_order_id(simulated_trader):
    _, _, trader = simulated_trader
    t1 = create_executed_trade(
        trader, enums.TradeOrderSide.BUY, 1, decimal.Decimal(10), decimal.Decimal(1500), SYMBOL, _get_fees("BTC", 0.1)
    )
    t2 = create_executed_trade(
        trader, enums.TradeOrderSide.BUY, 3, decimal.Decimal(13), decimal.Decimal(1605), SYMBOL, _get_fees("BTC", 0.5)
    )
    t3 = create_executed_trade(
        trader, enums.TradeOrderSide.BUY, 7, decimal.Decimal(7), decimal.Decimal(1400), SYMBOL, _get_fees("BTC", 1.4)
    )
    aggregated = personal_data.aggregate_trades_by_exchange_order_id([t1, t2, t3])
    # aggregated all trades together as all of their exchange_order_id is None
    assert list(aggregated) == [None]
    assert aggregated[None].trader is trader
    assert aggregated[None].symbol == t1.symbol
    assert aggregated[None].side is t1.side
    assert aggregated[None].executed_price == decimal.Decimal("1522.166666666666666666666667")
    assert aggregated[None].executed_quantity == sum(t.executed_quantity for t in (t1, t2, t3))
    assert aggregated[None].total_cost == sum(t.total_cost for t in (t1, t2, t3))
    assert aggregated[None].fee[enums.FeePropertyColumns.COST.value] == \
       sum(t.fee[enums.FeePropertyColumns.COST.value] for t in (t1, t2, t3))
    assert aggregated[None].executed_time == 7

    # set exchange_order_id
    t1.exchange_order_id = "1"
    t2.exchange_order_id = "1"
    t3.exchange_order_id = "2"
    aggregated = personal_data.aggregate_trades_by_exchange_order_id([t1, t2, t3])
    # aggregated all trades together as all of their exchange_order_id is None
    assert list(aggregated) == ["1", "2"]
    assert aggregated["1"].trader is trader
    assert aggregated["1"].symbol == t1.symbol
    assert aggregated["1"].side is t1.side
    assert aggregated["1"].executed_price == decimal.Decimal("1559.347826086956521739130435")
    assert aggregated["1"].executed_quantity == sum(t.executed_quantity for t in (t1, t2))
    assert aggregated["1"].total_cost == sum(t.total_cost for t in (t1, t2))
    assert aggregated["1"].fee[enums.FeePropertyColumns.COST.value] == \
       sum(t.fee[enums.FeePropertyColumns.COST.value] for t in (t1, t2))
    assert aggregated["1"].executed_time == 3

    assert aggregated["2"].executed_price == decimal.Decimal(1400)
    assert aggregated["2"].executed_quantity == decimal.Decimal(7)
    assert aggregated["2"].total_cost == t3.total_cost
    assert aggregated["2"].fee == _get_fees("BTC", 1.4)
    assert aggregated["2"].executed_time == 7


def _get_fees(currency, value):
    return {
        enums.FeePropertyColumns.CURRENCY.value: currency,
        enums.FeePropertyColumns.COST.value: decimal.Decimal(str(value))
    }


class TestGetTradingOrderFee:
    """Test class for get_trading_order_fee method."""

    def create_trade(
        self, trader, exchange_order_id: str,
        side, executed_quantity, executed_price, symbol, fee
    ) -> personal_data.Trade:
        return personal_data.create_trade_from_dict(
            trader,
            {
                enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_order_id,
                enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
                enums.ExchangeConstantsOrderColumns.SIDE.value: side,
                enums.ExchangeConstantsOrderColumns.AMOUNT.value: executed_quantity,
                enums.ExchangeConstantsOrderColumns.PRICE.value: executed_price,
                enums.ExchangeConstantsOrderColumns.TYPE.value: enums.TradeOrderType.LIMIT.value,
                enums.ExchangeConstantsOrderColumns.COST.value: executed_quantity * executed_price,
                enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: time.time(),
                enums.ExchangeConstantsOrderColumns.FEE.value: fee,
            }
        )

    def test_gets_fee_from_trade_with_base_currency(self, simulated_trader):
        _, _, trader = simulated_trader
        # Create trade with fee already set (base currency)
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL,
            {
                enums.FeePropertyColumns.CURRENCY.value: "BTC",
                enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),  # 0.1%
            }
        )
        
        # Get trading order fee
        # Should return calculated fee from trade.fee directly and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("BTC", 0.0001),
            False
        )

    def test_gets_fee_from_trade_with_quote_currency(self, simulated_trader):
        _, _, trader = simulated_trader
        # Create trade with fee already set (quote currency)
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL,
            {
                enums.FeePropertyColumns.CURRENCY.value: "USDT",
                enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),  # 0.1%
            }
        )
        
        # Get trading order fee
        # Should return calculated fee from trade.fee directly and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("USDT", 0.1),
            False
        )

    def test_gets_fee_from_order_with_base_currency(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        # Create mock order with fee in base currency
        mock_order = mock.Mock()
        mock_order.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "BTC",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),  # 0.1%
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Get trading order fee
        # Should return calculated fee and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("BTC", 0.0001),
            False
        )

    def test_gets_fee_from_order_with_quote_currency(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        # Create mock order with fee in quote currency
        mock_order = mock.Mock()
        mock_order.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),  # 0.1%
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Get trading order fee
        # Should return calculated fee and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("USDT", 0.1),
            False
        )
            
    def test_gets_fee_from_trades_when_order_has_no_fee(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Create mock order without fee
        mock_order = mock.Mock()
        mock_order.fee = None
        
        # Create mock trade with fee
        mock_trade = mock.Mock()
        mock_trade.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),
        }
        
        # Mock orders_manager.get_order to return order without fee
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Mock trades_manager.get_trades to return trade with fee
        trader.exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
            return_value=[mock_trade]
        )
        
        # Get trading order fee
        # Should return calculated fee from trade and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            # Fee cost = rate * amount * price = 0.001 * 0.1 * 1000 = 0.1 USDT
            _get_fees("USDT", 0.1),
            False
        )

    def test_gets_fee_from_trades_when_order_fee_missing_fields(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Create mock order with incomplete fee (missing RATE)
        mock_order = mock.Mock()
        mock_order.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            # Missing RATE
        }
        
        # Create mock trade with fee
        mock_trade = mock.Mock()
        mock_trade.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "BTC",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Mock trades_manager.get_trades
        trader.exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
            return_value=[mock_trade]
        )
        
        # Get trading order fee
        # Should return calculated fee from trade and not be estimated
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            # Fee cost = rate * amount = 0.001 * 0.1 = 0.0001 BTC
            _get_fees("BTC", 0.0001),
            False
        )

    def test_skips_trades_without_fee(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Create mock order without fee
        mock_order = mock.Mock()
        mock_order.fee = None
        
        # Create mock trades: one without fee, one with fee
        mock_trade_no_fee = mock.Mock()
        mock_trade_no_fee.fee = None
        
        mock_trade_with_fee = mock.Mock()
        mock_trade_with_fee.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Mock trades_manager.get_trades to return both trades
        trader.exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
            return_value=[mock_trade_no_fee, mock_trade_with_fee]
        )
        
        # Get trading order fee
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            # Should return calculated fee from the trade with fee
            _get_fees("USDT", 0.1),
            False
        )

    def test_estimates_fee_when_no_order_or_trade_fee(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Create mock order without fee
        mock_order = mock.Mock()
        mock_order.fee = None
        
        # Create mock trades without fee
        mock_trade = mock.Mock()
        mock_trade.fee = None
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Mock trades_manager.get_trades
        trader.exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
            return_value=[mock_trade]
        )
        
        # Mock get_trade_fee
        mock_fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1"),
        }
        with mock.patch.object(
            trader.exchange_manager.exchange,
            "get_trade_fee",
            return_value=mock_fee
        ) as mock_get_trade_fee:
            # Get trading order fee
            # Should estimate fee and return True for is_estimated
            assert personal_data.get_real_or_estimated_trade_fee(
                trade
            ) == (
                mock_fee,
                True
            )
            
            # Verify get_trade_fee was called with correct parameters
            mock_get_trade_fee.assert_called_once_with(
                trade.symbol,
                enums.TraderOrderType.BUY_LIMIT,  # BUY trade -> BUY_LIMIT
                trade.executed_quantity,
                trade.executed_price,
                trade.taker_or_maker
            )

    def test_handles_order_not_found_exception(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.1"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Mock orders_manager.get_order to raise KeyError (order not found)
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            side_effect=KeyError("Order not found")
        )
        
        # Create mock trade with fee
        mock_trade = mock.Mock()
        mock_trade.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),
        }
        
        # Mock trades_manager.get_trades
        trader.exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
            return_value=[mock_trade]
        )
        
        # Get trading order fee
        # Should fall back to trade fee
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("USDT", 0.1),
            False
        )

    def test_calculates_base_fee_correctly(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.BUY, decimal.Decimal("0.5"), decimal.Decimal("1000"), SYMBOL, None
        )
        
        # Create mock order with fee in base currency
        mock_order = mock.Mock()
        mock_order.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "BTC",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.002"),  # 0.2%
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Get trading order fee
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            _get_fees("BTC", 0.001),
            False
        )

    def test_calculates_quote_fee_correctly(self, simulated_trader):
        _, _, trader = simulated_trader
        trade = self.create_trade(
            trader, "order_123", enums.TradeOrderSide.SELL, decimal.Decimal("0.2"), decimal.Decimal("5000"), SYMBOL, None
        )
        
        # Create mock order with fee in quote currency
        mock_order = mock.Mock()
        mock_order.fee = {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
            enums.FeePropertyColumns.RATE.value: decimal.Decimal("0.001"),  # 0.1%
        }
        
        # Mock orders_manager.get_order
        trader.exchange_manager.exchange_personal_data.orders_manager.get_order = mock.Mock(
            return_value=mock_order
        )
        
        # Get trading order fee
        assert personal_data.get_real_or_estimated_trade_fee(
            trade
        ) == (
            # Fee cost = rate * amount * price = 0.001 * 0.2 * 5000 = 1.0 USDT
            _get_fees("USDT", 1.0),
            False
        )
