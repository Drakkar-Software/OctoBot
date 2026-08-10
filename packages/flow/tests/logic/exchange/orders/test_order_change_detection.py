#  Drakkar-Software OctoBot-Flow

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow.logic.exchange.orders.order_change_detection as order_change_detection_module


def _order_dict(exchange_id: str) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,
            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0,
        }
    }


class TestDetectChangedOrderIds:
    def test_returns_disappeared_order_ids(self):
        previous_ids = {"order-1", "order-2"}
        current_orders = [_order_dict("order-2")]
        changed_ids = order_change_detection_module.detect_changed_order_ids(
            previous_ids,
            current_orders,
        )
        assert changed_ids == {"order-1"}

    def test_returns_empty_when_no_previous_orders(self):
        changed_ids = order_change_detection_module.detect_changed_order_ids(
            set(),
            [_order_dict("order-1")],
        )
        assert changed_ids == set()
