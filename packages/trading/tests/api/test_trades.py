#  Drakkar-Software OctoBot-Trading
import decimal
import mock
import pytest

import octobot_trading.api.trades as trades_api
import octobot_trading.enums as enums

TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


class TestTradeFilterNetworkQualified:
    def test_quote_filter_uses_qualified_quote(self):
        trade = mock.Mock()
        trade.status = enums.OrderStatus.CLOSED
        trade.symbol = TICKER_WISE_SYMBOL
        trade.timestamp = 1
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(return_value=[trade])

        assert trades_api.get_trade_history(exchange_manager, quote="USDT@ETH") == [trade]
        assert trades_api.get_trade_history(exchange_manager, quote="USDT") == []
