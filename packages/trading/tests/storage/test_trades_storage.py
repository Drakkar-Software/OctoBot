import decimal
import mock

import octobot_trading.storage.trades_storage as trades_storage_module

TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


class TestTradesStorageUsdLikeVolume:
    def test_linear_trade_uses_qualified_quote_for_usd_like_volume(self):
        storage = trades_storage_module.TradesStorage.__new__(trades_storage_module.TradesStorage)
        storage.exchange_manager = mock.Mock()
        value_converter = mock.Mock()
        value_converter.get_usd_like_value = mock.Mock(return_value=decimal.Decimal("100"))
        storage.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter = (
            value_converter
        )
        trade = mock.Mock()
        trade.symbol = TICKER_WISE_SYMBOL
        trade.total_cost = decimal.Decimal("50")
        trade.to_dict.return_value = {}

        storage._get_trade_dict_with_usd_like_volume(trade)

        value_converter.get_usd_like_value.assert_called_once_with("USDT@ETH", decimal.Decimal("50"))

    def test_inverse_trade_uses_qualified_base_for_usd_like_volume(self):
        storage = trades_storage_module.TradesStorage.__new__(trades_storage_module.TradesStorage)
        storage.exchange_manager = mock.Mock()
        value_converter = mock.Mock()
        value_converter.get_usd_like_value = mock.Mock(return_value=decimal.Decimal("100"))
        storage.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter = (
            value_converter
        )
        trade = mock.Mock()
        trade.symbol = "BTC/USDT:BTC"
        trade.total_cost = decimal.Decimal("50")
        trade.to_dict.return_value = {}

        storage._get_trade_dict_with_usd_like_volume(trade)

        value_converter.get_usd_like_value.assert_called_once_with("BTC", decimal.Decimal("50"))
