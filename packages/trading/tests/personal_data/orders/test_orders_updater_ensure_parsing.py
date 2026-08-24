import mock
import pytest

import octobot_trading.personal_data.orders.channel.orders_updater as orders_updater_module


class TestOrdersUpdaterEnsureParsing:
    def test_delegates_to_parse_order_instance(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.exchange_name = "binance"
        parsed_order = mock.MagicMock()
        parsed_order.to_dict.return_value = {"id": "order-1"}
        import octobot_trading.enums as trading_enums
        order = {
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            "id": "order-1",
        }
        with mock.patch.object(
            orders_updater_module.OrdersUpdater,
            "parse_order_instance",
            return_value=parsed_order,
        ) as parse_order_mock:
            result = orders_updater_module.OrdersUpdater.ensure_parsing(
                exchange_manager, order, True, True
            )
        parse_order_mock.assert_called_once_with(exchange_manager, order, True)
        assert result == {"id": "order-1"}

    def test_ignores_unsupported_order_when_requested(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.exchange_name = "binance"
        import octobot_trading.enums as trading_enums
        unsupported_order = {
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: (
                trading_enums.TradeOrderType.UNSUPPORTED.value
            ),
        }
        with mock.patch.object(
            orders_updater_module.OrdersUpdater,
            "parse_order_instance",
        ) as parse_order_mock:
            result = orders_updater_module.OrdersUpdater.ensure_parsing(
                exchange_manager, unsupported_order, True, True
            )
        parse_order_mock.assert_not_called()
        assert result is None
